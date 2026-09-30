"""Q2 development variant: stateful A2 shadow without public equality gate.

The full public-production equality check was useful for the old
copied-private prototype, but it is redundant after exact stateful shadow
conformance.  Q2 keeps the 72-step full public conformance gate, the V8/V8
action gate, and the conservative clone-distance cap <=4.  It only allows the
independently advanced opposite-seat A2 shadow to operate after benign public
production paths diverge within that cap.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_core():
    name = "v14_queue_solver_no_mirror_core"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().with_name("prototype_queue_solver.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load queue core from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = _load_core()
MODEL_ID = "v14_queue_stateful_no_mirror"


class QueueStatefulNoMirrorAgent(core.QueueBestResponseAgent):
    def __init__(self) -> None:
        super().__init__(require_public_mirror=False)

    def diagnostics(self):
        payload = super().diagnostics()
        payload["kind"] = MODEL_ID
        payload["model_id"] = MODEL_ID
        payload["removed_gate"] = "full public-production equality"
        payload["retained_gate"] = "clone_distance<=4"
        return payload


def make_agent() -> QueueStatefulNoMirrorAgent:
    return QueueStatefulNoMirrorAgent()
