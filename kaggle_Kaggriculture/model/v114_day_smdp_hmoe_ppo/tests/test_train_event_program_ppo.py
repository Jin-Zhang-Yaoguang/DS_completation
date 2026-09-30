"""Contract tests for the true on-policy V114 V9 PPO trainer."""

from __future__ import annotations

import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest

import jax
import jax.numpy as jnp
import numpy as np


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from event_ppo_math import (  # noqa: E402
    HEAD_NAMES,
    HEAD_SIZES,
    factorized_log_probability_entropy,
)
from initialize_event_program_manager import initialize_payload  # noqa: E402
from model_event_program_ppo import (  # noqa: E402
    EventProgramPPOManager,
    validate_checkpoint_metadata,
)
from train_event_program_ppo import (  # noqa: E402
    PPOConfig,
    RewardConfig,
    build_checkpoint_payload,
    create_train_state,
    layer_standardize,
    make_batch,
    parameter_change_report,
    parameter_labels,
    potential_shaping,
    prepare_layer_training_data,
    terminal_outcome_reward,
    train_minibatch,
    validate_old_policy_evidence,
)


def behavior_table(rows: int = 12) -> tuple[dict[str, np.ndarray], object]:
    model = EventProgramPPOManager()
    params = model.init(
        jax.random.key(114930),
        jnp.zeros((1, 427), dtype=jnp.float32),
    )["params"]
    features = np.linspace(-0.5, 0.5, rows * 427, dtype=np.float32).reshape(rows, 427)
    outputs = model.apply({"params": params}, jnp.asarray(features))
    masks = {
        name: np.ones((rows, size), dtype=np.bool_)
        for name, size in HEAD_SIZES.items()
    }
    masks["production_line"][:, 1] = False
    actions = {
        name: np.arange(rows, dtype=np.int32) % size
        for name, size in HEAD_SIZES.items()
    }
    actions["production_line"] = np.asarray(
        [index for index in range(5) if index != 1] * ((rows + 3) // 4),
        dtype=np.int32,
    )[:rows]
    jax_masks = {name: jnp.asarray(value) for name, value in masks.items()}
    jax_actions = {name: jnp.asarray(value) for name, value in actions.items()}
    old_logits = {
        name: np.asarray(outputs["actor_logits"][name], dtype=np.float32)
        for name in HEAD_NAMES
    }
    joint_logp, _, _ = factorized_log_probability_entropy(
        {name: jnp.asarray(value) for name, value in old_logits.items()},
        jax_actions,
        jax_masks,
    )
    data: dict[str, np.ndarray] = {
        "features": features,
        "old_joint_logp": np.asarray(joint_logp, dtype=np.float32),
        "value": np.asarray(outputs["value"], dtype=np.float32),
        "constraint_value": np.asarray(outputs["constraint_value"], dtype=np.float32),
    }
    for name in HEAD_NAMES:
        data[f"mask_{name}"] = masks[name]
        data[f"action_{name}"] = actions[name]
        data[f"old_logits_{name}"] = old_logits[name]
    return data, params


def tiny_episode_table(second_margin: float = -500.0) -> dict[str, np.ndarray]:
    rows = 4
    return {
        "features": np.zeros((rows, 427), dtype=np.float32),
        "episode_offsets": np.asarray([0, 2, 4], dtype=np.int64),
        "value": np.zeros(rows, dtype=np.float32),
        "next_value": np.zeros(rows, dtype=np.float32),
        "constraint_value": np.zeros(rows, dtype=np.float32),
        "next_constraint_value": np.zeros(rows, dtype=np.float32),
        "duration_turns": np.asarray([24, 24, 24, 24], dtype=np.int16),
        "terminal": np.asarray([False, True, False, True]),
        "own_money_start": np.asarray([3000, 3200, 3000, 3100], dtype=np.float32),
        "own_money_end": np.asarray([3200, 3500, 3100, 2500], dtype=np.float32),
        "score": np.asarray([1, 1, 0, 0], dtype=np.float32),
        "margin": np.asarray([500, 500, second_margin, second_margin], dtype=np.float32),
        "candidate_reward": np.asarray([3500, 3500, 2500, 2500], dtype=np.float32),
        "catastrophe": np.asarray([False, False, True, True]),
    }


class RewardContractTest(unittest.TestCase):
    def test_terminal_reward_formula(self) -> None:
        config = RewardConfig()
        actual = terminal_outcome_reward(
            score=1.0,
            margin=5000.0,
            own_reward=8000.0,
            catastrophe=False,
            config=config,
        )
        expected = 1.0 + 0.25 * math.tanh(0.5) + 0.25 * math.tanh(0.5)
        self.assertAlmostEqual(actual, expected, places=7)
        catastrophe = terminal_outcome_reward(
            score=0.0,
            margin=-5000.0,
            own_reward=2000.0,
            catastrophe=True,
            config=config,
        )
        expected_bad = -1.0 + 0.25 * math.tanh(-0.5) + 0.25 * math.tanh(-0.1) - 1.0
        self.assertAlmostEqual(catastrophe, expected_bad, places=7)

    def test_potential_telescopes_under_smdp_discount_and_terminal_phi_is_zero(self) -> None:
        config = RewardConfig(potential_coefficient=0.1)
        money_start = np.asarray([4000.0, 5000.0, 4500.0])
        money_end = np.asarray([5000.0, 4500.0, 9000.0])
        durations = np.asarray([24.0, 48.0, 12.0])
        terminals = np.asarray([False, False, True])
        shaping = potential_shaping(
            money_start,
            money_end,
            durations,
            terminals,
            gamma_day=0.99,
            config=config,
        )
        discounts = np.power(0.99, durations / 24.0)
        discounted_sum = shaping[0] + discounts[0] * shaping[1]
        discounted_sum += discounts[0] * discounts[1] * shaping[2]
        initial_phi = (money_start[0] - 3000.0) / 10000.0
        self.assertAlmostEqual(discounted_sum, -0.1 * initial_phi, places=10)
        expected_terminal = -0.1 * (money_start[-1] - 3000.0) / 10000.0
        self.assertAlmostEqual(shaping[-1], expected_terminal, places=10)


class AdvantageContractTest(unittest.TestCase):
    def test_gae_is_calculated_inside_each_episode_boundary(self) -> None:
        config = PPOConfig()
        left, _ = prepare_layer_training_data(
            "GOLD", tiny_episode_table(-500.0),
            reward_config=RewardConfig(), ppo_config=config,
        )
        right, _ = prepare_layer_training_data(
            "GOLD", tiny_episode_table(-50000.0),
            reward_config=RewardConfig(), ppo_config=config,
        )
        np.testing.assert_allclose(
            left["reward_advantage_raw"][:2],
            right["reward_advantage_raw"][:2],
            rtol=0,
            atol=0,
        )
        self.assertFalse(np.allclose(
            left["reward_advantage_raw"][2:], right["reward_advantage_raw"][2:]
        ))

    def test_advantages_are_standardized_separately_by_layer(self) -> None:
        values = np.asarray([1.0, 3.0, 100.0, 104.0], dtype=np.float32)
        layers = np.asarray(["EASY", "EASY", "GOLD", "GOLD"])
        normalized, report = layer_standardize(values, layers)
        np.testing.assert_allclose(normalized, [-1, 1, -1, 1], atol=1.0e-7)
        self.assertAlmostEqual(report["EASY"]["raw_mean"], 2.0)
        self.assertAlmostEqual(report["GOLD"]["raw_mean"], 102.0)
        self.assertAlmostEqual(report["EASY"]["normalized_mean"], 0.0)
        self.assertAlmostEqual(report["GOLD"]["normalized_mean"], 0.0)


class OldPolicyEvidenceTest(unittest.TestCase):
    def test_old_logp_is_complete_and_must_recompute_from_stored_logits(self) -> None:
        data, _ = behavior_table(10)
        report = validate_old_policy_evidence(data)
        self.assertLess(report["max_old_joint_logp_recompute_error"], 2.0e-5)
        corrupted = copy.deepcopy(data)
        corrupted["old_joint_logp"] = corrupted["old_joint_logp"].copy()
        corrupted["old_joint_logp"][3] += 0.25
        with self.assertRaisesRegex(ValueError, "old_joint_logp"):
            validate_old_policy_evidence(corrupted)
        incomplete = copy.deepcopy(data)
        incomplete["old_logits_worker_cap"] = incomplete["old_logits_worker_cap"][:, :2]
        with self.assertRaisesRegex(ValueError, "old_logits_worker_cap"):
            validate_old_policy_evidence(incomplete)


class PPOUpdateTest(unittest.TestCase):
    def test_one_update_uses_one_shared_mask_and_changes_actor_and_critics(self) -> None:
        data, params = behavior_table(16)
        data.update({
            "actor_advantage": np.asarray([1.0, -0.6, 0.8, -0.4] * 4, dtype=np.float32),
            "reward_return": np.asarray(data["value"]) + 1.0,
            "constraint_return": np.asarray(data["constraint_value"]) + 0.5,
        })
        config = PPOConfig(
            actor_learning_rate=1.0e-4,
            critic_learning_rate=3.0e-4,
            minibatch_size=16,
            epochs=1,
        )
        state = create_train_state(params, config)
        batch = make_batch(data, np.arange(16))
        self.assertEqual(set(batch), {
            "features", "shared_masks", "actions", "old_logits",
            "old_joint_logp", "actor_advantage", "reward_return", "constraint_return",
        })
        before = state.params
        updated, metrics = train_minibatch(state, batch, config=config)
        changes = parameter_change_report(before, updated.params)
        self.assertGreater(changes["actor_changed_leaves"], 0)
        self.assertGreater(changes["critic_changed_leaves"], 0)
        self.assertTrue(np.isfinite(float(metrics["exact_kl"])))
        for name in HEAD_NAMES:
            self.assertIs(batch["shared_masks"][name], batch["shared_masks"][name])

    def test_parameter_labels_put_only_two_value_heads_on_critic_lr(self) -> None:
        _, params = behavior_table(2)
        labels = parameter_labels(params)
        for root, subtree in labels.items():
            unique = set(jax.tree_util.tree_leaves(subtree))
            expected = {"critic"} if root in {"value_head", "constraint_value_head"} else {"actor"}
            self.assertEqual(unique, expected, root)

    def test_trained_checkpoint_metadata_remains_independent_v9(self) -> None:
        initial = initialize_payload(114933, policy_seed=114934)
        payload = build_checkpoint_payload(
            initial,
            initial["params"],
            initial_checkpoint_sha256="a" * 64,
            dataset_sha256={"EASY": "b" * 64},
            rollout_report_sha256={"EASY": "c" * 64},
            reward_config=RewardConfig(),
            ppo_config=PPOConfig(),
            iteration=1,
            training_seed=114935,
        )
        validate_checkpoint_metadata(payload)
        self.assertIsNone(payload["strategy_parent"])
        self.assertTrue(payload["PPO"])
        self.assertNotIn("initial_checkpoint", payload)
        self.assertEqual(payload["training_initial_checkpoint_sha256"], "a" * 64)


if __name__ == "__main__":
    unittest.main()
