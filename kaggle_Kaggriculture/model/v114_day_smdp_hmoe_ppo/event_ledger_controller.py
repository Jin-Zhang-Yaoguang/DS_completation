"""V12 event-gated controller joining unit tasks and transaction intents."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from event_aggregator import EventAggregator, EventInputs, EventType
from event_ledger import (
    EconomySnapshot,
    EventKind,
    MarketEvent,
    TransactionIntent,
    TransactionLedger,
)
from option_catalog import OptionState


UnitPolicy = Callable[[Any], Mapping[str, Any]]
MarketPolicy = Callable[[Any, MarketEvent], Sequence[TransactionIntent]]


EVENT_KIND = {
    EventType.DAY_BOUNDARY: EventKind.DAY_START,
    EventType.SHOP_UNLOCKED: EventKind.SHOP_UNLOCK,
    EventType.SELL_INVENTORY_THRESHOLD_ENTERED: EventKind.INVENTORY_THRESHOLD,
    EventType.SHED_CAPACITY_CRISIS: EventKind.INVENTORY_THRESHOLD,
    EventType.CASH_CRISIS_ENTERED: EventKind.CASH_CRISIS,
    EventType.OPTION_CONTRACT_FAILED: EventKind.OPTION_FAILURE,
    EventType.TERMINAL_WINDOW_ENTERED: EventKind.TERMINAL_WINDOW,
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else default


def economy_snapshot(observation: Any) -> EconomySnapshot:
    step = int(_get(observation, "step", 0) or 0)
    player = int(_get(observation, "player", 0) or 0)
    farms = list(_get(observation, "farms", []) or [])
    farm = farms[player] if 0 <= player < len(farms) else {}
    private = _get(observation, "private", {}) or {}
    return EconomySnapshot(
        step=step,
        money=int(_get(farm, "money", 0) or 0),
        workers=1 + len(list(_get(farm, "hands", []) or [])),
        unlocked_land=len(list(_get(farm, "unlocked_quadrants", []) or [])),
        seeds=dict(_get(private, "seeds", {}) or {}),
        inventory=dict(_get(private, "shed", {}) or {}),
    )


def _market_event_type(snapshot) -> EventType | None:
    if EventType.TERMINAL_WINDOW_ENTERED in snapshot.events:
        return EventType.TERMINAL_WINDOW_ENTERED
    if EventType.SHOP_UNLOCKED in snapshot.events:
        return EventType.SHOP_UNLOCKED
    return snapshot.boundary_event if snapshot.boundary_event in EVENT_KIND else None


class EventLedgerController:
    """Call the market expert only on a debounced event and emit each intent once."""

    def __init__(
        self,
        unit_policy: UnitPolicy,
        market_policy: MarketPolicy,
        *,
        aggregator: EventAggregator | None = None,
        ledger: TransactionLedger | None = None,
    ) -> None:
        self.unit_policy = unit_policy
        self.market_policy = market_policy
        self.aggregator = aggregator or EventAggregator()
        self.ledger = ledger or TransactionLedger()
        self.option_state = OptionState()
        self.generation = 0
        self.last_step = -1
        self.opened_event_ids: set[str] = set()
        self.market_policy_calls = 0
        self.unauthorized_market_turns = 0

    def reset(self) -> None:
        self.option_state = OptionState()
        self.generation = 0
        self.last_step = -1
        self.opened_event_ids.clear()
        self.ledger = TransactionLedger(self.ledger.season_budget)
        self.market_policy_calls = 0
        self.unauthorized_market_turns = 0

    def act(self, observation: Any, *, event_inputs: EventInputs | Mapping[str, Any] | None = None) -> dict:
        current = economy_snapshot(observation)
        if current.step < self.last_step:
            self.reset()
        self.ledger.observe(current)
        self.option_state, event_snapshot = self.aggregator.observe(
            observation, self.option_state, event_inputs=event_inputs
        )
        market_orders: list[list] = []
        event_type = _market_event_type(event_snapshot)
        if event_type is not None and not event_snapshot.done:
            event_id = f"{event_type.value}:{current.step}"
            if event_id not in self.opened_event_ids:
                self.generation += 1
                event = MarketEvent(
                    event_id=event_id,
                    generation=self.generation,
                    kind=EVENT_KIND[event_type],
                    opened_step=current.step,
                    terminal=event_type == EventType.TERMINAL_WINDOW_ENTERED,
                )
                self.ledger.open_event(event)
                self.opened_event_ids.add(event_id)
                self.market_policy_calls += 1
                for intent in self.market_policy(observation, event):
                    key = self.ledger.propose(event_id, intent, current)
                    if key is not None:
                        market_orders.extend(self.ledger.emit(key, current.step))

        unit = dict(self.unit_policy(observation) or {})
        if list(unit.get("market", []) or []):
            self.unauthorized_market_turns += 1
            raise ValueError("unit policy is forbidden from generating market actions")
        self.last_step = max(self.last_step, current.step)
        return {
            "farmer": list(unit.get("farmer", ["PASS"]) or ["PASS"]),
            "hands": [list(order or ["PASS"]) for order in list(unit.get("hands", []) or [])],
            "market": market_orders[:10],
        }

    def audit(self) -> dict:
        return {
            "market_policy_calls": self.market_policy_calls,
            "opened_events": len(self.opened_event_ids),
            "unauthorized_market_turns": self.unauthorized_market_turns,
            "ledger": self.ledger.audit(),
        }
