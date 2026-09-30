"""State-safe execution for V114 bounded residual actions.

The executor applies a small residual to a *current neural expert* action.  It
does not import or call a historical agent.  Every edit is transactional: on
quota, shape, option-contract, legality, budget, or inventory failure, the
returned action is a fresh copy of the unmodified neural action and no quota is
consumed.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

try:  # Supports both package imports and PYTHONPATH=<v114 directory> tests.
    from .residual_action_space import (
        DailyResidualQuota,
        ResidualChannel,
        ResidualRequest,
        ResidualType,
        normalize_residual_type,
    )
except ImportError:  # pragma: no cover - exercised by the requested test command.
    from residual_action_space import (  # type: ignore
        DailyResidualQuota,
        ResidualChannel,
        ResidualRequest,
        ResidualType,
        normalize_residual_type,
    )


Action = Dict[str, Any]
Validator = Callable[..., bool]


@dataclass(frozen=True)
class ExecutionResult:
    action: Action
    applied: bool
    reason: str
    residual: ResidualType
    channel: ResidualChannel
    modifies_unit: bool
    modifies_market: bool
    quota: Mapping[str, Any]


def _as_list(value: Any, default: Optional[Sequence[Any]] = None) -> list:
    if value is None:
        return list(default or [])
    if isinstance(value, list):
        return copy.deepcopy(value)
    if isinstance(value, tuple):
        return [copy.deepcopy(item) for item in value]
    return [copy.deepcopy(value)]


def copy_kaggriculture_action(action: Any) -> Action:
    """Return a canonical, detached ``farmer/hands/market`` action.

    Missing/None fields are tolerated.  Unknown top-level fields are omitted so
    the result remains acceptable to Kaggriculture's action parser.
    """

    source = action if isinstance(action, Mapping) else {}
    farmer = _as_list(source.get("farmer"), ["PASS"])
    if not farmer:
        farmer = ["PASS"]

    raw_hands = source.get("hands")
    hands: list = []
    if isinstance(raw_hands, (list, tuple)):
        for order in raw_hands:
            normalized = _as_list(order, ["PASS"])
            hands.append(normalized or ["PASS"])

    raw_market = source.get("market")
    market: list = []
    if isinstance(raw_market, (list, tuple)):
        for order in raw_market:
            normalized = _as_list(order)
            if normalized:
                market.append(normalized)

    return {"farmer": farmer, "hands": hands, "market": market}


def _get(mapping: Any, key: str, default: Any = None) -> Any:
    if isinstance(mapping, Mapping):
        return mapping.get(key, default)
    return default


def _call_validator(validator: Validator, candidate: Action, request: ResidualRequest,
                    context: Mapping[str, Any]) -> bool:
    """Accept validators with one, two, or three positional arguments."""

    try:
        return bool(validator(candidate, request, context))
    except TypeError:
        try:
            return bool(validator(candidate, context))
        except TypeError:
            try:
                return bool(validator(candidate))
            except Exception:
                return False
        except Exception:
            return False
    except Exception:
        return False


def _is_pass(order: Any) -> bool:
    return not isinstance(order, (list, tuple)) or not order or str(order[0]).upper() == "PASS"


def _is_sell(order: Any) -> bool:
    return (
        isinstance(order, (list, tuple))
        and len(order) >= 3
        and str(order[0]).upper() == "SELL"
    )


def _quantity(order: Sequence[Any]) -> Optional[int]:
    if len(order) < 3:
        return None
    try:
        return int(order[2])
    except (TypeError, ValueError):
        return None


class SafetyExecutor:
    """Apply residual edits with deterministic, fail-closed safety checks."""

    def __init__(
        self,
        quota: Optional[DailyResidualQuota] = None,
        *,
        legal_validator: Optional[Validator] = None,
        budget_validator: Optional[Validator] = None,
        inventory_validator: Optional[Validator] = None,
        option_validator: Optional[Validator] = None,
    ) -> None:
        self.quota = quota or DailyResidualQuota(max_non_keep=4)
        self.legal_validator = legal_validator
        self.budget_validator = budget_validator
        self.inventory_validator = inventory_validator
        self.option_validator = option_validator

    def reset_day(self, day: Any = None) -> None:
        self.quota.reset(day)

    def apply(
        self,
        base_action: Any,
        residual: Any = ResidualType.KEEP,
        *,
        day: Any = None,
        context: Optional[Mapping[str, Any]] = None,
        **context_values: Any,
    ) -> Action:
        """Return only the safe action; use :meth:`execute` for audit metadata."""

        return self.execute(
            base_action,
            residual,
            day=day,
            context=context,
            **context_values,
        ).action

    def execute(
        self,
        base_action: Any,
        residual: Any = ResidualType.KEEP,
        *,
        day: Any = None,
        context: Optional[Mapping[str, Any]] = None,
        **context_values: Any,
    ) -> ExecutionResult:
        """Transactionally apply one residual request.

        Context is intentionally data/callback based.  Useful keys include
        ``option_id``, ``option_contract``, ``inventory``/``shed``,
        ``available_budget``, ``unit_prices``, ``legal_validator``, and their
        budget/inventory/option validator counterparts.
        """

        base = copy_kaggriculture_action(base_action)
        try:
            request = ResidualRequest.from_value(residual)
        except (TypeError, ValueError):
            return self._result(base, False, "invalid_residual", ResidualRequest(), day)

        merged_context: Dict[str, Any] = dict(context or {})
        merged_context.update(context_values)
        effective_day = self._resolve_day(day, merged_context)

        if request.kind is ResidualType.KEEP:
            # Rolling the day on KEEP keeps quota state synchronized without use.
            self.quota.can_consume(request, effective_day)
            return self._result(base, False, "keep", request, effective_day)

        allowed, reason = self.quota.can_consume(request, effective_day)
        if not allowed:
            return self._result(base, False, reason, request, effective_day)

        candidate, mutation_reason = self._mutate(base, request, merged_context)
        if candidate is None:
            return self._result(base, False, mutation_reason, request, effective_day)
        if candidate == base:
            return self._result(base, False, "no_effect", request, effective_day)

        checks = (
            self._check_shape,
            self._check_option_contract,
            self._check_legality,
            self._check_budget,
            self._check_inventory,
        )
        for check in checks:
            ok, check_reason = check(candidate, request, merged_context)
            if not ok:
                return self._result(base, False, check_reason, request, effective_day)

        consumed, consume_reason = self.quota.consume(request, effective_day)
        if not consumed:  # Defensive in case a future concurrent quota is used.
            return self._result(base, False, consume_reason, request, effective_day)
        return self._result(candidate, True, "applied", request, effective_day)

    def _result(
        self,
        action: Action,
        applied: bool,
        reason: str,
        request: ResidualRequest,
        day: Any,
    ) -> ExecutionResult:
        # Always detach the returned value from both base input and request data.
        detached = copy_kaggriculture_action(action)
        return ExecutionResult(
            action=detached,
            applied=applied,
            reason=reason,
            residual=request.kind,
            channel=request.spec.channel,
            modifies_unit=applied and request.spec.modifies_unit,
            modifies_market=applied and request.spec.modifies_market,
            quota=self.quota.snapshot(),
        )

    @staticmethod
    def _resolve_day(day: Any, context: Mapping[str, Any]) -> Any:
        if day is not None:
            return day
        if context.get("day") is not None:
            return context["day"]
        step = context.get("step")
        try:
            return int(step) // 24 if step is not None else 0
        except (TypeError, ValueError):
            return 0

    def _mutate(
        self, base: Action, request: ResidualRequest, context: Mapping[str, Any]
    ) -> Tuple[Optional[Action], str]:
        candidate = copy_kaggriculture_action(base)
        kind = request.kind

        if kind in (ResidualType.MARKET_QTY_UP_1, ResidualType.MARKET_QTY_DOWN_1):
            index = self._market_index(candidate, request.market_index, require_sell=False)
            if index is None:
                return None, "market_order_not_found"
            order = candidate["market"][index]
            current = _quantity(order)
            if current is None or current <= 0:
                return None, "market_order_has_no_positive_quantity"
            delta = request.quantity_step if kind is ResidualType.MARKET_QTY_UP_1 else -request.quantity_step
            updated = current + delta
            if updated <= 0:
                return None, "market_quantity_would_be_non_positive"
            order[2] = updated
            return candidate, "ok"

        if kind is ResidualType.DEFER_ONE_MARKET_ORDER:
            index = self._market_index(candidate, request.market_index, require_sell=False)
            if index is None:
                return None, "market_order_not_found"
            urgent = set(context.get("urgent_market_indices", ()) or ())
            if index in urgent or bool(request.metadata.get("urgent", False)):
                return None, "urgent_order_cannot_be_deferred"
            candidate["market"].pop(index)
            return candidate, "ok"

        if kind is ResidualType.ADVANCE_ONE_SELL:
            index = self._market_index(candidate, request.market_index, require_sell=True)
            if index is None:
                return None, "sell_order_not_found"
            if index == 0:
                return None, "sell_already_first"
            order = candidate["market"].pop(index)
            candidate["market"].insert(0, order)
            return candidate, "ok"

        if kind in (ResidualType.CASH_TIER_UP_1, ResidualType.CASH_TIER_DOWN_1):
            if not isinstance(request.candidate_action, Mapping):
                return None, "cash_tier_requires_neural_candidate_action"
            tier_action = copy_kaggriculture_action(request.candidate_action)
            # CASH_TIER belongs to the market ratio: unit actions must be fixed.
            if tier_action["farmer"] != base["farmer"] or tier_action["hands"] != base["hands"]:
                return None, "cash_tier_candidate_changed_unit_action"
            return tier_action, "ok"

        if kind is ResidualType.REASSIGN_ONE_IDLE_UNIT:
            if request.unit_index is None or request.replacement is None:
                return None, "reassign_requires_unit_and_replacement"
            replacement = _as_list(request.replacement)
            if not replacement or _is_pass(replacement):
                return None, "replacement_must_be_non_pass"
            if request.unit_index == -1:
                if not _is_pass(candidate["farmer"]):
                    return None, "unit_not_idle"
                candidate["farmer"] = replacement
            elif 0 <= request.unit_index < len(candidate["hands"]):
                if not _is_pass(candidate["hands"][request.unit_index]):
                    return None, "unit_not_idle"
                candidate["hands"][request.unit_index] = replacement
            else:
                return None, "unit_index_out_of_range"
            return candidate, "ok"

        if kind is ResidualType.TERMINAL_RETURN_OR_SELL:
            if isinstance(request.candidate_action, Mapping):
                return copy_kaggriculture_action(request.candidate_action), "ok"
            if request.market_order is not None:
                order = _as_list(request.market_order)
                if not _is_sell(order):
                    return None, "terminal_market_order_must_be_sell"
                candidate["market"].append(order)
                return candidate, "ok"
            if request.unit_index is not None and request.replacement is not None:
                replacement = _as_list(request.replacement)
                if not replacement:
                    return None, "terminal_replacement_is_empty"
                if request.unit_index == -1:
                    candidate["farmer"] = replacement
                elif 0 <= request.unit_index < len(candidate["hands"]):
                    candidate["hands"][request.unit_index] = replacement
                else:
                    return None, "unit_index_out_of_range"
                return candidate, "ok"
            return None, "terminal_residual_requires_candidate_edit"

        return None, "unsupported_residual"

    @staticmethod
    def _market_index(action: Action, requested: Optional[int], *, require_sell: bool) -> Optional[int]:
        market = action["market"]
        if requested is not None:
            if 0 <= requested < len(market) and (not require_sell or _is_sell(market[requested])):
                return requested
            return None
        for index, order in enumerate(market):
            if require_sell:
                if _is_sell(order):
                    return index
            elif _quantity(order) is not None:
                return index
        return None

    @staticmethod
    def _check_shape(
        candidate: Action, request: ResidualRequest, context: Mapping[str, Any]
    ) -> Tuple[bool, str]:
        if set(candidate) != {"farmer", "hands", "market"}:
            return False, "invalid_action_keys"
        if not isinstance(candidate["farmer"], list) or not candidate["farmer"]:
            return False, "invalid_farmer_action"
        if not isinstance(candidate["hands"], list) or any(
            not isinstance(order, list) or not order for order in candidate["hands"]
        ):
            return False, "invalid_hands_action"
        if not isinstance(candidate["market"], list) or any(
            not isinstance(order, list) or not order for order in candidate["market"]
        ):
            return False, "invalid_market_action"
        try:
            max_orders = int(context.get("max_market_orders", 10))
        except (TypeError, ValueError):
            max_orders = 10
        if len(candidate["market"]) > max_orders:
            return False, "market_order_limit"
        quantity_ops = {"SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"}
        for order in candidate["market"]:
            if str(order[0]).upper() in quantity_ops:
                quantity = _quantity(order)
                if quantity is None or quantity <= 0:
                    return False, "invalid_market_quantity"
        return True, "ok"

    def _check_option_contract(
        self, candidate: Action, request: ResidualRequest, context: Mapping[str, Any]
    ) -> Tuple[bool, str]:
        validator = context.get("option_validator") or self.option_validator
        if callable(validator) and not _call_validator(validator, candidate, request, context):
            return False, "option_contract_failed"

        contract = context.get("option_contract")
        if callable(contract):
            if not _call_validator(contract, candidate, request, context):
                return False, "option_contract_failed"
            contract = {}
        if contract is None:
            contract = {}
        if not isinstance(contract, Mapping):
            return False, "invalid_option_contract"

        option_id = str(context.get("option_id", contract.get("option_id", ""))).upper()
        if request.kind is ResidualType.TERMINAL_RETURN_OR_SELL:
            terminal = bool(context.get("terminal", False)) or option_id == "TERMINAL_LIQUIDATION"
            if not terminal:
                return False, "terminal_option_required"

        allowed = contract.get("allowed_residuals", context.get("allowed_residuals"))
        if allowed is not None:
            try:
                normalized = {normalize_residual_type(item) for item in allowed}
            except (TypeError, ValueError):
                return False, "invalid_allowed_residuals"
            if request.kind not in normalized:
                return False, "residual_not_allowed_by_option"

        forbidden = contract.get("forbidden_residuals", ()) or ()
        try:
            if request.kind in {normalize_residual_type(item) for item in forbidden}:
                return False, "residual_forbidden_by_option"
        except (TypeError, ValueError):
            return False, "invalid_forbidden_residuals"

        if request.spec.modifies_market and contract.get("allow_market") is False:
            return False, "market_edit_forbidden_by_option"
        if request.spec.modifies_unit and contract.get("allow_unit") is False:
            return False, "unit_edit_forbidden_by_option"
        return True, "ok"

    def _check_legality(
        self, candidate: Action, request: ResidualRequest, context: Mapping[str, Any]
    ) -> Tuple[bool, str]:
        validator = context.get("legal_validator") or self.legal_validator
        if callable(validator) and not _call_validator(validator, candidate, request, context):
            return False, "illegal_action"

        legal_units = context.get("legal_unit_actions")
        if request.spec.modifies_unit and isinstance(legal_units, Mapping):
            if request.unit_index == -1:
                allowed = legal_units.get("farmer", legal_units.get(-1))
                actual = candidate["farmer"]
            elif request.unit_index is not None:
                allowed = legal_units.get(request.unit_index, legal_units.get(f"hand:{request.unit_index}"))
                actual = (
                    candidate["hands"][request.unit_index]
                    if 0 <= request.unit_index < len(candidate["hands"])
                    else None
                )
            else:
                allowed = None
                actual = None
            if allowed is not None and actual not in [list(item) for item in allowed]:
                return False, "illegal_unit_reassignment"
        return True, "ok"

    def _check_budget(
        self, candidate: Action, request: ResidualRequest, context: Mapping[str, Any]
    ) -> Tuple[bool, str]:
        validator = context.get("budget_validator") or self.budget_validator
        if callable(validator) and not _call_validator(validator, candidate, request, context):
            return False, "budget_failed"

        budget = context.get("available_budget", context.get("budget_limit"))
        if budget is None:
            budget = self._money_from_observation(context)
        if budget is None:
            return True, "ok"
        try:
            budget_value = float(budget)
        except (TypeError, ValueError):
            return False, "invalid_budget"

        projected = context.get("projected_spend")
        if callable(projected):
            try:
                spend = float(projected(candidate))
            except Exception:
                return False, "budget_projection_failed"
        else:
            spend = self._estimate_spend(candidate, context)
        if spend > budget_value + 1e-9:
            return False, "budget_exceeded"
        return True, "ok"

    @staticmethod
    def _money_from_observation(context: Mapping[str, Any]) -> Optional[float]:
        observation = context.get("observation", context.get("obs"))
        if not isinstance(observation, Mapping):
            return None
        farms = observation.get("farms")
        try:
            player = int(observation.get("player", 0) or 0)
            farm = farms[player] if isinstance(farms, (list, tuple)) else None
            return float(farm["money"]) if isinstance(farm, Mapping) and "money" in farm else None
        except (IndexError, TypeError, ValueError):
            return None

    @staticmethod
    def _estimate_spend(candidate: Action, context: Mapping[str, Any]) -> float:
        prices = context.get("unit_prices", context.get("prices", {}))
        fixed = context.get("fixed_costs", {})
        if not isinstance(prices, Mapping):
            prices = {}
        if not isinstance(fixed, Mapping):
            fixed = {}
        total = 0.0
        for order in candidate["market"]:
            op = str(order[0]).upper()
            if op == "SELL":
                continue
            item = str(order[1]) if len(order) > 1 else ""
            quantity = _quantity(order)
            candidates: Iterable[Any] = ((op, item), f"{op}:{item}", item, op)
            price = next((prices[key] for key in candidates if key in prices), None)
            if price is not None and quantity is not None:
                try:
                    total += max(0, quantity) * max(0.0, float(price))
                except (TypeError, ValueError):
                    return float("inf")
            elif op in fixed:
                try:
                    total += max(0.0, float(fixed[op]))
                except (TypeError, ValueError):
                    return float("inf")
        return total

    def _check_inventory(
        self, candidate: Action, request: ResidualRequest, context: Mapping[str, Any]
    ) -> Tuple[bool, str]:
        validator = context.get("inventory_validator") or self.inventory_validator
        if callable(validator) and not _call_validator(validator, candidate, request, context):
            return False, "inventory_failed"

        inventory = context.get("inventory", context.get("shed"))
        if inventory is None:
            observation = context.get("observation", context.get("obs"))
            private = _get(observation, "private", {})
            inventory = _get(private, "shed")
        if inventory is not None and not isinstance(inventory, Mapping):
            return False, "invalid_inventory"

        if isinstance(inventory, Mapping):
            sells: Dict[str, int] = {}
            for order in candidate["market"]:
                if _is_sell(order):
                    item = str(order[1])
                    quantity = _quantity(order) or 0
                    sells[item] = sells.get(item, 0) + quantity
            for item, quantity in sells.items():
                try:
                    available = int(inventory.get(item, 0) or 0)
                except (TypeError, ValueError):
                    return False, "invalid_inventory_quantity"
                if quantity > available:
                    return False, "insufficient_inventory"

        market_inventory = context.get("market_inventory")
        if isinstance(market_inventory, Mapping):
            buys: Dict[str, int] = {}
            for order in candidate["market"]:
                if len(order) >= 3 and str(order[0]).upper() == "BUY_PRODUCT":
                    item = str(order[1])
                    buys[item] = buys.get(item, 0) + (_quantity(order) or 0)
            for item, quantity in buys.items():
                try:
                    available = int(market_inventory.get(item, 0) or 0)
                except (TypeError, ValueError):
                    return False, "invalid_market_inventory"
                if quantity > available:
                    return False, "market_inventory_exceeded"

        capacity = context.get("inventory_capacity")
        if capacity is not None and isinstance(inventory, Mapping):
            try:
                current = sum(max(0, int(value or 0)) for value in inventory.values())
                bought = sum(
                    _quantity(order) or 0
                    for order in candidate["market"]
                    if len(order) >= 3 and str(order[0]).upper() == "BUY_PRODUCT"
                )
                sold = sum(
                    _quantity(order) or 0 for order in candidate["market"] if _is_sell(order)
                )
                if current + bought - sold > int(capacity):
                    return False, "inventory_capacity_exceeded"
            except (TypeError, ValueError):
                return False, "invalid_inventory_capacity"
        return True, "ok"


def apply_residual(
    base_action: Any,
    residual: Any = ResidualType.KEEP,
    *,
    executor: Optional[SafetyExecutor] = None,
    day: Any = None,
    context: Optional[Mapping[str, Any]] = None,
    **context_values: Any,
) -> Action:
    """Stateless-looking convenience wrapper.

    Pass a persistent executor when daily quota must span multiple calls.
    """

    active = executor or SafetyExecutor()
    return active.apply(
        base_action,
        residual,
        day=day,
        context=context,
        **context_values,
    )


__all__ = [
    "ExecutionResult",
    "SafetyExecutor",
    "apply_residual",
    "copy_kaggriculture_action",
]
