"""R2.1-A 七类可观测损失归因账本。

这些数值是用于比较模块的保守机会损失代理，不是模拟器真实扣款，也不能相加后冒充
反事实金币差。运行时只读取当前/历史已发生状态、当前合同和本模型动作；不读取 seed、
Replay 身份、未来商店、未来价格、历史玩家动作或最终评测标签。
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from contracts import DailyContract
from schema import (BASE_PRICE, CROP_FACTS, SEED_COST, CanonicalState, animal_kind,
                    integer, inventory_total, shed_gate)


LOSS_CATEGORIES = (
    "FINANCING_SHORTFALL",
    "MISSED_HIGH_PRICE_SALE",
    "FEED_SHORTAGE",
    "OVERDUE_TASK",
    "UNPRODUCTIVE_MOVE",
    "INVENTORY_OVERHANG",
    "TERMINAL_UNREALIZED",
)

CATEGORY_LABELS = {
    "FINANCING_SHORTFALL": "融资不足",
    "MISSED_HIGH_PRICE_SALE": "错失高价销售",
    "FEED_SHORTAGE": "饲料短缺",
    "OVERDUE_TASK": "任务逾期",
    "UNPRODUCTIVE_MOVE": "无效移动",
    "INVENTORY_OVERHANG": "库存积压",
    "TERMINAL_UNREALIZED": "终局未兑现",
}

CATEGORY_DEFINITIONS = {
    "FINANCING_SHORTFALL": "同一日内合同允许采购额相对售后可用现金和现金储备的最大缺口，只取日峰值",
    "MISSED_HIGH_PRICE_SALE": "高于合同销售底价且未售出的可售库存，在下一已观察状态发生价格下跌后的价差",
    "FEED_SHORTAGE": "日末未喂动物中，即使把剩余小麦优先配置给高价值动物仍无法覆盖的最低产出价值",
    "OVERDUE_TASK": "超过合同截止时间的唯一任务，按任务价值乘保守劳动步价值估计并按日去重",
    "UNPRODUCTIVE_MOVE": "移动后位置未变化，或到已分配目标的可达最短距离没有缩短",
    "INVENTORY_OVERHANG": "超过合同储备且从日初持续到下一日的库存，按每日5%保守持有成本估计",
    "TERMINAL_UNREALIZED": "最终动作后仍未出售的商品、未使用种子和地块上可收获产出的当前可见价值",
}

MOVE_OPS = {"NORTH", "SOUTH", "EAST", "WEST"}
LABOR_STEP_VALUE = 25.0
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}


@dataclass(frozen=True)
class LossEvent:
    step: int
    day: int
    expert_id: str | None
    category: str
    estimated_value: float
    units: float
    reason: str
    details: Mapping[str, Any]


@dataclass(frozen=True)
class PendingMove:
    actor: int
    source: tuple[int, int]
    target: tuple[int, int] | None
    task_key: str | None
    grid: tuple[tuple[Any, ...], ...]


class LossAttributionLedger:
    """逐 seat、逐 episode 的诊断账本；生产策略不能读取其结果。"""

    def __init__(self) -> None:
        self.current_day = -1
        self.current_expert: str | None = None
        self.totals: Counter[str] = Counter()
        self.units: Counter[str] = Counter()
        self.event_counts: Counter[str] = Counter()
        self.by_day: dict[int, Counter[str]] = {}
        self.events: deque[LossEvent] = deque(maxlen=512)
        self.pending_moves: tuple[PendingMove, ...] = ()
        self.pending_high_price: dict[str, tuple[int, int]] = {}
        self.day_start_excess: dict[str, int] | None = None
        self.day_reserves: dict[str, int] = {}
        self.finance_peak = 0.0
        self.finance_peak_details: dict[str, Any] = {}
        self.seen_overdue: set[str] = set()
        self.feed_recorded_days: set[int] = set()
        self.terminal_recorded = False

    @staticmethod
    def _all_inventory(state: CanonicalState) -> Counter[str]:
        total = Counter({str(item): max(0, int(value)) for item, value in state.shed.items()})
        total.update(inventory_total(state.inventories))
        return total

    @classmethod
    def _excess_inventory(cls, state: CanonicalState, reserves: Mapping[str, int]) -> dict[str, int]:
        total = cls._all_inventory(state)
        return {
            item: max(0, int(quantity) - max(0, int(reserves.get(item, 0))))
            for item, quantity in total.items()
            if int(quantity) > max(0, int(reserves.get(item, 0)))
        }

    @staticmethod
    def _grid_distance(grid: Sequence[Sequence[Any]], source: tuple[int, int],
                       target: tuple[int, int]) -> int | None:
        if source == target:
            return 0
        queue: deque[tuple[tuple[int, int], int]] = deque([(source, 0)])
        visited = {source}
        while queue:
            (x, y), travelled = queue.popleft()
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                nx, ny = x + dx, y + dy
                position = (nx, ny)
                if position in visited or ny < 0 or ny >= len(grid) or nx < 0 or nx >= len(grid[ny]):
                    continue
                if grid[ny][nx] == "LOCKED":
                    continue
                if position == target:
                    return travelled + 1
                visited.add(position)
                queue.append((position, travelled + 1))
        return None

    def _record(self, state: CanonicalState, category: str, estimated_value: float,
                units: float, reason: str, details: Mapping[str, Any] | None = None,
                expert_id: str | None = None) -> None:
        if category not in LOSS_CATEGORIES or estimated_value <= 0:
            return
        value = float(estimated_value)
        quantity = max(0.0, float(units))
        event = LossEvent(
            step=int(state.step), day=int(state.day),
            expert_id=expert_id if expert_id is not None else self.current_expert,
            category=category, estimated_value=value, units=quantity,
            reason=str(reason), details=dict(details or {}),
        )
        self.events.append(event)
        self.totals[category] += value
        self.units[category] += quantity
        self.event_counts[category] += 1
        self.by_day.setdefault(int(state.day), Counter())[category] += value

    def _flush_finance(self, state: CanonicalState, day: int) -> None:
        if self.finance_peak > 0:
            proxy = CanonicalStateProxy(state, day)
            self._record(proxy, "FINANCING_SHORTFALL", self.finance_peak, 1.0,
                         "DAILY_MAX_CAPITAL_GAP", self.finance_peak_details)
        self.finance_peak = 0.0
        self.finance_peak_details = {}

    def _reconcile_moves(self, state: CanonicalState) -> None:
        for pending in self.pending_moves:
            if pending.actor >= len(state.positions):
                continue
            arrived = state.positions[pending.actor]
            reason: str | None = None
            before: int | None = None
            after: int | None = None
            if arrived == pending.source:
                reason = "BLOCKED_OR_NO_POSITION_CHANGE"
            elif pending.target is None:
                reason = "MOVE_WITHOUT_ASSIGNED_TARGET"
            else:
                before = self._grid_distance(pending.grid, pending.source, pending.target)
                after = self._grid_distance(pending.grid, arrived, pending.target)
                if before is not None and after is not None and after >= before:
                    reason = "TARGET_DISTANCE_NOT_REDUCED"
            if reason:
                self._record(
                    state, "UNPRODUCTIVE_MOVE", LABOR_STEP_VALUE, 1.0, reason,
                    {"actor": pending.actor, "source": list(pending.source),
                     "arrived": list(arrived), "target": list(pending.target) if pending.target else None,
                     "distance_before": before, "distance_after": after,
                     "task_key": pending.task_key},
                )
        self.pending_moves = ()

    def _reconcile_high_price(self, state: CanonicalState) -> None:
        inventory = self._all_inventory(state)
        for item, (prior_price, exposed_units) in self.pending_high_price.items():
            current_price = int(state.prices.get(item, prior_price))
            drop = max(0, int(prior_price) - current_price)
            remaining = min(max(0, int(exposed_units)), max(0, int(inventory.get(item, 0))))
            if drop and remaining:
                self._record(
                    state, "MISSED_HIGH_PRICE_SALE", remaining * drop, remaining,
                    "OBSERVED_PRICE_DROP_ON_PRIOR_SALEABLE_INVENTORY",
                    {"item": item, "prior_price": prior_price, "current_price": current_price,
                     "price_drop": drop, "remaining_units": remaining},
                )
        self.pending_high_price = {}

    def _record_inventory_overhang(self, state: CanonicalState, attributed_day: int) -> None:
        if self.day_start_excess is None:
            return
        current = self._excess_inventory(state, self.day_reserves)
        persisted = {
            item: min(max(0, int(quantity)), max(0, int(current.get(item, 0))))
            for item, quantity in self.day_start_excess.items()
        }
        persisted = {item: quantity for item, quantity in persisted.items() if quantity > 0}
        amount = sum(quantity * max(1.0, BASE_PRICE.get(item, 1) * 0.05)
                     for item, quantity in persisted.items())
        if amount:
            proxy = CanonicalStateProxy(state, attributed_day)
            self._record(
                proxy, "INVENTORY_OVERHANG", amount, sum(persisted.values()),
                "EXCESS_INVENTORY_PERSISTED_ACROSS_DAY",
                {"items": persisted, "daily_holding_rate": 0.05},
            )

    def observe(self, state: CanonicalState) -> None:
        """在策略决策前对上一动作进行事后核验；只处理已经发生的信息。"""

        self._reconcile_moves(state)
        self._reconcile_high_price(state)
        if self.current_day < 0:
            self.current_day = int(state.day)
        elif int(state.day) != self.current_day:
            self._flush_finance(state, self.current_day)
            self._record_inventory_overhang(state, self.current_day)
            self.current_day = int(state.day)
            self.day_start_excess = None
            self.day_reserves = {}
            self.seen_overdue = {key for key in self.seen_overdue if key.startswith(f"{state.day}:")}

    @staticmethod
    def _unfed_animals(state: CanonicalState) -> list[tuple[tuple[int, int], str, int]]:
        rows: list[tuple[tuple[int, int], str, int]] = []
        for y, line in enumerate(state.grid):
            for x, tile in enumerate(line):
                animal = animal_kind(tile)
                if animal is None or not isinstance(tile, Mapping) or tile.get("fed_today"):
                    continue
                product = ANIMAL_PRODUCT.get(animal)
                rows.append(((x, y), animal, BASE_PRICE.get(str(product), 0)))
        return rows

    def _record_feed_shortage(self, state: CanonicalState, controlled: Any) -> None:
        if state.day in self.feed_recorded_days or state.hour != 23:
            return
        self.feed_recorded_days.add(int(state.day))
        unfed = self._unfed_animals(state)
        if not unfed:
            return
        actions = [controlled.action.get("farmer", []), *controlled.action.get("hands", [])]
        fed_positions = {
            state.positions[actor] for actor, action in enumerate(actions)
            if actor < len(state.positions) and action and action[0] == "FEED"
        }
        remaining = [(position, animal, value) for position, animal, value in unfed if position not in fed_positions]
        wheat = int(state.shed.get("WHEAT", 0)) + sum(int(row.get("WHEAT", 0)) for row in state.inventories)
        wheat_after_actions = max(0, wheat - len(fed_positions))
        values = sorted((value for _, _, value in remaining), reverse=True)
        unavoidable = values[min(len(values), wheat_after_actions):]
        if unavoidable:
            self._record(
                state, "FEED_SHORTAGE", sum(unavoidable), len(unavoidable),
                "DAY_END_WHEAT_CANNOT_COVER_UNFED_ANIMALS",
                {"unfed_after_actions": len(remaining), "wheat_after_actions": wheat_after_actions,
                 "conservative_lost_outputs": unavoidable},
                expert_id=self.current_expert,
            )

    def _record_overdue(self, state: CanonicalState, executor: Any) -> None:
        wheat = int(state.shed.get("WHEAT", 0)) + sum(int(row.get("WHEAT", 0)) for row in state.inventories)
        for raw in getattr(executor, "overdue_task_details", ()):
            detail = dict(raw)
            signature = f"{state.day}:{detail.get('signature', '')}"
            if signature in self.seen_overdue:
                continue
            self.seen_overdue.add(signature)
            if detail.get("verb") == "FEED" and wheat <= 0:
                continue
            self._record(
                state, "OVERDUE_TASK", float(detail.get("estimated_value", LABOR_STEP_VALUE)), 1.0,
                "UNIQUE_TASK_PAST_CONTRACT_DEADLINE", detail,
                expert_id=self.current_expert,
            )

    @staticmethod
    def _terminal_unrealized(state: CanonicalState, controlled: Any) -> tuple[float, int, dict[str, Any]]:
        inventory = LossAttributionLedger._all_inventory(state)
        orders = list(controlled.action.get("market", []))
        sold: Counter[str] = Counter()
        for order in orders:
            if order and order[0] == "SELL" and len(order) >= 3:
                sold[str(order[1])] += max(0, int(order[2]))
        remaining = {item: max(0, int(quantity) - int(sold[item])) for item, quantity in inventory.items()
                     if item in BASE_PRICE}
        remaining = {item: quantity for item, quantity in remaining.items() if quantity > 0}
        inventory_value = sum(quantity * state.prices.get(item, BASE_PRICE.get(item, 0))
                              for item, quantity in remaining.items())
        seeds = {item: max(0, int(quantity)) for item, quantity in state.seeds.items() if int(quantity) > 0}
        seed_value = sum(quantity * SEED_COST.get(item, 0) for item, quantity in seeds.items())
        yield_value = 0
        yield_units = 0
        for line in state.grid:
            for tile in line:
                if not isinstance(tile, Mapping):
                    continue
                units = max(0, int(tile.get("yield_units", 0) or 0))
                if not units:
                    continue
                if tile.get("kind") == "PLANT":
                    product = str(tile.get("crop") or "")
                    facts = CROP_FACTS.get(product, {})
                    age = state.day - integer(tile.get("planted_day"), state.day)
                    ripe = (bool(facts.get("ongoing"))
                            or units >= integer(facts.get("max_yield"), 99)
                            or age >= integer(facts.get("mature"), 99))
                    if not ripe:
                        continue
                else:
                    product = str(ANIMAL_PRODUCT.get(animal_kind(tile) or "", ""))
                yield_value += units * state.prices.get(product, BASE_PRICE.get(product, 0))
                yield_units += units
        total_value = float(inventory_value + seed_value + yield_value)
        total_units = sum(remaining.values()) + sum(seeds.values()) + yield_units
        return total_value, total_units, {
            "remaining_products": remaining, "remaining_seeds": seeds,
            "unharvested_yield_units": yield_units, "sold_units": dict(sold),
        }

    def record_decision(self, state: CanonicalState, contract: DailyContract, feedback: Any,
                        executor: Any, market: Any, controlled: Any) -> None:
        """记录本 turn 的诊断暴露；不得把这些指标反馈给在线策略。"""

        self.current_expert = contract.expert_id
        if self.day_start_excess is None:
            self.day_reserves = {str(key): max(0, int(value))
                                 for key, value in contract.inventory_reserves.items()}
            self.day_start_excess = self._excess_inventory(state, self.day_reserves)

        diagnostics = dict(getattr(market, "diagnostics", {}) or {})
        finance = float(diagnostics.get("financing_shortfall_value", 0.0))
        if finance > self.finance_peak:
            self.finance_peak = finance
            self.finance_peak_details = {
                "cash_shortfall_value": float(diagnostics.get("cash_shortfall_value", 0.0)),
                "contract_budget_shortfall_value": float(diagnostics.get("contract_budget_shortfall_value", 0.0)),
                "purchase_execution_shortfall_value": float(diagnostics.get("purchase_execution_shortfall_value", 0.0)),
                "desired_purchase_value": float(diagnostics.get("desired_purchase_value", 0.0)),
                "budget_spent": float(getattr(market, "budget_spent", 0.0)),
            }
        self.pending_high_price = {
            str(item): (int(state.prices.get(str(item), BASE_PRICE.get(str(item), 0))), max(0, int(units)))
            for item, units in dict(diagnostics.get("high_price_unsold", {}) or {}).items()
            if int(units) > 0
        }

        self._record_overdue(state, executor)
        self._record_feed_shortage(state, controlled)

        actions = [controlled.action.get("farmer", []), *controlled.action.get("hands", [])]
        targets = list(getattr(executor, "actor_targets", ()))
        task_keys = list(getattr(executor, "actor_tasks", ()))
        pending: list[PendingMove] = []
        for actor, action in enumerate(actions):
            if actor >= len(state.positions) or not action or action[0] not in MOVE_OPS:
                continue
            target = targets[actor] if actor < len(targets) else None
            if getattr(controlled.mode, "value", str(controlled.mode)) in {"TERMINAL", "FEED_RECOVERY"}:
                target = shed_gate(state.positions[actor])
            pending.append(PendingMove(
                actor=actor, source=state.positions[actor], target=target,
                task_key=task_keys[actor] if actor < len(task_keys) else None,
                grid=state.grid,
            ))
        self.pending_moves = tuple(pending)

        if state.remaining_steps <= 1 and not self.terminal_recorded:
            self.terminal_recorded = True
            self._flush_finance(state, int(state.day))
            amount, units, details = self._terminal_unrealized(state, controlled)
            self._record(state, "TERMINAL_UNREALIZED", amount, units,
                         "FINAL_VISIBLE_VALUE_NOT_CONVERTED_TO_CASH", details,
                         expert_id=contract.expert_id)

    def status(self) -> dict[str, Any]:
        values = {category: float(self.totals.get(category, 0.0)) for category in LOSS_CATEGORIES}
        # 当前日尚未结束时只展示 provisional 峰值，不写入持久事件，避免重复累计。
        values["FINANCING_SHORTFALL"] += float(self.finance_peak)
        rows = [
            {
                "category": category,
                "label": CATEGORY_LABELS[category],
                "estimated_value": values[category],
                "units": float(self.units.get(category, 0.0)),
                "events": int(self.event_counts.get(category, 0)),
            }
            for category in LOSS_CATEGORIES
        ]
        rows.sort(key=lambda row: (-float(row["estimated_value"]), str(row["category"])))
        return {
            "schema": "v117-r2.1-a-loss-attribution-v1",
            "evidence_status": "OBSERVABLE_PROXY_NOT_COUNTERFACTUAL_COIN_LOSS",
            "categories": {category: {"label": CATEGORY_LABELS[category],
                                      "definition": CATEGORY_DEFINITIONS[category]}
                           for category in LOSS_CATEGORIES},
            "totals": {row["category"]: {key: value for key, value in row.items() if key != "category"}
                       for row in rows},
            "top_losses": rows[:3],
            "total_proxy_value": sum(values.values()),
            "by_day": {str(day): {category: float(counter.get(category, 0.0))
                                   for category in LOSS_CATEGORIES}
                       for day, counter in sorted(self.by_day.items())},
            "open_day": {"day": self.current_day, "financing_peak": float(self.finance_peak),
                         "provisional": True},
            "recent_events": [asdict(event) for event in self.events],
            "forbidden_as_strategy_input": True,
        }


class CanonicalStateProxy:
    """只在日切时把融资峰值归属到前一日；其余字段转发当前合法状态。"""

    def __init__(self, state: CanonicalState, day: int) -> None:
        self._state = state
        self.step = state.step
        self.day = int(day)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._state, name)
