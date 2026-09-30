"""稀缺蔬菜专家：独立短缺识别、作物、劳动和预算合同。"""

from __future__ import annotations

import math
from typing import Any, Mapping

from contracts import DailyContract
from schema import BASE_PRICE, PRODUCTS, SHOP_PRODUCTS, CanonicalState
from state_ledger import RuntimeFeedback

from .base import ExpertBase, ExpertQualification


class ScarcityVegetableExpert(ExpertBase):
    expert_id = "SCARCITY_VEGETABLE"
    qualification = ExpertQualification(
        implemented=True,
        status="QUARANTINED_PENDING_R3_QUALIFICATION",
        router_enabled=False,
        evidence="No Replay-derived scarcity-domain uplift CI or Oracle coverage yet",
    )

    @staticmethod
    def _focus(state: CanonicalState) -> str:
        candidates = ("CARROT", "TOMATO")
        return max(candidates, key=lambda item: (
            state.prices.get(item, BASE_PRICE[item]) / BASE_PRICE[item],
            -state.market_inventory.get(item, 10000),
            -candidates.index(item),
        ))

    def eligibility(self, state: CanonicalState, feedback: RuntimeFeedback,
                    previous: DailyContract | None) -> Mapping[str, Any]:
        focus = self._focus(state)
        public_support = any(focus in SHOP_PRODUCTS.get(shop, ()) for shop in state.shops)
        price_ratio = state.prices.get(focus, BASE_PRICE[focus]) / BASE_PRICE[focus]
        inventory_delta = state.market_inventory_delta.get(focus, 0)
        scarcity = price_ratio >= 1.05 or inventory_delta < 0
        capacity = state.lands >= 2 and feedback.labor_pressure < 0.75 and state.day <= 22
        return {
            "eligible": bool(public_support and scarcity and capacity), "focus": focus,
            "reason": "PUBLIC_SCARCITY_WITH_CAPACITY" if public_support and scarcity and capacity else "SCARCITY_CONDITION_MISSING",
            "confidence": min(1.0, max(0.0, price_ratio - 0.9)) if public_support and capacity else 0.0,
        }

    def propose(self, state: CanonicalState, feedback: RuntimeFeedback,
                previous: DailyContract | None) -> DailyContract:
        eligibility = self.eligibility(state, feedback, previous)
        focus = str(eligibility.get("focus", self._focus(state)))
        other = "TOMATO" if focus == "CARROT" else "CARROT"
        lands = 2 if state.day < 7 else 3
        crops = {"WHEAT": 8, focus: 18 if focus == "CARROT" else 12, other: 5, "STRAWBERRY": 5}
        animals = {"COW": 2}
        hands = min(15, max(7, math.ceil((sum(crops.values()) + 4) / 3.5)))
        priority = (focus, other, "STRAWBERRY", "MILK", "FERTILIZER", "WHEAT", "MELON", "EGG", "WOOL")
        return self._contract(
            state=state, previous=previous, eligibility=eligibility,
            terminate_if={"price_ratio_below": 0.9, "inventory_recovered": True, "day_after": 24, "hard_triggered": False},
            lands=lands, hands=hands, crops=crops, animals=animals, structures={"PASTURE": 2},
            production={focus: crops[focus] * 2, other: crops[other], "MILK": 2},
            reserves={"WHEAT": 6, focus: 2}, cash_reserve=350,
            purchase_budget=max(0, min(5200, state.money - 350)), sell_priority=priority,
            sell_cap={item: (18 if item == focus else 24) for item in PRODUCTS},
            labor_priority={"WATER": 0, "HARVEST": 1, "PLANT": 2, "FEED": 2, "CARE": 7},
            deadlines={"WATER": 20, "PLANT": 20, "HARVEST": 22, "RETURN": 23},
            risk_budget={"sell_floor": 0.62, "max_labor_pressure": 0.78, "max_shed_pressure": 0.85},
            min_dwell_days=2, risk_tier="MEDIUM",
        )
