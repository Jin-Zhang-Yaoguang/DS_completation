"""Development-only combination of stateful queue BR and WHEAT squeeze."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
from typing import Any


def _load_sibling(module_name: str, path: Path):
    """Load by file path so spawned evaluator workers need no repo package path."""
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_HERE = Path(__file__).resolve().parent
queue = _load_sibling("v14_queue_solver_local", _HERE / "prototype_queue_solver.py")
s1 = _load_sibling(
    "v14_s1_wheat_squeeze_local", _HERE / "alternatives" / "s1_wheat_squeeze" / "main.py"
)


MODEL_ID = "v14_queue_shadow_plus_wheat_squeeze"


class QueueShadowPlusWheatSqueeze(queue.QueueBestResponseAgent):
    """Use S1 as the complete own parent and keep A2 as opponent shadow."""

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


def make_agent() -> QueueShadowPlusWheatSqueeze:
    return QueueShadowPlusWheatSqueeze()
