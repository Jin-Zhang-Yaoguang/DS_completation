"""V13C: A2 plus V8-only removal of the top-day WOOL throttle."""

from __future__ import annotations

import copy
from typing import Any, Mapping

try:  # Standalone Kaggle archive.
    import a2_agent as a2  # type: ignore
except ImportError:  # Repository development runtime.
    from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2


MODEL_ID = "v13c_a2_v8_no_wool_throttle"


class A2V8NoWoolThrottleAgent(a2.NoShopGateAgent):
    """Remove WOOL only when A2 selected baseline_v8; preserve V5 A2."""

    def _reset(self) -> None:
        super()._reset()
        self.v8_wool_throttle_opportunities = 0

    def _should_throttle(
        self, obs: Any, action: Mapping[str, Any], branch: str | None
    ) -> tuple[bool, str, frozenset[str]]:
        a2_decision = super()._should_throttle(obs, action, branch)
        try:
            throttle, reason, products = a2_decision
            if not throttle or branch != "baseline_v8":
                return a2_decision
            has_wool_sale = any(
                len(order) >= 3
                and str(order[0]) == "SELL"
                and str(order[1]) == "WOOL"
                and int(order[2] or 0) > 0
                for order in action.get("market", [])
            )
            if "WOOL" in products and has_wool_sale:
                self.v8_wool_throttle_opportunities += 1
            retained = frozenset(products - {"WOOL"})
            if not retained:
                return False, "v13c_v8_wool_throttle_removed", retained
            return True, reason, retained
        except Exception:
            return a2_decision

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": "v13c_a2_v8_no_wool_throttle",
                "model_id": MODEL_ID,
                "parent_id": "v12a2_no_shop_gate",
                "change_scope": "remove WOOL throttle only for baseline_v8",
                "v8_wool_throttle_opportunities": self.v8_wool_throttle_opportunities,
            }
        )
        return payload


def make_agent() -> A2V8NoWoolThrottleAgent:
    return A2V8NoWoolThrottleAgent()


_AGENT: A2V8NoWoolThrottleAgent | None = None


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
