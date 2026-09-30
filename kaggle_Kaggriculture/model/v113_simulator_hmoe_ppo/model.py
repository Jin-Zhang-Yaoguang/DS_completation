"""Six-expert full-action Actor-Critic used by BC and PPO."""

from __future__ import annotations

from flax import linen as nn
import jax.numpy as jnp

import action_space as space
import features


NUM_EXPERTS = 6
HIDDEN = 128


class HMoEActorCritic(nn.Module):
    @nn.compact
    def __call__(self, global_state, board, units, unit_mask):
        board = board.transpose((0, 2, 3, 1, 4)).reshape((board.shape[0], features.BOARD_SIZE, features.BOARD_SIZE, -1))
        board_h = nn.relu(nn.Conv(32, (3, 3), padding="SAME", name="board_conv1")(board))
        board_h = nn.relu(nn.Conv(48, (3, 3), padding="SAME", name="board_conv2")(board_h))
        board_h = jnp.mean(board_h, axis=(1, 2))
        global_h = nn.relu(nn.Dense(HIDDEN, name="global_dense")(global_state))
        unit_h = nn.relu(nn.Dense(HIDDEN, name="unit_dense")(units))
        unit_identity = self.param("unit_identity_embedding", nn.initializers.normal(0.02), (features.MAX_UNITS, HIDDEN))
        unit_h = unit_h + unit_identity[None, :, :]
        attention_mask = nn.make_attention_mask(unit_mask, unit_mask)
        attended = nn.SelfAttention(
            num_heads=4, qkv_features=HIDDEN, out_features=HIDDEN,
            dropout_rate=0.0, deterministic=True, name="unit_self_attention",
        )(unit_h, mask=attention_mask)
        unit_h = nn.relu(unit_h + attended) * unit_mask[..., None]
        pooled_units = jnp.sum(unit_h * unit_mask[..., None], axis=1) / jnp.maximum(1.0, jnp.sum(unit_mask, axis=1, keepdims=True))
        core = jnp.concatenate((global_h, board_h, pooled_units), axis=-1)
        core = nn.relu(nn.Dense(256, name="core_dense")(core))
        router_logits = nn.Dense(NUM_EXPERTS, name="router_head")(core)
        expert_h = nn.Dense(NUM_EXPERTS * HIDDEN, name="expert_projection")(core).reshape((-1, NUM_EXPERTS, HIDDEN))
        expert_h = nn.tanh(expert_h)

        unit_query = nn.Dense(HIDDEN, name="unit_query")(unit_h)
        unit_joint = nn.tanh(expert_h[:, :, None, :] + unit_query[:, None, :, :])
        unit_logits = nn.Dense(len(space.UNIT_TOKENS), name="unit_action_head")(unit_joint)
        unit_quantity_logits = nn.Dense(space.QUANTITY_DIM, name="unit_quantity_head")(unit_joint)

        slot_embedding = self.param("market_slot_embedding", nn.initializers.normal(0.02), (space.MAX_MARKET_SLOTS, HIDDEN))
        market_joint = nn.tanh(expert_h[:, :, None, :] + slot_embedding[None, None, :, :])
        market_logits = nn.Dense(len(space.MARKET_TOKENS), name="market_action_head")(market_joint)
        market_quantity_logits = nn.Dense(space.QUANTITY_DIM, name="market_quantity_head")(market_joint)
        value = nn.Dense(1, name="value_head")(core)[..., 0]
        return {
            "router_logits": router_logits,
            "expert_h": expert_h,
            "unit_logits": unit_logits,
            "unit_quantity_logits": unit_quantity_logits,
            "market_logits": market_logits,
            "market_quantity_logits": market_quantity_logits,
            "value": value,
        }
