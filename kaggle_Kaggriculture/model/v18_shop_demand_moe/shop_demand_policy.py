#!/usr/bin/env python3
"""V18 shop-demand eight-expert router built on the V17 safe executor."""

from __future__ import annotations

import copy
import importlib.util
import json
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
PARENT_DIR = MODEL / "v16_gold_strategy_research" / "top_complete_portfolio"
PARENT_POLICY = PARENT_DIR / "portfolio_policy.py"
ROUTER_STEP = 72
UPDATE_STEPS = (144, 216)
DEFER_CAP_PER_DEMAND = 4
DEFER_STOP_STEP = 680
DEFER_EXCLUDED_ITEMS = ("WHEAT",)

SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}

ROUTE_SOURCES = {
    "default": ("tyz123456", 99609968),
    "yarn": ("Kronki", 99596430),
}

ROUTE_REFERENCE_SHOPS = {
    "default": ("SMOOTHIE_SHOP", "PET_CAFE", "FARMERS_MARKET"),
    "yarn": ("YARN_STORE", "FARMERS_MARKET", "PIZZA_SHOP"),
}

# Eight public-shop experts.  Production geometry stays within one of three
# exact-prefix-compatible complete routes; expert identity and target state do
# not imply that incompatible unit-action tails are spliced together.
EXPERTS = {
    "BAKERY": {"route": "default", "focus": ("EGG", "WHEAT")},
    "BRUNCH_SPOT": {"route": "default", "focus": ("EGG", "WHEAT", "STRAWBERRY")},
    "FARMERS_MARKET": {"route": "default", "focus": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")},
    "ICE_CREAM_SHOP": {"route": "default", "focus": ("STRAWBERRY", "MILK", "WHEAT")},
    "PET_CAFE": {"route": "default", "focus": ("CARROT",)},
    "PIZZA_SHOP": {"route": "default", "focus": ("MILK", "TOMATO", "WHEAT")},
    "SMOOTHIE_SHOP": {"route": "default", "focus": ("STRAWBERRY", "MILK")},
    "YARN_STORE": {"route": "yarn", "focus": ("WOOL",)},
}

DEMAND_TARGET_INITIALIZERS = {
    "SHEEP": (4.16696195056104, 3.3108917573610057, ("YARN_STORE",)),
    "COW": (3.1170127439622135, 1.2790749487567954, ("ICE_CREAM_SHOP", "PIZZA_SHOP", "SMOOTHIE_SHOP")),
    "GOOSE": (0.20758122743682306, 0.35890493381468114, ("BAKERY", "BRUNCH_SPOT")),
    "CARROT_SEED": (-2.698974646737746, 15.82390450441259, ("FARMERS_MARKET", "PET_CAFE")),
    "TOMATO_SEED": (-3.104313780325805, 4.209955953296511, ("FARMERS_MARKET", "PIZZA_SHOP")),
    "STRAWBERRY_SEED": (15.105714690867838, 3.8340187180941574, ("BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP")),
}


def _load_module(path: Path, prefix: str):
    spec = importlib.util.spec_from_file_location(f"{prefix}_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_PARENT = _load_module(PARENT_POLICY, "v18_parent")


def _find_replay(episode: int) -> Path:
    candidates = list((PROJECT / "model_data").glob(f"**/{episode}.json"))
    candidates += list((PROJECT / "model_data").glob(f"**/episode-{episode}-replay.json"))
    if not candidates:
        raise FileNotFoundError(f"replay {episode} not found")
    return sorted(candidates, key=lambda path: ("top5_leaderboard_replays" in str(path), str(path)))[-1]


def _route(team: str, episode: int) -> list[dict]:
    replay = json.loads(_find_replay(episode).read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(team)
    return [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]


_RAW_ROUTES = {name: _route(*source) for name, source in ROUTE_SOURCES.items()}
_PREFIX = _RAW_ROUTES["default"][:ROUTER_STEP]
_ROUTES = {name: _PREFIX + actions[ROUTER_STEP:] for name, actions in _RAW_ROUTES.items()}
for _name, _actions in _RAW_ROUTES.items():
    if _actions[:ROUTER_STEP] != _PREFIX:
        raise RuntimeError(f"route {_name} does not share the exact step-72 prefix")


def _shop_demand(shops) -> dict[str, int]:
    result: dict[str, int] = {}
    for shop in shops:
        products = SHOP_PRODUCTS.get(str(shop), ())
        weight = 2 if len(products) == 1 else 1
        for item in products:
            result[item] = result.get(item, 0) + weight
    return result


def _target_quantities(shops) -> dict[str, int]:
    shops = tuple(str(value) for value in shops)
    result = {}
    for item, (intercept, slope, families) in DEMAND_TARGET_INITIALIZERS.items():
        count = sum(shop in families for shop in shops)
        result[item] = max(0, int(round(intercept + slope * count)))
    return result


def _update_demand_state(state: dict, shops, step: int) -> None:
    shops = tuple(str(value) for value in shops)
    stage = int(state.get("update_stage", 0))
    if step >= UPDATE_STEPS[1] and stage < 2 and len(shops) >= 3:
        state["update_stage"] = 2
        state["target_shops"] = shops[:3]
        state["targets"] = _target_quantities(shops[:3])
    elif step >= UPDATE_STEPS[0] and stage < 1 and len(shops) >= 2:
        state["update_stage"] = 1
        state["target_shops"] = shops[:2]
        state["targets"] = _target_quantities(shops[:2])


def _apply_demand_overlay(obs, action, state: dict, step: int):
    """Delay a bounded demanded-product sale across a town-consumption tick."""
    action = copy.deepcopy(action)
    market = [list(order) for order in (action.get("market") or [])]
    shed = dict((obs.get("private") or {}).get("shed") or {})

    if int(state.get("due_step", -1)) == step:
        for item, requested in dict(state.get("due") or {}).items():
            existing = sum(
                max(0, int(order[2] or 0))
                for order in market
                if len(order) >= 3 and order[0] == "SELL" and order[1] == item
            )
            quantity = min(max(0, int(requested)), max(0, int(shed.get(item, 0) or 0) - existing))
            if quantity <= 0:
                continue
            current = next(
                (order for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == item),
                None,
            )
            if current is not None:
                current[2] = max(0, int(current[2] or 0)) + quantity
            elif len(market) < 10:
                market.append(["SELL", item, quantity])
        state["due_step"], state["due"] = -1, {}

    if (
        int(state.get("update_stage", 0)) > 0
        and step < DEFER_STOP_STEP
        and step % 4 == 0
        and not state.get("due")
    ):
        route = str(state.get("route") or "default")
        target_shops = tuple(state.get("target_shops") or ())
        actual = _shop_demand(target_shops)
        expected = _shop_demand(ROUTE_REFERENCE_SHOPS[route][:len(target_shops)])
        due = {}
        for order in market:
            if len(order) < 3 or order[0] != "SELL":
                continue
            if str(order[1]) in DEFER_EXCLUDED_ITEMS:
                continue
            delta = max(0, actual.get(str(order[1]), 0) - expected.get(str(order[1]), 0))
            quantity = min(max(0, int(order[2] or 0)), DEFER_CAP_PER_DEMAND * delta)
            if quantity > 0:
                order[2] = max(0, int(order[2] or 0)) - quantity
                due[str(order[1])] = due.get(str(order[1]), 0) + quantity
        market = [
            order for order in market
            if not (len(order) >= 3 and order[0] == "SELL" and int(order[2] or 0) <= 0)
        ]
        if due:
            state["due_step"], state["due"] = step + 1, due

    action["market"] = market[:10]
    return action


def make_agent(mode: str = "router"):
    if mode == "parent":
        return _PARENT.make_agent("router")
    if mode != "router":
        raise ValueError(mode)

    base = _PARENT._fresh_base()
    base._V17_FEED_GUARD = False
    states = {
        0: {"last": -1, "expert": None, "route": "default", "update_stage": 0, "due_step": -1, "due": {}},
        1: {"last": -1, "expert": None, "route": "default", "update_stage": 0, "due_step": -1, "due": {}},
    }

    def policy(obs, configuration=None):
        del configuration
        seat = _PARENT._seat(obs)
        step = _PARENT._step(obs)
        state = states[seat]
        if step == 0 or step < int(state.get("last", -1)):
            state.clear()
            state.update(last=step, expert=None, route="default", update_stage=0, due_step=-1, due={})
        state["last"] = step
        shops = tuple(str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or []))
        if state.get("expert") is None and step >= ROUTER_STEP:
            expert = shops[0] if shops and shops[0] in EXPERTS else "SMOOTHIE_SHOP"
            state["expert"] = expert
            state["route"] = EXPERTS[expert]["route"]
        _update_demand_state(state, shops, step)
        base._ACTIONS = _ROUTES[str(state.get("route") or "default")]
        action = base._CORE_AGENT(obs)
        action = _PARENT._cap_fixed_purchases(obs, action, base)
        action = _PARENT._fail_closed_units(obs, action)
        return _apply_demand_overlay(obs, action, state, step)

    policy.__name__ = "v18_shop_demand_moe"
    policy._v18_state = states
    return policy


agent = make_agent("router")
