"""Independent market-exposure-adaptive poultry enterprise for V114 Iteration 9."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from event_program import (
    BASE_PRICE,
    MAX_MARKET_ORDERS,
    PRODUCTS,
    TERMINAL_START_STEP,
    _fibonacci,
    _get,
    _integer,
    _nearest_shed,
    _one_step_toward,
    _own_farm,
    _private,
    _shed_access_tiles,
    _tiles,
    _unit_inventory,
    _unit_positions,
    observation_day,
    observation_step,
)
from market_residual import scheduled_demand_quantity


SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "MELON": 80}
FIRST_YIELD = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "MELON": 10}
LAND_PRICES = (1000, 2000, 4000)
WORKER_CAP = 12
CASH_RESERVE = 700
TARGET_GEESE = 6


@dataclass(frozen=True)
class PoultryTask:
    task_id: str
    priority: int
    target: tuple[int, int]
    action: tuple[Any, ...]
    requires_item: str | None = None


def _manhattan(left: tuple[int, int], right: tuple[int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _coop_targets(board_size: int) -> tuple[tuple[int, int], ...]:
    half = max(2, board_size // 2)
    candidates = (
        (half - 1, half - 1),
        (half - 2, half - 1),
        (half - 1, half - 2),
        (half - 2, half - 2),
        (half - 3, half - 1),
        (half - 1, half - 3),
    )
    return tuple((max(0, x), max(0, y)) for x, y in candidates)


def _expanded_coop_targets(board_size: int) -> tuple[tuple[int, int], ...]:
    half = max(2, board_size // 2)
    return (
        *_coop_targets(board_size),
        (half, half - 1),
        (half + 1, half - 1),
        (half, half - 2),
        (half + 1, half - 2),
        (half, half - 3),
        (half + 2, half - 1),
    )


def _projected_shed(
    observation: Mapping[str, Any], unit_actions: Sequence[Sequence[Any]]
) -> dict[str, int]:
    raw = _get(_private(observation), "shed", {}) or {}
    shed = {product: max(0, _integer(_get(raw, product, 0))) for product in PRODUCTS}
    positions = _unit_positions(observation)
    board_size = len(_tiles(observation)) or 10
    access = set(_shed_access_tiles(board_size))
    room = max(0, 100 - sum(max(0, _integer(value)) for value in raw.values()))
    for index, action in enumerate(unit_actions):
        if not action or action[0] != "DROP" or positions[index] not in access:
            continue
        for item, value in _unit_inventory(observation, index).items():
            quantity = min(max(0, _integer(value)), room)
            room -= quantity
            if item in shed:
                shed[item] += quantity
    return shed


class ExposureAdaptivePoultryPolicy:
    """Generate all actions for a six-coop, feed-aware, public-flow enterprise."""

    name = "EXPOSURE_ADAPTIVE_POULTRY"

    def __init__(self, *, target_geese: int = TARGET_GEESE, worker_cap: int = WORKER_CAP) -> None:
        if int(target_geese) not in (TARGET_GEESE, 12):
            raise ValueError("target_geese must be 6 or 12")
        self.target_geese = int(target_geese)
        self.worker_cap = int(worker_cap)
        self.action_steps = 0
        self.manager_decision_count = 0
        self.terminal_execution_steps = 0
        self._terminal_option_active = False
        self.contract_violation_count = 0
        self.terminal_procurement_count = 0
        self.sale_units = {product: 0 for product in PRODUCTS}
        self.previous_market_inventory: dict[str, float] | None = None
        self.previous_own_sales = {product: 0 for product in PRODUCTS}
        self.opponent_net_supply_ema = {product: 0.0 for product in PRODUCTS}
        self.cash_crop_by_day: dict[int, str] = {}
        self.max_geese_placed = 0
        self.last_audit: dict[str, Any] | None = None

    def _record_manager_boundary(self, step: int, terminal: bool) -> None:
        """Count the terminal option once while auditing all terminal turns."""

        if terminal:
            self.terminal_execution_steps += 1
            if not self._terminal_option_active:
                self._terminal_option_active = True
                self.manager_decision_count += 1
        elif step % 24 == 0:
            self.manager_decision_count += 1

    def coop_targets(self, board_size: int) -> tuple[tuple[int, int], ...]:
        targets = _expanded_coop_targets(board_size) if self.target_geese > 6 else _coop_targets(board_size)
        return targets[: self.target_geese]

    def _observe_public_flow(self, observation: Mapping[str, Any]) -> None:
        current = _get(_get(observation, "market", {}) or {}, "inventory", {}) or {}
        current_inventory = {product: float(_get(current, product, 0.0) or 0.0) for product in PRODUCTS}
        if self.previous_market_inventory is not None:
            for product in PRODUCTS:
                demand = scheduled_demand_quantity(observation, product, previous_step=True)
                net_other_supply = (
                    current_inventory[product]
                    - self.previous_market_inventory[product]
                    - float(self.previous_own_sales.get(product, 0))
                    + float(demand)
                )
                self.opponent_net_supply_ema[product] = (
                    0.8 * self.opponent_net_supply_ema[product] + 0.2 * net_other_supply
                )
        self.previous_market_inventory = current_inventory
        self.previous_own_sales = {product: 0 for product in PRODUCTS}

    def _select_cash_crop(self, observation: Mapping[str, Any]) -> str:
        day = observation_day(observation)
        if day in self.cash_crop_by_day:
            return self.cash_crop_by_day[day]
        prices = _get(_get(observation, "market", {}) or {}, "prices", {}) or {}
        if day >= 18:
            candidates = ("WHEAT", "CARROT")
        elif day >= 14:
            candidates = ("WHEAT", "CARROT", "TOMATO")
        else:
            candidates = ("CARROT", "TOMATO", "MELON")
        roi_prior = {"WHEAT": 1.0, "CARROT": 1.1, "TOMATO": 0.9, "MELON": 1.8}
        def score(product: str) -> tuple[float, str]:
            price_ratio = float(_get(prices, product, BASE_PRICE[product]) or BASE_PRICE[product]) / BASE_PRICE[product]
            crowding = max(0.0, self.opponent_net_supply_ema[product])
            demand = scheduled_demand_quantity(observation, product, previous_step=False)
            value = roi_prior[product] * price_ratio + 0.08 * demand - 0.06 * crowding
            return value, product
        chosen = max(candidates, key=score)
        self.cash_crop_by_day[day] = chosen
        return chosen

    def _crop_map(self, observation: Mapping[str, Any]) -> dict[tuple[int, int], str]:
        tiles = _tiles(observation)
        reserved = set(self.coop_targets(len(tiles) or 10))
        coordinates = sorted(
            (
                (x, y)
                for y, row in enumerate(tiles)
                for x, tile in enumerate(row)
                if tile != "LOCKED" and (x, y) not in reserved
            ),
            key=lambda xy: (xy[1], xy[0]),
        )
        cash_crop = self._select_cash_crop(observation)
        wheat_quota = int(math.ceil(len(coordinates) * 0.35))
        # Spread feed wheat through the field so nearest-task dispatch does not
        # postpone the entire feed reserve behind one distant block.
        result: dict[tuple[int, int], str] = {}
        wheat_assigned = 0
        for index, coordinate in enumerate(coordinates):
            remaining = len(coordinates) - index
            need_wheat = wheat_quota - wheat_assigned
            choose_wheat = need_wheat > 0 and (index % 3 == 0 or need_wheat >= remaining)
            result[coordinate] = "WHEAT" if choose_wheat else cash_crop
            wheat_assigned += int(choose_wheat)
        return result

    def _animal_tasks(self, observation: Mapping[str, Any]) -> list[PoultryTask]:
        tiles = _tiles(observation)
        board_size = len(tiles) or 10
        positions = _unit_positions(observation)
        inventories = [_unit_inventory(observation, index) for index in range(len(positions))]
        shed = _get(_private(observation), "shed", {}) or {}
        targets = self.coop_targets(board_size)
        tasks: list[PoultryTask] = []
        occupied: list[tuple[int, int]] = []
        empty_coops: list[tuple[int, int]] = []
        for target in targets:
            tile = tiles[target[1]][target[0]]
            if isinstance(tile, Mapping) and _get(tile, "animal", None) == "GOOSE":
                occupied.append(target)
                if _integer(_get(tile, "yield_units", 0)) > 0:
                    tasks.append(PoultryTask(f"egg:{target}", 0, target, ("HARVEST",)))
            elif isinstance(tile, Mapping) and _get(tile, "kind", None) == "COOP":
                empty_coops.append(target)
            elif isinstance(tile, Mapping) and _get(tile, "kind", None) == "WEED":
                tasks.append(PoultryTask(f"clear-coop:{target}", 0, target, ("DIG",)))
            elif tile is None:
                tasks.append(PoultryTask(f"build-coop:{target}", 0, target, ("BUILD_COOP",)))
        self.max_geese_placed = max(self.max_geese_placed, len(occupied))

        carrying_geese = sum(_integer(_get(inv, "GOOSE", 0)) for inv in inventories)
        for target in empty_coops[:carrying_geese]:
            tasks.append(PoultryTask(f"place-goose:{target}", 1, target, ("PLACE", "GOOSE"), "GOOSE"))
        pickup_needed = min(
            max(0, len(empty_coops) - carrying_geese),
            _integer(_get(shed, "GOOSE", 0)),
        )
        access = _shed_access_tiles(board_size)
        for index in range(pickup_needed):
            target = access[index % len(access)]
            tasks.append(PoultryTask(f"pickup-goose:{index}", 1, target, ("PICKUP", "GOOSE", 1)))

        carrying_wheat = sum(_integer(_get(inv, "WHEAT", 0)) for inv in inventories)
        feed_targets = [
            target for target in occupied
            if not bool(_get(tiles[target[1]][target[0]], "fed_today", False))
        ]
        for target in feed_targets[:carrying_wheat]:
            tasks.append(PoultryTask(f"feed:{target}", 2, target, ("FEED",), "WHEAT"))
        feed_pickups = min(
            max(0, len(feed_targets) - carrying_wheat),
            _integer(_get(shed, "WHEAT", 0)),
        )
        for index in range(feed_pickups):
            target = access[index % len(access)]
            tasks.append(PoultryTask(f"pickup-feed:{index}", 2, target, ("PICKUP", "WHEAT", 1)))

        for target in occupied:
            tile = tiles[target[1]][target[0]]
            if not bool(_get(tile, "cared_today", False)):
                tasks.append(PoultryTask(f"care:{target}", 3, target, ("CARE",)))
            if bool(_get(tile, "fertilizer_available", False)):
                tasks.append(PoultryTask(f"fertilizer:{target}", 4, target, ("COLLECT_FERTILIZER",)))
        return tasks

    def _crop_tasks(self, observation: Mapping[str, Any]) -> list[PoultryTask]:
        day = observation_day(observation)
        tiles = _tiles(observation)
        desired = self._crop_map(observation)
        seeds = _get(_private(observation), "seeds", {}) or {}
        remaining = {crop: max(0, _integer(_get(seeds, crop, 0))) for crop in SEED_COST}
        tasks: list[PoultryTask] = []
        for target, crop in desired.items():
            x, y = target
            tile = tiles[y][x]
            if isinstance(tile, Mapping) and _get(tile, "kind", None) == "PLANT":
                planted = _integer(_get(tile, "planted_day", day), day)
                existing_crop = str(_get(tile, "crop", ""))
                if day - planted >= FIRST_YIELD.get(existing_crop, 99) and _integer(_get(tile, "yield_units", 0)) > 0:
                    tasks.append(PoultryTask(f"harvest:{target}", 5, target, ("HARVEST",)))
                elif not bool(_get(tile, "watered_today", False)):
                    tasks.append(PoultryTask(f"water:{target}", 7, target, ("WATER",)))
            elif isinstance(tile, Mapping) and _get(tile, "kind", None) == "WEED":
                tasks.append(PoultryTask(f"weed:{target}", 8, target, ("DIG",)))
            elif tile is None and remaining.get(crop, 0) > 0:
                tasks.append(PoultryTask(f"plant:{crop}:{target}", 9, target, ("PLANT", crop)))
                remaining[crop] -= 1
        return tasks

    def _assign(
        self, observation: Mapping[str, Any], tasks: Sequence[PoultryTask]
    ) -> tuple[list[list[Any]], list[dict[str, Any]]]:
        positions = _unit_positions(observation)
        remaining = set(range(len(positions)))
        assigned: dict[int, PoultryTask] = {}
        for priority in sorted({task.priority for task in tasks}):
            group = [task for task in tasks if task.priority == priority]
            while remaining and group:
                candidates = []
                for unit in remaining:
                    inventory = _unit_inventory(observation, unit)
                    for task in group:
                        if task.requires_item and _integer(_get(inventory, task.requires_item, 0)) <= 0:
                            continue
                        candidates.append((_manhattan(positions[unit], task.target), unit, task.target[1], task.target[0], task.task_id, task))
                if not candidates:
                    break
                _, unit, _, _, _, task = min(candidates, key=lambda row: row[:-1])
                assigned[unit] = task
                remaining.remove(unit)
                group.remove(task)
        actions: list[list[Any]] = []
        audit: list[dict[str, Any]] = []
        for unit, position in enumerate(positions):
            task = assigned.get(unit)
            action = ["PASS"] if task is None else (
                _one_step_toward(position, task.target) if position != task.target else list(task.action)
            )
            actions.append(action)
            audit.append({"unit": unit, "task": task.task_id if task else None, "action": list(action)})
        return actions, audit

    def _terminal_actions(self, observation: Mapping[str, Any]) -> list[list[Any]]:
        board_size = len(_tiles(observation)) or 10
        access = set(_shed_access_tiles(board_size))
        actions: list[list[Any]] = []
        for index, position in enumerate(_unit_positions(observation)):
            inventory = _unit_inventory(observation, index)
            if any(_integer(value) > 0 for value in inventory.values()):
                actions.append(["DROP"] if position in access else _one_step_toward(position, _nearest_shed(position, board_size)))
            else:
                actions.append(["PASS"])
        return actions

    def _market(
        self, observation: Mapping[str, Any], unit_actions: Sequence[Sequence[Any]], terminal: bool
    ) -> tuple[list[list[Any]], dict[str, Any]]:
        farm = _own_farm(observation)
        private = _private(observation)
        money = float(_get(farm, "money", 0.0) or 0.0)
        remaining_cash = max(0.0, money - CASH_RESERVE)
        projected = _projected_shed(observation, unit_actions)
        prices = _get(_get(observation, "market", {}) or {}, "prices", {}) or {}
        step = observation_step(observation)
        orders: list[list[Any]] = []
        sold: dict[str, int] = {}
        geese = self._placed_geese(observation)
        feed_reserve = min(projected.get("WHEAT", 0), max(12, geese * 2))
        if terminal or step % 4 == 1:
            candidates = []
            for product, available in projected.items():
                quantity = available - feed_reserve if product == "WHEAT" and not terminal else available
                if quantity > 0:
                    price = max(1, _integer(_get(prices, product, BASE_PRICE[product]), BASE_PRICE[product]))
                    candidates.append((price, product, quantity))
            for _, product, quantity in sorted(candidates, reverse=True):
                if len(orders) >= MAX_MARKET_ORDERS:
                    break
                orders.append(["SELL", product, quantity])
                sold[product] = quantity

        procurement: list[list[Any]] = []
        if not terminal:
            day = observation_day(observation)
            current_units = len(_unit_positions(observation))
            hires_today = max(0, _integer(_get(farm, "hires_today", 0)))
            middle_cap = min(self.worker_cap, 10 if self.target_geese > 6 else 9)
            staged_worker_cap = 6 if day < 5 else (middle_cap if day < 10 else self.worker_cap)
            pending_hires = 0
            while current_units + pending_hires < staged_worker_cap:
                cost = _fibonacci(hires_today + pending_hires)
                if cost > remaining_cash:
                    break
                procurement.append(["HIRE"])
                remaining_cash -= cost
                pending_hires += 1

            tiles = _tiles(observation)
            targets = self.coop_targets(len(tiles) or 10)
            empty_coops = sum(
                isinstance(tiles[y][x], Mapping)
                and _get(tiles[y][x], "kind", None) == "COOP"
                and _get(tiles[y][x], "animal", None) is None
                for x, y in targets
            )
            shed = _get(private, "shed", {}) or {}
            carried = sum(_integer(_get(_unit_inventory(observation, index), "GOOSE", 0)) for index in range(len(_unit_positions(observation))))
            missing = max(0, empty_coops - _integer(_get(shed, "GOOSE", 0)) - carried)
            existing_or_planned_geese = self._placed_geese(observation) + _integer(_get(shed, "GOOSE", 0)) + carried + missing
            feed_target = max(12, existing_or_planned_geese * 2)
            carried_wheat = sum(_integer(_get(_unit_inventory(observation, index), "WHEAT", 0)) for index in range(len(_unit_positions(observation))))
            feed_shortfall = max(0, feed_target - projected.get("WHEAT", 0) - carried_wheat)
            wheat_price = max(1, _integer(_get(prices, "WHEAT", BASE_PRICE["WHEAT"]), BASE_PRICE["WHEAT"]))
            buy_feed = min(feed_shortfall, int(remaining_cash // wheat_price))
            if buy_feed > 0:
                procurement.append(["BUY_PRODUCT", "WHEAT", buy_feed])
                remaining_cash -= wheat_price * buy_feed
            affordable = int(remaining_cash // 300)
            buy_geese = min(missing, affordable)
            if buy_geese > 0:
                procurement.append(["BUY_ANIMAL", "GOOSE", buy_geese])
                remaining_cash -= 300 * buy_geese

            desired = self._crop_map(observation)
            seeds = _get(private, "seeds", {}) or {}
            for crop in sorted(set(desired.values()), key=lambda item: (item != "WHEAT", item)):
                empty_targets = sum(tiles[y][x] is None for (x, y), item in desired.items() if item == crop)
                need = max(0, empty_targets - _integer(_get(seeds, crop, 0)))
                quantity = min(need, int(remaining_cash // SEED_COST[crop]))
                if quantity > 0:
                    procurement.append(["BUY_SEED", crop, quantity])
                    remaining_cash -= quantity * SEED_COST[crop]

            unlocked = list(_get(farm, "unlocked_quadrants", []) or [])
            land_index = max(0, len(unlocked) - 1)
            land_price = LAND_PRICES[land_index] if land_index < len(LAND_PRICES) else None
            if (
                day >= 6
                and self._placed_geese(observation) >= 5
                and land_price is not None
                and land_price + 1000 <= remaining_cash
            ):
                procurement.append(["BUY_LAND"])
                remaining_cash -= land_price
        for order in procurement:
            if len(orders) >= MAX_MARKET_ORDERS:
                break
            orders.append(order)
        if terminal and any(order[0] != "SELL" for order in orders):
            self.terminal_procurement_count += 1
        for product, quantity in sold.items():
            self.sale_units[product] += quantity
            self.previous_own_sales[product] += quantity
        return orders, {
            "sold": sold,
            "feed_reserve": feed_reserve,
            "procurement": procurement,
            "cash_crop": self._select_cash_crop(observation),
            "opponent_net_supply_ema": dict(self.opponent_net_supply_ema),
        }

    def _placed_geese(self, observation: Mapping[str, Any]) -> int:
        tiles = _tiles(observation)
        return sum(
            isinstance(tiles[y][x], Mapping) and _get(tiles[y][x], "animal", None) == "GOOSE"
            for x, y in self.coop_targets(len(tiles) or 10)
        )

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        self._observe_public_flow(observation)
        step = observation_step(observation)
        terminal = step >= TERMINAL_START_STEP
        if terminal:
            unit_actions = self._terminal_actions(observation)
            assignments: list[dict[str, Any]] = []
        else:
            tasks = [*self._animal_tasks(observation), *self._crop_tasks(observation)]
            unit_actions, assignments = self._assign(observation, tasks)
        market, market_audit = self._market(observation, unit_actions, terminal)
        if len(market) > MAX_MARKET_ORDERS:
            self.contract_violation_count += 1
            raise RuntimeError("poultry market queue exceeds official limit")
        self.action_steps += 1
        self._record_manager_boundary(step, terminal)
        self.max_geese_placed = max(self.max_geese_placed, self._placed_geese(observation))
        self.last_audit = {
            "step": step,
            "terminal": terminal,
            "assignments": assignments,
            "market": market_audit,
            "geese_placed": self._placed_geese(observation),
        }
        return {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": market,
        }

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = [
    "ExposureAdaptivePoultryPolicy",
    "TARGET_GEESE",
    "WORKER_CAP",
    "_coop_targets",
    "_expanded_coop_targets",
]
