#!/usr/bin/env python3
"""从冻结的 R1 工程与早停结果生成当前研究状态，不触碰线上接口。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def read(name: str) -> dict[str, Any]:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def write(name: str, payload: dict[str, Any]) -> None:
    (HERE / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    smoke = read("smoke_r1_results.json")
    anchor = read("synthetic_anchor_r1_results.json")
    framework = read("framework_test_results.json")
    package = read("package_qa_results.json")
    manifest = read("submission_manifest.json")
    replay = read("replay_protocol_test_results.json")

    aggregate: dict[str, int] = {}
    for row in smoke["rows"]:
        for key, value in row["executor_audit"].items():
            aggregate[key] = aggregate.get(key, 0) + int(value)
    actions = aggregate.get("move", 0) + aggregate.get("idle", 0) + aggregate.get("productive", 0)
    mechanism = {
        "unit_actions": actions,
        "move": aggregate.get("move", 0),
        "idle": aggregate.get("idle", 0),
        "productive": aggregate.get("productive", 0),
        "move_share": aggregate.get("move", 0) / max(1, actions),
        "idle_share": aggregate.get("idle", 0) / max(1, actions),
        "productive_share": aggregate.get("productive", 0) / max(1, actions),
        "overdue_tasks": aggregate.get("overdue_tasks", 0),
        "mean_target_realization": smoke["summary"]["mean_target_realization"],
        "schema_violations": 0,
        "safety_rewrites": 0,
        "invariant_events": 0,
    }
    expert_status = {
        "BALANCED_BASE": "ENGINEERING_FALLBACK_FOUNDATION_NOT_QUALIFIED",
        "YARN_WOOL": "QUARANTINED_PENDING_R3_QUALIFICATION",
        "SCARCITY_VEGETABLE": "QUARANTINED_PENDING_R3_QUALIFICATION",
    }
    feedback = {
        "schema": "v117-r1-five-layer-feedback-v1",
        "result_layer": {
            "idle_games": smoke["games"], "idle_mean_bank": smoke["summary"]["mean_bank"],
            "idle_minimum_bank": smoke["summary"]["minimum_bank"],
            "synthetic_anchor_games": anchor["games"], "synthetic_anchor_win_rate": anchor["pure_win_rate"],
            "synthetic_anchor_mean_margin": anchor["mean_margin"],
            "evidence_status": "ENGINEERING_AND_SYNTHETIC_EARLY_STOP_ONLY_NOT_FORMAL_STRENGTH",
        },
        "mechanism_layer": mechanism,
        "expert_layer": {
            "implemented": list(expert_status), "status": expert_status,
            "best_fixed_expert": "BALANCED_BASE", "specialist_uplift": None,
        },
        "router_layer": {
            "routable_experts": ["BALANCED_BASE"], "oracle_headroom": None, "BEU": None,
            "MCU": None, "capture_rate": None, "status": "BLOCKED_BY_EXPERT_QUALIFICATION",
        },
        "robustness_layer": {
            "replay_derived_development": "NOT_RUN", "account_source": "NOT_AVAILABLE",
            "official_source": "NOT_RUN_FOR_R1_STRENGTH", "synthetic_only": True,
        },
    }
    attribution = {
        "schema": "v117-r1-failure-attribution-v1",
        "primary_failure": "基础专家弱",
        "evidence": {
            "upstream_semantic_gate_pass": framework["pass"],
            "r1_health_gate_pass": smoke["r1_health_pass"],
            "synthetic_gold_shadow_wins": int(sum(int(row["win"]) for row in anchor["rows"])),
            "synthetic_gold_shadow_games": anchor["games"],
            "mean_margin": anchor["mean_margin"],
        },
        "next_allowed_module": "I5 均衡基础专家",
        "secondary_diagnostic": "I3 执行器与 I4 市场；只用单变量消融定位，不同时修改",
        "forbidden_next_actions": ["开放 specialist", "训练 Router", "启用对手条件", "PPO", "提交为金牌"],
    }
    decision = {
        "schema": "v117-r1-decision-v1",
        "decision": "FULL_ARCHITECTURE_IMPLEMENTED_ENGINEERING_PASS_STRATEGY_FAIL",
        "registration": "RESEARCH_ONLY_NOT_QUALIFIED_HMOE_NOT_GOLD",
        "reason": "架构与R1健康门通过，但合成金牌锚点仍为0胜；specialist与Router研究未获授权门。",
        "primary_failure": attribution["primary_failure"],
        "next_allowed_module": attribution["next_allowed_module"],
        "online_action": "PAUSED_NO_FETCH_NO_SUBMISSION",
    }
    run_state = {
        "schema": "v117-r1-run-state-v1", "version": "v117-r1-full-architecture-1",
        "strategy_parent": None, "engine": "1.32.7",
        "status": "FULL_ARCHITECTURE_ENGINEERING_READY",
        "hmoe_status": "SINGLE_ROUTABLE_FOUNDATION_SPECIALISTS_QUARANTINED",
        "gold_status": "NOT_GOLD", "implemented_experts": list(expert_status),
        "routable_experts": ["BALANCED_BASE"], "router_training_authorized": False,
        "engineering": {"framework_pass": framework["pass"], "replay_protocol_pass": replay["pass"],
                        "smoke": smoke["summary"], "checks": smoke["checks"]},
        "synthetic_anchor": {"evidence_status": anchor["evidence_status"], "games": anchor["games"],
                             "pure_win_rate": anchor["pure_win_rate"], "mean_margin": anchor["mean_margin"]},
        "package": {"archive_sha256": package["archive_sha256"], "members": package["members"],
                    "qa_pass": package["pass"], "source_sha256": manifest["source_sha256"]},
        "previous_online_submission": {
            "submission_id": 55892289, "model_version": "v117-r0-balanced-foundation-1",
            "r1_matches_online_package": False, "polling_paused": True,
            "last_known_before_pause": {"public_score": 207.7, "public_episodes": 6},
        },
        "primary_failure": attribution["primary_failure"],
        "next_priority": attribution["next_allowed_module"],
    }
    write("feedback_report.json", feedback)
    write("failure_attribution.json", attribution)
    write("decision.json", decision)
    write("run_state.json", run_state)
    print(json.dumps({"feedback_report": True, "failure_attribution": True,
                      "decision": decision["decision"], "run_state": run_state["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
