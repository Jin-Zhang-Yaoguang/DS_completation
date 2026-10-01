#!/usr/bin/env python3
"""在固定 Development 子面板筛选 Balanced genome × Executor 联合候选；不访问 Blind。"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from evaluate_development import DEFAULT_PANEL, SOURCES, manifest_scenarios, play, summarize_rows  # noqa: E402


def canonical_sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def screen_play(task: tuple[str, str, int, dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    variant, scenario_path, seat, genome, tuning = task
    result = play((scenario_path, seat, genome, tuning))
    result["variant"] = variant
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--variants-json", type=Path, required=True)
    parser.add_argument("--scenarios-per-source", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.scenarios_per_source <= 32:
        raise ValueError("scenarios-per-source 必须在 1..32")
    variants = json.loads(args.variants_json.read_text(encoding="utf-8"))
    if not isinstance(variants, dict) or not variants:
        raise ValueError("variants-json 必须是非空 variant -> {genome, executor_tuning}")
    manifest, scenarios = manifest_scenarios(args.panel_dir, args.scenarios_per_source)
    tasks = [
        (
            variant,
            str(scenario["scenario_path"]),
            seat,
            dict(config.get("genome") or {}),
            dict(config.get("executor_tuning") or {}),
        )
        for variant, config in variants.items()
        for scenario in scenarios
        for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(screen_play, tasks, chunksize=1))

    result_variants: dict[str, Any] = {}
    for index, (variant, config) in enumerate(variants.items()):
        variant_rows = [row for row in rows if row["variant"] == variant]
        source_metrics = {
            source: summarize_rows(
                [row for row in variant_rows if row.get("source_class") == source],
                117410 + index * 10 + source_index,
            )
            for source_index, source in enumerate(SOURCES)
        }
        overall = summarize_rows(variant_rows, 117419 + index * 10)
        integrity = all(overall[key] == 0 for key in (
            "error_count", "action_violations", "trajectory_mismatches", "contract_invariant_events",
        ))
        result_variants[variant] = {
            "genome": dict(config.get("genome") or {}) or "R2.1_B_CURRENT_DEFAULT",
            "executor_tuning": dict(config.get("executor_tuning") or {}) or "R2.1_B_CURRENT_DEFAULT",
            "configuration_sha256": canonical_sha(config),
            "source_metrics": source_metrics,
            "overall": overall,
            "integrity_pass": integrity,
        }

    ranking = sorted(result_variants, key=lambda key: (
        not result_variants[key]["integrity_pass"],
        -float(result_variants[key]["overall"]["pure_win_rate"]),
        -float(result_variants[key]["overall"]["mean_margin"]),
        -float(result_variants[key]["overall"]["mean_candidate_reward"]),
        key,
    ))
    best = ranking[0]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    games_path = args.output_dir / "games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in sorted(rows, key=lambda item: (
            item["variant"], str(item.get("source_class")), int(item.get("episode_id") or -1),
            int(item.get("candidate_seat") or 0),
        )):
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    selected = variants[best]
    (args.output_dir / "selected_variant.json").write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    payload = {
        "schema": "v117-r2.1-b15-joint-screen-v1",
        "strength_status": "DEVELOPMENT_SCREEN_ONLY",
        "split": "development",
        "blind_content_accessed": False,
        "selection_rule": "integrity, pure_win_rate, mean_margin, candidate_reward, variant_id",
        "scenarios_per_source": args.scenarios_per_source,
        "scenario_ids": {
            source: [int(row["episode_id"]) for row in scenarios if row["source_class"] == source]
            for source in SOURCES
        },
        "manifest_sha256": canonical_sha(manifest),
        "games_sha256": hashlib.sha256(games_path.read_bytes()).hexdigest(),
        "ranking": ranking,
        "selected_variant": best,
        "selected_configuration_sha256": canonical_sha(selected),
        "variants": result_variants,
        "next_step": "只有利润与机制指标同向改善的候选才进入完整 Development",
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    compact = {
        "ranking": ranking,
        "selected_variant": best,
        "metrics": {
            key: {
                "win_rate": result_variants[key]["overall"]["pure_win_rate"],
                "mean_margin": result_variants[key]["overall"]["mean_margin"],
                "candidate_reward": result_variants[key]["overall"]["mean_candidate_reward"],
                "moves": result_variants[key]["overall"]["mean_moves"],
                "idle": result_variants[key]["overall"]["mean_idle_actions"],
                "overdue": result_variants[key]["overall"]["mean_loss_proxy_per_game"].get("OVERDUE_TASK", 0),
            }
            for key in ranking
        },
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0 if all(row["integrity_pass"] for row in result_variants.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
