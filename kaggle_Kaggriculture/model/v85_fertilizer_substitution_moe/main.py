"""V85 circular-input substitution MoE over the frozen V76 parent."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


def _load_parent():
    here = Path(__file__).resolve().parent
    candidates = (here / "parent_v76.py", here.parent / "v76_adjacent_safe_buy_lead/main.py")
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise RuntimeError("bundled V76 parent is missing")
    spec = importlib.util.spec_from_file_location("v85_bundled_parent_v76", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load bundled V76 parent")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PARENT = _load_parent()
__version__ = "v85-fertilizer-substitution-moe-rc1"


def _copy_action(action):
    action = copy.deepcopy(action or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or [])],
    }


def _collect_fertilizer_expert(obs, action):
    """Route only idle units standing on a currently collectable byproduct."""
    action = _copy_action(action)
    seat = 1 if int(obs.get("player", 0) or 0) == 1 else 0
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *(farm.get("hands") or [])]
    orders = [action["farmer"], *action["hands"]]
    for actor, (order, position) in enumerate(zip(orders, positions)):
        if not order or str(order[0]) != "PASS":
            continue
        x, y = int(position[0]), int(position[1])
        tile = farm["tiles"][y][x]
        if isinstance(tile, dict) and bool(tile.get("fertilizer_available")):
            orders[actor] = ["COLLECT_FERTILIZER"]
    action["farmer"], action["hands"] = orders[0], orders[1:]
    return action


def model_status():
    status = dict(_PARENT.model_status())
    status.update({
        "kind": "v85_fertilizer_substitution_moe",
        "model_id": "v85_fertilizer_substitution_moe",
        "parent": "v76_adjacent_safe_buy_lead",
        "lineage": "circular_input_substitution",
        "router": "idle_unit_collectable_fertilizer",
        "experts": ["frozen_v76", "collect_fertilizer"],
        "product_controller": "retain_v76_market_fail_closed",
    })
    return status


def agent(obs, configuration=None):
    return _collect_fertilizer_expert(obs, _PARENT.agent(obs, configuration))
