#!/usr/bin/env python3
"""把执行证据整理为 README 预注册的稳定产物名。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics


HERE = Path(__file__).resolve().parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(name: str, value: dict) -> None:
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    development = load(HERE / "development/development_report.json")
    gate0 = load(HERE / "gate0_audit.json")

    dump("dataset_manifest.json", dataset)
    dump("feature_contract.json", feature)
    dump("split_manifest.json", {
        "schema": "kaggriculture-v124-split-manifest-v1",
        "status": "NESTED_SPLITS_COMPLETE_TIME_BLIND_DEFERRED",
        "training_axis": dataset["split_policy"],
        "teacher_families": sorted(families["teacher"]["trajectory_support"]),
        "opponent_families": sorted(families["opponent"]["trajectory_support"]),
        "outer_episode_overlap_zero": all(fold["episode_overlap"] == 0 for fold in training["outer_folds"]),
        "blind": {"opened": False, "reason": "single training collection date and Gate 2 failure"},
    })
    dump("teacher_family_registry.json", {
        "schema": "kaggriculture-v124-teacher-family-registry-v1",
        "status": "READY",
        **families["teacher"],
        "fingerprint_policy": families["fingerprint_policy"],
    })
    dump("opponent_family_registry.json", {
        "schema": "kaggriculture-v124-opponent-family-registry-v1",
        "status": "READY",
        **families["opponent"],
        "fingerprint_policy": families["fingerprint_policy"],
    })
    dump("expert_support_report.json", {
        "schema": "kaggriculture-v124-expert-support-v1",
        "status": "PASS",
        "minimum": {"teachers": 3, "episodes": 8},
        "experts": training["final_expert_support"],
    })
    dump("training_report.json", {
        "schema": "kaggriculture-v124-training-report-v1",
        "status": training["status"],
        "training_rows": training["training_rows"],
        "feature_count": training["feature_count"],
        "active_target_count": training["active_target_count"],
        "configs": training["configs"],
        "full_inner_selection": training["full_inner_selection"],
        "model_sha256": sha(HERE / "training/contract_hmoe.joblib"),
        "promotion_effect": "NONE",
    })
    dump("outer_validation_report.json", {
        "schema": "kaggriculture-v124-outer-validation-v1",
        "status": training["status"],
        "method": training["method"],
        "outer_summary": training["outer_summary"],
        "outer_folds": training["outer_folds"],
        "gates": training["gates"],
        "promotion_effect": "NONE",
    })
    dump("development_report.json", development)

    candidate_files = (
        HERE / "main.py", HERE / "contract.py", HERE / "train_hmoe.py",
        HERE / "training/contract_hmoe.joblib",
    )
    candidate_hashes = {str(path.relative_to(HERE)): sha(path) for path in candidate_files}
    composite = hashlib.sha256(json.dumps(candidate_hashes, sort_keys=True).encode()).hexdigest()
    dump("candidate_freeze_manifest.json", {
        "schema": "kaggriculture-v124-candidate-freeze-v1",
        "status": "NOT_FROZEN_GATE2_FAILED",
        "candidate": "V124-R0",
        "composite_sha256": composite,
        "files": candidate_hashes,
        "gate3_eligible": False,
        "reason": "known closed-loop development gate failed 0/32 against both families",
    })
    dump("local_generalization_gate.json", {
        "schema": "kaggriculture-v124-local-generalization-gate-v1",
        "status": "NOT_OPENED",
        "games_played": 0,
        "required_games": 512,
        "reason": "Gate 2 failed; opening untouched Gate 3 would waste blind evidence",
    })
    dump("online_primary_report.json", {
        "schema": "kaggriculture-v124-online-primary-v1",
        "status": "NOT_STARTED_NOT_AUTHORIZED",
        "submission_attempted": False,
        "reason": "Gate 3 not passed and user explicitly withheld Kaggle submission authorization",
    })
    dump("official_confirmation_report.json", {
        "schema": "kaggriculture-v124-official-confirmation-v1",
        "status": "NOT_STARTED",
        "episodes_used": 0,
        "reason": "online primary was not authorized or started; panels remain independent",
    })

    game_rows = [json.loads(line) for line in (HERE / "development/games.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rewards = [float(row["candidate_reward"]) for row in game_rows if row["status"] == "DONE"]
    decision = {
        "schema": "kaggriculture-v124-decision-v1",
        "status": "STOPPED_AT_GATE2_NOT_GOLD",
        "decision": "STOP",
        "gold_status": "NOT_GOLD",
        "authorization_status": "NOT_AUTHORIZED",
        "gate_status": {
            "gate0": gate0["status"],
            "gate1": training["status"],
            "gate2": development["status"],
            "gate3": "NOT_OPENED",
            "gate4": "NOT_STARTED_NOT_AUTHORIZED",
            "gate5": "NOT_STARTED",
        },
        "development_evidence": {
            "games": development["completed_games"],
            "errors": development["error_count"],
            "matchups": development["matchups"],
            "candidate_reward_median": statistics.median(rewards),
            "candidate_reward_min": min(rewards),
            "candidate_reward_max": max(rewards),
        },
        "reason": "offline aggregate-contract prediction generalized, but the independent executor failed to realize the contracts in closed loop; both known-family win rates were 0%",
        "anti_overfit_action": "do not patch against observed V120/V21 games; keep Gate 3 unopened",
        "kaggle_submission": {"attempted": False, "authorized": False},
    }
    dump("decision.json", decision)
    print(json.dumps({
        "status": decision["status"],
        "gate_status": decision["gate_status"],
        "candidate_composite_sha256": composite,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
