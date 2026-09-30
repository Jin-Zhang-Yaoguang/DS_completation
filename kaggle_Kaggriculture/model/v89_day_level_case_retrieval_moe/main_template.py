"""Standalone day-level case-retrieval Option Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v89-day-level-case-retrieval-moe-rc1"
_MODE = "__MODE__"
_FULL = _MODE == "full"
_LIBRARY = json.loads(zlib.decompress(base64.b85decode("__LIBRARY_PAYLOAD__")).decode("utf-8"))
_CASES = _LIBRARY["cases"]
_REFERENCE_ID = str(_LIBRARY["reference_episode_id"])
_CASE_BY_ID = {str(case["episode_id"]): case for case in _CASES}
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_ASSETS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "GOOSE", "COW", "SHEEP", "PASTURE", "COOP", "WEED")
_STATE = {
    0: {"last": -1, "day": -1, "case": None, "calls": 0, "selections": {}, "switches": 0, "exact_regime": 0, "fallback": 0},
    1: {"last": -1, "day": -1, "case": None, "calls": 0, "selections": {}, "switches": 0, "exact_regime": 0, "fallback": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs):
    return min(718, max(0, int(_get(obs, "step", 0) or 0)))


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _copy_action(action):
    action = copy.deepcopy(action or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or []) if order],
    }


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


def _tile_counts(farm):
    counts = {key: 0 for key in _ASSETS}
    for row in list(_get(farm, "tiles", []) or []):
        for tile in row if isinstance(row, list) else []:
            if not isinstance(tile, dict):
                continue
            value = str(tile.get("crop") or tile.get("animal") or tile.get("kind") or "").upper()
            if value in counts:
                counts[value] += 1
    return counts


def _feature(obs):
    farm = _farm(obs)
    private = _get(obs, "private", {}) or {}
    shops = [str(value) for value in list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])]
    farmer = list(_get(farm, "farmer", [4, 4]) or [4, 4])
    return {
        "shops": shops,
        "money": int(_get(farm, "money", 0) or 0),
        "quadrants": len(list(_get(farm, "unlocked_quadrants", []) or [])),
        "farmer": [int(farmer[0]), int(farmer[1])],
        "tiles": _tile_counts(farm),
        "seeds": {key: int(value or 0) for key, value in dict(_get(private, "seeds", {}) or {}).items()},
        "shed": {key: int(value or 0) for key, value in dict(_get(private, "shed", {}) or {}).items()},
    }


def _shop_distance(left, right):
    width = max(len(left), len(right))
    return sum((left[index] if index < len(left) else None) != (right[index] if index < len(right) else None) for index in range(width))


def _state_distance(current, prototype):
    distance = 100.0 * abs(int(current["quadrants"]) - int(prototype["quadrants"]))
    distance += 5.0 * (abs(int(current["farmer"][0]) - int(prototype["farmer"][0])) + abs(int(current["farmer"][1]) - int(prototype["farmer"][1])))
    distance += 10.0 * sum(abs(int(current["tiles"].get(key, 0)) - int(prototype["tiles"].get(key, 0))) for key in _ASSETS)
    distance += sum(abs(int(current["seeds"].get(key, 0)) - int(prototype["seeds"].get(key, 0))) for key in current["seeds"])
    distance += 0.2 * sum(abs(int(current["shed"].get(key, 0)) - int(prototype["shed"].get(key, 0))) for key in current["shed"])
    distance += abs(int(current["money"]) - int(prototype["money"])) / 1000.0
    return distance


def _select_case(obs, day):
    if not _FULL:
        return _REFERENCE_ID, True
    current = _feature(obs)
    candidates = []
    for case in _CASES:
        prototype = case["days"][day]
        candidates.append((_shop_distance(current["shops"], prototype["shops"]), _state_distance(current, prototype), int(case["episode_id"])))
    best_shop = min(row[0] for row in candidates)
    _, _, episode_id = min(row for row in candidates if row[0] == best_shop)
    return str(episode_id), best_shop == 0


def _reset_and_route(obs):
    seat, step = _seat(obs), _step(obs)
    day = min(29, step // 24)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, day=-1, case=None, calls=0, selections={}, switches=0, exact_regime=0, fallback=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1
    if int(state.get("day", -1)) != day or state.get("case") is None:
        previous = state.get("case")
        selected, exact = _select_case(obs, day)
        state["case"] = selected
        state["day"] = day
        state["switches"] += int(previous is not None and previous != selected)
        state["exact_regime"] += int(exact)
        choices = state["selections"]
        choices[selected] = int(choices.get(selected, 0)) + 1
    return str(state["case"])


def _align(action, obs):
    action = _copy_action(action)
    expected = len(list(_get(_farm(obs), "hands", []) or []))
    action["hands"].extend([["PASS"] for _ in range(max(0, expected - len(action["hands"])))])
    action["hands"] = action["hands"][:expected]
    action["market"] = action["market"][:10]
    return action


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


def _legalize(action, obs):
    action = _align(action, obs)
    orders = [action["farmer"], *action["hands"]]
    for actor, order in enumerate(list(orders)):
        if not _valid(obs, actor, order):
            orders[actor] = ["PASS"]
    remaining = {key: max(0, int(value or 0)) for key, value in dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {}).items()}
    for actor, order in enumerate(list(orders)):
        if len(order) >= 3 and order[0] == "PICKUP":
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - quantity)
            orders[actor] = ["PICKUP", item, quantity] if quantity > 0 else ["PASS"]
    action["farmer"], action["hands"] = orders[0], orders[1:]
    return action


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v89_day_level_case_retrieval_moe",
        "model_id": "v89_day_level_case_retrieval_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": ["shop-sequence-regime-router", "state-nearest-neighbour-router"],
        "option_horizon": 24,
        "case_count": len(_CASES),
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        case_id = _reset_and_route(obs)
        action = _CASE_BY_ID[case_id]["actions"][_step(obs)]
        return _legalize(action, obs)
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)

