"""From-scratch V12 event-routed transaction-intent HMoE."""

from __future__ import annotations

from flax import linen as nn
import jax.numpy as jnp

from build_event_market_dataset import EVENT_TYPES, QUANTITY_TIERS, TRANSACTION_HEADS


HIDDEN = 160


class EventMarketHMoE(nn.Module):
    """Hard event Router with separate procurement, liquidation and terminal experts."""

    @nn.compact
    def __call__(self, global_features, board, event_type):
        batch = global_features.shape[0]
        board_rows = board.astype(jnp.float32).reshape((batch * 2, *board.shape[2:]))
        board_h = nn.relu(nn.Conv(16, (3, 3), padding="SAME")(board_rows))
        board_h = nn.relu(nn.Conv(24, (3, 3), strides=(2, 2), padding="SAME")(board_h))
        board_h = jnp.mean(board_h, axis=(1, 2)).reshape((batch, 48))
        event_one_hot = jnp.eye(len(EVENT_TYPES), dtype=jnp.float32)[event_type.astype(jnp.int32)]
        hidden = jnp.concatenate((global_features.astype(jnp.float32), board_h, event_one_hot), axis=-1)
        hidden = nn.relu(nn.Dense(HIDDEN)(hidden))
        hidden = nn.relu(nn.Dense(HIDDEN)(hidden))
        router_logits = nn.Dense(len(EVENT_TYPES), name="event_router")(hidden)
        experts = nn.tanh(
            nn.Dense(len(EVENT_TYPES) * HIDDEN, name="event_experts")(hidden)
        ).reshape((batch, len(EVENT_TYPES), HIDDEN))
        presence_logits = nn.Dense(
            len(TRANSACTION_HEADS), name="presence_head"
        )(experts)
        quantity_logits = nn.Dense(
            len(TRANSACTION_HEADS) * len(QUANTITY_TIERS), name="quantity_head"
        )(experts).reshape((
            batch, len(EVENT_TYPES), len(TRANSACTION_HEADS), len(QUANTITY_TIERS)
        ))
        values = nn.Dense(1, name="event_value")(experts)[..., 0]
        batch_index = jnp.arange(batch, dtype=jnp.int32)
        selected = event_type.astype(jnp.int32)
        return {
            "router_logits": router_logits,
            "presence_logits": presence_logits[batch_index, selected],
            "quantity_logits": quantity_logits[batch_index, selected],
            "value": values[batch_index, selected],
        }
