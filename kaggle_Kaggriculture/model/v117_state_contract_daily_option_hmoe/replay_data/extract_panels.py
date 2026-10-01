#!/usr/bin/env python3
"""提取已预注册 Train/Development 的外生场景；Blind 永远拒绝在本脚本中打开。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_PANEL = HERE / "panels/r2_1_v1"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from protocol import atomic_json_dump, extract_registered, validate_scenario_isolation  # noqa: E402


def extract(args: argparse.Namespace) -> dict[str, Any]:
    if args.split == "blind_confirmation":
        raise PermissionError("Blind 只能在候选冻结后的最终确认流程打开")
    manifest_path = args.panel_dir / "replay_panel_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [row for row in manifest.get("assignments", []) if row.get("split") == args.split]
    if not selected:
        raise ValueError(f"manifest 没有 {args.split} assignments")
    scenarios: list[dict[str, Any]] = []
    scenario_root = args.panel_dir / "scenarios"
    for assignment in selected:
        scenario = extract_registered(
            manifest, source_class=str(assignment["source_class"]),
            episode_id=int(assignment["episode_id"]),
        )
        destination = (scenario_root / str(assignment["source_class"]) / args.split /
                       f"episode-{assignment['episode_id']}.json")
        atomic_json_dump(scenario, destination)
        scenario["scenario_path"] = str(destination.resolve())
        scenarios.append(scenario)

    isolation = validate_scenario_isolation(scenarios)
    by_identity = {(row["source_class"], int(row["episode_id"])): row for row in scenarios}
    updated = json.loads(json.dumps(manifest))
    for assignment in updated["assignments"]:
        identity = (assignment["source_class"], int(assignment["episode_id"]))
        scenario = by_identity.get(identity)
        if scenario is not None:
            assignment["scenario_sha256"] = scenario["scenario_sha256"]
            assignment["scenario_path"] = scenario["scenario_path"]
    updated_path = args.panel_dir / "replay_panel_manifest_extracted.json"
    atomic_json_dump(updated, updated_path)

    exposure_path = args.panel_dir / "exposure_ledger.json"
    exposure = json.loads(exposure_path.read_text(encoding="utf-8"))
    exposure_by_id = {row["record_id"]: row for row in exposure.get("records", [])}
    for assignment in selected:
        row = exposure_by_id[assignment["record_id"]]
        scenario = by_identity[(assignment["source_class"], int(assignment["episode_id"]))]
        row["scenario_sha256"] = scenario["scenario_sha256"]
        row["exposure_state"] = "EXOGENOUS_SCENARIO_EXTRACTED"
        row["steps_opened"] = True
        row["historical_actions_materialized"] = False
        row["historical_market_materialized"] = False
        row["historical_rewards_materialized"] = False
    exposure["blind_content_accessed"] = False
    atomic_json_dump(exposure, exposure_path)

    receipt = {
        "schema": "v117-r2.1-scenario-extraction-receipt-v1",
        "split": args.split,
        "scenario_count": len(scenarios),
        "source_counts": {
            source: sum(row["source_class"] == source for row in scenarios)
            for source in ("ACCOUNT_ONLINE", "OFFICIAL_DAILY")
        },
        "isolation": isolation,
        "historical_player_actions_materialized": False,
        "historical_market_or_rewards_materialized": False,
        "blind_content_accessed": False,
        "updated_manifest": str(updated_path.resolve()),
        "pass": True,
    }
    atomic_json_dump(receipt, args.panel_dir / "scenario_extraction_receipt.json")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--split", choices=("train", "development", "blind_confirmation"),
                        default="development")
    return parser.parse_args()


if __name__ == "__main__":
    result = extract(parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
