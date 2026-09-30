"""Independent commodity-level market timing expert over a safe crop executor."""

from __future__ import annotations

from enum import Enum
import math
from typing import Any, Mapping

from event_program import TERMINAL_START_STEP, MacroDecision, observation_step
from policy_event_program import FixedEventProgramPolicy


class MarketTimingMode(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    POST_DEMAND = "POST_DEMAND"
    PRE_DAY_FLOOD = "PRE_DAY_FLOOD"


class MarketQueuePlacement(str, Enum):
    FRONT = "FRONT"
    BACK = "BACK"


def should_sell(mode: MarketTimingMode | str, step: int) -> bool:
    parsed = MarketTimingMode(mode)
    step = int(step)
    if parsed is MarketTimingMode.IMMEDIATE:
        return True
    if parsed is MarketTimingMode.POST_DEMAND:
        return step % 4 == 1
    return step % 24 == 23


class MarketTimingEventProgramPolicy:
    """Generate the complete market queue for one product and timing mode."""

    def __init__(
        self,
        decision: Mapping[str, Any],
        *,
        mode: MarketTimingMode | str,
        quantity_fraction: float = 1.0,
        queue_placement: MarketQueuePlacement | str = MarketQueuePlacement.FRONT,
        name: str | None = None,
    ) -> None:
        if not 0.0 < float(quantity_fraction) <= 1.0:
            raise ValueError("quantity_fraction must be in (0, 1]")
        fields = dict(decision)
        self.target_product = str(fields["production_line"])
        fields["sell_style"] = "HOLD"
        self.route = FixedEventProgramPolicy(
            MacroDecision(**fields), name=name or self.target_product.lower()
        )
        self.mode = MarketTimingMode(mode)
        self.quantity_fraction = float(quantity_fraction)
        self.queue_placement = MarketQueuePlacement(queue_placement)
        self.name = str(name or f"{self.target_product}__{self.mode.value}")
        self.action_steps = 0
        self.sale_events = 0
        self.units_offered = 0
        self.contract_violation_count = 0

    @property
    def manager_decision_count(self) -> int:
        return int(self.route.manager_decision_count)

    @property
    def terminal_procurement_count(self) -> int:
        return int(self.route.terminal_procurement_count)

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        step = observation_step(observation)
        action = self.route.act(observation)
        if step < TERMINAL_START_STEP and should_sell(self.mode, step):
            audit = self.route.last_audit or {}
            projected = dict((audit.get("market", {}) or {}).get("projected_shed", {}) or {})
            available = max(0, int(projected.get(self.target_product, 0) or 0))
            quantity = min(available, max(0, int(math.ceil(available * self.quantity_fraction))))
            if quantity > 0:
                market = [
                    list(order)
                    for order in (action.get("market", []) or [])
                    if not (
                        order
                        and order[0] == "SELL"
                        and len(order) >= 2
                        and str(order[1]) == self.target_product
                    )
                ]
                if len(market) >= 10:
                    self.contract_violation_count += 1
                    raise RuntimeError("market timing expert has no free order slot")
                action = dict(action)
                sell_order = ["SELL", self.target_product, quantity]
                if self.queue_placement is MarketQueuePlacement.FRONT:
                    action["market"] = [sell_order, *market]
                else:
                    action["market"] = [*market, sell_order]
                self.sale_events += 1
                self.units_offered += quantity
        self.action_steps += 1
        return action

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = [
    "MarketQueuePlacement",
    "MarketTimingEventProgramPolicy",
    "MarketTimingMode",
    "should_sell",
]
