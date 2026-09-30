"""Deterministic V113 policy using learned per-unit role and target options."""

from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from model_role_option import RoleOptionHMoEActorCritic
from policy import _masked_choice
from policy_factorized import FactorizedV113Policy


class RoleOptionV113Policy(FactorizedV113Policy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = RoleOptionHMoEActorCritic()
        self._apply = jax.jit(
            lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m)
        )
        self._apply_options = jax.jit(
            lambda params, g, b, u, m, roles, targets: self.model.apply(
                {"params": params}, g, b, u, m, roles, targets
            )
        )
        self.option_roles = None
        self.option_targets = None
        self.option_arrived = None
        self.option_initialized = None
        self.option_last_step = -1

    def _target_mask(self, obs):
        mask = np.zeros((features.BOARD_SIZE * features.BOARD_SIZE,), dtype=bool)
        tiles = space.get(space.own_farm(obs), "tiles", []) or []
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if tile != "LOCKED":
                    mask[y * features.BOARD_SIZE + x] = True
        return mask

    def sample(
        self, obs, rng: np.random.Generator, worker_temperature: float = 0.2,
        manager_temperature: float = 0.5,
    ):
        if manager_temperature <= 0:
            raise ValueError("manager_temperature must be positive")
        encoded, initial = self._forward(obs)
        step = int(space.get(obs, "step", 0) or 0)
        count = min(features.MAX_UNITS, space.unit_count(obs))
        if step <= self.option_last_step or self.option_roles is None:
            self.option_roles = np.zeros((features.MAX_UNITS,), dtype=np.int16)
            self.option_targets = np.full((features.MAX_UNITS,), 44, dtype=np.int16)
            self.option_arrived = np.zeros((features.MAX_UNITS,), dtype=bool)
            self.option_initialized = np.zeros((features.MAX_UNITS,), dtype=bool)
        self.option_last_step = step
        roles = self.option_roles.copy()
        targets = self.option_targets.copy()
        role_masks = np.zeros((features.MAX_UNITS, 2), dtype=bool)
        target_masks = np.zeros((features.MAX_UNITS, features.BOARD_SIZE * features.BOARD_SIZE), dtype=bool)
        role_logprobs = np.zeros((features.MAX_UNITS,), dtype=np.float32)
        target_logprobs = np.zeros((features.MAX_UNITS,), dtype=np.float32)
        target_active = np.zeros((features.MAX_UNITS,), dtype=np.float32)
        decision_active = np.zeros((features.MAX_UNITS,), dtype=np.float32)
        target_legal = self._target_mask(obs)
        for unit_index in range(count):
            decide = not self.option_initialized[unit_index] or step % 24 == 0
            if not decide and roles[unit_index] == 1:
                target = int(targets[unit_index])
                at_target = space.unit_position(obs, unit_index) == (target % 10, target // 10)
                if at_target and self.option_arrived[unit_index]:
                    decide = True
                self.option_arrived[unit_index] = at_target
            if roles[unit_index] == 0 and not decide:
                decide = False
            if not decide:
                continue
            role_masks[unit_index] = True
            role, role_logprob, _ = _masked_choice(
                initial["option_role_logits"][unit_index] / manager_temperature,
                role_masks[unit_index], rng, False,
            )
            roles[unit_index] = role
            role_logprobs[unit_index] = role_logprob
            decision_active[unit_index] = 1.0
            self.option_arrived[unit_index] = False
            self.option_initialized[unit_index] = True
            if role == 1:
                target_masks[unit_index] = target_legal
                target, target_logprob, _ = _masked_choice(
                    initial["option_target_logits"][unit_index] / manager_temperature,
                    target_legal, rng, False,
                )
                targets[unit_index] = target
                target_logprobs[unit_index] = target_logprob
                target_active[unit_index] = 1.0
        self.option_roles = roles.copy()
        self.option_targets = targets.copy()
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        conditioned = self._apply_options(
            self.params, state["global"], state["board"], state["units"], state["unit_mask"],
            jnp.asarray(roles)[None], jnp.asarray(targets)[None],
        )
        conditioned = jax.tree.map(lambda value: np.asarray(value[0]), conditioned)
        action, trace = super().sample(
            obs, rng, worker_temperature=worker_temperature,
            _encoded=encoded, _output=conditioned,
        )
        trace.update({
            "option_roles": roles, "option_targets": targets,
            "option_role_masks": role_masks, "option_target_masks": target_masks,
            "option_role_logprobs": role_logprobs, "option_target_logprobs": target_logprobs,
            "option_target_active": target_active,
            "option_decision_active": decision_active,
        })
        return action, trace

    def _unit_legal_mask(self, obs, unit_index, output):
        legal = np.asarray(space.unit_legal_mask(obs, unit_index), dtype=bool)
        role = int(output["selected_roles"][unit_index])
        if role == 0:
            idle = np.zeros_like(legal)
            idle[space.UNIT_INDEX["PASS"]] = True
            return idle

        target = int(output["selected_targets"][unit_index])
        target_position = (target % 10, target // 10)
        position = space.unit_position(obs, unit_index)
        if position == target_position:
            for move in space.MOVES:
                legal[space.UNIT_INDEX[move]] = False
            return legal

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
