#!/usr/bin/env python3
"""校验 V124 迭代协议、R0 不可变证据和 R1 启动边界。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "iteration_registry.json"
REPORT = HERE / "iteration_protocol_validation.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    cycles = registry.get("cycles", [])
    ids = [cycle.get("candidate_id") for cycle in cycles]
    r0 = next((cycle for cycle in cycles if cycle.get("candidate_id") == "V124-R0"), {})
    r1 = next((cycle for cycle in cycles if cycle.get("candidate_id") == "V124-R1"), {})
    evidence_checks = {
        name: (HERE / name).is_file() and sha256(HERE / name) == expected
        for name, expected in r0.get("immutable_evidence", {}).items()
    }
    invariants = registry.get("invariants", {})
    checks = {
        "schema": registry.get("schema") == "kaggriculture-v124-iteration-registry-v1",
        "program_iteration_ready": registry.get("program_status") == "ITERATION_READY",
        "candidate_ids_unique": len(ids) == len(set(ids)) and None not in ids,
        "single_active_design_cycle": sum(
            cycle.get("status") in {"DESIGN_READY_NOT_STARTED", "DRAFT", "TRAINING"}
            for cycle in cycles
        ) == 1,
        "r0_retired_not_gold": r0.get("status") == "RETIRED_GATE2_FAILED" and registry.get("gold_status") == "NOT_GOLD",
        "r0_gate3_unopened": r0.get("gate_status", {}).get("gate3") == "NOT_OPENED",
        "r0_opened_dev_is_diagnostic_only": all(
            r0.get("panel_transitions", {}).get(name) == "DIAGNOSTIC_ONLY"
            for name in ("gate2_v120_block", "gate2_v21_v29_v76_block")
        ),
        "r0_immutable_evidence_matches": bool(evidence_checks) and all(evidence_checks.values()),
        "r1_has_one_primary_change": bool(r1.get("single_primary_change")) and bool(r1.get("causal_hypothesis")),
        "r1_parent_chain_present": r1.get("parent_candidate_id") == "V124-R0" and bool(r1.get("parent_candidate_sha")),
        "r1_not_started_without_confirmation_block": (
            r1.get("status") == "DESIGN_READY_NOT_STARTED"
            and r1.get("fresh_confirmation_block") == "UNALLOCATED_REQUIRED_BEFORE_EVALUATION"
            and r1.get("candidate_sha") is None
        ),
        "one_primary_change_limit": invariants.get("maximum_primary_mechanism_changes_per_candidate") == 1,
        "opened_panels_cannot_be_blind": invariants.get("opened_panel_never_becomes_blind_again") is True,
        "online_panels_not_pooled": invariants.get("online_panels_never_pooled") is True,
        "explicit_submission_authorization_required": (
            invariants.get("submission_requires_explicit_user_authorization") is True
            and registry.get("kaggle_submission", {}).get("authorized") is False
            and registry.get("kaggle_submission", {}).get("attempted") is False
        ),
        "no_uplift_causes_redesign": registry.get("iteration_policy", {}).get("no_uplift_action") == "REDESIGN_REQUIRED_NOT_THRESHOLD_RELAXATION",
        "gate3_requires_all_gate2_layers": registry.get("iteration_policy", {}).get("gate3_eligibility") == "requires Gate 2A Gate 2B and Gate 2C"
    }
    passed = all(checks.values())
    report = {
        "schema": "kaggriculture-v124-iteration-protocol-validation-v1",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "immutable_evidence_checks": evidence_checks,
        "registry_sha256": sha256(REGISTRY),
        "current_program_status": registry.get("program_status"),
        "next_candidate": r1.get("candidate_id"),
        "next_candidate_status": r1.get("status"),
        "gold_status": registry.get("gold_status"),
        "kaggle_submission": registry.get("kaggle_submission")
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
