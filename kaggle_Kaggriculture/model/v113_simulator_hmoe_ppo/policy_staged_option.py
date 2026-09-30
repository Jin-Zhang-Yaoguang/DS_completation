"""Deterministic V113 staged-option policy with task-consistent action masks."""

from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from model_staged_option import StagedOptionHMoEActorCritic
from policy_factorized import FactorizedV113Policy


STAGE_OPERATIONS = {
    0: {"PASS"},
    1: {"BUILD_COOP", "BUILD_PASTURE"},
    2: {"PICKUP"},
    3: {"PLACE"},
    4: {"PLANT"},
    5: {"WATER", "FERTILIZE", "FEED", "CARE", "COLLECT_FERTILIZER"},
    6: {"HARVEST"},
    7: {"DROP"},
    8: {"DIG"},
    9: {"PASS"},
}


class StagedOptionV113Policy(FactorizedV113Policy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = StagedOptionHMoEActorCritic()
        self._apply = jax.jit(
            lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m)
        )
        self._apply_market_conditioned = jax.jit(
            lambda params, g, b, u, m, market_tokens, market_quantities: self.model.apply(
                {"params": params}, g, b, u, m, None, None,
                market_tokens, market_quantities,
            )
        )

    def _condition_market_output(
        self, obs, unit_tokens, unit_quantities,
        market_tokens, market_quantities, output,
    ):
        encoded = features.encode_observation(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        conditioned = self._apply_market_conditioned(
            self.params, state["global"], state["board"], state["units"],
            state["unit_mask"], jnp.asarray(market_tokens)[None],
            jnp.asarray(market_quantities)[None],
        )
        return jax.tree.map(lambda value: np.asarray(value[0]), conditioned)

    def _unit_legal_mask(self, obs, unit_index, output):
        legal = np.asarray(space.unit_legal_mask(obs, unit_index), dtype=bool)
        stage = int(output["selected_stages"][unit_index])
        target = int(output["selected_targets"][unit_index])
        target_position = (target % 10, target // 10)
        position = space.unit_position(obs, unit_index)
        if stage == 0:
            idle = np.zeros_like(legal)
            idle[space.UNIT_INDEX["PASS"]] = True
            return idle
        if position != target_position:
            distance = abs(position[0] - target_position[0]) + abs(position[1] - target_position[1])
            directed = np.zeros_like(legal)
            for move, (dx, dy) in zip(space.MOVES, ((0, -1), (0, 1), (1, 0), (-1, 0))):
                token = space.UNIT_INDEX[move]
                next_position = (position[0] + dx, position[1] + dy)
                next_distance = abs(next_position[0] - target_position[0]) + abs(next_position[1] - target_position[1])
                directed[token] = legal[token] and next_distance < distance
            if not np.any(directed):
                directed[space.UNIT_INDEX["PASS"]] = True
            return directed
        allowed_operations = STAGE_OPERATIONS[stage]
        task_mask = np.zeros_like(legal)
        for token, name in enumerate(space.UNIT_TOKENS):
            operation = name.split(":", 1)[0]
            task_mask[token] = legal[token] and operation in allowed_operations
        if not np.any(task_mask):
            task_mask[space.UNIT_INDEX["PASS"]] = True
        return task_mask
