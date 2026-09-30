"""One-day probe followed by one learned production-route commitment."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

from event_program import MacroDecision, observation_step
from event_program_features import (
    DECISION_HEAD_VALUES,
    FEATURE_SCHEMA,
    MANAGER_FEATURE_DIM,
    encode_event_program_features,
)
from model_event_program_ppo import EventProgramPPOManager, validate_checkpoint_metadata
from policy_event_program import FixedEventProgramPolicy
from policy_trainable_event_program import decision_key, qualified_macro_action_masks


class DelayedTrainableEventProgramPolicy:
    """Probe for 24 steps, choose one route, then execute it deterministically."""

    def __init__(
        self,
        checkpoint: str | Path,
        *,
        rollout_seed: int,
        episode_key: str,
        deterministic: bool = True,
        probe_steps: int = 24,
    ) -> None:
        if int(probe_steps) <= 0 or int(probe_steps) % 24 != 0:
            raise ValueError("probe_steps must be a positive whole number of days")
        payload = serialization.msgpack_restore(Path(checkpoint).expanduser().read_bytes())
        validate_checkpoint_metadata(payload)
        if int(payload.get("input_dim", -1)) != MANAGER_FEATURE_DIM:
            raise ValueError("checkpoint input_dim does not match delayed Router")
        if payload.get("feature_schema") != FEATURE_SCHEMA:
            raise ValueError("checkpoint feature schema mismatch")
        self.params = payload["params"]
        self.policy_seed = int(payload["policy_seed"])
        self.rollout_seed = int(rollout_seed)
        self.episode_key = str(episode_key)
        self.deterministic = bool(deterministic)
        self.probe_steps = int(probe_steps)
        self.model = EventProgramPPOManager()
        self.route: FixedEventProgramPolicy | None = None
        self.action_steps = 0
        self.probe_action_steps = 0
        self.manager_decision_count = 0
        self.probe_features: np.ndarray | None = None
        self.production_logits: np.ndarray | None = None
        self.selected_route: str | None = None

    @property
    def contract_violation_count(self) -> int:
        return 0 if self.route is None else int(self.route.contract_violation_count)

    @property
    def terminal_procurement_count(self) -> int:
        return 0 if self.route is None else int(self.route.terminal_procurement_count)

    def _activate_route(self, observation: Mapping[str, Any]) -> None:
        features = np.asarray(
            encode_event_program_features(
                observation, current_decision=None, current_event=None
            ),
            dtype=np.float32,
        )
        masks = qualified_macro_action_masks(observation)
        logits = self.model.apply(
            {"params": self.params}, jnp.asarray(features[None, :], dtype=jnp.float32)
        )["actor_logits"]["production_line"]
        mask = jnp.asarray(masks["production_line"])
        masked_logits = jnp.where(mask, logits, -jnp.inf)
        if self.deterministic:
            index = int(jnp.argmax(masked_logits, axis=-1)[0])
        else:
            key = decision_key(
                self.policy_seed,
                self.rollout_seed,
                self.episode_key,
                0,
            )
            index = int(jax.random.categorical(key, masked_logits, axis=-1)[0])
        production_line = DECISION_HEAD_VALUES["production_line"][index]
        decision = MacroDecision(
            production_line=production_line,
            worker_cap=4,
            cash_reserve=500,
            sell_style="IMMEDIATE",
            terminal_mode="NORMAL",
        )
        self.probe_features = features
        self.production_logits = np.asarray(logits[0], dtype=np.float32)
        self.selected_route = str(production_line.value)
        self.route = FixedEventProgramPolicy(
            decision, name=f"delayed_{self.selected_route.lower()}"
        )
        self.manager_decision_count = 1

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        from kaggle_environments.envs.kaggriculture import kaggriculture

        step = observation_step(observation)
        if step < self.probe_steps:
            action = kaggriculture.pass_agent(observation)
            self.probe_action_steps += 1
        else:
            if self.route is None:
                self._activate_route(observation)
            action = self.route.act(observation)
        self.action_steps += 1
        return action

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = ["DelayedTrainableEventProgramPolicy"]
