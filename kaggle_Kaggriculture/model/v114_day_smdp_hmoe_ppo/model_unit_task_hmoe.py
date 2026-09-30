"""From-scratch V12 persistent unit-task Hierarchical MoE."""

from __future__ import annotations

from flax import linen as nn
import jax.numpy as jnp

from build_unit_task_dataset import ITEMS, QUANTITY_TIERS, ROLE_NAMES, TASK_OPERATIONS


HIDDEN = 128
NUM_ROLES = len(ROLE_NAMES)


class UnitTaskHMoE(nn.Module):
    """Predict a durable task contract, never a one-step movement action."""

    @nn.compact
    def __call__(self, global_features, board, unit_features):
        global_features = global_features.astype(jnp.float32)
        board = board.astype(jnp.float32)
        unit_features = unit_features.astype(jnp.float32)
        batch = board.shape[0]
        board_rows = board.reshape((batch * 2, *board.shape[2:]))
        board_h = nn.relu(nn.Conv(16, (3, 3), strides=(1, 1), padding="SAME")(board_rows))
        board_h = nn.relu(nn.Conv(24, (3, 3), strides=(2, 2), padding="SAME")(board_h))
        board_h = jnp.mean(board_h, axis=(1, 2)).reshape((batch, 2 * 24))
        global_h = nn.relu(nn.Dense(64)(global_features))
        unit_h = nn.relu(nn.Dense(64)(unit_features))
        fused = nn.relu(nn.Dense(HIDDEN)(jnp.concatenate((global_h, board_h, unit_h), axis=-1)))
        fused = nn.relu(nn.Dense(HIDDEN)(fused))

        role_logits = nn.Dense(NUM_ROLES, name="role_router")(fused)
        expert_h = nn.tanh(
            nn.Dense(NUM_ROLES * HIDDEN, name="role_expert_projection")(fused)
        ).reshape((batch, NUM_ROLES, HIDDEN))

        def head(name: str, classes: int):
            return nn.Dense(NUM_ROLES * classes, name=name)(fused).reshape(
                (batch, NUM_ROLES, classes)
            ) + 0.15 * nn.Dense(classes, name=f"{name}_shared")(expert_h)

        return {
            "role_logits": role_logits,
            "operation_logits": head("operation_head", len(TASK_OPERATIONS)),
            "item_logits": head("item_head", len(ITEMS)),
            "quantity_logits": head("quantity_head", len(QUANTITY_TIERS)),
            "target_x_logits": head("target_x_head", 10),
            "target_y_logits": head("target_y_head", 10),
            "duration_logits": head("duration_head", 25),
            "value": nn.Dense(1, name="task_value")(fused)[:, 0],
        }
