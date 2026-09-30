"""Diagnostic only: unmodified selected route, explicitly non-promotable."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "v120_hierarchical_top5_distillation/main.py"
SPEC = importlib.util.spec_from_file_location("v120_diagnostic_source", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ROUTE = MODULE._V120_DISTILLED_ROUTE


def agent(obs, configuration=None):
    del configuration
    step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
    action = copy.deepcopy(ROUTE[min(step, len(ROUTE) - 1)])
    seat = 1 if int(obs.get("player", 0) or 0) == 1 else 0
    expected = len((obs.get("farms") or [{}, {}])[seat].get("hands") or [])
    hands = list(action.get("hands") or [])
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    action["hands"] = hands[:expected]
    return action


def model_status():
    return {"diagnostic_only": True, "tape": True, "promotable": False}
