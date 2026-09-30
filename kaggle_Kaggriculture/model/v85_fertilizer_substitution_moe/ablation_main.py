"""V85 mechanism ablation: identical wrapper with fertilizer expert disabled."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_parent():
    here = Path(__file__).resolve().parent
    candidates = (here / "parent_v76.py", here.parent / "v76_adjacent_safe_buy_lead/main.py")
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise RuntimeError("bundled V76 parent is missing")
    spec = importlib.util.spec_from_file_location("v85_ablation_parent_v76", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


_PARENT = _load_parent()
__version__ = "v85-fertilizer-substitution-ablation-rc1"


def model_status():
    status = dict(_PARENT.model_status())
    status.update({"kind": "v85_fertilizer_substitution_ablation",
                   "model_id": "v85_fertilizer_substitution_ablation",
                   "parent": "v76_adjacent_safe_buy_lead",
                   "collect_fertilizer_expert": False})
    return status


def agent(obs, configuration=None):
    return _PARENT.agent(obs, configuration)
