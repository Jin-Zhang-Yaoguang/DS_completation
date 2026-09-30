#!/usr/bin/env python3
"""Replay-derived complete routes wrapped by the V17 state-safe executor."""

from __future__ import annotations

import copy
import importlib.util
import json
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
PARENT_POLICY = MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "portfolio_policy.py"
HIERARCHICAL_POLICY = MODEL / "v19_hierarchical_moe" / "hierarchical_policy.py"

ROUTES = {
    "crop_high": ("Crop Dusta", 100075627),
    "milan_high": ("Milan Leonard", 100439982),
    "ryo_high": ("Ryo Hasegawa", 94824465),
    "subramanya_high": ("Subramanya N", 99226956),
    "lucaskna_high": ("lucaskna", 100485613),
    "crop_smoothie": ("Crop Dusta", 100075622),
    "crop_pet": ("Crop Dusta", 97692129),
    "crop_ice": ("Crop Dusta", 100075627),
    "crop_bakery": ("Crop Dusta", 98488487),
    "crop_yarn": ("Crop Dusta", 98292221),
    "crop_farmers": ("Crop Dusta", 98688814),
    "crop_pizza": ("Crop Dusta", 100337610),
    "crop_brunch": ("Crop Dusta", 97696718),
}

CROP_SHOP_ROUTES = {
    "crop_smoothie": "SMOOTHIE_SHOP",
    "crop_pet": "PET_CAFE",
    "crop_ice": "ICE_CREAM_SHOP",
    "crop_bakery": "BAKERY",
    "crop_yarn": "YARN_STORE",
    "crop_farmers": "FARMERS_MARKET",
    "crop_pizza": "PIZZA_SHOP",
    "crop_brunch": "BRUNCH_SPOT",
}


def _load_module(path: Path, prefix: str):
    spec = importlib.util.spec_from_file_location(f"{prefix}_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


PARENT = _load_module(PARENT_POLICY, "v21_parent")
HIER = _load_module(HIERARCHICAL_POLICY, "v21_hier")


def _find_replay(episode: int) -> Path:
    candidates = list((PROJECT / "model_data").glob(f"**/{episode}.json"))
    candidates += list((PROJECT / "model_data").glob(f"**/episode-{episode}-replay.json"))
    if not candidates:
        raise FileNotFoundError(episode)
    return sorted(candidates, key=str)[-1]


def source_actions(team: str, episode: int) -> list[dict]:
    replay = json.loads(_find_replay(episode).read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(team)
    actions = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
    if len(actions) != 719:
        raise RuntimeError(f"{team}::{episode}: expected 719 actions, got {len(actions)}")
    return actions


def route_actions(route_id: str) -> list[dict]:
    return source_actions(*ROUTES[route_id])


def make_route_agent(route_id: str):
    if route_id not in ROUTES:
        raise KeyError(route_id)
    actions = route_actions(route_id)
    base = PARENT._fresh_base()
    base._V17_FEED_GUARD = False

    def policy(obs, configuration=None):
        del configuration
        base._ACTIONS = actions
        action = base._CORE_AGENT(obs)
        action = PARENT._cap_fixed_purchases(obs, action, base)
        return PARENT._fail_closed_units(obs, action)

    policy.__name__ = f"v21_safe_{route_id}"
    return policy


def make_lucaskna_hybrid(switch_step: int, gate: str = "non_yarn", seller_mode: str = "demand_delay_25"):
    """Run the V20 router first, then expose the lucaskna route as a late expert.

    The state-safe executor repairs route/state mismatches.  ``first_pizza`` is
    the first causal shop gate suggested by the source replay; ``non_yarn`` is
    the broad ablation used to determine whether the route has general value.
    """

    if switch_step not in (216, 288, 360, 432, 504):
        raise ValueError(switch_step)
    if gate not in {"non_yarn", "first_pizza"}:
        raise ValueError(gate)
    lucas = route_actions("lucaskna_high")
    base = HIER.PARENT._fresh_base()
    base._V17_FEED_GUARD = False
    states = {
        0: {"last": -1, "expert": None, "demand_due_step": -1, "demand_due": {}},
        1: {"last": -1, "expert": None, "demand_due_step": -1, "demand_due": {}},
    }

    def policy(obs, configuration=None):
        del configuration
        seat = HIER.PARENT._seat(obs)
        step = HIER.PARENT._step(obs)
        state = states[seat]
        if step == 0 or step < int(state.get("last", -1)):
            state.clear()
            state.update(last=step, expert=None, demand_due_step=-1, demand_due={})
        state["last"] = step
        shops = [str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])]
        if state.get("expert") is None and step >= HIER.ROUTER_STEP:
            state["expert"] = "yarn" if shops and shops[0] == "YARN_STORE" else "default"

        current = str(state.get("expert") or "default")
        if current == "default" and step >= 360:
            current = "bakery_brunch"
        eligible = (
            step >= switch_step
            and current != "yarn"
            and (gate == "non_yarn" or bool(shops and shops[0] == "PIZZA_SHOP"))
        )
        base._ACTIONS = lucas if eligible else HIER._ROUTES[current]
        action = base._CORE_AGENT(obs)
        action = HIER._commodity_sell_control(obs, action, step, base, seller_mode, state)
        action = HIER.PARENT._cap_fixed_purchases(obs, action, base)
        return HIER.PARENT._fail_closed_units(obs, action)

    policy.__name__ = f"v21_lucaskna_{gate}_{switch_step}_{seller_mode}"
    policy._v21_state = states
    return policy


def make_shop_expert_router(route_id: str, seller_mode: str = "demand_delay_25"):
    """Replace exactly one first-shop branch at step 216; keep V21 elsewhere."""

    if route_id not in CROP_SHOP_ROUTES:
        raise KeyError(route_id)
    target_shop = CROP_SHOP_ROUTES[route_id]
    target_route = route_actions(route_id)
    lucas = route_actions("lucaskna_high")
    base = HIER.PARENT._fresh_base()
    base._V17_FEED_GUARD = False
    states = {
        0: {"last": -1, "first_shop": None, "demand_due_step": -1, "demand_due": {}},
        1: {"last": -1, "first_shop": None, "demand_due_step": -1, "demand_due": {}},
    }

    def policy(obs, configuration=None):
        del configuration
        seat = HIER.PARENT._seat(obs)
        step = HIER.PARENT._step(obs)
        state = states[seat]
        if step == 0 or step < int(state.get("last", -1)):
            state.clear()
            state.update(last=step, first_shop=None, demand_due_step=-1, demand_due={})
        state["last"] = step
        shops = [str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])]
        if state.get("first_shop") is None and step >= HIER.ROUTER_STEP and shops:
            state["first_shop"] = shops[0]
        first_shop = str(state.get("first_shop") or "")
        if step >= 216 and first_shop == target_shop:
            base._ACTIONS = target_route
        elif step >= 216 and first_shop != "YARN_STORE":
            base._ACTIONS = lucas
        else:
            base._ACTIONS = HIER._ROUTES["yarn" if first_shop == "YARN_STORE" else "default"]
        action = base._CORE_AGENT(obs)
        action = HIER._commodity_sell_control(obs, action, step, base, seller_mode, state)
        action = HIER.PARENT._cap_fixed_purchases(obs, action, base)
        return HIER.PARENT._fail_closed_units(obs, action)

    policy.__name__ = f"v24_{route_id}_{seller_mode}"
    policy._v24_state = states
    return policy


def make_compatible_shop_router(
    target_shop: str,
    team: str,
    episode: int,
    seller_mode: str = "demand_delay_25",
    switch_step: int = 216,
):
    """Target one first-shop branch with a mined prefix-compatible route."""

    target_route = source_actions(team, episode)
    lucas = route_actions("lucaskna_high")
    base = HIER.PARENT._fresh_base()
    base._V17_FEED_GUARD = False
    states = {
        0: {"last": -1, "first_shop": None, "demand_due_step": -1, "demand_due": {}},
        1: {"last": -1, "first_shop": None, "demand_due_step": -1, "demand_due": {}},
    }

    def policy(obs, configuration=None):
        del configuration
        seat = HIER.PARENT._seat(obs)
        step = HIER.PARENT._step(obs)
        state = states[seat]
        if step == 0 or step < int(state.get("last", -1)):
            state.clear()
            state.update(last=step, first_shop=None, demand_due_step=-1, demand_due={})
        state["last"] = step
        shops = [str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])]
        if state.get("first_shop") is None and step >= HIER.ROUTER_STEP and shops:
            state["first_shop"] = shops[0]
        first_shop = str(state.get("first_shop") or "")
        if step >= switch_step and first_shop == target_shop:
            base._ACTIONS = target_route
        elif step >= 216 and first_shop != "YARN_STORE":
            base._ACTIONS = lucas
        else:
            base._ACTIONS = HIER._ROUTES["yarn" if first_shop == "YARN_STORE" else "default"]
        action = base._CORE_AGENT(obs)
        action = HIER._commodity_sell_control(obs, action, step, base, seller_mode, state)
        action = HIER.PARENT._cap_fixed_purchases(obs, action, base)
        return HIER.PARENT._fail_closed_units(obs, action)

    policy.__name__ = f"v25_{team}_{episode}_{target_shop}_{seller_mode}_{switch_step}".replace(" ", "_")
    policy._v25_state = states
    return policy
