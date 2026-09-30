"""Deterministic 32-d action-history state for the recurrent V113 actor."""

from __future__ import annotations

import numpy as np

import action_space as space


HISTORY_FEATURES = 32


def _unit_category(name: str) -> int:
    if name == "PASS":
        return 0
    if name in space.MOVES:
        return 1
    if name == "DROP" or name.startswith("PICKUP:") or name.startswith("PLACE:"):
        return 2
    if name.startswith(("PLANT:",)) or name in {
        "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
        "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
    }:
        return 3
    return 4


class ActionHistoryState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.first_demand = np.zeros((len(space.PRODUCTS),), dtype=np.float32)
        self.first_demand_latched = False
        self.previous_market_flow = np.zeros((len(space.PRODUCTS),), dtype=np.float32)
        self.cumulative_market_flow = np.zeros((len(space.PRODUCTS),), dtype=np.float32)
        self.previous_unit_categories = np.zeros((5,), dtype=np.float32)

    def observe_global(self, global_features) -> np.ndarray:
        demand = np.asarray(global_features, dtype=np.float32)[-len(space.PRODUCTS):]
        if not self.first_demand_latched and np.any(np.abs(demand) > 1e-8):
            self.first_demand = demand.copy()
            self.first_demand_latched = True
        vector = np.concatenate((
            self.first_demand,
            self.previous_market_flow / 100.0,
            self.cumulative_market_flow / 1000.0,
            self.previous_unit_categories / 16.0,
        )).astype(np.float32)
        if vector.shape != (HISTORY_FEATURES,):
            raise AssertionError(f"invalid history vector shape: {vector.shape}")
        return vector

    def update_tokens(self, unit_tokens, market_tokens, market_quantities):
        categories = np.zeros((5,), dtype=np.float32)
        for token in np.asarray(unit_tokens).reshape(-1):
            index = int(token)
            if 0 <= index < len(space.UNIT_TOKENS):
                categories[_unit_category(space.UNIT_TOKENS[index])] += 1.0
        flow = np.zeros((len(space.PRODUCTS),), dtype=np.float32)
        for token, quantity in zip(
            np.asarray(market_tokens).reshape(-1),
            np.asarray(market_quantities).reshape(-1),
        ):
            index = int(token)
            if not 0 <= index < len(space.MARKET_TOKENS):
                continue
            name = space.MARKET_TOKENS[index]
            amount = float(min(100, max(0, int(quantity))))
            if name.startswith("SELL:"):
                item = name.split(":", 1)[1]
                flow[space.PRODUCTS.index(item)] += amount
            elif name.startswith("BUY_PRODUCT:") or name.startswith("BUY_SEED:"):
                item = name.split(":", 1)[1]
                if item in space.PRODUCTS:
                    flow[space.PRODUCTS.index(item)] -= amount
        self.previous_unit_categories = categories
        self.previous_market_flow = flow
        self.cumulative_market_flow += flow

    def update_action(self, action):
        unit_orders = [action.get("farmer", ["PASS"])] + list(action.get("hands", []) or [])
        unit_tokens = [space.unit_token(order)[0] for order in unit_orders]
        market_rows = [space.market_token(order) for order in list(action.get("market", []) or [])]
        market_tokens = [row[0] for row in market_rows]
        market_quantities = [row[1] for row in market_rows]
        self.update_tokens(unit_tokens, market_tokens, market_quantities)


def augment_global(global_features, history: ActionHistoryState) -> np.ndarray:
    base = np.asarray(global_features, dtype=np.float32).reshape(-1)
    return np.concatenate((base, history.observe_global(base))).astype(np.float32)
