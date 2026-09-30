#!/usr/bin/env python3
"""V19 three-route hierarchical production policy with the V17 safe executor."""

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
ROUTER_STEP = 72
STATE_SNAPSHOT_STEPS = (144, 216)
ROUTE_SWITCH_STEPS = (144, 216, 288, 360, 432, 504, 576)
SELL_PRICE_THRESHOLDS = {
    "STRAWBERRY": 155,
    "MELON": 156,
    "MILK": 172,
    "WOOL": 164,
    "FERTILIZER": 57,
}
SELL_HOLD_STOP_STEP = 672
SELL_SHED_PRESSURE = 80

ROUTE_SOURCES = {
    "default": ("tyz123456", 99609968),
    "bakery_brunch": ("Kronki", 99108392),
    "p1_smoothie": ("tyz123456", 99005630),
    "p1_bakery": ("tyz123456", 99190436),
    "p1_ice": ("tyz123456", 99512062),
    "p3_bakery": ("tyz123456", 99245027),
    "yarn": ("Kronki", 99596430),
}

FIRST_SHOP_ROUTE = {
    "BAKERY": "default",
    "BRUNCH_SPOT": "default",
    "FARMERS_MARKET": "default",
    "ICE_CREAM_SHOP": "default",
    "PET_CAFE": "default",
    "PIZZA_SHOP": "default",
    "SMOOTHIE_SHOP": "default",
    "YARN_STORE": "yarn",
}


def _load_module(path: Path, prefix: str):
    spec = importlib.util.spec_from_file_location(f"{prefix}_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


PARENT = _load_module(PARENT_POLICY, "v19_parent")


def _find_replay(episode: int) -> Path:
    candidates = list((PROJECT / "model_data").glob(f"**/{episode}.json"))
    candidates += list((PROJECT / "model_data").glob(f"**/episode-{episode}-replay.json"))
    if not candidates:
        raise FileNotFoundError(episode)
    return sorted(candidates, key=str)[-1]


def _route(team: str, episode: int) -> list[dict]:
    replay = json.loads(_find_replay(episode).read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(team)
    return [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]


_RAW_ROUTES = {name: _route(*source) for name, source in ROUTE_SOURCES.items()}
_PREFIX = _RAW_ROUTES["default"][:ROUTER_STEP]
for _name, _actions in _RAW_ROUTES.items():
    if _actions[:ROUTER_STEP] != _PREFIX:
        raise RuntimeError(f"route {_name} is not exact-prefix compatible")
_ROUTES = {name: _PREFIX + actions[ROUTER_STEP:] for name, actions in _RAW_ROUTES.items()}


def _public_state_snapshot(obs) -> dict:
    seat = PARENT._seat(obs)
    farm = obs["farms"][seat]
    animals = {"GOOSE": 0, "COW": 0, "SHEEP": 0}
    crops = {"WHEAT": 0, "CARROT": 0, "TOMATO": 0, "STRAWBERRY": 0, "MELON": 0}
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            animal = tile.get("animal")
            crop = tile.get("crop")
            if animal in animals:
                animals[animal] += 1
            if crop in crops:
                crops[crop] += 1
    return {
        "money": int(farm.get("money", 0) or 0),
        "hands": len(farm.get("hands") or []),
        "land": len(farm.get("unlocked_quadrants") or []),
        "animals": animals,
        "crops": crops,
        "shops": [str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])],
    }


def _commodity_sell_control(obs, action, step: int, base, seller_mode: str, seller_state: dict | None = None):
    if seller_mode == "none":
        return action
    demand_delay_modes = {
        "demand_delay_12_5": 0.125,
        "demand_delay_25": 0.25,
        "demand_delay_37_5": 0.375,
        "demand_delay_50": 0.50,
        "demand_delay_100": 1.00,
    }
    if seller_mode in demand_delay_modes:
        seller_state = seller_state if seller_state is not None else {}
        action = copy.deepcopy(action)
        market = [list(order) for order in (action.get("market") or [])]
        due_step = int(seller_state.get("demand_due_step", -1))
        due = {str(item): max(0, int(quantity or 0)) for item, quantity in dict(seller_state.get("demand_due") or {}).items()}
        if due and due_step <= step:
            for item, quantity in due.items():
                if quantity <= 0:
                    continue
                existing = next((order for order in market if base._is_sell(order) and str(order[1]) == item), None)
                if existing is not None:
                    existing[2] = max(0, int(existing[2] or 0)) + quantity
                elif len(market) < 10:
                    market.append(["SELL", item, quantity])
                else:
                    # Fail closed: carry once rather than silently dropping a
                    # quantity-neutral shift when all market slots are occupied.
                    seller_state["demand_due_step"] = step + 1
                    action["market"] = market[:10]
                    return action
            seller_state["demand_due_step"] = -1
            seller_state["demand_due"] = {}

        can_delay = (
            360 <= step < 672
            and not due
            and market
            and all(base._is_sell(order) for order in market)
        )
        if can_delay:
            shed = dict((obs.get("private") or {}).get("shed") or {})
            shed_total = sum(max(0, int(value or 0)) for value in shed.values())
            next_market = list((base._ACTIONS[step + 1] or {}).get("market") or []) if step + 1 < len(base._ACTIONS) else []
            delayed = {}
            if shed_total < SELL_SHED_PRESSURE:
                for order in market:
                    item = str(order[1])
                    quantity = max(0, int(order[2] or 0))
                    demand = int(base._v17_town_demand_at(obs, item, step) or 0)
                    next_has_room = len(next_market) < 10 or any(base._is_sell(future) and str(future[1]) == item for future in next_market)
                    if demand <= 0 or quantity <= 0 or not next_has_room:
                        continue
                    shift = min(quantity, max(1, int(round(quantity * demand_delay_modes[seller_mode]))))
                    order[2] = quantity - shift
                    delayed[item] = delayed.get(item, 0) + shift
            if delayed:
                market = [order for order in market if max(0, int(order[2] or 0)) > 0]
                seller_state["demand_due_step"] = step + 1
                seller_state["demand_due"] = delayed
        action["market"] = market[:10]
        return base._rank_sell_slots(obs, action, None)
    collision_modes = {
        "collision_rank_50": 0.50,
        "collision_rank_100": 1.00,
        "collision_rank_200": 2.00,
    }
    if seller_mode in collision_modes:
        seller_state = seller_state if seller_state is not None else {}
        market_obs = dict(obs.get("market") or {})
        inventory = {str(key): int(value or 0) for key, value in dict(market_obs.get("inventory") or {}).items()}
        previous_inventory = dict(seller_state.get("collision_inventory") or {})
        previous_market = [list(order) for order in (seller_state.get("collision_market") or [])]
        previous_step = int(seller_state.get("collision_step", -2))
        pressure = dict(seller_state.get("collision_pressure") or {})
        if previous_inventory and previous_step + 1 == step:
            for item, current in inventory.items():
                demand = int(base._v17_town_demand_at(obs, item, previous_step) or 0)
                own_net_supply = 0
                for order in previous_market:
                    if len(order) < 3 or str(order[1]) != item:
                        continue
                    quantity = max(0, int(order[2] or 0))
                    if order[0] == "SELL":
                        own_net_supply += quantity
                    elif order[0] == "BUY_PRODUCT":
                        own_net_supply -= quantity
                total_net_supply = int(current) - int(previous_inventory.get(item, current)) + demand
                inferred_opponent_supply = max(0, total_net_supply - own_net_supply)
                pressure[item] = 0.50 * float(pressure.get(item, 0.0) or 0.0) + inferred_opponent_supply

        action = copy.deepcopy(action)
        market = [list(order) for order in (action.get("market") or [])]
        rows = []
        for index, order in enumerate(market):
            if not base._is_sell(order):
                continue
            item = str(order[1])
            quantity = max(0, int(order[2] or 0))
            start_inventory = int(inventory.get(item, 0) or 0)
            predicted_units = max(0, int(round(float(pressure.get(item, 0.0) or 0.0))))

            def sale_revenue(start: int, units: int) -> tuple[float, int]:
                revenue = 0.0
                current_inventory = int(start)
                for _ in range(units):
                    price = base._market_price(item, current_inventory)
                    revenue += price
                    if price > base._PRICE_FLOOR:
                        current_inventory += 1
                return revenue, current_inventory

            revenue_now, _ = sale_revenue(start_inventory, quantity)
            _, delayed_inventory = sale_revenue(start_inventory, predicted_units)
            revenue_delayed, _ = sale_revenue(delayed_inventory, quantity)
            collision_loss = max(0.0, revenue_now - revenue_delayed)
            score = float(base._impact_score(obs, order)) + collision_modes[seller_mode] * collision_loss
            rows.append((score, -index, order))
        if len(rows) >= 2:
            rows.sort(reverse=True)
            ranked = iter(row[2] for row in rows)
            market = [next(ranked) if base._is_sell(order) else order for order in market]
        action["market"] = market[:10]
        seller_state["collision_inventory"] = inventory
        seller_state["collision_market"] = [list(order) for order in action["market"]]
        seller_state["collision_step"] = step
        seller_state["collision_pressure"] = pressure
        return action
    relative_modes = {
        "relative_q50_hold25": (0.50, 0.25, set(SELL_PRICE_THRESHOLDS), "hold"),
        "relative_q70_hold25": (0.70, 0.25, set(SELL_PRICE_THRESHOLDS), "hold"),
        "relative_q70_hold50": (0.70, 0.50, set(SELL_PRICE_THRESHOLDS), "hold"),
        "relative_q85_hold25": (0.85, 0.25, set(SELL_PRICE_THRESHOLDS), "hold"),
        "relative_wool_q70_hold25": (0.70, 0.25, {"WOOL"}, "hold"),
        "relative_strawberry_q70_hold25": (0.70, 0.25, {"STRAWBERRY"}, "hold"),
        "relative_q70_boost10": (0.70, 0.10, set(SELL_PRICE_THRESHOLDS), "boost"),
        "relative_q70_boost25": (0.70, 0.25, set(SELL_PRICE_THRESHOLDS), "boost"),
        "relative_q85_boost25": (0.85, 0.25, set(SELL_PRICE_THRESHOLDS), "boost"),
        "relative_wool_q70_boost25": (0.70, 0.25, {"WOOL"}, "boost"),
        "relative_strawberry_q70_boost25": (0.70, 0.25, {"STRAWBERRY"}, "boost"),
        "relative_milk_q70_boost25": (0.70, 0.25, {"MILK"}, "boost"),
        "relative_fertilizer_q70_boost25": (0.70, 0.25, {"FERTILIZER"}, "boost"),
    }
    if seller_mode in relative_modes:
        quantile_level, adjustment_fraction, active_products, direction = relative_modes[seller_mode]
        seller_state = seller_state if seller_state is not None else {}
        if seller_state.get("expert") == "yarn":
            return action
        histories = seller_state.setdefault("price_history", {})
        prices = dict((obs.get("market") or {}).get("prices") or {})
        thresholds = {}
        for item in active_products:
            history = list(histories.get(item) or [])[-72:]
            if len(history) >= 24:
                ordered = sorted(float(value) for value in history)
                thresholds[item] = ordered[int(round((len(ordered) - 1) * quantile_level))]
            histories.setdefault(item, []).append(float(prices.get(item, 0) or 0))
            histories[item] = histories[item][-72:]
        if step < 360 or step >= 672:
            return action
        action = copy.deepcopy(action)
        market = [list(order) for order in (action.get("market") or [])]
        projected = base._projected_shed(obs, action)
        shed_total = sum(max(0, int(value or 0)) for value in projected.values())
        remaining = {item: max(0, int(value or 0)) for item, value in projected.items()}
        for order in market:
            if len(order) < 3 or order[0] != "SELL":
                continue
            item = str(order[1])
            quantity = min(max(0, int(order[2] or 0)), remaining.get(item, 0))
            price = float(prices.get(item, 0) or 0)
            should_adjust = (
                item in active_products
                and item in thresholds
                and shed_total < SELL_SHED_PRESSURE
                and ((direction == "hold" and price < thresholds[item]) or (direction == "boost" and price > thresholds[item]))
            )
            if should_adjust and direction == "hold":
                quantity = max(0, quantity - max(1, int(round(quantity * adjustment_fraction))))
            elif should_adjust and direction == "boost":
                extra_room = max(0, remaining.get(item, 0) - quantity)
                quantity += min(extra_room, max(1, int(round(quantity * adjustment_fraction))))
            order[2] = quantity
            remaining[item] = max(0, remaining.get(item, 0) - quantity)
        action["market"] = [order for order in market if not (len(order) >= 3 and order[0] == "SELL" and int(order[2] or 0) <= 0)][:10]
        return action
    wheat_modes = {
        "wheat_no_buy": (None, 0),
        "wheat_hold_576": (576, 0),
        "wheat_hold_648": (648, 0),
        "wheat_reserve_25": (648, 25),
        "wheat_reserve_50": (648, 50),
        "wheat_reserve_75": (648, 75),
    }
    if seller_mode in wheat_modes:
        if step < 360:
            return action
        hold_until, reserve = wheat_modes[seller_mode]
        action = copy.deepcopy(action)
        market = [list(order) for order in (action.get("market") or [])]
        projected = base._projected_shed(obs, action)
        remaining_wheat = max(0, int(projected.get("WHEAT", 0) or 0))
        for order in market:
            if len(order) < 3 or order[1] != "WHEAT":
                continue
            if order[0] == "BUY_PRODUCT":
                order[2] = 0
            elif order[0] == "SELL":
                quantity = max(0, int(order[2] or 0))
                if hold_until is None:
                    allowed = quantity
                elif step < hold_until:
                    allowed = max(0, remaining_wheat - reserve)
                else:
                    allowed = quantity
                order[2] = min(quantity, allowed, remaining_wheat)
                remaining_wheat -= int(order[2] or 0)
        action["market"] = [order for order in market if not (len(order) >= 3 and int(order[2] or 0) <= 0)][:10]
        return action
    if seller_mode == "net_wheat_roundtrip":
        if step < 360:
            return action
        action = copy.deepcopy(action)
        market = [list(order) for order in (action.get("market") or [])]
        sell_total = sum(max(0, int(order[2] or 0)) for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == "WHEAT")
        buy_total = sum(max(0, int(order[2] or 0)) for order in market if len(order) >= 3 and order[0] == "BUY_PRODUCT" and order[1] == "WHEAT")
        cancel = min(sell_total, buy_total)
        remaining_sell = cancel
        remaining_buy = cancel
        for order in market:
            if len(order) < 3:
                continue
            if order[0] == "SELL" and order[1] == "WHEAT" and remaining_sell > 0:
                reduction = min(max(0, int(order[2] or 0)), remaining_sell)
                order[2] = max(0, int(order[2] or 0) - reduction)
                remaining_sell -= reduction
            elif order[0] == "BUY_PRODUCT" and order[1] == "WHEAT" and remaining_buy > 0:
                reduction = min(max(0, int(order[2] or 0)), remaining_buy)
                order[2] = max(0, int(order[2] or 0) - reduction)
                remaining_buy -= reduction
        action["market"] = [order for order in market if not (len(order) >= 3 and int(order[2] or 0) <= 0)][:10]
        return action
    parameters = {
        "hold25": (0.25, 0.0),
        "hold50": (0.50, 0.0),
        "boost25": (0.0, 0.25),
        "band25": (0.25, 0.25),
    }
    single_product = {
        "boost_strawberry": "STRAWBERRY",
        "boost_melon": "MELON",
        "boost_milk": "MILK",
        "boost_wool": "WOOL",
        "boost_fertilizer": "FERTILIZER",
    }
    active_products = set(SELL_PRICE_THRESHOLDS)
    if seller_mode in single_product:
        parameters[seller_mode] = (0.0, 0.25)
        active_products = {single_product[seller_mode]}
    if seller_mode not in parameters:
        raise ValueError(seller_mode)
    hold_fraction, boost_fraction = parameters[seller_mode]
    action = copy.deepcopy(action)
    market = [list(order) for order in (action.get("market") or [])]
    prices = dict((obs.get("market") or {}).get("prices") or {})
    projected = base._projected_shed(obs, action)
    shed_total = sum(max(0, int(value or 0)) for value in projected.values())
    remaining = {item: max(0, int(value or 0)) for item, value in projected.items()}
    for order in market:
        if len(order) < 3 or order[0] != "SELL" or order[1] not in SELL_PRICE_THRESHOLDS:
            if len(order) >= 3 and order[0] == "SELL":
                remaining[str(order[1])] = max(0, remaining.get(str(order[1]), 0) - max(0, int(order[2] or 0)))
            continue
        item = str(order[1])
        if item not in active_products:
            remaining[item] = max(0, remaining.get(item, 0) - max(0, int(order[2] or 0)))
            continue
        quantity = min(max(0, int(order[2] or 0)), remaining.get(item, 0))
        price = float(prices.get(item, 0) or 0)
        threshold = SELL_PRICE_THRESHOLDS[item]
        if hold_fraction > 0 and step < SELL_HOLD_STOP_STEP and shed_total < SELL_SHED_PRESSURE and price < threshold:
            quantity = max(0, quantity - max(1, int(round(quantity * hold_fraction))))
        elif boost_fraction > 0 and price >= threshold:
            extra_room = max(0, remaining.get(item, 0) - quantity)
            quantity += min(extra_room, max(1, int(round(quantity * boost_fraction))))
        order[2] = quantity
        remaining[item] = max(0, remaining.get(item, 0) - quantity)
    action["market"] = [
        order for order in market
        if not (len(order) >= 3 and order[0] == "SELL" and int(order[2] or 0) <= 0)
    ][:10]
    return action


def make_agent(mode: str = "router", seller_mode: str = "none"):
    if mode == "parent":
        return PARENT.make_agent("router")
    switch_mode = mode.startswith("switch_") and mode.removeprefix("switch_").isdigit()
    switch_step = int(mode.removeprefix("switch_")) if switch_mode else None
    route360_mode = mode.startswith("route360_") and mode.removeprefix("route360_") in _ROUTES
    route360_expert = mode.removeprefix("route360_") if route360_mode else None
    if switch_mode and switch_step not in ROUTE_SWITCH_STEPS:
        raise ValueError(mode)
    if mode not in {"router", "broad_router", "pizza_router", "v17_overlay", *[f"single_{name}" for name in _ROUTES]} and not switch_mode and not route360_mode:
        raise ValueError(mode)
    base = PARENT._fresh_base()
    base._V17_FEED_GUARD = False
    states = {
        0: {"last": -1, "expert": None, "pending_bakery": False, "snapshots": {}, "price_history": {}, "collision_pressure": {}},
        1: {"last": -1, "expert": None, "pending_bakery": False, "snapshots": {}, "price_history": {}, "collision_pressure": {}},
    }

    def policy(obs, configuration=None):
        del configuration
        seat = PARENT._seat(obs)
        step = PARENT._step(obs)
        state = states[seat]
        if step == 0 or step < int(state.get("last", -1)):
            state.clear()
            state.update(last=step, expert=None, pending_bakery=False, snapshots={}, price_history={}, collision_pressure={})
        state["last"] = step
        if mode.startswith("single_"):
            state["expert"] = mode[len("single_"):]
        elif state.get("expert") is None and step >= ROUTER_STEP:
            shops = [str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])]
            if mode == "broad_router":
                state["expert"] = "yarn" if shops and shops[0] == "YARN_STORE" else "bakery_brunch"
            elif mode == "pizza_router":
                first_shop = shops[0] if shops else ""
                state["expert"] = "yarn" if first_shop == "YARN_STORE" else "bakery_brunch" if first_shop == "PIZZA_SHOP" else "default"
            elif mode == "v17_overlay":
                state["expert"] = "yarn" if shops and shops[0] == "YARN_STORE" else "default"
            elif switch_mode:
                state["expert"] = "yarn" if shops and shops[0] == "YARN_STORE" else "default"
            elif route360_mode:
                state["expert"] = "yarn" if shops and shops[0] == "YARN_STORE" else "default"
            else:
                state["expert"] = FIRST_SHOP_ROUTE.get(shops[0] if shops else "", "default")
                state["pending_bakery"] = bool(shops and shops[0] == "BAKERY")
        if switch_mode and state.get("expert") == "default" and step >= int(switch_step or 720):
            state["expert"] = "bakery_brunch"
        if route360_mode and state.get("expert") == "default" and step >= 360:
            state["expert"] = str(route360_expert)
        if mode == "router" and state.get("pending_bakery") and step >= 216:
            shops = tuple(str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])[:3])
            state["expert"] = "bakery_brunch" if shops == ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT") else "default"
            state["pending_bakery"] = False
        if step in STATE_SNAPSHOT_STEPS:
            state["snapshots"][step] = _public_state_snapshot(obs)
        route_name = str(state.get("expert") or "default")
        base._ACTIONS = _ROUTES[route_name]
        action = base._CORE_AGENT(obs)
        action = _commodity_sell_control(obs, action, step, base, seller_mode, state)
        action = PARENT._cap_fixed_purchases(obs, action, base)
        return PARENT._fail_closed_units(obs, action)

    policy.__name__ = f"v19_{mode}_{seller_mode}"
    policy._v19_state = states
    return policy


agent = make_agent("switch_360")
