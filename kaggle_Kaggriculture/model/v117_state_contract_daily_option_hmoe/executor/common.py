"""E1/E2：sticky role、standing-on-work、任务批处理和全局最小成本匹配。"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from contracts import DailyContract
from schema import (ANIMALS, BASE_PRICE, CROP_FACTS, CROPS, PASS, PRODUCTS, SHED_CAPACITY, SHED_TILES,
                    CanonicalState, animal_kind, distance, farm_counts, inventory_total, integer,
                    quadrant, path_toward, shed_gate)
from state_ledger import RuntimeFeedback


LABOR_STEP_VALUE = 25.0


@dataclass(frozen=True)
class ExecutorTuning:
    """只控制任务分配代价，不改变专家目标、市场或安全逻辑。"""

    travel_weight: float = 4.0
    priority_weight: float = 100.0
    standing_bonus: float = 60.0
    sticky_bonus: float = 150.0
    role_penalty: float = 300.0
    deadline_penalty: float = 1200.0
    candidate_cap: int = 64
    stratified_candidate_pool_enabled: bool = False
    rolling_route_enabled: bool = False
    rolling_route_horizon: int = 4
    rolling_route_replan_interval: int = 4
    rolling_route_priority_slack: int = 0
    rolling_route_load_weight: float = 20.0
    transition_aware_route_enabled: bool = False
    rolling_route_delivery_weight: float = 0.02
    delivery_value_threshold: int = 1500
    opening_delivery_value_threshold: int = 0
    opening_delivery_start_day: int = 0
    opening_delivery_until_day: int = 0
    delivery_cash_ceiling: int = 10000
    delivery_max_distance: int = 20
    delivery_runner_cap: int = 2
    persistent_delivery_runner_enabled: bool = False
    delivery_cutoff_hour: int = 18
    fertilize_priority: int = 1
    fertilize_daily_cap: int = 64
    fertilize_start_day: int = 0
    fertilize_windowed: bool = False
    fertilize_before_water_enabled: bool = False
    fertilize_crops: tuple[str, ...] = ("TOMATO", "STRAWBERRY", "MELON")
    collect_fertilizer_priority: int = 2
    animal_harvest_priority: int = -1
    persistent_lock_enabled: bool = False
    persistent_lock_max_priority: int = 6
    persistent_preempt_priority: int = 0
    persistent_lock_radius: int = 20
    inflight_task_lock_enabled: bool = False
    inflight_task_preempt_priority: int = 0
    dynamic_role_enabled: bool = False
    dynamic_role_stability_penalty: int = 2
    capacity_admission_enabled: bool = False
    plant_cutoff_hour: int = 22
    plant_admission_cap: int = 64
    multi_feed_runner_enabled: bool = True
    feed_units_per_runner: int = 4
    feed_runner_cap: int = 4
    multi_animal_runner_enabled: bool = False
    animal_units_per_runner: int = 1
    animal_runner_cap: int = 1
    terminal_harvest_only_enabled: bool = True
    terminal_return_buffer: int = 2
    terminal_hire_cap: int = 8
    terminal_local_route_enabled: bool = False
    animal_zoning_enabled: bool = False
    crop_zoning_enabled: bool = False
    surplus_crop_retirement_enabled: bool = False
    surplus_crop_retirement_start_day: int = 12
    surplus_crop_retirement_priority: int = 1
    windowed_water_enabled: bool = True
    windowed_water_start_day: int = 10
    staggered_windowed_water_enabled: bool = False
    local_route_queue_enabled: bool = False
    local_route_priority_slack: int = 1
    local_route_spill_enabled: bool = True
    animal_service_session_enabled: bool = False
    animal_service_max_steps: int = 4
    animal_service_preempt_priority: int = -1
    work_conserving_second_pass_enabled: bool = False
    work_conserving_max_priority: int = 3
    work_conserving_max_distance: int = 8
    stable_tile_owner_enabled: bool = False
    stable_tile_owner_penalty: int = 50
    deadline_slack_weight: float = 0.0
    cow_care_deadline_enabled: bool = True
    cow_care_deadline_hour: int = 22
    cow_care_deadline_priority: int = 1
    fertilizer_collection_deadline_enabled: bool = False
    fertilizer_collection_deadline_hour: int = 22
    fertilizer_collection_deadline_priority: int = 1
    strawberry_fertilizer_first_enabled: bool = True
    strawberry_fertilizer_first_start_day: int = 12

    def __post_init__(self) -> None:
        values = (
            self.travel_weight, self.priority_weight, self.standing_bonus, self.sticky_bonus,
            self.role_penalty, self.deadline_penalty,
            self.rolling_route_load_weight, self.rolling_route_delivery_weight,
        )
        if any(float(value) < 0 for value in values):
            raise ValueError("ExecutorTuning 不允许负代价参数")
        if not 8 <= int(self.candidate_cap) <= 256:
            raise ValueError("candidate_cap 必须位于 8..256")
        if not 1 <= int(self.rolling_route_horizon) <= 12:
            raise ValueError("滚动路线 horizon 必须位于 1..12")
        if not 1 <= int(self.rolling_route_replan_interval) <= 12:
            raise ValueError("滚动路线重规划间隔必须位于 1..12")
        if not 0 <= int(self.rolling_route_priority_slack) <= 4:
            raise ValueError("滚动路线优先级 slack 必须位于 0..4")
        if (int(self.delivery_value_threshold) < 0
                or int(self.opening_delivery_value_threshold) < 0
                or int(self.delivery_cash_ceiling) < 0):
            raise ValueError("交付阈值不允许为负")
        if not 0 <= int(self.opening_delivery_start_day) <= int(self.opening_delivery_until_day) <= 29:
            raise ValueError("阶段交付窗口必须单调且位于 0..29")
        if not 0 <= int(self.delivery_max_distance) <= 20:
            raise ValueError("交付最大返仓距离必须位于 0..20")
        if not 1 <= int(self.delivery_runner_cap) <= 12:
            raise ValueError("并行交付工上限必须位于 1..12")
        if not 0 <= int(self.delivery_cutoff_hour) <= 23:
            raise ValueError("交付截止小时必须位于 0..23")
        if not 0 <= int(self.fertilize_priority) <= 6 or int(self.fertilize_daily_cap) < 0:
            raise ValueError("施肥调度参数非法")
        if not 0 <= int(self.fertilize_start_day) <= 29:
            raise ValueError("施肥起始日必须位于 0..29")
        if not 0 <= int(self.collect_fertilizer_priority) <= 8:
            raise ValueError("肥料收集优先级非法")
        if not -1 <= int(self.animal_harvest_priority) <= 8:
            raise ValueError("动物收获优先级必须位于 -1..8")
        if not 0 <= int(self.persistent_preempt_priority) <= int(self.persistent_lock_max_priority) <= 8:
            raise ValueError("持久任务优先级非法")
        if not 0 <= int(self.persistent_lock_radius) <= 20:
            raise ValueError("持久任务锁定半径非法")
        if not 0 <= int(self.inflight_task_preempt_priority) <= 8:
            raise ValueError("在途任务抢占优先级非法")
        if not 0 <= int(self.dynamic_role_stability_penalty) <= 100:
            raise ValueError("动态角色稳定惩罚非法")
        if not 0 <= int(self.plant_cutoff_hour) <= 23 or not 1 <= int(self.plant_admission_cap) <= 64:
            raise ValueError("种植容量准入参数非法")
        if not 1 <= int(self.feed_units_per_runner) <= 18 or not 1 <= int(self.feed_runner_cap) <= 12:
            raise ValueError("饲料工参数非法")
        if not 1 <= int(self.animal_units_per_runner) <= 8 or not 1 <= int(self.animal_runner_cap) <= 12:
            raise ValueError("动物搬运工参数非法")
        if not 0 <= int(self.terminal_return_buffer) <= 24:
            raise ValueError("终局返仓缓冲非法")
        if not 0 <= int(self.terminal_hire_cap) <= 15:
            raise ValueError("终局雇工上限必须位于 0..15")
        if any(crop not in CROPS for crop in self.fertilize_crops):
            raise ValueError("施肥作物集合非法")
        if not 0 <= int(self.windowed_water_start_day) <= 29:
            raise ValueError("窗口化浇水启用日非法")
        if not 0 <= int(self.local_route_priority_slack) <= 4:
            raise ValueError("局部路线优先级 slack 必须位于 0..4")
        if not 0 <= int(self.surplus_crop_retirement_start_day) <= 29:
            raise ValueError("冗余作物退役起始日必须位于 0..29")
        if not 0 <= int(self.surplus_crop_retirement_priority) <= 6:
            raise ValueError("冗余作物退役优先级必须位于 0..6")
        if not 1 <= int(self.animal_service_max_steps) <= 4:
            raise ValueError("动物同格服务会话步数必须位于 1..4")
        if not -1 <= int(self.animal_service_preempt_priority) <= 8:
            raise ValueError("动物同格服务抢占优先级必须位于 -1..8")
        if not 0 <= int(self.work_conserving_max_priority) <= 8:
            raise ValueError("保守二次分配优先级必须位于 0..8")
        if not 0 <= int(self.work_conserving_max_distance) <= 64:
            raise ValueError("保守二次分配距离必须位于 0..64")
        if int(self.stable_tile_owner_penalty) < 0 or (
            self.stable_tile_owner_enabled
            and int(self.stable_tile_owner_penalty) >= float(self.priority_weight)
        ):
            raise ValueError("稳定责任区惩罚必须非负且小于一级任务优先级代价")
        if float(self.deadline_slack_weight) < 0.0 or (
            float(self.deadline_slack_weight) > 0.0
            and float(self.deadline_slack_weight) * 24.0 >= float(self.priority_weight)
        ):
            raise ValueError("截止松弛权重在整日内不得跨越一级任务优先级")
        if not 0 <= int(self.cow_care_deadline_hour) <= 23:
            raise ValueError("奶牛照料截止小时必须位于 0..23")
        if not 0 <= int(self.cow_care_deadline_priority) <= 8:
            raise ValueError("奶牛照料截止优先级必须位于 0..8")
        if not 0 <= int(self.fertilizer_collection_deadline_hour) <= 23:
            raise ValueError("肥料回收截止小时必须位于 0..23")
        if not 0 <= int(self.fertilizer_collection_deadline_priority) <= 8:
            raise ValueError("肥料回收截止优先级必须位于 0..8")
        if not 0 <= int(self.strawberry_fertilizer_first_start_day) <= 29:
            raise ValueError("草莓优先施肥起始日必须位于 0..29")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "ExecutorTuning":
        payload = dict(raw or {})
        if "fertilize_crops" in payload:
            payload["fertilize_crops"] = tuple(str(crop) for crop in payload["fertilize_crops"])
        return cls(**payload)

    def stable_payload(self) -> dict[str, Any]:
        return {
            "travel_weight": float(self.travel_weight),
            "priority_weight": float(self.priority_weight),
            "standing_bonus": float(self.standing_bonus),
            "sticky_bonus": float(self.sticky_bonus),
            "role_penalty": float(self.role_penalty),
            "deadline_penalty": float(self.deadline_penalty),
            "candidate_cap": int(self.candidate_cap),
            "stratified_candidate_pool_enabled": bool(
                self.stratified_candidate_pool_enabled
            ),
            "rolling_route_enabled": bool(self.rolling_route_enabled),
            "rolling_route_horizon": int(self.rolling_route_horizon),
            "rolling_route_replan_interval": int(self.rolling_route_replan_interval),
            "rolling_route_priority_slack": int(self.rolling_route_priority_slack),
            "rolling_route_load_weight": float(self.rolling_route_load_weight),
            "transition_aware_route_enabled": bool(
                self.transition_aware_route_enabled
            ),
            "rolling_route_delivery_weight": float(
                self.rolling_route_delivery_weight
            ),
            "delivery_value_threshold": int(self.delivery_value_threshold),
            "opening_delivery_value_threshold": int(
                self.opening_delivery_value_threshold
            ),
            "opening_delivery_start_day": int(self.opening_delivery_start_day),
            "opening_delivery_until_day": int(self.opening_delivery_until_day),
            "delivery_cash_ceiling": int(self.delivery_cash_ceiling),
            "delivery_max_distance": int(self.delivery_max_distance),
            "delivery_runner_cap": int(self.delivery_runner_cap),
            "persistent_delivery_runner_enabled": bool(self.persistent_delivery_runner_enabled),
            "delivery_cutoff_hour": int(self.delivery_cutoff_hour),
            "fertilize_priority": int(self.fertilize_priority),
            "fertilize_daily_cap": int(self.fertilize_daily_cap),
            "fertilize_start_day": int(self.fertilize_start_day),
            "fertilize_windowed": bool(self.fertilize_windowed),
            "fertilize_before_water_enabled": bool(self.fertilize_before_water_enabled),
            "fertilize_crops": list(self.fertilize_crops),
            "collect_fertilizer_priority": int(self.collect_fertilizer_priority),
            "animal_harvest_priority": int(self.animal_harvest_priority),
            "persistent_lock_enabled": bool(self.persistent_lock_enabled),
            "persistent_lock_max_priority": int(self.persistent_lock_max_priority),
            "persistent_preempt_priority": int(self.persistent_preempt_priority),
            "persistent_lock_radius": int(self.persistent_lock_radius),
            "inflight_task_lock_enabled": bool(self.inflight_task_lock_enabled),
            "inflight_task_preempt_priority": int(self.inflight_task_preempt_priority),
            "dynamic_role_enabled": bool(self.dynamic_role_enabled),
            "dynamic_role_stability_penalty": int(self.dynamic_role_stability_penalty),
            "capacity_admission_enabled": bool(self.capacity_admission_enabled),
            "plant_cutoff_hour": int(self.plant_cutoff_hour),
            "plant_admission_cap": int(self.plant_admission_cap),
            "multi_feed_runner_enabled": bool(self.multi_feed_runner_enabled),
            "feed_units_per_runner": int(self.feed_units_per_runner),
            "feed_runner_cap": int(self.feed_runner_cap),
            "multi_animal_runner_enabled": bool(self.multi_animal_runner_enabled),
            "animal_units_per_runner": int(self.animal_units_per_runner),
            "animal_runner_cap": int(self.animal_runner_cap),
            "terminal_harvest_only_enabled": bool(self.terminal_harvest_only_enabled),
            "terminal_return_buffer": int(self.terminal_return_buffer),
            "terminal_hire_cap": int(self.terminal_hire_cap),
            "terminal_local_route_enabled": bool(
                self.terminal_local_route_enabled
            ),
            "animal_zoning_enabled": bool(self.animal_zoning_enabled),
            "crop_zoning_enabled": bool(self.crop_zoning_enabled),
            "surplus_crop_retirement_enabled": bool(
                self.surplus_crop_retirement_enabled
            ),
            "surplus_crop_retirement_start_day": int(
                self.surplus_crop_retirement_start_day
            ),
            "surplus_crop_retirement_priority": int(
                self.surplus_crop_retirement_priority
            ),
            "windowed_water_enabled": bool(self.windowed_water_enabled),
            "windowed_water_start_day": int(self.windowed_water_start_day),
            "staggered_windowed_water_enabled": bool(self.staggered_windowed_water_enabled),
            "local_route_queue_enabled": bool(self.local_route_queue_enabled),
            "local_route_priority_slack": int(self.local_route_priority_slack),
            "local_route_spill_enabled": bool(self.local_route_spill_enabled),
            "animal_service_session_enabled": bool(self.animal_service_session_enabled),
            "animal_service_max_steps": int(self.animal_service_max_steps),
            "animal_service_preempt_priority": int(self.animal_service_preempt_priority),
            "work_conserving_second_pass_enabled": bool(
                self.work_conserving_second_pass_enabled
            ),
            "work_conserving_max_priority": int(
                self.work_conserving_max_priority
            ),
            "work_conserving_max_distance": int(
                self.work_conserving_max_distance
            ),
            "stable_tile_owner_enabled": bool(self.stable_tile_owner_enabled),
            "stable_tile_owner_penalty": int(self.stable_tile_owner_penalty),
            "deadline_slack_weight": float(self.deadline_slack_weight),
            "cow_care_deadline_enabled": bool(self.cow_care_deadline_enabled),
            "cow_care_deadline_hour": int(self.cow_care_deadline_hour),
            "cow_care_deadline_priority": int(self.cow_care_deadline_priority),
            "fertilizer_collection_deadline_enabled": bool(
                self.fertilizer_collection_deadline_enabled
            ),
            "fertilizer_collection_deadline_hour": int(
                self.fertilizer_collection_deadline_hour
            ),
            "fertilizer_collection_deadline_priority": int(
                self.fertilizer_collection_deadline_priority
            ),
            "strawberry_fertilizer_first_enabled": bool(
                self.strawberry_fertilizer_first_enabled
            ),
            "strawberry_fertilizer_first_start_day": int(
                self.strawberry_fertilizer_first_start_day
            ),
        }


@dataclass(frozen=True)
class Task:
    priority: int
    x: int
    y: int
    action: tuple[Any, ...]
    deadline: int
    batch_key: tuple[Any, ...]
    chain_id: str
    value: float = 1.0

    @property
    def key(self) -> tuple[Any, ...]:
        return (self.priority, self.deadline, self.action[0], self.x, self.y, *self.action[1:])


@dataclass(frozen=True)
class ExecutorResult:
    unit_actions: tuple[tuple[Any, ...], ...]
    pending_plants: Mapping[str, int]
    actor_tasks: tuple[str | None, ...]
    actor_roles: tuple[int, ...]
    overdue_tasks: int
    actor_targets: tuple[tuple[int, int] | None, ...]
    overdue_task_details: tuple[Mapping[str, Any], ...]


class CommonExecutor:
    def __init__(self, tuning: ExecutorTuning | Mapping[str, Any] | None = None) -> None:
        self.tuning = tuning if isinstance(tuning, ExecutorTuning) else ExecutorTuning.from_mapping(tuning)
        self.sticky_chain: dict[int, str] = {}
        self.sticky_task: dict[int, tuple[Any, ...]] = {}
        self.roles: dict[tuple[int, int], int] = {}
        self.role_signature: tuple[int, int, int] | None = None
        self.animal_service_sessions: dict[int, tuple[int, str, int]] = {}
        self.delivery_runner: int | None = None
        self.rolling_routes: dict[int, list[tuple[Any, ...]]] = {}
        self.rolling_route_signature: tuple[Any, ...] | None = None
        self.rolling_route_next_replan = 0
        self.crop_cursor = 0
        self.audit: Counter[str] = Counter()

    @staticmethod
    def _open_positions(grid: Sequence[Sequence[Any]]) -> list[tuple[int, int]]:
        values = [(x, y) for y, row in enumerate(grid) for x, tile in enumerate(row) if tile != "LOCKED"]
        return sorted(values, key=lambda pos: (distance(pos, shed_gate(pos)), quadrant(pos), pos[1], pos[0]))

    def _fair_crop_order(self, have: Counter[str], target: Mapping[str, int],
                         assigned: Counter[str]) -> list[str]:
        cycle = list(CROPS)
        offset = self.crop_cursor % len(cycle)
        tie = cycle[offset:] + cycle[:offset]
        return sorted((crop for crop, count in target.items() if count > 0),
                      key=lambda crop: ((have[crop] + assigned[crop]) / max(1, target[crop]), tie.index(crop)))

    @staticmethod
    def _task(contract: DailyContract, priority: int, x: int, y: int,
              action: tuple[Any, ...], chain: str, value: float = 1.0) -> Task:
        verb = str(action[0])
        deadline = int(contract.deadlines.get(verb, 23 if verb in {"WATER", "FEED", "PLANT", "DIG"} else 24))
        product = action[1] if len(action) > 1 else None
        return Task(priority, x, y, action, deadline, (quadrant((x, y)), verb, product), chain, value)

    def tasks(self, state: CanonicalState, contract: DailyContract,
              feedback: RuntimeFeedback) -> list[Task]:
        grid = state.grid
        value_planner = bool(contract.risk_budget.get("value_labor_planner_enabled", 0.0))
        planner_windowed_water = bool(
            contract.risk_budget.get("planner_windowed_water_enabled", 0.0)
        )
        planner_allow_fertilize = bool(
            contract.risk_budget.get("planner_allow_fertilize", 0.0)
        )
        crops, animals, structures = farm_counts(grid)
        tasks: list[Task] = []
        fertilizer_candidates: list[Task] = []
        retirement_positions: set[tuple[int, int]] = set()
        if (self.tuning.surplus_crop_retirement_enabled
                and state.day >= int(self.tuning.surplus_crop_retirement_start_day)):
            for crop in ("STRAWBERRY", "TOMATO"):
                surplus = max(0, int(crops[crop]) - int(contract.crops.get(crop, 0)))
                if surplus <= 0:
                    continue
                positions = [
                    (x, y)
                    for y, row in enumerate(grid)
                    for x, tile in enumerate(row)
                    if isinstance(tile, Mapping)
                    and tile.get("kind") == "PLANT"
                    and str(tile.get("crop") or "") == crop
                ]
                # 高频动物优先占据近仓位，因此先退役离仓最近的多年生作物。
                positions.sort(key=lambda pos: (
                    distance(pos, shed_gate(pos)), pos[1], pos[0],
                ))
                retirement_positions.update(positions[:surplus])
                self.audit["surplus_crop_retirement_candidates"] += min(
                    surplus, len(positions)
                )
        fertilizer_available = (
            state.shed.get("FERTILIZER", 0)
            + sum(inventory.get("FERTILIZER", 0) for inventory in state.inventories)
        )
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if not isinstance(tile, Mapping):
                    continue
                kind = tile.get("kind")
                chain = f"q{quadrant((x, y))}:{x}:{y}"
                if kind == "PLANT":
                    crop = str(tile.get("crop") or "")
                    facts = CROP_FACTS.get(crop, {})
                    age = state.day - integer(tile.get("planted_day"), state.day)
                    if (x, y) in retirement_positions:
                        units = integer(tile.get("yield_units"))
                        ripe = (
                            units > 0
                            and age >= integer(facts.get("first"), 99)
                        )
                        if ripe:
                            tasks.append(self._task(
                                contract,
                                int(self.tuning.surplus_crop_retirement_priority),
                                x, y, ("HARVEST",), chain,
                                max(4.0, units * state.prices.get(
                                    crop, BASE_PRICE.get(crop, 1),
                                ) / 25.0),
                            ))
                            self.audit["surplus_crop_retirement_harvest"] += 1
                        else:
                            tasks.append(self._task(
                                contract,
                                int(self.tuning.surplus_crop_retirement_priority),
                                x, y, ("DIG",), chain, 3.0,
                            ))
                            self.audit["surplus_crop_retirement_dig"] += 1
                        continue
                    # 肥料只投向高价值作物，且一次覆盖三天；这是执行器的通用增产动作，
                    # 不改变专家的作物目标，也不读取未来价格/商店。
                    useful_window = True
                    if self.tuning.fertilize_windowed:
                        if bool(facts.get("ongoing")):
                            interval = 1 if crop == "TOMATO" else 2
                            last_age = integer(facts.get("first")) + interval * (
                                integer(facts.get("max_yield"), 1) - 1
                            )
                            useful_window = integer(facts.get("first")) - 1 <= age <= last_age
                        else:
                            first_bonus_age = (integer(facts.get("mature")) + 1) // 2
                            useful_window = first_bonus_age <= age <= integer(facts.get("mature"))
                    if ((not value_planner or planner_allow_fertilize)
                            and state.day >= int(self.tuning.fertilize_start_day)
                            and crop in self.tuning.fertilize_crops
                            and fertilizer_available > 0
                            and useful_window
                            and integer(tile.get("fertilized_until_day"), -1) < state.day
                            and not tile.get("watered_today")):
                        fertilizer_candidates.append(self._task(
                            contract, self.tuning.fertilize_priority, x, y, ("FERTILIZE",), chain,
                            max(2.0, float(BASE_PRICE.get(crop, 1)) / 25.0),
                        ))
                    needs_water = not tile.get("watered_today")
                    if (needs_water
                            and state.day >= int(self.tuning.windowed_water_start_day)
                            and (self.tuning.windowed_water_enabled or planner_windowed_water)):
                        survival_due = integer(tile.get("consecutive_unwatered"), 0) >= 1
                        staggered_maintenance = (
                            self.tuning.staggered_windowed_water_enabled
                            and (x + y + state.day) % 2 == 0
                        )
                        if bool(facts.get("ongoing")):
                            next_age = age + 1 - integer(facts.get("first"), 0)
                            interval = 1 if crop == "TOMATO" else 2
                            production_due = next_age >= 0 and next_age % interval == 0
                            fertilizer_bonus_due = (
                                production_due
                                and integer(tile.get("fertilized_until_day"), -1) >= state.day
                            )
                            needs_water = survival_due or fertilizer_bonus_due or staggered_maintenance
                        else:
                            window_start = (integer(facts.get("mature"), 0) + 1) // 2
                            productive_window = window_start <= age <= integer(facts.get("mature"), 0)
                            needs_water = survival_due or productive_window or staggered_maintenance
                    if needs_water:
                        urgent = integer(tile.get("consecutive_unwatered")) >= 1 or state.hour >= contract.deadlines.get("WATER", 22)
                        tasks.append(self._task(contract, 0 if urgent else int(contract.labor_priority.get("WATER", 2)),
                                                x, y, ("WATER",), chain, 3.0 if urgent else 2.0))
                    units = integer(tile.get("yield_units"))
                    ripe = bool(facts.get("ongoing")) or units >= integer(facts.get("max_yield"), 99) or age >= integer(facts.get("mature"), 99)
                    if units > 0 and age >= integer(facts.get("first")) and ripe:
                        harvest_value = (
                            max(4.0, units * state.prices.get(crop, BASE_PRICE.get(crop, 1)) / 25.0)
                            if value_planner else 4.0
                        )
                        tasks.append(self._task(contract, int(contract.labor_priority.get("HARVEST", 2)),
                                                x, y, ("HARVEST",), chain, harvest_value))
                elif animal_kind(tile):
                    animal = animal_kind(tile)
                    product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}.get(animal or "", "")
                    animal_task_value = max(2.5, state.prices.get(product, 1) / 25.0) if value_planner else 2.5
                    if not tile.get("fed_today"):
                        urgent = integer(tile.get("consecutive_unfed")) >= 1 or state.hour >= contract.deadlines.get("FEED", 20)
                        tasks.append(self._task(contract, 0 if urgent else int(contract.labor_priority.get("FEED", 1)),
                                                x, y, ("FEED",), chain, 4.0 if urgent else animal_task_value))
                    if integer(tile.get("yield_units")) > 0:
                        harvest_value = (
                            max(4.0, integer(tile.get("yield_units")) * state.prices.get(product, 1) / 25.0)
                            if value_planner else 4.0
                        )
                        animal_harvest_priority = (
                            int(self.tuning.animal_harvest_priority)
                            if int(self.tuning.animal_harvest_priority) >= 0
                            else int(contract.labor_priority.get("HARVEST", 2))
                        )
                        tasks.append(self._task(contract, animal_harvest_priority,
                                                x, y, ("HARVEST",), chain, harvest_value))
                    if tile.get("fertilizer_available"):
                        collect_priority = 1 if value_planner else self.tuning.collect_fertilizer_priority
                        collect_deadline_due = (
                            self.tuning.fertilizer_collection_deadline_enabled
                            and state.hour >= int(
                                self.tuning.fertilizer_collection_deadline_hour
                            )
                        )
                        if collect_deadline_due:
                            collect_priority = min(
                                collect_priority,
                                int(self.tuning.fertilizer_collection_deadline_priority),
                            )
                            self.audit["fertilizer_collection_deadline_tasks"] += 1
                        tasks.append(self._task(
                            contract, collect_priority, x, y,
                            ("COLLECT_FERTILIZER",), chain,
                            max(1.0, state.prices.get("FERTILIZER", 100) / 25.0) if value_planner else 1.0,
                        ))
                    if not tile.get("cared_today"):
                        care_priority = int(contract.labor_priority.get("CARE", 7))
                        care_value = animal_task_value if value_planner else 0.5
                        cow_deadline_due = (
                            self.tuning.cow_care_deadline_enabled
                            and animal == "COW"
                            and state.hour >= int(self.tuning.cow_care_deadline_hour)
                        )
                        if cow_deadline_due:
                            care_priority = min(
                                care_priority, int(self.tuning.cow_care_deadline_priority),
                            )
                            care_value = max(4.0, care_value)
                            self.audit["cow_care_deadline_tasks"] += 1
                        tasks.append(self._task(
                            contract, care_priority, x, y, ("CARE",), chain, care_value,
                        ))
                elif kind == "WEED":
                    tasks.append(self._task(contract, 6, x, y, ("DIG",), chain, 1.0))

        strawberry_first = (
            self.tuning.strawberry_fertilizer_first_enabled
            and state.day >= int(self.tuning.strawberry_fertilizer_first_start_day)
        )
        fertilizer_candidates.sort(key=lambda task: (
            0 if strawberry_first and str(grid[task.y][task.x].get("crop") or "")
            == "STRAWBERRY" else 1,
            -task.value, task.y, task.x,
        ))
        if strawberry_first and fertilizer_candidates:
            self.audit["strawberry_fertilizer_first_turns"] += 1
        selected_fertilizer = fertilizer_candidates[:min(
            int(self.tuning.fertilize_daily_cap), int(fertilizer_available),
        )]
        tasks.extend(selected_fertilizer)
        if self.tuning.fertilize_before_water_enabled and selected_fertilizer:
            selected_tiles = {(task.x, task.y) for task in selected_fertilizer}
            adjusted: list[Task] = []
            for task in tasks:
                if (
                    task.action[0] == "WATER"
                    and (task.x, task.y) in selected_tiles
                    and task.value < 3.0
                ):
                    adjusted.append(Task(
                        max(task.priority, int(self.tuning.fertilize_priority) + 1),
                        task.x, task.y, task.action, task.deadline,
                        task.batch_key, task.chain_id, task.value,
                    ))
                    self.audit["fertilize_water_bundle_deferred"] += 1
                else:
                    adjusted.append(task)
            tasks = adjusted

        empty = [pos for pos in self._open_positions(grid) if grid[pos[1]][pos[0]] is None]
        cursor = 0
        pasture_goal = int(contract.asset_targets.get("structures", {}).get(
            "PASTURE", contract.animals.get("SHEEP", 0) + contract.animals.get("COW", 0)))
        coop_goal = int(contract.asset_targets.get("structures", {}).get("COOP", contract.animals.get("GOOSE", 0)))
        for structure, deficit in (("PASTURE", max(0, pasture_goal - structures["PASTURE"])),
                                   ("COOP", max(0, coop_goal - structures["COOP"]))):
            for _ in range(min(deficit, max(0, len(empty) - cursor))):
                x, y = empty[cursor]
                cursor += 1
                verb = "BUILD_PASTURE" if structure == "PASTURE" else "BUILD_COOP"
                tasks.append(self._task(
                    contract, 3, x, y, (verb,), f"q{quadrant((x, y))}:{x}:{y}", 2.0,
                ))

        animal_deficit = {animal: max(0, contract.animals.get(animal, 0) - animals[animal]) for animal in ANIMALS}
        if self.tuning.animal_zoning_enabled:
            open_structures: dict[str, list[tuple[int, int]]] = {"PASTURE": [], "COOP": []}
            for y, row in enumerate(grid):
                for x, tile in enumerate(row):
                    if (isinstance(tile, Mapping) and not animal_kind(tile)
                            and tile.get("kind") in open_structures):
                        open_structures[str(tile["kind"])].append((x, y))
            # 奶牛的两日生产周期更短，放在近仓位；羊放到牧场外圈，为后续奶牛保留内圈。
            for animal in ("COW", "SHEEP", "GOOSE"):
                structure = "COOP" if animal == "GOOSE" else "PASTURE"
                positions = sorted(
                    open_structures[structure],
                    key=lambda pos: (
                        distance(pos, shed_gate(pos)) * (-1 if animal == "SHEEP" else 1),
                        pos[1], pos[0],
                    ),
                )
                for x, y in positions[:animal_deficit[animal]]:
                    tasks.append(self._task(
                        contract, 3, x, y, ("PLACE", animal),
                        f"q{quadrant((x, y))}:{x}:{y}", 3.0,
                    ))
                    open_structures[structure].remove((x, y))
        else:
            for y, row in enumerate(grid):
                for x, tile in enumerate(row):
                    if not isinstance(tile, Mapping) or animal_kind(tile):
                        continue
                    compatible = (("GOOSE",) if tile.get("kind") == "COOP" else
                                  ("SHEEP", "COW") if tile.get("kind") == "PASTURE" else ())
                    for animal in compatible:
                        if animal_deficit[animal] > 0:
                            tasks.append(self._task(
                                contract, 3, x, y, ("PLACE", animal),
                                f"q{quadrant((x, y))}:{x}:{y}", 3.0,
                            ))
                            animal_deficit[animal] -= 1
                            break

        plantable = list(empty[cursor:])
        if self.tuning.capacity_admission_enabled:
            remaining_hours = max(0, int(self.tuning.plant_cutoff_hour) - state.hour + 1)
            remaining_actions = remaining_hours * max(1, len(state.positions))
            maintenance = [
                task for task in tasks
                if task.action[0] in {"WATER", "FEED", "HARVEST", "CARE"}
            ]
            maintenance_work = sum(
                min((distance(position, (task.x, task.y)) for position in state.positions), default=20) + 1
                for task in maintenance
            )
            plant_budget = max(0, remaining_actions - maintenance_work)
            affordable: list[tuple[int, int]] = []
            for position in plantable:
                bundle_work = min(
                    (distance(actor_position, position) for actor_position in state.positions),
                    default=20,
                ) + 2  # 移动/种植，并为同日 WATER 预留一次动作。
                if bundle_work > plant_budget or len(affordable) >= self.tuning.plant_admission_cap:
                    break
                affordable.append(position)
                plant_budget -= bundle_work
            self.audit["plant_candidates_rejected_by_capacity"] += len(plantable) - len(affordable)
            self.audit["plant_candidates_admitted"] += len(affordable)
            plantable = affordable
        assigned: Counter[str] = Counter()
        budgets = {crop: state.seeds.get(crop, 0) for crop in CROPS}
        while plantable:
            order = self._fair_crop_order(crops, contract.crops, assigned)
            if self.tuning.crop_zoning_enabled:
                zone_rank = {"STRAWBERRY": 0, "TOMATO": 1, "MELON": 2, "WHEAT": 3, "CARROT": 4}
                order = sorted(order, key=lambda crop: (
                    zone_rank.get(crop, 9),
                    (crops[crop] + assigned[crop]) / max(1, contract.crops.get(crop, 0)),
                    CROPS.index(crop),
                ))
            crop = next((name for name in order
                         if crops[name] + assigned[name] < contract.crops.get(name, 0)
                         and assigned[name] < budgets[name]), None)
            if crop is None:
                break
            x, y = plantable.pop(0)
            tasks.append(self._task(contract, int(contract.labor_priority.get("PLANT", 3)),
                                    x, y, ("PLANT", crop), f"q{quadrant((x, y))}:{x}:{y}", 2.0))
            assigned[crop] += 1
            self.crop_cursor = (self.crop_cursor + 1) % len(CROPS)
        if feedback.terminal and self.tuning.terminal_harvest_only_enabled:
            before = len(tasks)
            tasks = [
                task for task in tasks
                if task.action[0] in {"HARVEST", "COLLECT_FERTILIZER"}
            ]
            self.audit["terminal_tasks_suppressed"] += before - len(tasks)
        if value_planner:
            # 全局按 value 重排会把同类高价任务塞满 candidate_cap，导致携带条件不满足的
            # FEED/PLACE 挤掉其他可执行任务。价值只进入 Hungarian 的局部代价，任务池仍按
            # deadline + batch 保持类型和空间覆盖。
            tasks.sort(key=lambda task: (
                task.priority, task.deadline, task.batch_key,
                task.y, task.x, task.action,
            ))
            self.audit["value_labor_planner_turns"] += 1
            self.audit["value_labor_planner_rejected_units"] += int(
                contract.risk_budget.get("planner_rejected_units", 0.0)
            )
        else:
            tasks.sort(key=lambda task: (task.priority, task.deadline, task.batch_key, task.y, task.x, task.action))
        self.audit["tasks_generated"] += len(tasks)
        self.audit["batches_generated"] += len({task.batch_key for task in tasks})
        self.audit["feedback_backlog_seen"] += int(feedback.task_backlog > 0)
        return tasks

    def _task_cost(self, actor: int, position: tuple[int, int], inventory: Mapping[str, int],
                   task: Task, state: CanonicalState, contract: DailyContract) -> float:
        verb = str(task.action[0])
        if verb == "FEED" and inventory.get("WHEAT", 0) <= 0:
            return 1e9
        if verb == "PLACE" and inventory.get(str(task.action[1]), 0) <= 0:
            return 1e9
        if verb == "FERTILIZE" and inventory.get("FERTILIZER", 0) <= 0:
            return 1e9
        travel = distance(position, (task.x, task.y))
        late = max(0, state.hour + travel + 1 - task.deadline)
        slack = max(0, task.deadline - state.hour - travel - 1)
        standing_bonus = -self.tuning.standing_bonus if position == (task.x, task.y) else 0.0
        sticky_bonus = -self.tuning.sticky_bonus if self.sticky_chain.get(actor) == task.chain_id else 0.0
        stage = max(1, contract.lands)
        role = self.roles.setdefault((stage, actor), actor % stage)
        role_penalty = self.tuning.role_penalty if quadrant((task.x, task.y)) != role else 0.0
        owner_penalty = 0.0
        if self.tuning.stable_tile_owner_enabled:
            owner = self._stable_tile_owner(task, state, contract)
            if owner is not None and actor != owner:
                owner_penalty = float(self.tuning.stable_tile_owner_penalty)
        return (task.priority * self.tuning.priority_weight + late * self.tuning.deadline_penalty
                + travel * self.tuning.travel_weight + role_penalty
                + slack * self.tuning.deadline_slack_weight
                + owner_penalty + sticky_bonus + standing_bonus - task.value)

    def _stable_tile_owner(self, task: Task, state: CanonicalState,
                           contract: DailyContract) -> int | None:
        """在象限内构造确定性 Voronoi 责任区；只影响软成本，不形成任务硬锁。"""

        stage = max(1, int(contract.lands))
        task_role = quadrant((task.x, task.y))
        role_actors = sorted(
            actor for actor in range(len(state.positions))
            if self.roles.setdefault((stage, actor), actor % stage) == task_role
        )
        if not role_actors:
            return None

        # 把每个象限镜像到“仓库侧为 (0, 0)”的统一局部坐标，再以最远点采样
        # 生成稳定锚点。相邻格倾向于归同一 actor，同时随人数增加逐步细分。
        local_x = 4 - task.x if task.x < 5 else task.x - 5
        local_y = 4 - task.y if task.y < 5 else task.y - 5
        tiles = [(x, y) for y in range(5) for x in range(5)]
        anchors = [(0, 0)]
        while len(anchors) < min(len(role_actors), len(tiles)):
            candidates = [tile for tile in tiles if tile not in anchors]
            anchors.append(max(candidates, key=lambda tile: (
                min(distance(tile, anchor) for anchor in anchors),
                distance(tile, (0, 0)), tile[1], tile[0],
            )))
        slot = min(range(len(anchors)), key=lambda index: (
            distance((local_x, local_y), anchors[index]), index,
        ))
        return role_actors[slot]

    def _rebalance_roles(self, state: CanonicalState, contract: DailyContract,
                         tasks: Sequence[Task], actors: Sequence[int]) -> None:
        """按当日真实任务负荷分配象限人手；同一天人数不变时保持稳定。"""
        stage = max(1, int(contract.lands))
        signature = (int(state.day), stage, len(state.positions))
        if not self.tuning.dynamic_role_enabled or self.role_signature == signature or not actors:
            return
        active = list(range(stage))
        load = {role: 0.25 for role in active}
        targets: dict[int, list[tuple[int, int]]] = {role: [] for role in active}
        for task in tasks:
            role = quadrant((task.x, task.y))
            if role not in load:
                continue
            urgency = max(0.5, 4.0 - min(3, int(task.priority)))
            load[role] += urgency + max(0.0, float(task.value)) * 0.25
            targets[role].append((task.x, task.y))

        quota = {role: 0 for role in active}
        remaining = len(actors)
        if len(actors) >= len(active):
            for role in active:
                quota[role] = 1
            remaining -= len(active)
        total_load = sum(load.values())
        raw = {role: remaining * load[role] / max(0.01, total_load) for role in active}
        for role in active:
            take = int(raw[role])
            quota[role] += take
            remaining -= take
        for role in sorted(active, key=lambda item: (-(raw[item] - int(raw[item])), -load[item], item)):
            if remaining <= 0:
                break
            quota[role] += 1
            remaining -= 1

        slots = [role for role in active for _ in range(quota[role])]
        if len(slots) != len(actors):
            return
        matrix: list[list[float]] = []
        for actor in actors:
            previous = self.roles.get((stage, actor))
            row: list[float] = []
            for role in slots:
                proximity = min(
                    (distance(state.positions[actor], target) for target in targets[role]),
                    default=0,
                )
                stability = (
                    self.tuning.dynamic_role_stability_penalty
                    if previous is not None and previous != role else 0
                )
                row.append(float(proximity + stability))
            matrix.append(row)
        chosen = self._hungarian(matrix)
        for actor, column in zip(actors, chosen):
            if 0 <= column < len(slots):
                self.roles[(stage, actor)] = slots[column]
        self.role_signature = signature
        self.audit["dynamic_role_rebalances"] += 1
        for role, count in quota.items():
            self.audit[f"dynamic_role_quota_q{role}"] += count

    @staticmethod
    def _hungarian(cost: Sequence[Sequence[float]]) -> list[int]:
        """矩形最小成本匹配；每个 actor 返回唯一任务列。"""
        n = len(cost)
        m = len(cost[0]) if n else 0
        if not n:
            return []
        if m < n:
            raise ValueError("Hungarian requires columns >= rows")
        u = [0.0] * (n + 1)
        v = [0.0] * (m + 1)
        p = [0] * (m + 1)
        way = [0] * (m + 1)
        for i in range(1, n + 1):
            p[0] = i
            j0 = 0
            minv = [math.inf] * (m + 1)
            used = [False] * (m + 1)
            while True:
                used[j0] = True
                i0 = p[j0]
                delta = math.inf
                j1 = 0
                for j in range(1, m + 1):
                    if used[j]:
                        continue
                    cur = float(cost[i0 - 1][j - 1]) - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
                for j in range(m + 1):
                    if used[j]:
                        u[p[j]] += delta
                        v[j] -= delta
                    else:
                        minv[j] -= delta
                j0 = j1
                if p[j0] == 0:
                    break
            while True:
                j1 = way[j0]
                p[j0] = p[j1]
                j0 = j1
                if j0 == 0:
                    break
        assignment = [-1] * n
        for j in range(1, m + 1):
            if p[j] > 0:
                assignment[p[j] - 1] = j - 1
        return assignment

    @staticmethod
    def _stratified_candidates(tasks: Sequence[Task], cap: int) -> list[Task]:
        """在不跨越优先级/截止期的前提下，轮转覆盖不同任务批次。"""
        strata: dict[tuple[int, int], dict[tuple[Any, ...], list[Task]]] = {}
        for task in tasks:
            batch_groups = strata.setdefault((task.priority, task.deadline), {})
            batch_groups.setdefault(task.batch_key, []).append(task)
        selected: list[Task] = []
        for stratum in sorted(strata):
            queues = list(strata[stratum].values())
            offsets = [0] * len(queues)
            while len(selected) < cap:
                advanced = False
                for index, queue in enumerate(queues):
                    if offsets[index] >= len(queue):
                        continue
                    selected.append(queue[offsets[index]])
                    offsets[index] += 1
                    advanced = True
                    if len(selected) >= cap:
                        break
                if not advanced:
                    break
            if len(selected) >= cap:
                break
        return selected

    @staticmethod
    def _route_task_feasible(inventory: Mapping[str, int], task: Task) -> bool:
        verb = str(task.action[0])
        if verb == "FEED":
            return inventory.get("WHEAT", 0) > 0
        if verb == "FERTILIZE":
            return inventory.get("FERTILIZER", 0) > 0
        if verb == "PLACE":
            return inventory.get(str(task.action[1]), 0) > 0
        return True

    @staticmethod
    def _route_consume(inventory: dict[str, int], task: Task) -> None:
        item = None
        if task.action[0] == "FEED":
            item = "WHEAT"
        elif task.action[0] == "FERTILIZE":
            item = "FERTILIZER"
        elif task.action[0] == "PLACE" and len(task.action) > 1:
            item = str(task.action[1])
        if item is not None:
            inventory[item] = max(0, int(inventory.get(item, 0)) - 1)

    @staticmethod
    def _route_action_rank(task: Task) -> int:
        """同一地块的保值顺序；只使用当前已生成任务。"""
        return {
            "FERTILIZE": 0,
            "WATER": 1,
            "FEED": 1,
            "HARVEST": 2,
            "COLLECT_FERTILIZER": 3,
            "CARE": 4,
            "DIG": 5,
        }.get(str(task.action[0]), 2)

    @classmethod
    def _route_predecessors_pending(cls, task: Task,
                                    remaining: Sequence[Task]) -> bool:
        """若同格仍有应先执行的动作，则当前动作暂不进入路线。"""
        rank = cls._route_action_rank(task)
        return any(
            other.chain_id == task.chain_id
            and cls._route_action_rank(other) < rank
            for other in remaining
        )

    @staticmethod
    def _route_harvest_payload(state: CanonicalState, task: Task) -> tuple[str, int] | None:
        """从当前合法地块估计收获后背包变化，不预测未来产量。"""
        if task.action[0] != "HARVEST":
            return None
        tile = state.grid[task.y][task.x]
        if not isinstance(tile, Mapping):
            return None
        units = max(0, integer(tile.get("yield_units")))
        if units <= 0:
            return None
        if tile.get("kind") == "PLANT":
            item = str(tile.get("crop") or "")
        else:
            item = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}.get(
                animal_kind(tile) or "", "",
            )
        return (item, units) if item in PRODUCTS else None

    @classmethod
    def _route_transition(cls, inventory: dict[str, int], task: Task,
                          state: CanonicalState) -> None:
        """应用当前动作的确定性背包转移。"""
        cls._route_consume(inventory, task)
        payload = cls._route_harvest_payload(state, task)
        if payload is not None:
            item, units = payload
            inventory[item] = int(inventory.get(item, 0)) + units
        elif task.action[0] == "COLLECT_FERTILIZER":
            inventory["FERTILIZER"] = int(inventory.get("FERTILIZER", 0)) + 1

    @staticmethod
    def _route_inventory_value(inventory: Mapping[str, int],
                               state: CanonicalState) -> int:
        return sum(
            max(0, integer(quantity)) * integer(state.prices.get(item))
            for item, quantity in inventory.items() if item in PRODUCTS
        )

    def _build_rolling_routes(self, state: CanonicalState, contract: DailyContract,
                              tasks: Sequence[Task], actors: Sequence[int]) \
            -> dict[int, list[tuple[Any, ...]]]:
        """E3：用当前合法任务做短视窗多工人路线拍卖，不预测未来 Replay。"""
        horizon = int(self.tuning.rolling_route_horizon)
        slack = int(self.tuning.rolling_route_priority_slack)
        routes: dict[int, list[tuple[Any, ...]]] = {actor: [] for actor in actors}
        positions = {actor: state.positions[actor] for actor in actors}
        inventories = {actor: dict(state.inventories[actor]) for actor in actors}
        elapsed = {actor: 0 for actor in actors}
        remaining = list(tasks)
        stage = max(1, int(contract.lands))
        transition_aware = bool(self.tuning.transition_aware_route_enabled)
        chain_owner: dict[str, int] = {}

        while remaining:
            feasible_pairs: list[tuple[int, int, int, Task, float]] = []
            for task_index, task in enumerate(remaining):
                if transition_aware and self._route_predecessors_pending(task, remaining):
                    continue
                for actor in actors:
                    if len(routes[actor]) >= horizon:
                        continue
                    if transition_aware and chain_owner.get(task.chain_id, actor) != actor:
                        continue
                    if not self._route_task_feasible(inventories[actor], task):
                        continue
                    travel = distance(positions[actor], (task.x, task.y))
                    finish = elapsed[actor] + travel + 1
                    if transition_aware and state.hour + finish > 24:
                        continue
                    late = max(0, state.hour + finish - task.deadline)
                    role = self.roles.setdefault((stage, actor), actor % stage)
                    role_cost = (
                        self.tuning.role_penalty
                        if quadrant((task.x, task.y)) != role else 0.0
                    )
                    cost = (
                        travel * self.tuning.travel_weight
                        + elapsed[actor] * self.tuning.rolling_route_load_weight
                        + late * self.tuning.deadline_penalty
                        + role_cost
                        - task.value
                    )
                    if transition_aware:
                        projected = dict(inventories[actor])
                        self._route_transition(projected, task, state)
                        delivery_burden = (
                            self._route_inventory_value(projected, state)
                            * distance((task.x, task.y), shed_gate((task.x, task.y)))
                            * self.tuning.rolling_route_delivery_weight
                        )
                        cost += delivery_burden
                    feasible_pairs.append((task.priority, task_index, actor, task, cost))
            if not feasible_pairs:
                break
            best_priority = min(row[0] for row in feasible_pairs)
            admitted = [row for row in feasible_pairs if row[0] <= best_priority + slack]
            _, task_index, actor, task, _ = min(
                admitted,
                key=lambda row: (
                    row[4], len(routes[row[2]]), row[2], row[3].deadline,
                    row[3].y, row[3].x, row[3].action,
                ),
            )
            travel = distance(positions[actor], (task.x, task.y))
            routes[actor].append(task.key)
            positions[actor] = (task.x, task.y)
            elapsed[actor] += travel + 1
            if transition_aware:
                chain_owner.setdefault(task.chain_id, actor)
                self._route_transition(inventories[actor], task, state)
                self.audit["transition_route_actions"] += 1
            else:
                self._route_consume(inventories[actor], task)
            remaining.pop(task_index)

        self.audit["rolling_route_plans"] += 1
        self.audit["rolling_route_planned_tasks"] += sum(map(len, routes.values()))
        self.audit["rolling_route_unplanned_tasks"] += len(remaining)
        self.audit["transition_route_plans"] += int(transition_aware)
        return routes

    def _assign_rolling_routes(self, state: CanonicalState, contract: DailyContract,
                               tasks: Sequence[Task], actors: Sequence[int],
                               unavailable: set[int]) -> dict[int, Task]:
        available = [actor for actor in actors if actor not in unavailable]
        if not available or not tasks:
            return {}
        signature = (state.day, len(state.positions), tuple(sorted(unavailable)))
        replan = (
            self.rolling_route_signature != signature
            or state.step >= self.rolling_route_next_replan
        )
        task_by_key = {task.key: task for task in tasks}
        if not replan:
            for actor in available:
                route = self.rolling_routes.get(actor, [])
                while route and (
                    route[0] not in task_by_key
                    or not self._route_task_feasible(
                        state.inventories[actor], task_by_key[route[0]]
                    )
                ):
                    route.pop(0)
                    self.audit["rolling_route_stale_steps"] += 1
                if not route:
                    replan = True
                    break
        if replan:
            self.rolling_routes = self._build_rolling_routes(
                state, contract, tasks, available,
            )
            self.rolling_route_signature = signature
            self.rolling_route_next_replan = (
                state.step + int(self.tuning.rolling_route_replan_interval)
            )
            task_by_key = {task.key: task for task in tasks}

        result: dict[int, Task] = {}
        claimed: set[tuple[Any, ...]] = set()
        for actor in available:
            route = self.rolling_routes.get(actor, [])
            while route and route[0] not in task_by_key:
                route.pop(0)
                self.audit["rolling_route_stale_steps"] += 1
            if not route or route[0] in claimed:
                continue
            task = task_by_key[route[0]]
            if not self._route_task_feasible(state.inventories[actor], task):
                continue
            result[actor] = task
            claimed.add(route[0])
            self.audit["rolling_route_assignments"] += 1
        return result

    def assign(self, state: CanonicalState, contract: DailyContract, tasks: Sequence[Task],
               unavailable: set[int]) -> dict[int, Task]:
        self._rebalance_roles(state, contract, tasks, list(range(len(state.positions))))
        actors = [index for index in range(len(state.positions)) if index not in unavailable]
        if not actors or not tasks:
            return {}
        if self.tuning.terminal_local_route_enabled and state.remaining_steps <= 24:
            self.audit["terminal_local_route_turns"] += 1
            return self._assign_local_routes(state, contract, tasks, actors)
        if self.tuning.rolling_route_enabled:
            return self._assign_rolling_routes(
                state, contract, tasks, list(range(len(state.positions))), unavailable,
            )
        result: dict[int, Task] = {}
        remaining_tasks = list(tasks)
        if self.tuning.inflight_task_lock_enabled:
            # 只锁定尚未抵达的原任务；到达后立刻释放给全局分配器。
            # 这避免每回合 Hungarian 因任务池变化让 actor 在半路反复换目标，
            # 同时不会像整条 chain 锁那样阻止同格多动作的重新排序。
            for actor in list(actors):
                signature = self.sticky_task.get(actor)
                if signature is None:
                    continue
                matching = [
                    task for task in remaining_tasks
                    if (task.x, task.y, task.action) == signature
                    and state.positions[actor] != (task.x, task.y)
                    and self._task_cost(
                        actor, state.positions[actor], state.inventories[actor], task,
                        state, contract,
                    ) < 1e8
                ]
                if not matching:
                    continue
                locked = min(matching, key=lambda task: (
                    task.priority, task.deadline, -task.value, task.action,
                ))
                urgent_elsewhere = any(
                    task.chain_id != locked.chain_id
                    and task.priority <= int(self.tuning.inflight_task_preempt_priority)
                    and task.priority < locked.priority
                    for task in remaining_tasks
                )
                if urgent_elsewhere:
                    self.audit["inflight_task_preemption"] += 1
                    continue
                result[actor] = locked
                actors.remove(actor)
                remaining_tasks.remove(locked)
                self.audit["inflight_task_lock_assignment"] += 1
        if self.tuning.animal_service_session_enabled:
            service_order = {
                "FEED": 0,
                "HARVEST": 1,
                "COLLECT_FERTILIZER": 2,
                "CARE": 3,
            }
            # 只有已经到达动物格且上一回合仍属于该格的 actor 才获得会话锁。
            # 会话最多覆盖该动物当日四个原子动作，不跨格、不读取未来状态。
            for actor in list(actors):
                chain = self.sticky_chain.get(actor)
                position = state.positions[actor]
                x, y = position
                if not chain or animal_kind(state.grid[y][x]) is None:
                    continue
                session = self.animal_service_sessions.get(actor)
                steps = session[2] if session and session[:2] == (state.day, chain) else 0
                if steps >= int(self.tuning.animal_service_max_steps):
                    continue
                matching = [
                    task for task in remaining_tasks
                    if task.chain_id == chain
                    and (task.x, task.y) == position
                    and str(task.action[0]) in service_order
                    and self._task_cost(
                        actor, position, state.inventories[actor], task, state, contract,
                    ) < 1e8
                ]
                if not matching:
                    continue
                chosen = min(matching, key=lambda task: (
                    service_order[str(task.action[0])], task.priority,
                    task.deadline, -task.value, task.action,
                ))
                preempt_priority = int(self.tuning.animal_service_preempt_priority)
                urgent_elsewhere = preempt_priority >= 0 and any(
                    task.chain_id != chain
                    and task.priority <= preempt_priority
                    and task.priority < chosen.priority
                    for task in remaining_tasks
                )
                if urgent_elsewhere:
                    self.audit["animal_service_session_preemption"] += 1
                    continue
                result[actor] = chosen
                actors.remove(actor)
                remaining_tasks.remove(chosen)
                self.audit["animal_service_session_assignment"] += 1
        if self.tuning.persistent_lock_enabled:
            for actor in list(actors):
                chain = self.sticky_chain.get(actor)
                if not chain:
                    continue
                matching = [
                    task for task in remaining_tasks
                    if task.chain_id == chain
                    and task.priority <= self.tuning.persistent_lock_max_priority
                    and distance(state.positions[actor], (task.x, task.y)) <= self.tuning.persistent_lock_radius
                    and self._task_cost(
                        actor, state.positions[actor], state.inventories[actor], task, state, contract,
                    ) < 1e8
                ]
                if not matching:
                    continue
                locked = min(matching, key=lambda task: self._task_cost(
                    actor, state.positions[actor], state.inventories[actor], task, state, contract,
                ))
                urgent_elsewhere = any(
                    task.chain_id != chain
                    and task.priority <= self.tuning.persistent_preempt_priority
                    and task.priority < locked.priority
                    for task in remaining_tasks
                )
                if urgent_elsewhere:
                    self.audit["persistent_preemption"] += 1
                    continue
                result[actor] = locked
                actors.remove(actor)
                remaining_tasks.remove(locked)
                self.audit["persistent_lock_assignment"] += 1
        if not actors or not remaining_tasks:
            return result
        if self.tuning.local_route_queue_enabled:
            result.update(self._assign_local_routes(
                state, contract, remaining_tasks, actors,
            ))
            return result
        # 只保留全局最紧迫的一组候选，避免大量重复任务拖慢 1 秒时限。
        candidate_count = max(
            len(actors), min(len(remaining_tasks), self.tuning.candidate_cap),
        )
        if self.tuning.stratified_candidate_pool_enabled:
            candidates = self._stratified_candidates(remaining_tasks, candidate_count)
            self.audit["stratified_candidate_pool_turns"] += 1
            self.audit["stratified_candidate_pool_source_tasks"] += len(remaining_tasks)
            self.audit["stratified_candidate_pool_selected"] += len(candidates)
            self.audit["stratified_candidate_pool_batches"] += len({
                task.batch_key for task in candidates
            })
        else:
            candidates = list(remaining_tasks[:candidate_count])
        dummy_count = max(0, len(actors) - len(candidates))
        columns: list[Task | None] = candidates + [None] * dummy_count
        matrix: list[list[float]] = []
        for actor in actors:
            row = [self._task_cost(actor, state.positions[actor], state.inventories[actor], task, state, contract)
                   if task is not None else 1e8 for task in columns]
            matrix.append(row)
        chosen = self._hungarian(matrix)
        for row_index, (actor, column) in enumerate(zip(actors, chosen)):
            if 0 <= column < len(columns) and columns[column] is not None and matrix[row_index][column] < 1e8:
                result[actor] = columns[column]  # type: ignore[assignment]
        if self.tuning.work_conserving_second_pass_enabled:
            # 首轮候选池可能被同类紧急任务占满，但部分 actor 因缺少饲料/肥料而
            # 无法执行，最终在仍有 WATER/CARE/HARVEST 等合法任务时 PASS。
            # 二次分配只利用当前 observation 中未占用的任务，并受优先级和距离
            # 双重限制；不跨日规划，也不读取未来 Replay。
            claimed = {task.key for task in result.values()}
            max_priority = int(self.tuning.work_conserving_max_priority)
            max_distance = int(self.tuning.work_conserving_max_distance)
            for actor in actors:
                if actor in result:
                    continue
                position = state.positions[actor]
                feasible = [
                    task for task in remaining_tasks
                    if task.key not in claimed
                    and task.priority <= max_priority
                    and distance(position, (task.x, task.y)) <= max_distance
                    and self._task_cost(
                        actor, position, state.inventories[actor], task,
                        state, contract,
                    ) < 1e8
                ]
                if not feasible:
                    self.audit["work_conserving_second_pass_miss"] += 1
                    continue
                best_priority = min(task.priority for task in feasible)
                admitted = [task for task in feasible if task.priority == best_priority]
                task = min(admitted, key=lambda item: (
                    self._task_cost(
                        actor, position, state.inventories[actor], item,
                        state, contract,
                    ),
                    item.deadline, -item.value, item.y, item.x, item.action,
                ))
                result[actor] = task
                claimed.add(task.key)
                self.audit["work_conserving_second_pass_assignment"] += 1
        self.audit["hungarian_calls"] += 1
        return result

    def _assign_local_routes(self, state: CanonicalState, contract: DailyContract,
                             tasks: Sequence[Task], actors: Sequence[int]) -> dict[int, Task]:
        """E3b：先完成当前地块链，再在固定责任区内走最近下一站。"""

        remaining = list(tasks)
        result: dict[int, Task] = {}
        stage = max(1, int(contract.lands))
        global_urgent = min((task.priority for task in remaining), default=9)

        # 已经在途的地块只在出现更紧急任务时被抢占，避免每回合重新规划目标。
        for actor in actors:
            chain = self.sticky_chain.get(actor)
            if not chain:
                continue
            feasible = [
                task for task in remaining
                if task.chain_id == chain
                and self._task_cost(
                    actor, state.positions[actor], state.inventories[actor], task, state, contract,
                ) < 1e8
            ]
            if not feasible:
                continue
            chosen = min(feasible, key=lambda task: (
                task.priority, task.deadline, -task.value, task.action,
            ))
            if global_urgent < chosen.priority:
                self.audit["local_route_preemption"] += 1
                continue
            result[actor] = chosen
            remaining.remove(chosen)
            self.audit["local_route_same_chain"] += 1

        # 空闲 actor 在自己的象限内走最近下一站；责任区无任务时才允许溢出。
        for actor in actors:
            if actor in result or not remaining:
                continue
            role = self.roles.setdefault((stage, actor), actor % stage)
            feasible = [
                task for task in remaining
                if self._task_cost(
                    actor, state.positions[actor], state.inventories[actor], task, state, contract,
                ) < 1e8
            ]
            if not feasible:
                continue
            local = [task for task in feasible if quadrant((task.x, task.y)) == role]
            pool = local or (feasible if self.tuning.local_route_spill_enabled else [])
            if not pool:
                continue
            best_priority = min(task.priority for task in pool)
            admitted = [
                task for task in pool
                if task.priority <= best_priority + int(self.tuning.local_route_priority_slack)
            ]
            chosen = min(admitted, key=lambda task: (
                distance(state.positions[actor], (task.x, task.y)),
                task.priority, task.deadline, -task.value,
                task.y, task.x, task.action,
            ))
            result[actor] = chosen
            remaining.remove(chosen)
            self.audit["local_route_assignment"] += 1
            self.audit["local_route_spill"] += int(not local)
        self.audit["local_route_calls"] += 1
        return result

    def inventory_actions(self, state: CanonicalState, contract: DailyContract,
                          tasks: Sequence[Task]) -> dict[int, list[Any]]:
        actions: dict[int, list[Any]] = {}
        carried = inventory_total(state.inventories)
        feed_tasks = sum(task.action[0] == "FEED" for task in tasks)
        if feed_tasks > carried["WHEAT"] and state.shed.get("WHEAT", 0) > 0:
            if self.tuning.multi_feed_runner_enabled:
                existing_runners = sum(inventory.get("WHEAT", 0) > 0 for inventory in state.inventories)
                desired_runners = min(
                    int(self.tuning.feed_runner_cap),
                    (feed_tasks + int(self.tuning.feed_units_per_runner) - 1)
                    // int(self.tuning.feed_units_per_runner),
                )
                runner_gap = max(0, desired_runners - existing_runners)
                remaining = min(feed_tasks - carried["WHEAT"], state.shed["WHEAT"])
                stage = max(1, int(contract.lands))
                candidates = sorted(
                    (
                        index for index, inventory in enumerate(state.inventories)
                        if inventory.get("WHEAT", 0) <= 0
                    ),
                    key=lambda index: (
                        self.roles.get((stage, index), index % stage) != 0,
                        distance(state.positions[index], shed_gate(state.positions[index])),
                        index,
                    ),
                )
                for actor in candidates[:runner_gap]:
                    if remaining <= 0:
                        break
                    position = state.positions[actor]
                    if position in SHED_TILES:
                        quantity = min(int(self.tuning.feed_units_per_runner), remaining)
                        actions[actor] = ["PICKUP", "WHEAT", quantity]
                        remaining -= quantity
                        self.audit["feed_runner_pickup"] += 1
                        self.audit["feed_runner_units"] += quantity
                    else:
                        actions[actor] = path_toward(state.grid, position, shed_gate(position), actor)
                        self.audit["feed_runner_return"] += 1
            else:
                actor = min(
                    range(len(state.positions)),
                    key=lambda index: distance(state.positions[index], shed_gate(state.positions[index])),
                )
                position = state.positions[actor]
                actions[actor] = (
                    ["PICKUP", "WHEAT", min(feed_tasks - carried["WHEAT"], state.shed["WHEAT"])]
                    if position in SHED_TILES else path_toward(state.grid, position, shed_gate(position), actor)
                )
        if self.tuning.multi_animal_runner_enabled:
            for animal in ANIMALS:
                place_tasks = sum(
                    task.action[0] == "PLACE" and len(task.action) > 1 and task.action[1] == animal
                    for task in tasks
                )
                carried_units = sum(inventory.get(animal, 0) for inventory in state.inventories)
                available = min(
                    max(0, place_tasks - carried_units),
                    max(0, state.shed.get(animal, 0)),
                )
                if available <= 0:
                    continue
                existing_runners = sum(inventory.get(animal, 0) > 0 for inventory in state.inventories)
                desired_runners = min(
                    int(self.tuning.animal_runner_cap),
                    math.ceil(place_tasks / int(self.tuning.animal_units_per_runner)),
                )
                runner_gap = max(0, desired_runners - existing_runners)
                candidates = sorted(
                    (
                        index for index, inventory in enumerate(state.inventories)
                        if index not in actions and inventory.get(animal, 0) <= 0
                    ),
                    key=lambda index: (
                        distance(state.positions[index], shed_gate(state.positions[index])), index,
                    ),
                )
                for actor in candidates[:runner_gap]:
                    if available <= 0:
                        break
                    position = state.positions[actor]
                    if position in SHED_TILES:
                        quantity = min(int(self.tuning.animal_units_per_runner), available)
                        actions[actor] = ["PICKUP", animal, quantity]
                        available -= quantity
                        self.audit["animal_runner_pickup"] += 1
                        self.audit["animal_runner_units"] += quantity
                    else:
                        actions[actor] = path_toward(state.grid, position, shed_gate(position), actor)
                        self.audit["animal_runner_return"] += 1
        else:
            for task in tasks:
                if task.action[0] != "PLACE":
                    continue
                animal = str(task.action[1])
                if carried[animal] > 0 or state.shed.get(animal, 0) <= 0:
                    continue
                candidates = [index for index in range(len(state.positions)) if index not in actions]
                if candidates:
                    actor = min(candidates, key=lambda index: distance(state.positions[index], shed_gate(state.positions[index])))
                    position = state.positions[actor]
                    actions[actor] = (["PICKUP", animal, 1] if position in SHED_TILES
                                      else path_toward(state.grid, position, shed_gate(position), actor))
                break
        fertilize_tasks = sum(task.action[0] == "FERTILIZE" for task in tasks)
        fertilizer_carried = carried["FERTILIZER"]
        if fertilize_tasks > fertilizer_carried and state.shed.get("FERTILIZER", 0) > 0:
            candidates = [index for index in range(len(state.positions)) if index not in actions]
            if candidates:
                actor = min(
                    candidates,
                    key=lambda index: distance(state.positions[index], shed_gate(state.positions[index])),
                )
                position = state.positions[actor]
                quantity = min(
                    fertilize_tasks - fertilizer_carried,
                    state.shed["FERTILIZER"],
                    12,
                )
                actions[actor] = (
                    ["PICKUP", "FERTILIZER", quantity]
                    if position in SHED_TILES
                    else path_toward(state.grid, position, shed_gate(position), actor)
                )
        # M1 日内现金闭环：只有现金确实偏低、背包产物达到价值阈值且仓容可接收时，
        # 才占用一个 actor 返仓。日末引擎会自动落仓，因此不做无条件往返。
        delivery_threshold = int(self.tuning.delivery_value_threshold)
        if (self.tuning.opening_delivery_value_threshold > 0
                and state.day >= int(self.tuning.opening_delivery_start_day)
                and state.day <= int(self.tuning.opening_delivery_until_day)):
            delivery_threshold = int(self.tuning.opening_delivery_value_threshold)
            self.audit["opening_delivery_window_turns"] += 1
        if (delivery_threshold > 0
                and state.money < self.tuning.delivery_cash_ceiling
                and state.hour <= int(self.tuning.delivery_cutoff_hour)):
            shed_room = max(0, SHED_CAPACITY - state.shed_used)
            candidates: list[tuple[float, int, int]] = []
            for actor, (position, inventory) in enumerate(zip(state.positions, state.inventories)):
                if actor in actions:
                    continue
                carried_units = sum(max(0, int(value)) for value in inventory.values())
                sale_value = sum(
                    max(0, int(quantity)) * state.prices.get(item, 0)
                    for item, quantity in inventory.items() if item in PRODUCTS
                )
                # DROP 是全背包动作；不能把仍在执行的饲料、动物或肥料链一并卸下。
                protected = (
                    (feed_tasks > 0 and inventory.get("WHEAT", 0) > 0)
                    or (fertilize_tasks > 0 and inventory.get("FERTILIZER", 0) > 0)
                    or any(task.action[0] == "PLACE" and inventory.get(str(task.action[1]), 0) > 0
                           for task in tasks if len(task.action) > 1)
                )
                if (protected or carried_units <= 0 or carried_units > shed_room
                        or sale_value < delivery_threshold):
                    continue
                trip = distance(position, shed_gate(position))
                if trip > int(self.tuning.delivery_max_distance):
                    self.audit["delivery_rejected_by_distance"] += 1
                    continue
                candidates.append((float(sale_value) - 25.0 * trip, actor, trip))
            if candidates:
                cap = min(int(self.tuning.delivery_runner_cap), len(candidates))
                ranked = sorted(
                    candidates, key=lambda row: (row[0], -row[1]), reverse=True,
                )
                selected: list[tuple[float, int, int]] = []
                locked = next((row for row in candidates if row[1] == self.delivery_runner), None)
                if self.tuning.persistent_delivery_runner_enabled and locked is not None:
                    selected.append(locked)
                    self.audit["delivery_runner_reused"] += 1
                selected.extend(
                    row for row in ranked
                    if row not in selected
                )
                selected = selected[:cap]
                if self.tuning.persistent_delivery_runner_enabled and locked is None:
                    self.delivery_runner = selected[0][1]
                    self.audit["delivery_runner_started"] += 1
                for _, actor, trip in selected:
                    position = state.positions[actor]
                    actions[actor] = (
                        ["DROP"] if position in SHED_TILES
                        else path_toward(state.grid, position, shed_gate(position), actor)
                    )
                    self.audit["delivery_drop" if position in SHED_TILES else "delivery_return"] += 1
                    self.audit[f"delivery_distance_{trip}"] += 1
                    self.audit[f"delivery_hour_{state.hour}"] += 1
                self.audit["delivery_parallel_assignments"] += len(selected)
            elif self.tuning.persistent_delivery_runner_enabled:
                self.delivery_runner = None
        elif self.tuning.persistent_delivery_runner_enabled:
            self.delivery_runner = None
        return actions

    def act(self, state: CanonicalState, contract: DailyContract,
            feedback: RuntimeFeedback) -> ExecutorResult:
        tasks = self.tasks(state, contract, feedback)
        synthetic = self.inventory_actions(state, contract, tasks)
        prior_chains = dict(self.sticky_chain)
        assignments = self.assign(state, contract, tasks, set(synthetic))
        for actor in range(len(state.positions)):
            if actor in synthetic or actor in assignments:
                continue
            if not tasks:
                self.audit["idle_reason_no_tasks"] += 1
                continue
            feasible = any(
                self._task_cost(
                    actor, state.positions[actor], state.inventories[actor], task,
                    state, contract,
                ) < 1e8
                for task in tasks
            )
            self.audit[
                "idle_reason_assignable_but_unassigned"
                if feasible else "idle_reason_no_feasible_task"
            ] += 1
        verbs: list[tuple[Any, ...]] = []
        pending_plants: Counter[str] = Counter()
        actor_tasks: list[str | None] = []
        actor_targets: list[tuple[int, int] | None] = []
        overdue = sum(int(state.hour > task.deadline) for task in tasks)
        overdue_details = tuple({
            "signature": f"{task.chain_id}:{task.action[0]}:{task.x}:{task.y}:{task.deadline}",
            "verb": str(task.action[0]),
            "x": int(task.x),
            "y": int(task.y),
            "deadline": int(task.deadline),
            "task_value": float(task.value),
            "estimated_value": max(LABOR_STEP_VALUE, float(task.value) * LABOR_STEP_VALUE),
        } for task in tasks if state.hour > task.deadline)
        roles: list[int] = []
        for actor, position in enumerate(state.positions):
            roles.append(self.roles.setdefault((max(1, contract.lands), actor), actor % max(1, contract.lands)))
            task = assignments.get(actor)
            if actor in synthetic:
                verb = tuple(synthetic[actor])
                actor_tasks.append("inventory")
                actor_targets.append(shed_gate(position))
            elif task is not None:
                self.sticky_chain[actor] = task.chain_id
                self.sticky_task[actor] = (task.x, task.y, task.action)
                self.audit["assignment_distance"] += distance(position, (task.x, task.y))
                self.audit["assignment_sticky"] += int(prior_chains.get(actor) == task.chain_id)
                self.audit["assignment_switch"] += int(
                    prior_chains.get(actor) is not None and prior_chains.get(actor) != task.chain_id
                )
                verb = task.action if position == (task.x, task.y) else tuple(path_toward(state.grid, position, (task.x, task.y), actor))
                actor_tasks.append(task.chain_id)
                actor_targets.append((task.x, task.y))
                if (self.tuning.animal_service_session_enabled
                        and position == (task.x, task.y)
                        and animal_kind(state.grid[task.y][task.x]) is not None
                        and str(task.action[0]) in {
                            "FEED", "HARVEST", "COLLECT_FERTILIZER", "CARE",
                        }):
                    previous = self.animal_service_sessions.get(actor)
                    steps = previous[2] if previous and previous[:2] == (state.day, task.chain_id) else 0
                    self.animal_service_sessions[actor] = (
                        state.day, task.chain_id,
                        min(int(self.tuning.animal_service_max_steps), steps + 1),
                    )
                    self.audit["animal_service_session_step"] += 1
            else:
                self.sticky_chain.pop(actor, None)
                self.sticky_task.pop(actor, None)
                self.animal_service_sessions.pop(actor, None)
                verb = tuple(PASS)
                actor_tasks.append(None)
                actor_targets.append(None)
            if verb and verb[0] == "PLANT" and len(verb) > 1:
                pending_plants[str(verb[1])] += 1
            op = str(verb[0]) if verb else "INVALID"
            self.audit[f"unit_{op.lower()}"] += 1
            if op in {"NORTH", "SOUTH", "EAST", "WEST"}:
                self.audit["move"] += 1
            elif op == "PASS":
                self.audit["idle"] += 1
            else:
                self.audit["productive"] += 1
            verbs.append(verb)
        self.audit["overdue_tasks"] += overdue
        return ExecutorResult(
            tuple(verbs), dict(pending_plants), tuple(actor_tasks), tuple(roles), overdue,
            tuple(actor_targets), overdue_details,
        )
