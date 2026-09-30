"""Candidate-level SMDP PPO math for V12 persistent unit tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import jax
import jax.numpy as jnp
import numpy as np

from build_unit_task_dataset import ITEMS, TASK_OPERATIONS


MAX_CANDIDATES = 256
MASKED_LOGIT = -1.0e9


def candidate_arrays(tasks: Sequence[Any], *, maximum: int = MAX_CANDIDATES) -> dict[str, np.ndarray]:
    if not tasks or len(tasks) > maximum:
        raise ValueError(f"candidate count must be in 1..{maximum}")
    arrays = {
        "role": np.zeros(maximum, np.int16),
        "operation": np.zeros(maximum, np.int16),
        "item": np.zeros(maximum, np.int16),
        "quantity": np.zeros(maximum, np.int16),
        "target_x": np.zeros(maximum, np.int16),
        "target_y": np.zeros(maximum, np.int16),
        "duration": np.ones(maximum, np.int16),
        "use_item": np.zeros(maximum, np.bool_),
        "use_quantity": np.zeros(maximum, np.bool_),
        "mask": np.zeros(maximum, np.bool_),
    }
    for index, task in enumerate(tasks):
        arrays["role"][index] = int(task.role_index)
        arrays["operation"][index] = TASK_OPERATIONS.index(task.operation)
        arrays["item"][index] = ITEMS.index(task.item)
        arrays["quantity"][index] = int(task.quantity_index)
        arrays["target_x"][index] = int(task.target_x)
        arrays["target_y"][index] = int(task.target_y)
        arrays["duration"][index] = int(task.duration)
        arrays["use_item"][index] = task.operation in {"PLANT", "PICKUP", "PLACE"}
        arrays["use_quantity"][index] = task.operation in {"PICKUP", "PLACE"}
        arrays["mask"][index] = True
    return arrays


def _gather_role_head(values: jnp.ndarray, role: jnp.ndarray, choice: jnp.ndarray) -> jnp.ndarray:
    batch = jnp.arange(values.shape[0], dtype=jnp.int32)[:, None]
    return values[batch, role.astype(jnp.int32), choice.astype(jnp.int32)]


def score_candidates(
    outputs: Mapping[str, jnp.ndarray], candidates: Mapping[str, jnp.ndarray]
) -> jnp.ndarray:
    """Return one normalized-composite logit for every complete task candidate."""
    role = candidates["role"].astype(jnp.int32)
    batch = jnp.arange(role.shape[0], dtype=jnp.int32)[:, None]
    role_logp = jax.nn.log_softmax(outputs["role_logits"], axis=-1)[batch, role]
    score = role_logp
    for output_name, candidate_name in (
        ("operation_logits", "operation"),
        ("target_x_logits", "target_x"),
        ("target_y_logits", "target_y"),
        ("duration_logits", "duration"),
    ):
        score = score + _gather_role_head(
            jax.nn.log_softmax(outputs[output_name], axis=-1),
            role,
            candidates[candidate_name],
        )
    item_score = _gather_role_head(
        jax.nn.log_softmax(outputs["item_logits"], axis=-1), role, candidates["item"]
    )
    quantity_score = _gather_role_head(
        jax.nn.log_softmax(outputs["quantity_logits"], axis=-1), role, candidates["quantity"]
    )
    score = score + jnp.where(candidates["use_item"], item_score, 0.0)
    score = score + jnp.where(candidates["use_quantity"], quantity_score, 0.0)
    return jnp.where(candidates["mask"], score, jnp.asarray(MASKED_LOGIT, score.dtype))


def categorical_stats(
    candidate_logits: jnp.ndarray,
    actions: jnp.ndarray,
    mask: jnp.ndarray,
) -> tuple[jnp.ndarray, jnp.ndarray]:
    masked = jnp.where(mask, candidate_logits, jnp.asarray(MASKED_LOGIT, candidate_logits.dtype))
    logp = jax.nn.log_softmax(masked, axis=-1)
    selected = jnp.take_along_axis(logp, actions.astype(jnp.int32)[:, None], axis=-1)[:, 0]
    probability = jnp.where(mask, jnp.exp(logp), 0.0)
    entropy = -jnp.sum(probability * logp, axis=-1)
    return selected, entropy


def ppo_loss(
    new_logp: jnp.ndarray,
    old_logp: jnp.ndarray,
    advantage: jnp.ndarray,
    entropy: jnp.ndarray,
    *,
    clip_epsilon: float = 0.15,
    entropy_coefficient: float = 0.002,
) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
    log_ratio = new_logp - jax.lax.stop_gradient(old_logp)
    ratio = jnp.exp(log_ratio)
    unclipped = ratio * jax.lax.stop_gradient(advantage)
    clipped = jnp.clip(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * jax.lax.stop_gradient(advantage)
    actor = -jnp.mean(jnp.minimum(unclipped, clipped))
    mean_entropy = jnp.mean(entropy)
    return actor - entropy_coefficient * mean_entropy, {
        "actor_loss": actor,
        "entropy": mean_entropy,
        "approximate_kl": jnp.mean((ratio - 1.0) - log_ratio),
        "clip_fraction": jnp.mean((jnp.abs(ratio - 1.0) > clip_epsilon).astype(jnp.float32)),
    }
