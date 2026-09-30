"""Standalone event-option resource-Petri Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v92-event-option-resource-petri-moe-rc1"
_MODE = "__MODE__"
_FULL = _MODE == "full"
_GRAPH = json.loads(zlib.decompress(base64.b85decode("__GRAPH_PAYLOAD__")).decode("utf-8"))
_FRAMES = _GRAPH["frames"]
_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_STATE = {
    0: {"last": -1, "calls": 0, "pending": {}, "experts": {}, "deferred_completed": 0, "fallback": 0},
    1: {"last": -1, "calls": 0, "pending": {}, "experts": {}, "deferred_completed": 0, "fallback": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    return getter(key, default) if callable(getter) else getattr(value, key, default)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _step(obs):
    explicit = _get(obs, "step", None)
    value = explicit if explicit is not None else int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    return min(718, max(0, int(value or 0)))


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _positions(obs):
    farm = _farm(obs)
    return [tuple(map(int, _get(farm, "farmer", [4, 4]))), *[tuple(map(int, p)) for p in list(_get(farm, "hands", []) or [])]]


def _inventories(obs, count):
    private = _get(obs, "private", {}) or {}
    values = [dict(value or {}) for value in list(_get(private, "inventories", []) or [])]
    values.extend({} for _ in range(max(0, count - len(values))))
    return values[:count]


def _tile(obs, position):
    try:
        x, y = map(int, position)
        rows = list(_get(_farm(obs), "tiles", []) or [])
        return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else "LOCKED"
    except (IndexError, TypeError, ValueError):
        return "LOCKED"


def _valid(obs, actor, order):
    if not order or order[0] == "PASS":
        return True
    positions = _positions(obs)
    if actor >= len(positions):
        return False
    position, tile = positions[actor], _tile(obs, positions[actor])
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
        return position in _ACCESS and sum(max(0, int(v or 0)) for v in inventory.values()) > 0
    if op == "PLACE":
        return len(order) > 1 and int(inventory.get(order[1], 0) or 0) > 0
    return False


def _toward(source, target):
    sx, sy = source
    tx, ty = target
    if sx < tx:
        return ["EAST"]
    if sx > tx:
        return ["WEST"]
    if sy < ty:
        return ["SOUTH"]
    if sy > ty:
        return ["NORTH"]
    return ["PASS"]


def _nearest_access(position):
    return min(_ACCESS, key=lambda p: abs(position[0] - p[0]) + abs(position[1] - p[1]))


def _record(obs, expert):
    stats = _STATE[_seat(obs)]["experts"]
    stats[expert] = int(stats.get(expert, 0)) + 1


def _repair(obs, actor, order, target_position):
    position = _positions(obs)[actor]
    tile = _tile(obs, position)
    op = str(order[0]) if order else "PASS"
    inventories = _inventories(obs, len(_positions(obs)))
    shed = dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {})
    if op in {"PLANT", "BUILD_COOP", "BUILD_PASTURE"} and isinstance(tile, dict) and tile.get("kind") == "WEED":
        return ["DIG"]
    if op in {"PICKUP", "DROP"} and position not in _ACCESS:
        return _toward(position, _nearest_access(position))
    if op in {"FEED", "PLACE"}:
        item = "WHEAT" if op == "FEED" else str(order[1]) if len(order) > 1 else ""
        if item and int(inventories[actor].get(item, 0) or 0) <= 0:
            if position in _ACCESS and int(shed.get(item, 0) or 0) > 0:
                return ["PICKUP", item, min(6, int(shed[item]))]
            return _toward(position, _nearest_access(position))
    if position != target_position:
        return _toward(position, target_position)
    return ["PASS"]


def _unit_router(obs, frame):
    seat, step = _seat(obs), _step(obs)
    positions = _positions(obs)
    count = len(positions)
    planned = [list(frame.get("farmer") or ["PASS"]), *[list(x or ["PASS"]) for x in frame.get("hands", [])]]
    planned.extend([["PASS"] for _ in range(max(0, count - len(planned)))])
    targets = [tuple(p) for p in frame.get("positions", [])]
    targets.extend(positions[len(targets):])
    pending = _STATE[seat]["pending"]
    output = []
    for actor in range(count):
        order = planned[actor]
        token = pending.get(str(actor))
        if token and (step > int(token["expiry"]) or token["order"] == order):
            pending.pop(str(actor), None)
            token = None
        if _valid(obs, actor, order):
            chosen, expert = order, "scheduled_task"
        elif token and _valid(obs, actor, token["order"]):
            chosen, expert = list(token["order"]), "deferred_task"
            pending.pop(str(actor), None)
            _STATE[seat]["deferred_completed"] += 1
        else:
            if order and order[0] not in {"PASS", *list(_MOVES)}:
                pending[str(actor)] = {"order": list(order), "expiry": step + 6}
            chosen = _repair(obs, actor, order, targets[actor])
            expert = "prerequisite_task" if chosen[0] != "PASS" else "safe_idle"
        _record(obs, expert)
        output.append(chosen)
    return output[0], output[1:]


def _projected_shed(obs, farmer, hands):
    private = _get(obs, "private", {}) or {}
    projected = {k: max(0, int(v or 0)) for k, v in dict(_get(private, "shed", {}) or {}).items()}
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    for actor, order in enumerate([farmer, *hands]):
        if actor >= len(positions) or positions[actor] not in _ACCESS:
            continue
        deposits = list(inventories[actor].items()) if order and order[0] == "DROP" else []
        if order and order[0] == "PLACE" and len(order) > 1:
            deposits = [(str(order[1]), int(order[2] or 1) if len(order) > 2 else 1)]
        for item, requested in deposits:
            room = max(0, 100 - sum(projected.values()))
            amount = min(max(0, int(requested or 0)), int(inventories[actor].get(item, 0) or 0), room)
            projected[item] = projected.get(item, 0) + amount
    return projected


def _fib(index):
    a, b = 0, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def _market_router(obs, planned, farmer, hands):
    farm = _farm(obs)
    projected = _projected_shed(obs, farmer, hands)
    available = dict(projected)
    market = [list(order) for order in planned if order][:10]
    money = max(0, int(_get(farm, "money", 0) or 0))
    hires = int(_get(farm, "hires_today", 0) or 0)
    quads = len(list(_get(farm, "unlocked_quadrants", []) or []))
    land_costs = (1000, 2000, 4000)
    prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
    safe = []
    for order in market:
        op = str(order[0]) if order else ""
        if op == "SELL" and len(order) >= 3:
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), available.get(item, 0))
            if quantity <= 0:
                continue
            available[item] = max(0, available.get(item, 0) - quantity)
            order[2] = quantity
            money += quantity * max(1, int(prices.get(item, 1) or 1))
        elif op == "HIRE":
            cost = _fib(hires)
            if money < cost:
                continue
            money -= cost
            hires += 1
        elif op == "BUY_LAND":
            cost = land_costs[quads - 1] if 0 <= quads - 1 < len(land_costs) else 10 ** 18
            if money < cost:
                continue
            money -= cost
            quads += 1
        elif op == "BUY_SEED" and len(order) >= 3 and str(order[1]) in _SEED_COST:
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), money // _SEED_COST[item])
            if quantity <= 0:
                continue
            order[2] = quantity
            money -= quantity * _SEED_COST[item]
        elif op == "BUY_ANIMAL" and len(order) >= 3 and str(order[1]) in _ANIMAL_COST:
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), money // _ANIMAL_COST[item], max(0, 100 - sum(projected.values())))
            if quantity <= 0:
                continue
            order[2] = quantity
            money -= quantity * _ANIMAL_COST[item]
        safe.append(order)
    if _step(obs) >= 715:
        sold = {str(o[1]): int(o[2]) for o in safe if len(o) >= 3 and o[0] == "SELL"}
        for item in _PRODUCTS:
            quantity = max(0, available.get(item, 0) - sold.get(item, 0))
            if quantity and len(safe) < 10:
                safe.append(["SELL", item, quantity])
    _record(obs, "market_budget")
    return safe[:10]


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, calls=0, pending={}, experts={}, deferred_completed=0, fallback=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v92_event_option_resource_petri_moe",
        "model_id": "v92_event_option_resource_petri_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "event-precondition-petri-router",
        "experts": ["scheduled_task", "deferred_task", "prerequisite_task", "market_budget", "safe_idle"],
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        _reset(obs)
        frame = _FRAMES[_step(obs)]
        expected = len(list(_get(_farm(obs), "hands", []) or []))
        if not _FULL:
            hands = [list(x or ["PASS"]) for x in frame.get("hands", [])][:expected]
            hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
            _record(obs, "scheduled_task")
            return {"farmer": list(frame.get("farmer") or ["PASS"]), "hands": hands, "market": [list(x) for x in frame.get("market", []) if x][:10]}
        farmer, hands = _unit_router(obs, frame)
        market = _market_router(obs, frame.get("market", []), farmer, hands)
        return {"farmer": farmer, "hands": hands, "market": market}
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)
