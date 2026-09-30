"""Standalone factorized shallow-tree imitation Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v90-factorized-shallow-tree-moe-rc1"
_MODE = "__MODE__"
_FULL = _MODE == "full"
_MODEL = json.loads(zlib.decompress(base64.b85decode("__MODEL_PAYLOAD__")).decode("utf-8"))
_TREES = _MODEL["trees"]
_ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_SEEDS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
_SHOPS = ("BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE")
_ASSETS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "GOOSE", "COW", "SHEEP", "PASTURE", "COOP", "WEED")
_TILE_TYPES = ("EMPTY", "LOCKED", "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "GOOSE", "COW", "SHEEP", "PASTURE", "COOP", "WEED", "OTHER")
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_STATE = {
    0: {"last": -1, "calls": 0, "regimes": {}, "unit_drops": 0, "market_orders": 0, "fallback": 0},
    1: {"last": -1, "calls": 0, "regimes": {}, "unit_drops": 0, "market_orders": 0, "fallback": 0},
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


def _tile_type(tile):
    if tile is None:
        return "EMPTY"
    if tile == "LOCKED":
        return "LOCKED"
    if isinstance(tile, dict):
        value = str(tile.get("crop") or tile.get("animal") or tile.get("kind") or "OTHER").upper()
        return value if value in _TILE_TYPES else "OTHER"
    return "OTHER"


def _asset_counts(farm):
    counts = {key: 0 for key in _ASSETS}
    for row in list(_get(farm, "tiles", []) or []):
        for tile in row if isinstance(row, list) else []:
            value = _tile_type(tile)
            if value in counts:
                counts[value] += 1
    return counts


def _features(obs, actor, slot=-1):
    step = _step(obs)
    farm = _farm(obs)
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    private = _get(obs, "private", {}) or {}
    shops = [str(value) for value in list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])]
    shop_counts = {key: shops.count(key) for key in _SHOPS}
    assets = _asset_counts(farm)
    seeds = dict(_get(private, "seeds", {}) or {})
    shed = dict(_get(private, "shed", {}) or {})
    if 0 <= actor < len(positions):
        position = positions[actor]
        tile = _tile(obs, position)
        inventory = inventories[actor]
    else:
        position, tile, inventory = (-1, -1), "LOCKED", {}
    tile_name = _tile_type(tile)
    values = [
        float(step), float(step // 24), float(step % 24),
        float(len(positions) - 1), float(len(list(_get(farm, "unlocked_quadrants", []) or []))),
        float(_get(farm, "money", 0) or 0) / 100.0,
        float(actor), float(slot), float(position[0]), float(position[1]),
    ]
    values.extend(1.0 if tile_name == key else 0.0 for key in _TILE_TYPES)
    values.extend([
        float(tile.get("yield_units", 0) or 0) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("watered_today"))) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("fed_today"))) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("cared_today"))) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("fertilizer_available"))) if isinstance(tile, dict) else 0.0,
    ])
    values.extend(float(inventory.get(key, 0) or 0) for key in _ITEMS)
    values.extend(float(shop_counts[key]) for key in _SHOPS)
    values.extend(float(seeds.get(key, 0) or 0) for key in _SEEDS)
    values.extend(float(shed.get(key, 0) or 0) for key in _ITEMS)
    values.extend(float(assets[key]) for key in _ASSETS)
    return values


def _predict(tree, features):
    node = 0
    children_left = tree["left"]
    children_right = tree["right"]
    split_features = tree["feature"]
    thresholds = tree["threshold"]
    outputs = tree["output"]
    while children_left[node] != children_right[node]:
        node = children_left[node] if features[split_features[node]] <= thresholds[node] else children_right[node]
    return tree["labels"][outputs[node]]


def _regime(obs):
    shops = [str(value) for value in list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])]
    if _FULL and shops and shops[0] in _SHOPS:
        return shops[0]
    return "GLOBAL"


def _copy_action(action):
    action = copy.deepcopy(action or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or []) if order],
    }


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


def _execute(obs, unit_orders, market):
    seat = _seat(obs)
    private = _get(obs, "private", {}) or {}
    seeds = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "seeds", {}) or {}).items()}
    shed = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    safe = []
    for actor, order in enumerate(unit_orders):
        order = list(order or ["PASS"])
        if not _valid(obs, actor, order):
            order = ["PASS"]
            _STATE[seat]["unit_drops"] += 1
        elif len(order) >= 2 and order[0] == "PLANT":
            item = str(order[1])
            if seeds.get(item, 0) <= 0:
                order = ["PASS"]
                _STATE[seat]["unit_drops"] += 1
            else:
                seeds[item] -= 1
        elif len(order) >= 3 and order[0] == "PICKUP":
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), shed.get(item, 0))
            shed[item] = max(0, shed.get(item, 0) - quantity)
            order = ["PICKUP", item, quantity] if quantity > 0 else ["PASS"]
        safe.append(order)
    action = {
        "farmer": safe[0] if safe else ["PASS"],
        "hands": safe[1:],
        "market": [list(order) for order in market if order][:10],
    }
    _STATE[seat]["market_orders"] += len(action["market"])
    return action


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, calls=0, regimes={}, unit_drops=0, market_orders=0, fallback=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v90_factorized_shallow_tree_moe",
        "model_id": "v90_factorized_shallow_tree_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "first-shop-regime-router",
        "experts": ["role-conditioned-unit-tree", "market-slot-tree", "conflict-executor"],
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        _reset(obs)
        seat = _seat(obs)
        regime = _regime(obs)
        regimes = _STATE[seat]["regimes"]
        regimes[regime] = int(regimes.get(regime, 0)) + 1
        trees = _TREES[regime]
        positions = _positions(obs)
        unit_orders = [json.loads(_predict(trees["unit"], _features(obs, actor))) for actor in range(len(positions))]
        market = []
        for slot in range(10):
            order = json.loads(_predict(trees["market"], _features(obs, -1, slot)))
            if order:
                market.append(order)
        return _execute(obs, unit_orders, market)
    except Exception:
        _STATE[_seat(obs)]["fallback"] += 1
        return _fallback(obs)
