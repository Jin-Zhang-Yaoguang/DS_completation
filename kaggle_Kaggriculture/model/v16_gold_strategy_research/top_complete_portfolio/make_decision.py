#!/usr/bin/env python3
"""Produce behavior-deduplicated seed-cluster inference and V17 decision."""

from __future__ import annotations

import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent


def score(row):
    return 1.0 if row["margin"] > 0 else 0.5 if row["margin"] == 0 else 0.0


def q(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, max(0, int(p * len(values))))]


def main() -> int:
    live = json.loads((HERE / "live_pool_results.json").read_text())
    oracle = json.loads((HERE / "route_shop_oracle_results.json").read_text())
    audit = json.loads((HERE / "compatibility_audit_results.json").read_text())
    parity = json.loads((HERE / "package_qa_results.json").read_text())
    rows = [row for row in live["rows"] if row["mode"] == "router"]
    families = sorted({row["opponent_family"] for row in rows})
    fingerprints = {}
    for family in families:
        values = [(r["seed"], r["seat"], r["own"], r["opp"]) for r in rows if r["opponent_family"] == family]
        fingerprints[family] = hashlib.sha256(json.dumps(values).encode()).hexdigest()
    grouped = defaultdict(list)
    for family, fingerprint in fingerprints.items():
        grouped[fingerprint].append(family)
    clusters = list(grouped.values())
    seeds = sorted({int(row["seed"]) for row in rows})

    per_seed = {}
    for seed in seeds:
        cluster_scores = []
        for cluster in clusters:
            family = cluster[0]
            selected = [row for row in rows if row["opponent_family"] == family and int(row["seed"]) == seed]
            cluster_scores.append(statistics.mean(score(row) for row in selected))
        per_seed[seed] = statistics.mean(cluster_scores)
    rng = random.Random(1701)
    samples = []
    for _ in range(10000):
        selected = rng.choices(seeds, k=len(seeds))
        samples.append(statistics.mean(per_seed[seed] for seed in selected))
    cluster_summary = []
    for cluster in clusters:
        family = cluster[0]
        selected = [row for row in rows if row["opponent_family"] == family]
        cluster_summary.append({
            "members": cluster,
            "games": len(selected),
            "score_rate": statistics.mean(score(row) for row in selected),
            "mean_margin": statistics.mean(row["margin"] for row in selected),
        })
    result = {
        "decision": "ADVANCE_AS_V17_SUBMISSION_CANDIDATE",
        "not_claimed": "not gold proof; current top policies are available only as fixed public replay routes",
        "mapping_frozen_from_dev_only": oracle["shop_route_choices"],
        "offline_heldout_top_replay_proxy": oracle["shop_router_test"],
        "live_heldout_cpp_l1": live["modes"]["router"],
        "behavior_dedup": {
            "method": "families with identical own/opponent banks on every held-out seed and seat are one behavior cluster",
            "clusters": cluster_summary,
            "cluster_equal_score_rate": statistics.mean(item["score_rate"] for item in cluster_summary),
            "worst_cluster_score_rate": min(item["score_rate"] for item in cluster_summary),
            "seed_cluster_bootstrap_ci95": [q(samples, 0.025), q(samples, 0.975)],
            "bootstrap_reps": 10000,
        },
        "hard_gates": {
            "exact_shared_prefix": audit["route_boundary"]["exact_prefix"],
            "unit_precondition_valid_rate": audit["action_audit"]["unit_precondition_valid_rate"],
            "hands_match_rate": audit["action_audit"]["hand_count_match_rate"],
            "land_success_rate": audit["action_audit"]["land_success_rate"],
            "hire_success_rate": audit["action_audit"]["hire_success_rate_non_dayend"],
            "seed_success_rate": audit["action_audit"]["buy_seed_success_rate"],
            "animal_success_rate": audit["action_audit"]["buy_animal_success_rate"],
            "raw_loader_callable": parity["selected_callable"],
            "official_cpp_exact_games": [parity["exact_games"], parity["games"]],
        },
    }
    (HERE / "decision.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

