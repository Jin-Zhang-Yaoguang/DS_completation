from evaluate_lineage_foundation import gate, schedule, summarize


def _row(score=1.0, reward=5000.0, opponent="x", sell=2, buy=2):
    return {
        "error": None, "statuses": ["DONE", "DONE"], "steps": 720,
        "action_steps": 719, "score": score, "candidate_reward": reward,
        "opponent_reward": 2000.0, "margin": reward - 2000.0,
        "catastrophe": reward < 3000, "opponent_id": opponent,
        "sell_orders": sell, "procurement_expansion_orders": buy,
    }


def test_schedule_fixes_eight_seed_blocks_per_l1_representative():
    registry = {"foundation_l1": {"representative_ids": ["a", "b", "c", "d"]}}
    rows = schedule("l1", 100, registry)
    assert len(rows) == 32
    assert rows[0] == (100, "registry:a")
    assert rows[8] == (108, "registry:b")
    assert rows[-1] == (131, "registry:d")


def test_l1_gate_checks_role_coverage_and_opponent_floor():
    rows = [_row(opponent=name) for name in ("a", "b", "c", "d") for _ in range(16)]
    pooled = summarize(rows)
    by_opponent = []
    for name in ("a", "b", "c", "d"):
        item = summarize([row for row in rows if row["opponent_id"] == name])
        item["opponent_id"] = name
        by_opponent.append(item)
    status, checks = gate("l1", "V10A_DEMAND_TIMING", pooled, by_opponent)
    assert status == "PASS_L1"
    assert all(checks.values())


def test_replay_lineage_requires_complete_economy_responsibilities():
    rows = [
        _row(opponent=name, sell=2, buy=0)
        for name in ("a", "b", "c", "d") for _ in range(16)
    ]
    pooled = summarize(rows)
    by_opponent = []
    for name in ("a", "b", "c", "d"):
        item = summarize([row for row in rows if row["opponent_id"] == name])
        item["opponent_id"] = name
        by_opponent.append(item)
    status, checks = gate("l1", "V11A_V2_REPLAY", pooled, by_opponent)
    assert status == "FAIL_L1"
    assert checks["responsibility_coverage"] is False
