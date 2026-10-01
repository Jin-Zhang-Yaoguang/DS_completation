#!/usr/bin/env python3
"""在固定 Development 子面板筛选 I3 任务分配参数；不访问 Blind。"""

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

from evaluate_development import (  # noqa: E402
    DEFAULT_PANEL, SOURCES, manifest_scenarios, play, summarize_rows,
)


def canonical_sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def screen_play(task: tuple[str, str, int, dict[str, Any]]) -> dict[str, Any]:
    variant, scenario_path, seat, tuning = task
    result = play((scenario_path, seat, {}, tuning))
    result["variant"] = variant
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--tunings-json", type=Path, default=HERE / "executor_assignment_tunings.json")
    parser.add_argument("--scenarios-per-source", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not 1 <= args.scenarios_per_source <= 32:
        raise ValueError("scenarios-per-source 必须在 1..32")

    tunings = json.loads(args.tunings_json.read_text(encoding="utf-8"))
    if not isinstance(tunings, dict) or not tunings:
        raise ValueError("tunings-json 必须是非空 variant -> tuning 对象")
    manifest, scenarios = manifest_scenarios(args.panel_dir, args.scenarios_per_source)
    tasks = [
        (variant, str(scenario["scenario_path"]), seat, tuning)
        for variant, tuning in tunings.items()
        for scenario in scenarios
        for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(screen_play, tasks, chunksize=1))

    variants: dict[str, Any] = {}
    for index, (variant, tuning) in enumerate(tunings.items()):
        variant_rows = [row for row in rows if row["variant"] == variant]
        sources = {
            source: summarize_rows(
                [row for row in variant_rows if row.get("source_class") == source],
                117310 + index * 10 + source_index,
            )
            for source_index, source in enumerate(SOURCES)
        }
        overall = summarize_rows(variant_rows, 117319 + index * 10)
        integrity = (
            overall["error_count"] == 0
            and overall["action_violations"] == 0
            and overall["trajectory_mismatches"] == 0
            and overall["contract_invariant_events"] == 0
        )
        variants[variant] = {
            "tuning": tuning or "R2.1_B_CURRENT_DEFAULT",
            "tuning_sha256": canonical_sha(tuning),
            "source_metrics": sources,
            "overall": overall,
            "integrity_pass": integrity,
        }

    ranking = sorted(variants, key=lambda key: (
        not variants[key]["integrity_pass"],
        -float(variants[key]["overall"]["pure_win_rate"]),
        -float(variants[key]["overall"]["mean_margin"]),
        -float(variants[key]["overall"]["mean_candidate_reward"]),
        key,
    ))
    best = ranking[0]
    output_dir = args.output_dir or (args.panel_dir / "evaluations/r2_1_b8_executor_assignment_screen")
    output_dir.mkdir(parents=True, exist_ok=True)
    games_path = output_dir / "games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in sorted(rows, key=lambda item: (
            item["variant"], str(item.get("source_class")), int(item.get("episode_id") or -1),
            int(item.get("candidate_seat") or 0),
        )):
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    selected = tunings[best]
    (output_dir / "selected_tuning.json").write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    payload = {
        "schema": "v117-r2.1-b8-executor-assignment-screen-v1",
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
        "selected_tuning_sha256": canonical_sha(selected),
        "variants": variants,
        "next_step": "只有同时改善 Replay 分差与执行指标的参数才进入完整 Development",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    compact = {
        "ranking": ranking,
        "selected_variant": best,
        "metrics": {
            key: {
                "win_rate": variants[key]["overall"]["pure_win_rate"],
                "mean_margin": variants[key]["overall"]["mean_margin"],
                "candidate_reward": variants[key]["overall"]["mean_candidate_reward"],
                "moves": variants[key]["overall"]["mean_moves"],
                "idle": variants[key]["overall"]["mean_idle_actions"],
                "overdue": variants[key]["overall"]["mean_loss_proxy_per_game"].get("OVERDUE_TASK", 0),
            }
            for key in ranking
        },
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0 if all(row["integrity_pass"] for row in variants.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
