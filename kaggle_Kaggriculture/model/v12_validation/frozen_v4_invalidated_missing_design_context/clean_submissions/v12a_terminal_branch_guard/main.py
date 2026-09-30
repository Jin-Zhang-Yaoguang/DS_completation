"""Kaggriculture V12A: r002 branch guard plus terminal clearance safety net.

The production route is still owned by V10's frozen learned full-expert
router.  This module reproduces r002's top-day animal-product throttle, but
activates it only for the V5/V8 router branches and only when the resulting
shed occupancy is safe.  The final actionable turn (step 718; the agent is
called on steps 0--718) may fill otherwise unused market slots with saleable
stock omitted by the parent.

No rule in this module withholds a sale because of a price floor.  Farmer and
farm-hand actions are copied byte-for-byte from the parent policy.
"""

from __future__ import annotations

from collections import Counter
import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
V11 = MODEL_ROOT / "v11_iterative_league"
SOURCE_REGISTRY = V11 / "runs" / "round_002" / "strategy" / "registry_next.json"

MODEL_ID = "v12a_terminal_branch_guard"
PARENT_ID = "r002_learned_router_topday_animal_throttle"
ROUTER_PARENT_ID = "learned_router"
TOP_DAYS = frozenset({10, 17, 24})
THROTTLED_BRANCHES = frozenset({"baseline_v5", "baseline_v8"})
ANIMAL_PRODUCTS = frozenset({"EGG", "MILK", "WOOL"})
SHOP_PRODUCTS = {
    "BAKERY": frozenset({"EGG", "WHEAT"}),
    "PIZZA_SHOP": frozenset({"MILK", "TOMATO", "WHEAT"}),
    "BRUNCH_SPOT": frozenset({"EGG", "WHEAT", "STRAWBERRY"}),
    "YARN_STORE": frozenset({"WOOL"}),
    "ICE_CREAM_SHOP": frozenset({"STRAWBERRY", "MILK", "WHEAT"}),
    "PET_CAFE": frozenset({"CARROT"}),
    "SMOOTHIE_SHOP": frozenset({"STRAWBERRY", "MILK"}),
    "FARMERS_MARKET": frozenset(
        {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY"}
    ),
}
SELLABLE_PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
)

DEFAULT_CONFIG = {
    "top_days": sorted(TOP_DAYS),
    "throttled_branches": sorted(THROTTLED_BRANCHES),
    "fraction": 0.5,
    "require_unlocked_shop_demand": True,
    "minimum_animal_sell": 4,
    "maximum_post_sale_shed": 90,
    "terminal_start_step": 718,
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs: Any) -> int:
    return int(_get(obs, "step", 0) or 0)


def _day(obs: Any) -> int:
    explicit = _get(obs, "day")
    return int(explicit if explicit is not None else _step(obs) // 24)


def _canonical_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    source = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in (source.get("hands") or [])],
        "market": [list(item) for item in (source.get("market") or [])],
    }


def _shed(obs: Any) -> dict[str, int]:
    private = _get(obs, "private", {}) or {}
    raw = _get(private, "shed", {}) or {}
    return {
        str(product): max(0, int(quantity or 0))
        for product, quantity in dict(raw).items()
    }


def _has_drop(action: Mapping[str, Any]) -> bool:
    unit_actions = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    return any(item and str(item[0]) in {"DROP", "PLACE"} for item in unit_actions)


def _unlocked_shops(obs: Any) -> tuple[str, ...]:
    town = _get(obs, "town", {}) or {}
    return tuple(str(item) for item in (_get(town, "unlocked_shops", []) or []))


def _shop_demand_products(obs: Any) -> frozenset[str]:
    products: set[str] = set()
    for shop in _unlocked_shops(obs):
        products.update(SHOP_PRODUCTS.get(shop, ()))
    return frozenset(products)


def _animal_sell_total(
    action: Mapping[str, Any], products: frozenset[str] = ANIMAL_PRODUCTS
) -> int:
    return sum(
        max(0, int(order[2] or 0))
        for order in action.get("market", [])
        if len(order) >= 3
        and str(order[0]) == "SELL"
        and str(order[1]) in products
    )


def _post_sale_shed(
    obs: Any,
    action: Mapping[str, Any],
    fraction: float,
    throttled_products: frozenset[str] = ANIMAL_PRODUCTS,
) -> int:
    """Conservative shed occupancy after the throttled existing SELLs.

    Same-turn DROP/PLACE is rejected by the caller because exact execution
    ordering and quantity depend on unit positions.  Existing SELL quantities
    are capped by current per-product stock so malformed/over-sized parent
    requests cannot make the guard look safer than it is.
    """

    shed = _shed(obs)
    planned: Counter[str] = Counter()
    for order in action.get("market", []):
        if (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and str(order[1]) in throttled_products
        ):
            quantity = max(0, int(order[2] or 0))
            planned[str(order[1])] += max(0, int(round(quantity * fraction)))
        elif len(order) >= 3 and str(order[0]) == "SELL":
            planned[str(order[1])] += max(0, int(order[2] or 0))
    sold = sum(min(shed.get(product, 0), quantity) for product, quantity in planned.items())
    return max(0, sum(shed.values()) - sold)


def _apply_topday_throttle(
    action: Mapping[str, Any],
    fraction: float,
    products: frozenset[str] = ANIMAL_PRODUCTS,
) -> dict[str, list[Any]]:
    """Exact r002 quantity transform for an already-approved trigger."""

    result = _canonical_action(action)
    market: list[list[Any]] = []
    fraction = min(1.0, max(0.0, float(fraction)))
    for order in result["market"]:
        if (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and str(order[1]) in products
        ):
            order[2] = int(round(max(0, int(order[2] or 0)) * fraction))
            if int(order[2]) <= 0:
                continue
        market.append(order)
    result["market"] = market[:10]
    return result


def _terminal_clearance_fill(
    action: Mapping[str, Any], obs: Any, start_step: int
) -> tuple[dict[str, list[Any]], int, int]:
    """Use empty final slots for shed stock not already sold by the parent."""

    result = _canonical_action(action)
    if _step(obs) < int(start_step):
        return result, 0, 0
    shed = _shed(obs)
    already: Counter[str] = Counter()
    for order in result["market"]:
        if len(order) >= 3 and str(order[0]) == "SELL":
            already[str(order[1])] += max(0, int(order[2] or 0))
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    candidates: list[tuple[float, str, int]] = []
    for product in SELLABLE_PRODUCTS:
        remaining = max(0, shed.get(product, 0) - already.get(product, 0))
        if remaining:
            value = float(_get(prices, product, 0.0) or 0.0) * remaining
            candidates.append((value, product, remaining))
    candidates.sort(key=lambda row: (row[0], row[2], row[1]), reverse=True)
    added_orders = 0
    added_quantity = 0
    for _, product, quantity in candidates:
        if len(result["market"]) >= 10:
            break
        result["market"].append(["SELL", product, quantity])
        added_orders += 1
        added_quantity += quantity
    return result, added_orders, added_quantity


def _load_router_from_bundle() -> Any:
    runtime = HERE / "runtime"
    policy_path = runtime / "policy.json"
    if not policy_path.is_file():
        return None
    sys.path.insert(0, str(runtime))
    try:
        import fast_router  # type: ignore

        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        return fast_router.create_agent(
            policy["router_spec"],
            policy["expert_specs"],
            str(runtime),
        )
    finally:
        sys.path.pop(0)


def _load_router_from_repository() -> Any:
    from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
        create_agent as create_registered_agent,
        load_registry,
    )

    registry = load_registry(SOURCE_REGISTRY)
    return create_registered_agent(registry, ROUTER_PARENT_ID)


def _load_learned_router() -> Any:
    bundled = _load_router_from_bundle()
    return bundled if bundled is not None else _load_router_from_repository()


def _parent_diagnostics(parent: Any) -> dict[str, Any]:
    method = getattr(parent, "diagnostics", None)
    return dict(method()) if callable(method) else {}


class BranchGuardAgent:
    """Episode-local r002 descendant with branch and storage guards."""

    def __init__(
        self,
        *,
        enable_guard: bool = True,
        enable_terminal: bool = True,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        self.config = dict(DEFAULT_CONFIG)
        self.config.update(dict(config or {}))
        self.enable_guard = bool(enable_guard)
        self.enable_terminal = bool(enable_terminal)
        self.parent = _load_learned_router()
        self._reset()

    def _reset(self) -> None:
        self.last_step = -1
        self.calls = 0
        self.changed_steps = 0
        self.throttle_steps = 0
        self.terminal_fill_steps = 0
        self.terminal_added_orders = 0
        self.terminal_added_quantity = 0
        self.residual_fallbacks = 0
        self.branch_counts: Counter[str] = Counter()
        self.skip_reasons: Counter[str] = Counter()
        self.throttled_product_steps: Counter[str] = Counter()

    def _selected_branch(self) -> str | None:
        diagnostics = _parent_diagnostics(self.parent)
        selected = diagnostics.get("selected")
        if selected:
            return str(selected)
        nested = diagnostics.get("parent_diagnostics")
        while isinstance(nested, Mapping):
            if nested.get("selected"):
                return str(nested["selected"])
            nested = nested.get("parent_diagnostics")
        return None

    def _should_throttle(
        self, obs: Any, action: Mapping[str, Any], branch: str | None
    ) -> tuple[bool, str, frozenset[str]]:
        if _day(obs) not in {int(value) for value in self.config["top_days"]}:
            return False, "not_top_day", frozenset()
        if not self.enable_guard:
            return True, "unguarded_r002_reproduction", ANIMAL_PRODUCTS
        if branch not in {str(value) for value in self.config["throttled_branches"]}:
            return False, "non_v5_v8_branch", frozenset()
        products = ANIMAL_PRODUCTS
        if bool(self.config.get("require_unlocked_shop_demand", True)):
            products = frozenset(ANIMAL_PRODUCTS & _shop_demand_products(obs))
            if not products:
                return False, "no_unlocked_animal_shop_demand", frozenset()
        if _has_drop(action):
            return False, "same_turn_shed_deposit", frozenset()
        total = _animal_sell_total(action, products)
        if total < int(self.config["minimum_animal_sell"]):
            return False, "small_animal_sale", frozenset()
        projected = _post_sale_shed(
            obs,
            action,
            float(self.config["fraction"]),
            products,
        )
        if projected > int(self.config["maximum_post_sale_shed"]):
            return False, "shed_headroom_guard", frozenset()
        return True, "branch_shop_demand_and_shed_safe", products

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
        step = _step(obs)
        if step == 0 or step < self.last_step:
            self._reset()
        self.last_step = step
        self.calls += 1
        parent_action = _canonical_action(self.parent(obs, configuration))
        branch = self._selected_branch()
        self.branch_counts[branch or "unselected"] += 1
        result = parent_action
        try:
            throttle, reason, products = self._should_throttle(obs, result, branch)
            self.skip_reasons[reason] += 1
            if throttle:
                before_throttle = result
                result = _apply_topday_throttle(
                    result, float(self.config["fraction"]), products
                )
                if result != parent_action:
                    self.throttle_steps += 1
                    before_quantities: Counter[str] = Counter()
                    after_quantities: Counter[str] = Counter()
                    for raw in before_throttle["market"]:
                        if len(raw) >= 3 and str(raw[0]) == "SELL":
                            before_quantities[str(raw[1])] += max(0, int(raw[2] or 0))
                    for raw in result["market"]:
                        if len(raw) >= 3 and str(raw[0]) == "SELL":
                            after_quantities[str(raw[1])] += max(0, int(raw[2] or 0))
                    for product in products:
                        if after_quantities[product] != before_quantities[product]:
                            self.throttled_product_steps[product] += 1
            if self.enable_terminal:
                result, orders, quantity = _terminal_clearance_fill(
                    result, obs, int(self.config["terminal_start_step"])
                )
                if orders:
                    self.terminal_fill_steps += 1
                    self.terminal_added_orders += orders
                    self.terminal_added_quantity += quantity
            if result["farmer"] != parent_action["farmer"]:
                raise AssertionError("residual changed farmer action")
            if result["hands"] != parent_action["hands"]:
                raise AssertionError("residual changed farm-hand actions")
            if len(result["market"]) > 10:
                raise AssertionError("residual emitted more than ten market orders")
        except Exception:
            self.residual_fallbacks += 1
            return parent_action
        if result != parent_action:
            self.changed_steps += 1
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {
            "kind": "v12a_r002_branch_guard_terminal_fill",
            "model_id": MODEL_ID,
            "parent_id": PARENT_ID,
            "router_parent_id": ROUTER_PARENT_ID,
            "calls": self.calls,
            "changed_steps": self.changed_steps,
            "throttle_steps": self.throttle_steps,
            "terminal_fill_steps": self.terminal_fill_steps,
            "terminal_added_orders": self.terminal_added_orders,
            "terminal_added_quantity": self.terminal_added_quantity,
            "residual_fallbacks": self.residual_fallbacks,
            "branch_counts": dict(self.branch_counts),
            "skip_reasons": dict(self.skip_reasons),
            "throttled_product_steps": dict(self.throttled_product_steps),
            "config": copy.deepcopy(self.config),
            "parent_diagnostics": _parent_diagnostics(self.parent),
        }


def make_agent(
    *,
    enable_guard: bool = True,
    enable_terminal: bool = True,
    config: Mapping[str, Any] | None = None,
) -> BranchGuardAgent:
    return BranchGuardAgent(
        enable_guard=enable_guard,
        enable_terminal=enable_terminal,
        config=config,
    )


_AGENT: BranchGuardAgent | None = None


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = _step(obs)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)


def model_status() -> dict[str, Any]:
    return _AGENT.diagnostics() if _AGENT is not None else {
        "kind": "v12a_r002_branch_guard_terminal_fill",
        "model_id": MODEL_ID,
        "status": "not_started",
    }
