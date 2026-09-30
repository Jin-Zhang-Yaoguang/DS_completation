"""Standalone Contractual Path Forest Hierarchical MoE for Kaggriculture."""

import base64
import copy
import json
import zlib


__version__ = "v115-contractual-path-forest-moe-rc1"
_MODE = "__MODE__"
_FULL = _MODE == "full"
_PAYLOAD = json.loads(zlib.decompress(base64.b85decode("__PAYLOAD__")).decode("utf-8"))
_PLANS = _PAYLOAD["plans"]
_TREE = _PAYLOAD["tree"]
_ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_PURCHASES = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}
_MARKET_OPS = _PURCHASES | {"SELL"}
_STATE = {0: {}, 1: {}}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _step(obs):
    raw = _get(obs, "step", None)
    if raw is None:
        raw = int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    return min(718, max(0, int(raw or 0)))


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _shops(obs):
    town = _get(obs, "town", {}) or {}
    return tuple(str(value) for value in list(_get(town, "unlocked_shops", []) or []))


def _reset(obs):
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(
            last=step,
            calls=0,
            first_shop=None,
            committed=None,
            dues={},
            previous_inventory=None,
            previous_prices=None,
            previous_market=[],
            previous_shops=(),
            previous_step=-1,
            stats={
                "route_calls": {},
                "commitments": {},
                "contract_failures": 0,
                "predict_buy": 0,
                "predict_neutral": 0,
                "predict_sell": 0,
                "preempt": 0,
                "wait": 0,
                "release": 0,
                "changed_calls": 0,
                "fallback": 0,
            },
        )
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1
    shops = _shops(obs)
    if state.get("first_shop") is None and shops:
        state["first_shop"] = shops[0]
    return state


def _record(state, key, name=None, amount=1):
    stats = state["stats"]
    if name is None:
        stats[key] = int(stats.get(key, 0)) + int(amount)
    else:
        bucket = stats.setdefault(key, {})
        bucket[name] = int(bucket.get(name, 0)) + int(amount)


def _plan_contract(obs, route):
    plan = _PLANS.get(route)
    if not isinstance(plan, list) or len(plan) != 719:
        return False
    action = plan[_step(obs)]
    if not isinstance(action, dict) or set(action) - {"farmer", "hands", "market"}:
        return False
    if not isinstance(action.get("market", []), list):
        return False
    return len(list(_get(_farm(obs), "hands", []) or [])) >= 0


def _desired_route(obs, state):
    step = _step(obs)
    if _MODE.startswith("expert_"):
        return _MODE.removeprefix("expert_")
    if _MODE == "ablation":
        return "default" if step < 216 else "dairy"
    if state.get("committed") is not None:
        return str(state["committed"])
    first = state.get("first_shop")
    shops = _shops(obs)
    if step >= 72 and first == "YARN_STORE":
        return "yarn"
    if step >= 216:
        smoothie_score = 2 * int("SMOOTHIE_SHOP" in shops) + int("ICE_CREAM_SHOP" in shops)
        return "smoothie" if smoothie_score >= 2 else "dairy"
    return "default"


def _route(obs, state):
    step = _step(obs)
    desired = _desired_route(obs, state)
    if _MODE.startswith("expert_"):
        state["committed"] = desired
    elif _MODE == "ablation" and step >= 216:
        state["committed"] = "dairy"
    elif _FULL and state.get("committed") is None and ((step >= 72 and desired == "yarn") or step >= 216):
        if _plan_contract(obs, desired):
            state["committed"] = desired
            _record(state, "commitments", desired)
        else:
            state["committed"] = "default" if step < 216 else "dairy"
            _record(state, "contract_failures")
    route = str(state.get("committed") or desired)
    if not _plan_contract(obs, route):
        route = "default" if step < 216 else "dairy"
        _record(state, "contract_failures")
    _record(state, "route_calls", route)
    return route


def _copy_planned_action(obs, route):
    action = copy.deepcopy(_PLANS[route][_step(obs)] or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in list(action.get("hands", []) or [])],
        "market": [list(order) for order in list(action.get("market", []) or []) if order],
    }


def _signed_market(market, item):
    signed, first_slot = 0, 10
    for index, order in enumerate(market or []):
        if len(order) < 3 or str(order[1]) != item:
            continue
        quantity = max(0, int(order[2] or 0))
        if order[0] == "SELL":
            signed += quantity
            first_slot = min(first_slot, index)
        elif order[0] == "BUY_PRODUCT":
            signed -= quantity
            first_slot = min(first_slot, index)
    return signed, first_slot


def _tree_predict(features):
    node = 0
    while int(_TREE["left"][node]) >= 0:
        feature = int(_TREE["feature"][node])
        node = int(_TREE["left"][node]) if features[feature] <= float(_TREE["threshold"][node]) else int(_TREE["right"][node])
    values = list(_TREE["value"][node])
    return int(_TREE["classes"][max(range(len(values)), key=lambda index: values[index])])


def _opponent_path(obs, state):
    if state.get("previous_inventory") is None:
        return {item: 0 for item in _ITEMS}
    market = _get(obs, "market", {}) or {}
    inventory = dict(_get(market, "inventory", {}) or {})
    prices = dict(_get(market, "prices", {}) or {})
    previous_step = int(state.get("previous_step", -1))
    previous_shops = set(state.get("previous_shops", ()))
    labels = {}
    for item_index, item in enumerate(_ITEMS):
        own, slot = _signed_market(state.get("previous_market", []), item)
        features = [
            int(inventory.get(item, 0) or 0) - int(state["previous_inventory"].get(item, 0) or 0),
            int(prices.get(item, 0) or 0) - int(state["previous_prices"].get(item, 0) or 0),
            own,
            slot,
            item_index,
            _seat(obs),
            previous_step % 4,
            previous_step % 24,
            int(previous_step % 4 == 0),
            int(previous_step % 24 == 0),
            *[int(shop in previous_shops) for shop in ("BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE")],
        ]
        labels[item] = _tree_predict(features)
        _record(state, "predict_buy" if labels[item] < 0 else "predict_sell" if labels[item] > 0 else "predict_neutral")
    return labels


def _merge_sells(market):
    merged = []
    for raw in market:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL":
            prior = next((value for value in merged if len(value) >= 3 and value[0] == "SELL" and str(value[1]) == str(order[1])), None)
            if prior is not None:
                prior[2] = max(0, int(prior[2] or 0)) + max(0, int(order[2] or 0))
                continue
        merged.append(order)
    return merged


def _sell_controller(obs, action, labels, state):
    original = [list(order) for order in action["market"]]
    if not _FULL:
        return action
    step = _step(obs)
    has_purchase = any(order and str(order[0]) in _PURCHASES for order in original)
    front, body = [], []
    for raw in original:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL" and str(order[1]) in _ITEMS:
            item = str(order[1])
            quantity = max(0, int(order[2] or 0))
            label = int(labels.get(item, 0))
            if label > 0 and not has_purchase and step < 712 and quantity >= 4:
                held = max(1, quantity // 4)
                order[2] = quantity - held
                state["dues"][item] = int(state["dues"].get(item, 0)) + held
                _record(state, "wait")
            elif label < 0:
                front.append(order)
                _record(state, "preempt")
                continue
        if len(order) < 3 or int(order[2] or 0) > 0:
            body.append(order)
    for item, quantity in list(state.get("dues", {}).items()):
        if int(quantity) > 0:
            front.append(["SELL", item, int(quantity)])
            _record(state, "release")
    state["dues"] = {}
    action["market"] = _merge_sells(front + body)
    _record(state, "changed_calls", amount=int(action["market"] != original))
    return action


def _safe_execute(obs, action, state):
    expected = len(list(_get(_farm(obs), "hands", []) or []))
    hands = [list(order or ["PASS"]) for order in list(action.get("hands", []) or [])]
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    safe_market = []
    for raw in list(action.get("market", []) or []):
        order = list(raw)
        if not order or str(order[0]) not in _MARKET_OPS:
            continue
        if len(order) >= 3:
            try:
                order[2] = max(0, min(1000000, int(order[2] or 0)))
            except (TypeError, ValueError):
                continue
            if order[2] <= 0:
                continue
        safe_market.append(order)
        if len(safe_market) == 10:
            break
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": hands[:expected],
        "market": safe_market,
    }


def _remember(obs, action, state):
    market = _get(obs, "market", {}) or {}
    state["previous_inventory"] = dict(_get(market, "inventory", {}) or {})
    state["previous_prices"] = dict(_get(market, "prices", {}) or {})
    state["previous_market"] = copy.deepcopy(action.get("market", []))
    state["previous_shops"] = _shops(obs)
    state["previous_step"] = _step(obs)


def _fallback(obs, state):
    _record(state, "fallback")
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])],
        "market": [],
    }


def model_status():
    return {
        "kind": "v115_contractual_path_forest_moe",
        "model_id": "v115_contractual_path_forest_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "mode": _MODE,
        "router": "shop-demand-contractual-complete-route-router",
        "production_experts": ["default", "yarn", "dairy", "smoothie"],
        "opponent_predictor": "lagged-public-market-impact-depth6-tree",
        "sell_experts": ["preempt", "same_slot", "one_step_wait", "due_release"],
        "state_contract": "shared-prefix-one-way-commitment",
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    state = _reset(obs)
    try:
        route = _route(obs, state)
        labels = _opponent_path(obs, state)
        action = _copy_planned_action(obs, route)
        action = _sell_controller(obs, action, labels, state)
        action = _safe_execute(obs, action, state)
        _remember(obs, action, state)
        return action
    except Exception:
        return _fallback(obs, state)

