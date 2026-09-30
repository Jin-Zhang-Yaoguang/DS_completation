"""Randomly initialized V9 event-program PPO Manager.

The network emits five independent categorical heads plus reward and
constraint values.  It has no import, checkpoint path, parameter adapter, or
fallback connected to V6/V8 or any historical policy.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flax import linen as nn
import jax.numpy as jnp

from event_ppo_math import HEAD_SIZES


CHECKPOINT_SCHEMA = "kaggriculture-v114-event-program-ppo-v9-checkpoint-v1"
MODEL_ID = "v114-v9-event-program-ppo-manager"
ARCHITECTURE = "event-encoder-five-head-factorized-manager-v1"


class EventProgramPPOManager(nn.Module):
    """Five-head factorized Manager with separate value predictions."""

    hidden_sizes: tuple[int, ...] = (256, 192, 128)

    @nn.compact
    def __call__(self, manager_state: jnp.ndarray) -> dict[str, Any]:
        if manager_state.ndim != 2:
            raise ValueError("manager_state must have shape [B, features]")
        hidden = manager_state.astype(jnp.float32)
        for index, width in enumerate(self.hidden_sizes):
            residual = hidden
            hidden = nn.Dense(
                width,
                kernel_init=nn.initializers.orthogonal(jnp.sqrt(2.0)),
                name=f"trunk_dense_{index}",
            )(hidden)
            hidden = nn.LayerNorm(name=f"trunk_norm_{index}")(hidden)
            hidden = nn.tanh(hidden)
            if residual.shape[-1] == width:
                hidden = (hidden + residual) / jnp.sqrt(2.0)

        actor_logits = {
            name: nn.Dense(
                size,
                kernel_init=nn.initializers.orthogonal(0.01),
                bias_init=nn.initializers.zeros,
                name=f"{name}_head",
            )(hidden)
            for name, size in HEAD_SIZES.items()
        }
        value = nn.Dense(
            1,
            kernel_init=nn.initializers.orthogonal(1.0),
            bias_init=nn.initializers.zeros,
            name="value_head",
        )(hidden)[..., 0]
        constraint_value = nn.Dense(
            1,
            kernel_init=nn.initializers.orthogonal(1.0),
            bias_init=nn.initializers.zeros,
            name="constraint_value_head",
        )(hidden)[..., 0]
        return {
            "actor_logits": actor_logits,
            "value": value,
            "constraint_value": constraint_value,
        }


def checkpoint_metadata() -> dict[str, Any]:
    """Return the immutable V9 independent-lineage checkpoint contract."""

    return {
        "schema": CHECKPOINT_SCHEMA,
        "model_id": MODEL_ID,
        "architecture": ARCHITECTURE,
        "strategy_parent": None,
        "parent_checkpoint_sha256": None,
        "parameter_initialization": "random_v9",
        "loads_historical_policy_parameters": False,
        "uses_historical_agent_fallback": False,
        "head_sizes": dict(HEAD_SIZES),
        "framework": "jax_flax",
    }


def validate_checkpoint_metadata(metadata: Mapping[str, Any]) -> None:
    """Reject inherited or mislabeled checkpoints before deserialization."""

    expected = checkpoint_metadata()
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(
                f"invalid V9 checkpoint metadata: {key} must equal {value!r}"
            )
    for key in (
        "source_checkpoint",
        "initial_checkpoint",
        "teacher_checkpoint",
        "fallback_agent",
    ):
        if metadata.get(key) not in (None, ""):
            raise ValueError(f"V9 checkpoint must not define {key}")
    for value in metadata.values():
        if isinstance(value, str) and "v6" in value.lower():
            raise ValueError("V9 checkpoint metadata must not reference V6")


def make_checkpoint_payload(params: Any) -> dict[str, Any]:
    """Package parameters without introducing any parent checkpoint field."""

    return {**checkpoint_metadata(), "params": params}

