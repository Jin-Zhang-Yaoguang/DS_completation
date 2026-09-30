"""羊毛经营专家：独立羊毛资产、饲料、劳动和现金合同。"""

from __future__ import annotations

import math
from typing import Any, Mapping

from contracts import DailyContract
from schema import BASE_PRICE, PRODUCTS, CanonicalState
from state_ledger import RuntimeFeedback

from .base import ExpertBase, ExpertQualification


class YarnWoolExpert(ExpertBase):
    expert_id = "YARN_WOOL"
    qualification = ExpertQualification(
        implemented=True,
        status="QUARANTINED_PENDING_R3_QUALIFICATION",
        router_enabled=False,
        evidence="No Replay-derived eligible uplift CI or Oracle coverage yet",
    )

    def eligibility(self, state: CanonicalState, feedback: RuntimeFeedback,
                    previous: DailyContract | None) -> Mapping[str, Any]:
        yarn = "YARN_STORE" in state.shops
        price_support = state.prices.get("WOOL", BASE_PRICE["WOOL"]) >= int(BASE_PRICE["WOOL"] * 0.85)
        capacity = feedback.labor_pressure < 0.8 and feedback.feed_risk < 0.75 and state.day <= 23
        return {
            "eligible": bool(yarn and price_support and capacity),
            "reason": "PUBLIC_YARN_WITH_CAPACITY" if yarn and capacity else "YARN_CONDITION_MISSING",
            "confidence": 0.7 if yarn and capacity else 0.0,
        }

    def propose(self, state: CanonicalState, feedback: RuntimeFeedback,
                previous: DailyContract | None) -> DailyContract:
        lands = 2 if state.day < 9 else 3
        sheep = 8 if state.day < 12 else 10
        crops = {"WHEAT": max(18, sheep * 2), "STRAWBERRY": 6, "MELON": 4}
        animals = {"SHEEP": sheep}
        hands = min(15, max(7, math.ceil((sum(crops.values()) + 2 * sheep) / 3.7)))
        priority = ("WOOL", "STRAWBERRY", "MELON", "FERTILIZER", "WHEAT", "MILK", "EGG", "CARROT", "TOMATO")
        return self._contract(
            state=state, previous=previous, eligibility=self.eligibility(state, feedback, previous),
            terminate_if={"yarn_absent": True, "feed_risk_above": 0.75, "day_after": 25, "hard_triggered": False},
            lands=lands, hands=hands, crops=crops, animals=animals, structures={"PASTURE": sheep},
            production={"WOOL": sheep * 2, "WHEAT": sheep * 2},
            reserves={"WHEAT": sheep * 3, "WOOL": 2}, cash_reserve=400,
            purchase_budget=max(0, min(6000, state.money - 400)), sell_priority=priority,
            sell_cap={item: (16 if item == "WOOL" else 24) for item in PRODUCTS},
            labor_priority={"FEED": 0, "HARVEST": 1, "WATER": 1, "CARE": 5, "PLANT": 3},
            deadlines={"FEED": 18, "WATER": 21, "HARVEST": 22, "RETURN": 23},
            risk_budget={"sell_floor": 0.68, "max_labor_pressure": 0.82, "max_shed_pressure": 0.82},
            min_dwell_days=3, risk_tier="MEDIUM",
        )
