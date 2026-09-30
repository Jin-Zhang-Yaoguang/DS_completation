from event_ledger import (
    EconomySnapshot,
    EventKind,
    LedgerStatus,
    MarketEvent,
    TransactionIntent,
    TransactionLedger,
)


def snapshot(step=0, money=3000, workers=1, land=1, seeds=None, inventory=None):
    return EconomySnapshot(
        step=step,
        money=money,
        workers=workers,
        unlocked_land=land,
        seeds=seeds or {},
        inventory=inventory or {},
    )


def test_same_intent_emits_once_under_one_hundred_repeated_inputs():
    ledger = TransactionLedger(season_budget=5000)
    event = MarketEvent("day-0", 1, EventKind.DAY_START, 0)
    ledger.open_event(event)
    intent = TransactionIntent("HIRE", None, 4, 200, 1000, 1000, 4, worker_cap=6)
    keys = [ledger.propose("day-0", intent, snapshot()) for _ in range(100)]
    assert len(set(keys)) == 1
    emitted = [ledger.emit(keys[0], 0) for _ in range(100)]
    assert sum(bool(orders) for orders in emitted) == 1
    assert ledger.audit()["commit_count"] == 1


def test_unauthorized_turn_is_structurally_empty():
    ledger = TransactionLedger()
    intent = TransactionIntent("BUY_SEED", "WHEAT", 10, 20, 200, 1000, 8)
    key = ledger.propose("not-open", intent, snapshot())
    assert key is None
    assert ledger.emit(("not-open", 0, "BUY_SEED", "WHEAT"), 0) == []
    assert ledger.audit()["unauthorized_proposals"] == 1


def test_terminal_event_cannot_represent_procurement():
    ledger = TransactionLedger()
    ledger.open_event(MarketEvent("terminal", 1, EventKind.TERMINAL_WINDOW, 671, True))
    buy = TransactionIntent("BUY_ANIMAL", "COW", 1, 500, 500, 0, 700)
    assert ledger.propose("terminal", buy, snapshot(step=671)) is None
    assert ledger.audit()["terminal_procurement_rejections"] == 1


def test_budget_cash_floor_and_worker_cap_are_cumulative():
    ledger = TransactionLedger(season_budget=600)
    ledger.open_event(MarketEvent("day-0", 1, EventKind.DAY_START, 0))
    intent = TransactionIntent("HIRE", None, 10, 200, 2000, 1000, 4, worker_cap=4)
    key = ledger.propose("day-0", intent, snapshot(money=3000, workers=1))
    assert key is not None
    assert ledger.emit(key, 0) == [["HIRE"], ["HIRE"], ["HIRE"]]
    assert ledger.audit()["season_spend"] == 600
    ledger.open_event(MarketEvent("day-1", 1, EventKind.DAY_START, 24))
    assert ledger.propose("day-1", intent, snapshot(step=24, money=3000, workers=4)) is None


def test_next_observation_acknowledges_without_retry():
    ledger = TransactionLedger()
    ledger.open_event(MarketEvent("sell", 1, EventKind.INVENTORY_THRESHOLD, 100))
    intent = TransactionIntent("SELL", "WHEAT", 5, 0, 0, 0, 120)
    key = ledger.propose("sell", intent, snapshot(step=100, inventory={"WHEAT": 8}))
    assert ledger.emit(key, 100) == [["SELL", "WHEAT", 5]]
    ledger.observe(snapshot(step=101, money=3050, inventory={"WHEAT": 3}))
    assert ledger.records[key].status == LedgerStatus.ACKED
    assert ledger.emit(key, 101) == []


def test_absolute_target_and_retain_semantics_compile_state_gap():
    ledger = TransactionLedger()
    ledger.open_event(MarketEvent("targets", 1, EventKind.DAY_START, 0))
    seed = TransactionIntent(
        "BUY_SEED", "WHEAT", 99, 10, 1000, 0, 0, target_total=12
    )
    key = ledger.propose("targets", seed, snapshot(seeds={"WHEAT": 7}))
    assert ledger.emit(key, 0) == [["BUY_SEED", "WHEAT", 5]]

    selling = TransactionLedger()
    selling.open_event(MarketEvent("sell-target", 1, EventKind.INVENTORY_THRESHOLD, 10))
    intent = TransactionIntent(
        "SELL", "WHEAT", 99, 0, 0, 0, 10, retain_total=3
    )
    key = selling.propose(
        "sell-target", intent, snapshot(step=10, inventory={"WHEAT": 11})
    )
    assert selling.emit(key, 10) == [["SELL", "WHEAT", 8]]
