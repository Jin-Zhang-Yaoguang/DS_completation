#!/usr/bin/env python3
"""汇总 V124 Gate 0：来源、去重、切分、特征和独立性边界。"""

from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPLAY_HOME = HERE.parent / "community_research/top20_gold_distillation_active/replay_data"
CUTOFF = date(2026, 8, 20)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    dataset = load(HERE / "dataset/dataset_manifest.json")
    feature = load(HERE / "dataset/feature_contract.json")
    families = load(HERE / "dataset/behavior_family_audit.json")
    training = load(HERE / "training/nested_cv_report.json")
    independence = load(HERE / "independence_audit.json")
    train_receipt = load(REPLAY_HOME / "top20_cli_receipt.json")
    reserved_receipt = load(REPLAY_HOME / "receipt.json")
    train_keys = {(int(row["episode_id"]), str(row["sha256"])) for row in train_receipt["rows"]}
    reserved_keys = {(int(row["episode_id"]), str(row["sha256"])) for row in reserved_receipt["rows"]}

    trajectory_counts: Counter = Counter()
    with (HERE / "dataset/daily_contract_families.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            trajectory_counts[(row["episode_id"], row["replay_sha256"], row["teacher"], row["seat"])] += 1
    outer_overlap_zero = all(fold["episode_overlap"] == 0 for fold in training["outer_folds"])
    inner_overlap_zero = all(
        fold["episode_overlap"] == 0
        for outer in training["outer_folds"]
        for candidate in outer["inner_cv"]
        for fold in candidate["folds"]
    )
    checks = {
        "training_dates_at_or_after_cutoff": all(date.fromisoformat(row["actual_date"]) >= CUTOFF for row in train_receipt["rows"]),
        "reserved_dates_at_or_after_cutoff": all(date.fromisoformat(row["actual_date"]) >= CUTOFF for row in reserved_receipt["rows"]),
        "engine_exactly_1_32_7": all(str(row["module_version"]) == "1.32.7" for row in (*train_receipt["rows"], *reserved_receipt["rows"])),
        "training_panel_only_auxiliary": all(row["source_panel"] == "top20_cli_training_auxiliary" for row in train_receipt["rows"]),
        "formal_panels_not_used_for_training": dataset["leakage_checks"]["formal_online_rows_used_for_training"] == 0,
        "training_reserved_episode_sha_disjoint": not train_keys.intersection(reserved_keys),
        "all_training_trajectories_have_exactly_30_days": bool(trajectory_counts) and set(trajectory_counts.values()) == {30},
        "runtime_future_fields_zero": feature["runtime_uses_future_actions"] is False and not feature["forbidden_found"],
        "action_tape_not_exported": dataset["leakage_checks"]["raw_action_tape_exported"] is False,
        "outer_episode_overlap_zero": outer_overlap_zero,
        "inner_episode_overlap_zero": inner_overlap_zero,
        "teacher_family_minimum_support_met": min(families["teacher"]["trajectory_support"].values()) >= 8,
        "opponent_family_minimum_support_met": min(families["opponent"]["trajectory_support"].values()) >= 4,
        "independent_agent_audit_pass": independence["status"] == "PASS",
        "strategy_parent_is_null": independence["strategy_parent"] is None,
    }
    core_pass = all(checks.values())
    time_available = dataset["split_policy"]["time_axis_status"] == "AVAILABLE"
    report = {
        "schema": "kaggriculture-v124-gate0-audit-v1",
        "status": "PASS_TIME_BLIND_DEFERRED" if core_pass and not time_available else "PASS" if core_pass else "FAIL",
        "checks": checks,
        "training_replay_keys": len(train_keys),
        "reserved_replay_keys": len(reserved_keys),
        "training_reserved_overlap": len(train_keys.intersection(reserved_keys)),
        "time_axis": {
            "available_inside_training": time_available,
            "reason": dataset["split_policy"]["time_axis_status"],
            "blind_panel_opened": False,
            "replacement": dataset["split_policy"]["time_blind_replacement"],
        },
        "artifact_sha256": {
            str(path.relative_to(HERE)): sha(path)
            for path in (
                HERE / "main.py", HERE / "contract.py", HERE / "train_hmoe.py",
                HERE / "training/contract_hmoe.joblib",
                HERE / "dataset/dataset_manifest.json",
                HERE / "dataset/feature_contract.json",
                HERE / "dataset/behavior_family_audit.json",
            )
        },
        "promotion_effect": "NONE",
    }
    (HERE / "gate0_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if core_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
