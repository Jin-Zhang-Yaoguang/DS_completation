"""V117 日级经营合同及其守恒检查。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class TargetRealization:
    """合同目标的事实账本；不保存历史动作路线。"""

    completed: Mapping[str, int] = field(default_factory=dict)
    in_flight: Mapping[str, int] = field(default_factory=dict)
    blocked: Mapping[str, str] = field(default_factory=dict)
    abandoned: Mapping[str, str] = field(default_factory=dict)

    def remaining(self, key: str, target: int) -> int:
        return max(0, int(target) - int(self.completed.get(key, 0)) - int(self.in_flight.get(key, 0)))


@dataclass(frozen=True)
class DailyContract:
    """专家与公共执行底盘之间唯一、显式、可审计的接口。"""

    expert_id: str
    contract_id: str
    issued_at: int
    issued_day: int
    valid_until_day: int
    min_dwell_days: int
    eligibility: Mapping[str, Any]
    terminate_if: Mapping[str, Any]
    asset_targets: Mapping[str, Any]
    production_quotas: Mapping[str, int]
    inventory_reserves: Mapping[str, int]
    cash_reserve: int
    purchase_budget: int
    sell_priority: tuple[str, ...]
    sell_cap: Mapping[str, int]
    labor_priority: Mapping[str, int]
    deadlines: Mapping[str, int]
    risk_budget: Mapping[str, float]
    transition_cost: float
    target_realization: TargetRealization = field(default_factory=TargetRealization)
    risk_tier: str = "NORMAL"

    @property
    def lands(self) -> int:
        return int(self.asset_targets.get("lands", 1))

    @property
    def hands(self) -> int:
        return int(self.asset_targets.get("hands", 0))

    @property
    def crops(self) -> dict[str, int]:
        return {str(key): int(value) for key, value in dict(self.asset_targets.get("crops", {})).items()}

    @property
    def animals(self) -> dict[str, int]:
        return {str(key): int(value) for key, value in dict(self.asset_targets.get("animals", {})).items()}

    @property
    def feed_reserve(self) -> int:
        return int(self.inventory_reserves.get("WHEAT", 0))

    @property
    def sell_floor(self) -> float:
        return float(self.risk_budget.get("sell_floor", 0.55))

    def stable_payload(self) -> dict[str, Any]:
        return {
            "expert_id": self.expert_id,
            "contract_id": self.contract_id,
            "issued_at": self.issued_at,
            "issued_day": self.issued_day,
            "valid_until_day": self.valid_until_day,
            "min_dwell_days": self.min_dwell_days,
            "eligibility": dict(self.eligibility),
            "terminate_if": dict(self.terminate_if),
            "asset_targets": dict(self.asset_targets),
            "production_quotas": dict(self.production_quotas),
            "inventory_reserves": dict(self.inventory_reserves),
            "cash_reserve": self.cash_reserve,
            "purchase_budget": self.purchase_budget,
            "sell_priority": list(self.sell_priority),
            "sell_cap": dict(self.sell_cap),
            "labor_priority": dict(self.labor_priority),
            "deadlines": dict(self.deadlines),
            "risk_budget": dict(self.risk_budget),
            "transition_cost": self.transition_cost,
            "risk_tier": self.risk_tier,
        }

    def signature(self) -> str:
        raw = json.dumps(self.stable_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def contract_violations(contract: DailyContract) -> tuple[str, ...]:
    """Fail-closed 合同检查；返回确定性、单义的违规码。"""

    errors: list[str] = []
    payload = repr(contract).lower()
    forbidden_runtime_fields = ("replay_id", "teacher" + "_id", "future_shop", "seed=")
    if any(token in payload for token in forbidden_runtime_fields):
        errors.append("FORBIDDEN_INFORMATION")
    if not contract.expert_id or not contract.contract_id:
        errors.append("MISSING_IDENTITY")
    if contract.issued_at < 0 or contract.valid_until_day < contract.issued_day:
        errors.append("INVALID_VALIDITY")
    if contract.min_dwell_days < 1:
        errors.append("INVALID_DWELL")
    if contract.cash_reserve < 0 or contract.purchase_budget < 0 or contract.transition_cost < 0:
        errors.append("NEGATIVE_BUDGET")
    if contract.lands < 1 or contract.hands < 0:
        errors.append("INVALID_ASSET_TARGET")
    if any(int(value) < 0 for value in (*contract.crops.values(), *contract.animals.values())):
        errors.append("NEGATIVE_TARGET")
    if not contract.eligibility or not contract.terminate_if:
        errors.append("MISSING_OPTION_BOUNDARY")
    return tuple(errors)


def realize_contract(contract: DailyContract, state: Any, blocked_reasons: tuple[str, ...] = ()) -> DailyContract:
    """从当前真实状态重算目标兑现；不沿用专家的内部预测。"""

    completed: dict[str, int] = {
        "lands": min(contract.lands, int(state.lands)),
        "hands": min(contract.hands, max(0, len(state.positions) - 1)),
    }
    in_flight: dict[str, int] = {}
    for item, target in contract.crops.items():
        completed[f"crop:{item}"] = min(int(target), int(state.crops.get(item, 0)))
        in_flight[f"crop:{item}"] = max(0, int(state.seeds.get(item, 0)))
    for item, target in contract.animals.items():
        completed[f"animal:{item}"] = min(int(target), int(state.animals.get(item, 0)))
    carried: dict[str, int] = {}
    for inventory in state.inventories:
        for item, quantity in inventory.items():
            carried[str(item)] = carried.get(str(item), 0) + max(0, int(quantity))
    for item, target in contract.inventory_reserves.items():
        completed[f"reserve:{item}"] = min(
            int(target), int(state.shed.get(item, 0)) + carried.get(str(item), 0)
        )
    blocked = {str(reason).lower(): str(reason) for reason in blocked_reasons}
    return replace(contract, target_realization=TargetRealization(
        completed=completed, in_flight=in_flight, blocked=blocked, abandoned={}
    ))


def transition_violations(previous: DailyContract | None, candidate: DailyContract,
                          current_day: int, available_cash: int,
                          active_since_day: int | None = None,
                          hard_termination: bool = False) -> tuple[str, ...]:
    """Router 切换前的公共守卫；专家自身不能绕过。"""

    errors = list(contract_violations(candidate))
    if not bool(candidate.eligibility.get("eligible", False)):
        errors.append("INELIGIBLE_EXPERT")
    if candidate.issued_day != current_day:
        errors.append("NON_DAILY_ISSUE")
    if candidate.transition_cost > max(0, int(available_cash) - candidate.cash_reserve):
        errors.append("UNAFFORDABLE_TRANSITION")
    if previous is not None and previous.expert_id != candidate.expert_id:
        age = current_day - (previous.issued_day if active_since_day is None else active_since_day)
        if age < previous.min_dwell_days and not hard_termination:
            errors.append("MIN_DWELL_VIOLATION")
    return tuple(errors)
