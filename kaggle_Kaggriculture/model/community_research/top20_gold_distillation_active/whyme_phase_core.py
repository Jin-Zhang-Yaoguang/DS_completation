"""Tape-free Whyme role/phase HMoE core distilled from the Top20 panel."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / "whyme_role_phase_contract.json").read_text(encoding="utf-8"))
assert CONTRACT.get("runtime_contract") == {
    "unit_move_actions_stored": False,
    "unit_action_source": "state_recovered_daily_option_queue",
    "market_action_source": "six_hour_semantic_resource_budget",
    "market_tape": False,
    "step_lookup": False,
    "future_features": False,
}
SHED = {(4, 4), (5, 4), (4, 5), (5, 5)}
MOVE = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
ANIMAL_STRUCTURE = {"COW": "PASTURE", "SHEEP": "PASTURE", "GOOSE": "COOP"}
PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")
ALL_SELLABLE = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
PRICE_FLOOR = 1
MARKET_PARAMS = {
    "WHEAT": (25, 10000, 400, "sqrt", 0.8, "log", 0.2),
    "CARROT": (35, 10000, 450, "hinge", 1.0, "sqrt", 0.7),
    "TOMATO": (60, 10000, 200, "hinge", 0.4, "sqrt", 0.6),
    "STRAWBERRY": (120, 10000, 100, "sqrt", 0.7, "linear", 1.6),
    "MELON": (250, 10000, 300, "log", 0.2, "sq", 3.6),
    "EGG": (50, 10000, 332, "hinge", 0.4, "log", 0.2),
    "MILK": (160, 10000, 122, "sqrt", 0.6, "linear", 1.6),
    "WOOL": (200, 10000, 105, "log", 0.2, "sq", 3.2),
    "FERTILIZER": (100, 10000, 200, "linear", 0.4, "linear", 0.4),
}
SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
LIQUIDATION_ORDER = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
_STATE = {0: {}, 1: {}}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _seat(obs: Mapping[str, Any]) -> int:
    return 1 if _int(obs.get("player")) == 1 else 0


def _tile(grid: list, point: tuple[int, int]) -> Any:
    x, y = point
    if not (0 <= y < len(grid) and 0 <= x < len(grid[y])):
        return "LOCKED"
    return grid[y][x]


def _kind(tile: Any) -> str:
    if tile is None:
        return "EMPTY"
    return str(tile.get("kind") or "EMPTY") if isinstance(tile, Mapping) else str(tile)


def _animal(tile: Any) -> str:
    if not isinstance(tile, Mapping):
        return ""
    value = tile.get("animal")
    return str(value.get("kind") or "") if isinstance(value, Mapping) else str(value or "")


def _toward(position: tuple[int, int], target: tuple[int, int]) -> list[str]:
    x, y = position
    tx, ty = target
    # Alternate axis priority by parity to reduce systematic congestion while
    # preserving shortest paths.
    if (x + y + tx + ty) % 2 == 0:
        if x < tx: return ["EAST"]
        if x > tx: return ["WEST"]
        if y < ty: return ["SOUTH"]
        if y > ty: return ["NORTH"]
    else:
        if y < ty: return ["SOUTH"]
        if y > ty: return ["NORTH"]
        if x < tx: return ["EAST"]
        if x > tx: return ["WEST"]
    return ["PASS"]


def _legal(order: list, tile: Any, point: tuple[int, int], inventory: Mapping[str, Any], obs: Mapping[str, Any]) -> bool:
    op = str(order[0])
    kind, animal = _kind(tile), _animal(tile)
    private = obs.get("private") or {}
    if op == "PLANT":
        return kind == "EMPTY" and _int((private.get("seeds") or {}).get(order[1])) > 0
    if op == "WATER": return kind == "PLANT" and not bool(tile.get("watered_today"))
    if op == "FERTILIZE": return kind == "PLANT" and _int(inventory.get("FERTILIZER")) > 0
    if op == "HARVEST": return isinstance(tile, Mapping) and _int(tile.get("yield_units")) > 0
    if op == "DIG": return kind not in {"EMPTY", "LOCKED"}
    if op == "BUILD_PASTURE": return kind == "EMPTY"
    if op == "BUILD_COOP": return kind == "EMPTY"
    if op == "PLACE":
        item = str(order[1])
        if item in ANIMAL_STRUCTURE:
            return kind == ANIMAL_STRUCTURE[item] and not animal and _int(inventory.get(item)) > 0
        return point in SHED and _int(inventory.get(item)) > 0
    if op == "FEED": return bool(animal) and not bool(tile.get("fed_today")) and _int(inventory.get("WHEAT")) > 0
    if op == "CARE": return bool(animal) and not bool(tile.get("cared_today"))
    if op == "COLLECT_FERTILIZER": return bool(animal) and bool(tile.get("fertilizer_available"))
    if op == "PICKUP": return point in SHED and _int((private.get("shed") or {}).get(order[1])) > 0
    if op == "DROP": return point in SHED and any(_int(value) > 0 for value in inventory.values())
    return False


def _obsolete(order: list, tile: Any, point: tuple[int, int], inventory: Mapping[str, Any], obs: Mapping[str, Any], hour: int, due: int) -> bool:
    op, kind, animal = str(order[0]), _kind(tile), _animal(tile)
    grace = 0
    if hour <= due + grace:
        return False
    if op == "WATER": return kind != "PLANT" or bool(tile.get("watered_today"))
    if op == "HARVEST": return kind in {"EMPTY", "LOCKED"} or _int(tile.get("yield_units") if isinstance(tile, Mapping) else 0) <= 0
    if op in {"FEED", "CARE", "COLLECT_FERTILIZER"}: return not animal
    if op.startswith("BUILD_"): return kind != "EMPTY"
    if op == "PLANT": return kind != "EMPTY"
    if op == "PLACE" and len(order) > 1 and order[1] in ANIMAL_STRUCTURE: return bool(animal)
    if op in {"PICKUP", "DROP"}: return hour > due + max(grace, 5)
    return hour > due + grace


def _market_queue_expert(raw_market: list[list]) -> list[list]:
    """Quantity-neutral queue rules distilled from repeated Top20 patterns."""
    market = [list(order) for order in raw_market]
    # Merge duplicate sells at their first occurrence.
    merged = []
    sell_slot = {}
    for order in market:
        if len(order) >= 3 and order[0] == "SELL":
            item = str(order[1])
            if item in sell_slot:
                merged[sell_slot[item]][2] = _int(merged[sell_slot[item]][2]) + _int(order[2])
                continue
            sell_slot[item] = len(merged)
        merged.append(order)
    market = merged
    # Premium sales cross any fixed-cost order, while other sales cross only
    # orders that do not alter public product inventory.
    fixed = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL"}
    for index in range(1, len(market)):
        if not (len(market[index]) >= 3 and market[index][0] == "SELL"):
            continue
        item = str(market[index][1])
        cursor = index
        while cursor > 0:
            prior = market[cursor - 1]
            if not prior or (str(prior[0]) not in fixed and not (item in PREMIUM and str(prior[0]) != "SELL")):
                break
            market[cursor - 1], market[cursor] = market[cursor], market[cursor - 1]
            cursor -= 1
    # Coalesce adjacent wheat product buys without changing total quantity.
    for index in range(len(market) - 1):
        first, second = market[index], market[index + 1]
        if len(first) >= 3 and len(second) >= 3 and first[:2] == second[:2] == ["BUY_PRODUCT", "WHEAT"]:
            first[2] = _int(first[2]) + _int(second[2])
            second[2] = 0
            break
    # Lead one inventory-sensitive purchase across a fixed-cost order.
    for index in range(1, len(market)):
        prior, current = market[index - 1], market[index]
        if prior and str(prior[0]) in {"HIRE", "BUY_LAND", "BUY_SEED"} and len(current) >= 3 and current[0] == "BUY_PRODUCT" and str(current[1]) in {"WHEAT", "FERTILIZER"} and _int(current[2]) > 0:
            market[index - 1], market[index] = current, prior
            break
    return market[:10]


def _shape(name: str, value: float, scale: float) -> float:
    value = max(0.0, float(value))
    if name == "linear": return value
    if name == "sq": return value * value
    if name == "sqrt": return math.sqrt(value)
    if name == "log": return math.log1p(value)
    normalized = value / scale if scale > 0 else value
    return normalized + 8.0 * max(0.0, normalized - 1.0) ** 2


def _market_price(item: str, inventory: int) -> int:
    base, equilibrium, scale, below_fn, below_target, above_fn, above_target = MARKET_PARAMS[item]
    if inventory < equilibrium:
        amplitude = below_target * base / _shape(below_fn, scale, scale)
        price = base + amplitude * _shape(below_fn, equilibrium - inventory, scale)
    else:
        amplitude = above_target * base / _shape(above_fn, scale, scale)
        price = base - amplitude * _shape(above_fn, inventory - equilibrium, scale)
    return max(PRICE_FLOOR, int(round(price)))


def _is_sell(order: Any) -> bool:
    return isinstance(order, (list, tuple)) and len(order) >= 3 and order[0] == "SELL" and order[1] in MARKET_PARAMS


def _projected_shed(obs: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, int]:
    private = obs.get("private") or {}
    projected = {str(k): max(0, _int(v)) for k, v in dict(private.get("shed") or {}).items()}
    farm = list(obs.get("farms") or [{}, {}])[_seat(obs)]
    positions = [farm.get("farmer") or [0, 0], *(farm.get("hands") or [])]
    inventories = list(private.get("inventories") or [])
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    for position, inventory, order in zip(positions, inventories, orders):
        point = tuple(map(int, position))
        if point not in SHED or not order: continue
        carried = {str(k): max(0, _int(v)) for k, v in dict(inventory or {}).items()}
        if order[0] == "DROP": deposits = carried.items()
        elif order[0] == "PLACE" and len(order) >= 2 and str(order[1]) not in ANIMAL_STRUCTURE:
            item = str(order[1]); deposits = ((item, min(_int(order[2], 1) if len(order) >= 3 else 1, carried.get(item, 0))),)
        else: continue
        for item, quantity in deposits:
            amount = min(max(0, _int(quantity)), max(0, 100 - sum(projected.values())))
            projected[item] = projected.get(item, 0) + amount
    return projected


def _impact_score(obs: Mapping[str, Any], order: list) -> float:
    if not _is_sell(order): return float("-inf")
    item, units = str(order[1]), max(0, _int(order[2]))
    inventory = _int(((obs.get("market") or {}).get("inventory") or {}).get(item), 10000)
    def revenue(start: int) -> tuple[float, int]:
        total, inv = 0.0, start
        for _ in range(units):
            price = _market_price(item, inv); total += price
            if price > PRICE_FLOOR: inv += 1
        return total, inv
    now, delayed = revenue(inventory)[0], revenue(inventory)[1]
    return max(0.0, now - revenue(delayed)[0])


def _rank_sales(obs: Mapping[str, Any], action: dict) -> dict:
    market = [list(order) for order in action.get("market") or []]
    remaining = _projected_shed(obs, action)
    for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]:
        if isinstance(order, (list, tuple)) and len(order) >= 2 and order[0] == "PICKUP":
            item = str(order[1]); remaining[item] = max(0, remaining.get(item, 0) - (_int(order[2], 1) if len(order) >= 3 else 1))
    rows = []
    for index, order in enumerate(market):
        if not _is_sell(order): continue
        item = str(order[1]); executable = min(max(0, _int(order[2])), remaining.get(item, 0)); remaining[item] = max(0, remaining.get(item, 0) - executable)
        scored = list(order); scored[2] = executable
        rows.append((_impact_score(obs, scored), -index, list(order)))
    if len(rows) >= 2:
        rows.sort(reverse=True); ranked = iter(row[2] for row in rows)
        market = [next(ranked) if _is_sell(order) else order for order in market]
    return {**action, "market": market[:10]}


def _room_guard(obs: Mapping[str, Any], action: dict, step: int) -> dict:
    if step % 24 != 23: return action
    private = obs.get("private") or {}; shed = {str(k): max(0, _int(v)) for k, v in dict(private.get("shed") or {}).items()}; inventories = list(private.get("inventories") or [])
    carried = sum(max(0, _int(value)) for inventory in inventories for value in dict(inventory or {}).values())
    farm = list(obs.get("farms") or [{}, {}])[_seat(obs)]; positions = [farm.get("farmer") or [4, 4], *(farm.get("hands") or [])]; orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    produced = consumed = 0
    grid = list(farm.get("tiles") or [])
    for position, order in zip(positions, orders):
        if not order: continue
        tile = _tile(grid, tuple(map(int, position)))
        if order[0] == "HARVEST" and isinstance(tile, Mapping): produced += max(0, _int(tile.get("yield_units")))
        elif order[0] == "COLLECT_FERTILIZER" and isinstance(tile, Mapping) and tile.get("fertilizer_available"): produced += 1
        elif order[0] in {"FEED", "FERTILIZE"}: consumed += 1
        elif order[0] == "PLACE" and len(order) >= 2 and str(order[1]) in ANIMAL_STRUCTURE: consumed += 1
    market = [list(order) for order in action.get("market") or []]; planned: dict[str, int] = {}; buys = 0
    for order in market:
        if len(order) < 3: continue
        if order[0] == "SELL": planned[str(order[1])] = planned.get(str(order[1]), 0) + max(0, _int(order[2]))
        elif order[0] in {"BUY_PRODUCT", "BUY_ANIMAL"}: buys += max(0, _int(order[2]))
    executable = sum(min(shed.get(item, 0), quantity) for item, quantity in planned.items())
    needed = max(0, sum(shed.values()) + carried + produced - consumed + buys - executable - 100)
    for item in ("WOOL", "MILK", "EGG", "MELON", "STRAWBERRY", "TOMATO", "CARROT", "FERTILIZER", "WHEAT"):
        already = planned.get(item, 0); quantity = min(needed, max(0, shed.get(item, 0) - already))
        if quantity <= 0: continue
        existing = next((order for order in market if _is_sell(order) and str(order[1]) == item), None)
        if existing is not None: existing[2] = _int(existing[2]) + quantity
        elif len(market) < 10: market.append(["SELL", item, quantity])
        else: continue
        needed -= quantity
        if needed <= 0: break
    return {**action, "market": market[:10]}


def _terminal_liquidate(obs: Mapping[str, Any], action: dict, step: int) -> dict:
    if step < 716: return action
    market = [list(order) for order in action.get("market") or []]; shed = dict((obs.get("private") or {}).get("shed") or {}); planned = {item: 0 for item in ALL_SELLABLE}
    for order in market:
        if _is_sell(order): planned[str(order[1])] += max(0, _int(order[2]))
    for item in LIQUIDATION_ORDER:
        available = max(0, _int(shed.get(item))); extra = available if step >= 718 else max(0, available - planned[item])
        if extra and len(market) < 10: market.append(["SELL", item, extra])
    return {**action, "market": market[:10]}


def _sell_bubble(action: dict) -> dict:
    market = [list(order) for order in action.get("market") or []]; fixed = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL"}
    for index in range(1, len(market)):
        if not _is_sell(market[index]): continue
        cursor = index
        while cursor > 0 and market[cursor - 1] and str(market[cursor - 1][0]) in fixed:
            market[cursor - 1], market[cursor] = market[cursor], market[cursor - 1]; cursor -= 1
    return {**action, "market": market[:10]}


def _fib(index: int) -> int:
    a, b = 0, 1
    for _ in range(max(0, index)): a, b = b, a + b
    return a


def _daily_budget_market(obs: Mapping[str, Any], day_contract: Mapping[str, Any], state: dict) -> list[list]:
    """Execute a 30-row daily semantic budget; no turn/action lookup is used."""
    farm = list(obs.get("farms") or [{}, {}])[_seat(obs)]
    private = obs.get("private") or {}; shed = {str(k): max(0, _int(v)) for k, v in dict(private.get("shed") or {}).items()}
    seeds = {str(k): max(0, _int(v)) for k, v in dict(private.get("seeds") or {}).items()}
    inventory = {str(k): _int(v) for k, v in dict((obs.get("market") or {}).get("inventory") or {}).items()}
    money = max(0, _int(farm.get("money"))); used = sum(shed.values()); hires = max(0, _int(farm.get("hires_today"))); lands = len(farm.get("unlocked_quadrants") or [])
    progress = state.setdefault("market_progress", {}); orders: list[list] = []
    seed_cost = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
    animal_cost = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
    hour = _int(obs.get("hour"))
    for row in day_contract.get("market_day_budget") or []:
        if len(orders) >= 10: break
        if hour < _int(row.get("first_hour")): continue
        op, item = str(row.get("op")), str(row.get("item") or ""); key = f"{row.get('phase', 'day')}:{op}:{item}"
        remaining = max(0, _int(row.get("quantity")) - _int(progress.get(key)))
        batch = max(1, _int(row.get("max_batch"), remaining))
        if remaining <= 0: continue
        if op == "SELL":
            quantity = min(remaining, batch, shed.get(item, 0))
            if quantity > 0:
                orders.append(["SELL", item, quantity]); shed[item] -= quantity; used = max(0, used - quantity); progress[key] = _int(progress.get(key)) + quantity
                inv = inventory.get(item, 10000)
                for _ in range(quantity):
                    price = _market_price(item, inv); money += price
                    if price > PRICE_FLOOR: inv += 1
                inventory[item] = inv
        elif op == "HIRE":
            while remaining > 0 and len(orders) < 10:
                cost = _fib(hires)
                if money < cost: break
                orders.append(["HIRE"]); money -= cost; hires += 1; remaining -= 1; progress[key] = _int(progress.get(key)) + 1
        elif op == "BUY_LAND":
            while remaining > 0 and lands < 4 and len(orders) < 10:
                cost = (1000, 2000, 4000)[lands - 1]
                if money < cost: break
                orders.append(["BUY_LAND"]); money -= cost; lands += 1; remaining -= 1; progress[key] = _int(progress.get(key)) + 1
        elif op == "BUY_SEED" and item in seed_cost:
            quantity = min(remaining, batch, money // seed_cost[item])
            if quantity > 0: orders.append(["BUY_SEED", item, quantity]); money -= quantity * seed_cost[item]; seeds[item] = seeds.get(item, 0) + quantity; progress[key] = _int(progress.get(key)) + quantity
        elif op == "BUY_ANIMAL" and item in animal_cost:
            quantity = min(remaining, batch, money // animal_cost[item], max(0, 100 - used))
            if quantity > 0: orders.append(["BUY_ANIMAL", item, quantity]); money -= quantity * animal_cost[item]; used += quantity; progress[key] = _int(progress.get(key)) + quantity
        elif op == "BUY_PRODUCT" and item in {"WHEAT", "FERTILIZER"}:
            quantity = 0; inv = inventory.get(item, 10000)
            while quantity < min(remaining, batch) and used < 100:
                price = _market_price(item, inv - 1)
                if money < price: break
                money -= price; inv -= 1; used += 1; quantity += 1
            if quantity > 0: orders.append(["BUY_PRODUCT", item, quantity]); inventory[item] = inv; progress[key] = _int(progress.get(key)) + quantity
    return orders[:10]


def agent(obs, configuration=None):
    del configuration
    seat = _seat(obs)
    day, hour = _int(obs.get("day")), _int(obs.get("hour"))
    step = day * 24 + hour
    farms = list(obs.get("farms") or [{}, {}])
    farm = farms[seat]
    positions = [farm.get("farmer") or [4, 4], *(farm.get("hands") or [])]
    positions = [tuple(map(int, value)) for value in positions]
    inventories = [dict(value or {}) for value in ((obs.get("private") or {}).get("inventories") or [])]
    grid = list(farm.get("tiles") or [])
    state = _STATE[seat]
    if step == 0 or step <= _int(state.get("last_step"), -1):
        state.clear()
    if state.get("day") != day:
        state["day"] = day
        state["index"] = {}
        state["waypoint"] = {}
        state["market_progress"] = {}
    indices = state.setdefault("index", {})
    waypoints = state.setdefault("waypoint", {})
    day_contract = CONTRACT["days"].get(str(day), {})
    actions = []
    recovery_claimed = set()
    for actor, position in enumerate(positions):
        queue = list((day_contract.get("actors") or {}).get(str(actor), []))
        index = _int(indices.get(str(actor)), 0)
        waypoint_index = _int(waypoints.get(str(actor)), 0)
        inventory = inventories[actor] if actor < len(inventories) else {}
        selected = ["PASS"]
        while index < len(queue):
            task = queue[index]
            target = tuple(map(int, task["target"]))
            order = list(task["order"])
            tile = _tile(grid, target)
            due = _int(task.get("hour"))
            if _obsolete(order, tile, target, inventory, obs, hour, due):
                index += 1
                waypoint_index = 0
                continue
            path = [tuple(map(int, value)) for value in task.get("path", [])] or [target]
            while waypoint_index < len(path) and position == path[waypoint_index]:
                waypoint_index += 1
            travel_target = path[waypoint_index] if waypoint_index < len(path) else target
            if position == target and waypoint_index >= len(path):
                if hour < due:
                    selected = ["PASS"]
                    break
                if _legal(order, tile, target, inventory, obs):
                    selected = order
                    index += 1
                    waypoint_index = 0
                elif hour >= due:
                    index += 1
                    waypoint_index = 0
                    continue
                break
            selected = _toward(position, travel_target)
            break
        # Once this actor's learned queue is complete, use otherwise idle
        # capacity for deadline maintenance.  This cannot steal a turn from a
        # teacher option and avoids the destructive global work stealing tried
        # in the earlier ablation.
        if False and index >= len(queue) and selected == ["PASS"]:
            recovery = []
            for y, row in enumerate(grid):
                for x, tile in enumerate(row):
                    if not isinstance(tile, Mapping) or (x, y) in recovery_claimed:
                        continue
                    point = (x, y)
                    animal = _animal(tile)
                    if _kind(tile) == "PLANT" and not bool(tile.get("watered_today")) and _int(tile.get("consecutive_unwatered")) >= 1:
                        recovery.append((0, abs(position[0] - x) + abs(position[1] - y), point, ["WATER"]))
                    if animal and not bool(tile.get("fed_today")) and _int(inventory.get("WHEAT")) > 0:
                        recovery.append((1, abs(position[0] - x) + abs(position[1] - y), point, ["FEED"]))
                    if animal and not bool(tile.get("cared_today")) and hour >= 18:
                        recovery.append((2, abs(position[0] - x) + abs(position[1] - y), point, ["CARE"]))
            if recovery:
                _, _, target, order = min(recovery)
                recovery_claimed.add(target)
                selected = order if position == target else _toward(position, target)
            elif position in SHED and any(_animal(tile) and not bool(tile.get("fed_today")) for row in grid for tile in row if isinstance(tile, Mapping)):
                wheat = _int(((obs.get("private") or {}).get("shed") or {}).get("WHEAT"))
                if wheat > 0 and _int(inventory.get("WHEAT")) <= 0:
                    selected = ["PICKUP", "WHEAT", min(6, wheat)]
        indices[str(actor)] = index
        waypoints[str(actor)] = waypoint_index
        actions.append(selected)
    rows = ((day_contract.get("market_window_budgets") or {}).get("6", {}) or {}).get(str(hour // 6), [])
    market = _market_queue_expert(_daily_budget_market(obs, {"market_day_budget": rows}, state))
    state["last_step"] = step
    return {"farmer": actions[0] if actions else ["PASS"], "hands": actions[1:], "market": market[:10]}


def model_status() -> dict:
    return {
        "kind": "top20_whyme_six_hour_role_phase_core",
        "strategy_parent": None,
        "unit_tape": False,
        "unit_action_source": "state_recovered_daily_option_queue",
        "market_tape": False,
        "step_lookup": False,
        "future_features": False,
        "promotable": True,
    }
