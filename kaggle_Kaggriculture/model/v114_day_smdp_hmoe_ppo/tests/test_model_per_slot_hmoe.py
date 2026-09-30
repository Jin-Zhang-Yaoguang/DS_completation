"""Independent unittest contract for the V114 per-slot HMoE."""

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
from model_per_slot_hmoe import (  # noqa: E402
    NUM_MARKET_ROLES,
    NUM_OPTIONS,
    NUM_UNIT_ROLES,
    PerSlotOptionRoleHMoE,
)


def parameter_count(tree) -> int:
    return sum(int(value.size) for value in jax.tree_util.tree_leaves(tree))


def parameter_paths(tree, prefix: str = "") -> list[str]:
    paths = []
    for key, value in tree.items():
        path = f"{prefix}/{key}" if prefix else str(key)
        if hasattr(value, "items"):
            paths.extend(parameter_paths(value, path))
        else:
            paths.append(path)
    return paths


class PerSlotOptionRoleHMoETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = 2
        rng = np.random.default_rng(11401)
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
        cls.model = PerSlotOptionRoleHMoE()
        cls.variables = cls.model.init(jax.random.key(11401), **cls.inputs)

    def test_default_timed_and_exact_output_shapes(self) -> None:
        self.assertTrue(self.model.timed)
        output = self.model.apply(self.variables, **self.inputs)
        expected = {
            "option_router_logits": (self.batch, 3),
            "unit_role_logits": (self.batch, 3, 16, 4),
            "market_role_logits": (self.batch, 3, 10, 3),
            "unit_logits": (
                self.batch,
                3,
                16,
                len(space.UNIT_TOKENS),
            ),
            "unit_quantity_logits": (
                self.batch,
                3,
                16,
                space.QUANTITY_DIM,
            ),
            "market_logits": (
                self.batch,
                3,
                10,
                len(space.MARKET_TOKENS),
            ),
            "market_quantity_logits": (
                self.batch,
                3,
                10,
                space.QUANTITY_DIM,
            ),
            "option_value": (self.batch, 3),
            "catastrophe_logits": (self.batch, 3),
        }
        self.assertEqual(NUM_OPTIONS, 3)
        self.assertEqual(NUM_UNIT_ROLES, 4)
        self.assertEqual(NUM_MARKET_ROLES, 3)
        for name, shape in expected.items():
            with self.subTest(output=name):
                self.assertEqual(output[name].shape, shape)
                self.assertTrue(bool(jnp.all(jnp.isfinite(output[name]))))

    def test_inference_roles_are_per_slot_argmax(self) -> None:
        output = self.model.apply(self.variables, **self.inputs)
        np.testing.assert_array_equal(
            output["unit_roles"],
            jnp.argmax(output["unit_role_logits"], axis=-1),
        )
        np.testing.assert_array_equal(
            output["market_roles"],
            jnp.argmax(output["market_role_logits"], axis=-1),
        )

    def test_teacher_roles_condition_shared_decoders(self) -> None:
        unit_roles_a = jnp.zeros(
            (self.batch, features.MAX_UNITS), dtype=jnp.int32
        )
        market_roles_a = jnp.zeros(
            (self.batch, space.MAX_MARKET_SLOTS), dtype=jnp.int32
        )
        unit_roles_b = unit_roles_a.at[:, 0].set(NUM_UNIT_ROLES - 1)
        market_roles_b = market_roles_a.at[:, 0].set(NUM_MARKET_ROLES - 1)
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
        expected_unit_b = jnp.broadcast_to(
            unit_roles_b[:, None, :], (self.batch, 3, 16)
        )
        expected_market_b = jnp.broadcast_to(
            market_roles_b[:, None, :], (self.batch, 3, 10)
        )
        np.testing.assert_array_equal(output_b["unit_roles"], expected_unit_b)
        np.testing.assert_array_equal(
            output_b["market_roles"], expected_market_b
        )
        self.assertFalse(
            np.allclose(
                np.asarray(output_a["unit_logits"][:, :, 0]),
                np.asarray(output_b["unit_logits"][:, :, 0]),
            )
        )
        self.assertFalse(
            np.allclose(
                np.asarray(output_a["market_logits"][:, :, 0]),
                np.asarray(output_b["market_logits"][:, :, 0]),
            )
        )

    def test_token_teacher_forcing_is_autoregressive(self) -> None:
        unit_tokens_a = jnp.zeros(
            (self.batch, features.MAX_UNITS), dtype=jnp.int32
        )
        unit_tokens_b = unit_tokens_a.at[:, 0].set(1)
        unit_quantities = jnp.zeros_like(unit_tokens_a)
        market_tokens_a = jnp.zeros(
            (self.batch, space.MAX_MARKET_SLOTS), dtype=jnp.int32
        )
        market_tokens_b = market_tokens_a.at[:, 0].set(1)
        market_quantities = jnp.zeros_like(market_tokens_a)
        kwargs = {
            "unit_teacher_quantities": unit_quantities,
            "market_teacher_quantities": market_quantities,
            "unit_teacher_roles": jnp.zeros_like(unit_tokens_a),
            "market_teacher_roles": jnp.zeros_like(market_tokens_a),
        }
        output_a = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_tokens=unit_tokens_a,
            market_teacher_tokens=market_tokens_a,
            **kwargs,
        )
        output_b = self.model.apply(
            self.variables,
            **self.inputs,
            unit_teacher_tokens=unit_tokens_b,
            market_teacher_tokens=market_tokens_b,
            **kwargs,
        )
        self.assertFalse(
            np.allclose(
                np.asarray(output_a["unit_logits"][:, :, 1]),
                np.asarray(output_b["unit_logits"][:, :, 1]),
            )
        )
        self.assertFalse(
            np.allclose(
                np.asarray(output_a["market_logits"][:, :, 1]),
                np.asarray(output_b["market_logits"][:, :, 1]),
            )
        )

    def test_shared_model_parameter_budget_and_finite_gradients(self) -> None:
        params = self.variables["params"]
        paths = parameter_paths(params)
        self.assertIn("unit_gru", params)
        self.assertIn("market_gru", params)
        self.assertIn("unit_action_head", params)
        self.assertIn("market_action_head", params)
        self.assertEqual(sum(name == "unit_gru" for name in params), 1)
        self.assertEqual(sum(name == "market_gru" for name in params), 1)
        self.assertFalse(any("option_0" in path for path in paths))
        self.assertFalse(any("role_0" in path for path in paths))
        self.assertLess(parameter_count(params), 1_000_000)

        single_inputs = {name: value[:1] for name, value in self.inputs.items()}

        def loss_fn(current_params):
            output = self.model.apply({"params": current_params}, **single_inputs)
            return sum(
                jnp.mean(output[name] ** 2)
                for name in (
                    "option_router_logits",
                    "unit_role_logits",
                    "market_role_logits",
                    "unit_logits",
                    "unit_quantity_logits",
                    "market_logits",
                    "market_quantity_logits",
                    "option_value",
                    "catastrophe_logits",
                )
            )

        loss, gradients = jax.value_and_grad(loss_fn)(params)
        self.assertTrue(bool(jnp.isfinite(loss)))
        self.assertTrue(
            all(
                bool(jnp.all(jnp.isfinite(gradient)))
                for gradient in jax.tree_util.tree_leaves(gradients)
            )
        )
        self.assertTrue(
            any(
                bool(jnp.any(jnp.abs(gradient) > 0))
                for gradient in jax.tree_util.tree_leaves(gradients)
            )
        )

    def test_invalid_teacher_shapes_and_incomplete_pairs_are_rejected(self) -> None:
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
                unit_teacher_roles=jnp.zeros(
                    (self.batch, features.MAX_UNITS - 1), dtype=jnp.int32
                ),
            )


if __name__ == "__main__":
    unittest.main()
