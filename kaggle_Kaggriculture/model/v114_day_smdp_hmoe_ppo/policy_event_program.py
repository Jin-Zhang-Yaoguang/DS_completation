"""Checkpoint-free fixed macro policy for the independent V114 event program."""

from __future__ import annotations

from typing import Any, Mapping

from event_program import (
    MacroDecision,
    MacroPlanExecutor,
    PlanState,
    TERMINAL_START_STEP,
    observation_day,
    observation_step,
)


PROCUREMENT_OPERATIONS = frozenset(
    {"HIRE", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "BUY_LAND"}
)


def decision_as_dict(decision: MacroDecision) -> dict[str, Any]:
    """Return the stable JSON representation used by evaluation reports."""

    return {
        "production_line": decision.production_line.value,
        "worker_cap": int(decision.worker_cap),
        "cash_reserve": int(decision.cash_reserve),
        "sell_style": decision.sell_style.value,
        "terminal_mode": decision.terminal_mode.value,
    }


class FixedEventProgramPolicy:
    """Execute one fixed five-field macro decision for an entire episode.

    The same decision is selected at step 0 and reconsidered at every day
    boundary.  It is never changed intra-day.  ``MacroPlanExecutor`` supplies
    the absorbing terminal behaviour from step 671 onward.  This class has no
    checkpoint, learned parameter, historical-agent or action-fallback input.
    """

    def __init__(
        self,
        decision: MacroDecision | Mapping[str, Any],
        *,
        name: str | None = None,
    ) -> None:
        if isinstance(decision, MacroDecision):
            parsed = decision
        elif isinstance(decision, Mapping):
            parsed = MacroDecision(**dict(decision))
        else:
            raise TypeError("decision must be MacroDecision or a mapping")
        self.name = str(name or parsed.production_line.value.lower())
        self.fixed_decision = parsed
        self.executor = MacroPlanExecutor()
        self.state: PlanState | None = None
        self.manager_decision_count = 0
        self.action_steps = 0
        self.contract_violation_count = 0
        self.terminal_procurement_count = 0
        self.last_audit: dict[str, Any] | None = None

    @property
    def decision(self) -> dict[str, Any]:
        return decision_as_dict(self.fixed_decision)

    def reset(self) -> None:
        self.state = None
        self.manager_decision_count = 0
        self.action_steps = 0
        self.contract_violation_count = 0
        self.terminal_procurement_count = 0
        self.last_audit = None

    def act(self, observation: Any) -> dict[str, Any]:
        day = observation_day(observation)
        is_initial = self.state is None
        is_day_boundary = self.state is not None and day != self.state.decision_day
        if is_initial:
            self.state = self.executor.activate(observation, self.fixed_decision)
            self.manager_decision_count += 1
        elif is_day_boundary:
            self.manager_decision_count += 1

        try:
            result = self.executor.step(
                observation,
                self.state,
                daily_decision=self.fixed_decision if is_day_boundary else None,
            )
        except Exception:
            self.contract_violation_count += 1
            raise

        self.state = result.state
        self.last_audit = dict(result.audit)
        violations = list(result.audit.get("violations", []) or [])
        self.contract_violation_count += len(violations)
        step = observation_step(observation)
        if step >= TERMINAL_START_STEP:
            self.terminal_procurement_count += sum(
                bool(order and str(order[0]) in PROCUREMENT_OPERATIONS)
                for order in result.action.get("market", [])
            )
        self.action_steps += 1
        return result.action

    def __call__(self, observation: Any, configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = [
    "FixedEventProgramPolicy",
    "PROCUREMENT_OPERATIONS",
    "decision_as_dict",
]
