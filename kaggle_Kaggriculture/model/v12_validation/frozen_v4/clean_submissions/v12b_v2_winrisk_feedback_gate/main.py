"""V12B observable market-feedback residual over the sealed V8 agent.

The complete V8 policy remains responsible for production, movement, safety
repairs, market ordering and terminal liquidation.  This wrapper only reduces
an already-existing EGG/MILK/WOOL SELL when *current observable evidence*
indicates that another producer has just pushed an already weak market farther
into glut.  It never adds an order, changes a route, or changes worker actions.

Serving package layout::

    main.py
    parent_agent.py  # byte-identical v8_kawa_lead2_slot/main.py

During local development the parent is loaded directly from the sibling V8
directory.  ``build_submission.py`` packages it as ``parent_agent.py``.
"""

from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
from typing import Any, Callable, Mapping


MODEL_ID = "v12b_v2_winrisk_feedback_gate"
SCHEMA = "kaggriculture-v12b-v2-winrisk-feedback-gate-1"
PARENT_MODEL = "baseline_v8"
PARENT_SHA256 = "ed2e443f6ae3683da9f34c55920bc8aa06a81e22e3b905df92389597e8adc327"

ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL")
PRODUCT_ANIMAL = {"EGG": "GOOSE", "MILK": "COW", "WOOL": "SHEEP"}
BASE_PRICE = {"EGG": 50.0, "MILK": 160.0, "WOOL": 200.0}
PRODUCT_SHOPS = {
    "EGG": frozenset({"BAKERY", "BRUNCH_SPOT"}),
    "MILK": frozenset({"PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"}),
    "WOOL": frozenset({"YARN_STORE"}),
}

# Auditable serving thresholds.  These are state gates, not fixed-day actions.
MIN_ORDER_QUANTITY = 4
WEAK_PRICE_RATIO = 0.90
SEVERE_PRICE_RATIO = 0.75
MIN_GLUT = 20
SEVERE_GLUT = 80
MIN_OPPONENT_SUPPLY_LOWER_BOUND = 2
SEVERE_INVENTORY_FLOW = 8
MAX_HELD_PER_ORDER = 8
SOFT_HOLD_FRACTION = 0.25
SEVERE_HOLD_FRACTION = 0.50
MAX_SHED_FILL = 0.70
MAX_TOTAL_PRIVATE_STOCK = 88
# V8 owns its final liquidation.  The feedback residual is completely bypassed
# for the last two in-game days so it cannot strand stock at season end.
TERMINAL_BYPASS_STEP = 672


def _load_parent():
    try:
        import parent_agent as module  # type: ignore

        return module
    except ImportError:
        path = Path(__file__).resolve().parents[1] / "v8_kawa_lead2_slot" / "main.py"
        spec = importlib.util.spec_from_file_location("_v12b_local_v8_parent", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load sealed V8 parent: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


_PARENT = _load_parent()


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _seat(obs: Any) -> int:
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _step(obs: Any) -> int:
    explicit = _get(obs, "step")
    if explicit is not None:
        return int(explicit or 0)
    return int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)


def _copy_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    source = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (source.get("hands") or [])],
        "market": [list(order or []) for order in (source.get("market") or [])],
    }


def _market_snapshot(obs: Any) -> dict[str, tuple[float, float]]:
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    inventory = _get(market, "inventory", {}) or {}
    result = {}
    for item in ANIMAL_PRODUCTS:
        raw_price = _get(prices, item, None)
        raw_inventory = _get(inventory, item, None)
        result[item] = (
            BASE_PRICE[item] if raw_price is None else float(raw_price),
            10000.0 if raw_inventory is None else float(raw_inventory),
        )
    return result


def _animal_counts(farm: Any) -> dict[str, int]:
    counts = {animal: 0 for animal in PRODUCT_ANIMAL.values()}
    for row in list(_get(farm, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, Mapping):
                continue
            animal = str(tile.get("animal") or "")
            if animal in counts:
                counts[animal] += 1
    return counts


def _production_context(obs: Any) -> tuple[dict[str, int], dict[str, int]]:
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    if len(farms) != 2:
        return ({animal: 0 for animal in PRODUCT_ANIMAL.values()},) * 2
    return _animal_counts(farms[seat]), _animal_counts(farms[1 - seat])


def _private_pressure(obs: Any) -> tuple[float, int]:
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    shed_total = sum(max(0, int(value or 0)) for value in dict(shed).values())
    inventories = list(_get(private, "inventories", []) or [])
    carried = sum(
        max(0, int(value or 0))
        for inventory in inventories
        for value in dict(inventory or {}).values()
    )
    return shed_total / 100.0, shed_total + carried


def _public_bank_context(obs: Any) -> tuple[float, float, float, str]:
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    if len(farms) != 2:
        return 0.0, 0.0, 0.0, "unknown"
    own = float(_get(farms[seat], "money", 0) or 0)
    opponent = float(_get(farms[1 - seat], "money", 0) or 0)
    margin = own - opponent
    state = "ahead" if margin > 0 else "behind" if margin < 0 else "tied"
    return own, opponent, margin, state


def _has_recovery_demand(obs: Any, item: str) -> bool:
    town = _get(obs, "town", {}) or {}
    shops = {str(value) for value in (_get(town, "unlocked_shops", []) or [])}
    return bool(shops.intersection(PRODUCT_SHOPS[item]))


def _recovery_demand_per_day(obs: Any, item: str) -> float:
    """Drain rate from current shop instances plus the daily town centre."""
    town = _get(obs, "town", {}) or {}
    shops = [str(value) for value in (_get(town, "unlocked_shops", []) or [])]
    per_day = 1.0
    for shop in shops:
        if shop in PRODUCT_SHOPS[item]:
            # YARN_STORE is a single-product shop, so each tick consumes two.
            per_day += 12.0 if shop == "YARN_STORE" else 6.0
    return per_day


def _town_drain_for_step(obs: Any, step: int) -> dict[str, int]:
    town = _get(obs, "town", {}) or {}
    shops = [str(value) for value in (_get(town, "unlocked_shops", []) or [])]
    drain = {item: int(step % 24 == 0) for item in ANIMAL_PRODUCTS}
    if step % 4 == 0:
        for item in ANIMAL_PRODUCTS:
            for shop in shops:
                if shop in PRODUCT_SHOPS[item]:
                    drain[item] += 2 if shop == "YARN_STORE" else 1
    return drain


def _planned_sales(action: Mapping[str, Any]) -> dict[str, int]:
    result = {item: 0 for item in ANIMAL_PRODUCTS}
    for order in list(action.get("market") or []):
        if not isinstance(order, (list, tuple)) or len(order) < 3:
            continue
        if order[0] != "SELL" or str(order[1]) not in result:
            continue
        try:
            result[str(order[1])] += max(0, int(order[2] or 0))
        except (TypeError, ValueError):
            continue
    return result


def _transition_context(obs: Any, action: Mapping[str, Any]) -> dict[str, Any]:
    step = _step(obs)
    return {
        "step": step,
        "snapshot": _market_snapshot(obs),
        # Planned sales upper-bound our actual non-floor sales.  Subtracting
        # them therefore produces a conservative opponent-supply lower bound.
        "own_planned_sales": _planned_sales(action),
        "town_drain": _town_drain_for_step(obs, step),
    }


def _new_state() -> dict[str, Any]:
    return {"last_step": -1, "transition": None}


def feedback_decision(
    obs: Any,
    item: str,
    quantity: int,
    previous: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a fully auditable decision for one existing animal-product SELL."""

    result: dict[str, Any] = {
        "item": item,
        "original_quantity": int(quantity),
        "new_quantity": int(quantity),
        "triggered": False,
        "reason": "pass",
        "severity": "none",
    }
    step = _step(obs)
    if item not in ANIMAL_PRODUCTS or quantity < MIN_ORDER_QUANTITY:
        result["reason"] = "not_eligible_order"
        return result
    if step >= TERMINAL_BYPASS_STEP:
        result["reason"] = "terminal_bypass"
        return result
    previous_snapshot = _get(previous, "snapshot", {}) if previous is not None else {}
    if not isinstance(previous_snapshot, Mapping) or item not in previous_snapshot:
        result["reason"] = "no_lagged_observation"
        return result

    own_bank, opponent_bank, bank_margin, bank_state = _public_bank_context(obs)
    result.update(
        own_public_bank=own_bank,
        opponent_public_bank=opponent_bank,
        public_bank_margin=bank_margin,
        public_bank_state=bank_state,
    )
    shed_fill, total_private = _private_pressure(obs)
    result.update(shed_fill=shed_fill, total_private_stock=total_private)
    if shed_fill >= MAX_SHED_FILL or total_private >= MAX_TOTAL_PRIVATE_STOCK:
        result["reason"] = "warehouse_pressure_bypass"
        return result
    if not _has_recovery_demand(obs, item):
        result["reason"] = "no_product_specific_recovery_demand"
        return result

    snapshot = _market_snapshot(obs)
    price, inventory = snapshot[item]
    previous_price, previous_inventory = previous_snapshot[item]
    base = BASE_PRICE[item]
    price_ratio = price / base
    glut = inventory - 10000.0
    inventory_flow = inventory - previous_inventory
    price_drop_ratio = (previous_price - price) / base
    floor_risk = price <= 1.0 or previous_price <= 1.0
    result["floor_risk"] = floor_risk
    if floor_risk:
        # At the price floor successful sales no longer increase public market
        # inventory.  The opponent-flow estimator is then non-identifiable.
        result["reason"] = "floor_risk_uncertainty_bypass"
        return result

    own_planned = int(_get(_get(previous, "own_planned_sales", {}) or {}, item, 0) or 0)
    town_drain = int(_get(_get(previous, "town_drain", {}) or {}, item, 0) or 0)
    opponent_supply_lower_bound = inventory_flow + town_drain - own_planned
    own, opponent = _production_context(obs)
    animal = PRODUCT_ANIMAL[item]
    own_capacity = own[animal]
    opponent_capacity = opponent[animal]
    rival_supply = opponent_capacity >= max(2, own_capacity)
    fresh_shock = opponent_supply_lower_bound >= MIN_OPPONENT_SUPPLY_LOWER_BOUND
    weak_market = price_ratio <= WEAK_PRICE_RATIO and glut >= MIN_GLUT
    recovery_demand = _recovery_demand_per_day(obs, item)
    recovery_days = max(0.0, glut) / max(1.0, recovery_demand)
    remaining_days = max(0.0, (720 - step) / 24.0)
    recoverable_before_terminal = recovery_days <= max(0.0, remaining_days - 2.0)
    result.update(
        price_ratio=price_ratio,
        glut=glut,
        inventory_flow=inventory_flow,
        price_drop_ratio=price_drop_ratio,
        own_planned_previous_sale=own_planned,
        deterministic_town_drain=town_drain,
        opponent_supply_lower_bound=opponent_supply_lower_bound,
        opponent_supply_upper_bound=None,
        estimator_uncertainty="upper_bound_unidentifiable",
        own_capacity=own_capacity,
        opponent_capacity=opponent_capacity,
        weak_market=weak_market,
        fresh_shock=fresh_shock,
        rival_supply=rival_supply,
        recovery_demand_per_day=recovery_demand,
        recovery_days=recovery_days,
        remaining_days=remaining_days,
        recoverable_before_terminal=recoverable_before_terminal,
    )
    if not weak_market:
        result["reason"] = "market_not_weak"
        return result
    if not fresh_shock:
        result["reason"] = "no_positive_opponent_supply_lower_bound"
        return result
    if not rival_supply:
        result["reason"] = "no_visible_rival_supply"
        return result
    if not recoverable_before_terminal:
        result["reason"] = "glut_not_recoverable_before_terminal"
        return result
    if bank_margin > 0:
        # Win-probability guard: count a bypass only after every original
        # feedback qualification has passed.  This means the audit counter is
        # the number of real v1 proposals suppressed, not merely the number of
        # eligible SELL orders seen while leading.  Zero is the objective's
        # sign boundary, not a replay-fitted threshold.
        result["reason"] = "public_lead_protection_bypass"
        return result

    severe = price_ratio <= SEVERE_PRICE_RATIO or (
        glut >= SEVERE_GLUT and inventory_flow >= SEVERE_INVENTORY_FLOW
    )
    fraction = SEVERE_HOLD_FRACTION if severe else SOFT_HOLD_FRACTION
    held = min(MAX_HELD_PER_ORDER, max(1, int(math.ceil(quantity * fraction))))
    new_quantity = max(1, quantity - held)
    result.update(
        new_quantity=new_quantity,
        held_quantity=quantity - new_quantity,
        triggered=new_quantity < quantity,
        reason="observable_collision_pressure",
        severity="severe" if severe else "soft",
    )
    return result


class MarketFeedbackPolicy:
    """Episode-local wrapper with one-step public-market memory per seat."""

    def __init__(self, parent: Callable[..., Mapping[str, Any]]) -> None:
        self.parent = parent
        self.states = {0: _new_state(), 1: _new_state()}
        self.calls = 0
        self.trigger_count = 0
        self.held_quantity = 0
        self.last_events: list[dict[str, Any]] = []
        self.trigger_history: list[dict[str, Any]] = []
        self.trigger_by_product = {item: 0 for item in ANIMAL_PRODUCTS}
        self.trigger_by_bank_state = {
            item: 0 for item in ("ahead", "tied", "behind", "unknown")
        }
        self.lead_protection_bypasses = 0
        self.errors: list[str] = []

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, Any]:
        try:
            parent_action = self.parent(obs, configuration)
        except TypeError:
            parent_action = self.parent(obs)
        self.calls += 1
        untouched = _copy_action(parent_action)
        try:
            seat = _seat(obs)
            step = _step(obs)
            state = self.states[seat]
            if step == 0 or step <= int(state.get("last_step", -1)):
                state = _new_state()
                self.states[seat] = state
            previous = state.get("transition")

            result = _copy_action(parent_action)
            events: list[dict[str, Any]] = []
            market: list[list[Any]] = []
            for raw in result["market"]:
                order = list(raw)
                if len(order) >= 3 and order[0] == "SELL" and str(order[1]) in ANIMAL_PRODUCTS:
                    try:
                        quantity = max(0, int(order[2] or 0))
                    except (TypeError, ValueError):
                        market.append(order)
                        continue
                    decision = feedback_decision(obs, str(order[1]), quantity, previous)
                    events.append(decision)
                    if decision.get("reason") == "public_lead_protection_bypass":
                        self.lead_protection_bypasses += 1
                    if decision["triggered"]:
                        order[2] = int(decision["new_quantity"])
                        self.trigger_count += 1
                        self.held_quantity += int(decision["held_quantity"])
                        product = str(decision["item"])
                        bank_state = str(decision.get("public_bank_state") or "unknown")
                        self.trigger_by_product[product] += 1
                        self.trigger_by_bank_state[bank_state] += 1
                        self.trigger_history.append(
                            {
                                "step": step,
                                "item": product,
                                "pre_money_gap": float(decision.get("public_bank_margin", 0.0)),
                                "bank_state": bank_state,
                                "original_quantity": int(decision["original_quantity"]),
                                "new_quantity": int(decision["new_quantity"]),
                                "held_quantity": int(decision["held_quantity"]),
                            }
                        )
                        self.trigger_history = self.trigger_history[-64:]
                market.append(order)
            result["market"] = market[:10]
            state["transition"] = _transition_context(obs, result)
            state["last_step"] = step
            self.last_events = events
            return result
        except Exception as exc:
            # Residual failures never suppress the verified parent action.
            self.errors.append(f"step={_step(obs)}:{type(exc).__name__}:{exc}")
            self.last_events = []
            return untouched

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "model_id": MODEL_ID,
            "parent_model": PARENT_MODEL,
            "parent_sha256": PARENT_SHA256,
            "calls": self.calls,
            "trigger_count": self.trigger_count,
            "held_quantity": self.held_quantity,
            "trigger_by_product": dict(self.trigger_by_product),
            "trigger_by_bank_state": dict(self.trigger_by_bank_state),
            "trigger_history": copy.deepcopy(self.trigger_history),
            "lead_protection_bypasses": self.lead_protection_bypasses,
            "last_events": copy.deepcopy(self.last_events),
            "errors": list(self.errors),
            "gates": {
                "eligible_products": list(ANIMAL_PRODUCTS),
                "weak_price_ratio": WEAK_PRICE_RATIO,
                "min_glut": MIN_GLUT,
                "min_opponent_supply_lower_bound": MIN_OPPONENT_SUPPLY_LOWER_BOUND,
                "severe_inventory_flow": SEVERE_INVENTORY_FLOW,
                "rival_supply": "opponent_capacity >= max(2, own_capacity)",
                "max_shed_fill": MAX_SHED_FILL,
                "max_total_private_stock": MAX_TOTAL_PRIVATE_STOCK,
                "terminal_bypass_step": TERMINAL_BYPASS_STEP,
                "requires_product_specific_shop": True,
                "requires_recovery_before_terminal": True,
                "floor_price": "uncertainty_bypass_not_hold_signal",
                "winrisk_gate": "feedback allowed only when own public bank <= opponent public bank",
            },
        }


_POLICY = MarketFeedbackPolicy(_PARENT.agent)


def agent(obs: Any, configuration: Any = None) -> dict[str, Any]:
    return _POLICY(obs, configuration)


def model_status() -> dict[str, Any]:
    return _POLICY.diagnostics()
