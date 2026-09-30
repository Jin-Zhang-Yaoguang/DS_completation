#!/usr/bin/env python3
"""Audit a static whole-agent mixture using development-only evidence.

This analysis deliberately reads only the three already-open V11 development
rounds and the already-open V12 v3/v4 screen controls.  It never reads a
formal/test result.  The output is a decision artifact, not a serving policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.optimize import linprog


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
LEAGUE_ROOT = MODEL_ROOT / "v11_iterative_league" / "runs"
SCREEN_ROOT = MODEL_ROOT / "v12_validation"
OUTPUT = HERE / "mixture_audit.json"

COMMON_SUPPORT = (
    "baseline_v5",
    "baseline_v8",
    "learned_router",
)
PROPOSED_SUPPORT = (
    "baseline_v5",
    "baseline_v8",
    "learned_router",
    "r002_learned_router_topday_animal_throttle",
)
R002 = "r002_learned_router_topday_animal_throttle"
V8 = "baseline_v8"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _weights(values: Sequence[float], support: Sequence[str]) -> dict[str, float]:
    return {name: float(max(0.0, value)) for name, value in zip(support, values)}


def _maximin(matrix: np.ndarray) -> tuple[np.ndarray, float]:
    """Maximise the minimum expected score over columns."""

    experts, opponents = matrix.shape
    objective = np.r_[np.zeros(experts), -1.0]
    upper = np.c_[-matrix.T, np.ones(opponents)]
    equality = np.r_[np.ones(experts), 0.0][None, :]
    result = linprog(
        objective,
        A_ub=upper,
        b_ub=np.zeros(opponents),
        A_eq=equality,
        b_eq=[1.0],
        bounds=[(0.0, 1.0)] * experts + [(None, None)],
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"maximin optimisation failed: {result.message}")
    weights = np.where(np.abs(result.x[:-1]) < 1e-12, 0.0, result.x[:-1])
    return weights, float(result.x[-1])


def _score_stats(
    matrix: np.ndarray,
    weights: np.ndarray,
    opponents: Sequence[str],
) -> dict[str, Any]:
    scores = weights @ matrix
    worst_index = int(np.argmin(scores))
    return {
        "overall_score": float(np.mean(scores)),
        "worst_opponent_score": float(scores[worst_index]),
        "worst_opponent": opponents[worst_index],
        "opponent_scores": {
            opponent: float(score) for opponent, score in zip(opponents, scores)
        },
    }


def _best_fixed(
    matrix: np.ndarray,
    support: Sequence[str],
    opponents: Sequence[str],
) -> dict[str, Any]:
    rows = []
    for index, name in enumerate(support):
        weight = np.zeros(len(support), dtype=np.float64)
        weight[index] = 1.0
        rows.append(
            {
                "expert": name,
                **_score_stats(matrix, weight, opponents),
            }
        )
    by_overall = max(rows, key=lambda row: (row["overall_score"], row["worst_opponent_score"]))
    by_worst = max(rows, key=lambda row: (row["worst_opponent_score"], row["overall_score"]))
    return {"by_overall": by_overall, "by_worst": by_worst, "all": rows}


def _matrix(
    summary: Mapping[str, Any],
    support: Sequence[str],
    opponents: Sequence[str],
) -> np.ndarray:
    score_matrix = summary["score_matrix"]
    return np.asarray(
        [[float(score_matrix[expert][opponent]) for opponent in opponents] for expert in support],
        dtype=np.float64,
    )


def _loo_common(rounds: Mapping[int, Mapping[str, Any]]) -> dict[str, Any]:
    common_opponents = sorted(
        set.intersection(*(set(rounds[index]["models"]) for index in sorted(rounds)))
    )
    matrices = {
        index: _matrix(summary, COMMON_SUPPORT, common_opponents)
        for index, summary in rounds.items()
    }
    folds = []
    fitted_weights = []
    for holdout in sorted(rounds):
        training = np.mean(
            [matrix for index, matrix in matrices.items() if index != holdout], axis=0
        )
        weights, training_floor = _maximin(training)
        fitted_weights.append(weights)
        holdout_stats = _score_stats(matrices[holdout], weights, common_opponents)
        fixed = _best_fixed(matrices[holdout], COMMON_SUPPORT, common_opponents)
        folds.append(
            {
                "held_out_round": holdout,
                "weights": _weights(weights, COMMON_SUPPORT),
                "training_maximin_floor": training_floor,
                "holdout": holdout_stats,
                "holdout_best_fixed": fixed,
                "delta_vs_best_fixed_overall": float(
                    holdout_stats["overall_score"] - fixed["by_overall"]["overall_score"]
                ),
                "delta_vs_best_fixed_worst": float(
                    holdout_stats["worst_opponent_score"]
                    - fixed["by_worst"]["worst_opponent_score"]
                ),
            }
        )
    pairwise_l1 = [
        float(np.abs(fitted_weights[left] - fitted_weights[right]).sum())
        for left in range(len(fitted_weights))
        for right in range(left + 1, len(fitted_weights))
    ]
    return {
        "support": list(COMMON_SUPPORT),
        "opponents": common_opponents,
        "note": (
            "r002 was activated only in Round 3, so honest three-fold LOO is "
            "identifiable only for the support common to all three rounds."
        ),
        "folds": folds,
        "max_pairwise_weight_l1": max(pairwise_l1, default=0.0),
        "all_folds_non_degenerate_mixture": all(
            sum(value > 1e-9 for value in row["weights"].values()) >= 2 for row in folds
        ),
        "strictly_beats_best_fixed_overall_every_fold": all(
            row["delta_vs_best_fixed_overall"] > 0.0 for row in folds
        ),
        "strictly_beats_best_fixed_worst_every_fold": all(
            row["delta_vs_best_fixed_worst"] > 0.0 for row in folds
        ),
    }


def _round3_proposed(round3: Mapping[str, Any]) -> dict[str, Any]:
    # Exclude only the exact r002 row from the opponent pool.  This avoids a
    # trivial self-play 0.5 floor while retaining all other support experts as
    # possible adversaries.
    opponents = [name for name in round3["models"] if name != R002]
    matrix = _matrix(round3, PROPOSED_SUPPORT, opponents)
    weights, floor = _maximin(matrix)
    fitted = _score_stats(matrix, weights, opponents)
    fixed = _best_fixed(matrix, PROPOSED_SUPPORT, opponents)

    forced_half = np.zeros(len(PROPOSED_SUPPORT), dtype=np.float64)
    forced_half[PROPOSED_SUPPORT.index(V8)] = 0.5
    forced_half[PROPOSED_SUPPORT.index(R002)] = 0.5
    forced_stats = _score_stats(matrix, forced_half, opponents)

    external = [name for name in opponents if name not in PROPOSED_SUPPORT]
    external_matrix = _matrix(round3, PROPOSED_SUPPORT, external)
    external_weights, external_floor = _maximin(external_matrix)
    external_stats = _score_stats(external_matrix, external_weights, external)

    return {
        "support": list(PROPOSED_SUPPORT),
        "opponents_excluding_exact_r002": opponents,
        "maximin_weights": _weights(weights, PROPOSED_SUPPORT),
        "maximin_floor": floor,
        "maximin": fitted,
        "best_fixed": fixed,
        "forced_r002_v8_50_50": {
            "weights": _weights(forced_half, PROPOSED_SUPPORT),
            **forced_stats,
            "delta_vs_pure_r002_overall": float(
                forced_stats["overall_score"] - fixed["by_overall"]["overall_score"]
            ),
            "delta_vs_pure_r002_worst": float(
                forced_stats["worst_opponent_score"]
                - fixed["by_worst"]["worst_opponent_score"]
            ),
        },
        "external_opponents_only": {
            "opponents": external,
            "maximin_weights": _weights(external_weights, PROPOSED_SUPPORT),
            "maximin_floor": external_floor,
            "maximin": external_stats,
            "best_fixed": _best_fixed(external_matrix, PROPOSED_SUPPORT, external),
        },
    }


def _screen_controls() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for version in ("v3", "v4"):
        path = (
            SCREEN_ROOT
            / f"runs_{version}"
            / "screen_control"
            / f"{R002}__vs__{V8}"
            / "summary.json"
        )
        summary = _load_json(path)
        pair = summary["pairs"][f"{R002}__vs__{V8}"]
        result[version] = {
            "path": str(path),
            "sha256": _sha256_file(path),
            "games": int(pair["valid_games"]),
            "paired_seeds": int(pair["paired_seeds"]),
            "r002_score": float(pair["paired_score_rate_a"]),
            "r002_ci95": [float(value) for value in pair["paired_score_ci95"]],
            "errors": int(pair["errors"]),
            "not_done": int(pair["not_done"]),
        }
    return result


def _public_initial_observation(obs: Mapping[str, Any]) -> dict[str, Any]:
    # player/private are agent-specific, remainingOverageTime is runtime timing,
    # and step is fixed at zero.  The rest is the reproducible public state.
    return {
        key: obs[key]
        for key in sorted(obs)
        if key not in {"player", "private", "remainingOverageTime", "step"}
    }


def _entropy_audit(panels: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    from kaggle_environments import make

    source_seeds = sorted(
        {
            int(record["seed"])
            for panel in panels
            for record in panel["records"]
        }
    )
    hashes: set[str] = set()
    configuration_seed_values: set[str] = set()
    seat_player_values: set[int] = set()
    for seed in source_seeds:
        # Match the evaluator's explicit process RNG seeding.  It does not
        # expose that value to the agent at step zero.
        random.seed(seed * 104729)
        np.random.seed(seed % (2**32 - 1))
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.reset(2)
        configuration_seed_values.add(repr(env.configuration.get("seed")))
        for state in env.state:
            obs = dict(state.observation)
            seat_player_values.add(int(obs["player"]))
            hashes.add(hashlib.sha256(_canonical(_public_initial_observation(obs))).hexdigest())

    return {
        "source_seeds": len(source_seeds),
        "seat_observations": len(source_seeds) * 2,
        "unique_public_initial_observation_hashes": len(hashes),
        "public_initial_observation_hashes": sorted(hashes),
        "configuration_seed_values_visible_to_agent_runner": sorted(configuration_seed_values),
        "player_values": sorted(seat_player_values),
        "player_is_fair_entropy": False,
        "player_rejection_reason": (
            "seat is a two-valued, opponent-predictable role label rather than "
            "episode randomness; it cannot implement general weights and a "
            "knowledgeable opponent can condition on it"
        ),
        "fair_reproducible_step0_entropy_available": False,
    }


def main() -> None:
    round_paths = {
        index: LEAGUE_ROOT / f"round_{index:03d}" / "pairwise_summary.json"
        for index in (1, 2, 3)
    }
    panel_paths = {
        index: LEAGUE_ROOT / f"round_{index:03d}" / "panel.json"
        for index in (1, 2, 3)
    }
    rounds = {index: _load_json(path) for index, path in round_paths.items()}
    panels = [_load_json(path) for path in panel_paths.values()]

    loo = _loo_common(rounds)
    proposed = _round3_proposed(rounds[3])
    screens = _screen_controls()
    entropy = _entropy_audit(panels)

    proposed_weights = proposed["maximin_weights"]
    mandatory_support_positive = (
        proposed_weights[R002] > 1e-9 and proposed_weights[V8] > 1e-9
    )
    gates = {
        "honest_r002_three_round_loo_identifiable": False,
        "common_support_loo_is_non_degenerate_mixture": bool(
            loo["all_folds_non_degenerate_mixture"]
        ),
        "common_support_loo_strict_overall_gain_every_fold": bool(
            loo["strictly_beats_best_fixed_overall_every_fold"]
        ),
        "common_support_loo_strict_worst_gain_every_fold": bool(
            loo["strictly_beats_best_fixed_worst_every_fold"]
        ),
        "round3_maximin_keeps_r002_and_v8": mandatory_support_positive,
        "fair_reproducible_step0_entropy_available": bool(
            entropy["fair_reproducible_step0_entropy_available"]
        ),
    }
    result = {
        "schema": "kaggriculture-v12-static-minimax-mixture-audit-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "rejected",
        "decision": (
            "Do not implement, package, validate on formal/test, or submit the "
            "static mixture. Existing development evidence selects a pure expert, "
            "and step-zero observation exposes no fair reproducible entropy."
        ),
        "data_boundary": {
            "used": [
                *[str(path) for path in round_paths.values()],
                *[str(path) for path in panel_paths.values()],
                str(SCREEN_ROOT / "runs_v3" / "screen_control"),
                str(SCREEN_ROOT / "runs_v4" / "screen_control"),
            ],
            "formal_or_test_accessed": False,
            "round_file_sha256": {
                str(index): _sha256_file(path) for index, path in round_paths.items()
            },
            "panel_file_sha256": {
                str(index): _sha256_file(path) for index, path in panel_paths.items()
            },
        },
        "common_support_leave_one_round_out": loo,
        "proposed_support_round3": proposed,
        "already_open_screen_controls": screens,
        "step0_entropy_audit": entropy,
        "acceptance_gates": gates,
        "all_acceptance_gates_pass": all(gates.values()),
        "artifacts_intentionally_absent": [
            "main.py",
            "submission.tar.gz",
            "registry_entry.json",
            "formal results",
        ],
    }
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "all_acceptance_gates_pass": result["all_acceptance_gates_pass"],
        "output": str(OUTPUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
