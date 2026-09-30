"""Shared, dependency-free action compiler for PPO v3 experts.

This module is deliberately route-agnostic.  It compiles an already selected
full production plan plus at most one market residual, freezes the mandated
opening, verifies the action closure, and fails back to the supplied V1 plan
when anything is malformed.  It can be copied unchanged into a Kaggle
submission; no JAX, NumPy or kaggle-environments imports are required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from experts import (
    Action,
    ActionFootprint,
    MarketExpert,
    MarketProposal,
    ProductionProposal,
    action_footprint,
    apply_market_proposal,
    copy_action,
)


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _seat(obs: Mapping[str, Any]) -> int:
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs: Mapping[str, Any]) -> Mapping[str, Any]:
    farms = _get(obs, "farms", None) or []
    seat = _seat(obs)
    if isinstance(farms, Sequence) and seat < len(farms):
        value = farms[seat]
        return value if isinstance(value, Mapping) else {}
    farm = _get(obs, "farm", None)
    return farm if isinstance(farm, Mapping) else {}


_UNIT_OPS = frozenset((
    "PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER", "HARVEST", "FEED",
    "CARE", "COLLECT_FERTILIZER", "PLANT", "PICKUP", "PLACE", "FERTILIZE",
    "BUILD_PASTURE", "DIG", "DROP",
))
_MARKET_OPS = frozenset(("SELL", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "BUY_LAND", "HIRE"))
_SELLABLE_DEFAULT = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")


@dataclass(frozen=True)
class CompilerConfig:
    frozen_steps: int = 72
    terminal_start_step: int = 716
    market_slots: int = 10
    enforce_terminal_liquidation: bool = True
    liquidation_order: Tuple[str, ...] = _SELLABLE_DEFAULT
    # All experts are still considered by the Router during the opening.  This
    # flag only makes their emitted atomic action non-deployable until step 72.
    freeze_opening_to_baseline: bool = True


@dataclass(frozen=True)
class CompilationResult:
    action: Action
    production_expert_id: str
    market_expert_id: Optional[str]
    footprint: ActionFootprint
    fallback_used: bool
    frozen_opening: bool
    terminal_guard_applied: bool
    reasons: Tuple[str, ...] = ()

    @property
    def effective_intervention(self) -> bool:
        return self.footprint.effective and not self.fallback_used and not self.frozen_opening

    def audit_row(self) -> Dict[str, Any]:
        return {
            "production_expert": self.production_expert_id,
            "market_expert": self.market_expert_id,
            "footprint": self.footprint.as_dict(),
            "effective_action_change": self.effective_intervention,
            "fallback_used": self.fallback_used,
            "frozen_opening": self.frozen_opening,
            "terminal_guard_applied": self.terminal_guard_applied,
            "compiler_reasons": list(self.reasons),
        }


class ActionCompiler:
    """Compile a flat expert selection into a legal Kaggle action.

    ``baseline_action`` must be the independently generated V1 action for the
    same observation.  It is not a policy-selection default: it is solely the
    frozen-opening value and the fail-closed action closure.
    """

    def __init__(self, config: Optional[CompilerConfig] = None) -> None:
        self.config = config or CompilerConfig()

    def compile(
        self,
        obs: Mapping[str, Any],
        *,
        baseline_action: Mapping[str, Any],
        production: Optional[ProductionProposal],
        market_expert: Optional[MarketExpert] = None,
        market: Optional[MarketProposal] = None,
    ) -> CompilationResult:
        baseline, baseline_errors = self._normalise_and_validate(obs, baseline_action)
        # Baseline should itself already be valid.  If it isn't, still return a
        # shaped PASS action rather than propagating a submission exception.
        if baseline_errors:
            baseline = self._pass_action(obs)
        step = int(_get(obs, "step", 0) or 0)
        selected_id = production.expert_id if production is not None else "unknown"
        reasons = list(baseline_errors)
        fallback = False
        frozen = bool(self.config.freeze_opening_to_baseline and step < self.config.frozen_steps)

        if frozen:
            candidate = baseline
            reasons.append("opening_frozen")
        elif production is None or not production.eligible or production.plan is None:
            candidate = baseline
            fallback = True
            reasons.append("production_ineligible")
        else:
            candidate, errors = self._normalise_and_validate(obs, production.plan.action)
            if errors:
                candidate = baseline
                fallback = True
                reasons.extend("production_%s" % error for error in errors)

        market_id: Optional[str] = None
        if not frozen and not fallback and market_expert is not None and market is not None:
            market_id = market.expert_id
            if market.eligible:
                changed = apply_market_proposal(market_expert, market, candidate, obs)
                changed, errors = self._normalise_and_validate(obs, changed)
                if errors:
                    # Market failure does not invalidate the independently
                    # selected production expert; discard just the residual.
                    reasons.extend("market_%s" % error for error in errors)
                else:
                    candidate = changed
            else:
                reasons.append("market_ineligible:%s" % (market.reason or "unknown"))

        terminal = False
        if self.config.enforce_terminal_liquidation and step >= self.config.terminal_start_step:
            before_terminal = candidate
            liquidated, changed = self._terminal_liquidation(obs, candidate)
            candidate, errors = self._normalise_and_validate(obs, liquidated)
            if errors:
                # It is safer to retain the pre-liquidation legal candidate
                # than to use a malformed safety edit.
                candidate, _ = self._normalise_and_validate(obs, before_terminal)
                reasons.extend("terminal_%s" % error for error in errors)
            else:
                terminal = changed

        # Ensure the final action closure after every transform.
        candidate, final_errors = self._normalise_and_validate(obs, candidate)
        if final_errors:
            candidate = baseline
            fallback = True
            reasons.extend("final_%s" % error for error in final_errors)
        footprint = action_footprint(baseline, candidate)
        return CompilationResult(
            action=candidate,
            production_expert_id=selected_id,
            market_expert_id=market_id,
            footprint=footprint,
            fallback_used=fallback,
            frozen_opening=frozen,
            terminal_guard_applied=terminal,
            reasons=tuple(reasons),
        )

    def _pass_action(self, obs: Mapping[str, Any]) -> Action:
        hands = _get(_farm(obs), "hands", None) or []
        return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}

    def _normalise_and_validate(self, obs: Mapping[str, Any], action: Mapping[str, Any]) -> Tuple[Action, Tuple[str, ...]]:
        errors = []
        if not isinstance(action, Mapping):
            return self._pass_action(obs), ("action_not_mapping",)
        result = copy_action(action)
        expected_hands = len(_get(_farm(obs), "hands", None) or [])
        result["hands"] = result["hands"][:expected_hands]
        if len(result["hands"]) < expected_hands:
            result["hands"].extend([["PASS"] for _ in range(expected_hands - len(result["hands"]))])
        result["farmer"], farmer_error = self._unit_order(result["farmer"])
        if farmer_error:
            errors.append("farmer_%s" % farmer_error)
        validated_hands = []
        for index, order in enumerate(result["hands"]):
            checked, error = self._unit_order(order)
            validated_hands.append(checked)
            if error:
                errors.append("hand%d_%s" % (index, error))
        result["hands"] = validated_hands

        validated_market = []
        for index, order in enumerate(result["market"][: self.config.market_slots]):
            checked, error = self._market_order(order)
            if error:
                errors.append("market%d_%s" % (index, error))
            else:
                validated_market.append(checked)
        if len(result["market"]) > self.config.market_slots:
            errors.append("market_slot_overflow")
        result["market"] = validated_market
        return result, tuple(errors)

    @staticmethod
    def _unit_order(order: Sequence[Any]) -> Tuple[list, Optional[str]]:
        if not isinstance(order, Sequence) or isinstance(order, (str, bytes)) or not order:
            return ["PASS"], "malformed"
        checked = list(order)
        op = str(checked[0])
        if op not in _UNIT_OPS:
            return ["PASS"], "unknown_op"
        if op in ("PICKUP", "PLACE", "DROP") and len(checked) >= 3:
            try:
                if int(checked[2]) < 0:
                    return ["PASS"], "negative_quantity"
            except (TypeError, ValueError):
                return ["PASS"], "bad_quantity"
        return checked, None

    @staticmethod
    def _market_order(order: Sequence[Any]) -> Tuple[list, Optional[str]]:
        if not isinstance(order, Sequence) or isinstance(order, (str, bytes)) or not order:
            return [], "malformed"
        checked = list(order)
        op = str(checked[0])
        if op not in _MARKET_OPS:
            return [], "unknown_op"
        # The Kaggriculture protocol allows singleton HIRE and BUY_LAND
        # orders.  The V1 baseline uses both forms in its valid frozen trace.
        if op not in ("HIRE", "BUY_LAND") and len(checked) < 2:
            return [], "missing_target"
        if op in ("SELL", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"):
            if len(checked) < 3:
                return [], "missing_quantity"
            try:
                quantity = int(checked[2])
            except (TypeError, ValueError):
                return [], "bad_quantity"
            # The frozen V1 trace deliberately contains a few zero-quantity
            # buy placeholders.  Kaggriculture accepts those as no-ops, and
            # rejecting them would turn an otherwise valid baseline turn into
            # a PASS fallback.  Only negative quantities are malformed.
            if quantity < 0:
                return [], "negative_quantity"
            checked[2] = quantity
        return checked, None

    def _terminal_liquidation(self, obs: Mapping[str, Any], action: Mapping[str, Any]) -> Tuple[Action, bool]:
        """Append bounded, observable sales from own shed near the terminal.

        This is intentionally conservative: it never deletes a plan's orders,
        never exceeds market slots, and only sells positive private shed stock
        that is not already fully scheduled to sell this turn.
        """
        result = copy_action(action)
        # Kaggriculture exposes the current player's liquid inventory under
        # ``private.shed`` rather than the public farm object.  Reading the
        # farm here would silently turn the terminal guard into a no-op.
        private = _get(obs, "private", None) or {}
        shed = _get(private, "shed", None) or {}
        if not isinstance(shed, Mapping):
            return result, False
        planned = {}
        for order in result["market"]:
            if len(order) >= 3 and order[0] == "SELL":
                try:
                    planned[str(order[1])] = planned.get(str(order[1]), 0) + max(0, int(order[2]))
                except (TypeError, ValueError):
                    continue
        changed = False
        for item in self.config.liquidation_order:
            if len(result["market"]) >= self.config.market_slots:
                break
            try:
                available = max(0, int(_get(shed, item, 0) or 0))
            except (TypeError, ValueError):
                continue
            quantity = available - planned.get(item, 0)
            if quantity > 0:
                result["market"].append(["SELL", item, quantity])
                planned[item] = planned.get(item, 0) + quantity
                changed = True
        return result, changed


def compile_action(
    obs: Mapping[str, Any],
    *,
    baseline_action: Mapping[str, Any],
    production: Optional[ProductionProposal],
    market_expert: Optional[MarketExpert] = None,
    market: Optional[MarketProposal] = None,
    config: Optional[CompilerConfig] = None,
) -> CompilationResult:
    """Convenience functional entry point used by collectors and submission."""
    return ActionCompiler(config).compile(
        obs,
        baseline_action=baseline_action,
        production=production,
        market_expert=market_expert,
        market=market,
    )
