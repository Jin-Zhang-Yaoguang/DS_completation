#!/usr/bin/env python3
"""Analyze paired mixed-opponent screens with seed-block bootstrap intervals."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", action="append", nargs=2, metavar=("NAME", "REPORT"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=20_000)
    parser.add_argument("--bootstrap-seed", type=int, default=113027)
    parser.add_argument(
        "--require-catastrophe-strict-improvement",
        action="store_true",
        help="Require catastrophe rate to be strictly below the baseline.",
    )
    parser.add_argument(
        "--require-positive-economic-ci",
        action="store_true",
        help="Require the lower CI bound of reward or margin gain to exceed zero.",
    )
    parser.add_argument(
        "--require-exploiter-nondegradation",
        action="store_true",
        help="Require non-negative mean score gain on the exploiter layer.",
    )
    return parser.parse_args()


def load_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    rows = report["rows"]
    keys = [(int(row["seed"]), int(row["seat"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate seed/seat rows in {path}")
    if any(row["error"] is not None or row["statuses"] != ["DONE", "DONE"] for row in rows):
        raise ValueError(f"abnormal game in {path}")
    return report


def wdl(rows: list[dict]) -> list[int]:
    return [
        sum(row["score"] == 1.0 for row in rows),
        sum(row["score"] == 0.5 for row in rows),
        sum(row["score"] == 0.0 for row in rows),
    ]


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "wins_ties_losses": wdl(rows),
        "score_rate": float(np.mean([row["score"] for row in rows])),
        "mean_candidate_reward": float(np.mean([row["candidate_reward"] for row in rows])),
        "mean_margin": float(np.mean([row["margin"] for row in rows])),
        "catastrophe_rate_reward_lt_3000": float(
            np.mean([row["candidate_reward"] < 3000 for row in rows])
        ),
    }


def summarize_report(report: dict) -> dict:
    rows = report["rows"]
    by_layer: dict[str, list[dict]] = defaultdict(list)
    by_opponent: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_layer[row["opponent_layer"]].append(row)
        by_opponent[row["opponent_member_id"]].append(row)
    return {
        "overall": summarize(rows),
        "by_layer": {name: summarize(group) for name, group in sorted(by_layer.items())},
        "by_opponent": {name: summarize(group) for name, group in sorted(by_opponent.items())},
    }


def percentile_ci(seed_values: np.ndarray, samples: int, rng: np.random.Generator) -> list[float]:
    n = len(seed_values)
    draws = rng.integers(0, n, size=(samples, n))
    boot = seed_values[draws].mean(axis=1)
    return [float(value) for value in np.percentile(boot, [2.5, 97.5])]


def paired_analysis(baseline: dict, candidate: dict, samples: int, bootstrap_seed: int) -> dict:
    base = {(int(row["seed"]), int(row["seat"])): row for row in baseline["rows"]}
    cand = {(int(row["seed"]), int(row["seat"])): row for row in candidate["rows"]}
    if set(base) != set(cand):
        raise ValueError("candidate seed/seat set does not match baseline")

    pairs = []
    for key in sorted(base):
        b, c = base[key], cand[key]
        if (b["opponent_layer"], b["opponent_member_id"]) != (
            c["opponent_layer"], c["opponent_member_id"]
        ):
            raise ValueError(f"opponent mismatch at {key}")
        pairs.append(
            {
                "seed": key[0],
                "seat": key[1],
                "layer": b["opponent_layer"],
                "opponent": b["opponent_member_id"],
                "score_gain": float(c["score"] - b["score"]),
                "reward_gain": float(c["candidate_reward"] - b["candidate_reward"]),
                "margin_gain": float(c["margin"] - b["margin"]),
            }
        )

    def paired_metric(name: str) -> dict:
        values = np.asarray([row[name] for row in pairs], dtype=np.float64)
        seed_groups: dict[int, list[float]] = defaultdict(list)
        for row in pairs:
            seed_groups[row["seed"]].append(row[name])
        seed_values = np.asarray(
            [np.mean(seed_groups[seed]) for seed in sorted(seed_groups)], dtype=np.float64
        )
        rng = np.random.default_rng(bootstrap_seed + {"score_gain": 1, "reward_gain": 2, "margin_gain": 3}[name])
        return {
            "mean": float(values.mean()),
            "wins_ties_losses": [
                int(np.sum(values > 0)),
                int(np.sum(values == 0)),
                int(np.sum(values < 0)),
            ],
            "seed_block_ci95": percentile_ci(seed_values, samples, rng),
        }

    by_layer: dict[str, list[dict]] = defaultdict(list)
    for row in pairs:
        by_layer[row["layer"]].append(row)

    layer_delta = {}
    for layer, group in sorted(by_layer.items()):
        layer_delta[layer] = {
            metric: float(np.mean([row[metric] for row in group]))
            for metric in ("score_gain", "reward_gain", "margin_gain")
        }

    return {
        "games": len(pairs),
        "seed_blocks": len({row["seed"] for row in pairs}),
        "score_gain": paired_metric("score_gain"),
        "reward_gain": paired_metric("reward_gain"),
        "margin_gain": paired_metric("margin_gain"),
        "by_layer_mean_gain": layer_delta,
    }


def main() -> None:
    args = parse_args()
    baseline = load_report(args.baseline)
    candidates = [(name, load_report(Path(path))) for name, path in args.candidate]
    result = {
        "schema": "kaggriculture-v113-mixed-screen-analysis-v1",
        "protocol": {
            "fresh_seed_blocks": len({row["seed"] for row in baseline["rows"]}),
            "dual_seat_same_opponent": True,
            "bootstrap_unit": "seed_block_two_seats",
            "bootstrap_samples": args.bootstrap_samples,
            "bootstrap_seed": args.bootstrap_seed,
            "catastrophe_definition": "candidate_reward < 3000",
            "require_catastrophe_strict_improvement": (
                args.require_catastrophe_strict_improvement
            ),
            "require_positive_economic_ci": args.require_positive_economic_ci,
            "require_exploiter_nondegradation": args.require_exploiter_nondegradation,
        },
        "baseline": summarize_report(baseline),
        "candidates": {},
    }
    baseline_score = result["baseline"]["overall"]["score_rate"]
    baseline_catastrophe = result["baseline"]["overall"]["catastrophe_rate_reward_lt_3000"]
    for name, report in candidates:
        summary = summarize_report(report)
        paired = paired_analysis(
            baseline, report, args.bootstrap_samples, args.bootstrap_seed
        )
        pooled_pass = summary["overall"]["score_rate"] >= baseline_score
        gold_delta = paired["by_layer_mean_gain"].get("gold_train", {})
        gold_pass = gold_delta.get("score_gain", float("-inf")) >= 0.0
        baseline_gold = {
            member: metrics for member, metrics in result["baseline"]["by_opponent"].items()
            if member.startswith("gold_")
        }
        candidate_gold = summary["by_opponent"]
        gold_member_score_gains = {
            member: candidate_gold[member]["score_rate"] - metrics["score_rate"]
            for member, metrics in baseline_gold.items()
        }
        worst_gold_pass = bool(
            gold_member_score_gains and min(gold_member_score_gains.values()) >= 0.0
        )
        candidate_catastrophe = summary["overall"]["catastrophe_rate_reward_lt_3000"]
        catastrophe_pass = (
            candidate_catastrophe < baseline_catastrophe
            if args.require_catastrophe_strict_improvement
            else candidate_catastrophe <= baseline_catastrophe
        )
        reward_ci_lower = paired["reward_gain"]["seed_block_ci95"][0]
        margin_ci_lower = paired["margin_gain"]["seed_block_ci95"][0]
        economic_ci_pass = (
            reward_ci_lower > 0.0 or margin_ci_lower > 0.0
            if args.require_positive_economic_ci
            else True
        )
        exploiter_delta = paired["by_layer_mean_gain"].get("exploiter", {})
        exploiter_pass = (
            exploiter_delta.get("score_gain", float("-inf")) >= 0.0
            if args.require_exploiter_nondegradation
            else True
        )
        passed = bool(
            pooled_pass
            and gold_pass
            and worst_gold_pass
            and catastrophe_pass
            and economic_ci_pass
            and exploiter_pass
        )
        summary["paired_vs_baseline"] = paired
        summary["screen_gate"] = {
            "pooled_score_non_degradation": pooled_pass,
            "gold_train_score_non_degradation": gold_pass,
            "gold_member_score_gains": gold_member_score_gains,
            "worst_gold_score_non_degradation": worst_gold_pass,
            "catastrophe_rate_gate": catastrophe_pass,
            "catastrophe_gate_mode": (
                "strict_improvement"
                if args.require_catastrophe_strict_improvement
                else "non_degradation"
            ),
            "reward_gain_ci95_lower": reward_ci_lower,
            "margin_gain_ci95_lower": margin_ci_lower,
            "positive_economic_ci_gate": economic_ci_pass,
            "exploiter_score_gain": exploiter_delta.get("score_gain"),
            "exploiter_score_non_degradation": exploiter_pass,
            "passed": passed,
            "decision": (
                "ADVANCE_TO_GOLD_DEV"
                if passed
                else "REJECT_SCREEN"
            ),
        }
        result["candidates"][name] = summary

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
