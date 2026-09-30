"""History policy with a market-only observation-memory branch."""

from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from action_history import augment_global
from market_state_history import MARKET_MEMORY_FEATURES, MarketStateHistory, augment_market_memory
from model_sequence_action import SequenceActionHMoEActorCritic
from policy_history_sequence import HistoryTimedSequenceActionV113Policy


class MarketMemoryTimedSequenceActionV113Policy(HistoryTimedSequenceActionV113Policy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.market_state_history = MarketStateHistory()
        self.model = SequenceActionHMoEActorCritic(
            timed=True, market_memory_features=MARKET_MEMORY_FEATURES,
        )
        self._apply = jax.jit(
            lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m)
        )
        self._apply_conditioned = jax.jit(
            lambda params, g, b, u, m, ut, uq, mt, mq: self.model.apply(
                {"params": params}, g, b, u, m, ut, uq, mt, mq,
            )
        )

    def _encoded(self, obs):
        encoded = features.encode_observation(obs)
        encoded["global"] = augment_global(encoded["global"], self.action_history)
        encoded["global"] = augment_market_memory(
            encoded["global"], obs, self.market_state_history,
        )
        return encoded

    def act(self, obs):
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.market_state_history.reset()
        return super().act(obs)

    def sample(self, obs, *args, **kwargs):
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.market_state_history.reset()
        return super().sample(obs, *args, **kwargs)
