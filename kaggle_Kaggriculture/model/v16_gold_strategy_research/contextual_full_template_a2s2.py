"""One-shot contextual router over finance/resource-complete production plans.

This is a development candidate, not a submission package.  It shadows the
current A2 anchor and the complete V8 Kawa expert from step 0.  The two experts
must emit the same actions through step 71; at step 72 the public opponent
layout chooses exactly one expert for the rest of the season.

The threshold was frozen after a 3-replay-per-family discovery screen:
opponent MELON tiles >= 10 selects V8, otherwise A2.  It is intentionally
small and auditable; no team name, seed, replay id, private opponent state or
future information is available to the selector.
"""

from __future__ import annotations

import copy
import importlib.util
import itertools
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
SWITCH_STEP = 72
MELON_THRESHOLD = 10
_SERIAL = itertools.count()

# Six complete templates were screened.  Only two non-dominated templates are
# retained by the frozen candidate router; the other four remain provenance.
SEARCH_TEMPLATE_CATALOG = (
    "a2_current_complete",
    "v8_kawa_adaptive_complete",
    "v9_forced_10c4s_3q",
    "v9_forced_8c6s_3q",
    "v9_forced_6c8s_3q",
    "v9_forced_6c12s_4q_second_yarn",
)
ACTIVE_TEMPLATES = ("a2_current_complete", "v8_kawa_adaptive_complete")


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _seat(obs: Any) -> int:
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _copy_action(action: Any) -> dict[str, list[Any]]:
    raw = copy.deepcopy(action or {})
    if not isinstance(raw, Mapping):
        raise TypeError("complete expert returned a non-mapping action")
    return {
        "farmer": list(_get(raw, "farmer", []) or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (_get(raw, "hands", []) or [])],
        "market": [list(order or []) for order in (_get(raw, "market", []) or [])],
    }


def _load_module(relative_path: str, tag: str) -> ModuleType:
    path = MODEL_ROOT / relative_path
    name = f"_v16_a2s2_{tag}_{next(_SERIAL)}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load complete expert: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public_opponent_tile_counts(obs: Any) -> dict[str, int]:
    """Count only publicly visible opponent crops/animals/structures."""
    seat = _seat(obs)
    farms = list(_get(obs, "farms", []) or [])
    opponent = farms[1 - seat] if len(farms) == 2 else {}
    counts: dict[str, int] = {}
    for row in list(_get(opponent, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, Mapping):
                continue
            value = tile.get("crop") or tile.get("animal") or tile.get("kind")
            if value:
                key = str(value)
                counts[key] = counts.get(key, 0) + 1
    return counts


class ContextualFullTemplateAgent:
    """Shadow two complete experts and make one irreversible public decision."""

    def __init__(self) -> None:
        self.a2 = _load_module("v1_adaptive_market/main.py", "a2")
        self.v8 = _load_module("v8_kawa_lead2_slot/main.py", "v8")
        self._state = {0: self._blank_state(), 1: self._blank_state()}

    @staticmethod
    def _blank_state() -> dict[str, Any]:
        return {
            "last_step": -1,
            "seen_prefix": set(),
            "prefix_match": True,
            "first_mismatch": None,
            "selected": None,
            "reason": "not_reached",
            "opponent_tiles": {},
        }

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
        del configuration
        seat = _seat(obs)
        step = int(_get(obs, "step", 0) or 0)
        state = self._state[seat]
        if step == 0 or step < int(state["last_step"]):
            state = self._blank_state()
            self._state[seat] = state
        state["last_step"] = step

        anchor_action = _copy_action(self.a2.agent(obs))
        v8_action = _copy_action(self.v8.agent(obs))
        if step < SWITCH_STEP:
            state["seen_prefix"].add(step)
            if anchor_action != v8_action:
                state["prefix_match"] = False
                if state["first_mismatch"] is None:
                    state["first_mismatch"] = step
            return anchor_action

        if state["selected"] is None:
            complete = state["seen_prefix"] == set(range(SWITCH_STEP))
            if not complete or not state["prefix_match"]:
                state["selected"] = "a2_current_complete"
                state["reason"] = "prefix_guard_fallback"
            else:
                counts = public_opponent_tile_counts(obs)
                state["opponent_tiles"] = counts
                if counts.get("MELON", 0) >= MELON_THRESHOLD:
                    state["selected"] = "v8_kawa_adaptive_complete"
                    state["reason"] = "public_opponent_melon_ge_10"
                else:
                    state["selected"] = "a2_current_complete"
                    state["reason"] = "public_opponent_melon_lt_10"

        if state["selected"] == "v8_kawa_adaptive_complete":
            return v8_action
        return anchor_action

    def diagnostics(self, seat: int) -> dict[str, Any]:
        state = self._state[1 if int(seat) == 1 else 0]
        return {
            "switch_step": SWITCH_STEP,
            "melon_threshold": MELON_THRESHOLD,
            "active_templates": list(ACTIVE_TEMPLATES),
            "search_template_catalog": list(SEARCH_TEMPLATE_CATALOG),
            "prefix_complete": state["seen_prefix"] == set(range(SWITCH_STEP)),
            "prefix_match": bool(state["prefix_match"]),
            "first_mismatch": state["first_mismatch"],
            "selected": state["selected"],
            "reason": state["reason"],
            "opponent_tiles": dict(state["opponent_tiles"]),
        }


def make_agent() -> ContextualFullTemplateAgent:
    return ContextualFullTemplateAgent()


_DEFAULT = make_agent()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    return _DEFAULT(obs, configuration)

