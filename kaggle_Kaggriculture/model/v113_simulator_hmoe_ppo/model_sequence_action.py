"""Hierarchical MoE actor-critic with a fully autoregressive joint action decoder."""

from __future__ import annotations

from flax import linen as nn
import jax.numpy as jnp

import action_space as space
import features


NUM_EXPERTS = 6
HIDDEN = 128


class SequenceActionHMoEActorCritic(nn.Module):
    timed: bool = False
    market_memory_features: int = 0

    @nn.compact
    def __call__(
        self, global_state, board, units, unit_mask,
        unit_teacher_tokens=None, unit_teacher_quantities=None,
        market_teacher_tokens=None, market_teacher_quantities=None,
    ):
        own_board, opponent_board = board[:, 0], board[:, 1]
        if self.market_memory_features:
            base_global = global_state[:, :-self.market_memory_features]
            market_memory = global_state[:, -self.market_memory_features:]
        else:
            base_global = global_state
            market_memory = None
        own_board_h = nn.relu(nn.Conv(32, (3, 3), padding="SAME", name="own_board_conv1")(own_board))
        own_board_h = nn.relu(nn.Conv(48, (3, 3), padding="SAME", name="own_board_conv2")(own_board_h))
        own_board_h = jnp.mean(own_board_h, axis=(1, 2))
        own_global = base_global.at[:, 10:16].set(0.0)
        own_global_h = nn.relu(nn.Dense(HIDDEN, name="own_global_dense")(own_global))
        if self.timed:
            step_index = jnp.clip(
                jnp.rint(base_global[:, 0] * 30.0).astype(jnp.int32) * 24
                + jnp.rint(base_global[:, 1] * 24.0).astype(jnp.int32),
                0, 719,
            )
            step_embedding = self.param(
                "season_step_embedding", nn.initializers.normal(0.02), (720, HIDDEN)
            )
            own_global_h = own_global_h + step_embedding[step_index]
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
        opponent_board_h = nn.relu(nn.Conv(
            16, (3, 3), padding="SAME", name="opponent_board_conv"
        )(opponent_board))
        opponent_board_h = jnp.mean(opponent_board_h, axis=(1, 2))
        opponent_h = nn.tanh(nn.Dense(256, name="opponent_projection")(
            jnp.concatenate((base_global[:, 10:16], opponent_board_h), axis=-1)
        ))
        opponent_gate = 0.1 * nn.sigmoid(nn.Dense(
            1, kernel_init=nn.initializers.zeros,
            bias_init=nn.initializers.constant(-4.0), name="opponent_residual_gate",
        )(own_core))
        fused_core = own_core + opponent_gate * opponent_h

        unit_router_logits = nn.Dense(NUM_EXPERTS, name="unit_router_head")(fused_core)
        if market_memory is not None:
            market_memory_h = nn.tanh(nn.Dense(
                256, kernel_init=nn.initializers.zeros,
                bias_init=nn.initializers.zeros, name="market_memory_dense",
            )(market_memory))
            market_core = fused_core + market_memory_h
        else:
            market_core = fused_core
        market_router_logits = nn.Dense(NUM_EXPERTS, name="market_router_head")(market_core)
        unit_expert_h = nn.tanh(nn.Dense(
            NUM_EXPERTS * HIDDEN, name="unit_expert_projection"
        )(fused_core)).reshape((-1, NUM_EXPERTS, HIDDEN))
        market_expert_h = nn.tanh(nn.Dense(
            NUM_EXPERTS * HIDDEN, name="market_expert_projection"
        )(market_core)).reshape((-1, NUM_EXPERTS, HIDDEN))

        unit_token_embedding = self.param(
            "unit_token_embedding", nn.initializers.normal(0.02),
            (len(space.UNIT_TOKENS), HIDDEN),
        )
        unit_quantity_embedding = self.param(
            "unit_quantity_embedding", nn.initializers.normal(0.02),
            (space.QUANTITY_DIM, HIDDEN),
        )
        unit_slot_embedding = self.param(
            "unit_slot_embedding", nn.initializers.normal(0.02),
            (features.MAX_UNITS, HIDDEN),
        )
        batch_size = global_state.shape[0]
        carry = unit_expert_h.reshape((batch_size * NUM_EXPERTS, HIDDEN))
        previous_token = jnp.zeros((batch_size, NUM_EXPERTS), dtype=jnp.int32)
        previous_quantity = jnp.zeros((batch_size, NUM_EXPERTS), dtype=jnp.int32)
        unit_gru = nn.GRUCell(features=HIDDEN, name="unit_gru")
        unit_action_head = nn.Dense(len(space.UNIT_TOKENS), name="unit_action_head")
        unit_quantity_head = nn.Dense(space.QUANTITY_DIM, name="unit_quantity_head")
        unit_logits_rows, unit_quantity_rows = [], []
        decoded_unit_tokens, decoded_unit_quantities = [], []
        for slot in range(features.MAX_UNITS):
            current_unit = jnp.broadcast_to(
                unit_h[:, slot, None, :], (batch_size, NUM_EXPERTS, HIDDEN)
            )
            decoder_input = (
                current_unit + unit_token_embedding[previous_token]
                + unit_quantity_embedding[previous_quantity]
                + unit_slot_embedding[slot][None, None]
            ).reshape((batch_size * NUM_EXPERTS, HIDDEN))
            carry, decoded = unit_gru(carry, decoder_input)
            slot_logits = unit_action_head(decoded).reshape(
                (batch_size, NUM_EXPERTS, len(space.UNIT_TOKENS))
            )
            slot_quantities = unit_quantity_head(decoded).reshape(
                (batch_size, NUM_EXPERTS, space.QUANTITY_DIM)
            )
            unit_logits_rows.append(slot_logits)
            unit_quantity_rows.append(slot_quantities)
            if unit_teacher_tokens is None:
                selected_token = jnp.argmax(slot_logits, axis=-1)
                selected_quantity = jnp.argmax(slot_quantities, axis=-1)
            else:
                selected_token = jnp.broadcast_to(
                    unit_teacher_tokens[:, slot, None], (batch_size, NUM_EXPERTS)
                ).astype(jnp.int32)
                selected_quantity = jnp.broadcast_to(
                    unit_teacher_quantities[:, slot, None], (batch_size, NUM_EXPERTS)
                ).astype(jnp.int32)
            decoded_unit_tokens.append(selected_token)
            decoded_unit_quantities.append(selected_quantity)
            previous_token, previous_quantity = selected_token, selected_quantity
        unit_logits = jnp.stack(unit_logits_rows, axis=2)
        unit_quantity_logits = jnp.stack(unit_quantity_rows, axis=2)
        unit_sequence_tokens = jnp.stack(decoded_unit_tokens, axis=2)
        unit_sequence_quantities = jnp.stack(decoded_unit_quantities, axis=2)
        unit_sequence_h = jnp.mean(
            unit_token_embedding[unit_sequence_tokens]
            + unit_quantity_embedding[unit_sequence_quantities], axis=2,
        )

        market_token_embedding = self.param(
            "market_token_embedding", nn.initializers.normal(0.02),
            (len(space.MARKET_TOKENS), HIDDEN),
        )
        market_quantity_embedding = self.param(
            "market_quantity_embedding", nn.initializers.normal(0.02),
            (space.QUANTITY_DIM, HIDDEN),
        )
        market_slot_embedding = self.param(
            "market_slot_embedding", nn.initializers.normal(0.02),
            (space.MAX_MARKET_SLOTS, HIDDEN),
        )
        carry = nn.tanh(nn.Dense(HIDDEN, name="market_unit_bridge")(
            market_expert_h + unit_sequence_h
        )).reshape((batch_size * NUM_EXPERTS, HIDDEN))
        previous_token = jnp.zeros((batch_size, NUM_EXPERTS), dtype=jnp.int32)
        previous_quantity = jnp.zeros((batch_size, NUM_EXPERTS), dtype=jnp.int32)
        market_gru = nn.GRUCell(features=HIDDEN, name="market_gru")
        market_action_head = nn.Dense(len(space.MARKET_TOKENS), name="market_action_head")
        market_quantity_head = nn.Dense(space.QUANTITY_DIM, name="market_quantity_head")
        market_logits_rows, market_quantity_rows = [], []
        for slot in range(space.MAX_MARKET_SLOTS):
            decoder_input = (
                market_token_embedding[previous_token]
                + market_quantity_embedding[previous_quantity]
                + market_slot_embedding[slot][None, None]
            ).reshape((batch_size * NUM_EXPERTS, HIDDEN))
            carry, decoded = market_gru(carry, decoder_input)
            slot_logits = market_action_head(decoded).reshape(
                (batch_size, NUM_EXPERTS, len(space.MARKET_TOKENS))
            )
            slot_quantities = market_quantity_head(decoded).reshape(
                (batch_size, NUM_EXPERTS, space.QUANTITY_DIM)
            )
            market_logits_rows.append(slot_logits)
            market_quantity_rows.append(slot_quantities)
            if market_teacher_tokens is None:
                previous_token = jnp.argmax(slot_logits, axis=-1)
                previous_quantity = jnp.argmax(slot_quantities, axis=-1)
            else:
                previous_token = jnp.broadcast_to(
                    market_teacher_tokens[:, slot, None], (batch_size, NUM_EXPERTS)
                ).astype(jnp.int32)
                previous_quantity = jnp.broadcast_to(
                    market_teacher_quantities[:, slot, None], (batch_size, NUM_EXPERTS)
                ).astype(jnp.int32)

        return {
            "unit_router_logits": unit_router_logits,
            "market_router_logits": market_router_logits,
            "unit_expert_h": unit_expert_h,
            "market_expert_h": market_expert_h,
            "unit_logits": unit_logits,
            "unit_quantity_logits": unit_quantity_logits,
            "market_logits": jnp.stack(market_logits_rows, axis=2),
            "market_quantity_logits": jnp.stack(market_quantity_rows, axis=2),
            "value": nn.Dense(1, name="value_head")(fused_core)[..., 0],
            "opponent_next_delta": nn.Dense(6, name="opponent_prediction_head")(opponent_h),
            "opponent_gate": opponent_gate[..., 0],
        }
