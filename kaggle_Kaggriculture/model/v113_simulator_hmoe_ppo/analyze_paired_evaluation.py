#!/usr/bin/env python3
"""Analyze a direct baseline/candidate evaluation on paired seed/seat blocks."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--opponent-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=20_000)
    parser.add_argument("--bootstrap-seed", type=int, default=113028)
    return parser.parse_args()


def load_rows(path: Path) -> list[dict]:
    report = json.loads(path.read_text())
    rows = report["rows"]
    keys = [(int(row["seed"]), int(row["seat"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate seed/seat rows in {path}")
    if any(row["error"] is not None or row["statuses"] != ["DONE", "DONE"] for row in rows):
        raise ValueError(f"abnormal game in {path}")
    return rows


def summarize(rows: list[dict]) -> dict:
    scores = np.asarray([row["score"] for row in rows], dtype=np.float64)
    own = np.asarray([row["candidate_reward"] for row in rows], dtype=np.float64)
    opponent = np.asarray([row["opponent_reward"] for row in rows], dtype=np.float64)
    margin = np.asarray([row["margin"] for row in rows], dtype=np.float64)
    return {
        "games": len(rows),
        "wins_ties_losses": [
            int(np.sum(scores == 1.0)),
            int(np.sum(scores == 0.5)),
            int(np.sum(scores == 0.0)),
        ],
        "score_rate": float(scores.mean()),
        "mean_own_reward": float(own.mean()),
        "mean_opponent_reward": float(opponent.mean()),
        "mean_margin": float(margin.mean()),
        "catastrophe_rate_reward_lt_3000": float(np.mean(own < 3000)),
    }


def bootstrap_ci(seed_values: np.ndarray, samples: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(seed_values), size=(samples, len(seed_values)))
    boot = seed_values[draws].mean(axis=1)
    return [float(x) for x in np.percentile(boot, [2.5, 97.5])]


def paired_metrics(
    baseline_rows: list[dict], candidate_rows: list[dict], samples: int, seed: int
) -> dict:
    baseline = {(int(row["seed"]), int(row["seat"])): row for row in baseline_rows}
    candidate = {(int(row["seed"]), int(row["seat"])): row for row in candidate_rows}
    if set(baseline) != set(candidate):
        raise ValueError("candidate seed/seat set does not match baseline")

    metric_sources = {
        "score_gain": "score",
        "own_reward_gain": "candidate_reward",
        "opponent_reward_gain": "opponent_reward",
        "margin_gain": "margin",
    }
    deltas: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for key in sorted(baseline):
        b, c = baseline[key], candidate[key]
        for output_name, row_name in metric_sources.items():
            deltas[output_name].append((key[0], float(c[row_name] - b[row_name])))

    result = {}
    for offset, name in enumerate(metric_sources, start=1):
        values = np.asarray([value for _, value in deltas[name]], dtype=np.float64)
        by_seed: dict[int, list[float]] = defaultdict(list)
        for block_seed, value in deltas[name]:
            by_seed[block_seed].append(value)
        seed_values = np.asarray(
            [np.mean(by_seed[block_seed]) for block_seed in sorted(by_seed)],
            dtype=np.float64,
        )
        result[name] = {
            "mean": float(values.mean()),
            "positive_zero_negative": [
                int(np.sum(values > 0)),
                int(np.sum(values == 0)),
                int(np.sum(values < 0)),
            ],
            "seed_block_ci95": bootstrap_ci(seed_values, samples, seed + offset),
        }
    result["games"] = len(baseline)
    result["seed_blocks"] = len({key[0] for key in baseline})
    return result


def main() -> None:
    args = parse_args()
    baseline_rows = load_rows(args.baseline)
    candidate_rows = load_rows(args.candidate)
    baseline = summarize(baseline_rows)
    candidate = summarize(candidate_rows)
    paired = paired_metrics(
        baseline_rows,
        candidate_rows,
        args.bootstrap_samples,
        args.bootstrap_seed,
    )

    own_ci = paired["own_reward_gain"]["seed_block_ci95"]
    margin_ci = paired["margin_gain"]["seed_block_ci95"]
    score_non_degradation = candidate["score_rate"] >= baseline["score_rate"]
    economy_improvement = own_ci[0] > 0.0
    margin_improvement = margin_ci[0] >= 0.0
    catastrophe_non_degradation = (
        candidate["catastrophe_rate_reward_lt_3000"]
        <= baseline["catastrophe_rate_reward_lt_3000"]
    )
    actual_gold_win = candidate["wins_ties_losses"][0] > 0
    specialist_pass = bool(
        score_non_degradation
        and economy_improvement
        and margin_improvement
        and catastrophe_non_degradation
    )
    result = {
        "schema": "kaggriculture-v113-paired-direct-evaluation-v1",
        "protocol": {
            "opponent": args.opponent_name,
            "fresh_seed_blocks": paired["seed_blocks"],
            "dual_seat": True,
            "bootstrap_unit": "seed_block_two_seats",
            "bootstrap_samples": args.bootstrap_samples,
            "catastrophe_definition": "own_reward < 3000",
        },
        "baseline": baseline,
        "candidate_name": args.candidate_name,
        "candidate": candidate,
        "paired_vs_baseline": paired,
        "gold_dev_gate": {
            "score_non_degradation": score_non_degradation,
            "own_reward_ci_lower_gt_zero": economy_improvement,
            "margin_ci_lower_ge_zero": margin_improvement,
            "catastrophe_non_degradation": catastrophe_non_degradation,
            "actual_gold_win_observed": actual_gold_win,
            "specialist_passed": specialist_pass,
            "global_gold_candidate_passed": bool(specialist_pass and actual_gold_win),
            "decision": (
                "ADVANCE_AS_GLOBAL_GOLD_CANDIDATE"
                if specialist_pass and actual_gold_win
                else "REGISTER_AS_TRAINING_SPECIALIST_ONLY"
                if specialist_pass
                else "REJECT_GOLD_DEV"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
