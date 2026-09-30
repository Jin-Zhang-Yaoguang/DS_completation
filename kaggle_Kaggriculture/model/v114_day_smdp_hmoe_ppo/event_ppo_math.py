"""Pure-JAX probability and SMDP PPO math for the V114 V9 Manager.

This module deliberately contains no environment runner, replay adapter, or
historical-policy loading path.  Masks are validated on the host before a
compiled update; the numerical kernels then receive one shared mask tree for
both the old and new policies.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import jax
import jax.numpy as jnp
import numpy as np


HEAD_SIZES: dict[str, int] = {
    "production_line": 5,
    "worker_cap": 3,
    "cash_reserve": 3,
    "sell_style": 3,
    "terminal_mode": 2,
}
HEAD_NAMES: tuple[str, ...] = tuple(HEAD_SIZES)
MASKED_LOGIT = -1.0e9


def validate_action_masks(
    masks: Mapping[str, Any],
    *,
    batch_size: int | None = None,
) -> None:
    """Fail closed when a factorized action mask violates the V9 contract."""

    if set(masks) != set(HEAD_NAMES):
        raise ValueError(f"masks must contain exactly {HEAD_NAMES}")
    inferred_batch = batch_size
    for name in HEAD_NAMES:
        mask = np.asarray(masks[name])
        if mask.ndim != 2 or mask.shape[1] != HEAD_SIZES[name]:
            raise ValueError(
                f"{name} mask must have shape [B, {HEAD_SIZES[name]}], "
                f"got {mask.shape}"
            )
        if inferred_batch is None:
            inferred_batch = int(mask.shape[0])
        if mask.shape[0] != inferred_batch:
            raise ValueError("all action masks must use the same batch size")
        if mask.dtype != np.bool_:
            raise ValueError(f"{name} mask must have boolean dtype")
        if not np.all(np.any(mask, axis=-1)):
            raise ValueError(f"{name} mask has a row with no legal action")


def validate_shared_masks(
    old_masks: Mapping[str, Any],
    new_masks: Mapping[str, Any],
) -> None:
    """Require old/new PPO policies to use byte-identical legal masks.

    Call this once before entering a jitted optimization step.  The compiled
    step should then accept only one ``shared_masks`` tree.
    """

    validate_action_masks(old_masks)
    validate_action_masks(new_masks)
    for name in HEAD_NAMES:
        if not np.array_equal(np.asarray(old_masks[name]), np.asarray(new_masks[name])):
            raise ValueError(f"old/new action masks differ for head {name}")


def _masked_logits(logits: jnp.ndarray, mask: jnp.ndarray) -> jnp.ndarray:
    return jnp.where(mask, logits, jnp.asarray(MASKED_LOGIT, logits.dtype))


def masked_categorical_log_probability(
    logits: jnp.ndarray,
    actions: jnp.ndarray,
    mask: jnp.ndarray,
) -> jnp.ndarray:
    """Log probability of selected legal categorical actions."""

    log_probabilities = jax.nn.log_softmax(_masked_logits(logits, mask), axis=-1)
    return jnp.take_along_axis(
        log_probabilities, actions.astype(jnp.int32)[..., None], axis=-1
    )[..., 0]


def masked_categorical_entropy(
    logits: jnp.ndarray,
    mask: jnp.ndarray,
) -> jnp.ndarray:
    masked = _masked_logits(logits, mask)
    log_probabilities = jax.nn.log_softmax(masked, axis=-1)
    probabilities = jnp.where(mask, jnp.exp(log_probabilities), 0.0)
    return -jnp.sum(probabilities * log_probabilities, axis=-1)


def masked_categorical_kl(
    old_logits: jnp.ndarray,
    new_logits: jnp.ndarray,
    shared_mask: jnp.ndarray,
) -> jnp.ndarray:
    """Exact KL(old || new) under a prevalidated shared mask."""

    old_logp = jax.nn.log_softmax(
        _masked_logits(old_logits, shared_mask), axis=-1
    )
    new_logp = jax.nn.log_softmax(
        _masked_logits(new_logits, shared_mask), axis=-1
    )
    old_probability = jnp.where(shared_mask, jnp.exp(old_logp), 0.0)
    return jnp.sum(old_probability * (old_logp - new_logp), axis=-1)


def factorized_log_probability_entropy(
    logits: Mapping[str, jnp.ndarray],
    actions: Mapping[str, jnp.ndarray],
    shared_masks: Mapping[str, jnp.ndarray],
) -> tuple[jnp.ndarray, jnp.ndarray, dict[str, jnp.ndarray]]:
    """Return joint log-probability, joint entropy, and per-head log-probs."""

    per_head = {
        name: masked_categorical_log_probability(
            logits[name], actions[name], shared_masks[name]
        )
        for name in HEAD_NAMES
    }
    joint_logp = sum(per_head.values(), jnp.asarray(0.0, jnp.float32))
    joint_entropy = sum(
        (
            masked_categorical_entropy(logits[name], shared_masks[name])
            for name in HEAD_NAMES
        ),
        jnp.zeros_like(joint_logp),
    )
    return joint_logp, joint_entropy, per_head


def sample_factorized_actions(
    key: jax.Array,
    logits: Mapping[str, jnp.ndarray],
    shared_masks: Mapping[str, jnp.ndarray],
) -> tuple[dict[str, jnp.ndarray], jnp.ndarray, jnp.ndarray]:
    """Sample all five heads and return actions, joint log-prob, entropy."""

    keys = jax.random.split(key, len(HEAD_NAMES))
    actions = {
        name: jax.random.categorical(
            head_key, _masked_logits(logits[name], shared_masks[name]), axis=-1
        ).astype(jnp.int32)
        for name, head_key in zip(HEAD_NAMES, keys, strict=True)
    }
    joint_logp, joint_entropy, _ = factorized_log_probability_entropy(
        logits, actions, shared_masks
    )
    return actions, joint_logp, joint_entropy


def factorized_exact_kl(
    old_logits: Mapping[str, jnp.ndarray],
    new_logits: Mapping[str, jnp.ndarray],
    shared_masks: Mapping[str, jnp.ndarray],
) -> jnp.ndarray:
    """Sum exact per-head KL values into the joint policy KL."""

    return sum(
        (
            masked_categorical_kl(
                old_logits[name], new_logits[name], shared_masks[name]
            )
            for name in HEAD_NAMES
        ),
        jnp.zeros(old_logits[HEAD_NAMES[0]].shape[:-1], dtype=jnp.float32),
    )


def duration_aware_smdp_gae(
    rewards: jnp.ndarray,
    values: jnp.ndarray,
    next_values: jnp.ndarray,
    terminals: jnp.ndarray,
    durations_turns: jnp.ndarray,
    *,
    gamma_day: float = 0.99,
    lambda_day: float = 0.95,
) -> dict[str, jnp.ndarray]:
    """Compute SMDP GAE with gamma and lambda scaled by duration/24.

    Arrays use time as their leading dimension.  Rewards must already be the
    discounted reward accumulated inside each event interval.
    """

    rewards = jnp.asarray(rewards, dtype=jnp.float32)
    values = jnp.asarray(values, dtype=jnp.float32)
    next_values = jnp.asarray(next_values, dtype=jnp.float32)
    terminals = jnp.asarray(terminals, dtype=jnp.float32)
    durations_turns = jnp.asarray(durations_turns, dtype=jnp.float32)
    if rewards.shape != values.shape or rewards.shape != next_values.shape:
        raise ValueError("rewards, values, and next_values must share shape")
    if rewards.shape != terminals.shape or rewards.shape != durations_turns.shape:
        raise ValueError("terminals and durations_turns must match rewards")

    gamma_discounts = jnp.power(
        jnp.asarray(gamma_day, jnp.float32), durations_turns / 24.0
    )
    lambda_discounts = jnp.power(
        jnp.asarray(lambda_day, jnp.float32), durations_turns / 24.0
    )
    not_terminal = 1.0 - terminals
    deltas = rewards + not_terminal * gamma_discounts * next_values - values

    def reverse_step(next_advantage, row):
        delta, gamma_discount, lambda_discount, alive = row
        advantage = (
            delta
            + alive * gamma_discount * lambda_discount * next_advantage
        )
        return advantage, advantage

    _, advantages = jax.lax.scan(
        reverse_step,
        jnp.zeros_like(deltas[-1]),
        (deltas, gamma_discounts, lambda_discounts, not_terminal),
        reverse=True,
    )
    return {
        "advantages": advantages,
        "returns": advantages + values,
        "deltas": deltas,
        "gamma_discounts": gamma_discounts,
        "lambda_discounts": lambda_discounts,
    }


def ppo_clipped_loss(
    new_joint_logp: jnp.ndarray,
    old_joint_logp: jnp.ndarray,
    advantages: jnp.ndarray,
    joint_entropy: jnp.ndarray,
    *,
    clip_epsilon: float = 0.2,
    entropy_coefficient: float = 0.0,
    exact_kl: jnp.ndarray | None = None,
) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
    """Differentiable PPO clipped actor loss with KL diagnostics."""

    log_ratio = new_joint_logp - jax.lax.stop_gradient(old_joint_logp)
    ratio = jnp.exp(log_ratio)
    unclipped = ratio * advantages
    clipped = jnp.clip(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon) * advantages
    policy_loss = -jnp.mean(jnp.minimum(unclipped, clipped))
    mean_entropy = jnp.mean(joint_entropy)
    loss = policy_loss - entropy_coefficient * mean_entropy
    approximate_kl = jnp.mean(
        (jnp.exp(log_ratio) - 1.0) - log_ratio
    )
    metrics = {
        "loss": loss,
        "policy_loss": policy_loss,
        "entropy": mean_entropy,
        "approximate_kl": approximate_kl,
        "clip_fraction": jnp.mean(
            (jnp.abs(ratio - 1.0) > clip_epsilon).astype(jnp.float32)
        ),
        "mean_ratio": jnp.mean(ratio),
    }
    if exact_kl is not None:
        metrics["exact_kl"] = jnp.mean(exact_kl)
    return loss, metrics


def factorized_ppo_loss(
    old_logits: Mapping[str, jnp.ndarray],
    new_logits: Mapping[str, jnp.ndarray],
    actions: Mapping[str, jnp.ndarray],
    shared_masks: Mapping[str, jnp.ndarray],
    advantages: jnp.ndarray,
    *,
    clip_epsilon: float = 0.2,
    entropy_coefficient: float = 0.0,
) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
    """Pure-JAX factorized PPO kernel using one mask tree by construction."""

    old_joint_logp, _, _ = factorized_log_probability_entropy(
        old_logits, actions, shared_masks
    )
    new_joint_logp, joint_entropy, _ = factorized_log_probability_entropy(
        new_logits, actions, shared_masks
    )
    exact_kl = factorized_exact_kl(old_logits, new_logits, shared_masks)
    return ppo_clipped_loss(
        new_joint_logp,
        old_joint_logp,
        advantages,
        joint_entropy,
        clip_epsilon=clip_epsilon,
        entropy_coefficient=entropy_coefficient,
        exact_kl=exact_kl,
    )

