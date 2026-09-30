"""Tests for full-information route PPO."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import jax
import jax.numpy as jnp
import numpy as np

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from model_event_program_ppo import EventProgramPPOManager  # noqa: E402
from train_counterfactual_route_ppo import (  # noqa: E402
    counterfactual_actor_loss,
    create_state,
    normalize_utility_by_layer,
    route_utility,
)
from train_event_program_headwise_ppo import parameter_root_changes  # noqa: E402


class CounterfactualObjectiveTest(unittest.TestCase):
    def test_better_route_receives_improving_gradient(self) -> None:
        old = jnp.asarray([[0.0, -9.0, 0.0, 0.0, 0.0]])
        mask = jnp.asarray([[True, False, True, True, True]])
        utility = jnp.asarray([[0.0, 0.0, 0.0, 0.0, 1.0]])

        def loss_fn(logits: jnp.ndarray) -> jnp.ndarray:
            loss, _ = counterfactual_actor_loss(
                logits, old, mask, utility,
                clip_epsilon=0.1, entropy_coefficient=0.0,
            )
            return loss

        gradient = jax.grad(loss_fn)(old)
        self.assertLess(float(gradient[0, 4]), 0.0)
        self.assertGreater(float(gradient[0, 0]), 0.0)

    def test_relative_utility_penalizes_opponent_growth(self) -> None:
        utility = route_utility(
            np.asarray([[0.0, 0.0]]),
            np.asarray([[12000.0, 10000.0]]),
            np.asarray([[200000.0, 30000.0]]),
            np.asarray([[False, False]]),
        )
        self.assertLess(float(utility[0, 0]), float(utility[0, 1]))

    def test_optimizer_freezes_every_root_except_production_head(self) -> None:
        model = EventProgramPPOManager()
        params = model.init(jax.random.key(7), jnp.zeros((4, 427)))['params']
        state = create_state(params, 1.0e-4)
        features = jnp.ones((4, 427)) * 0.01
        old = state.apply_fn({"params": state.params}, features)["actor_logits"]["production_line"]
        mask = jnp.asarray([[True, False, True, True, True]] * 4)
        utility = jnp.asarray([[0.0, 0.0, 0.0, 0.2, 1.0]] * 4)

        def loss_fn(tree):
            logits = state.apply_fn({"params": tree}, features)["actor_logits"]["production_line"]
            return counterfactual_actor_loss(
                logits, old, mask, utility,
                clip_epsilon=0.1, entropy_coefficient=0.01,
            )[0]

        gradients = jax.grad(loss_fn)(state.params)
        updated = state.apply_gradients(grads=gradients)
        changes = parameter_root_changes(params, updated.params)
        self.assertGreater(changes["production_line_head"], 0.0)
        for root, value in changes.items():
            if root != "production_line_head":
                self.assertEqual(value, 0.0, root)

    def test_layer_normalization_preserves_route_order_and_equalizes_scale(self) -> None:
        utility = np.asarray(
            [[1.0, 0.0, 3.0], [10.0, 0.0, 30.0], [2.0, 0.0, 4.0]],
            dtype=np.float32,
        )
        mask = np.asarray([[True, False, True]] * 3)
        layers = np.asarray(["small", "large", "small"])
        normalized, report = normalize_utility_by_layer(utility, mask, layers)

        self.assertTrue(np.all(np.argmax(normalized, axis=1) == 2))
        self.assertTrue(np.all(normalized[:, 1] == 0.0))
        self.assertEqual(report["small"]["contexts"], 2)
        self.assertEqual(report["large"]["contexts"], 1)
        for layer in ("small", "large"):
            rows = layers == layer
            active = normalized[rows][mask[rows]]
            self.assertAlmostEqual(float(np.std(active)), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
