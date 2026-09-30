"""Fail-closed hourly alignment audit for the long-running V114 goal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent


def audit(run_state: dict, model_dir: Path) -> dict:
    violations: list[str] = []
    if run_state.get("strategy_parent") is not None:
        violations.append("strategy_parent_must_be_null")
    if run_state.get("kaggle_submission") != "NOT_AUTHORIZED_NOT_SUBMITTED":
        violations.append("kaggle_submission_not_authorized")
    boundary = run_state.get("source_boundary") or {}
    if boundary.get("inherits_v113_checkpoint") is not False:
        violations.append("v113_checkpoint_inheritance_forbidden")
    if boundary.get("historical_agents_online_action_source") is not False:
        violations.append("historical_agent_online_action_forbidden")
    active = run_state.get("active_stage") or {}
    training = active.get("training") or {}
    if training.get("value_coefficient") == 0:
        violations.append("value_coefficient_zero_forbidden")
    if training.get("ratio_mode") == "joint":
        violations.append("joint_unit_market_ratio_forbidden")
    exposure = active.get("opponent_exposure") or {}
    if float(exposure.get("v76_share", 0.0) or 0.0) > 0.10 + 1e-12:
        violations.append("v76_share_above_10_percent")
    if float(exposure.get("max_member_share", 0.0) or 0.0) > 0.125 + 1e-12:
        violations.append("single_opponent_share_above_12_5_percent")
    if active.get("gold_blind_access") and run_state.get("phase") != "V4_6_BLIND_CONFIRMATION":
        violations.append("gold_blind_access_before_final_confirmation")
    if not (model_dir / "PPO_V4_PLAN.md").exists():
        violations.append("ppo_v4_plan_missing")
    foundation_contract: dict = {}
    foundation_gate_result: dict = {}
    if str(run_state.get("phase", "")).startswith("V4_2"):
        if active.get("name") != "V4_2":
            violations.append("v4_2_phase_active_stage_mismatch")
        gate_protocol = active.get("gate_protocol") or {}
        if gate_protocol.get("L0") != "HARD_FOUNDATION_SURVIVAL":
            violations.append("foundation_l0_not_hard")
        if gate_protocol.get("L1") != "HARD_BEHAVIOR_DEDUPLICATED_LOCAL_V1_V10":
            violations.append("foundation_l1_not_hard")
        if gate_protocol.get("L2") != "SHADOW_DIAGNOSTIC_ONLY":
            violations.append("foundation_l2_not_shadow_only")
        registry_path = model_dir / "opponent_registry.json"
        if not registry_path.is_file():
            violations.append("opponent_registry_missing")
        else:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            foundation_contract = registry.get("foundation_l1") or {}
            representative_ids = foundation_contract.get("representative_ids") or []
            if len(representative_ids) != 4 or len(set(representative_ids)) != 4:
                violations.append("foundation_l1_not_four_unique_representatives")
        foundation_gate_result = (
            (run_state.get("failed_gates") or {}).get("V4_2_FOUNDATION_PROGRAM_L1") or {}
        )
    return {
        "schema": "kaggriculture-v114-hourly-plan-audit-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "phase": run_state.get("phase"),
        "status": run_state.get("status"),
        "gold_status": run_state.get("gold_status"),
        "foundation_l1_registry_status": foundation_contract.get("status"),
        "foundation_l1_gate_status": foundation_gate_result.get("status"),
        "foundation_candidates_registered": foundation_gate_result.get(
            "foundation_candidates_registered"
        ),
        "foundation_l1_representatives": foundation_contract.get("representative_ids", []),
        "next_gate": run_state.get("next_gate"),
        "violations": violations,
        "aligned": not violations,
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-state", type=Path, default=HERE / "run_state.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(json.loads(args.run_state.read_text(encoding="utf-8")), args.run_state.parent)
    atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["aligned"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
