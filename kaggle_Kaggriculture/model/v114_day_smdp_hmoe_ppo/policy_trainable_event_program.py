"""On-policy day-level SMDP policy for the independent V114 V9 Manager.

The policy records the exact behavior-policy inputs and outputs used at each
day boundary.  It does not calculate advantages, shape rewards, or update
parameters; those responsibilities belong to a separately reviewed trainer.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
from typing import Any

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

try:
    from .event_ppo_math import (
        factorized_log_probability_entropy,
        sample_factorized_actions,
        validate_action_masks,
    )
    from .event_program import (
        TERMINAL_START_STEP,
        MacroActionMask,
        MacroDecision,
        MacroPlanExecutor,
        PlanState,
        ProductionLine,
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
    from .policy_event_program import PROCUREMENT_OPERATIONS
except ImportError:  # Direct-file imports used by local runners.
    from event_ppo_math import (  # type: ignore
        factorized_log_probability_entropy,
        sample_factorized_actions,
        validate_action_masks,
    )
    from event_program import (  # type: ignore
        TERMINAL_START_STEP,
        MacroActionMask,
        MacroDecision,
        MacroPlanExecutor,
        PlanState,
        ProductionLine,
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
    from policy_event_program import PROCUREMENT_OPERATIONS  # type: ignore


POLICY_SCHEMA = "kaggriculture-v114-event-program-on-policy-v1"
QUALIFIED_PRODUCTION_LINES = (
    ProductionLine.WHEAT,
    ProductionLine.TOMATO,
    ProductionLine.STRAWBERRY,
    ProductionLine.MELON,
)
REJECTED_PRODUCTION_LINES = (ProductionLine.CARROT,)
CATASTROPHE_REWARD = 3000.0


def _read(container: Any, key: str, default: Any = None) -> Any:
    if isinstance(container, Mapping):
        return container.get(key, default)
    getter = getattr(container, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(container, key, default)


def _own_money(observation: Any) -> float:
    """Return public own money or NaN when the observation does not expose it."""

    farms = list(_read(observation, "farms", []) or [])
    try:
        player = int(_read(observation, "player", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        return float("nan")
    if not 0 <= player < len(farms):
        return float("nan")
    money = _read(farms[player], "money", None)
    if money is None:
        return float("nan")
    try:
        value = float(money)
    except (TypeError, ValueError, OverflowError):
        return float("nan")
    return value if np.isfinite(value) else float("nan")


def qualified_macro_action_masks(observation: Mapping[str, Any]) -> dict[str, np.ndarray]:
    """Apply state legality and the preregistered V9-1 expert qualification gate.

    CARROT remains index 1 of the five-wide production head, but is never a
    legal PPO action because its fixed program failed V9-1 survival.
    """

    semantic = MacroActionMask.from_observation(observation)
    masks = macro_action_mask_arrays(semantic)
    production = masks["production_line"].copy()
    carrot_index = DECISION_HEAD_VALUES["production_line"].index(ProductionLine.CARROT)
    production[:, carrot_index] = False
    masks["production_line"] = production
    validate_action_masks(masks, batch_size=1)
    return masks


def _stable_u32(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big", signed=False)


def decision_key(
    policy_seed: int,
    rollout_seed: int,
    episode_key: str,
    decision_count: int,
) -> jax.Array:
    """Derive exploration only from explicit rollout identity and checkpoint seed."""

    key = jax.random.PRNGKey(int(policy_seed) & 0xFFFFFFFF)
    key = jax.random.fold_in(key, int(rollout_seed) & 0xFFFFFFFF)
    key = jax.random.fold_in(key, _stable_u32(str(episode_key)))
    return jax.random.fold_in(key, int(decision_count) & 0xFFFFFFFF)


class TrainableEventProgramPolicy:
    """Collect exact day-level behavior-policy transitions without training."""

    def __init__(
        self,
        checkpoint: str | Path,
        *,
        rollout_seed: int,
        episode_key: str,
        deterministic: bool = False,
    ) -> None:
        payload = serialization.msgpack_restore(Path(checkpoint).expanduser().read_bytes())
        validate_checkpoint_metadata(payload)
        if int(payload.get("input_dim", -1)) != MANAGER_FEATURE_DIM:
            raise ValueError("checkpoint input_dim does not match the 427-feature contract")
        if payload.get("feature_schema") != FEATURE_SCHEMA:
            raise ValueError("checkpoint feature schema does not match the policy")
        if "params" not in payload:
            raise ValueError("checkpoint has no Manager parameters")
        if not str(episode_key):
            raise ValueError("episode_key must be non-empty")

        self.params = payload["params"]
        self.policy_seed = int(payload["policy_seed"])
        self.rollout_seed = int(rollout_seed)
        self.episode_key = str(episode_key)
        self.deterministic = bool(deterministic)
        self.model = EventProgramPPOManager()
        self.executor = MacroPlanExecutor()
        self.state: PlanState | None = None
        self.transitions: list[dict[str, Any]] = []
        self.manager_decision_count = 0
        self.action_steps = 0
        self.contract_violation_count = 0
        self.terminal_procurement_count = 0
        self.last_observation: Mapping[str, Any] | None = None
        self._finalized = False

    def _boundary_record(self, observation: Mapping[str, Any]) -> tuple[MacroDecision, dict[str, Any]]:
        features = encode_event_program_features(
            observation,
            current_decision=self.state,
            current_event="DAY_BOUNDARY",
        )
        masks = qualified_macro_action_masks(observation)
        outputs = self.model.apply(
            {"params": self.params},
            jnp.asarray(features[None, :], dtype=jnp.float32),
        )
        key = decision_key(
            self.policy_seed,
            self.rollout_seed,
            self.episode_key,
            self.manager_decision_count,
        )
        jax_masks = {name: jnp.asarray(value) for name, value in masks.items()}
        if self.deterministic:
            actions = {
                name: jnp.argmax(
                    jnp.where(jax_masks[name], logits, -jnp.inf), axis=-1
                ).astype(jnp.int32)
                for name, logits in outputs["actor_logits"].items()
            }
            joint_logp, _, _ = factorized_log_probability_entropy(
                outputs["actor_logits"], actions, jax_masks
            )
        else:
            actions, joint_logp, _ = sample_factorized_actions(
                key, outputs["actor_logits"], jax_masks
            )
        action_indices = {name: int(value[0]) for name, value in actions.items()}
        selected = {
            name: DECISION_HEAD_VALUES[name][index]
            for name, index in action_indices.items()
        }
        decision = MacroDecision(**selected)
        semantic_mask = MacroActionMask.from_observation(observation)
        if not semantic_mask.allows(decision):
            raise RuntimeError("sampled macro decision violates state MacroActionMask")
        if decision.production_line in REJECTED_PRODUCTION_LINES:
            raise RuntimeError("sampled rejected CARROT production expert")

        record = {
            "schema": POLICY_SCHEMA,
            "features": np.asarray(features, dtype=np.float32),
            "masks": {
                name: np.asarray(value[0], dtype=np.bool_)
                for name, value in masks.items()
            },
            "actions": action_indices,
            "old_joint_logp": float(np.asarray(joint_logp[0])),
            "old_logits": {
                name: np.asarray(value[0], dtype=np.float32)
                for name, value in outputs["actor_logits"].items()
            },
            "value": float(np.asarray(outputs["value"][0])),
            "constraint_value": float(np.asarray(outputs["constraint_value"][0])),
            "action_selection": "masked_argmax" if self.deterministic else "categorical_sample",
            "start_step": int(observation_step(observation)),
            "start_day": int(observation_day(observation)),
            "own_money_start": _own_money(observation),
        }
        return decision, record

    @staticmethod
    def _close_transition(
        transition: dict[str, Any],
        *,
        end_step: int,
        end_observation: Any,
        next_value: float,
        next_constraint_value: float,
        terminal: bool,
    ) -> None:
        duration = int(end_step) - int(transition["start_step"])
        if duration <= 0:
            raise ValueError("SMDP transition duration must be positive")
        own_money_end = _own_money(end_observation)
        own_money_start = float(transition["own_money_start"])
        money_delta = (
            own_money_end - own_money_start
            if np.isfinite(own_money_start) and np.isfinite(own_money_end)
            else float("nan")
        )
        transition.update(
            {
                "end_step": int(end_step),
                "duration_turns": duration,
                "next_value": float(next_value),
                "next_constraint_value": float(next_constraint_value),
                "terminal": bool(terminal),
                "own_money_end": own_money_end,
                "reward_delta_money": money_delta,
                "training_reward_raw": money_delta,
                "training_reward_source": "public_own_money_delta",
            }
        )

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        if self._finalized:
            raise RuntimeError("cannot act after finalize_episode")
        step = observation_step(observation)
        day = observation_day(observation)
        hour = int(_read(observation, "hour", step % 24) or 0) % 24
        initial_boundary = self.state is None and step == 0 and hour == 0
        next_day_boundary = (
            self.state is not None
            and step < TERMINAL_START_STEP
            and hour == 0
            and day != self.state.decision_day
        )
        daily_decision: MacroDecision | None = None
        if self.state is None:
            if not initial_boundary:
                raise ValueError("policy must be initialized at step 0/hour 0")
            decision, record = self._boundary_record(observation)
            self.transitions.append(record)
            self.state = self.executor.activate(observation, decision)
        elif next_day_boundary:
            daily_decision, record = self._boundary_record(observation)
            previous = self.transitions[-1]
            self._close_transition(
                previous,
                end_step=step,
                end_observation=observation,
                next_value=float(record["value"]),
                next_constraint_value=float(record["constraint_value"]),
                terminal=False,
            )
            self.transitions.append(record)

        self.manager_decision_count = len(self.transitions)
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
        self.contract_violation_count += len(result.audit.get("violations", []) or [])
        if step >= TERMINAL_START_STEP:
            self.terminal_procurement_count += sum(
                bool(order and str(order[0]) in PROCUREMENT_OPERATIONS)
                for order in result.action.get("market", [])
            )
        self.action_steps += 1
        self.last_observation = observation
        return result.action

    def finalize_episode(
        self,
        *,
        candidate_reward: float,
        opponent_reward: float,
        final_observation: Any = None,
        terminal_step: int | None = None,
    ) -> list[dict[str, Any]]:
        """Seal pending intervals and attach unchanged episode outcomes."""

        if self._finalized:
            raise RuntimeError("episode has already been finalized")
        if not self.transitions:
            raise RuntimeError("cannot finalize an episode with no decisions")
        end_step = self.action_steps if terminal_step is None else int(terminal_step)
        observation = final_observation if final_observation is not None else self.last_observation
        if observation is None:
            raise RuntimeError("final observation is unavailable")
        self._close_transition(
            self.transitions[-1],
            end_step=end_step,
            end_observation=observation,
            next_value=0.0,
            next_constraint_value=0.0,
            terminal=True,
        )
        candidate = float(candidate_reward)
        opponent = float(opponent_reward)
        margin = candidate - opponent
        score = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
        catastrophe = candidate < CATASTROPHE_REWARD
        for transition in self.transitions:
            transition.update(
                {
                    "candidate_reward": candidate,
                    "opponent_reward": opponent,
                    "margin": margin,
                    "score": score,
                    "catastrophe": catastrophe,
                }
            )
        self._finalized = True
        return self.transitions

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = [
    "CATASTROPHE_REWARD",
    "POLICY_SCHEMA",
    "QUALIFIED_PRODUCTION_LINES",
    "REJECTED_PRODUCTION_LINES",
    "TrainableEventProgramPolicy",
    "decision_key",
    "qualified_macro_action_masks",
]
