"""Kaggriculture runtime helpers with reproducible mid-episode forks."""

from __future__ import annotations

import copy


def fork_env(env):
    """Fork a Kaggle Environment without losing Kaggriculture RNG state.

    `Environment.clone()` restores the steps but does not retain ``env.info``.
    Kaggriculture reads ``info['seed']`` for daily shop/weed randomness, so a
    bare clone makes same-state branches diverge.  Logs are copied as well for
    clean branch-local accounting.
    """
    branch = env.clone()
    branch.info = copy.deepcopy(env.info)
    branch.logs = copy.deepcopy(env.logs)
    return branch


def set_step_for_both_seats(env, step: int) -> None:
    """Keep manual local rollouts consistent for seat 0 and seat 1 agents."""
    for state in env.state:
        state.observation.step = int(step)


def copy_agent_state(agent):
    """Require cloneable agent objects instead of sharing mutable module state."""
    snapshot = getattr(agent, "snapshot", None)
    if not callable(snapshot):
        raise TypeError("PPO v3 fork agents must provide snapshot()")
    return copy.deepcopy(snapshot())


def restore_agent_state(agent, state) -> None:
    restore = getattr(agent, "restore", None)
    if not callable(restore):
        raise TypeError("PPO v3 fork agents must provide restore(state)")
    restore(copy.deepcopy(state))
