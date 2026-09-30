#!/usr/bin/env python3
"""Market-only one-step MPC wrapper around frozen V17 RC1.

The wrapper never edits ``farmer`` or ``hands``.  It may defer a safe subset
of an existing SELL queue from a town-drain turn to the immediately following
turn.  The deferred SELL is inserted first, so an opponent's simultaneous
slot-0 sale receives the same pre-commit quote and cannot pre-empt it.

Only public town/market/farm state and our own private state are used.  The
opponent's shed and carried inventory are neither available nor inferred.
"""

from __future__ import annotations

import copy
import importlib.util
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
V17 = RESEARCH / "top_complete_portfolio" / "main.py"
EXPECTED_V17_SHA256 = "b52e62545fb6bdc93f9e947f9a829e348dd6119ee9daf7d8eba7df9aec29a4b1"

SAFE_PRODUCTS = {"CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"}
SHOP_PRODUCTS = {
    "BAKERY": {"WHEAT": 1, "EGG": 1},
    "BRUNCH_SPOT": {"WHEAT": 1, "EGG": 1, "STRAWBERRY": 1},
    "FARMERS_MARKET": {"WHEAT": 1, "CARROT": 1, "TOMATO": 1, "STRAWBERRY": 1},
    "ICE_CREAM_SHOP": {"WHEAT": 1, "STRAWBERRY": 1, "MILK": 1},
    "PET_CAFE": {"CARROT": 2},
    "PIZZA_SHOP": {"WHEAT": 1, "TOMATO": 1, "MILK": 1},
    "SMOOTHIE_SHOP": {"STRAWBERRY": 1, "MILK": 1},
    "YARN_STORE": {"WOOL": 2},
}
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND_COST = (1000, 2000, 4000)


def _load_v17():
    name = f"frozen_v17_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, V17)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _step(obs: dict) -> int:
    if obs.get("step") is not None:
        return int(obs.get("step") or 0)
    return int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)


def _seat(obs: dict) -> int:
    return 1 if int(obs.get("player", 0) or 0) == 1 else 0


def _fib(index: int) -> int:
    a, b = 0, 1
    for _ in range(max(0, index)):
        a, b = b, a + b
    return a


def _fixed_spend_upper_bound(obs: dict, action: dict, price_fn=None) -> int | None:
    """Return a conservative current-turn spend, or None when not bounded.

    BUY_PRODUCT assumes the opponent spends its entire 100-unit shed capacity
    buying the same product before us.  This is intentionally much harsher
    than most legal states, but guarantees that removing an unrelated product
    sale does not finance our planned WHEAT/FERTILIZER purchase.
    """
    farm = obs["farms"][_seat(obs)]
    hires = int(farm.get("hires_today", 0) or 0)
    quadrants = len(farm.get("unlocked_quadrants", []) or [])
    spend = 0
    product_bought: dict[str, int] = {}
    market_inventory = dict((obs.get("market") or {}).get("inventory") or {})
    for order in action.get("market") or []:
        if not order:
            continue
        op = str(order[0])
        if op == "BUY_PRODUCT":
            if price_fn is None or len(order) < 3:
                return None
            item = str(order[1])
            quantity = max(0, int(order[2] or 0))
            already = product_bought.get(item, 0)
            start = int(market_inventory.get(item, 0) or 0) - 100 - already
            for offset in range(quantity):
                spend += int(price_fn(item, start - offset - 1))
            product_bought[item] = already + quantity
        if op == "HIRE":
            spend += _fib(hires)
            hires += 1
        elif op == "BUY_LAND":
            extra = quadrants - 1
            if not 0 <= extra < len(LAND_COST):
                return None
            spend += LAND_COST[extra]
            quadrants += 1
        elif op == "BUY_SEED" and len(order) >= 3:
            if str(order[1]) not in SEED_COST:
                return None
            spend += SEED_COST[str(order[1])] * max(0, int(order[2] or 0))
        elif op == "BUY_ANIMAL" and len(order) >= 3:
            if str(order[1]) not in ANIMAL_COST:
                return None
            spend += ANIMAL_COST[str(order[1])] * max(0, int(order[2] or 0))
    return spend


def _town_drain(obs: dict, item: str, step: int) -> int:
    if step % 4 != 0:
        return 0
    drain = 1 if step % 24 == 0 and item != "FERTILIZER" else 0
    for shop in list((obs.get("town") or {}).get("unlocked_shops") or []):
        drain += SHOP_PRODUCTS.get(str(shop), {}).get(item, 0)
    return drain


def _pickup_reserve(action: dict, item: str) -> int:
    reserve = 0
    for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]:
        if order and order[0] == "PICKUP" and len(order) >= 2 and str(order[1]) == item:
            reserve += max(1, int(order[2] or 1)) if len(order) >= 3 else 1
    return reserve


def _has_shed_unit_action(action: dict) -> bool:
    return any(
        order and str(order[0]) in {"PICKUP", "DROP", "PLACE"}
        for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    )


def _merge_front(market: list[list], due: dict[str, int]) -> list[list]:
    """Insert due sales first, merging same-product sales without truncation."""
    remaining = {item: max(0, int(qty)) for item, qty in due.items() if int(qty) > 0}
    out: list[list] = []
    for item in sorted(remaining):
        quantity = remaining[item]
        for order in market:
            if order and order[0] == "SELL" and len(order) >= 3 and str(order[1]) == item:
                quantity += max(0, int(order[2] or 0))
                order[2] = 0
        out.append(["SELL", item, quantity])
    out.extend(order for order in market if not (order and order[0] == "SELL" and len(order) >= 3 and int(order[2] or 0) <= 0))
    return out[:10]


def make_agent(
    *,
    lead_ceiling: int = 5000,
    quantity_cap: int = 20,
    shed_ceiling: int = 80,
    cash_floor: int = 3000,
    min_step: int = 72,
    max_step: int = 708,
):
    """Create a fresh causal policy.

    ``lead_ceiling`` is the public-money advantage above which V17 is kept
    unchanged.  This is the win-protection gate: only trailing/close games
    take the one-step liquidity and room risk.
    """
    v17 = _load_v17()
    parent = v17.agent
    price_fn = v17._market_price
    state = {
        0: {"last": -1, "due_step": -1, "due": {}},
        1: {"last": -1, "due_step": -1, "due": {}},
    }
    stats = {
        "changed_turns": 0,
        "deferred_units": 0,
        "repaid_turns": 0,
        "expired_due_units": 0,
    }

    def policy(obs, configuration=None):
        action = parent(obs, configuration)
        # Preserve exact objects semantically, then mutate market only.
        farmer = copy.deepcopy(action.get("farmer"))
        hands = copy.deepcopy(action.get("hands"))
        action = copy.deepcopy(action)
        action["market"] = [list(order) for order in (action.get("market") or [])][:10]
        seat = _seat(obs)
        step = _step(obs)
        local = state[seat]
        if step == 0 or step < int(local["last"]):
            local.update(last=step, due_step=-1, due={})
        local["last"] = step

        # A due sale is fail-closed at exactly t+1.  It is capped to inventory
        # remaining after this turn's PICKUP, because unit actions resolve first.
        if int(local["due_step"]) == step:
            shed = dict((obs.get("private") or {}).get("shed") or {})
            executable = {}
            for item, quantity in dict(local["due"]).items():
                available = max(0, int(shed.get(item, 0) or 0) - _pickup_reserve(action, item))
                sold = min(max(0, int(quantity)), available)
                if sold > 0:
                    executable[item] = sold
                stats["expired_due_units"] += max(0, int(quantity) - sold)
            if executable:
                action["market"] = _merge_front(action["market"], executable)
                stats["repaid_turns"] += 1
            local.update(due_step=-1, due={})

        farms = list(obs.get("farms") or [{}, {}])
        own = farms[seat] if len(farms) > seat else {}
        rival = farms[1 - seat] if len(farms) > 1 else {}
        money_lead = int(own.get("money", 0) or 0) - int(rival.get("money", 0) or 0)
        spend = _fixed_spend_upper_bound(obs, action, price_fn)
        shed = dict((obs.get("private") or {}).get("shed") or {})
        shed_total = sum(max(0, int(value or 0)) for value in shed.values())
        can_plan = (
            int(local["due_step"]) < 0
            and min_step <= step <= max_step
            and money_lead <= lead_ceiling
            and spend is not None
            and int(own.get("money", 0) or 0) >= int(spend) + cash_floor
            and shed_total <= shed_ceiling
            and len(action["market"]) < 10
            and not _has_shed_unit_action(action)
            and step + 1 < len(v17._ACTIONS)
            and not _has_shed_unit_action(v17._ACTIONS[step + 1] or {})
        )
        if can_plan:
            due: dict[str, int] = {}
            kept: list[list] = []
            remaining = {item: max(0, int(value or 0)) for item, value in shed.items()}
            for order in action["market"]:
                if not (order and order[0] == "SELL" and len(order) >= 3 and str(order[1]) in SAFE_PRODUCTS):
                    kept.append(order)
                    continue
                item = str(order[1])
                quantity = max(0, int(order[2] or 0))
                executable = min(quantity, remaining.get(item, 0))
                remaining[item] = max(0, remaining.get(item, 0) - executable)
                drain = _town_drain(obs, item, step)
                # A small tranche bounds next-turn room/liquidity exposure.
                move = min(executable, quantity_cap) if drain > 0 else 0
                if move > 0:
                    due[item] = due.get(item, 0) + move
                if quantity - move > 0:
                    kept.append(["SELL", item, quantity - move])
            if due:
                action["market"] = kept[:10]
                local.update(due_step=step + 1, due=due)
                stats["changed_turns"] += 1
                stats["deferred_units"] += sum(due.values())

        assert action.get("farmer") == farmer
        assert action.get("hands") == hands
        return action

    policy.__name__ = "v18_market_only_mpc"
    policy.market_mpc_stats = stats
    policy.market_mpc_config = {
        "lead_ceiling": lead_ceiling,
        "quantity_cap": quantity_cap,
        "shed_ceiling": shed_ceiling,
        "cash_floor": cash_floor,
        "min_step": min_step,
        "max_step": max_step,
    }
    return policy


agent = make_agent()
