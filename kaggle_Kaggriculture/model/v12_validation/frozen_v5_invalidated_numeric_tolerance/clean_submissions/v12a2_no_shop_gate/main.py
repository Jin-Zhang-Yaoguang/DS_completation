"""V12A2: delete V12A's screen-falsified shop-demand product gate."""

from __future__ import annotations

import copy
from typing import Any

try:  # Standalone Kaggle archive.
    import base_agent as base  # type: ignore
except ImportError:  # Repository development runtime.
    from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import main as base


MODEL_ID = "v12a2_no_shop_gate"


class NoShopGateAgent(base.BranchGuardAgent):
    """Keep every V12A rule except the product-level unlocked-shop filter."""

    def __init__(self) -> None:
        super().__init__(config={"require_unlocked_shop_demand": False})

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": "v12a2_no_shop_gate",
                "model_id": MODEL_ID,
                "removed_component": "unlocked-shop product gate",
            }
        )
        return payload


def make_agent() -> NoShopGateAgent:
    return NoShopGateAgent()


_AGENT: NoShopGateAgent | None = None


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = base._step(obs)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)


def model_status() -> dict[str, Any]:
    return _AGENT.diagnostics() if _AGENT is not None else {
        "kind": "v12a2_no_shop_gate",
        "model_id": MODEL_ID,
        "status": "not_started",
    }
