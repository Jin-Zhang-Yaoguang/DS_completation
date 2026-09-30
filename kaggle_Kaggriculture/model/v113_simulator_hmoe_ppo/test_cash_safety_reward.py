"""Tests for the independent cash-safety PPO expert reward contract."""

from collect_factorized_rollouts import cash_safety_relative_potential


def _obs(own_cash: float, opponent_cash: float = 3000.0) -> dict:
    farm = lambda money: {
        "money": money,
        "hands": [],
        "unlocked_quadrants": [0],
        "tiles": [],
    }
    return {
        "player": 0,
        "step": 100,
        "farms": [farm(own_cash), farm(opponent_cash)],
        "market": {"prices": {}},
    }


def test_cash_safety_potential_rewards_solvency():
    solvent = cash_safety_relative_potential(
        _obs(6000.0), opponent_impact_weight=1.0, cash_floor=3000.0,
        cash_reserve_weight=0.25, cash_shortfall_weight=0.75,
    )
    distressed = cash_safety_relative_potential(
        _obs(500.0), opponent_impact_weight=1.0, cash_floor=3000.0,
        cash_reserve_weight=0.25, cash_shortfall_weight=0.75,
    )
    assert solvent > distressed


def test_cash_shortfall_penalty_is_effective():
    penalized = cash_safety_relative_potential(
        _obs(500.0), opponent_impact_weight=1.0, cash_floor=3000.0,
        cash_reserve_weight=0.0, cash_shortfall_weight=1.0,
    )
    unpenalized = cash_safety_relative_potential(
        _obs(500.0), opponent_impact_weight=1.0, cash_floor=3000.0,
        cash_reserve_weight=0.0, cash_shortfall_weight=0.0,
    )
    assert penalized < unpenalized
