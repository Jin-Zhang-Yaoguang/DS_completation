"""经营专家公共接口；只生成日级合同。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from contracts import DailyContract, TargetRealization
from schema import PRODUCTS, CanonicalState
from state_ledger import RuntimeFeedback


@dataclass(frozen=True)
class ExpertQualification:
    implemented: bool
    status: str
    router_enabled: bool
    evidence: str


class ContractExpert(Protocol):
    expert_id: str
    qualification: ExpertQualification

    def eligibility(self, state: CanonicalState, feedback: RuntimeFeedback,
                    previous: DailyContract | None) -> Mapping[str, Any]: ...

    def propose(self, state: CanonicalState, feedback: RuntimeFeedback,
                previous: DailyContract | None) -> DailyContract: ...


class ExpertBase:
    expert_id = "ABSTRACT"
    qualification = ExpertQualification(False, "NOT_IMPLEMENTED", False, "none")

    def _transition_cost(self, state: CanonicalState, previous: DailyContract | None,
                         lands: int, hands: int, animals: Mapping[str, int]) -> float:
        if previous is None:
            return 0.0
        if previous.expert_id == self.expert_id:
            return 0.0
        land_gap = abs(int(previous.lands) - int(lands)) * 300
        hand_gap = abs(int(previous.hands) - int(hands)) * 40
        animal_gap = sum(abs(int(previous.animals.get(key, 0)) - int(value)) for key, value in animals.items()) * 80
        task_cost = len(state.actor_tasks) * 2
        return float(land_gap + hand_gap + animal_gap + task_cost)

    def _contract(self, *, state: CanonicalState, previous: DailyContract | None,
                  eligibility: Mapping[str, Any], terminate_if: Mapping[str, Any],
                  lands: int, hands: int, crops: Mapping[str, int], animals: Mapping[str, int],
                  structures: Mapping[str, int], production: Mapping[str, int],
                  reserves: Mapping[str, int], cash_reserve: int, purchase_budget: int,
                  sell_priority: tuple[str, ...], sell_cap: Mapping[str, int],
                  labor_priority: Mapping[str, int], deadlines: Mapping[str, int],
                  risk_budget: Mapping[str, float], min_dwell_days: int, risk_tier: str) -> DailyContract:
        identity = f"{self.expert_id}:s{state.seat}:d{state.day}:e{state.step}"
        return DailyContract(
            expert_id=self.expert_id, contract_id=identity, issued_at=state.step, issued_day=state.day,
            valid_until_day=min(29, state.day + max(1, min_dwell_days) - 1),
            min_dwell_days=max(1, min_dwell_days), eligibility=dict(eligibility),
            terminate_if=dict(terminate_if),
            asset_targets={"lands": int(lands), "hands": int(hands), "crops": dict(crops),
                           "animals": dict(animals), "structures": dict(structures)},
            production_quotas={str(k): max(0, int(v)) for k, v in production.items()},
            inventory_reserves={str(k): max(0, int(v)) for k, v in reserves.items()},
            cash_reserve=max(0, int(cash_reserve)), purchase_budget=max(0, int(purchase_budget)),
            sell_priority=tuple(item for item in sell_priority if item in PRODUCTS),
            sell_cap={str(k): max(0, int(v)) for k, v in sell_cap.items()},
            labor_priority={str(k): int(v) for k, v in labor_priority.items()},
            deadlines={str(k): int(v) for k, v in deadlines.items()},
            risk_budget={str(k): float(v) for k, v in risk_budget.items()},
            transition_cost=self._transition_cost(state, previous, lands, hands, animals),
            target_realization=TargetRealization(), risk_tier=risk_tier,
        )
