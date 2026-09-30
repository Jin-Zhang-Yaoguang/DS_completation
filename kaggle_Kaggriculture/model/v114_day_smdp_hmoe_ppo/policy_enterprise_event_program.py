"""Independent multi-product enterprise expert for V114 Iteration 8."""

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


SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"COW": 400, "SHEEP": 500}
ANIMAL_PRODUCT = {"COW": "MILK", "SHEEP": "WOOL"}
ANIMAL_STRUCTURE = {"COW": "PASTURE", "SHEEP": "PASTURE"}
LAND_PRICES = (1000, 2000, 4000)


@dataclass(frozen=True)
class EnterpriseProfile:
    name: str
    crop_weights: tuple[tuple[str, float], ...]
    animal: str | None
    worker_cap: int
    cash_reserve: int

    def __post_init__(self) -> None:
        if not self.crop_weights:
            raise ValueError("crop_weights may not be empty")
        if any(crop not in SEED_COST or weight <= 0 for crop, weight in self.crop_weights):
            raise ValueError("invalid crop_weights")
        if self.animal not in (None, "COW", "SHEEP"):
            raise ValueError("animal must be COW, SHEEP or None")
        if self.worker_cap < 1 or self.cash_reserve < 0:
            raise ValueError("invalid worker or cash contract")


PROFILES = {
    "GRAIN_MELON": EnterpriseProfile(
        "GRAIN_MELON", (("WHEAT", 0.30), ("MELON", 0.70)), None, 10, 500
    ),
    "DAIRY_BERRY": EnterpriseProfile(
        "DAIRY_BERRY", (("WHEAT", 0.55), ("STRAWBERRY", 0.45)), "COW", 10, 600
    ),
    "WOOL_MELON": EnterpriseProfile(
        "WOOL_MELON", (("WHEAT", 0.45), ("MELON", 0.55)), "SHEEP", 10, 600
    ),
}


@dataclass(frozen=True)
class EnterpriseTask:
    task_id: str
    priority: int
    target: tuple[int, int]
    action: tuple[Any, ...]
    requires_item: str | None = None


def _manhattan(left: tuple[int, int], right: tuple[int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _structure_target(board_size: int) -> tuple[int, int]:
    half = max(1, board_size // 2)
    return half - 1, half - 1


def _crop_assignment(
    coordinates: Sequence[tuple[int, int]], profile: EnterpriseProfile
) -> dict[tuple[int, int], str]:
    ordered = sorted(coordinates, key=lambda xy: (xy[1], xy[0]))
    crops = [crop for crop, _ in profile.crop_weights]
    weights = [float(weight) for _, weight in profile.crop_weights]
    total = sum(weights)
    quotas = [int(math.floor(len(ordered) * weight / total)) for weight in weights]
    for index in range(len(ordered) - sum(quotas)):
        quotas[index % len(quotas)] += 1
    labels: list[str] = []
    for crop, quota in zip(crops, quotas):
        labels.extend([crop] * quota)
    # Interleave product lines spatially, preventing one distant block from
    # monopolising a crop while retaining deterministic quotas.
    labels.sort(key=lambda crop: crops.index(crop))
    interleaved = [labels[(index * len(crops)) % len(labels)] for index in range(len(labels))]
    # The modular permutation can repeat indices when crop count and tile count
    # share factors. Fall back to a smooth weighted round-robin label stream.
    deficits = [0.0] * len(crops)
    stream: list[str] = []
    remaining = quotas[:]
    for _ in ordered:
        for index, weight in enumerate(weights):
            deficits[index] += weight / total
        candidates = [index for index, count in enumerate(remaining) if count > 0]
        chosen = max(candidates, key=lambda index: (deficits[index], -index))
        stream.append(crops[chosen])
        deficits[chosen] -= 1.0
        remaining[chosen] -= 1
    del interleaved
    return dict(zip(ordered, stream))


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


class EnterpriseEventProgramPolicy:
    """Create all unit and market actions from a new enterprise task graph."""

    def __init__(self, profile: EnterpriseProfile | str) -> None:
        self.profile = PROFILES[str(profile)] if isinstance(profile, str) else profile
        self.name = self.profile.name
        self.action_steps = 0
        self.manager_decision_count = 0
        self.terminal_execution_steps = 0
        self._terminal_option_active = False
        self.contract_violation_count = 0
        self.terminal_procurement_count = 0
        self.sale_units = {product: 0 for product in PRODUCTS}
        self.sale_events = {product: 0 for product in PRODUCTS}
        self.last_audit: dict[str, Any] | None = None

    def _record_manager_boundary(self, step: int, terminal: bool) -> None:
        """Count real option selections, not every turn of terminal execution."""

        if terminal:
            self.terminal_execution_steps += 1
            if not self._terminal_option_active:
                self._terminal_option_active = True
                self.manager_decision_count += 1
        elif step % 24 == 0:
            self.manager_decision_count += 1

    def _animal_tasks(self, observation: Mapping[str, Any]) -> list[EnterpriseTask]:
        animal = self.profile.animal
        if animal is None:
            return []
        tiles = _tiles(observation)
        board_size = len(tiles) or 10
        target = _structure_target(board_size)
        tile = tiles[target[1]][target[0]]
        tasks: list[EnterpriseTask] = []
        if isinstance(tile, Mapping) and _get(tile, "animal", None) == animal:
            if _integer(_get(tile, "yield_units", 0)) > 0:
                tasks.append(EnterpriseTask(f"animal-harvest:{animal}", 0, target, ("HARVEST",)))
            if bool(_get(tile, "fertilizer_available", False)):
                tasks.append(EnterpriseTask(f"animal-fertilizer:{animal}", 1, target, ("COLLECT_FERTILIZER",)))
            if not bool(_get(tile, "fed_today", False)):
                carrying = any(_integer(_get(_unit_inventory(observation, index), "WHEAT", 0)) > 0 for index in range(len(_unit_positions(observation))))
                shed_wheat = _integer(_get(_get(_private(observation), "shed", {}) or {}, "WHEAT", 0))
                if carrying:
                    tasks.append(EnterpriseTask(f"animal-feed:{animal}", 2, target, ("FEED",), "WHEAT"))
                elif shed_wheat > 0:
                    pickup = min(_shed_access_tiles(board_size), key=lambda xy: (_manhattan(xy, target), xy[1], xy[0]))
                    tasks.append(EnterpriseTask(f"pickup-feed:{animal}", 2, pickup, ("PICKUP", "WHEAT", 1)))
            if not bool(_get(tile, "cared_today", False)):
                tasks.append(EnterpriseTask(f"animal-care:{animal}", 3, target, ("CARE",)))
            return tasks

        if isinstance(tile, Mapping) and _get(tile, "kind", None) == ANIMAL_STRUCTURE[animal]:
            carrying = any(_integer(_get(_unit_inventory(observation, index), animal, 0)) > 0 for index in range(len(_unit_positions(observation))))
            shed_animal = _integer(_get(_get(_private(observation), "shed", {}) or {}, animal, 0))
            if carrying:
                tasks.append(EnterpriseTask(f"place:{animal}", 0, target, ("PLACE", animal), animal))
            elif shed_animal > 0:
                pickup = min(_shed_access_tiles(board_size), key=lambda xy: (_manhattan(xy, target), xy[1], xy[0]))
                tasks.append(EnterpriseTask(f"pickup:{animal}", 0, pickup, ("PICKUP", animal, 1)))
            return tasks

        if isinstance(tile, Mapping) and _get(tile, "kind", None) == "WEED":
            tasks.append(EnterpriseTask("clear-structure-weed", 0, target, ("DIG",)))
        elif tile is None:
            tasks.append(EnterpriseTask("build-pasture", 0, target, ("BUILD_PASTURE",)))
        return tasks

    def _crop_tasks(self, observation: Mapping[str, Any]) -> list[EnterpriseTask]:
        day = observation_day(observation)
        tiles = _tiles(observation)
        board_size = len(tiles) or 10
        reserved = {_structure_target(board_size)} if self.profile.animal else set()
        unlocked = [
            (x, y)
            for y, row in enumerate(tiles)
            for x, tile in enumerate(row)
            if tile != "LOCKED" and (x, y) not in reserved
        ]
        desired = _crop_assignment(unlocked, self.profile)
        seeds = _get(_private(observation), "seeds", {}) or {}
        seeds_remaining = {crop: max(0, _integer(_get(seeds, crop, 0))) for crop, _ in self.profile.crop_weights}
        tasks: list[EnterpriseTask] = []
        for target, crop in desired.items():
            x, y = target
            tile = tiles[y][x]
            if isinstance(tile, Mapping) and _get(tile, "kind", None) == "PLANT":
                planted_day = _integer(_get(tile, "planted_day", day), day)
                first_yield = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}.get(str(_get(tile, "crop", "")), 99)
                if day - planted_day >= first_yield and _integer(_get(tile, "yield_units", 0)) > 0:
                    tasks.append(EnterpriseTask(f"harvest:{x}:{y}", 4, target, ("HARVEST",)))
                elif not bool(_get(tile, "watered_today", False)):
                    tasks.append(EnterpriseTask(f"water:{x}:{y}", 6, target, ("WATER",)))
            elif isinstance(tile, Mapping) and _get(tile, "kind", None) == "WEED":
                tasks.append(EnterpriseTask(f"weed:{x}:{y}", 7, target, ("DIG",)))
            elif tile is None and seeds_remaining.get(crop, 0) > 0:
                tasks.append(EnterpriseTask(f"plant:{crop}:{x}:{y}", 8, target, ("PLANT", crop)))
                seeds_remaining[crop] -= 1
        return tasks

    def _assign_tasks(
        self, observation: Mapping[str, Any], tasks: Sequence[EnterpriseTask]
    ) -> tuple[list[list[Any]], list[dict[str, Any]]]:
        positions = _unit_positions(observation)
        remaining = set(range(len(positions)))
        assignments: dict[int, EnterpriseTask] = {}
        for priority in sorted({task.priority for task in tasks}):
            current = [task for task in tasks if task.priority == priority]
            while remaining and current:
                candidates = []
                for unit in remaining:
                    inventory = _unit_inventory(observation, unit)
                    for task in current:
                        if task.requires_item and _integer(_get(inventory, task.requires_item, 0)) <= 0:
                            continue
                        candidates.append((_manhattan(positions[unit], task.target), unit, task.target[1], task.target[0], task.task_id, task))
                if not candidates:
                    break
                _, unit, _, _, _, task = min(candidates, key=lambda row: row[:-1])
                assignments[unit] = task
                remaining.remove(unit)
                current.remove(task)
        actions: list[list[Any]] = []
        audit: list[dict[str, Any]] = []
        for unit, position in enumerate(positions):
            task = assignments.get(unit)
            if task is None:
                action: list[Any] = ["PASS"]
            elif position != task.target:
                action = _one_step_toward(position, task.target)
            else:
                action = list(task.action)
            actions.append(action)
            audit.append({"unit": unit, "task": task.task_id if task else None, "action": list(action)})
        return actions, audit

    def _terminal_actions(self, observation: Mapping[str, Any]) -> list[list[Any]]:
        positions = _unit_positions(observation)
        board_size = len(_tiles(observation)) or 10
        access = set(_shed_access_tiles(board_size))
        actions: list[list[Any]] = []
        for index, position in enumerate(positions):
            inventory = _unit_inventory(observation, index)
            if any(_integer(value) > 0 for value in inventory.values()):
                actions.append(["DROP"] if position in access else _one_step_toward(position, _nearest_shed(position, board_size)))
            else:
                actions.append(["PASS"])
        return actions

    def _market_actions(
        self, observation: Mapping[str, Any], unit_actions: Sequence[Sequence[Any]], terminal: bool
    ) -> tuple[list[list[Any]], dict[str, Any]]:
        farm = _own_farm(observation)
        private = _private(observation)
        money = float(_get(farm, "money", 0.0) or 0.0)
        remaining = max(0.0, money - self.profile.cash_reserve)
        projected = _projected_shed(observation, unit_actions)
        prices = _get(_get(observation, "market", {}) or {}, "prices", {}) or {}
        step = observation_step(observation)
        orders: list[list[Any]] = []
        sold: dict[str, int] = {}
        sale_window = terminal or step % 4 == 1
        if sale_window:
            candidates = [
                (max(1, _integer(_get(prices, product, BASE_PRICE[product]), BASE_PRICE[product])), product, quantity)
                for product, quantity in projected.items()
                if quantity > 0
            ]
            for _, product, quantity in sorted(candidates, reverse=True):
                if len(orders) >= MAX_MARKET_ORDERS:
                    break
                orders.append(["SELL", product, quantity])
                sold[product] = quantity

        procurement: list[list[Any]] = []
        if not terminal:
            day = observation_day(observation)
            unlocked = list(_get(farm, "unlocked_quadrants", []) or [])
            land_index = max(0, len(unlocked) - 1)
            if day >= 3 and land_index < len(LAND_PRICES) and LAND_PRICES[land_index] <= remaining:
                procurement.append(["BUY_LAND"])
                remaining -= LAND_PRICES[land_index]

            current_units = len(_unit_positions(observation))
            hires_today = max(0, _integer(_get(farm, "hires_today", 0)))
            pending_hires = 0
            while current_units + pending_hires < self.profile.worker_cap:
                cost = _fibonacci(hires_today + pending_hires)
                if cost > remaining:
                    break
                procurement.append(["HIRE"])
                remaining -= cost
                pending_hires += 1

            animal = self.profile.animal
            if animal:
                tiles = _tiles(observation)
                target = _structure_target(len(tiles) or 10)
                tile = tiles[target[1]][target[0]]
                has_placed = isinstance(tile, Mapping) and _get(tile, "animal", None) == animal
                shed = _get(private, "shed", {}) or {}
                carried = sum(_integer(_get(_unit_inventory(observation, index), animal, 0)) for index in range(len(_unit_positions(observation))))
                if (
                    isinstance(tile, Mapping)
                    and _get(tile, "kind", None) == ANIMAL_STRUCTURE[animal]
                    and not has_placed
                    and _integer(_get(shed, animal, 0)) + carried == 0
                    and ANIMAL_COST[animal] <= remaining
                ):
                    procurement.append(["BUY_ANIMAL", animal, 1])
                    remaining -= ANIMAL_COST[animal]

            tiles = _tiles(observation)
            board_size = len(tiles) or 10
            reserved = {_structure_target(board_size)} if animal else set()
            unlocked_coordinates = [
                (x, y) for y, row in enumerate(tiles) for x, tile in enumerate(row)
                if tile != "LOCKED" and (x, y) not in reserved
            ]
            desired = _crop_assignment(unlocked_coordinates, self.profile)
            seeds = _get(private, "seeds", {}) or {}
            for crop, _ in self.profile.crop_weights:
                empty_targets = sum(tiles[y][x] is None for (x, y), target_crop in desired.items() if target_crop == crop)
                need = max(0, empty_targets - _integer(_get(seeds, crop, 0)))
                affordable = int(remaining // SEED_COST[crop])
                quantity = min(need, affordable)
                if quantity > 0:
                    procurement.append(["BUY_SEED", crop, quantity])
                    remaining -= quantity * SEED_COST[crop]

        for order in procurement:
            if len(orders) >= MAX_MARKET_ORDERS:
                break
            orders.append(order)
        if terminal and any(order[0] != "SELL" for order in orders):
            self.terminal_procurement_count += 1
        for product, quantity in sold.items():
            self.sale_units[product] += quantity
            self.sale_events[product] += 1
        return orders, {"projected_shed": projected, "sold": sold, "procurement": procurement, "remaining_cash_budget": remaining}

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        step = observation_step(observation)
        terminal = step >= TERMINAL_START_STEP
        if terminal:
            unit_actions = self._terminal_actions(observation)
            assignments: list[dict[str, Any]] = []
        else:
            tasks = [*self._animal_tasks(observation), *self._crop_tasks(observation)]
            unit_actions, assignments = self._assign_tasks(observation, tasks)
        market, market_audit = self._market_actions(observation, unit_actions, terminal)
        if len(market) > MAX_MARKET_ORDERS:
            self.contract_violation_count += 1
            raise RuntimeError("enterprise market queue exceeds official limit")
        action = {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": market,
        }
        self.action_steps += 1
        self._record_manager_boundary(step, terminal)
        self.last_audit = {
            "step": step,
            "profile": self.profile.name,
            "terminal": terminal,
            "assignments": assignments,
            "market": market_audit,
        }
        return action

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = ["EnterpriseEventProgramPolicy", "EnterpriseProfile", "PROFILES"]
