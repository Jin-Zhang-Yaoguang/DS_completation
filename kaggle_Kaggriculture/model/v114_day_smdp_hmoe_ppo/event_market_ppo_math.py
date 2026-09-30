"""Masked factorized PPO math for V12 event transaction intents."""

from __future__ import annotations

import jax
import jax.numpy as jnp


MASKED_LOGIT = -1.0e9


def calibrated_presence_logits(raw_logits, thresholds, mask, temperature=0.25):
    clipped = jnp.clip(thresholds, 1e-4, 1.0 - 1e-4)
    boundary = jnp.log(clipped) - jnp.log1p(-clipped)
    adjusted = (raw_logits - boundary) / temperature
    return jnp.where(mask, adjusted, jnp.asarray(MASKED_LOGIT, adjusted.dtype))


def factorized_logp_entropy(
    presence_logits,
    quantity_logits,
    presence_actions,
    quantity_actions,
    presence_mask,
    quantity_mask,
):
    presence_actions = presence_actions.astype(jnp.float32)
    presence_logp = -jax.nn.softplus(
        jnp.where(presence_actions > 0, -presence_logits, presence_logits)
    )
    presence_logp = jnp.where(presence_mask, presence_logp, 0.0)
    probability = jax.nn.sigmoid(presence_logits)
    presence_entropy = jnp.where(
        presence_mask,
        -probability * jax.nn.log_sigmoid(presence_logits)
        -(1.0 - probability) * jax.nn.log_sigmoid(-presence_logits),
        0.0,
    )
    masked_quantity = jnp.where(quantity_mask, quantity_logits, MASKED_LOGIT)
    quantity_logp_all = jax.nn.log_softmax(masked_quantity, axis=-1)
    quantity_logp = jnp.take_along_axis(
        quantity_logp_all, quantity_actions.astype(jnp.int32)[..., None], axis=-1
    )[..., 0]
    active_quantity = presence_mask & (presence_actions > 0)
    quantity_logp = jnp.where(active_quantity, quantity_logp, 0.0)
    quantity_probability = jnp.where(quantity_mask, jnp.exp(quantity_logp_all), 0.0)
    quantity_entropy = -jnp.sum(quantity_probability * quantity_logp_all, axis=-1)
    quantity_entropy = jnp.where(active_quantity, quantity_entropy, 0.0)
    return (
        jnp.sum(presence_logp + quantity_logp, axis=-1),
        jnp.sum(presence_entropy + quantity_entropy, axis=-1),
    )
