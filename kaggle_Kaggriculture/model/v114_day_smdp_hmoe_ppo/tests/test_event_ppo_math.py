"""Math and model contracts for the independent V9 event-program PPO."""

from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

import jax
import jax.numpy as jnp
import numpy as np


V114_DIR = Path(__file__).resolve().parents[1]
if str(V114_DIR) not in sys.path:
    sys.path.insert(0, str(V114_DIR))

from event_ppo_math import (  # noqa: E402
    HEAD_NAMES,
    HEAD_SIZES,
    duration_aware_smdp_gae,
    factorized_log_probability_entropy,
    factorized_ppo_loss,
    ppo_clipped_loss,
    sample_factorized_actions,
    validate_action_masks,
    validate_shared_masks,
)
from model_event_program_ppo import (  # noqa: E402
    EventProgramPPOManager,
    checkpoint_metadata,
    make_checkpoint_payload,
    validate_checkpoint_metadata,
)


def all_legal_masks(batch: int) -> dict[str, jnp.ndarray]:
    return {
        name: jnp.ones((batch, size), dtype=jnp.bool_)
        for name, size in HEAD_SIZES.items()
    }


class FactorizedPolicyMathTest(unittest.TestCase):
    def test_joint_log_probability_and_entropy_are_five_head_sums(self) -> None:
        batch = 2
        logits = {
            name: jnp.zeros((batch, size), dtype=jnp.float32)
            for name, size in HEAD_SIZES.items()
        }
        masks = all_legal_masks(batch)
        actions = {
            name: jnp.zeros((batch,), dtype=jnp.int32)
            for name in HEAD_NAMES
        }
        joint_logp, entropy, per_head = factorized_log_probability_entropy(
            logits, actions, masks
        )
        expected = -sum(math.log(size) for size in HEAD_SIZES.values())
        np.testing.assert_allclose(joint_logp, expected, rtol=1e-6)
        np.testing.assert_allclose(entropy, -expected, rtol=1e-6)
        np.testing.assert_allclose(
            joint_logp,
            sum(per_head.values(), jnp.zeros_like(joint_logp)),
            rtol=1e-6,
        )

    def test_masked_sampler_never_selects_illegal_high_logit_actions(self) -> None:
        batch = 256
        logits = {}
        masks = {}
        expected = {}
        for index, (name, size) in enumerate(HEAD_SIZES.items()):
            legal_index = index % size
            expected[name] = legal_index
            mask = np.zeros((batch, size), dtype=bool)
            mask[:, legal_index] = True
            masks[name] = jnp.asarray(mask)
            values = np.full((batch, size), -100.0, dtype=np.float32)
            values[:, (legal_index + 1) % size] = 1_000.0
            logits[name] = jnp.asarray(values)
        actions, logp, entropy = sample_factorized_actions(
            jax.random.key(9), logits, masks
        )
        for name in HEAD_NAMES:
            np.testing.assert_array_equal(actions[name], expected[name])
        np.testing.assert_allclose(logp, 0.0, atol=1e-6)
        np.testing.assert_allclose(entropy, 0.0, atol=1e-6)

    def test_mask_contract_rejects_empty_and_old_new_mismatch(self) -> None:
        masks = {
            name: np.ones((2, size), dtype=bool)
            for name, size in HEAD_SIZES.items()
        }
        validate_action_masks(masks)
        mismatched = {name: value.copy() for name, value in masks.items()}
        mismatched["cash_reserve"][0, 0] = False
        with self.assertRaisesRegex(ValueError, "cash_reserve"):
            validate_shared_masks(masks, mismatched)
        empty = {name: value.copy() for name, value in masks.items()}
        empty["sell_style"][1] = False
        with self.assertRaisesRegex(ValueError, "no legal action"):
            validate_action_masks(empty)

    def test_clipped_loss_matches_hand_calculation_and_reports_kl(self) -> None:
        loss, metrics = ppo_clipped_loss(
            jnp.asarray([math.log(0.75)], dtype=jnp.float32),
            jnp.asarray([math.log(0.50)], dtype=jnp.float32),
            jnp.asarray([1.0], dtype=jnp.float32),
            jnp.asarray([0.0], dtype=jnp.float32),
            clip_epsilon=0.2,
            exact_kl=jnp.asarray([0.125], dtype=jnp.float32),
        )
        self.assertAlmostEqual(float(loss), -1.2, places=6)
        self.assertAlmostEqual(float(metrics["clip_fraction"]), 1.0, places=6)
        self.assertAlmostEqual(float(metrics["exact_kl"]), 0.125, places=6)
        self.assertGreaterEqual(float(metrics["approximate_kl"]), 0.0)

    def test_factorized_ppo_loss_has_finite_nonzero_logit_gradients(self) -> None:
        batch = 4
        old_logits = {
            name: jnp.zeros((batch, size), dtype=jnp.float32)
            for name, size in HEAD_SIZES.items()
        }
        new_logits = {
            name: jnp.linspace(-0.2, 0.2, batch * size).reshape(batch, size)
            for name, size in HEAD_SIZES.items()
        }
        actions = {
            name: jnp.arange(batch, dtype=jnp.int32) % size
            for name, size in HEAD_SIZES.items()
        }
        masks = all_legal_masks(batch)
        advantages = jnp.asarray([1.0, -0.5, 0.75, -1.25], dtype=jnp.float32)

        def loss_fn(current_logits):
            return factorized_ppo_loss(
                old_logits,
                current_logits,
                actions,
                masks,
                advantages,
                entropy_coefficient=0.01,
            )[0]

        loss, gradients = jax.value_and_grad(loss_fn)(new_logits)
        self.assertTrue(bool(jnp.isfinite(loss)))
        for name in HEAD_NAMES:
            with self.subTest(head=name):
                self.assertTrue(bool(jnp.all(jnp.isfinite(gradients[name]))))
                self.assertTrue(bool(jnp.any(jnp.abs(gradients[name]) > 0)))


class DurationAwareGAETest(unittest.TestCase):
    def test_two_transition_gae_matches_hand_calculation(self) -> None:
        result = duration_aware_smdp_gae(
            rewards=jnp.asarray([1.0, 2.0]),
            values=jnp.asarray([0.5, 0.25]),
            next_values=jnp.asarray([0.25, 0.0]),
            terminals=jnp.asarray([0.0, 1.0]),
            durations_turns=jnp.asarray([24.0, 12.0]),
        )
        expected_last = 2.0 - 0.25
        expected_first_delta = 1.0 + 0.99 * 0.25 - 0.5
        expected_first = expected_first_delta + 0.99 * 0.95 * expected_last
        np.testing.assert_allclose(
            result["advantages"], [expected_first, expected_last], rtol=1e-6
        )
        np.testing.assert_allclose(
            result["returns"], [expected_first + 0.5, 2.0], rtol=1e-6
        )
        np.testing.assert_allclose(
            result["gamma_discounts"], [0.99, math.sqrt(0.99)], rtol=1e-6
        )
        np.testing.assert_allclose(
            result["lambda_discounts"], [0.95, math.sqrt(0.95)], rtol=1e-6
        )


class EventProgramManagerTest(unittest.TestCase):
    def test_random_v9_model_shapes_initialization_and_gradients(self) -> None:
        model = EventProgramPPOManager()
        state = jnp.linspace(-1.0, 1.0, 3 * 423).reshape(3, 423)
        variables_a = model.init(jax.random.key(11409), state)
        variables_b = model.init(jax.random.key(11410), state)
        output = model.apply(variables_a, state)
        for name, size in HEAD_SIZES.items():
            self.assertEqual(output["actor_logits"][name].shape, (3, size))
        self.assertEqual(output["value"].shape, (3,))
        self.assertEqual(output["constraint_value"].shape, (3,))
        self.assertFalse(
            all(
                np.array_equal(left, right)
                for left, right in zip(
                    jax.tree_util.tree_leaves(variables_a["params"]),
                    jax.tree_util.tree_leaves(variables_b["params"]),
                    strict=True,
                )
            )
        )

        def loss_fn(params):
            current = model.apply({"params": params}, state)
            actor = sum(
                jnp.mean(logits**2)
                for logits in current["actor_logits"].values()
            )
            return actor + jnp.mean(current["value"] ** 2) + jnp.mean(
                current["constraint_value"] ** 2
            )

        loss, gradients = jax.value_and_grad(loss_fn)(variables_a["params"])
        self.assertTrue(bool(jnp.isfinite(loss)))
        for name in (
            *(f"{head}_head" for head in HEAD_NAMES),
            "value_head",
            "constraint_value_head",
        ):
            with self.subTest(parameter=name):
                leaves = jax.tree_util.tree_leaves(gradients[name])
                self.assertTrue(
                    any(bool(jnp.any(jnp.abs(leaf) > 0)) for leaf in leaves)
                )

    def test_checkpoint_contract_is_parentless_and_rejects_inheritance(self) -> None:
        metadata = checkpoint_metadata()
        validate_checkpoint_metadata(metadata)
        self.assertIsNone(metadata["strategy_parent"])
        self.assertIsNone(metadata["parent_checkpoint_sha256"])
        self.assertEqual(metadata["parameter_initialization"], "random_v9")
        payload = make_checkpoint_payload({"test": jnp.asarray([1.0])})
        self.assertIn("params", payload)
        inherited = dict(metadata)
        inherited["parent_checkpoint_sha256"] = "deadbeef"
        with self.assertRaisesRegex(ValueError, "parent_checkpoint_sha256"):
            validate_checkpoint_metadata(inherited)
        forbidden = dict(metadata)
        forbidden["source_checkpoint"] = "/tmp/latent_role_bc_v6.msgpack"
        with self.assertRaisesRegex(ValueError, "source_checkpoint"):
            validate_checkpoint_metadata(forbidden)


if __name__ == "__main__":
    unittest.main()
