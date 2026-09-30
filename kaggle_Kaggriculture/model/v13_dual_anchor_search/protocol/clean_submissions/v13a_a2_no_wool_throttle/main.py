"""V13A: A2 plus global removal of the top-day WOOL throttle."""

from __future__ import annotations

import copy
from typing import Any, Mapping

try:  # Standalone Kaggle archive.
    import a2_agent as a2  # type: ignore
except ImportError:  # Repository development runtime.
    from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2


MODEL_ID = "v13a_a2_no_wool_throttle"


class A2NoWoolThrottleAgent(a2.NoShopGateAgent):
    """Retain A2's EGG/MILK decisions while never throttling WOOL."""

    def _reset(self) -> None:
        super()._reset()
        self.wool_throttle_opportunities = 0

    def _should_throttle(
        self, obs: Any, action: Mapping[str, Any], branch: str | None
    ) -> tuple[bool, str, frozenset[str]]:
        a2_decision = super()._should_throttle(obs, action, branch)
        try:
            throttle, reason, products = a2_decision
            if not throttle:
                return a2_decision
            has_wool_sale = any(
                len(order) >= 3
                and str(order[0]) == "SELL"
                and str(order[1]) == "WOOL"
                and int(order[2] or 0) > 0
                for order in action.get("market", [])
            )
            if "WOOL" in products and has_wool_sale:
                self.wool_throttle_opportunities += 1
            retained = frozenset(products - {"WOOL"})
            if not retained:
                return False, "v13a_wool_throttle_removed", retained
            return True, reason, retained
        except Exception:
            # Any V13-only failure preserves A2's exact decision.
            return a2_decision

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": "v13a_a2_no_wool_throttle",
                "model_id": MODEL_ID,
                "parent_id": "v12a2_no_shop_gate",
                "change_scope": "remove WOOL from every approved A2 throttle",
                "wool_throttle_opportunities": self.wool_throttle_opportunities,
            }
        )
        return payload


def make_agent() -> A2NoWoolThrottleAgent:
    return A2NoWoolThrottleAgent()


_AGENT: A2NoWoolThrottleAgent | None = None


def model_status() -> dict[str, Any]:
    if _AGENT is None:
        return {"kind": MODEL_ID, "model_id": MODEL_ID, "status": "not_started"}
    return _AGENT.diagnostics()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = a2.base._step(obs)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)
