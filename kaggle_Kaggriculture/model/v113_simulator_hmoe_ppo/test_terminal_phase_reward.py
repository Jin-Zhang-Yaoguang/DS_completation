"""Tests for terminal-phase PPO objectives."""

from collect_factorized_rollouts import phase_indices, terminal_objective


def test_terminal_objective_rewards_own_liquidation():
    high = terminal_objective(
        [12000.0, 10000.0], 0, 100000.0, "smooth", 3000.0, 0.25, 0.25,
    )
    low = terminal_objective(
        [4000.0, 2000.0], 0, 100000.0, "smooth", 3000.0, 0.25, 0.25,
    )
    assert high > low


def test_terminal_objective_penalizes_cash_catastrophe():
    penalized = terminal_objective(
        [500.0, 1000.0], 0, 100000.0, "smooth", 3000.0, 1.0, 0.0,
    )
    unpenalized = terminal_objective(
        [500.0, 1000.0], 0, 100000.0, "smooth", 3000.0, 0.0, 0.0,
    )
    assert penalized < unpenalized


def test_phase_indices_select_last_48_decision_rounds():
    traces = [{"environment_step": step} for step in range(1, 720)]
    selected = phase_indices(traces, 672, 720)
    assert len(selected) == 48
    assert selected[0] == 671
    assert selected[-1] == 718
