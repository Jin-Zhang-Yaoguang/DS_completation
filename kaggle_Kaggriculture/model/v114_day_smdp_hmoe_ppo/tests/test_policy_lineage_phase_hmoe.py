from policy_lineage_phase_hmoe import (
    REPLAY_MARKET_PHASE_SCHEDULE,
    REPLAY_UNIT_PHASE_SCHEDULE,
)


def _selected(schedule, step):
    selected = None
    for boundary, expert in schedule:
        if step >= boundary:
            selected = expert
    return selected


def test_replay_unit_phase_schedule_matches_dataset_contract():
    expected = {0: 4, 71: 4, 72: 2, 215: 2, 216: 0, 479: 0, 480: 1, 670: 1, 671: 5, 718: 5}
    assert {step: _selected(REPLAY_UNIT_PHASE_SCHEDULE, step) for step in expected} == expected


def test_replay_market_phase_schedule_matches_dataset_contract():
    expected = {0: 4, 479: 4, 480: 3, 670: 3, 671: 5, 718: 5}
    assert {step: _selected(REPLAY_MARKET_PHASE_SCHEDULE, step) for step in expected} == expected
