from collections import Counter
from pathlib import Path

from opponent_pool import build_schedule, layer_quotas, load_registry


HERE = Path(__file__).resolve().parent


def test_registry_and_64_seed_quota_contract():
    registry = load_registry(HERE / "opponent_registry.json")
    assert layer_quotas(registry, 64) == {
        "gold_train": 26,
        "ppo_history": 19,
        "self_play": 9,
        "exploiter": 7,
        "anchor": 3,
    }
    assert registry["gold_family_split_ratios"] == {
        "train": 0.6, "dev": 0.2, "blind": 0.2,
    }


def test_schedule_is_reproducible_and_dual_seat_ready():
    registry = load_registry(HERE / "opponent_registry.json")
    first = build_schedule(registry, 7_000_000, 64, 113027, iteration=0)
    second = build_schedule(registry, 7_000_000, 64, 113027, iteration=0)
    assert [(row.seed, row.layer, row.member_id) for row in first] == [
        (row.seed, row.layer, row.member_id) for row in second
    ]
    assert len({row.seed for row in first}) == 64
    counts = Counter(row.layer for row in first)
    assert counts == Counter({
        "gold_train": 26, "ppo_history": 19, "self_play": 9,
        "exploiter": 7, "anchor": 3,
    })
    v76 = sum(row.member_id == "gold_v76_adjacent_buy" for row in first)
    assert v76 == 6
    assert 0.08 <= v76 / 64 <= 0.10


def test_exact_20_seed_layer_mix():
    registry = load_registry(HERE / "opponent_registry.json")
    rows = build_schedule(registry, 8_000_000, 20, 99)
    assert Counter(row.layer for row in rows) == Counter({
        "gold_train": 8, "ppo_history": 6, "self_play": 3,
        "exploiter": 2, "anchor": 1,
    })
