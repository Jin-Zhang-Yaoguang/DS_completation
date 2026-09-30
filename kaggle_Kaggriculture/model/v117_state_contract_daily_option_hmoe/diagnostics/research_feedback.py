"""双反馈之外的离线五层报告、Oracle 接口与词典序主失败码。"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


FAILURE_ORDER = (
    "Replay准入失败", "Replay覆盖不足", "语义状态失败", "执行器瓶颈", "经济闭环瓶颈",
    "基础专家弱", "条件专家无增益", "专家集合缺口", "门控选择失败", "切换状态漂移",
    "元策略覆盖不足", "尾部风险失败", "稳健性失败", "强化学习负增益", "伪混合专家",
)


def oracle_readiness(router_status: Mapping[str, Any]) -> dict[str, Any]:
    qualification = dict(router_status.get("qualification") or {})
    qualified = [key for key, value in qualification.items()
                 if bool(dict(value).get("router_enabled")) and key != "BALANCED_BASE"]
    ready = len(qualified) >= 1
    return {
        "ready": ready,
        "status": "READY_FOR_COUNTERFACTUAL_BRANCHING" if ready else "BLOCKED_BY_EXPERT_QUALIFICATION",
        "required": "Balanced plus at least one specialist passing R3 gates",
        "qualified_specialists": qualified,
    }


def compute_oracle_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """只计算调用方提供的同状态分支结果；不读取对手身份或 blind 标签。"""
    if not rows:
        return {"available": False, "reason": "NO_COUNTERFACTUAL_BRANCH_ROWS"}
    by_state: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_state.setdefault(str(row["state_id"]), []).append(row)
    experts = sorted({str(row["expert_id"]) for row in rows})
    fixed = {expert: sum(float(row["score"]) for row in rows if row["expert_id"] == expert) for expert in experts}
    oracle = sum(max(float(row["score"]) for row in group) for group in by_state.values())
    best_fixed = max(fixed.values()) if fixed else 0.0
    coverage = Counter(
        str(max(group, key=lambda row: (float(row["score"]), str(row["expert_id"]))) ["expert_id"])
        for group in by_state.values()
    )
    return {
        "available": True, "states": len(by_state), "experts": experts,
        "oracle_score": oracle, "best_fixed_score": best_fixed,
        "oracle_headroom": oracle - best_fixed,
        "best_expert_coverage": {str(key): value / max(1, len(by_state)) for key, value in coverage.items()},
    }


def primary_failure(evidence: Mapping[str, bool]) -> dict[str, Any]:
    for code in FAILURE_ORDER:
        if bool(evidence.get(code, False)):
            next_module = {
                "语义状态失败": "I1 状态与合同", "执行器瓶颈": "I3 统一执行器",
                "经济闭环瓶颈": "I4 市场与融资", "基础专家弱": "I5 均衡基础专家",
                "条件专家无增益": "I6 条件专家", "专家集合缺口": "I6 新机制专家",
                "门控选择失败": "I2/I7 反馈与标签", "切换状态漂移": "I1 合同迁移",
                "尾部风险失败": "I4 风险融资与安全", "稳健性失败": "I9 稳健性",
            }.get(code, "按 rs_plan 第12节处理")
            return {"code": code, "next_allowed_module": next_module}
    return {"code": "NO_FAILURE_ASSIGNED", "next_allowed_module": "保持冻结"}


def build_feedback_report(status: Mapping[str, Any], metrics: Mapping[str, Any] | None = None,
                          robustness: Mapping[str, Any] | None = None) -> dict[str, Any]:
    router = dict(status.get("router") or {})
    seats = dict(status.get("seats") or {})
    executor = {str(seat): dict(value.get("executor") or {}) for seat, value in seats.items()}
    market = {str(seat): dict(value.get("market") or {}) for seat, value in seats.items()}
    loss_attribution = {str(seat): dict(value.get("loss_attribution") or {})
                        for seat, value in seats.items()}
    aggregate_losses: Counter[str] = Counter()
    for payload in loss_attribution.values():
        for category, row in dict(payload.get("totals") or {}).items():
            aggregate_losses[str(category)] += float(dict(row).get("estimated_value", 0.0))
    top_losses = [
        {"category": category, "estimated_value": float(value)}
        for category, value in sorted(aggregate_losses.items(), key=lambda row: (-row[1], row[0]))[:3]
    ]
    invariant_events = sum(len(dict(value.get("ledger") or {}).get("invariant_events") or [])
                           for value in seats.values())
    rewrites = sum(int(value.get("control_rewrites", 0)) for value in seats.values())
    return {
        "schema": "v117-r2.1-a-five-layer-feedback-v2",
        "result_layer": dict(metrics or {"status": "ENGINEERING_ONLY_NO_STRENGTH_CLAIM"}),
        "mechanism_layer": {"executor": executor, "market": market,
                            "loss_attribution": loss_attribution, "top_losses": top_losses,
                            "invariant_events": invariant_events, "control_rewrites": rewrites},
        "expert_layer": {"qualification": router.get("qualification", {}),
                         "implemented": router.get("implemented_experts", [])},
        "router_layer": {"readiness": oracle_readiness(router), "audit": router.get("audit", {}),
                         "seats": router.get("seats", {})},
        "robustness_layer": dict(robustness or {"status": "NOT_EVALUATED"}),
    }
