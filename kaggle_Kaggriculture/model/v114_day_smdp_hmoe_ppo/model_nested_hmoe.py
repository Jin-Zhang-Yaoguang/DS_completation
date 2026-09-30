"""Compact two-level Option -> Role autoregressive HMoE for V114.

The model is policy-only: it consumes encoded observations and never calls a
historical agent.  All 3 x 6 routes share one unit decoder and one market
decoder.  Route-specific behaviour enters only through small option-role
projections, keeping the parameter count and CPU training cost bounded.
"""

from __future__ import annotations

from typing import Optional

from flax import linen as nn
import jax.numpy as jnp

import action_space as space
import features


NUM_OPTIONS = 3
NUM_ROLES = 6
HIDDEN = 96
CORE_HIDDEN = 192
NUM_ROUTES = NUM_OPTIONS * NUM_ROLES


def _validate_teacher_pair(
    tokens: Optional[jnp.ndarray],
    quantities: Optional[jnp.ndarray],
    name: str,
) -> None:
    if (tokens is None) != (quantities is None):
        raise ValueError(
            f"{name}_teacher_tokens and {name}_teacher_quantities must be "
            "provided together"
        )


def _teacher_step(
    values: jnp.ndarray,
    slot: int,
    batch_size: int,
    slots: int,
    name: str,
) -> jnp.ndarray:
    """Return one teacher-forcing step as [B, option, role]."""

    if values.ndim == 2:
        if values.shape != (batch_size, slots):
            raise ValueError(
                f"{name} must have shape [B, {slots}] or "
                f"[B, {NUM_OPTIONS}, {NUM_ROLES}, {slots}], got {values.shape}"
            )
        return jnp.broadcast_to(
            values[:, slot, None, None],
            (batch_size, NUM_OPTIONS, NUM_ROLES),
        ).astype(jnp.int32)
    if values.ndim == 4:
        expected = (batch_size, NUM_OPTIONS, NUM_ROLES, slots)
        if values.shape != expected:
            raise ValueError(f"{name} must have shape {expected}, got {values.shape}")
        return values[..., slot].astype(jnp.int32)
    raise ValueError(
        f"{name} must be rank 2 or rank 4, got rank {values.ndim}"
    )


class NestedHMoEActorCritic(nn.Module):
    """Two-level Option -> Role actor-critic with shared sequence decoders."""

    timed: bool = False
    market_memory_features: int = 0

    @nn.compact
    def __call__(
        self,
        global_state,
        board,
        units,
        unit_mask,
        unit_teacher_tokens=None,
        unit_teacher_quantities=None,
        market_teacher_tokens=None,
        market_teacher_quantities=None,
    ):
        _validate_teacher_pair(
            unit_teacher_tokens, unit_teacher_quantities, "unit"
        )
        _validate_teacher_pair(
            market_teacher_tokens, market_teacher_quantities, "market"
        )

        own_board, opponent_board = board[:, 0], board[:, 1]
        if self.market_memory_features:
            base_global = global_state[:, :-self.market_memory_features]
            market_memory = global_state[:, -self.market_memory_features:]
        else:
            base_global = global_state
            market_memory = None

        own_board_h = nn.relu(
            nn.Conv(24, (3, 3), padding="SAME", name="own_board_conv1")(
                own_board
            )
        )
        own_board_h = nn.relu(
            nn.Conv(32, (3, 3), padding="SAME", name="own_board_conv2")(
                own_board_h
            )
        )
        own_board_h = jnp.mean(own_board_h, axis=(1, 2))

        own_global = base_global.at[:, 10:16].set(0.0)
        own_global_h = nn.relu(
            nn.Dense(HIDDEN, name="own_global_dense")(own_global)
        )
        if self.timed:
            step_index = jnp.clip(
                jnp.rint(base_global[:, 0] * 30.0).astype(jnp.int32) * 24
                + jnp.rint(base_global[:, 1] * 24.0).astype(jnp.int32),
                0,
                719,
            )
            step_embedding = self.param(
                "season_step_embedding",
                nn.initializers.normal(0.02),
                (720, HIDDEN),
            )
            own_global_h = own_global_h + step_embedding[step_index]

        unit_h = nn.relu(nn.Dense(HIDDEN, name="unit_dense")(units))
        unit_identity = self.param(
            "unit_identity_embedding",
            nn.initializers.normal(0.02),
            (features.MAX_UNITS, HIDDEN),
        )
        unit_h = unit_h + unit_identity[None]
        attention_mask = nn.make_attention_mask(unit_mask, unit_mask)
        attended = nn.SelfAttention(
            num_heads=4,
            qkv_features=HIDDEN,
            out_features=HIDDEN,
            dropout_rate=0.0,
            deterministic=True,
            name="unit_self_attention",
        )(unit_h, mask=attention_mask)
        unit_h = nn.relu(unit_h + attended) * unit_mask[..., None]
        pooled_units = jnp.sum(
            unit_h * unit_mask[..., None], axis=1
        ) / jnp.maximum(1.0, jnp.sum(unit_mask, axis=1, keepdims=True))
        own_core = nn.relu(
            nn.Dense(CORE_HIDDEN, name="own_core_dense")(
                jnp.concatenate(
                    (own_global_h, own_board_h, pooled_units), axis=-1
                )
            )
        )

        opponent_board_h = nn.relu(
            nn.Conv(
                12,
                (3, 3),
                padding="SAME",
                name="opponent_board_conv",
            )(opponent_board)
        )
        opponent_board_h = jnp.mean(opponent_board_h, axis=(1, 2))
        opponent_h = nn.tanh(
            nn.Dense(CORE_HIDDEN, name="opponent_projection")(
                jnp.concatenate(
                    (base_global[:, 10:16], opponent_board_h), axis=-1
                )
            )
        )
        opponent_gate = 0.1 * nn.sigmoid(
            nn.Dense(
                1,
                kernel_init=nn.initializers.zeros,
                bias_init=nn.initializers.constant(-4.0),
                name="opponent_residual_gate",
            )(own_core)
        )
        fused_core = own_core + opponent_gate * opponent_h

        option_router_logits = nn.Dense(
            NUM_OPTIONS, name="option_router_head"
        )(fused_core)
        manager_h = nn.tanh(
            nn.Dense(HIDDEN, name="manager_projection")(fused_core)
        )
        option_embedding = self.param(
            "option_embedding",
            nn.initializers.normal(0.02),
            (NUM_OPTIONS, HIDDEN),
        )
        option_h = nn.tanh(manager_h[:, None, :] + option_embedding[None])

        unit_role_router_logits = nn.Dense(
            NUM_ROLES, name="unit_role_router_head"
        )(option_h)
        if market_memory is not None:
            market_memory_h = nn.tanh(
                nn.Dense(
                    HIDDEN,
                    kernel_init=nn.initializers.zeros,
                    bias_init=nn.initializers.zeros,
                    name="market_memory_dense",
                )(market_memory)
            )
            market_option_h = nn.tanh(option_h + market_memory_h[:, None, :])
        else:
            market_option_h = option_h
        market_role_router_logits = nn.Dense(
            NUM_ROLES, name="market_role_router_head"
        )(market_option_h)

        option_value = nn.Dense(1, name="option_value_head")(option_h)[..., 0]
        catastrophe_logits = nn.Dense(
            1, name="catastrophe_head"
        )(option_h)[..., 0]

        # Route identity is represented only by these compact projections.
        # The GRU cells, embeddings and action heads below are shared by all
        # NUM_OPTIONS * NUM_ROLES paths.
        unit_option_role_projection = self.param(
            "unit_option_role_projection",
            nn.initializers.normal(0.02),
            (NUM_OPTIONS, NUM_ROLES, HIDDEN),
        )
        market_option_role_projection = self.param(
            "market_option_role_projection",
            nn.initializers.normal(0.02),
            (NUM_OPTIONS, NUM_ROLES, HIDDEN),
        )
        unit_decoder_base = nn.tanh(
            nn.Dense(HIDDEN, name="unit_decoder_seed")(fused_core)
        )
        unit_route_h = nn.tanh(
            unit_decoder_base[:, None, None, :]
            + unit_option_role_projection[None]
        )

        unit_token_embedding = self.param(
            "unit_token_embedding",
            nn.initializers.normal(0.02),
            (len(space.UNIT_TOKENS), HIDDEN),
        )
        unit_quantity_embedding = self.param(
            "unit_quantity_embedding",
            nn.initializers.normal(0.02),
            (space.QUANTITY_DIM, HIDDEN),
        )
        unit_slot_embedding = self.param(
            "unit_slot_embedding",
            nn.initializers.normal(0.02),
            (features.MAX_UNITS, HIDDEN),
        )
        batch_size = global_state.shape[0]
        carry = unit_route_h.reshape((batch_size * NUM_ROUTES, HIDDEN))
        previous_token = jnp.zeros(
            (batch_size, NUM_OPTIONS, NUM_ROLES), dtype=jnp.int32
        )
        previous_quantity = jnp.zeros_like(previous_token)
        unit_gru = nn.GRUCell(features=HIDDEN, name="unit_gru")
        unit_action_head = nn.Dense(
            len(space.UNIT_TOKENS), name="unit_action_head"
        )
        unit_quantity_head = nn.Dense(
            space.QUANTITY_DIM, name="unit_quantity_head"
        )
        unit_logits_rows = []
        unit_quantity_rows = []
        decoded_unit_tokens = []
        decoded_unit_quantities = []
        for slot in range(features.MAX_UNITS):
            current_unit = jnp.broadcast_to(
                unit_h[:, slot, None, None, :],
                (batch_size, NUM_OPTIONS, NUM_ROLES, HIDDEN),
            )
            decoder_input = (
                current_unit
                + unit_token_embedding[previous_token]
                + unit_quantity_embedding[previous_quantity]
                + unit_slot_embedding[slot][None, None, None, :]
            ).reshape((batch_size * NUM_ROUTES, HIDDEN))
            carry, decoded = unit_gru(carry, decoder_input)
            slot_logits = unit_action_head(decoded).reshape(
                (
                    batch_size,
                    NUM_OPTIONS,
                    NUM_ROLES,
                    len(space.UNIT_TOKENS),
                )
            )
            slot_quantities = unit_quantity_head(decoded).reshape(
                (batch_size, NUM_OPTIONS, NUM_ROLES, space.QUANTITY_DIM)
            )
            unit_logits_rows.append(slot_logits)
            unit_quantity_rows.append(slot_quantities)
            if unit_teacher_tokens is None:
                selected_token = jnp.argmax(slot_logits, axis=-1)
                selected_quantity = jnp.argmax(slot_quantities, axis=-1)
            else:
                selected_token = _teacher_step(
                    unit_teacher_tokens,
                    slot,
                    batch_size,
                    features.MAX_UNITS,
                    "unit_teacher_tokens",
                )
                selected_quantity = _teacher_step(
                    unit_teacher_quantities,
                    slot,
                    batch_size,
                    features.MAX_UNITS,
                    "unit_teacher_quantities",
                )
            decoded_unit_tokens.append(selected_token)
            decoded_unit_quantities.append(selected_quantity)
            previous_token = selected_token
            previous_quantity = selected_quantity

        unit_logits = jnp.stack(unit_logits_rows, axis=3)
        unit_quantity_logits = jnp.stack(unit_quantity_rows, axis=3)
        unit_sequence_tokens = jnp.stack(decoded_unit_tokens, axis=3)
        unit_sequence_quantities = jnp.stack(decoded_unit_quantities, axis=3)
        unit_sequence_h = jnp.mean(
            unit_token_embedding[unit_sequence_tokens]
            + unit_quantity_embedding[unit_sequence_quantities],
            axis=3,
        )

        market_token_embedding = self.param(
            "market_token_embedding",
            nn.initializers.normal(0.02),
            (len(space.MARKET_TOKENS), HIDDEN),
        )
        market_quantity_embedding = self.param(
            "market_quantity_embedding",
            nn.initializers.normal(0.02),
            (space.QUANTITY_DIM, HIDDEN),
        )
        market_slot_embedding = self.param(
            "market_slot_embedding",
            nn.initializers.normal(0.02),
            (space.MAX_MARKET_SLOTS, HIDDEN),
        )
        market_decoder_base = nn.tanh(
            nn.Dense(HIDDEN, name="market_decoder_seed")(fused_core)
        )
        market_route_h = nn.tanh(
            market_decoder_base[:, None, None, :]
            + market_option_role_projection[None]
        )
        carry = nn.tanh(
            nn.Dense(HIDDEN, name="market_unit_bridge")(
                market_route_h + unit_sequence_h
            )
        ).reshape((batch_size * NUM_ROUTES, HIDDEN))
        previous_token = jnp.zeros(
            (batch_size, NUM_OPTIONS, NUM_ROLES), dtype=jnp.int32
        )
        previous_quantity = jnp.zeros_like(previous_token)
        market_gru = nn.GRUCell(features=HIDDEN, name="market_gru")
        market_action_head = nn.Dense(
            len(space.MARKET_TOKENS), name="market_action_head"
        )
        market_quantity_head = nn.Dense(
            space.QUANTITY_DIM, name="market_quantity_head"
        )
        market_logits_rows = []
        market_quantity_rows = []
        decoded_market_tokens = []
        decoded_market_quantities = []
        for slot in range(space.MAX_MARKET_SLOTS):
            decoder_input = (
                market_token_embedding[previous_token]
                + market_quantity_embedding[previous_quantity]
                + market_slot_embedding[slot][None, None, None, :]
            ).reshape((batch_size * NUM_ROUTES, HIDDEN))
            carry, decoded = market_gru(carry, decoder_input)
            slot_logits = market_action_head(decoded).reshape(
                (
                    batch_size,
                    NUM_OPTIONS,
                    NUM_ROLES,
                    len(space.MARKET_TOKENS),
                )
            )
            slot_quantities = market_quantity_head(decoded).reshape(
                (batch_size, NUM_OPTIONS, NUM_ROLES, space.QUANTITY_DIM)
            )
            market_logits_rows.append(slot_logits)
            market_quantity_rows.append(slot_quantities)
            if market_teacher_tokens is None:
                selected_token = jnp.argmax(slot_logits, axis=-1)
                selected_quantity = jnp.argmax(slot_quantities, axis=-1)
            else:
                selected_token = _teacher_step(
                    market_teacher_tokens,
                    slot,
                    batch_size,
                    space.MAX_MARKET_SLOTS,
                    "market_teacher_tokens",
                )
                selected_quantity = _teacher_step(
                    market_teacher_quantities,
                    slot,
                    batch_size,
                    space.MAX_MARKET_SLOTS,
                    "market_teacher_quantities",
                )
            decoded_market_tokens.append(selected_token)
            decoded_market_quantities.append(selected_quantity)
            previous_token = selected_token
            previous_quantity = selected_quantity

        return {
            "option_router_logits": option_router_logits,
            "unit_role_router_logits": unit_role_router_logits,
            "market_role_router_logits": market_role_router_logits,
            "unit_logits": unit_logits,
            "unit_quantity_logits": unit_quantity_logits,
            "market_logits": jnp.stack(market_logits_rows, axis=3),
            "market_quantity_logits": jnp.stack(
                market_quantity_rows, axis=3
            ),
            "unit_sequence_tokens": unit_sequence_tokens,
            "unit_sequence_quantities": unit_sequence_quantities,
            "market_sequence_tokens": jnp.stack(
                decoded_market_tokens, axis=3
            ),
            "market_sequence_quantities": jnp.stack(
                decoded_market_quantities, axis=3
            ),
            "option_value": option_value,
            "catastrophe_logits": catastrophe_logits,
        }


# Descriptive alias for callers that want the sequence nature in the name.
NestedSequenceActionHMoEActorCritic = NestedHMoEActorCritic
NestedOptionRoleHMoE = NestedHMoEActorCritic
