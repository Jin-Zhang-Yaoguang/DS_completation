"""Independent unittest contract for the V114 nested HMoE model."""

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
from model_nested_hmoe import (  # noqa: E402
    NUM_OPTIONS,
    NUM_ROLES,
    NestedHMoEActorCritic,
)


def parameter_count(tree) -> int:
    return sum(int(value.size) for value in jax.tree_util.tree_leaves(tree))


def parameter_paths(tree, prefix: str = "") -> list[str]:
    paths = []
    for key, value in tree.items():
        path = f"{prefix}/{key}" if prefix else str(key)
        if isinstance(value, dict):
            paths.extend(parameter_paths(value, path))
        else:
            paths.append(path)
    return paths


class NestedHMoEContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = 2
        rng = np.random.default_rng(114)
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
                        [1] * 5 + [0] * (features.MAX_UNITS - 5),
                        [1] * 3 + [0] * (features.MAX_UNITS - 3),
                    ],
                    dtype=np.float32,
                )
            ),
        }
        cls.model = NestedHMoEActorCritic(timed=True)
        cls.variables = cls.model.init(
            jax.random.key(114), **cls.inputs
        )

    def test_exact_nested_output_shapes_and_finite_values(self) -> None:
        output = self.model.apply(self.variables, **self.inputs)
        expected = {
            "option_router_logits": (self.batch, 3),
            "unit_role_router_logits": (self.batch, 3, 6),
            "market_role_router_logits": (self.batch, 3, 6),
            "unit_logits": (
                self.batch,
                3,
                6,
                16,
                len(space.UNIT_TOKENS),
            ),
            "unit_quantity_logits": (
                self.batch,
                3,
                6,
                16,
                space.QUANTITY_DIM,
            ),
            "market_logits": (
                self.batch,
                3,
                6,
                10,
                len(space.MARKET_TOKENS),
            ),
            "market_quantity_logits": (
                self.batch,
                3,
                6,
                10,
                space.QUANTITY_DIM,
            ),
            "option_value": (self.batch, 3),
            "catastrophe_logits": (self.batch, 3),
        }
        self.assertEqual(NUM_OPTIONS, 3)
        self.assertEqual(NUM_ROLES, 6)
        self.assertEqual(features.MAX_UNITS, 16)
        self.assertEqual(space.MAX_MARKET_SLOTS, 10)
        for name, shape in expected.items():
            with self.subTest(output=name):
                self.assertEqual(output[name].shape, shape)
                self.assertTrue(bool(jnp.all(jnp.isfinite(output[name]))))

    def test_teacher_forcing_supports_shared_and_route_specific_tokens(self) -> None:
        shared_unit_tokens = jnp.zeros(
            (self.batch, features.MAX_UNITS), dtype=jnp.int32
        )
        shared_unit_quantities = jnp.zeros_like(shared_unit_tokens)
        shared_market_tokens = jnp.zeros(
            (self.batch, space.MAX_MARKET_SLOTS), dtype=jnp.int32
        )
        shared_market_quantities = jnp.zeros_like(shared_market_tokens)
        shared_output = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_tokens=shared_unit_tokens,
            unit_teacher_quantities=shared_unit_quantities,
            market_teacher_tokens=shared_market_tokens,
            market_teacher_quantities=shared_market_quantities,
        )
        expected_unit = jnp.broadcast_to(
            shared_unit_tokens[:, None, None, :],
            (self.batch, 3, 6, features.MAX_UNITS),
        )
        expected_market = jnp.broadcast_to(
            shared_market_tokens[:, None, None, :],
            (self.batch, 3, 6, space.MAX_MARKET_SLOTS),
        )
        np.testing.assert_array_equal(
            shared_output["unit_sequence_tokens"], expected_unit
        )
        np.testing.assert_array_equal(
            shared_output["market_sequence_tokens"], expected_market
        )

        route_unit_tokens = expected_unit.at[:, 2, 5, 0].set(1)
        route_market_tokens = expected_market.at[:, 1, 4, 0].set(1)
        route_output = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_tokens=route_unit_tokens,
            unit_teacher_quantities=jnp.zeros_like(route_unit_tokens),
            market_teacher_tokens=route_market_tokens,
            market_teacher_quantities=jnp.zeros_like(route_market_tokens),
        )
        np.testing.assert_array_equal(
            route_output["unit_sequence_tokens"], route_unit_tokens
        )
        np.testing.assert_array_equal(
            route_output["market_sequence_tokens"], route_market_tokens
        )
        self.assertFalse(
            np.allclose(
                np.asarray(shared_output["unit_logits"][:, 2, 5, 1]),
                np.asarray(route_output["unit_logits"][:, 2, 5, 1]),
            )
        )
        self.assertFalse(
            np.allclose(
                np.asarray(shared_output["market_logits"][:, 1, 4, 1]),
                np.asarray(route_output["market_logits"][:, 1, 4, 1]),
            )
        )

    def test_routes_share_decoders_and_parameter_budget_is_cpu_sized(self) -> None:
        params = self.variables["params"]
        paths = parameter_paths(params)
        self.assertIn("unit_gru", params)
        self.assertIn("market_gru", params)
        self.assertIn("unit_action_head", params)
        self.assertIn("market_action_head", params)
        self.assertIn("unit_option_role_projection", params)
        self.assertIn("market_option_role_projection", params)
        self.assertFalse(any("option_0" in path for path in paths))
        self.assertFalse(any("role_0" in path for path in paths))
        self.assertLess(parameter_count(params), 1_000_000)

        output = self.model.apply(self.variables, **self.inputs)
        route_a = np.asarray(output["unit_logits"][:, 0, 0])
        route_b = np.asarray(output["unit_logits"][:, 2, 5])
        self.assertFalse(np.allclose(route_a, route_b))

    def test_backward_pass_is_finite(self) -> None:
        single_inputs = {key: value[:1] for key, value in self.inputs.items()}

        def loss_fn(params):
            output = self.model.apply({"params": params}, **single_inputs)
            return (
                jnp.mean(output["unit_logits"] ** 2)
                + jnp.mean(output["market_logits"] ** 2)
                + jnp.mean(output["option_router_logits"] ** 2)
                + jnp.mean(output["option_value"] ** 2)
                + jnp.mean(output["catastrophe_logits"] ** 2)
            )

        loss, gradients = jax.value_and_grad(loss_fn)(self.variables["params"])
        self.assertTrue(bool(jnp.isfinite(loss)))
        self.assertTrue(
            all(
                bool(jnp.all(jnp.isfinite(gradient)))
                for gradient in jax.tree_util.tree_leaves(gradients)
            )
        )

    def test_incomplete_teacher_pair_is_rejected(self) -> None:
        tokens = jnp.zeros(
            (self.batch, features.MAX_UNITS), dtype=jnp.int32
        )
        with self.assertRaises(ValueError):
            self.model.apply(
                self.variables,
                **self.inputs,
                unit_teacher_tokens=tokens,
            )


if __name__ == "__main__":
    unittest.main()
