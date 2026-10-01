#!/usr/bin/env python3
"""在固定 Development 子面板上筛选 Balanced 经营 genome；不访问 Blind。"""

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


GENOMES: dict[str, dict[str, Any]] = {
    "a_default_r2_1_a": {},
    "b_crop_lean": {
        "crop_blocks": [
            [["WHEAT", 6], ["MELON", 4]],
            [["WHEAT", 4], ["STRAWBERRY", 2]],
            [["WHEAT", 2], ["CARROT", 2]],
        ],
        "cow_target": 6,
        "cow_start_day": 4,
        "hands_cap": 12,
        "hands_ramp_additional": 8,
    },
    "c_dairy_balanced": {
        "second_land_day": 4,
        "third_land_day": 7,
        "crop_blocks": [
            [["WHEAT", 6], ["MELON", 2]],
            [["WHEAT", 4], ["STRAWBERRY", 2]],
            [["WHEAT", 2]],
        ],
        "cow_target": 8,
        "cow_start_day": 3,
        "hands_cap": 12,
        "hands_ramp_additional": 8,
        "care_priority": 4,
    },
    "d_dairy_dense_feed1": {
        "second_land_day": 3,
        "third_land_day": 6,
        "crop_blocks": [
            [["WHEAT", 6]],
            [["WHEAT", 4]],
            [["WHEAT", 2]],
        ],
        "cow_target": 10,
        "cow_start_day": 3,
        "hands_cap": 12,
        "hands_ramp_additional": 8,
        "feed_units_per_animal": 1,
        "care_priority": 4,
    },
    "e_dairy_dense_feed2": {
        "second_land_day": 3,
        "third_land_day": 6,
        "crop_blocks": [
            [["WHEAT", 6]],
            [["WHEAT", 4]],
            [["WHEAT", 2]],
        ],
        "cow_target": 10,
        "cow_start_day": 3,
        "hands_cap": 12,
        "hands_ramp_additional": 8,
        "feed_units_per_animal": 2,
        "care_priority": 4,
    },
    "f_cow_focus": {
        "second_land_day": 3,
        "third_land_day": 6,
        "crop_blocks": [
            [["WHEAT", 8]],
            [["WHEAT", 4]],
            [["WHEAT", 2]],
        ],
        "sheep_initial": 1,
        "sheep_target": 2,
        "cow_target": 12,
        "cow_start_day": 3,
        "hands_cap": 12,
        "hands_ramp_additional": 8,
        "feed_units_per_animal": 1,
        "care_priority": 4,
    },
    "g_wool_dairy": {
        "second_land_day": 3,
        "third_land_day": 6,
        "crop_blocks": [
            [["WHEAT", 8]],
            [["WHEAT", 4]],
            [["WHEAT", 2]],
        ],
        "sheep_target": 8,
        "cow_target": 8,
        "cow_start_day": 3,
        "hands_cap": 14,
        "feed_units_per_animal": 1,
        "care_priority": 4,
    },
}


def screen_play(task: tuple[str, str, int, dict[str, Any]]) -> dict[str, Any]:
    variant, scenario_path, seat, genome = task
    result = play((scenario_path, seat, genome))
    result["variant"] = variant
    return result


def canonical_sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--scenarios-per-source", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--genomes-json", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.scenarios_per_source < 1 or args.scenarios_per_source > 32:
        raise ValueError("scenarios-per-source 必须在 1..32")

    genomes = (
        json.loads(args.genomes_json.read_text(encoding="utf-8"))
        if args.genomes_json else GENOMES
    )
    if not isinstance(genomes, dict) or not genomes:
        raise ValueError("genomes-json 必须是非空 variant -> genome 对象")
    manifest, scenarios = manifest_scenarios(args.panel_dir, args.scenarios_per_source)
    tasks = [
        (variant, str(scenario["scenario_path"]), seat, genome)
        for variant, genome in genomes.items()
        for scenario in scenarios
        for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(screen_play, tasks, chunksize=1))

    variants: dict[str, Any] = {}
    for index, (variant, genome) in enumerate(genomes.items()):
        variant_rows = [row for row in rows if row["variant"] == variant]
        sources = {
            source: summarize_rows(
                [row for row in variant_rows if row.get("source_class") == source],
                117230 + index * 10 + source_index,
            )
            for source_index, source in enumerate(SOURCES)
        }
        overall = summarize_rows(variant_rows, 117239 + index * 10)
        integrity = (
            overall["error_count"] == 0
            and overall["action_violations"] == 0
            and overall["trajectory_mismatches"] == 0
            and overall["contract_invariant_events"] == 0
        )
        variants[variant] = {
            "genome": genome or "R2.1_B_CURRENT_DEFAULT",
            "genome_sha256": canonical_sha(genome),
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
    output_dir = args.output_dir or (args.panel_dir / "evaluations/r2_1_b_genome_screen_1")
    output_dir.mkdir(parents=True, exist_ok=True)
    games_path = output_dir / "games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in sorted(rows, key=lambda item: (
            item["variant"], str(item.get("source_class")), int(item.get("episode_id") or -1),
            int(item.get("candidate_seat") or 0),
        )):
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    best_genome = genomes[best]
    (output_dir / "selected_genome.json").write_text(
        json.dumps(best_genome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    payload = {
        "schema": "v117-r2.1-b-balanced-genome-screen-v1",
        "strength_status": "DEVELOPMENT_SCREEN_ONLY",
        "split": "development",
        "blind_content_accessed": False,
        "selection_rule": "integrity, pure_win_rate, mean_margin, candidate_reward, variant_id",
        "scenario_selection": "每来源按 observed_date + episode_id 排序后的固定前 N 个",
        "scenarios_per_source": args.scenarios_per_source,
        "scenario_ids": {
            source: [int(row["episode_id"]) for row in scenarios if row["source_class"] == source]
            for source in SOURCES
        },
        "manifest_sha256": canonical_sha(manifest),
        "games_sha256": hashlib.sha256(games_path.read_bytes()).hexdigest(),
        "ranking": ranking,
        "selected_variant": best,
        "selected_genome_sha256": canonical_sha(best_genome),
        "variants": variants,
        "next_step": "只把选中 genome 放到完整 64 场景×双座位 Development；未通过前不改 Router",
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    compact = {
        "ranking": ranking,
        "selected_variant": best,
        "metrics": {
            key: {
                "win_rate": variants[key]["overall"]["pure_win_rate"],
                "mean_margin": variants[key]["overall"]["mean_margin"],
                "candidate_reward": variants[key]["overall"]["mean_candidate_reward"],
                "final_crops": variants[key]["overall"]["mean_final_crops"],
                "final_animals": variants[key]["overall"]["mean_final_animals"],
            }
            for key in ranking
        },
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0 if all(row["integrity_pass"] for row in variants.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
