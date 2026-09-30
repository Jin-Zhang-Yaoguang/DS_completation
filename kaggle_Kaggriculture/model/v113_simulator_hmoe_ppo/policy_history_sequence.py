"""Stateful history-augmented timed sequence policy."""

from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from action_history import ActionHistoryState, augment_global
from policy_sequence_action import TimedSequenceActionV113Policy


class HistoryTimedSequenceActionV113Policy(TimedSequenceActionV113Policy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_history = ActionHistoryState()

    def _encoded(self, obs):
        encoded = features.encode_observation(obs)
        encoded["global"] = augment_global(encoded["global"], self.action_history)
        return encoded

    def _forward(self, obs):
        encoded = self._encoded(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        output = self._apply(
            self.params, state["global"], state["board"], state["units"], state["unit_mask"]
        )
        return encoded, jax.tree.map(lambda value: np.asarray(value[0]), output)

    def _conditioned(self, obs, unit_tokens, unit_quantities, market_tokens=None, market_quantities=None):
        encoded = self._encoded(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        if market_tokens is None:
            market_tokens = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
            market_quantities = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
        output = self._apply_conditioned(
            self.params, state["global"], state["board"], state["units"], state["unit_mask"],
            jnp.asarray(unit_tokens)[None], jnp.asarray(unit_quantities)[None],
            jnp.asarray(market_tokens)[None], jnp.asarray(market_quantities)[None],
        )
        return jax.tree.map(lambda value: np.asarray(value[0]), output)

    def act(self, obs):
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.action_history.reset()
        action = super().act(obs)
        self.action_history.update_action(action)
        return action

    def sample(self, obs, *args, **kwargs):
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.action_history.reset()
        action, trace = super().sample(obs, *args, **kwargs)
        self.action_history.update_action(action)
        return action, trace
