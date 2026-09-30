"""V113 role-option Hierarchical MoE actor-critic."""

from __future__ import annotations

from flax import linen as nn
import jax.numpy as jnp

import action_space as space
import features


NUM_EXPERTS = 6
NUM_ROLES = 2
NUM_TARGETS = features.BOARD_SIZE * features.BOARD_SIZE
HIDDEN = 128


class RoleOptionHMoEActorCritic(nn.Module):
    @nn.compact
    def __call__(self, global_state, board, units, unit_mask, option_roles=None, option_targets=None):
        own_board, opponent_board = board[:, 0], board[:, 1]
        own_board_h = nn.relu(nn.Conv(32, (3, 3), padding="SAME", name="own_board_conv1")(own_board))
        own_board_h = nn.relu(nn.Conv(48, (3, 3), padding="SAME", name="own_board_conv2")(own_board_h))
        own_board_h = jnp.mean(own_board_h, axis=(1, 2))

        own_global = global_state.at[:, 10:16].set(0.0)
        own_global_h = nn.relu(nn.Dense(HIDDEN, name="own_global_dense")(own_global))
        unit_h = nn.relu(nn.Dense(HIDDEN, name="unit_dense")(units))
        unit_identity = self.param(
            "unit_identity_embedding", nn.initializers.normal(0.02),
            (features.MAX_UNITS, HIDDEN),
        )
        unit_h = unit_h + unit_identity[None]
        attention_mask = nn.make_attention_mask(unit_mask, unit_mask)
        attended = nn.SelfAttention(
            num_heads=4, qkv_features=HIDDEN, out_features=HIDDEN,
            dropout_rate=0.0, deterministic=True, name="unit_self_attention",
        )(unit_h, mask=attention_mask)
        unit_h = nn.relu(unit_h + attended) * unit_mask[..., None]
        pooled_units = jnp.sum(unit_h * unit_mask[..., None], axis=1) / jnp.maximum(
            1.0, jnp.sum(unit_mask, axis=1, keepdims=True)
        )
        own_core = nn.relu(nn.Dense(256, name="own_core_dense")(
            jnp.concatenate((own_global_h, own_board_h, pooled_units), axis=-1)
        ))

        opponent_board_h = nn.relu(nn.Conv(16, (3, 3), padding="SAME", name="opponent_board_conv")(opponent_board))
        opponent_board_h = jnp.mean(opponent_board_h, axis=(1, 2))
        opponent_h = nn.tanh(nn.Dense(256, name="opponent_projection")(
            jnp.concatenate((global_state[:, 10:16], opponent_board_h), axis=-1)
        ))
        gate = 0.1 * nn.sigmoid(nn.Dense(
            1, kernel_init=nn.initializers.zeros, bias_init=nn.initializers.constant(-4.0),
            name="opponent_residual_gate",
        )(own_core))
        fused_core = own_core + gate * opponent_h

        manager_context = nn.tanh(nn.Dense(HIDDEN, name="manager_core_projection")(fused_core))
        manager_h = nn.tanh(nn.Dense(HIDDEN, name="manager_unit_projection")(unit_h) + manager_context[:, None])
        option_role_logits = nn.Dense(NUM_ROLES, name="option_role_head")(manager_h)
        option_target_logits = nn.Dense(NUM_TARGETS, name="option_target_head")(manager_h)
        selected_roles = jnp.argmax(option_role_logits, axis=-1) if option_roles is None else option_roles.astype(jnp.int32)
        selected_targets = jnp.argmax(option_target_logits, axis=-1) if option_targets is None else option_targets.astype(jnp.int32)
        role_embedding = self.param("role_embedding", nn.initializers.normal(0.02), (NUM_ROLES, HIDDEN))
        target_embedding = self.param("target_embedding", nn.initializers.normal(0.02), (NUM_TARGETS, HIDDEN))
        option_h = role_embedding[selected_roles] + target_embedding[selected_targets]

        unit_router_logits = nn.Dense(NUM_EXPERTS, name="unit_router_head")(fused_core)
        market_router_logits = nn.Dense(NUM_EXPERTS, name="market_router_head")(fused_core)
        unit_expert_h = nn.tanh(nn.Dense(NUM_EXPERTS * HIDDEN, name="unit_expert_projection")(fused_core)).reshape(
            (-1, NUM_EXPERTS, HIDDEN)
        )
        market_expert_h = nn.tanh(nn.Dense(NUM_EXPERTS * HIDDEN, name="market_expert_projection")(fused_core)).reshape(
            (-1, NUM_EXPERTS, HIDDEN)
        )
        unit_query = nn.Dense(HIDDEN, name="unit_query")(unit_h) + option_h
        unit_joint = nn.tanh(unit_expert_h[:, :, None] + unit_query[:, None])
        unit_logits = nn.Dense(len(space.UNIT_TOKENS), name="unit_action_head")(unit_joint)
        unit_quantity_logits = nn.Dense(space.QUANTITY_DIM, name="unit_quantity_head")(unit_joint)

        slot_embedding = self.param(
            "market_slot_embedding", nn.initializers.normal(0.02),
            (space.MAX_MARKET_SLOTS, HIDDEN),
        )
        market_joint = nn.tanh(market_expert_h[:, :, None] + slot_embedding[None, None])
        market_logits = nn.Dense(len(space.MARKET_TOKENS), name="market_action_head")(market_joint)
        market_quantity_logits = nn.Dense(space.QUANTITY_DIM, name="market_quantity_head")(market_joint)
        return {
            "option_role_logits": option_role_logits,
            "option_target_logits": option_target_logits,
            "selected_roles": selected_roles,
            "selected_targets": selected_targets,
            "unit_router_logits": unit_router_logits,
            "market_router_logits": market_router_logits,
            "unit_expert_h": unit_expert_h,
            "market_expert_h": market_expert_h,
            "unit_logits": unit_logits,
            "unit_quantity_logits": unit_quantity_logits,
            "market_logits": market_logits,
            "market_quantity_logits": market_quantity_logits,
            "value": nn.Dense(1, name="value_head")(fused_core)[..., 0],
            "opponent_next_delta": nn.Dense(6, name="opponent_prediction_head")(opponent_h),
            "opponent_gate": gate[..., 0],
        }
