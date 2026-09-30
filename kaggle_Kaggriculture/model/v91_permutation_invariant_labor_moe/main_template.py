"""Standalone permutation-invariant labor matching Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v91-permutation-invariant-labor-moe-rc1"
_MODE = "__MODE__"
_FULL = _MODE == "full"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("__REFERENCE_PAYLOAD__")).decode("utf-8"))
_ACTIONS = _REFERENCE["actions"]
_TARGETS = _REFERENCE["targets"]
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_STATE = {
    0: {"last": -1, "calls": 0, "reassigned_calls": 0, "reassigned_pairs": 0, "experts": {}, "fallback": 0},
    1: {"last": -1, "calls": 0, "reassigned_calls": 0, "reassigned_pairs": 0, "experts": {}, "fallback": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs):
    explicit = _get(obs, "step", None)
    value = explicit if explicit is not None else int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    return min(718, max(0, int(value or 0)))


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _positions(obs):
    farm = _farm(obs)
    return [tuple(map(int, _get(farm, "farmer", [4, 4]))), *[
        tuple(map(int, value)) for value in list(_get(farm, "hands", []) or [])
    ]]


def _inventories(obs, count):
    private = _get(obs, "private", {}) or {}
    values = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    values.extend({} for _ in range(max(0, count - len(values))))
    return values[:count]


def _tile(obs, position):
    try:
        x, y = map(int, position)
        rows = list(_get(_farm(obs), "tiles", []) or [])
        if 0 <= y < len(rows) and 0 <= x < len(rows[y]):
            return rows[y][x]
    except (IndexError, TypeError, ValueError):
        pass
    return "LOCKED"


def _valid(obs, actor, order):
    if not order or order[0] == "PASS":
        return True
    positions = _positions(obs)
    if actor >= len(positions):
        return False
    position = positions[actor]
    tile = _tile(obs, position)
    inventory = _inventories(obs, len(positions))[actor]
    private = _get(obs, "private", {}) or {}
    shed = dict(_get(private, "shed", {}) or {})
    seeds = dict(_get(private, "seeds", {}) or {})
    op = str(order[0])
    if op in _MOVES:
        dx, dy = _MOVES[op]
        rows = list(_get(_farm(obs), "tiles", []) or [])
        x, y = position[0] + dx, position[1] + dy
        return 0 <= y < len(rows) and 0 <= x < len(rows[y])
    if op == "DIG":
        return tile != "LOCKED" and not (isinstance(tile, dict) and tile.get("animal"))
    if op == "PLANT":
        return tile is None and len(order) > 1 and int(seeds.get(order[1], 0) or 0) > 0
    if op == "WATER":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
    if op == "HARVEST":
        return isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    if op == "FERTILIZE":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inventory.get("FERTILIZER", 0) or 0) > 0
    if op in {"BUILD_COOP", "BUILD_PASTURE"}:
        return tile is None
    if op == "FEED":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inventory.get("WHEAT", 0) or 0) > 0
    if op == "CARE":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
    if op == "COLLECT_FERTILIZER":
        return isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
    if op == "PICKUP":
        return position in _ACCESS and len(order) > 2 and int(shed.get(order[1], 0) or 0) > 0
    if op == "DROP":
        return position in _ACCESS and sum(max(0, int(value or 0)) for value in inventory.values()) > 0
    if op == "PLACE":
        return len(order) > 1 and int(inventory.get(order[1], 0) or 0) > 0
    return False


def _task_cost(obs, actor, slot, order, target):
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    position = positions[actor]
    target_positions = [tuple(value) for value in target.get("positions", [])]
    target_inventories = list(target.get("inventories", []) or [])
    target_position = target_positions[slot] if slot < len(target_positions) else position
    target_inventory = target_inventories[slot] if slot < len(target_inventories) else {}
    cost = 10 * (abs(position[0] - target_position[0]) + abs(position[1] - target_position[1]))
    cost += 2 * sum(abs(int(inventories[actor].get(item, 0) or 0) - int(target_inventory.get(item, 0) or 0)) for item in _ITEMS)
    cost += 1000 * int(not _valid(obs, actor, order))
    return cost


def _match(obs, planned, target):
    count = len(_positions(obs))
    hands = count - 1
    planned_hands = list(planned.get("hands", []) or [])[:hands]
    planned_hands.extend([["PASS"] for _ in range(max(0, hands - len(planned_hands)))])
    if not _FULL or hands <= 1:
        return planned_hands, 0
    pairs = []
    for actor in range(1, count):
        for slot, order in enumerate(planned_hands, 1):
            pairs.append((_task_cost(obs, actor, slot, order, target), actor, slot))
    pairs.sort()
    actor_used, slot_used, assignment = set(), set(), {}
    for _, actor, slot in pairs:
        if actor in actor_used or slot in slot_used:
            continue
        actor_used.add(actor)
        slot_used.add(slot)
        assignment[actor] = slot
    orders = [["PASS"] for _ in range(hands)]
    changed = 0
    for actor in range(1, count):
        slot = assignment.get(actor, actor)
        orders[actor - 1] = list(planned_hands[slot - 1])
        changed += int(slot != actor)
    return orders, changed


def _execute(obs, planned, target):
    seat = _seat(obs)
    hand_orders, changed = _match(obs, planned, target)
    orders = [list(planned.get("farmer") or ["PASS"]), *hand_orders]
    private = _get(obs, "private", {}) or {}
    seeds = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "seeds", {}) or {}).items()}
    shed = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    safe = []
    for actor, order in enumerate(orders):
        expert = "matched_task"
        if not _valid(obs, actor, order):
            order, expert = ["PASS"], "safe_idle"
        elif len(order) >= 2 and order[0] == "PLANT":
            item = str(order[1])
            if seeds.get(item, 0) <= 0:
                order, expert = ["PASS"], "safe_idle"
            else:
                seeds[item] -= 1
        elif len(order) >= 3 and order[0] == "PICKUP":
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), shed.get(item, 0))
            shed[item] = max(0, shed.get(item, 0) - quantity)
            order = ["PICKUP", item, quantity] if quantity > 0 else ["PASS"]
            expert = "supply_task" if quantity > 0 else "safe_idle"
        stats = _STATE[seat]["experts"]
        stats[expert] = int(stats.get(expert, 0)) + 1
        safe.append(order)
    if changed:
        _STATE[seat]["reassigned_calls"] += 1
        _STATE[seat]["reassigned_pairs"] += changed
    return {
        "farmer": safe[0],
        "hands": safe[1:],
        "market": [list(order) for order in (planned.get("market", []) or []) if order][:10],
    }


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, calls=0, reassigned_calls=0, reassigned_pairs=0, experts={}, fallback=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v91_permutation_invariant_labor_moe",
        "model_id": "v91_permutation_invariant_labor_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "worker-task-min-cost-matching",
        "experts": ["matched_task", "supply_task", "safe_idle"],
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        _reset(obs)
        step = _step(obs)
        return _execute(obs, copy.deepcopy(_ACTIONS[step]), _TARGETS[step])
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)

