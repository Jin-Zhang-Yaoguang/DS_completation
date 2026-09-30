"""Analyze Iteration 7 same-context market residual counterfactuals."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping

from evaluate_event_program import atomic_json, file_sha256
from evaluate_market_timing_program import parse_variant


BASELINE_SUFFIX = "POST_DEMAND__Q100__FRONT"


def _quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("quantile requires at least one value")
    position = (len(ordered) - 1) * float(probability)
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def seed_block_bootstrap_ci(
    blocks: list[float], *, draws: int = 20_000, seed: int = 114_007
) -> list[float]:
    if not blocks:
        raise ValueError("bootstrap requires seed blocks")
    rng = random.Random(int(seed))
    estimates = [
        mean(rng.choice(blocks) for _ in range(len(blocks)))
        for _ in range(int(draws))
    ]
    return [_quantile(estimates, 0.025), _quantile(estimates, 0.975)]


def _index(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, int, int], Mapping[str, Any]]:
    result: dict[tuple[str, int, int], Mapping[str, Any]] = {}
    for row in rows:
        key = (str(row["decision_name"]), int(row["seed"]), int(row["seat"]))
        if key in result:
            raise ValueError(f"duplicate row {key}")
        result[key] = row
    return result


def compare_variant(
    report: Mapping[str, Any], variant: str, baseline: str
) -> dict[str, Any]:
    rows = list(report["rows"])
    indexed = _index(rows)
    seeds = sorted(
        int(row["seed"]) for row in rows if str(row["decision_name"]) == variant
    )
    seeds = sorted(set(seeds))
    paired: list[dict[str, float]] = []
    seed_blocks: list[float] = []
    candidate_wins = baseline_wins = 0
    candidate_catastrophes = baseline_catastrophes = 0
    for seed in seeds:
        block_margins: list[float] = []
        for seat in (0, 1):
            candidate = indexed[(variant, seed, seat)]
            incumbent = indexed[(baseline, seed, seat)]
            delta = {
                "margin": float(candidate["margin"]) - float(incumbent["margin"]),
                "candidate_reward": float(candidate["candidate_reward"])
                - float(incumbent["candidate_reward"]),
                "opponent_reward": float(candidate["opponent_reward"])
                - float(incumbent["opponent_reward"]),
                "score": float(candidate["score"]) - float(incumbent["score"]),
            }
            paired.append(delta)
            block_margins.append(delta["margin"])
            candidate_wins += int(float(candidate["score"]) == 1.0)
            baseline_wins += int(float(incumbent["score"]) == 1.0)
            candidate_catastrophes += int(bool(candidate["catastrophe"]))
            baseline_catastrophes += int(bool(incumbent["catastrophe"]))
        seed_blocks.append(mean(block_margins))
    return {
        "games": len(paired),
        "seed_blocks": len(seed_blocks),
        "mean_margin_delta": mean(item["margin"] for item in paired),
        "mean_candidate_reward_delta": mean(
            item["candidate_reward"] for item in paired
        ),
        "mean_opponent_reward_delta": mean(item["opponent_reward"] for item in paired),
        "mean_score_delta": mean(item["score"] for item in paired),
        "margin_delta_signs": [
            sum(item["margin"] > 0 for item in paired),
            sum(item["margin"] == 0 for item in paired),
            sum(item["margin"] < 0 for item in paired),
        ],
        "wins_candidate_vs_baseline": [candidate_wins, baseline_wins],
        "catastrophes_candidate_vs_baseline": [
            candidate_catastrophes,
            baseline_catastrophes,
        ],
        "seed_block_margin_deltas": seed_blocks,
    }


def analyze(reports: list[tuple[Path, Mapping[str, Any]]]) -> dict[str, Any]:
    if len(reports) < 2:
        raise ValueError("at least two opponent reports are required")
    execution_errors: list[str] = []
    variants: set[str] | None = None
    for path, report in reports:
        if report.get("status") != "VALID":
            execution_errors.append(f"{path}: report is not VALID")
        current = {str(spec["name"]) for spec in report["decision_specs"]}
        variants = current if variants is None else variants & current
        for summary in report["summaries"]:
            if int(summary["errors"]) or int(summary["incomplete_games"]):
                execution_errors.append(f"{path}: incomplete variant {summary['decision_name']}")
            if int(summary["contract_violations"]) or int(summary["terminal_procurement_count"]):
                execution_errors.append(f"{path}: contract violation {summary['decision_name']}")
            if float(summary["p10_candidate_reward"]) < 3000.0:
                execution_errors.append(f"{path}: P10 below gate {summary['decision_name']}")
    if not variants:
        raise ValueError("reports have no common variants")

    comparisons: dict[str, Any] = {}
    passed_variants: list[str] = []
    for variant in sorted(variants):
        product, _, quantity, placement = parse_variant(variant)
        baseline = f"{product}__{BASELINE_SUFFIX}"
        if variant == baseline:
            continue
        opponent_results: dict[str, Any] = {}
        pooled_blocks: list[float] = []
        for path, report in reports:
            opponent = str(report["opponent"]["id"])
            result = compare_variant(report, variant, baseline)
            opponent_results[opponent] = result
            pooled_blocks.extend(result["seed_block_margin_deltas"])
        pooled_ci = seed_block_bootstrap_ci(pooled_blocks)
        passed = (
            not execution_errors
            and all(result["mean_margin_delta"] > 0 for result in opponent_results.values())
            and all(
                result["mean_candidate_reward_delta"] >= 0
                for result in opponent_results.values()
            )
            and all(
                result["wins_candidate_vs_baseline"][0]
                >= result["wins_candidate_vs_baseline"][1]
                for result in opponent_results.values()
            )
            and all(
                result["catastrophes_candidate_vs_baseline"][0]
                <= result["catastrophes_candidate_vs_baseline"][1]
                for result in opponent_results.values()
            )
            and pooled_ci[0] >= 0
        )
        comparisons[variant] = {
            "product": product,
            "quantity_fraction": quantity,
            "queue_placement": placement,
            "opponents": opponent_results,
            "pooled_seed_block_bootstrap_95_ci": pooled_ci,
            "pooled_mean_margin_delta": mean(pooled_blocks),
            "passed": passed,
        }
        if passed:
            passed_variants.append(variant)

    passed_variants.sort(
        key=lambda name: comparisons[name]["pooled_mean_margin_delta"], reverse=True
    )
    return {
        "schema": "kaggriculture-v114-bounded-market-residual-oracle-report-v1",
        "status": "PASS_ORACLE_GATE_NOT_GOLD" if passed_variants else "REJECT_ORACLE_GATE",
        "execution_gate": {"passed": not execution_errors, "errors": execution_errors},
        "passed_variants": passed_variants,
        "selected_variant": passed_variants[0] if passed_variants else None,
        "comparisons": comparisons,
        "source_reports": [
            {"path": str(path), "sha256": file_sha256(path)} for path, _ in reports
        ],
        "gold_qualification": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    loaded = [(path, json.loads(path.read_text())) for path in args.report]
    result = analyze(loaded)
    atomic_json(args.output, result)
    print(json.dumps({
        "status": result["status"],
        "passed_variants": result["passed_variants"],
        "selected_variant": result["selected_variant"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
