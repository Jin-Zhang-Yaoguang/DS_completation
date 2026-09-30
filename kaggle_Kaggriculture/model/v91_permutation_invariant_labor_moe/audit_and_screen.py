#!/usr/bin/env python3
"""Synthetic architecture and closed-loop screen for V91."""

from __future__ import annotations

import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import statistics


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
BASE_PATH = MODEL / "v88_reference_trajectory_state_tube_moe/audit_and_screen.py"
spec = importlib.util.spec_from_file_location("v91_audit_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(base)
base.HERE = HERE
base.POLICIES = {
    "full": HERE / "main.py",
    "ablation": HERE / "ablation_main.py",
    "comparator": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
base.SEEDS = tuple(range(91101, 91117))


def play(task):
    return base.play(task)


def main():
    tasks = [
        (mode, family, seed, seat)
        for mode in base.POLICIES
        for family in base.OPPONENTS
        for seed in base.SEEDS
        for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))

    mode_scores = {
        mode: statistics.mean(row["score"] for row in rows if row["mode"] == mode)
        for mode in base.POLICIES
    }
    by_family = {
        mode: {
            family: statistics.mean(
                row["score"] for row in rows if row["mode"] == mode and row["family"] == family
            )
            for family in base.OPPONENTS
        }
        for mode in base.POLICIES
    }
    full_rows = [row for row in rows if row["mode"] == "full"]
    comparator_rows = [row for row in rows if row["mode"] == "comparator"]
    reassigned_games = sum(int(row.get("stats", {}).get("reassigned_calls", 0)) > 0 for row in full_rows)
    reassigned_calls = sum(int(row.get("stats", {}).get("reassigned_calls", 0)) for row in full_rows)
    reassigned_pairs = sum(int(row.get("stats", {}).get("reassigned_pairs", 0)) for row in full_rows)
    expert_games = {}
    expert_calls = {}
    for row in full_rows:
        for expert, count in (row.get("stats", {}).get("experts", {}) or {}).items():
            expert_calls[expert] = expert_calls.get(expert, 0) + int(count)
            expert_games[expert] = expert_games.get(expert, 0) + int(int(count) > 0)

    full_vs_ablation = base.paired(rows, "full", "ablation")
    full_vs_comparator = base.paired(rows, "full", "comparator")
    architecture = base.static_audit()
    candidate_cat = statistics.mean(row["margin"] < -10000 for row in full_rows)
    comparator_cat = statistics.mean(row["margin"] < -10000 for row in comparator_rows)
    safety = sum(row["violations"] for row in rows)
    all_719 = all(row["calls"] == 719 for row in rows)
    gate = bool(
        not architecture["complete_agent_call_detected"]
        and all_719
        and safety == 0
        and reassigned_games >= 8
        and full_vs_ablation["uplift_pp"] > 0
        and full_vs_ablation["positive_zero_negative"][0] > full_vs_ablation["positive_zero_negative"][2]
        and mode_scores["full"] >= 0.60
        and by_family["full"]["v76"] >= 0.50
        and 100 * (candidate_cat - comparator_cat) <= 1.0
    )
    payload = {
        "schema": "kaggriculture-v91-preconstruction-audit-v1",
        "engine": str(base.kagsim.ENGINE_VERSION),
        "official_replay_sources_consumed": 0,
        "synthetic_seed_range": [min(base.SEEDS), max(base.SEEDS)],
        "games": len(rows),
        "static_architecture_audit": architecture,
        "score_rate": mode_scores,
        "score_rate_by_opponent": by_family,
        "full_vs_ablation": full_vs_ablation,
        "full_vs_comparator": full_vs_comparator,
        "direct_v76_score_rate": by_family["full"]["v76"],
        "candidate_catastrophic_rate": candidate_cat,
        "comparator_catastrophic_rate": comparator_cat,
        "catastrophic_rate_delta_pp": 100 * (candidate_cat - comparator_cat),
        "reassigned_games": reassigned_games,
        "reassigned_calls": reassigned_calls,
        "reassigned_pairs": reassigned_pairs,
        "expert_game_coverage": expert_games,
        "expert_call_coverage": expert_calls,
        "all_719_calls": all_719,
        "safety_violations": safety,
        "fallback_calls_full": sum(int(row.get("stats", {}).get("fallback", 0)) for row in full_rows),
        "decision": "PASS_PRECONSTRUCTION" if gate else "REJECT_PRECONSTRUCTION",
        "rows": rows,
    }
    (HERE / "preconstruction_audit_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
