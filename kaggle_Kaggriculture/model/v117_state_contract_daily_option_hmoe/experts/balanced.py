"""均衡基础专家：广覆盖、低风险的独立完整经营合同。"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from contracts import DailyContract
from schema import BASE_PRICE, CROPS, PRODUCTS, SHOP_PRODUCTS, CanonicalState
from state_ledger import RuntimeFeedback

from .base import ExpertBase, ExpertQualification
from .cashflow_calendar import CalendarDecision, build_calendar
from .value_capacity import admit_targets


@dataclass(frozen=True)
class BalancedGenome:
    """Balanced 可搜索的低维经营参数；默认值为当前 R2.1 冻结方案。"""

    second_land_day: int = 5
    third_land_day: int = 9
    crop_blocks: tuple[tuple[tuple[str, int], ...], ...] = (
        (("WHEAT", 7), ("MELON", 8)),
        (("WHEAT", 5), ("STRAWBERRY", 11)),
        (("WHEAT", 3), ("STRAWBERRY", 14)),
    )
    demand_shift_units: int = 6
    demand_shift_products: int = 2
    scarcity_signal_enabled: bool = False
    melon_exit_day: int = 12
    melon_exit_wheat_units: int = 4
    melon_exit_strawberry_units: int = 4
    opening_melon_ramp_add: int = 0
    opening_melon_ramp_start_day: int = 1
    opening_melon_ramp_days: int = 2
    post_rotation_wheat_add: int = 0
    post_rotation_strawberry_add: int = 8
    post_rotation_ramp_days: int = 1
    sheep_initial: int = 2
    sheep_target: int = 4
    sheep_start_day: int = 1
    cow_initial: int = 0
    cow_initial_day: int = 0
    cow_target: int = 6
    cow_start_day: int = 4
    post_rotation_cow_add: int = 0
    post_rotation_cow_ramp_days: int = 1
    hands_floor: int = 4
    hands_cap: int = 12
    labor_units_per_hand: int = 4
    hands_ramp_days: int = 7
    hands_ramp_additional: int = 8
    late_hands_day: int = 10
    late_hands_cap: int = 11
    feed_units_per_animal: int = 2
    normal_cash_reserve: int = 150
    risk_cash_reserve: int = 250
    purchase_budget_cap: int = 5000
    market_shock_budget_percent: int = 90
    sell_floor: float = 0.00
    sell_cap_per_product: int = 36
    # 市场出售时点：0=需求前与需求当回合等待；1=仅需求前等待；
    # 2=不等待；3=仅需求当回合等待。默认 0 保持既有行为。
    market_demand_sell_timing_mode: int = 0
    market_impact_ordering_enabled: bool = False
    care_priority: int = 3
    water_priority: int = 0
    harvest_priority: int = 2
    wheat_prebuy_cap: int = 0
    wheat_prebuy_min_demand: int = 1
    # I4 购买依赖图。默认先关闭，由固定 Development 子面板做配对消融；
    # 通过后才允许成为下一冻结默认值。
    capital_tranches_enabled: bool = False
    capital_priority_mode: int = 0
    capital_crop_floor_percent: int = 80
    capital_seed_batch: int = 12
    capital_animal_batch: int = 2
    capital_require_animal_slots: bool = True
    future_pasture_reserve_enabled: bool = False
    # I5b 联合产能—劳动价值规划。默认关闭；只有合规 Development 配对胜出才可冻结。
    value_labor_planner_enabled: bool = False
    planner_capacity_units_per_actor: int = 5
    planner_windowed_water_enabled: bool = False
    planner_allow_fertilize: bool = False
    # I5c-2 多阶段资产—现金收据日历。默认关闭；只在合规 Development 胜出后冻结。
    cashflow_calendar_enabled: bool = True
    calendar_stage_assets_enabled: bool = False
    calendar_opening_assets_enabled: bool = True
    calendar_asset_admission_enabled: bool = False
    calendar_receipt_budget_enabled: bool = True
    calendar_terminal_replant_guard_enabled: bool = True
    calendar_terminal_buffer_days: int = 0
    calendar_melon_add: int = 0
    calendar_cow_initial: int = 2
    calendar_cow_cap: int = 10
    calendar_cow_ramp_start_day: int = 3
    calendar_cow_ramp_interval_days: int = 1
    calendar_mid_cow_add: int = 0
    calendar_mid_cow_start_day: int = 7
    calendar_mid_cow_interval_days: int = 2
    calendar_sheep_initial: int = 2
    calendar_sheep_cap: int = 4
    calendar_sheep_ramp_start_day: int = 7
    calendar_sheep_ramp_interval_days: int = 2
    calendar_low_cash_reserve: int = 20
    calendar_low_cash_reserve_until_day: int = 10
    calendar_feed_units_per_animal: int = 1
    calendar_receipt_window_days: int = 3
    calendar_receipt_haircut_percent: int = 80
    structure_admission_enabled: bool = False
    opening_structure_slots: int = 4
    structure_spare_slots: int = 1
    capacity_feedback_enabled: bool = False
    capacity_feedback_start_day: int = 2
    capacity_feedback_target_floor_percent: int = 90
    capacity_feedback_overdue_trigger: int = 4
    capacity_feedback_hands_add: int = 1
    capacity_feedback_hands_cap: int = 12

    def __post_init__(self) -> None:
        if len(self.crop_blocks) != 3:
            raise ValueError("BalancedGenome 必须有三个土地 crop block")
        if not 0 <= self.second_land_day <= self.third_land_day <= 29:
            raise ValueError("土地扩张日必须单调且位于赛季内")
        integer_fields = (
            self.demand_shift_units, self.demand_shift_products, self.sheep_initial,
            self.melon_exit_day, self.melon_exit_wheat_units, self.melon_exit_strawberry_units,
            self.opening_melon_ramp_add, self.opening_melon_ramp_start_day,
            self.opening_melon_ramp_days,
            self.post_rotation_wheat_add, self.post_rotation_strawberry_add,
            self.post_rotation_ramp_days,
            self.sheep_target, self.sheep_start_day, self.cow_target, self.cow_start_day,
            self.cow_initial, self.cow_initial_day,
            self.post_rotation_cow_add, self.post_rotation_cow_ramp_days,
            self.hands_floor, self.hands_cap, self.labor_units_per_hand,
            self.hands_ramp_days, self.hands_ramp_additional, self.feed_units_per_animal,
            self.late_hands_day, self.late_hands_cap,
            self.normal_cash_reserve, self.risk_cash_reserve, self.purchase_budget_cap,
            self.market_shock_budget_percent,
            self.sell_cap_per_product, self.market_demand_sell_timing_mode,
            self.care_priority, self.water_priority, self.harvest_priority,
            self.wheat_prebuy_cap,
            self.wheat_prebuy_min_demand, self.capital_priority_mode,
            self.capital_crop_floor_percent, self.capital_seed_batch, self.capital_animal_batch,
            self.planner_capacity_units_per_actor,
            self.calendar_melon_add, self.calendar_cow_initial, self.calendar_cow_cap,
            self.calendar_cow_ramp_start_day, self.calendar_cow_ramp_interval_days,
            self.calendar_mid_cow_add, self.calendar_mid_cow_start_day,
            self.calendar_mid_cow_interval_days,
            self.calendar_sheep_initial, self.calendar_sheep_cap,
            self.calendar_sheep_ramp_start_day, self.calendar_sheep_ramp_interval_days,
            self.calendar_low_cash_reserve, self.calendar_low_cash_reserve_until_day,
            self.calendar_feed_units_per_animal, self.calendar_receipt_window_days,
            self.calendar_receipt_haircut_percent, self.calendar_terminal_buffer_days,
            self.opening_structure_slots, self.structure_spare_slots,
            self.capacity_feedback_start_day,
            self.capacity_feedback_target_floor_percent,
            self.capacity_feedback_overdue_trigger,
            self.capacity_feedback_hands_add, self.capacity_feedback_hands_cap,
        )
        if any(int(value) < 0 for value in integer_fields):
            raise ValueError("BalancedGenome 不允许负参数")
        if self.hands_floor > self.hands_cap or self.labor_units_per_hand < 1:
            raise ValueError("劳动力参数非法")
        if not 0 <= self.late_hands_day <= 30:
            raise ValueError("后期劳动力切换日非法")
        if self.late_hands_cap > 0 and not self.hands_floor <= self.late_hands_cap <= self.hands_cap:
            raise ValueError("后期劳动力上限非法")
        if self.cow_initial > self.cow_target or self.cow_initial_day > self.cow_start_day:
            raise ValueError("奶牛两阶段目标非法")
        if not 1 <= self.post_rotation_cow_ramp_days <= 18:
            raise ValueError("轮作后奶牛爬坡天数非法")
        if not 0 <= self.melon_exit_day <= 30:
            raise ValueError("甜瓜退出日非法")
        if not 0 <= self.opening_melon_ramp_start_day <= 11:
            raise ValueError("开局甜瓜分批起始日必须位于 0..11")
        if not 1 <= self.opening_melon_ramp_days <= 10:
            raise ValueError("开局甜瓜分批天数必须位于 1..10")
        if not 1 <= self.post_rotation_ramp_days <= 18:
            raise ValueError("轮作后扩产爬坡天数非法")
        if not 0 <= self.market_shock_budget_percent <= 150:
            raise ValueError("市场冲击预算比例非法")
        if self.market_demand_sell_timing_mode not in {0, 1, 2, 3}:
            raise ValueError("市场需求出售时点模式必须为 0/1/2/3")
        if not all(
            0 <= int(priority) <= 8
            for priority in (
                self.care_priority, self.water_priority, self.harvest_priority,
            )
        ):
            raise ValueError("劳动优先级必须位于 0..8")
        if self.capital_priority_mode not in {0, 1, 2}:
            raise ValueError("资本 tranche 优先模式必须为 0/1/2")
        if not 0 <= self.capital_crop_floor_percent <= 100:
            raise ValueError("资本 tranche 作物底仓比例必须在 0..100")
        if self.capital_seed_batch < 1 or self.capital_animal_batch < 1:
            raise ValueError("资本 tranche 批量必须为正整数")
        if not 3 <= self.planner_capacity_units_per_actor <= 10:
            raise ValueError("I5b 每 actor 产能必须位于 3..10")
        if self.calendar_cow_initial > self.calendar_cow_cap:
            raise ValueError("I5c-2 奶牛初始目标不得超过上限")
        if self.calendar_sheep_initial > self.calendar_sheep_cap:
            raise ValueError("I5c-2 羊初始目标不得超过上限")
        if not 1 <= self.calendar_cow_ramp_interval_days <= 10:
            raise ValueError("I5c-2 奶牛阶段间隔非法")
        if not 1 <= self.calendar_mid_cow_interval_days <= 10:
            raise ValueError("I5c-2 第二批奶牛间隔非法")
        if not 1 <= self.calendar_sheep_ramp_interval_days <= 10:
            raise ValueError("I5c-2 羊阶段间隔非法")
        if not 0 <= self.calendar_low_cash_reserve_until_day <= 30:
            raise ValueError("I5c-2 低现金阶段边界非法")
        if not 1 <= self.calendar_feed_units_per_animal <= 4:
            raise ValueError("I5c-2 饲料储备单位非法")
        if not 1 <= self.calendar_receipt_window_days <= 10:
            raise ValueError("I5c-2 收据窗口非法")
        if not 25 <= self.calendar_receipt_haircut_percent <= 100:
            raise ValueError("I5c-2 收据折扣必须位于 25..100")
        if not 0 <= self.calendar_terminal_buffer_days <= 5:
            raise ValueError("I5c-2 终局回本缓冲非法")
        if not 0 <= self.opening_structure_slots <= 16:
            raise ValueError("首日结构槽位必须位于 0..16")
        if not 0 <= self.structure_spare_slots <= 8:
            raise ValueError("结构冗余槽位必须位于 0..8")
        if not 0 <= self.capacity_feedback_start_day <= 29:
            raise ValueError("产能反馈启用日必须位于 0..29")
        if not 50 <= self.capacity_feedback_target_floor_percent <= 100:
            raise ValueError("产能反馈兑现率阈值必须位于 50..100")
        if not 0 <= self.capacity_feedback_overdue_trigger <= 64:
            raise ValueError("产能反馈逾期阈值必须位于 0..64")
        if not 0 <= self.capacity_feedback_hands_add <= 3:
            raise ValueError("产能反馈增员必须位于 0..3")
        if not self.hands_floor <= self.capacity_feedback_hands_cap <= 15:
            raise ValueError("产能反馈雇工上限非法")
        if not 0.0 <= self.sell_floor <= 2.0:
            raise ValueError("sell_floor 超出允许范围")
        for block in self.crop_blocks:
            for crop, quantity in block:
                if crop not in CROPS or int(quantity) < 0:
                    raise ValueError(f"非法 crop block: {(crop, quantity)!r}")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "BalancedGenome":
        if not raw:
            return cls()
        payload = dict(raw)
        if "crop_blocks" in payload:
            payload["crop_blocks"] = tuple(
                tuple((str(item), int(quantity)) for item, quantity in block)
                for block in payload["crop_blocks"]
            )
        return cls(**payload)

    def stable_payload(self) -> dict[str, Any]:
        return asdict(self)


class BalancedExpert(ExpertBase):
    expert_id = "BALANCED_BASE"
    qualification = ExpertQualification(
        implemented=True,
        status="ENGINEERING_FALLBACK_FOUNDATION_NOT_QUALIFIED",
        router_enabled=True,
        evidence="R1 engineering fallback; Foundation and Gold shadow gates remain unpassed",
    )

    def __init__(self, genome: BalancedGenome | Mapping[str, Any] | None = None) -> None:
        self.genome = genome if isinstance(genome, BalancedGenome) else BalancedGenome.from_mapping(genome)

    def eligibility(self, state: CanonicalState, feedback: RuntimeFeedback,
                    previous: DailyContract | None) -> Mapping[str, Any]:
        return {"eligible": True, "reason": "DEFAULT_FALLBACK", "confidence": 1.0}

    def _targets(self, state: CanonicalState) -> tuple[int, dict[str, int]]:
        genome = self.genome
        lands = 1 + int(state.day >= genome.second_land_day) + int(state.day >= genome.third_land_day)
        crops: Counter[str] = Counter()
        for block in genome.crop_blocks[:lands]:
            crops.update(dict(block))
        if (state.day < genome.melon_exit_day
                and state.day >= genome.opening_melon_ramp_start_day
                and genome.opening_melon_ramp_add > 0):
            ramp = min(
                genome.opening_melon_ramp_days,
                state.day - genome.opening_melon_ramp_start_day + 1,
            )
            crops["MELON"] += (
                genome.opening_melon_ramp_add * ramp
                // genome.opening_melon_ramp_days
            )
        if state.day >= genome.melon_exit_day and crops["MELON"] > 0:
            shift = min(
                crops["MELON"],
                genome.melon_exit_wheat_units + genome.melon_exit_strawberry_units,
            )
            to_wheat = min(shift, genome.melon_exit_wheat_units)
            crops["MELON"] -= shift
            crops["WHEAT"] += to_wheat
            crops["STRAWBERRY"] += shift - to_wheat
            ramp_numerator = min(
                genome.post_rotation_ramp_days,
                state.day - genome.melon_exit_day + 1,
            )
            crops["WHEAT"] += (
                genome.post_rotation_wheat_add * ramp_numerator // genome.post_rotation_ramp_days
            )
            crops["STRAWBERRY"] += (
                genome.post_rotation_strawberry_add * ramp_numerator // genome.post_rotation_ramp_days
            )
        public_demand: Counter[str] = Counter()
        for shop in state.shops:
            for item in SHOP_PRODUCTS.get(shop, ()):
                if item in CROPS:
                    public_demand[item] += 2 if len(SHOP_PRODUCTS.get(shop, ())) == 1 else 1
        if genome.scarcity_signal_enabled:
            demand_order = sorted(
                (crop for crop in CROPS if public_demand[crop] > 0),
                key=lambda crop: (
                    -(
                        4.0 * public_demand[crop]
                        + 2.0 * state.prices.get(crop, BASE_PRICE[crop]) / BASE_PRICE[crop]
                        + max(-5.0, min(
                            5.0,
                            (10000 - state.market_inventory.get(crop, 10000)) / 250.0,
                        ))
                        - 0.15 * int(state.opponent.crops.get(crop, 0))
                    ),
                    CROPS.index(crop),
                ),
            )
        else:
            demand_order = [crop for crop, _ in public_demand.most_common()]
        for target in demand_order[:genome.demand_shift_products]:
            donor = max((item for item in CROPS if item != target), key=lambda item: crops[item])
            if crops[donor] > (5 if donor == "WHEAT" else 2):
                shift = min(genome.demand_shift_units, crops[donor])
                crops[donor] -= shift
                crops[target] += shift
        return lands, dict(crops)

    def propose(self, state: CanonicalState, feedback: RuntimeFeedback,
                previous: DailyContract | None) -> DailyContract:
        genome = self.genome
        lands, crops = self._targets(state)
        animals = {
            "SHEEP": genome.sheep_target if state.day >= genome.sheep_start_day else genome.sheep_initial,
            "COW": (
                genome.cow_target if state.day >= genome.cow_start_day
                else genome.cow_initial if state.day >= genome.cow_initial_day else 0
            ),
        }
        if state.day >= genome.melon_exit_day:
            cow_ramp = min(
                genome.post_rotation_cow_ramp_days,
                state.day - genome.melon_exit_day + 1,
            )
            animals["COW"] += (
                genome.post_rotation_cow_add * cow_ramp // genome.post_rotation_cow_ramp_days
            )
        animals = {key: value for key, value in animals.items() if value > 0}
        active = sum(crops.values()) + 2 * sum(animals.values())
        ramp = genome.hands_floor + genome.hands_ramp_additional * min(
            state.day, max(1, genome.hands_ramp_days),
        ) // max(1, genome.hands_ramp_days)
        hands = min(
            genome.hands_cap,
            max(genome.hands_floor, math.ceil(active / genome.labor_units_per_hand)),
            ramp,
        )
        if genome.late_hands_cap > 0 and state.day >= genome.late_hands_day:
            hands = min(hands, genome.late_hands_cap)
        calendar: CalendarDecision | None = None
        if genome.cashflow_calendar_enabled:
            calendar = build_calendar(
                state, lands, crops, animals, hands,
                stage_assets_enabled=genome.calendar_stage_assets_enabled,
                opening_assets_enabled=genome.calendar_opening_assets_enabled,
                asset_admission_enabled=genome.calendar_asset_admission_enabled,
                receipt_budget_enabled=genome.calendar_receipt_budget_enabled,
                terminal_replant_guard_enabled=genome.calendar_terminal_replant_guard_enabled,
                terminal_buffer_days=genome.calendar_terminal_buffer_days,
                melon_add=genome.calendar_melon_add,
                melon_exit_day=genome.melon_exit_day,
                cow_initial=genome.calendar_cow_initial,
                cow_cap=genome.calendar_cow_cap,
                cow_ramp_start_day=genome.calendar_cow_ramp_start_day,
                cow_ramp_interval_days=genome.calendar_cow_ramp_interval_days,
                mid_cow_add=genome.calendar_mid_cow_add,
                mid_cow_start_day=genome.calendar_mid_cow_start_day,
                mid_cow_interval_days=genome.calendar_mid_cow_interval_days,
                sheep_initial=genome.calendar_sheep_initial,
                sheep_cap=genome.calendar_sheep_cap,
                sheep_ramp_start_day=genome.calendar_sheep_ramp_start_day,
                sheep_ramp_interval_days=genome.calendar_sheep_ramp_interval_days,
                low_cash_reserve=genome.calendar_low_cash_reserve,
                low_cash_reserve_until_day=genome.calendar_low_cash_reserve_until_day,
                normal_cash_reserve=genome.normal_cash_reserve,
                feed_units_per_animal=genome.calendar_feed_units_per_animal,
                receipt_window_days=genome.calendar_receipt_window_days,
                receipt_haircut_percent=genome.calendar_receipt_haircut_percent,
                purchase_budget_cap=genome.purchase_budget_cap,
            )
            lands = calendar.lands
            crops = dict(calendar.crops)
            animals = dict(calendar.animals)
            hands = calendar.hands
        capacity_feedback_triggered = bool(
            genome.capacity_feedback_enabled
            and state.day >= genome.capacity_feedback_start_day
            and feedback.previous_day_target_realization
            < genome.capacity_feedback_target_floor_percent / 100.0
            and feedback.previous_day_overdue_tasks
            >= genome.capacity_feedback_overdue_trigger
        )
        if capacity_feedback_triggered:
            hands = min(
                genome.capacity_feedback_hands_cap,
                hands + genome.capacity_feedback_hands_add,
            )
        planner = None
        if genome.value_labor_planner_enabled:
            planner = admit_targets(
                state, crops, animals, hands, genome.planner_capacity_units_per_actor,
            )
            crops = dict(planner.crops)
            animals = dict(planner.animals)
        demand_rank = Counter()
        for shop in state.shops:
            demand_rank.update(SHOP_PRODUCTS.get(shop, ()))
        sell_priority = tuple(sorted(PRODUCTS, key=lambda item: (
            -demand_rank[item], -state.prices.get(item, BASE_PRICE[item]), PRODUCTS.index(item)
        )))
        reserve = (
            calendar.cash_reserve if calendar is not None
            else genome.risk_cash_reserve if feedback.cash_risk > 0
            else genome.normal_cash_reserve
        )
        pasture_target = sum(animals.values())
        if genome.structure_admission_enabled:
            installed_animals = sum(
                max(0, int(state.animals.get(animal, 0)))
                for animal in ("SHEEP", "COW")
            )
            pending_animals = sum(
                max(0, int(state.shed.get(animal, 0)))
                + sum(
                    max(0, int(inventory.get(animal, 0)))
                    for inventory in state.inventories
                )
                for animal in ("SHEEP", "COW")
            )
            spare = (
                genome.opening_structure_slots
                if state.day == 0 else genome.structure_spare_slots
            )
            pasture_target = min(
                pasture_target,
                installed_animals + pending_animals + spare,
            )
        if genome.future_pasture_reserve_enabled:
            pasture_target = max(
                pasture_target,
                genome.sheep_target + genome.cow_target + genome.post_rotation_cow_add,
            )
        return self._contract(
            state=state, previous=previous, eligibility=self.eligibility(state, feedback, previous),
            terminate_if={"cash_below": 120, "feed_risk_above": 0.8, "hard_triggered": False},
            lands=lands, hands=hands, crops=crops, animals=animals,
            structures={"PASTURE": pasture_target},
            production={"WHEAT": max(8, 2 * sum(animals.values())), "MILK": animals.get("COW", 0),
                        "WOOL": animals.get("SHEEP", 0)},
            reserves={
                "WHEAT": (
                    calendar.feed_units_per_animal if calendar is not None
                    else genome.feed_units_per_animal
                ) * sum(animals.values()),
                "FERTILIZER": 0,
            },
            cash_reserve=reserve,
            purchase_budget=(
                calendar.purchase_budget if calendar is not None
                else max(0, min(genome.purchase_budget_cap, state.money - reserve))
            ),
            sell_priority=sell_priority,
            sell_cap={item: genome.sell_cap_per_product for item in PRODUCTS},
            labor_priority=(
                {"WATER": 3, "FEED": 0, "HARVEST": 0, "PLANT": 4, "CARE": 1}
                if genome.value_labor_planner_enabled else
                {"WATER": genome.water_priority, "FEED": 0,
                 "HARVEST": genome.harvest_priority, "PLANT": 3,
                 "CARE": genome.care_priority}
            ),
            deadlines={"WATER": 22, "FEED": 20, "PLANT": 22, "RETURN": 23},
            risk_budget={"sell_floor": genome.sell_floor, "max_labor_pressure": 0.95,
                         "max_shed_pressure": 0.9,
                         "market_shock_budget_factor": genome.market_shock_budget_percent / 100.0,
                         "market_demand_sell_timing_mode": float(
                             genome.market_demand_sell_timing_mode
                         ),
                         "market_impact_ordering_enabled": float(
                             genome.market_impact_ordering_enabled
                         ),
                         "wheat_prebuy_cap": float(genome.wheat_prebuy_cap),
                         "wheat_prebuy_min_demand": float(genome.wheat_prebuy_min_demand),
                         "capital_tranches_enabled": float(genome.capital_tranches_enabled),
                         "capital_priority_mode": float(genome.capital_priority_mode),
                         "capital_crop_floor_percent": float(genome.capital_crop_floor_percent),
                         "capital_seed_batch": float(genome.capital_seed_batch),
                         "capital_animal_batch": float(genome.capital_animal_batch),
                         "capital_require_animal_slots": float(genome.capital_require_animal_slots),
                         "value_labor_planner_enabled": float(genome.value_labor_planner_enabled),
                         "planner_windowed_water_enabled": float(genome.planner_windowed_water_enabled),
                         "planner_allow_fertilize": float(genome.planner_allow_fertilize),
                         "planner_capacity_units": float(planner.capacity_units if planner else 0),
                         "planner_requested_work": float(planner.requested_work if planner else 0),
                         "planner_admitted_work": float(planner.admitted_work if planner else 0),
                         "planner_rejected_units": float(planner.rejected_units if planner else 0),
                         "cashflow_calendar_enabled": float(genome.cashflow_calendar_enabled),
                         "calendar_stage_assets_enabled": float(genome.calendar_stage_assets_enabled),
                         "calendar_opening_assets_enabled": float(
                             genome.calendar_opening_assets_enabled
                         ),
                         "calendar_asset_admission_enabled": float(
                             genome.calendar_asset_admission_enabled
                         ),
                         "calendar_receipt_budget_enabled": float(
                             genome.calendar_receipt_budget_enabled
                         ),
                         "calendar_terminal_replant_guard_enabled": float(
                             genome.calendar_terminal_replant_guard_enabled
                         ),
                         "calendar_projected_receipts": float(calendar.projected_receipts if calendar else 0),
                         "calendar_liquidatable_value": float(calendar.liquidatable_value if calendar else 0),
                         "calendar_upfront_commitment": float(calendar.upfront_commitment if calendar else 0),
                         "calendar_operating_commitment": float(calendar.operating_commitment if calendar else 0),
                         "calendar_first_receipt_day": float(calendar.first_receipt_day if calendar else 30),
                         "calendar_admitted_units": float(calendar.admitted_units if calendar else 0),
                         "calendar_rejected_units": float(calendar.rejected_units if calendar else 0),
                         "calendar_minimum_projected_cash": float(
                            calendar.minimum_projected_cash if calendar else 0
                         ),
                         "capacity_feedback_enabled": float(
                             genome.capacity_feedback_enabled
                         ),
                         "capacity_feedback_triggered": float(
                             capacity_feedback_triggered
                         ),
                         "capacity_feedback_previous_realization": float(
                             feedback.previous_day_target_realization
                         ),
                         "capacity_feedback_previous_overdue": float(
                             feedback.previous_day_overdue_tasks
                         ),
                         "capacity_feedback_miss_streak": float(
                             feedback.capacity_miss_streak
                         )},
            min_dwell_days=2, risk_tier="LOW",
        )
