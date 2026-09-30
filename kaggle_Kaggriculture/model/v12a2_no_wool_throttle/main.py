"""V12A2: V12A with the screen-falsified WOOL throttle removed.

The complete frozen Router and every worker action remain owned by V12A's
parent.  This residual may still throttle EGG/MILK under V12A's existing
branch/shop/storage guards, but WOOL sale quantities always pass through from
the learned Router unchanged.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

try:  # Standalone Kaggle archive.
    import base_agent as base  # type: ignore
except ImportError:  # Repository development runtime.
    from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import main as base


MODEL_ID = "v12a2_no_wool_throttle"


class NoWoolThrottleAgent(base.BranchGuardAgent):
    """Delete only WOOL from an otherwise unchanged V12A trigger."""

    def _should_throttle(
        self, obs: Any, action: Mapping[str, Any], branch: str | None
    ) -> tuple[bool, str, frozenset[str]]:
        throttle, reason, products = super()._should_throttle(obs, action, branch)
        if not throttle:
            return throttle, reason, products
        products = frozenset(products - {"WOOL"})
        if not products:
            return False, "wool_throttle_removed", products
        return True, reason, products

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": "v12a2_no_wool_throttle",
                "model_id": MODEL_ID,
                "removed_component": "WOOL top-day throttle",
            }
        )
        return payload


def make_agent() -> NoWoolThrottleAgent:
    return NoWoolThrottleAgent()


_AGENT: NoWoolThrottleAgent | None = None


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = base._step(obs)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)


def model_status() -> dict[str, Any]:
    if _AGENT is None:
        return {
            "kind": "v12a2_no_wool_throttle",
            "model_id": MODEL_ID,
            "status": "not_started",
        }
    return _AGENT.diagnostics()
