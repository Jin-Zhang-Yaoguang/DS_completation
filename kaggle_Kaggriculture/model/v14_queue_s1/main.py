"""V14-QS1 serving entry: queue best response over the full S1 parent."""

from __future__ import annotations

import copy
from typing import Any

try:
    import queue_core as queue  # type: ignore
    import s1_agent as s1  # type: ignore
except ImportError:
    from kaggle_Kaggriculture.model.v14_first_principles_search import (
        prototype_queue_solver as queue,
    )
    from kaggle_Kaggriculture.model.v14_first_principles_search.alternatives.s1_wheat_squeeze import (
        main as s1,
    )


MODEL_ID = "v14_queue_s1"


class QueueS1Agent(queue.QueueBestResponseAgent):
    def __init__(self) -> None:
        super().__init__()
        self.parent = s1.make_agent()

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": MODEL_ID,
                "model_id": MODEL_ID,
                "components": [
                    "stateful_opponent_shadow_queue_best_response",
                    "inventory_neutral_wheat_squeeze",
                ],
            }
        )
        return payload


def make_agent() -> QueueS1Agent:
    return QueueS1Agent()


_AGENT: QueueS1Agent | None = None


def model_status() -> dict[str, Any]:
    if _AGENT is None:
        return {"kind": MODEL_ID, "model_id": MODEL_ID, "status": "not_started"}
    return _AGENT.diagnostics()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = int(queue._get(obs, "step", 0) or 0)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)

