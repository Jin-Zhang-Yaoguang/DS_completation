from event_ledger import EventKind, TransactionIntent
from event_ledger_controller import EventLedgerController


def obs(step, money=3000, seeds=None):
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "episode_steps": 720,
        "farms": [
            {"money": money, "hands": [], "unlocked_quadrants": [0], "tiles": []},
            {"money": 3000, "hands": [], "unlocked_quadrants": [0], "tiles": []},
        ],
        "private": {"seeds": seeds or {}, "shed": {}, "inventories": [{}]},
        "town": {"unlocked_shops": []},
    }


def unit_policy(_):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def buy_seed_policy(observation, event):
    assert event.kind in {EventKind.DAY_START, EventKind.TERMINAL_WINDOW}
    return [TransactionIntent("BUY_SEED", "WHEAT", 5, 10, 50, 1000, event.opened_step)]


def test_repeated_same_event_calls_market_policy_and_emits_once():
    controller = EventLedgerController(unit_policy, buy_seed_policy)
    actions = [controller.act(obs(0)) for _ in range(100)]
    assert sum(bool(action["market"]) for action in actions) == 1
    assert controller.audit()["market_policy_calls"] == 1
    assert controller.audit()["ledger"]["commit_count"] == 1


def test_non_event_turn_market_is_structurally_empty():
    controller = EventLedgerController(unit_policy, buy_seed_policy)
    controller.act(obs(0))
    for step in range(1, 24):
        assert controller.act(obs(step))["market"] == []
    assert controller.audit()["market_policy_calls"] == 1


def test_next_observation_ack_does_not_retry():
    controller = EventLedgerController(unit_policy, buy_seed_policy)
    assert controller.act(obs(0))["market"] == [["BUY_SEED", "WHEAT", 5]]
    assert controller.act(obs(1, money=2950, seeds={"WHEAT": 5}))["market"] == []
    assert controller.audit()["ledger"]["statuses"]["ACKED"] == 1


def test_terminal_event_blocks_procurement():
    controller = EventLedgerController(unit_policy, buy_seed_policy)
    assert controller.act(obs(671))["market"] == []
    assert controller.audit()["ledger"]["terminal_procurement_rejections"] == 1
