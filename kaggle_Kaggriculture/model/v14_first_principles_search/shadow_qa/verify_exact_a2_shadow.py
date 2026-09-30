"""Independent truth-oracle QA for V14's stateful A2 opponent shadow.

This script deliberately uses only the three synthetic seeds that were already
published by ``v12a2_no_shop_gate/package_qa.py``.  It never opens or consumes
the V14 screen, confirmatory, or test panels.

The candidate module is not instrumented or modified.  Instead, the internal
``opponent_shadow`` callable is wrapped so its injected private observation and
predicted action can be compared, step for step, with the observation and
action of the real opposite-seat A2 agent in the same live environment.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any, Callable

import numpy as np


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2
from kaggle_Kaggriculture.model.v14_first_principles_search import (
    prototype_queue_solver as candidate_module,
)


SCHEMA = "kaggriculture-v14-exact-a2-shadow-qa-1"
QA_SEEDS = (93451031, 93451032, 93451033)
QA_SEED_PROVENANCE = (
    WORKSPACE
    / "kaggle_Kaggriculture"
    / "model"
    / "v12a2_no_shop_gate"
    / "package_qa.py"
)
PROTOTYPE = HERE.parent / "prototype_queue_solver.py"
OUTPUT = HERE / "exact_a2_shadow_qa.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plain(value: Any) -> Any:
    """Losslessly canonicalize Kaggle Struct/dict/list state for exact QA."""

    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    items = getattr(value, "items", None)
    if callable(items):
        return _plain(dict(items()))
    raise TypeError(f"unsupported state value for exact comparison: {type(value)!r}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _step(obs: Any) -> int:
    if isinstance(obs, Mapping):
        return int(obs.get("step", 0) or 0)
    return int(getattr(obs, "step", 0) or 0)


def _player(obs: Any) -> int:
    if isinstance(obs, Mapping):
        return int(obs.get("player", 0) or 0)
    return int(getattr(obs, "player", 0) or 0)


def _private(obs: Any) -> Any:
    if isinstance(obs, Mapping):
        return obs.get("private", {}) or {}
    return getattr(obs, "private", {}) or {}


def _first_difference(left: Any, right: Any, path: str = "$") -> dict[str, Any] | None:
    left = _plain(left)
    right = _plain(right)
    if type(left) is not type(right):
        return {"path": path, "predicted": left, "actual": right, "reason": "type"}
    if isinstance(left, dict):
        left_keys = set(left)
        right_keys = set(right)
        if left_keys != right_keys:
            return {
                "path": path,
                "predicted_only_keys": sorted(left_keys - right_keys),
                "actual_only_keys": sorted(right_keys - left_keys),
                "reason": "keys",
            }
        for key in sorted(left):
            difference = _first_difference(left[key], right[key], f"{path}.{key}")
            if difference is not None:
                return difference
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return {
                "path": path,
                "predicted_length": len(left),
                "actual_length": len(right),
                "reason": "length",
            }
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            difference = _first_difference(left_item, right_item, f"{path}[{index}]")
            if difference is not None:
                return difference
        return None
    if left != right:
        return {"path": path, "predicted": left, "actual": right, "reason": "value"}
    return None


class RecordingAgent:
    """Record input private state and output action without changing behavior."""

    def __init__(self, handle: Callable[..., Any]) -> None:
        self.handle = handle
        self.records: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        private = copy.deepcopy(_plain(_private(obs)))
        action = self.handle(obs, configuration)
        canonical_action = candidate_module._canonical_action(action)
        self.records.append(
            {
                "step": _step(obs),
                "player": _player(obs),
                "private": private,
                "private_sha256": _digest(private),
                "action": _plain(canonical_action),
                "action_sha256": _digest(canonical_action),
            }
        )
        return action

    def __getattr__(self, name: str) -> Any:
        # QueueBestResponseAgent asks its shadow for branch diagnostics.  Full
        # delegation keeps the wrapper behaviorally transparent.
        return getattr(self.handle, name)


def _run_game(seed: int, candidate_seat: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from kaggle_environments import make

    random.seed(seed * 104729 + candidate_seat * 1009)
    np.random.seed((seed + candidate_seat * 65537) % (2**32 - 1))

    candidate = candidate_module.make_agent()
    predicted = RecordingAgent(candidate.opponent_shadow)
    candidate.opponent_shadow = predicted
    actual = RecordingAgent(a2.make_agent())
    agents = [candidate, actual] if candidate_seat == 0 else [actual, candidate]
    steps = make("kaggriculture", configuration={"seed": seed}, debug=False).run(agents)
    final = steps[-1]

    predicted_by_step = {int(row["step"]): row for row in predicted.records}
    actual_by_step = {int(row["step"]): row for row in actual.records}
    all_steps = sorted(set(predicted_by_step) | set(actual_by_step))
    comparisons: list[dict[str, Any]] = []
    for step in all_steps:
        predicted_row = predicted_by_step.get(step)
        actual_row = actual_by_step.get(step)
        if predicted_row is None or actual_row is None:
            comparisons.append(
                {
                    "step": step,
                    "private_exact": False,
                    "action_exact": False,
                    "missing_predicted": predicted_row is None,
                    "missing_actual": actual_row is None,
                    "first_private_difference": {"reason": "missing_record"},
                    "first_action_difference": {"reason": "missing_record"},
                }
            )
            continue
        private_exact = predicted_row["private"] == actual_row["private"]
        action_exact = predicted_row["action"] == actual_row["action"]
        comparisons.append(
            {
                "step": step,
                "day_boundary_input": step > 0 and step % 24 == 0,
                "predicted_player": predicted_row["player"],
                "actual_player": actual_row["player"],
                "private_exact": private_exact,
                "action_exact": action_exact,
                "predicted_private_sha256": predicted_row["private_sha256"],
                "actual_private_sha256": actual_row["private_sha256"],
                "predicted_action_sha256": predicted_row["action_sha256"],
                "actual_action_sha256": actual_row["action_sha256"],
                "first_private_difference": (
                    None
                    if private_exact
                    else _first_difference(predicted_row["private"], actual_row["private"])
                ),
                "first_action_difference": (
                    None
                    if action_exact
                    else _first_difference(predicted_row["action"], actual_row["action"])
                ),
            }
        )

    first_private_mismatch = next(
        (row for row in comparisons if not row["private_exact"]), None
    )
    first_action_mismatch = next(
        (row for row in comparisons if not row["action_exact"]), None
    )
    diagnostics = candidate.diagnostics()
    summary = {
        "seed": seed,
        "candidate_seat": candidate_seat,
        "environment_steps": len(steps),
        "predicted_calls": len(predicted.records),
        "actual_calls": len(actual.records),
        "compared_calls": len(comparisons),
        "private_exact_calls": sum(bool(row["private_exact"]) for row in comparisons),
        "action_exact_calls": sum(bool(row["action_exact"]) for row in comparisons),
        "day_boundary_calls": sum(bool(row.get("day_boundary_input")) for row in comparisons),
        "day_boundary_private_exact_calls": sum(
            bool(row.get("day_boundary_input") and row["private_exact"]) for row in comparisons
        ),
        "day_boundary_action_exact_calls": sum(
            bool(row.get("day_boundary_input") and row["action_exact"]) for row in comparisons
        ),
        "first_private_mismatch": first_private_mismatch,
        "first_action_mismatch": first_action_mismatch,
        "candidate_reordered_steps": int(diagnostics["reordered_steps"]),
        "candidate_shadow_trusted": bool(diagnostics["shadow_trusted"]),
        "candidate_conformance_steps": int(diagnostics["conformance_steps"]),
        "candidate_shadow_faults": int(diagnostics["shadow_faults"]),
        "candidate_shadow_update_errors": int(diagnostics["shadow_update_errors"]),
        "statuses": [str(state.status) for state in final],
        "rewards": [float(state.reward or 0.0) for state in final],
    }
    return summary, comparisons


def main() -> None:
    provenance_text = QA_SEED_PROVENANCE.read_text(encoding="utf-8")
    if not all(str(seed) in provenance_text for seed in QA_SEEDS):
        raise RuntimeError("QA seed provenance changed; refusing to consume unproven seeds")

    games: list[dict[str, Any]] = []
    mismatch_evidence: list[dict[str, Any]] = []
    for seed in QA_SEEDS:
        for candidate_seat in (0, 1):
            game, comparisons = _run_game(seed, candidate_seat)
            games.append(game)
            for comparison in comparisons:
                if not comparison["private_exact"] or not comparison["action_exact"]:
                    mismatch_evidence.append(
                        {
                            "seed": seed,
                            "candidate_seat": candidate_seat,
                            **comparison,
                        }
                    )
                    break

    compared_calls = sum(row["compared_calls"] for row in games)
    private_exact_calls = sum(row["private_exact_calls"] for row in games)
    action_exact_calls = sum(row["action_exact_calls"] for row in games)
    boundary_calls = sum(row["day_boundary_calls"] for row in games)
    boundary_private_exact = sum(row["day_boundary_private_exact_calls"] for row in games)
    boundary_action_exact = sum(row["day_boundary_action_exact_calls"] for row in games)
    checks = {
        "three_previously_exposed_qa_seeds": len(QA_SEEDS) == 3,
        "both_candidate_seats": {row["candidate_seat"] for row in games} == {0, 1},
        "minimum_4314_compared_calls": compared_calls >= 3 * 2 * 719,
        "all_private_states_exact": private_exact_calls == compared_calls,
        "all_actions_exact": action_exact_calls == compared_calls,
        "all_day_boundary_private_states_exact": boundary_private_exact == boundary_calls,
        "all_day_boundary_actions_exact": boundary_action_exact == boundary_calls,
        "all_games_done": all(row["statuses"] == ["DONE", "DONE"] for row in games),
        "no_candidate_shadow_faults": all(row["candidate_shadow_faults"] == 0 for row in games),
        "no_candidate_shadow_update_errors": all(
            row["candidate_shadow_update_errors"] == 0 for row in games
        ),
        "candidate_shadow_trusted_at_end": all(row["candidate_shadow_trusted"] for row in games),
        "candidate_intervention_exercised": sum(row["candidate_reordered_steps"] for row in games) > 0,
    }
    result = {
        "schema": SCHEMA,
        "scope": {
            "qa_only": True,
            "fresh_v14_screen_consumed": False,
            "fresh_v14_confirmatory_consumed": False,
            "test_consumed": False,
            "seed_provenance": str(QA_SEED_PROVENANCE),
            "seeds": list(QA_SEEDS),
            "candidate_seats": [0, 1],
        },
        "artifacts": {
            "prototype_path": str(PROTOTYPE),
            "prototype_sha256": _sha256(PROTOTYPE),
            "qa_script_sha256": _sha256(Path(__file__).resolve()),
            "seed_provenance_sha256": _sha256(QA_SEED_PROVENANCE),
        },
        "aggregate": {
            "games": len(games),
            "compared_calls": compared_calls,
            "private_exact_calls": private_exact_calls,
            "private_exact_rate": private_exact_calls / compared_calls,
            "action_exact_calls": action_exact_calls,
            "action_exact_rate": action_exact_calls / compared_calls,
            "day_boundary_calls": boundary_calls,
            "day_boundary_private_exact_calls": boundary_private_exact,
            "day_boundary_action_exact_calls": boundary_action_exact,
            "candidate_reordered_steps": sum(row["candidate_reordered_steps"] for row in games),
            "candidate_shadow_faults": sum(row["candidate_shadow_faults"] for row in games),
            "candidate_shadow_update_errors": sum(
                row["candidate_shadow_update_errors"] for row in games
            ),
            "first_mismatch": mismatch_evidence[0] if mismatch_evidence else None,
        },
        "checks": checks,
        "go": all(checks.values()),
        "games": games,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["go"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
