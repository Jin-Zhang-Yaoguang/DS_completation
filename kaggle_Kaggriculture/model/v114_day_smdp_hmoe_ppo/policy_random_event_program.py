"""Random-checkpoint policy for the independent event-program Manager."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from flax import serialization
import jax
import jax.numpy as jnp

try:
    from .event_ppo_math import sample_factorized_actions, validate_action_masks
    from .event_program import (
        TERMINAL_START_STEP,
        MacroActionMask,
        MacroDecision,
        MacroPlanExecutor,
        PlanState,
        observation_day,
        observation_step,
    )
    from .event_program_features import (
        DECISION_HEAD_VALUES,
        FEATURE_SCHEMA,
        MANAGER_FEATURE_DIM,
        encode_event_program_features,
        macro_action_mask_arrays,
    )
    from .model_event_program_ppo import (
        EventProgramPPOManager,
        validate_checkpoint_metadata,
    )
    from .policy_event_program import PROCUREMENT_OPERATIONS, decision_as_dict
except ImportError:  # Direct-file imports used by local runners.
    from event_ppo_math import (  # type: ignore
        sample_factorized_actions,
        validate_action_masks,
    )
    from event_program import (  # type: ignore
        TERMINAL_START_STEP,
        MacroActionMask,
        MacroDecision,
        MacroPlanExecutor,
        PlanState,
        observation_day,
        observation_step,
    )
    from event_program_features import (  # type: ignore
        DECISION_HEAD_VALUES,
        FEATURE_SCHEMA,
        MANAGER_FEATURE_DIM,
        encode_event_program_features,
        macro_action_mask_arrays,
    )
    from model_event_program_ppo import (  # type: ignore
        EventProgramPPOManager,
        validate_checkpoint_metadata,
    )
    from policy_event_program import (  # type: ignore
        PROCUREMENT_OPERATIONS,
        decision_as_dict,
    )


class RandomEventProgramPolicy:
    """Sample a legal macro decision at each pre-terminal day boundary."""

    def __init__(self, checkpoint: str | Path) -> None:
        payload = serialization.msgpack_restore(Path(checkpoint).expanduser().read_bytes())
        validate_checkpoint_metadata(payload)
        if int(payload.get("input_dim", -1)) != MANAGER_FEATURE_DIM:
            raise ValueError("checkpoint input_dim does not match the 427-feature contract")
        if payload.get("feature_schema") != FEATURE_SCHEMA:
            raise ValueError("checkpoint feature schema does not match the policy")
        if "params" not in payload:
            raise ValueError("checkpoint has no Manager parameters")
        self.params = payload["params"]
        self.policy_seed = int(payload["policy_seed"])
        self.model = EventProgramPPOManager()
        self.executor = MacroPlanExecutor()
        self.state: PlanState | None = None
        self.manager_decision_count = 0
        self.action_steps = 0
        self.contract_violation_count = 0
        self.terminal_procurement_count = 0
        self.head_usage = {
            name: Counter() for name in DECISION_HEAD_VALUES
        }
        self.last_audit: dict[str, Any] | None = None
        self.last_logits: dict[str, Any] | None = None

    def reset(self) -> None:
        self.state = None
        self.manager_decision_count = 0
        self.action_steps = 0
        self.contract_violation_count = 0
        self.terminal_procurement_count = 0
        self.head_usage = {name: Counter() for name in DECISION_HEAD_VALUES}
        self.last_audit = None
        self.last_logits = None

    @property
    def decision(self) -> dict[str, Any] | None:
        return None if self.state is None else decision_as_dict(self.state.decision)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "decision_count": self.manager_decision_count,
            "action_steps": self.action_steps,
            "head_usage": {
                name: dict(counter) for name, counter in self.head_usage.items()
            },
            "contract_violations": self.contract_violation_count,
            "terminal_procurement": self.terminal_procurement_count,
        }

    def _sample_decision(self, observation: Mapping[str, Any]) -> MacroDecision:
        mask = MacroActionMask.from_observation(observation)
        masks = macro_action_mask_arrays(mask)
        validate_action_masks(masks, batch_size=1)
        features = encode_event_program_features(
            observation,
            current_decision=self.state,
            current_event="DAY_BOUNDARY",
        )
        outputs = self.model.apply(
            {"params": self.params},
            jnp.asarray(features[None, :], dtype=jnp.float32),
        )
        key = jax.random.fold_in(
            jax.random.PRNGKey(self.policy_seed), self.manager_decision_count
        )
        actions, _, _ = sample_factorized_actions(
            key,
            outputs["actor_logits"],
            {name: jnp.asarray(value) for name, value in masks.items()},
        )
        indices = {name: int(value[0]) for name, value in actions.items()}
        selected = {
            name: DECISION_HEAD_VALUES[name][index]
            for name, index in indices.items()
        }
        decision = MacroDecision(**selected)
        if not mask.allows(decision):
            raise RuntimeError("sampled macro decision is outside MacroActionMask")
        for name, value in selected.items():
            self.head_usage[name][str(getattr(value, "value", value))] += 1
        self.last_logits = {
            name: jnp.asarray(value[0]).tolist()
            for name, value in outputs["actor_logits"].items()
        }
        self.manager_decision_count += 1
        return decision

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        step = observation_step(observation)
        day = observation_day(observation)
        hour = int(observation.get("hour", step % 24) or 0) % 24
        initial_boundary = self.state is None and step == 0 and hour == 0
        next_day_boundary = (
            self.state is not None
            and step < TERMINAL_START_STEP
            and hour == 0
            and day != self.state.decision_day
        )
        if self.state is None:
            if not initial_boundary:
                raise ValueError("policy must be initialized at step 0/hour 0")
            decision = self._sample_decision(observation)
            self.state = self.executor.activate(observation, decision)
            daily_decision = None
        elif next_day_boundary:
            daily_decision = self._sample_decision(observation)
        else:
            daily_decision = None

        try:
            result = self.executor.step(
                observation,
                self.state,
                daily_decision=daily_decision,
            )
        except Exception:
            self.contract_violation_count += 1
            raise
        self.state = result.state
        self.last_audit = dict(result.audit)
        self.contract_violation_count += len(result.audit.get("violations", []) or [])
        if step >= TERMINAL_START_STEP:
            self.terminal_procurement_count += sum(
                bool(order and str(order[0]) in PROCUREMENT_OPERATIONS)
                for order in result.action.get("market", [])
            )
        self.action_steps += 1
        return result.action

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = ["RandomEventProgramPolicy"]
