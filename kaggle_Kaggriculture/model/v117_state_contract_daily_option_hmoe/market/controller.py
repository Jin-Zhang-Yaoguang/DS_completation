"""M0-M3：确定性账本、现金闭环、需求/价格响应和公开对手冲击。"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from contracts import DailyContract
from schema import (ANIMAL_COST, ANIMALS, BASE_PRICE, CROPS, LAND_PRICES, PRODUCTS,
                    SEED_COST, SHED_CAPACITY, SHOP_PRODUCTS, CanonicalState, farm_counts,
                    fib, integer, inventory_total)
from state_ledger import RuntimeFeedback


# 1.32.7 公共市场曲线；来自同版本规则配置，不含 Replay 或对手私有信息。
MARKET_PARAMS = {
    "WHEAT": (25, 10000, 400, "sqrt", 0.8, "log", 0.2),
    "CARROT": (35, 10000, 450, "hinge", 1.0, "sqrt", 0.7),
    "TOMATO": (60, 10000, 200, "hinge", 0.4, "sqrt", 0.6),
    "STRAWBERRY": (120, 10000, 100, "sqrt", 0.7, "linear", 1.6),
    "MELON": (250, 10000, 300, "log", 0.2, "sq", 3.6),
    "EGG": (50, 10000, 332, "hinge", 0.4, "log", 0.2),
    "MILK": (160, 10000, 122, "sqrt", 0.6, "linear", 1.6),
    "WOOL": (200, 10000, 105, "log", 0.2, "sq", 3.2),
    "FERTILIZER": (100, 10000, 200, "linear", 0.4, "linear", 0.4),
}


@dataclass(frozen=True)
class MarketResult:
    orders: tuple[tuple[Any, ...], ...]
    projected_cash: int
    projected_shed_used: int
    cash_recovery: bool
    budget_spent: int
    diagnostics: Mapping[str, Any]


class MarketController:
    def __init__(self, enable_opponent_conditioning: bool = False) -> None:
        self.audit: Counter[str] = Counter()
        self.enable_opponent_conditioning = bool(enable_opponent_conditioning)

    @staticmethod
    def _project_shed(state: CanonicalState, verbs: Sequence[Sequence[Any]]) -> dict[str, int]:
        projected = dict(state.shed)
        total = sum(projected.values())
        for actor, verb in enumerate(verbs):
            if not verb:
                continue
            if verb[0] == "DROP":
                for item, quantity in state.inventories[actor].items():
                    take = min(max(0, int(quantity)), max(0, SHED_CAPACITY - total))
                    projected[item] = projected.get(item, 0) + take
                    total += take
            elif verb[0] == "PICKUP" and len(verb) >= 3:
                item = str(verb[1])
                projected[item] = max(0, projected.get(item, 0) - integer(verb[2]))
            elif verb[0] == "PLACE" and len(verb) >= 2:
                item = str(verb[1])
                projected[item] = max(0, projected.get(item, 0) - 1)
        return projected

    @staticmethod
    def _demand_window(state: CanonicalState) -> tuple[Counter[str], int]:
        demand: Counter[str] = Counter()
        until_shop = (4 - state.step % 4) % 4
        for shop in state.shops:
            goods = SHOP_PRODUCTS.get(shop, ())
            for item in goods:
                demand[item] += 2 if len(goods) == 1 else 1
        if (24 - state.step % 24) % 24 <= until_shop:
            for item in PRODUCTS:
                if item != "FERTILIZER":
                    demand[item] += 1
        return demand, until_shop

    @staticmethod
    def _sell_unit_price(state: CanonicalState, item: str, already: int) -> int:
        # 只作保守的当回合预算预演；真实 observation 在下一 turn 覆盖预测。
        observed = state.prices.get(item, BASE_PRICE[item])
        inventory = state.market_inventory.get(item, 10000) + already
        impact = already // max(1, 4 + abs(inventory - 10000) // 500)
        return max(1, observed - impact)

    @staticmethod
    def _shape(name: str, value: float, scale: float) -> float:
        value = max(0.0, float(value))
        if name == "linear":
            return value
        if name == "sq":
            return value * value
        if name == "sqrt":
            return math.sqrt(value)
        if name == "log":
            return math.log1p(value)
        if name == "hinge":
            normalized = value / max(1.0, scale)
            return normalized + 8.0 * max(0.0, normalized - 1.0) ** 2
        raise ValueError(f"未知市场曲线: {name}")

    @classmethod
    def _exact_market_price(cls, item: str, inventory: int) -> int:
        base, equilibrium, scale, below_shape, below_target, above_shape, above_target = (
            MARKET_PARAMS[item]
        )
        if inventory < equilibrium:
            amplitude = below_target * base / cls._shape(below_shape, scale, scale)
            raw = base + amplitude * cls._shape(
                below_shape, equilibrium - inventory, scale,
            )
        else:
            amplitude = above_target * base / cls._shape(above_shape, scale, scale)
            raw = base - amplitude * cls._shape(
                above_shape, inventory - equilibrium, scale,
            )
        return max(1, int(round(raw)))

    @classmethod
    def _sell_impact_score(cls, state: CanonicalState, item: str, quantity: int) -> int:
        """若同量竞争销售先成交，本订单损失的精确公开曲线收入。"""

        start = int(state.market_inventory.get(item, 10000))

        def sell_revenue(inventory: int) -> tuple[int, int]:
            revenue = 0
            for _ in range(max(0, int(quantity))):
                price = cls._exact_market_price(item, inventory)
                revenue += price
                if price > 1:
                    inventory += 1
            return revenue, inventory

        revenue_now, _ = sell_revenue(start)
        _, delayed_inventory = sell_revenue(start)
        revenue_after, _ = sell_revenue(delayed_inventory)
        return max(0, revenue_now - revenue_after)

    @staticmethod
    def _wait_for_demand(timing_mode: int, until_demand: int) -> bool:
        """只编码当前/下一次确定性需求时点，不读取未来 Replay 轨迹。"""
        if timing_mode == 0:
            return until_demand <= 1
        if timing_mode == 1:
            return until_demand == 1
        if timing_mode == 2:
            return False
        if timing_mode == 3:
            return until_demand == 0
        raise ValueError(f"非法市场需求出售时点模式: {timing_mode}")

    @staticmethod
    def _purchase_candidates(state: CanonicalState, contract: DailyContract,
                             projected: Mapping[str, int], carried: Counter[str],
                             pending_plants: Mapping[str, int], feedback: RuntimeFeedback,
                             demand: Counter[str], until_demand: int) \
            -> tuple[list[tuple[int, list[Any], int]], str]:
        crops, animals, structures = farm_counts(state.grid)
        candidates: list[tuple[int, list[Any], int]] = []
        tranche_enabled = bool(contract.risk_budget.get("capital_tranches_enabled", 0.0))
        priority_mode = int(contract.risk_budget.get("capital_priority_mode", 0.0))
        crop_floor = max(0, min(100, int(contract.risk_budget.get("capital_crop_floor_percent", 80.0))))
        seed_batch = max(1, int(contract.risk_budget.get("capital_seed_batch", 12.0)))
        animal_batch = max(1, int(contract.risk_budget.get("capital_animal_batch", 2.0)))
        require_slots = bool(contract.risk_budget.get("capital_require_animal_slots", 1.0))
        feed_gap = max(0, contract.feed_reserve - projected.get("WHEAT", 0) - carried["WHEAT"])
        if feed_gap:
            candidates.append((100, ["BUY_PRODUCT", "WHEAT", min(18, feed_gap)],
                               state.prices.get("WHEAT", BASE_PRICE["WHEAT"])))
        for offset in range(max(0, contract.hands - (len(state.positions) - 1))):
            candidates.append((92, ["HIRE"], fib(state.hires_today + offset)))
        pasture_claimed = (
            animals["SHEEP"] + animals["COW"]
            + projected.get("SHEEP", 0) + projected.get("COW", 0)
            + carried["SHEEP"] + carried["COW"]
        )
        coop_claimed = animals["GOOSE"] + projected.get("GOOSE", 0) + carried["GOOSE"]
        slot_room = {
            "PASTURE": max(0, structures["PASTURE"] - pasture_claimed),
            "COOP": max(0, structures["COOP"] - coop_claimed),
        }
        for animal in ANIMALS:
            have = animals[animal] + projected.get(animal, 0) + carried[animal]
            gap = max(0, contract.animals.get(animal, 0) - have)
            if gap:
                quantity = gap
                if tranche_enabled:
                    quantity = min(quantity, animal_batch)
                    if require_slots:
                        structure = "COOP" if animal == "GOOSE" else "PASTURE"
                        quantity = min(quantity, slot_room[structure])
                        slot_room[structure] -= quantity
                if quantity > 0:
                    candidates.append((86, ["BUY_ANIMAL", animal, quantity], ANIMAL_COST[animal]))
        gaps = {crop: max(0, contract.crops.get(crop, 0) - crops[crop] - state.seeds.get(crop, 0)
                               - int(pending_plants.get(crop, 0))) for crop in CROPS}
        for crop in sorted(CROPS, key=lambda item: (-(gaps[item] / max(1, contract.crops.get(item, 0))), CROPS.index(item))):
            if gaps[crop]:
                candidates.append((80, ["BUY_SEED", crop, min(seed_batch, gaps[crop])], SEED_COST[crop]))
        if state.lands < contract.lands and state.day <= 18 and feedback.labor_pressure <= contract.risk_budget.get("max_labor_pressure", 1.0):
            # 土地是后续动物/作物目标的容量前置条件。排在饲料与当日雇工之后、
            # 新增动物和种子之前，避免目标缺口长期抽干现金而永远无法扩地。
            candidates.append((90, ["BUY_LAND"], LAND_PRICES[max(0, state.lands - 1)]))
        prebuy_cap = max(0, int(contract.risk_budget.get("wheat_prebuy_cap", 0)))
        prebuy_min_demand = max(1, int(contract.risk_budget.get("wheat_prebuy_min_demand", 1)))
        # 公开需求周期在本回合市场撮合后发生。这里只利用当前已解锁商店可推导的
        # 当回合小麦需求，在消费前建立不超过 cap 的短仓位；下一回合由正常销售逻辑退出。
        # 不读取未来商店、Replay 动作或对手私有状态。
        if prebuy_cap > 0 and until_demand == 0 and demand["WHEAT"] >= prebuy_min_demand:
            candidates.append((70, ["BUY_PRODUCT", "WHEAT", prebuy_cap],
                               state.prices.get("WHEAT", BASE_PRICE["WHEAT"])))
        stage = "PARALLEL"
        if tranche_enabled:
            operating = [row for row in candidates if row[1][0] in {"BUY_PRODUCT", "HIRE"}]
            land = [row for row in candidates if row[1][0] == "BUY_LAND"]
            seeds = [row for row in candidates if row[1][0] == "BUY_SEED"]
            livestock = [row for row in candidates if row[1][0] == "BUY_ANIMAL"]
            target_crops = sum(max(0, int(value)) for value in contract.crops.values())
            established_crops = sum(
                int(crops[crop]) + int(state.seeds.get(crop, 0)) + int(pending_plants.get(crop, 0))
                for crop in CROPS
            )
            crop_floor_met = established_crops * 100 >= target_crops * crop_floor
            if land:
                capital, stage = land, "LAND"
            elif priority_mode == 0 and seeds and not crop_floor_met:
                capital, stage = seeds, "SEED_FLOOR"
            elif priority_mode == 0 and livestock:
                capital, stage = livestock, "ANIMAL"
            elif priority_mode == 0 and seeds:
                capital, stage = seeds, "SEED_REPLENISH"
            elif priority_mode == 1 and livestock:
                capital, stage = livestock, "ANIMAL"
            elif priority_mode == 2:
                capital = [*livestock, *seeds]
                stage = "ANIMAL_AND_SEED" if capital else "STEADY"
            elif livestock:
                capital, stage = livestock, "ANIMAL"
            elif seeds:
                capital, stage = seeds, "SEED"
            else:
                capital, stage = [], "STEADY"
            candidates = [*operating, *capital]
        return sorted(candidates, key=lambda row: (-row[0], row[1])), stage

    def act(self, state: CanonicalState, contract: DailyContract, feedback: RuntimeFeedback,
            unit_actions: Sequence[Sequence[Any]], pending_plants: Mapping[str, int],
            force_recovery: bool = False, terminal: bool = False) -> MarketResult:
        projected = self._project_shed(state, unit_actions)
        carried = inventory_total(state.inventories)
        total = sum(projected.values())
        money = state.money
        demand, until_demand = self._demand_window(state)
        candidates, purchase_stage = ([], "TERMINAL") if terminal else self._purchase_candidates(
            state, contract, projected, carried, pending_plants, feedback, demand, until_demand
        )
        self.audit[f"purchase_stage_{purchase_stage.lower()}"] += 1
        desired_purchase_value = sum(
            unit_cost * (integer(raw[2], 1) if len(raw) >= 3 else 1)
            for _, raw, unit_cost in candidates
        )
        affordable_budget = min(contract.purchase_budget, max(0, money - contract.cash_reserve))
        if self.enable_opponent_conditioning and feedback.opponent_pressure > 0.5:
            affordable_budget = int(affordable_budget * 0.8)
            self.audit["opponent_risk_throttle"] += 1
        if feedback.market_shock > 0.25:
            affordable_budget = int(affordable_budget * float(
                contract.risk_budget.get("market_shock_budget_factor", 0.9)
            ))
            self.audit["market_shock_throttle"] += 1
        planned_cost = 0
        for _, raw, unit_cost in candidates:
            quantity = integer(raw[2], 1) if len(raw) >= 3 else 1
            planned_cost += unit_cost * quantity
            if planned_cost >= affordable_budget:
                break
        finance_gap = max(0, min(planned_cost, contract.purchase_budget) + contract.cash_reserve - money)
        if force_recovery:
            finance_gap = max(finance_gap, contract.cash_reserve - money)

        saleable = {item: max(0, projected.get(item, 0)
                              - (contract.inventory_reserves.get(item, 0) if not terminal else 0))
                    for item in PRODUCTS}
        sell: Counter[str] = Counter()
        ranked = list(contract.sell_priority) or list(PRODUCTS)
        ranked = sorted(ranked, key=lambda item: (
            -int(item in demand), -state.prices.get(item, BASE_PRICE[item]), ranked.index(item)
        ))
        for item in ranked:
            cap = min(saleable[item], int(contract.sell_cap.get(item, 24)))
            while finance_gap > 0 and sell[item] < cap:
                sell[item] += 1
                finance_gap -= self._sell_unit_price(state, item, sell[item] - 1)
        pressure = total >= int(SHED_CAPACITY * contract.risk_budget.get("max_shed_pressure", 0.9))
        timing_mode = int(contract.risk_budget.get("market_demand_sell_timing_mode", 0.0))
        for item in ranked:
            remaining = min(saleable[item] - sell[item], int(contract.sell_cap.get(item, 24)) - sell[item])
            if remaining <= 0:
                continue
            price = state.prices.get(item, BASE_PRICE[item])
            supported = price >= BASE_PRICE[item] * contract.sell_floor
            wait_for_demand = (
                demand[item] > 0
                and self._wait_for_demand(timing_mode, until_demand)
                and not terminal
                and not pressure
            )
            if terminal or pressure or force_recovery or (supported and not wait_for_demand):
                sell[item] += remaining if terminal else min(remaining, 24)

        high_price_unsold = {
            item: max(0, int(saleable[item]) - int(sell[item]))
            for item in PRODUCTS
            if (max(0, int(saleable[item]) - int(sell[item])) > 0
                and state.prices.get(item, BASE_PRICE[item]) >= BASE_PRICE[item] * contract.sell_floor)
        }

        orders: list[tuple[Any, ...]] = []
        order_rank = ranked
        if bool(contract.risk_budget.get("market_impact_ordering_enabled", 0.0)):
            original_rank = {item: index for index, item in enumerate(ranked)}
            order_rank = sorted(ranked, key=lambda item: (
                -self._sell_impact_score(state, item, sell[item]),
                original_rank[item],
            ))
            self.audit["market_impact_ordering_turns"] += 1
        for item in order_rank:
            quantity = sell[item]
            if quantity <= 0 or len(orders) >= 10:
                continue
            orders.append(("SELL", item, quantity))
            revenue = sum(self._sell_unit_price(state, item, offset) for offset in range(quantity))
            money += revenue
            total -= quantity
            self.audit["units_sold"] += quantity

        cash_after_sales = int(money)
        spent = 0
        for _, raw, unit_cost in candidates:
            if len(orders) >= 10 or spent >= affordable_budget:
                break
            requested = integer(raw[2], 1) if len(raw) >= 3 else 1
            max_cash = max(0, min(money - contract.cash_reserve, affordable_budget - spent))
            if raw[0] in {"BUY_PRODUCT", "BUY_ANIMAL"}:
                quantity = min(requested, max_cash // max(1, unit_cost), max(0, SHED_CAPACITY - total))
            elif raw[0] == "BUY_SEED":
                quantity = min(requested, max_cash // max(1, unit_cost))
            else:
                quantity = int(max_cash >= unit_cost)
            if quantity <= 0:
                self.audit["purchase_withheld"] += 1
                continue
            order = tuple(raw) if len(raw) < 3 else (raw[0], raw[1], int(quantity))
            orders.append(order)
            cost = unit_cost * quantity
            money -= cost
            spent += cost
            if raw[0] in {"BUY_PRODUCT", "BUY_ANIMAL"}:
                total += quantity
            self.audit["units_purchased"] += quantity
        self.audit["orders"] += len(orders)
        self.audit["cash_recovery"] += int(force_recovery)
        cash_shortfall = max(
            0,
            min(int(desired_purchase_value), int(contract.purchase_budget))
            + int(contract.cash_reserve) - cash_after_sales,
        )
        budget_shortfall = max(0, int(desired_purchase_value) - int(contract.purchase_budget))
        executable_after_sales = min(
            int(contract.purchase_budget), max(0, cash_after_sales - int(contract.cash_reserve)),
        )
        purchase_execution_shortfall = max(
            0, min(int(desired_purchase_value), executable_after_sales) - int(spent),
        )
        diagnostics = {
            "purchase_stage": purchase_stage,
            "capital_tranches_enabled": bool(contract.risk_budget.get("capital_tranches_enabled", 0.0)),
            "desired_purchase_value": int(desired_purchase_value),
            "cash_shortfall_value": int(cash_shortfall),
            "contract_budget_shortfall_value": int(budget_shortfall),
            "purchase_execution_shortfall_value": int(purchase_execution_shortfall),
            # 正式“融资不足”只计算现金缺口；主动合同预算和执行短缺另列诊断，不能冒充缺钱。
            "financing_shortfall_value": int(cash_shortfall),
            "high_price_unsold": dict(high_price_unsold),
        }
        return MarketResult(
            tuple(orders[:10]), int(money), int(total), bool(force_recovery), int(spent), diagnostics,
        )
