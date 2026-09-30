"""Kaggriculture V4：冠军路线启发的分层规则策略。"""

from __future__ import annotations

import base_agent as base
from routes import ROUTES


__version__ = "v4-rule-hybrid-r4-safe-gate"
_FINAL_LAYER = "r4"
_LAYER_ORDER = {"r1": 1, "r2": 2, "r3": 3, "r4": 4}
_MILK_SHOPS = {
    "PIZZA_SHOP",
    "ICE_CREAM_SHOP",
    "SMOOTHIE_SHOP",
}


def _copy_route(route):
    return [
        {
            "farmer": list(action.get("farmer") or ["PASS"]),
            "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
            "market": [list(order) for order in (action.get("market") or [])],
        }
        for action in route
    ]


_R1_LOW = _copy_route(base._LOW_ROUTE_ACTIONS)
_R1_HIGH = _copy_route(base._HIGH_ROUTE_ACTIONS)
for _route in (_R1_LOW, _R1_HIGH):
    # 冠军与原路线在第 88 步重新汇合；只替换第 3 天的扩张与工人排程。
    _route[72:88] = _copy_route(ROUTES["default"][72:88])


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs):
    explicit = _get(obs, "step")
    if explicit is not None:
        return int(explicit or 0)
    return int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _shops(obs):
    town = _get(obs, "town", {}) or {}
    return tuple(str(value) for value in (_get(town, "unlocked_shops", []) or []))


def _new_state(step=0):
    return {
        "last_step": step,
        "shops": (),
        "novelty": None,
    }


def _r1_route(state, step):
    if step < 168:
        return _R1_LOW
    shops = tuple(state.get("shops") or ())
    dominated = len(shops) >= 2 and shops[0] == "ICE_CREAM_SHOP" and shops[1] == "YARN_STORE"
    return _R1_HIGH if "YARN_STORE" in shops[:2] and not dominated else _R1_LOW


def _v2_route(state, step):
    if step < 168:
        return base._LOW_ROUTE_ACTIONS
    shops = tuple(state.get("shops") or ())
    dominated = len(shops) >= 2 and shops[0] == "ICE_CREAM_SHOP" and shops[1] == "YARN_STORE"
    return base._HIGH_ROUTE_ACTIONS if "YARN_STORE" in shops[:2] and not dominated else base._LOW_ROUTE_ACTIONS


def _r3_route(state, step):
    shops = tuple(state.get("shops") or ())
    if step >= 168 and "YARN_STORE" in shops[:2]:
        dominated = len(shops) >= 2 and shops[0] == "ICE_CREAM_SHOP" and shops[1] == "YARN_STORE"
        if not dominated:
            return ROUTES["early_yarn"]
    if step >= 216 and len(shops) >= 3 and shops[2] == "YARN_STORE":
        return ROUTES["mid_yarn"]
    if step >= 312 and len(shops) >= 4 and shops[3] == "YARN_STORE":
        milk_demand = sum(shop in _MILK_SHOPS for shop in shops[:4])
        if milk_demand <= 1:
            return ROUTES["late_yarn"]
    return ROUTES["default"]


def make_agent(layer="r4"):
    """构造独立的 R1/R2/R3/R4 评测 Agent。"""
    if layer not in _LAYER_ORDER:
        raise ValueError(layer)
    states = {0: _new_state(), 1: _new_state()}

    def layered_agent(obs, configuration=None):
        del configuration
        step = _step(obs)
        seat = _seat(obs)
        state = states[seat]
        if step == 0 or step < int(state.get("last_step", -1)):
            state = _new_state(step)
            states[seat] = state
        state["last_step"] = step
        state["shops"] = _shops(obs)

        if _LAYER_ORDER[layer] >= 4 and state.get("novelty") is None and step >= 72:
            state["novelty"] = base._clone_distance(obs) > 4

        if _LAYER_ORDER[layer] == 1:
            route = _r1_route(state, step)
        elif _LAYER_ORDER[layer] == 2:
            route = ROUTES["default"]
        else:
            route = _r3_route(state, step)
        if _LAYER_ORDER[layer] >= 4 and state.get("novelty"):
            # 冠军的单条陌生对手路线在本地弱对手和公开轨迹上出现明显尾部回撤；
            # 陌生开局使用已经过线上回归的 V2 路线，避免把单样本分支写死。
            route = _v2_route(state, step)

        base._ACTIONS = route
        return base._CORE_AGENT(obs)

    return layered_agent


_FINAL_AGENT = make_agent(_FINAL_LAYER)


def agent(obs):
    return _FINAL_AGENT(obs)
