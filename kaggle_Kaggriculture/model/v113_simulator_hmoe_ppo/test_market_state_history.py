"""Tests for observation-delta market memory."""

import numpy as np

import action_space as space
from market_state_history import MARKET_MEMORY_FEATURES, MarketStateHistory


def _obs(step: int, inventory: int, price: int) -> dict:
    return {
        "step": step,
        "market": {
            "inventory": {item: inventory for item in space.PRODUCTS},
            "prices": {item: price for item in space.PRODUCTS},
        },
    }


def test_first_observation_has_zero_deltas():
    vector = MarketStateHistory().observe(_obs(0, 10000, 50))
    assert vector.shape == (MARKET_MEMORY_FEATURES,)
    n = len(space.PRODUCTS)
    assert np.all(vector[n:2*n] == 0.0)
    assert np.all(vector[3*n:4*n] == 0.0)


def test_next_observation_exposes_inventory_and_price_deltas():
    history = MarketStateHistory()
    history.observe(_obs(0, 10000, 50))
    vector = history.observe(_obs(1, 9000, 100))
    n = len(space.PRODUCTS)
    assert np.allclose(vector[n:2*n], -1.0)
    assert np.all(vector[3*n:4*n] > 0.0)


def test_repeated_encoding_within_step_is_idempotent():
    history = MarketStateHistory()
    history.observe(_obs(0, 10000, 50))
    first = history.observe(_obs(1, 9000, 100))
    second = history.observe(_obs(1, 8000, 200))
    assert np.array_equal(first, second)
