#!/usr/bin/env python3
"""Consume V76's single-use Confirmation set and apply gold strength gates."""

from __future__ import annotations

import concurrent.futures
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import random
import statistics

import evaluate_development as common


HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "model_data/loop_evaluations/v76_adjacent_safe_buy_lead"
SOURCE_MANIFEST = DATA / "confirmation_source_manifest.json"


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    low, high = math.floor(index), math.ceil(index)
    if low == high:
        return values[low]
    return values[low] * (high - index) + values[high] * (index - low)


def direct_parent_ci(rows: list[dict], sources: list[dict]) -> tuple[float, list[float]]:
    candidate = {
        (row["source_id"], row["seat"]): common.score(float(row["margin"]))
        for row in rows
        if row.get("status") == "DONE" and row["mode"] == "candidate" and row["family"] == "v73"
    }
    clustered = [{
        "date": source["date"], "first_shop": source["first_shop"],
        "score": statistics.mean(candidate[(source["episode_id"], seat)] for seat in (0, 1)),
    } for source in sources]
    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in clustered:
        strata[(row["date"], row["first_shop"])].append(row)
    rng = random.Random(760033)
    draws = []
    for _ in range(20000):
        sample = []
        for values in strata.values():
            sample.extend(rng.choices(values, k=len(values)))
        draws.append(statistics.mean(float(row["score"]) for row in sample))
    return statistics.mean(float(row["score"]) for row in clustered), [percentile(draws, 0.025), percentile(draws, 0.975)]


def cvar10(rows: list[dict]) -> float:
    margins = sorted(float(row["margin"]) for row in rows)
    count = max(1, math.ceil(len(margins) * 0.10))
    return statistics.mean(margins[:count])


def changed_coverage(rows: list[dict]) -> tuple[set[str], set[str]]:
    done = [row for row in rows if row.get("status") == "DONE"]
    paired = {(row["mode"], row["family"], row["source_id"], row["seat"]): row for row in done}
    sources: set[str] = set()
    regimes: set[str] = set()
    for row in done:
        if row["mode"] != "candidate":
            continue
        parent = paired[("parent", row["family"], row["source_id"], row["seat"])]
        if float(row["own"]) != float(parent["own"]) or float(row["opponent"]) != float(parent["opponent"]):
            sources.add(str(row["source_id"]))
            regimes.add(str(row["first_shop"]))
    return sources, regimes


def main() -> None:
    if common.sha256(HERE / "submission.tar.gz") != common.EXPECTED_ARCHIVE_SHA:
        raise RuntimeError("candidate archive drifted before Confirmation")
    payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    sources = payload["sources"]
    tasks = [(mode, family, source, seat)
             for mode in common.POLICIES for family in common.OPPONENTS
             for source in sources for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(common.play, tasks, chunksize=1))
    games_path = DATA / "confirmation_games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = common.summarize(rows, sources)
    done = [row for row in rows if row.get("status") == "DONE"]
    candidate = [row for row in done if row["mode"] == "candidate"]
    parent = [row for row in done if row["mode"] == "parent"]
    direct_score, direct_ci = direct_parent_ci(rows, sources)
    by_family_score = {
        family: statistics.mean(common.score(float(row["margin"])) for row in candidate if row["family"] == family)
        for family in common.OPPONENTS
    }
    candidate_cvar, parent_cvar = cvar10(candidate), cvar10(parent)
    cvar_tolerance = 0.05 * max(abs(parent_cvar), 1000.0)
    changed_sources, changed_regimes = changed_coverage(rows)
    checks = {
        "pgu_at_least_1pp": summary["pgu_pp"] >= 1.0,
        "pgu_ci_lower_above_zero": summary["pgu_95ci_pp"][0] > 0,
        "pool_score_at_least_52pct": summary["candidate_pool_score"] >= 0.52,
        "pool_ci_lower_above_50pct": summary["pool_score_95ci"][0] > 0.50,
        "direct_parent_score_at_least_50pct": direct_score >= 0.50,
        "direct_parent_ci_lower_at_least_48pct": direct_ci[0] >= 0.48,
        "each_gold_score_at_least_48pct": min(by_family_score.values()) >= 0.48,
        "each_family_delta_at_least_minus_2pp": min(summary["by_family_pgu_pp"].values()) >= -2.0,
        "positive_flips_above_negative": summary["positive_zero_negative"][0] > summary["positive_zero_negative"][2],
        "catastrophic_delta_at_most_half_pp": summary["catastrophic_rate_delta_pp"] <= 0.5,
        "cvar10_within_tolerance": candidate_cvar >= parent_cvar - cvar_tolerance,
        "changed_at_least_8_sources": len(changed_sources) >= 8,
        "changed_at_least_2_shop_regimes": len(changed_regimes) >= 2,
        "zero_errors_integrity_safety": summary["error_count"] == 0 and summary["task_keys_unique"] and summary["safety_violations"] == 0,
        "serving_fingerprint_differs_parent": common.sha256(HERE / "main.py") != common.sha256(common.POLICIES["parent"]),
    }
    result = {
        "schema": "kaggriculture-loop-confirmation-v1",
        "model_id": "v76_adjacent_safe_buy_lead", "engine": str(common.kagsim.ENGINE_VERSION),
        "single_use_confirmation_consumed": True,
        "candidate_archive_sha256": common.EXPECTED_ARCHIVE_SHA,
        "source_manifest_sha256": common.sha256(SOURCE_MANIFEST),
        "games_sha256": common.sha256(games_path), "source_count": len(sources),
        "gold_lineages": list(common.OPPONENTS), "summary": summary,
        "direct_parent_score": direct_score, "direct_parent_score_95ci": direct_ci,
        "by_family_candidate_score": by_family_score,
        "candidate_cvar10_margin": candidate_cvar, "parent_cvar10_margin": parent_cvar,
        "cvar10_tolerance": cvar_tolerance, "changed_source_count": len(changed_sources),
        "changed_shop_regimes": sorted(changed_regimes), "strength_gate_checks": checks,
        "strength_gate": "PASS" if all(checks.values()) else "FAIL",
        "engineering_gate": "PENDING_PACKAGE_AND_OFFICIAL_PARITY",
    }
    (DATA / "confirmation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "confirmation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
