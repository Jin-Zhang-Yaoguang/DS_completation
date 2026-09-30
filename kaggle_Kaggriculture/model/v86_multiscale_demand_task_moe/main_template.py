"""Standalone multi-timescale demand/task Hierarchical MoE for Kaggriculture."""

import base64
import copy
import json
import math
import zlib


__version__ = "v86-multiscale-demand-task-moe-rc1"
_MODE = "__MODE__"
_HIERARCHY = _MODE == "full"
_PLANS = json.loads(zlib.decompress(base64.b85decode("__ROUTE_PAYLOAD__")).decode("utf-8"))

_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")
_LIQUIDATION = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
_SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
_PRICE_BASE = {
    "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
    "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100,
}
_STATE = {
    0: {"last": -1, "regime": "opening", "first_shop": None, "recovery": {}, "dues": {}, "calls": 0},
    1: {"last": -1, "regime": "opening", "first_shop": None, "recovery": {}, "dues": {}, "calls": 0},
}
_STATS = {
    0: {"routes": {}, "weed": 0, "inventory": 0, "fertilizer": 0, "market": 0, "fallback": 0},
    1: {"routes": {}, "weed": 0, "inventory": 0, "fertilizer": 0, "market": 0, "fallback": 0},
}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs):
    return int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs, seat=None):
    target = _seat(obs) if seat is None else int(seat)
    farms = list(_get(obs, "farms", []) or [])
    return farms[target] if target < len(farms) else {}


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


def _align(action, obs):
    action = _copy_action(action)
    expected = len(list(_get(_farm(obs), "hands", []) or []))
    hands = list(action["hands"])
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    action["hands"] = hands[:expected]
    action["market"] = action["market"][:10]
    return action


def _reset_state(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, regime="opening", first_shop=None, recovery={}, dues={}, calls=0)
        _STATS[seat] = {"routes": {}, "weed": 0, "inventory": 0, "fertilizer": 0, "market": 0, "fallback": 0}
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1
    return state


def _route(obs, state):
    step = _step(obs)
    shops = [str(value) for value in list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])]
    if state.get("first_shop") is None and shops:
        state["first_shop"] = shops[0]
    if not _HIERARCHY:
        route = "dairy" if step >= 216 else "default"
    elif state.get("first_shop") == "YARN_STORE" and step >= 72:
        route = "yarn"
    elif "SMOOTHIE_SHOP" in shops and step >= 260 and not state.get("recovery"):
        route = "smoothie"
    elif step >= 216:
        route = "dairy"
    else:
        route = "default"
    state["regime"] = route
    stats = _STATS[_seat(obs)]["routes"]
    stats[route] = int(stats.get(route, 0)) + 1
    return route


def _planned_action(obs, route):
    step = min(max(_step(obs), 0), 718)
    return _align(_PLANS[route][step], obs)


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
    return min(_ACCESS, key=lambda value: abs(position[0] - value[0]) + abs(position[1] - value[1]))


def _valid_unit(obs, actor, order):
    if not order or order[0] == "PASS":
        return True
    positions = _positions(obs)
    if actor >= len(positions):
        return False
    position = positions[actor]
    tile = _tile(obs, position)
    inventories = _inventories(obs, len(positions))
    inventory = inventories[actor]
    private = _get(obs, "private", {}) or {}
    shed = dict(_get(private, "shed", {}) or {})
    seeds = dict(_get(private, "seeds", {}) or {})
    op = str(order[0])
    if op in _MOVES:
        dx, dy = _MOVES[op]
        x, y = position[0] + dx, position[1] + dy
        rows = list(_get(_farm(obs), "tiles", []) or [])
        # The engine allows units to traverse a locked quadrant; only service
        # actions are land-gated. Rejecting movement onto LOCKED tiles breaks
        # valid route corridors before the next BUY_LAND settles.
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


def _recovery_order(obs, actor, transaction):
    step = _step(obs)
    if step > int(transaction.get("expires", step)):
        return None, True
    position = _positions(obs)[actor]
    target = tuple(transaction.get("target", position))
    order = list(transaction.get("order") or ["PASS"])
    op = str(order[0])
    inventory = _inventories(obs, len(_positions(obs)))[actor]
    shed = dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {})
    need = "WHEAT" if op == "FEED" else order[1] if op == "PLACE" and len(order) > 1 else None
    if need and int(inventory.get(need, 0) or 0) <= 0:
        if position in _ACCESS and int(shed.get(need, 0) or 0) > 0:
            return ["PICKUP", need, min(6, int(shed.get(need, 0) or 0))], False
        access = _nearest_access(position)
        return _toward(position, access), False
    if position != target:
        return _toward(position, target), False
    if _valid_unit(obs, actor, order):
        return order, True
    return None, False


def _event_router(obs, action, state):
    action = _align(action, obs)
    positions = _positions(obs)
    orders = [action["farmer"], *action["hands"]]
    recovery = state.setdefault("recovery", {})
    stats = _STATS[_seat(obs)]
    step = _step(obs)

    for actor in range(len(orders)):
        key = str(actor)
        if key in recovery:
            replacement, finished = _recovery_order(obs, actor, recovery[key])
            if replacement is not None:
                orders[actor] = replacement
            if finished:
                recovery.pop(key, None)

    for actor, order in enumerate(list(orders)):
        if _valid_unit(obs, actor, order):
            continue
        op = str(order[0]) if order else "PASS"
        tile = _tile(obs, positions[actor])
        if _HIERARCHY and op in {"PLANT", "BUILD_COOP", "BUILD_PASTURE"} and isinstance(tile, dict) and tile.get("kind") == "WEED":
            recovery[str(actor)] = {"order": list(order), "target": list(positions[actor]), "expires": step + 10}
            orders[actor] = ["DIG"]
            stats["weed"] += 1
        elif _HIERARCHY and op in {"FEED", "PLACE"}:
            recovery[str(actor)] = {"order": list(order), "target": list(positions[actor]), "expires": min(step + 12, (step // 24) * 24 + 23)}
            replacement, _ = _recovery_order(obs, actor, recovery[str(actor)])
            orders[actor] = replacement or ["PASS"]
            stats["inventory"] += 1
        else:
            orders[actor] = ["PASS"]
            stats["fallback"] += 1

    remaining = {key: max(0, int(value or 0)) for key, value in dict(_get(_get(obs, "private", {}) or {}, "shed", {}) or {}).items()}
    for actor, order in enumerate(list(orders)):
        if len(order) >= 3 and order[0] == "PICKUP":
            item, requested = str(order[1]), max(0, int(order[2] or 0))
            quantity = min(requested, remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - quantity)
            orders[actor] = ["PICKUP", item, quantity] if quantity > 0 else ["PASS"]

    if _HIERARCHY:
        for actor, order in enumerate(list(orders)):
            if order and order[0] == "PASS" and _valid_unit(obs, actor, ["COLLECT_FERTILIZER"]):
                orders[actor] = ["COLLECT_FERTILIZER"]
                stats["fertilizer"] += 1

    action["farmer"], action["hands"] = orders[0], orders[1:]
    return action


def _public_signature(farm):
    counts = {key: 0 for key in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "COW", "SHEEP", "GOOSE", "PASTURE", "COOP")}
    for row in list(_get(farm, "tiles", []) or []):
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            for field in ("crop", "animal", "kind"):
                value = tile.get(field)
                if isinstance(value, dict):
                    value = value.get("kind")
                value = str(value or "").upper()
                if value in counts:
                    counts[value] += 1
                    break
    return (len(list(_get(farm, "hands", []) or [])), tuple(counts[key] for key in sorted(counts)))


def _rival_distance(obs):
    farms = list(_get(obs, "farms", []) or [])
    if len(farms) < 2:
        return 10 ** 9
    left, right = _public_signature(farms[0]), _public_signature(farms[1])
    return abs(left[0] - right[0]) + sum(abs(a - b) for a, b in zip(left[1], right[1]))


def _projected_shed(obs, action):
    private = _get(obs, "private", {}) or {}
    projected = {key: max(0, int(value or 0)) for key, value in dict(_get(private, "shed", {}) or {}).items()}
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    orders = [action["farmer"], *action["hands"]]
    for actor, order in enumerate(orders):
        if actor >= len(positions) or positions[actor] not in _ACCESS:
            continue
        inventory = inventories[actor]
        if order and order[0] == "DROP":
            deposits = list(inventory.items())
        elif order and order[0] == "PLACE" and len(order) > 1:
            deposits = [(str(order[1]), int(order[2] or 1) if len(order) > 2 else 1)]
        else:
            continue
        for item, requested in deposits:
            room = max(0, 100 - sum(projected.values()))
            amount = min(max(0, int(requested or 0)), max(0, int(inventory.get(item, 0) or 0)), room)
            projected[item] = projected.get(item, 0) + amount
    return projected


def _town_demand(obs, item, step):
    demand = 1 if item != "FERTILIZER" and step % 24 == 0 else 0
    if step % 4 == 0:
        shops = list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])
        for shop in shops:
            products = _SHOP_PRODUCTS.get(str(shop), ())
            if item in products:
                demand += 2 if len(products) == 1 else 1
    return demand


def _repay_market(action, state, step):
    dues = state.setdefault("dues", {})
    due = dict(dues.pop(str(step), {}) or {})
    if not due:
        return action
    market = []
    for raw in action["market"]:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL" and due.get(str(order[1]), 0) > 0:
            item = str(order[1])
            cut = min(max(0, int(order[2] or 0)), int(due[item]))
            order[2] = max(0, int(order[2] or 0) - cut)
            due[item] -= cut
            if order[2] <= 0:
                continue
        market.append(order)
    action["market"] = market
    return action


def _future_sell(route, step):
    if step + 1 > 718:
        return {}
    result = {}
    for order in _PLANS[route][step + 1].get("market", []) or []:
        if len(order) >= 3 and order[0] == "SELL" and str(order[1]) in _PREMIUM:
            item = str(order[1])
            result[item] = result.get(item, 0) + max(0, int(order[2] or 0))
    return result


def _market_router(obs, action, state, route):
    if not _HIERARCHY:
        action["market"] = [list(order) for order in action["market"][:10]]
        return action
    step = _step(obs)
    action = _repay_market(action, state, step)
    market = [list(order) for order in action["market"] if order]
    projected = _projected_shed(obs, action)
    planned_sell = {}
    for order in market:
        if len(order) >= 3 and order[0] == "SELL":
            item = str(order[1])
            planned_sell[item] = planned_sell.get(item, 0) + max(0, int(order[2] or 0))

    moved = {}
    if 120 <= step < 680 and _rival_distance(obs) <= 6 and len(market) < 10:
        for item, future in _future_sell(route, step).items():
            if _town_demand(obs, item, step) > 0:
                continue
            available = max(0, int(projected.get(item, 0) or 0) - int(planned_sell.get(item, 0)))
            quantity = min(available, int(future), 30)
            if quantity <= 0:
                continue
            existing = next((order for order in market if len(order) >= 3 and order[0] == "SELL" and str(order[1]) == item), None)
            if existing is not None:
                existing[2] = int(existing[2]) + quantity
            elif len(market) < 10:
                market.append(["SELL", item, quantity])
            else:
                break
            moved[item] = moved.get(item, 0) + quantity
            planned_sell[item] = planned_sell.get(item, 0) + quantity
    if moved:
        state.setdefault("dues", {})[str(step + 1)] = moved

    if step >= 715:
        for item in _LIQUIDATION:
            extra = max(0, int(projected.get(item, 0) or 0) - int(planned_sell.get(item, 0)))
            if extra <= 0:
                continue
            existing = next((order for order in market if len(order) >= 3 and order[0] == "SELL" and str(order[1]) == item), None)
            if existing is not None:
                existing[2] = int(existing[2]) + extra
            elif len(market) < 10:
                market.append(["SELL", item, extra])
            planned_sell[item] = planned_sell.get(item, 0) + extra

    merged = []
    for order in market:
        if len(order) >= 3 and order[0] in {"SELL", "BUY_PRODUCT"}:
            same = next((prior for prior in merged if len(prior) >= 3 and prior[0] == order[0] and str(prior[1]) == str(order[1])), None)
            if same is not None:
                same[2] = max(0, int(same[2] or 0)) + max(0, int(order[2] or 0))
                continue
        merged.append(order)
    market = merged[:10]

    prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
    sells = [order for order in market if len(order) >= 3 and order[0] == "SELL"]
    fixed = [order for order in market if not (len(order) >= 3 and order[0] == "SELL")]
    sells.sort(key=lambda order: (-float(prices.get(str(order[1]), _PRICE_BASE.get(str(order[1]), 1)) or 0), _PRODUCTS.index(str(order[1])) if str(order[1]) in _PRODUCTS else 99))
    market = (sells + fixed)[:10]

    safe = {"HIRE", "BUY_LAND", "BUY_SEED"}
    for index in range(1, len(market)):
        previous, current = market[index - 1], market[index]
        if previous and str(previous[0]) in safe and len(current) >= 3 and current[0] == "BUY_PRODUCT" and str(current[1]) in {"WHEAT", "FERTILIZER"} and int(current[2] or 0) > 0:
            market[index - 1], market[index] = current, previous
            break

    action["market"] = market[:10]
    _STATS[_seat(obs)]["market"] += int(action["market"] != _copy_action(_PLANS[route][min(step, 718)])["market"])
    return action


def _safe_fallback(obs):
    hands = list(_get(_farm(obs), "hands", []) or [])
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


def model_status():
    return {
        "kind": "v86_multiscale_demand_task_moe",
        "model_id": "v86_multiscale_demand_task_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "public-shop-multiscale-state-router",
        "production_experts": ["wool", "dairy_fruit", "smoothie"],
        "event_experts": ["on_plan", "weed_recovery", "inventory_recovery", "fertilizer_byproduct"],
        "market_experts": ["financing", "rival_supply", "terminal_conversion"],
        "stats": copy.deepcopy(_STATS),
    }


def agent(obs, configuration=None):
    del configuration
    try:
        state = _reset_state(obs)
        route = _route(obs, state)
        action = _planned_action(obs, route)
        action = _event_router(obs, action, state)
        action = _market_router(obs, action, state, route)
        return _align(action, obs)
    except Exception:
        _STATS[_seat(obs)]["fallback"] += 1
        return _safe_fallback(obs)
