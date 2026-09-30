import numpy as np

import action_space as space
from policy_factorized import FactorizedV113Policy


def bare_policy(worker_cap=8, seed_capacity=11):
    policy = object.__new__(FactorizedV113Policy)
    policy.scale_worker_cap = worker_cap
    policy.scale_seed_capacity = seed_capacity
    return policy


def observation(hour=0, planted=0):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    for index in range(planted):
        tiles[index // 5][index % 5] = {"kind": "PLANT", "crop": "TOMATO"}
    return {
        "step": hour, "hour": hour, "player": 0,
        "farms": [{"tiles": tiles}, {"tiles": tiles}],
    }


def shadow(units=1, seeds=0, money=3000):
    return {
        "money": money, "hires": max(0, units - 1), "units": units, "land": 1,
        "shed": {item: 0 for item in space.ITEMS},
        "seeds": {crop: (seeds if crop == "TOMATO" else 0) for crop in space.CROPS},
        "prices": dict(space.BASE_PRICES),
    }


def test_scale_contract_allows_only_hour_zero_hires_up_to_cap():
    policy = bare_policy()
    assert policy._market_legal_mask(observation(0), shadow(1))[space.MARKET_INDEX["HIRE"]]
    assert not policy._market_legal_mask(observation(1), shadow(1))[space.MARKET_INDEX["HIRE"]]
    assert not policy._market_legal_mask(observation(0), shadow(9))[space.MARKET_INDEX["HIRE"]]


def test_scale_contract_caps_seed_reserve_by_planted_capacity():
    policy = bare_policy()
    obs = observation(0, planted=9)
    buy = space.MARKET_INDEX["BUY_SEED:TOMATO"]
    mask = policy._market_quantity_mask(obs, shadow(seeds=0), buy)
    assert np.flatnonzero(mask).tolist() == [1, 2]
    assert not policy._market_legal_mask(obs, shadow(seeds=2))[buy]
