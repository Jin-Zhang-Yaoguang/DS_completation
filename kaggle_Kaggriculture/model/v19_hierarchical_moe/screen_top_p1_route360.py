#!/usr/bin/env python3
"""Expanded four-model development screen for the top five all-P1 routes."""

from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
from pathlib import Path

from screen_all_p1_route360 import OPPONENTS, run_baseline, run_job, score


HERE = Path(__file__).resolve().parent
SEEDS = tuple(range(91000, 91064))
TOP_COUNT = 5


def main() -> int:
    source = json.loads((HERE / "all_p1_route360_screen.json").read_text(encoding="utf-8"))
    routes = [row["route"] for row in source["metrics"][:TOP_COUNT]]
    base_jobs = [(family, seed, seat) for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    jobs = [
        (row["full_action_hash"], row["team"], int(row["episode"]), row["path"], family, seed, seat)
        for row in routes for family, seed, seat in base_jobs
    ]
    workers = max(1, os.cpu_count() or 1)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        baseline_rows = list(pool.map(run_baseline, base_jobs, chunksize=4))
        candidate_rows = list(pool.map(run_job, jobs, chunksize=16))
    baseline = {(row["opponent_family"], row["seed"], row["seat"]): row for row in baseline_rows}
    metrics = []
    for route in routes:
        selected = [row for row in candidate_rows if row["route_hash"] == route["full_action_hash"]]
        paired = []
        for row in selected:
            base = baseline[(row["opponent_family"], row["seed"], row["seat"])]
            paired.append({
                **row,
                "score_delta": score(row["margin"]) - score(base["margin"]),
                "margin_delta": row["margin"] - base["margin"],
                "own_delta": row["own"] - base["own"],
            })
        by_family = {}
        for family in OPPONENTS:
            family_rows = [row for row in paired if row["opponent_family"] == family]
            by_family[family] = {
                "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in family_rows),
                "positive_zero_negative": [sum(row["score_delta"] > 0 for row in family_rows), sum(row["score_delta"] == 0 for row in family_rows), sum(row["score_delta"] < 0 for row in family_rows)],
                "margin_delta_mean": statistics.mean(row["margin_delta"] for row in family_rows),
            }
        metrics.append({
            "route": route,
            "cells": len(paired),
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in paired),
            "positive_zero_negative": [sum(row["score_delta"] > 0 for row in paired), sum(row["score_delta"] == 0 for row in paired), sum(row["score_delta"] < 0 for row in paired)],
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in paired),
            "own_delta_mean": statistics.mean(row["own_delta"] for row in paired),
            "by_family": by_family,
            "guardrail_pass": all(value["score_uplift_pp"] >= -2.0 for value in by_family.values()),
        })
    metrics.sort(key=lambda row: (row["score_uplift_pp"], -row["positive_zero_negative"][2], row["margin_delta_mean"]), reverse=True)
    result = {
        "schema": "kaggriculture-v20-top-p1-route360-expanded-screen-v1",
        "status": "EXPANDED_DEVELOPMENT_NOT_CONFIRMATION",
        "seed_range": [SEEDS[0], SEEDS[-1]],
        "opponent_families": list(OPPONENTS),
        "double_seat": True,
        "route_count": len(routes),
        "cells_per_route": len(base_jobs),
        "baseline": "V19 switch_360 Kronki::99108392",
        "metrics": metrics,
    }
    (HERE / "top_p1_route360_screen.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{"route_id": row["route"]["team"] + "::" + str(row["route"]["episode"]), **{key: row[key] for key in ("score_uplift_pp", "positive_zero_negative", "margin_delta_mean", "own_delta_mean", "guardrail_pass")}, "by_family": row["by_family"]} for row in metrics], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
