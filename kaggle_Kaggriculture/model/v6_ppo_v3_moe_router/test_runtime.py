"""Regression test for the environment-fork seed bug and its repair."""

from __future__ import annotations

from runtime import fork_env, set_step_for_both_seats


def _pass(env, start, end):
    for step in range(start, end):
        set_step_for_both_seats(env, step)
        env.step([
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["PASS"], "hands": [], "market": []},
        ])


def test_fork_preserves_seeded_daily_randomness():
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"seed": 123}, debug=False)
    env.reset(2)
    _pass(env, 0, 48)
    branch = fork_env(env)
    _pass(env, 48, 96)
    _pass(branch, 48, 96)
    assert env.info == branch.info
    assert env.state[0].observation["town"] == branch.state[0].observation["town"]
    assert env.state[0].observation["farms"] == branch.state[0].observation["farms"]


if __name__ == "__main__":
    test_fork_preserves_seeded_daily_randomness()
    print("runtime fork test passed")
