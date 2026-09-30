"""Contract tests for V114 per-slot latent-role HMoE V6."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import jax
import jax.numpy as jnp
import numpy as np


V114_DIR = Path(__file__).resolve().parents[1]
V113_SHARED_DIR = V114_DIR.parent / "v113_simulator_hmoe_ppo"
for module_dir in (V113_SHARED_DIR, V114_DIR):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

import action_space as space  # noqa: E402
import features  # noqa: E402
from model_latent_role_hmoe import (  # noqa: E402
    NUM_MARKET_ROLES,
    NUM_OPTIONS,
    NUM_UNIT_ROLES,
    LatentRoleHMoE,
)


def parameter_count(tree) -> int:
    return sum(int(value.size) for value in jax.tree_util.tree_leaves(tree))


class LatentRoleHMoETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = 2
        rng = np.random.default_rng(11406)
        cls.inputs = {
            "global_state": jnp.asarray(
                rng.normal(size=(cls.batch, 32)).astype(np.float32)
            ),
            "board": jnp.asarray(
                rng.normal(
                    size=(
                        cls.batch,
                        2,
                        features.BOARD_SIZE,
                        features.BOARD_SIZE,
                        features.BOARD_CHANNELS,
                    )
                ).astype(np.float32)
            ),
            "units": jnp.asarray(
                rng.normal(
                    size=(
                        cls.batch,
                        features.MAX_UNITS,
                        features.UNIT_FEATURES,
                    )
                ).astype(np.float32)
            ),
            "unit_mask": jnp.asarray(
                np.array(
                    [
                        [1] * 7 + [0] * (features.MAX_UNITS - 7),
                        [1] * 4 + [0] * (features.MAX_UNITS - 4),
                    ],
                    dtype=np.float32,
                )
            ),
        }
        cls.model = LatentRoleHMoE()
        cls.variables = cls.model.init(jax.random.key(11406), **cls.inputs)

    def test_exact_output_shapes_and_finite_values(self) -> None:
        output = self.model.apply(self.variables, **self.inputs)
        expected = {
            "option_router_logits": (self.batch, NUM_OPTIONS),
            "unit_role_logits": (
                self.batch,
                NUM_OPTIONS,
                features.MAX_UNITS,
                NUM_UNIT_ROLES,
            ),
            "market_role_logits": (
                self.batch,
                NUM_OPTIONS,
                space.MAX_MARKET_SLOTS,
                NUM_MARKET_ROLES,
            ),
            "unit_logits": (
                self.batch,
                NUM_OPTIONS,
                features.MAX_UNITS,
                len(space.UNIT_TOKENS),
            ),
            "unit_quantity_logits": (
                self.batch,
                NUM_OPTIONS,
                features.MAX_UNITS,
                space.QUANTITY_DIM,
            ),
            "market_logits": (
                self.batch,
                NUM_OPTIONS,
                space.MAX_MARKET_SLOTS,
                len(space.MARKET_TOKENS),
            ),
            "market_quantity_logits": (
                self.batch,
                NUM_OPTIONS,
                space.MAX_MARKET_SLOTS,
                space.QUANTITY_DIM,
            ),
            "option_value": (self.batch, NUM_OPTIONS),
            "catastrophe_logits": (self.batch, NUM_OPTIONS),
        }
        self.assertTrue(self.model.timed)
        self.assertEqual(NUM_OPTIONS, 3)
        for name, shape in expected.items():
            with self.subTest(output=name):
                self.assertEqual(output[name].shape, shape)
                self.assertTrue(bool(jnp.all(jnp.isfinite(output[name]))))
        np.testing.assert_allclose(
            np.asarray(jnp.sum(output["unit_role_probabilities"], axis=-1)),
            1.0,
            atol=1e-6,
        )
        np.testing.assert_allclose(
            np.asarray(jnp.sum(output["market_role_probabilities"], axis=-1)),
            1.0,
            atol=1e-6,
        )

    def test_teacher_roles_are_auxiliary_and_cannot_leak_into_actions(self) -> None:
        unit_roles_a = jnp.zeros(
            (self.batch, features.MAX_UNITS), dtype=jnp.int32
        )
        market_roles_a = jnp.zeros(
            (self.batch, space.MAX_MARKET_SLOTS), dtype=jnp.int32
        )
        unit_roles_b = jnp.full_like(unit_roles_a, NUM_UNIT_ROLES - 1)
        market_roles_b = jnp.full_like(
            market_roles_a, NUM_MARKET_ROLES - 1
        )
        output_a = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_roles=unit_roles_a,
            market_teacher_roles=market_roles_a,
        )
        output_b = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_roles=unit_roles_b,
            market_teacher_roles=market_roles_b,
        )
        for name in (
            "unit_role_logits",
            "market_role_logits",
            "unit_logits",
            "unit_quantity_logits",
            "market_logits",
            "market_quantity_logits",
            "unit_sequence_tokens",
            "market_sequence_tokens",
        ):
            with self.subTest(output=name):
                np.testing.assert_array_equal(output_a[name], output_b[name])

    def test_unit_and_market_roles_read_executed_prefix(self) -> None:
        unit_tokens_a = jnp.zeros(
            (self.batch, features.MAX_UNITS), dtype=jnp.int32
        )
        unit_tokens_b = unit_tokens_a.at[:, 0].set(
            space.UNIT_INDEX["NORTH"]
        )
        unit_quantities = jnp.zeros_like(unit_tokens_a)
        market_tokens_a = jnp.full(
            (self.batch, space.MAX_MARKET_SLOTS),
            space.MARKET_INDEX["HIRE"],
            dtype=jnp.int32,
        )
        market_tokens_b = market_tokens_a.at[:, 0].set(
            space.MARKET_INDEX["BUY_LAND"]
        )
        market_quantities = jnp.zeros_like(market_tokens_a)
        output_a = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_tokens=unit_tokens_a,
            unit_teacher_quantities=unit_quantities,
            market_teacher_tokens=market_tokens_a,
            market_teacher_quantities=market_quantities,
        )
        output_b = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_tokens=unit_tokens_b,
            unit_teacher_quantities=unit_quantities,
            market_teacher_tokens=market_tokens_b,
            market_teacher_quantities=market_quantities,
        )
        self.assertFalse(
            np.allclose(
                np.asarray(output_a["unit_role_logits"][:, :, 1]),
                np.asarray(output_b["unit_role_logits"][:, :, 1]),
            )
        )
        self.assertFalse(
            np.allclose(
                np.asarray(output_a["market_role_logits"][:, :, 1]),
                np.asarray(output_b["market_role_logits"][:, :, 1]),
            )
        )

    def test_market_stop_is_absorbing_even_against_later_teacher_orders(self) -> None:
        market_tokens = jnp.full(
            (self.batch, space.MAX_MARKET_SLOTS),
            space.MARKET_INDEX["BUY_LAND"],
            dtype=jnp.int32,
        )
        market_tokens = market_tokens.at[:, 0].set(
            space.MARKET_INDEX["HIRE"]
        )
        market_tokens = market_tokens.at[:, 1].set(
            space.MARKET_INDEX["STOP"]
        )
        market_quantities = jnp.ones_like(market_tokens)
        output = self.model.apply(
            self.variables,
            **self.inputs,
            market_teacher_tokens=market_tokens,
            market_teacher_quantities=market_quantities,
        )
        stop = space.MARKET_INDEX["STOP"]
        expected_stop_tail = np.full(
            (self.batch, NUM_OPTIONS, space.MAX_MARKET_SLOTS - 1),
            stop,
            dtype=np.int32,
        )
        np.testing.assert_array_equal(
            output["market_sequence_tokens"][:, :, 1:], expected_stop_tail
        )
        np.testing.assert_array_equal(
            output["market_sequence_quantities"][:, :, 1:], 0
        )
        np.testing.assert_array_equal(
            jnp.argmax(output["market_logits"][:, :, 2:], axis=-1), stop
        )
        np.testing.assert_array_equal(
            jnp.argmax(
                output["market_quantity_logits"][:, :, 2:], axis=-1
            ),
            0,
        )
        self.assertTrue(
            bool(jnp.all(output["market_absorbed_before_slot"][:, :, 2:]))
        )

    def test_action_loss_backpropagates_through_latent_role_routers(self) -> None:
        params = self.variables["params"]
        single_inputs = {
            name: value[:1] for name, value in self.inputs.items()
        }

        def action_only_loss(current_params):
            output = self.model.apply(
                {"params": current_params}, **single_inputs
            )
            return (
                jnp.mean(output["unit_logits"][:, :, 0] ** 2)
                + jnp.mean(output["market_logits"][:, :, 0] ** 2)
            )

        loss, gradients = jax.value_and_grad(action_only_loss)(params)
        self.assertTrue(bool(jnp.isfinite(loss)))
        for name in (
            "unit_role_head",
            "unit_role_embedding",
            "market_role_head",
            "market_role_embedding",
        ):
            with self.subTest(parameter=name):
                leaves = jax.tree_util.tree_leaves(gradients[name])
                self.assertTrue(
                    any(bool(jnp.any(jnp.abs(leaf) > 0)) for leaf in leaves)
                )

    def test_shared_parameter_budget_and_invalid_teachers(self) -> None:
        params = self.variables["params"]
        self.assertIn("unit_gru", params)
        self.assertIn("market_gru", params)
        self.assertLess(parameter_count(params), 1_000_000)
        unit_tokens = jnp.zeros(
            (self.batch, features.MAX_UNITS), dtype=jnp.int32
        )
        with self.assertRaises(ValueError):
            self.model.apply(
                self.variables,
                **self.inputs,
                unit_teacher_tokens=unit_tokens,
            )
        with self.assertRaises(ValueError):
            self.model.apply(
                self.variables,
                **self.inputs,
                market_teacher_roles=jnp.zeros(
                    (self.batch, space.MAX_MARKET_SLOTS - 1),
                    dtype=jnp.int32,
                ),
            )


if __name__ == "__main__":
    unittest.main()
