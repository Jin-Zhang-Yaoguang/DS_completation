"""Cross-turn transaction ledger for V12 Event-Ledger HMoE.

The ledger makes repeated market execution structurally impossible. A market
expert may propose one bounded intent only for an authorized event. The intent
is emitted once, then acknowledged or rejected from the next observation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class EventKind(str, Enum):
    DAY_START = "DAY_START"
    SHOP_UNLOCK = "SHOP_UNLOCK"
    INVENTORY_THRESHOLD = "INVENTORY_THRESHOLD"
    CASH_CRISIS = "CASH_CRISIS"
    OPTION_FAILURE = "OPTION_FAILURE"
    TERMINAL_WINDOW = "TERMINAL_WINDOW"
    EXPLICIT_RETRY_AFTER_REJECTION = "EXPLICIT_RETRY_AFTER_REJECTION"


class LedgerStatus(str, Enum):
    PROPOSED = "PROPOSED"
    COMMITTED = "COMMITTED"
    ACKED = "ACKED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


PROCUREMENT = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}
OPERATIONS = PROCUREMENT | {"SELL"}


@dataclass(frozen=True)
class EconomySnapshot:
    step: int
    money: int
    workers: int
    unlocked_land: int
    seeds: Mapping[str, int] = field(default_factory=dict)
    inventory: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    generation: int
    kind: EventKind
    opened_step: int
    terminal: bool = False


@dataclass(frozen=True)
class TransactionIntent:
    operation: str
    product: str | None
    quantity: int
    unit_price: int
    max_spend: int
    cash_floor: int
    expiry_step: int
    target_total: int | None = None
    retain_total: int | None = None
    worker_cap: int = 16
    land_cap: int = 4
    animal_cap: int = 100

    def key(self, event: MarketEvent) -> tuple[str, int, str, str]:
        return (
            event.event_id,
            int(event.generation),
            self.operation,
            self.product or "_",
        )


@dataclass
class LedgerRecord:
    event: MarketEvent
    intent: TransactionIntent
    before: EconomySnapshot
    approved_quantity: int
    approved_spend: int
    status: LedgerStatus = LedgerStatus.PROPOSED
    committed_step: int | None = None


class TransactionLedger:
    """State machine enforcing one commit per event and transaction key."""

    def __init__(self, season_budget: int = 1_000_000):
        if season_budget < 0:
            raise ValueError("season_budget must be non-negative")
        self.season_budget = int(season_budget)
        self.season_spend = 0
        self.events: dict[str, MarketEvent] = {}
        self.records: dict[tuple[str, int, str, str], LedgerRecord] = {}
        self.commit_count = 0
        self.blocked_duplicate_emits = 0
        self.unauthorized_proposals = 0
        self.budget_rejections = 0
        self.terminal_procurement_rejections = 0

    def open_event(self, event: MarketEvent) -> None:
        previous = self.events.get(event.event_id)
        if previous is not None and event.generation <= previous.generation:
            raise ValueError("event generation must increase")
        self.events[event.event_id] = event

    def propose(
        self,
        event_id: str,
        intent: TransactionIntent,
        snapshot: EconomySnapshot,
    ) -> tuple[str, int, str, str] | None:
        event = self.events.get(event_id)
        if event is None:
            self.unauthorized_proposals += 1
            return None
        if intent.operation not in OPERATIONS:
            raise ValueError(f"unknown market operation: {intent.operation}")
        if intent.quantity <= 0 or intent.unit_price < 0 or intent.max_spend < 0:
            raise ValueError("quantity must be positive and price/budget non-negative")
        if snapshot.step > intent.expiry_step:
            return None
        if (event.terminal or event.kind == EventKind.TERMINAL_WINDOW) and intent.operation in PROCUREMENT:
            self.terminal_procurement_rejections += 1
            return None
        key = intent.key(event)
        if key in self.records:
            return key

        quantity = int(intent.quantity)
        if intent.target_total is not None:
            target = max(0, int(intent.target_total))
            if intent.operation == "HIRE":
                quantity = max(0, target - snapshot.workers)
            elif intent.operation == "BUY_LAND":
                quantity = max(0, target - snapshot.unlocked_land)
            elif intent.operation == "BUY_SEED" and intent.product is not None:
                quantity = max(0, target - int(snapshot.seeds.get(intent.product, 0)))
            elif intent.operation in {"BUY_PRODUCT", "BUY_ANIMAL"} and intent.product is not None:
                quantity = max(0, target - int(snapshot.inventory.get(intent.product, 0)))
        if intent.operation == "SELL" and intent.product is not None and intent.retain_total is not None:
            quantity = max(
                0,
                int(snapshot.inventory.get(intent.product, 0)) - max(0, int(intent.retain_total)),
            )
        if intent.operation == "HIRE":
            quantity = min(quantity, max(0, intent.worker_cap - snapshot.workers))
        elif intent.operation == "BUY_LAND":
            quantity = min(quantity, max(0, intent.land_cap - snapshot.unlocked_land))
        elif intent.operation == "BUY_ANIMAL" and intent.product is not None:
            current = int(snapshot.inventory.get(intent.product, 0))
            quantity = min(quantity, max(0, intent.animal_cap - current))
        elif intent.operation == "SELL" and intent.product is not None:
            quantity = min(quantity, max(0, int(snapshot.inventory.get(intent.product, 0))))

        spend = 0
        if intent.operation in PROCUREMENT:
            remaining_cash = max(0, int(snapshot.money) - int(intent.cash_floor))
            remaining_season = max(0, self.season_budget - self.season_spend)
            budget = min(int(intent.max_spend), remaining_cash, remaining_season)
            if intent.unit_price > 0:
                quantity = min(quantity, budget // int(intent.unit_price))
            spend = quantity * int(intent.unit_price)
        if quantity <= 0:
            self.budget_rejections += 1
            return None
        self.records[key] = LedgerRecord(event, intent, snapshot, quantity, spend)
        return key

    def emit(self, key: tuple[str, int, str, str], step: int) -> list[list]:
        record = self.records.get(key)
        if record is None:
            return []
        if record.status != LedgerStatus.PROPOSED:
            self.blocked_duplicate_emits += 1
            return []
        if step > record.intent.expiry_step:
            record.status = LedgerStatus.EXPIRED
            return []
        record.status = LedgerStatus.COMMITTED
        record.committed_step = int(step)
        self.commit_count += 1
        self.season_spend += record.approved_spend
        if record.intent.operation in {"HIRE", "BUY_LAND"}:
            return [[record.intent.operation] for _ in range(record.approved_quantity)]
        return [[record.intent.operation, record.intent.product, record.approved_quantity]]

    def observe(self, snapshot: EconomySnapshot) -> None:
        for record in self.records.values():
            if record.status != LedgerStatus.COMMITTED:
                continue
            if snapshot.step <= int(record.committed_step or -1):
                continue
            before = record.before
            operation = record.intent.operation
            product = record.intent.product
            if operation == "HIRE":
                changed = snapshot.workers > before.workers
            elif operation == "BUY_LAND":
                changed = snapshot.unlocked_land > before.unlocked_land
            elif operation == "BUY_SEED" and product is not None:
                changed = int(snapshot.seeds.get(product, 0)) > int(before.seeds.get(product, 0))
            elif operation in {"BUY_PRODUCT", "BUY_ANIMAL"} and product is not None:
                changed = int(snapshot.inventory.get(product, 0)) > int(before.inventory.get(product, 0))
            elif operation == "SELL" and product is not None:
                changed = (
                    int(snapshot.inventory.get(product, 0)) < int(before.inventory.get(product, 0))
                    or snapshot.money > before.money
                )
            else:
                changed = False
            record.status = LedgerStatus.ACKED if changed else LedgerStatus.REJECTED

    def expire(self, step: int) -> None:
        for record in self.records.values():
            if record.status == LedgerStatus.PROPOSED and step > record.intent.expiry_step:
                record.status = LedgerStatus.EXPIRED

    def audit(self) -> dict:
        statuses = {status.value: 0 for status in LedgerStatus}
        for record in self.records.values():
            statuses[record.status.value] += 1
        return {
            "records": len(self.records),
            "commit_count": self.commit_count,
            "blocked_duplicate_emits": self.blocked_duplicate_emits,
            "unauthorized_proposals": self.unauthorized_proposals,
            "budget_rejections": self.budget_rejections,
            "terminal_procurement_rejections": self.terminal_procurement_rejections,
            "season_spend": self.season_spend,
            "statuses": statuses,
        }
