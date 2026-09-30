"""V14-Q2 serving entry: stateful A2 shadow without the mirror heuristic."""

from __future__ import annotations

from typing import Any

try:
    import queue_core as core  # type: ignore
except ImportError:
    from kaggle_Kaggriculture.model.v14_first_principles_search import (
        prototype_queue_solver as core,
    )


MODEL_ID = "v14_queue_stateful_no_mirror"


class QueueStatefulNoMirrorAgent(core.QueueBestResponseAgent):
    def __init__(self) -> None:
        super().__init__(require_public_mirror=False)

    def diagnostics(self) -> dict[str, Any]:
        payload = super().diagnostics()
        payload["kind"] = MODEL_ID
        payload["model_id"] = MODEL_ID
        payload["removed_gate"] = "full public-production equality"
        payload["retained_gate"] = "clone_distance<=4"
        return payload


def make_agent() -> QueueStatefulNoMirrorAgent:
    return QueueStatefulNoMirrorAgent()


_AGENT: QueueStatefulNoMirrorAgent | None = None


def model_status() -> dict[str, Any]:
    if _AGENT is None:
        return {"kind": MODEL_ID, "model_id": MODEL_ID, "status": "not_started"}
    return _AGENT.diagnostics()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = int(core._get(obs, "step", 0) or 0)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)
