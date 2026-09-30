"""Stateful, observation-only market memory for shared-market shock experts."""

from __future__ import annotations

import numpy as np

import action_space as space


MARKET_MEMORY_FEATURES = 4 * len(space.PRODUCTS)


class MarketStateHistory:
    def __init__(self):
        self.reset()

    def reset(self):
        self.previous_inventory = None
        self.previous_log_price = None
        self.cached_step = None
        self.cached_vector = None

    def observe(self, obs) -> np.ndarray:
        step = int(space.get(obs, "step", 0) or 0)
        if self.cached_step == step and self.cached_vector is not None:
            return self.cached_vector.copy()
        market = space.get(obs, "market", {}) or {}
        inventory = space.get(market, "inventory", {}) or {}
        prices = space.get(market, "prices", {}) or {}
        current_inventory = np.asarray([
            float(space.get(inventory, item, 10000.0) or 0.0)
            for item in space.PRODUCTS
        ], dtype=np.float32)
        current_log_price = np.asarray([
            np.log1p(max(0.0, float(space.get(prices, item, space.BASE_PRICES[item]) or 0.0)))
            / np.log1p(500.0)
            for item in space.PRODUCTS
        ], dtype=np.float32)
        previous_inventory = (
            current_inventory if self.previous_inventory is None else self.previous_inventory
        )
        previous_log_price = (
            current_log_price if self.previous_log_price is None else self.previous_log_price
        )
        vector = np.concatenate((
            (previous_inventory - 10000.0) / 1000.0,
            (current_inventory - previous_inventory) / 1000.0,
            previous_log_price,
            current_log_price - previous_log_price,
        )).astype(np.float32)
        if vector.shape != (MARKET_MEMORY_FEATURES,):
            raise AssertionError(f"invalid market memory shape: {vector.shape}")
        self.previous_inventory = current_inventory.copy()
        self.previous_log_price = current_log_price.copy()
        self.cached_step = step
        self.cached_vector = vector.copy()
        return vector


def augment_market_memory(global_features, obs, history: MarketStateHistory) -> np.ndarray:
    return np.concatenate((
        np.asarray(global_features, dtype=np.float32).reshape(-1),
        history.observe(obs),
    )).astype(np.float32)
