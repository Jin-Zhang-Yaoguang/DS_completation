"""逐 turn 真实状态对账、运行反馈与日级结果反馈。"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from contracts import DailyContract
from schema import (ANIMAL_COST, BASE_PRICE, CROPS, PRODUCTS, SEED_COST, SHED_CAPACITY,
                    CanonicalState, canonicalize, inventory_total, integer)


@dataclass(frozen=True)
class RuntimeFeedback:
    target_gap: Mapping[str, int]
    task_backlog: int
    maintenance_backlog: int
    labor_pressure: float
    cash_risk: float
    cash_runway: float
    shed_pressure: float
    feed_risk: float
    market_shock: float
    opponent_pressure: float
    switch_feasible: bool
    shop_changed: bool
    terminal: bool
    blocked_reasons: tuple[str, ...]
    previous_day_target_realization: float
    previous_day_productive_share: float
    previous_day_idle_share: float
    previous_day_overdue_tasks: int
    capacity_miss_streak: int


@dataclass(frozen=True)
class DailyOutcome:
    day: int
    expert_id: str | None
    contract_id: str | None
    cash_delta: int
    enterprise_value_delta: float
    inventory_delta: int
    productive_actions: int
    moves: int
    idle_actions: int
    overdue_tasks: int
    transition_cost: float
    target_realization_rate: float


@dataclass
class LedgerState:
    episode_serial: int = 0
    previous: CanonicalState | None = None
    day_start: CanonicalState | None = None
    current_day: int = -1
    active_contract: DailyContract | None = None
    contract_started_day: int = 0
    actor_tasks: tuple[str | None, ...] = ()
    actor_roles: tuple[int, ...] = ()
    pending_orders: tuple[tuple[Any, ...], ...] = ()
    action_counts: Counter[str] = field(default_factory=Counter)
    overdue_tasks: int = 0
    invariant_events: list[str] = field(default_factory=list)
    daily_outcomes: deque[DailyOutcome] = field(default_factory=lambda: deque(maxlen=30))
    last_feedback: RuntimeFeedback | None = None


def _enterprise_value(state: CanonicalState) -> float:
    shed_value = sum(int(quantity) * BASE_PRICE.get(item, 0) for item, quantity in state.shed.items())
    carried_value = sum(int(quantity) * BASE_PRICE.get(item, 0)
                        for inventory in state.inventories for item, quantity in inventory.items())
    crop_value = sum(int(quantity) * SEED_COST.get(item, 0) for item, quantity in state.crops.items())
    animal_value = sum(int(quantity) * ANIMAL_COST.get(item, 0) for item, quantity in state.animals.items())
    return float(state.money + shed_value + carried_value + crop_value + animal_value)


class StateLedger:
    """真实 observation 优先；内部预测冲突时只记录，不覆盖事实。"""

    def __init__(self) -> None:
        self.by_seat = {0: LedgerState(), 1: LedgerState()}

    def _runtime_fields(self, ledger: LedgerState) -> dict[str, Any]:
        contract = ledger.active_contract
        return {
            "active_contract_id": contract.contract_id if contract else None,
            "active_expert_id": contract.expert_id if contract else None,
            "contract_age_days": max(0, ledger.current_day - ledger.contract_started_day) if contract else 0,
            "actor_tasks": ledger.actor_tasks,
            "actor_roles": ledger.actor_roles,
            "pending_orders": ledger.pending_orders,
        }

    @staticmethod
    def _maintenance(state: CanonicalState) -> int:
        total = 0
        for row in state.grid:
            for tile in row:
                if not isinstance(tile, Mapping):
                    continue
                if tile.get("kind") == "PLANT" and not tile.get("watered_today"):
                    total += 1
                if tile.get("animal") and not tile.get("fed_today"):
                    total += 1
        return total

    @staticmethod
    def _target_gap(state: CanonicalState, contract: DailyContract | None) -> dict[str, int]:
        if contract is None:
            return {}
        gaps = {
            "lands": max(0, contract.lands - state.lands),
            "hands": max(0, contract.hands - (len(state.positions) - 1)),
        }
        for item, target in contract.crops.items():
            gaps[f"crop:{item}"] = max(0, int(target) - int(state.crops.get(item, 0)))
        for item, target in contract.animals.items():
            gaps[f"animal:{item}"] = max(0, int(target) - int(state.animals.get(item, 0)))
        total_inventory = inventory_total(state.inventories)
        for item, target in contract.inventory_reserves.items():
            have = int(state.shed.get(item, 0)) + int(total_inventory.get(item, 0))
            gaps[f"reserve:{item}"] = max(0, int(target) - have)
        return gaps

    def _finalize_day(self, ledger: LedgerState, current: CanonicalState) -> None:
        start = ledger.day_start
        if start is None or start.day == current.day:
            return
        counts = ledger.action_counts
        moves = sum(counts[op] for op in ("NORTH", "SOUTH", "EAST", "WEST"))
        idle = counts["PASS"]
        productive = sum(value for op, value in counts.items() if op not in {
            "NORTH", "SOUTH", "EAST", "WEST", "PASS", "MARKET_ORDER"
        })
        contract = ledger.active_contract
        target_total = 0
        completed_total = 0
        if contract is not None:
            targets = {"lands": contract.lands, "hands": contract.hands}
            targets.update({f"crop:{key}": int(value) for key, value in contract.crops.items()})
            targets.update({f"animal:{key}": int(value) for key, value in contract.animals.items()})
            targets.update({f"reserve:{key}": int(value) for key, value in contract.inventory_reserves.items()})
            target_total = sum(max(0, int(value)) for value in targets.values())
            completed_total = sum(min(max(0, int(value)), int(contract.target_realization.completed.get(key, 0)))
                                  for key, value in targets.items())
        ledger.daily_outcomes.append(DailyOutcome(
            day=start.day,
            expert_id=contract.expert_id if contract else None,
            contract_id=contract.contract_id if contract else None,
            cash_delta=current.money - start.money,
            enterprise_value_delta=_enterprise_value(current) - _enterprise_value(start),
            inventory_delta=current.shed_used - start.shed_used,
            productive_actions=productive,
            moves=moves,
            idle_actions=idle,
            overdue_tasks=ledger.overdue_tasks,
            transition_cost=float(contract.transition_cost if contract else 0.0),
            target_realization_rate=(completed_total / target_total if target_total else 1.0),
        ))
        ledger.action_counts.clear()
        ledger.overdue_tasks = 0

    def observe(self, observation: Mapping[str, Any]) -> tuple[CanonicalState, RuntimeFeedback]:
        seat = 1 if integer(observation.get("player")) == 1 else 0
        ledger = self.by_seat[seat]
        raw_step = integer(observation.get("step"), integer(observation.get("day")) * 24 + integer(observation.get("hour")))
        reset = raw_step == 0 or (ledger.previous is not None and raw_step <= ledger.previous.step)
        if reset:
            serial = ledger.episode_serial + 1
            ledger = LedgerState(episode_serial=serial)
            self.by_seat[seat] = ledger
        state = canonicalize(observation, ledger.previous, self._runtime_fields(ledger))
        if ledger.previous is not None and state.step != ledger.previous.step + 1:
            ledger.invariant_events.append("NON_CONTIGUOUS_STEP")
        if ledger.current_day != state.day:
            self._finalize_day(ledger, state)
            ledger.current_day = state.day
            ledger.day_start = state
        if len(state.inventories) != len(state.positions):
            ledger.invariant_events.append("ACTOR_INVENTORY_SHAPE")
        if state.shed_used > SHED_CAPACITY:
            ledger.invariant_events.append("SHED_CAPACITY_OBSERVATION")
        maintenance = self._maintenance(state)
        gaps = self._target_gap(state, ledger.active_contract)
        backlog = maintenance + sum(gaps.values())
        available = max(1, len(state.positions) * max(1, 23 - state.hour))
        contract = ledger.active_contract
        necessary = max(1, int(contract.cash_reserve if contract else 150))
        cash_runway = state.money / necessary
        cash_risk = max(0.0, min(1.0, (necessary - state.money) / necessary))
        carried = inventory_total(state.inventories)
        feed_need = int(contract.inventory_reserves.get("WHEAT", 0)) if contract else 0
        feed_have = int(state.shed.get("WHEAT", 0)) + int(carried.get("WHEAT", 0))
        feed_risk = max(0.0, min(1.0, (feed_need - feed_have) / max(1, feed_need))) if feed_need else 0.0
        price_shock = max((abs(value) / max(1, state.prices.get(item, 1))
                           for item, value in state.price_delta.items()), default=0.0)
        own_assets = state.lands + len(state.positions) + sum(state.animals.values())
        rival_assets = state.opponent.lands + len(state.opponent.positions) + sum(state.opponent.animals.values())
        opponent_pressure = max(0.0, min(2.0, (rival_assets - own_assets) / max(1, own_assets)))
        blocked: list[str] = []
        if cash_risk > 0:
            blocked.append("CASH")
        if feed_risk > 0:
            blocked.append("FEED")
        if state.shed_used / SHED_CAPACITY >= 0.9:
            blocked.append("SHED")
        if maintenance > available:
            blocked.append("LABOR")
        latest = ledger.daily_outcomes[-1] if ledger.daily_outcomes else None
        latest_actions = (
            latest.productive_actions + latest.moves + latest.idle_actions
            if latest is not None else 0
        )
        miss_streak = 0
        for outcome in reversed(ledger.daily_outcomes):
            if outcome.target_realization_rate >= 0.90 and outcome.overdue_tasks <= 4:
                break
            miss_streak += 1
        transition_cost = float(contract.transition_cost if contract else 0.0)
        feedback = RuntimeFeedback(
            target_gap=gaps, task_backlog=backlog, maintenance_backlog=maintenance,
            labor_pressure=max(0.0, backlog / available), cash_risk=cash_risk, cash_runway=cash_runway,
            shed_pressure=state.shed_used / SHED_CAPACITY, feed_risk=feed_risk,
            market_shock=price_shock, opponent_pressure=opponent_pressure,
            switch_feasible=state.money - necessary >= transition_cost,
            shop_changed=bool(state.new_shops), terminal=state.remaining_steps <= 24,
            blocked_reasons=tuple(blocked),
            previous_day_target_realization=(
                float(latest.target_realization_rate) if latest is not None else 1.0
            ),
            previous_day_productive_share=(
                float(latest.productive_actions) / max(1, latest_actions)
                if latest is not None else 1.0
            ),
            previous_day_idle_share=(
                float(latest.idle_actions) / max(1, latest_actions)
                if latest is not None else 0.0
            ),
            previous_day_overdue_tasks=(
                int(latest.overdue_tasks) if latest is not None else 0
            ),
            capacity_miss_streak=miss_streak,
        )
        ledger.previous = state
        ledger.last_feedback = feedback
        return state, feedback

    def activate_contract(self, seat: int, contract: DailyContract, switched: bool) -> None:
        ledger = self.by_seat[seat]
        previous = ledger.active_contract
        if previous is not None and previous.contract_id == contract.contract_id:
            ledger.active_contract = contract
            return
        if switched and previous is not None:
            # 只更换合同引用；真实资产、库存、任务与订单完全保留。
            ledger.invariant_events.append("CONTRACT_SWITCH_RECONCILED")
        ledger.active_contract = contract
        ledger.contract_started_day = contract.issued_day if switched or previous is None else ledger.contract_started_day

    def record_execution(self, seat: int, unit_actions: Sequence[Sequence[Any]], market_orders: Sequence[Sequence[Any]],
                         actor_tasks: Sequence[str | None], actor_roles: Sequence[int], overdue_tasks: int = 0) -> None:
        ledger = self.by_seat[seat]
        for action in unit_actions:
            ledger.action_counts[str(action[0]) if action else "INVALID"] += 1
        ledger.action_counts["MARKET_ORDER"] += len(market_orders)
        ledger.actor_tasks = tuple(actor_tasks)
        ledger.actor_roles = tuple(int(value) for value in actor_roles)
        ledger.pending_orders = tuple(tuple(order) for order in market_orders)
        ledger.overdue_tasks += max(0, int(overdue_tasks))

    def status(self, seat: int) -> dict[str, Any]:
        ledger = self.by_seat[seat]
        return {
            "episode_serial": ledger.episode_serial,
            "active_contract": ledger.active_contract.contract_id if ledger.active_contract else None,
            "invariant_events": list(ledger.invariant_events),
            "daily_outcomes": [outcome.__dict__ for outcome in ledger.daily_outcomes],
            "last_feedback": ledger.last_feedback.__dict__ if ledger.last_feedback else None,
        }
