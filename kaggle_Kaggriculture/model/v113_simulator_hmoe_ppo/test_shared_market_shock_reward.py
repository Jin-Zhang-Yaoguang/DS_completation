"""Tests for the independent shared-market-shock PPO reward contract."""

import action_space as space
from collect_factorized_rollouts import shared_market_shock_potential


def _obs(market_level: int, own_stock: int, own_cash: int = 3000) -> dict:
    farm = lambda money: {
        "money": money,
        "hands": [],
        "unlocked_quadrants": [0],
        "tiles": [],
    }
    return {
        "player": 0,
        "step": 100,
        "farms": [farm(own_cash), farm(3000)],
        "private": {
            "shed": {space.PRODUCTS[0]: own_stock},
            "inventories": [],
        },
        "market": {
            "prices": {},
            "inventory": {item: market_level for item in space.PRODUCTS},
        },
    }


def _potential(obs: dict) -> float:
    return shared_market_shock_potential(
        obs, opponent_impact_weight=1.0, inventory_reference=10000.0,
        inventory_scale=1000.0, liquidity_weight=0.35, cash_weight=0.15,
    )


def test_scarce_market_values_liquid_stock():
    assert _potential(_obs(7000, 20)) > _potential(_obs(7000, 0))


def test_full_market_removes_stock_scarcity_bonus():
    assert _potential(_obs(10000, 20)) == _potential(_obs(10000, 0))


def test_scarce_market_values_cash_buffer():
    assert _potential(_obs(7000, 0, 6000)) > _potential(_obs(7000, 0, 500))
