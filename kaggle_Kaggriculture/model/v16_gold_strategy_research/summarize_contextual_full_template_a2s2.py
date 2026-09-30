#!/usr/bin/env python3
"""Build the frozen decision record from the two raw paired result files."""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PRIMARY = HERE / "contextual_full_template_a2s2_results.json"
LATE = HERE / "contextual_full_template_a2s2_late_proxy_results.json"
OUTPUT = HERE / "contextual_full_template_a2s2_decision.json"
BEHAVIOR_FAMILIES = {
    "a2_derived": {
        "baseline_v1", "baseline_v2", "v12a2_no_shop_gate",
        "v13c_a2_v8_no_wool_throttle", "v14_queue_best_response",
    },
    "v5_champion": {"baseline_v5"},
    "v8_kawa": {"baseline_v8"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tail_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    series = {
        "margin_delta": sorted(row["candidate_margin"] - row["baseline_margin"] for row in rows),
        "candidate_margin": sorted(row["candidate_margin"] for row in rows),
        "own_delta": sorted(row["candidate_own"] - row["baseline_own"] for row in rows),
    }
    result = {}
    for name, values in series.items():
        tail_n = max(1, math.ceil(0.10 * len(values)))
        p10_index = max(0, math.ceil(0.10 * len(values)) - 1)
        result[f"{name}_p10"] = float(values[p10_index])
        result[f"{name}_cvar10"] = float(statistics.mean(values[:tail_n]))
        result[f"{name}_min"] = float(values[0])
    return result


def cluster_candidate_score_ci(rows: list[dict[str, Any]], key: str, rounds: int = 5000) -> list[float]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    keys = sorted(grouped)
    rng = random.Random(20260826)
    values = []
    for _ in range(rounds):
        sample = [row for chosen in (rng.choice(keys) for _ in keys) for row in grouped[chosen]]
        values.append(statistics.mean(row["candidate_score"] for row in sample))
    values.sort()
    return [values[max(0, int(0.025 * rounds) - 1)], values[min(rounds - 1, int(0.975 * rounds))]]


def family_stats(rows: list[dict[str, Any]], ids: set[str]) -> dict[str, float | int]:
    selected = [row for row in rows if row["opponent"] in ids]
    return {
        "comparisons": len(selected),
        "baseline_score_rate": statistics.mean(row["baseline_score"] for row in selected),
        "candidate_score_rate": statistics.mean(row["candidate_score"] for row in selected),
        "baseline_mean_margin": statistics.mean(row["baseline_margin"] for row in selected),
        "candidate_mean_margin": statistics.mean(row["candidate_margin"] for row in selected),
        "margin_delta_mean": statistics.mean(row["candidate_margin"] - row["baseline_margin"] for row in selected),
    }


def main() -> int:
    primary = json.loads(PRIMARY.read_text())
    late = json.loads(LATE.read_text())
    top = primary["top_tape_holdout"]
    early_rows = primary["local_closed_loop_proxy"]["rows"]
    late_rows = late["rows"]
    proxy_rows = early_rows + late_rows
    behavior = {name: family_stats(proxy_rows, ids) for name, ids in BEHAVIOR_FAMILIES.items()}
    behavior_equal_baseline = statistics.mean(row["baseline_score_rate"] for row in behavior.values())
    behavior_equal_candidate = statistics.mean(row["candidate_score_rate"] for row in behavior.values())
    top_score = float(top["overall"]["candidate_score_rate"])
    top_score_ci = cluster_candidate_score_ci(top["rows"], "episode_id")
    top_worst = min(row["candidate_score_rate"] for row in top["by_team"].values())
    late_score = float(late["overall"]["candidate_score_rate"])
    result = {
        "status": "REJECT_AS_V17_KEEP_RYO_ROUTER_LEAD",
        "v17_candidate": False,
        "frozen_rule": "at step72, public opponent MELON tiles >= 10 selects the complete V8 suffix; otherwise complete A2",
        "search_templates": primary["search_templates"],
        "regression": primary["a2_identity"],
        "top_meta_holdout": {
            "sources": top["identity_replay"]["checks"],
            "comparisons": top["overall"]["comparisons"],
            "candidate_score_rate": top_score,
            "candidate_score_cluster_ci95": top_score_ci,
            "paired_score_uplift": top["overall"]["paired_score_uplift"],
            "paired_score_uplift_cluster_ci95": top["overall"]["paired_score_uplift_ci95"],
            "margin_delta_mean": top["overall"]["margin_delta_mean"],
            "margin_delta_mean_cluster_ci95": top["overall"]["margin_delta_mean_ci95"],
            "worst_family_candidate_score_rate": top_worst,
            "by_team": top["by_team"],
            "tails": tail_metrics(top["rows"]),
            "prefix_failures": top["overall"]["prefix_failures"],
        },
        "closed_loop_behavior_lineages": {
            "comparisons": len(proxy_rows),
            "families": behavior,
            "family_equal_baseline_score_rate": behavior_equal_baseline,
            "family_equal_candidate_score_rate": behavior_equal_candidate,
            "worst_family_candidate_score_rate": min(row["candidate_score_rate"] for row in behavior.values()),
            "early_proxy_tails": tail_metrics(early_rows),
            "late_proxy_tails": tail_metrics(late_rows),
            "late_proxy_absolute_score_rate": late_score,
            "late_proxy_own_delta_mean": late["overall"]["own_delta_mean"],
            "late_proxy_own_positive_zero_negative": late["overall"]["own_positive_zero_negative"],
            "prefix_failures": primary["local_closed_loop_proxy"]["overall"]["prefix_failures"] + late["overall"]["prefix_failures"],
        },
        "gates": {
            "top_family_equal_score_ge_60pct": top_score >= 0.60,
            "top_score_ci_lower_ge_55pct": top_score_ci[0] >= 0.55,
            "every_top_family_score_ge_50pct": top_worst >= 0.50,
            "behavior_family_equal_score_ge_60pct": behavior_equal_candidate >= 0.60,
            "every_behavior_family_score_ge_50pct": min(row["candidate_score_rate"] for row in behavior.values()) >= 0.50,
            "late_proxy_absolute_score_ge_50pct": late_score >= 0.50,
            "zero_prefix_failures": top["overall"]["prefix_failures"] == 0 and primary["local_closed_loop_proxy"]["overall"]["prefix_failures"] == 0 and late["overall"]["prefix_failures"] == 0,
            "nonnegative_cvar10_margin_delta_all_panels": all(
                tail_metrics(rows)["margin_delta_cvar10"] >= 0
                for rows in (top["rows"], early_rows, late_rows)
            ),
        },
        "decision_reasons": [
            "Top/meta holdout score is 53.70%, below the 60% gate, and its source-cluster score/uplift intervals do not establish the required win-rate floor.",
            "The worst top family remains Kronki at 22.22%; the route only improves the publicly identifiable high-MELON/Ryo branch.",
            "Later closed-loop proxies improve relative to A2 but still win only 27.08%; losing less than A2 is not gold competitiveness.",
            "Later-proxy own bank is lower than A2 on average and in 78/144 comparisons, so the margin gain is not a clean production-value gain.",
            "All three panels have negative CVaR10 margin delta; tail safety is not established.",
        ],
        "unseen_boundaries": {
            "rule_discovery": "newest 3 replays per named family on 2026-08-25",
            "top_holdout": "ranks 4-12 from the same date/families; seeds and episodes unseen by the threshold, opponent families seen",
            "local_proxy_seeds": "integer seeds 0-23 unseen by the replay threshold, but all opponent code lineages were already present locally",
            "unknown_opponent_policy": "not tested; no current top-team live package is available",
            "future_date": "not opened; required before any V17 reconsideration",
        },
        "reproduction": {
            "primary_command": primary["commands"]["full"],
            "late_proxy_command": late["command"],
            "summary_command": ".venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/summarize_contextual_full_template_a2s2.py",
            "sha256": {
                PRIMARY.name: sha256(PRIMARY),
                LATE.name: sha256(LATE),
                "contextual_full_template_a2s2.py": sha256(HERE / "contextual_full_template_a2s2.py"),
                "run_contextual_full_template_a2s2.py": sha256(HERE / "run_contextual_full_template_a2s2.py"),
                "run_contextual_late_proxy_a2s2.py": sha256(HERE / "run_contextual_late_proxy_a2s2.py"),
            },
        },
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

