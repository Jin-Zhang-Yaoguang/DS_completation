"""V114 V4-0 option catalog and switching contracts.

This module is intentionally policy-free.  It defines the small action space
seen by the day-level manager and the deterministic rules that prevent an
option from chattering within a day.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Optional, Union


TURNS_PER_DAY = 24
RECOVERY_MIN_TURNS = 6
SWITCH_COOLDOWN_TURNS = 6


class OptionId(str, Enum):
    """The four independently trainable high-level responsibilities."""

    PRODUCTION_LOGISTICS = "PRODUCTION_LOGISTICS"
    MARKET_CASH = "MARKET_CASH"
    RECOVERY = "RECOVERY"
    TERMINAL_LIQUIDATION = "TERMINAL_LIQUIDATION"


class BudgetTier(str, Enum):
    """Coarse spending envelope; exact money limits belong to the executor."""

    LEAN = "LEAN"
    STANDARD = "STANDARD"
    EXPANSIVE = "EXPANSIVE"


class RiskTier(str, Enum):
    """Coarse risk appetite exposed to an option expert."""

    SAFE = "SAFE"
    BALANCED = "BALANCED"
    ASSERTIVE = "ASSERTIVE"


@dataclass(frozen=True)
class OptionSpec:
    option_id: OptionId
    normal_duration_turns: Optional[int]
    minimum_duration_turns: int
    terminal: bool = False


OPTION_CATALOG: Mapping[OptionId, OptionSpec] = MappingProxyType(
    {
        OptionId.PRODUCTION_LOGISTICS: OptionSpec(
            OptionId.PRODUCTION_LOGISTICS, TURNS_PER_DAY, TURNS_PER_DAY
        ),
        OptionId.MARKET_CASH: OptionSpec(
            OptionId.MARKET_CASH, TURNS_PER_DAY, TURNS_PER_DAY
        ),
        OptionId.RECOVERY: OptionSpec(
            OptionId.RECOVERY, TURNS_PER_DAY, RECOVERY_MIN_TURNS
        ),
        OptionId.TERMINAL_LIQUIDATION: OptionSpec(
            OptionId.TERMINAL_LIQUIDATION, None, 0, terminal=True
        ),
    }
)


def _coerce_enum(value: Union[str, Enum], enum_type: type[Enum]) -> Enum:
    if isinstance(value, enum_type):
        return value
    text = str(value).upper()
    try:
        return enum_type(text)
    except ValueError:
        return enum_type[text]


def coerce_option(value: Union[str, OptionId]) -> OptionId:
    return _coerce_enum(value, OptionId)  # type: ignore[return-value]


def coerce_budget_tier(value: Union[str, BudgetTier]) -> BudgetTier:
    return _coerce_enum(value, BudgetTier)  # type: ignore[return-value]


def coerce_risk_tier(value: Union[str, RiskTier]) -> RiskTier:
    return _coerce_enum(value, RiskTier)  # type: ignore[return-value]


@dataclass(frozen=True)
class OptionState:
    """All state needed to reproduce high-level switching decisions.

    ``terminal_entered`` is an episode-level latch.  Once terminal liquidation
    is entered it is absorbing, so a second entry is impossible.
    """

    current_option: Optional[OptionId] = None
    budget_tier: BudgetTier = BudgetTier.STANDARD
    risk_tier: RiskTier = RiskTier.BALANCED
    entered_step: int = 0
    last_switch_step: int = -SWITCH_COOLDOWN_TURNS
    switch_cooldown_until: int = 0
    cash_crisis: bool = False
    terminal_entered: bool = False
    terminal_entry_step: Optional[int] = None
    last_observed_step: int = 0

    def duration_turns(self, step: Optional[int] = None) -> int:
        current_step = self.last_observed_step if step is None else int(step)
        return max(0, current_step - self.entered_step)


@dataclass(frozen=True)
class OptionTransition:
    state: OptionState
    allowed: bool
    changed: bool
    reason: str


def transition_option(
    state: OptionState,
    requested_option: Union[str, OptionId],
    step: int,
    *,
    budget_tier: Union[str, BudgetTier, None] = None,
    risk_tier: Union[str, RiskTier, None] = None,
    day_boundary: bool = False,
    emergency: bool = False,
    recovery_resolved: bool = False,
) -> OptionTransition:
    """Apply the V4-0 option switching contract.

    Terminal entry overrides timing locks and is absorbing.  Other ordinary
    switches are only legal at ``hour=0``.  A cash emergency may enter
    recovery intra-day; recovery may leave intra-day after both its six-turn
    minimum and the six-turn switch cooldown have elapsed.
    """

    step = int(step)
    requested = coerce_option(requested_option)
    budget = state.budget_tier if budget_tier is None else coerce_budget_tier(budget_tier)
    risk = state.risk_tier if risk_tier is None else coerce_risk_tier(risk_tier)

    if state.current_option is OptionId.TERMINAL_LIQUIDATION:
        if requested is OptionId.TERMINAL_LIQUIDATION:
            return OptionTransition(
                replace(state, last_observed_step=max(state.last_observed_step, step)),
                True,
                False,
                "terminal_already_active",
            )
        return OptionTransition(state, False, False, "terminal_is_absorbing")

    if requested is OptionId.TERMINAL_LIQUIDATION:
        if state.terminal_entered:
            return OptionTransition(state, False, False, "terminal_already_entered")
        next_state = replace(
            state,
            current_option=requested,
            budget_tier=budget,
            risk_tier=risk,
            entered_step=step,
            last_switch_step=step,
            switch_cooldown_until=step + SWITCH_COOLDOWN_TURNS,
            terminal_entered=True,
            terminal_entry_step=step,
            last_observed_step=max(state.last_observed_step, step),
        )
        return OptionTransition(next_state, True, True, "terminal_entered")

    if state.terminal_entered:
        return OptionTransition(state, False, False, "terminal_already_entered")

    same_contract = (
        requested is state.current_option
        and budget is state.budget_tier
        and risk is state.risk_tier
    )
    if same_contract:
        return OptionTransition(
            replace(state, last_observed_step=max(state.last_observed_step, step)),
            True,
            False,
            "option_already_active",
        )

    if step < state.switch_cooldown_until:
        return OptionTransition(state, False, False, "switch_cooldown")

    leaving_recovery = (
        state.current_option is OptionId.RECOVERY
        and requested is not OptionId.RECOVERY
    )
    if leaving_recovery:
        if state.duration_turns(step) < RECOVERY_MIN_TURNS:
            return OptionTransition(state, False, False, "recovery_minimum_duration")
        if not (recovery_resolved or day_boundary):
            return OptionTransition(state, False, False, "recovery_not_resolved")
    elif not (day_boundary or emergency):
        return OptionTransition(state, False, False, "not_a_day_boundary")

    if requested is OptionId.RECOVERY and state.current_option is not None:
        if not (emergency or day_boundary):
            return OptionTransition(state, False, False, "recovery_requires_emergency")

    next_state = replace(
        state,
        current_option=requested,
        budget_tier=budget,
        risk_tier=risk,
        entered_step=step,
        last_switch_step=step,
        switch_cooldown_until=step + SWITCH_COOLDOWN_TURNS,
        last_observed_step=max(state.last_observed_step, step),
    )
    return OptionTransition(next_state, True, True, "option_entered")


def smdp_duration_discount(
    gamma_day: float, duration_turns: int, turns_per_day: int = TURNS_PER_DAY
) -> float:
    """Return ``gamma_day ** (duration_turns / turns_per_day)``."""

    gamma_day = float(gamma_day)
    duration_turns = int(duration_turns)
    turns_per_day = int(turns_per_day)
    if not isfinite(gamma_day) or not 0.0 < gamma_day <= 1.0:
        raise ValueError("gamma_day must be finite and in (0, 1]")
    if duration_turns < 0:
        raise ValueError("duration_turns must be non-negative")
    if turns_per_day <= 0:
        raise ValueError("turns_per_day must be positive")
    return gamma_day ** (duration_turns / turns_per_day)


__all__ = [
    "BudgetTier",
    "OPTION_CATALOG",
    "OptionId",
    "OptionSpec",
    "OptionState",
    "OptionTransition",
    "RECOVERY_MIN_TURNS",
    "RiskTier",
    "SWITCH_COOLDOWN_TURNS",
    "TURNS_PER_DAY",
    "smdp_duration_discount",
    "transition_option",
]
