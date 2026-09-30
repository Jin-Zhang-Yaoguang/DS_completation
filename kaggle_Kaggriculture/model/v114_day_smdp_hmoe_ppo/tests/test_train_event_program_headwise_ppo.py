"""Contract tests for Iteration 2 head-wise active-decision PPO."""

from __future__ import annotations

import math
from pathlib import Path
import sys
import tempfile
import unittest

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from event_ppo_math import (  # noqa: E402
    HEAD_NAMES,
    HEAD_SIZES,
    masked_categorical_log_probability,
)
from initialize_event_program_manager import initialize_payload  # noqa: E402
from model_event_program_ppo import EventProgramPPOManager, validate_checkpoint_metadata  # noqa: E402
from train_event_program_headwise_ppo import (  # noqa: E402
    PPOConfig,
    RewardConfig,
    TRAINING_METHOD,
    build_checkpoint_payload,
    concatenate_bindings,
    create_scoped_train_state,
    headwise_actor_objective,
    make_batch,
    normalization_group,
    parameter_root_changes,
    prepare_binding_training_data,
    recompute_old_head_logp,
    terminal_outcome_reward,
    train_minibatch,
)
from train_event_program_ppo import create_train_state, parameter_change_report  # noqa: E402


def behavior_table(rows: int = 12) -> tuple[dict[str, np.ndarray], object]:
    model = EventProgramPPOManager()
    params = model.init(
        jax.random.key(114940), jnp.zeros((1, 427), dtype=jnp.float32)
    )["params"]
    features = np.linspace(-0.4, 0.4, rows * 427, dtype=np.float32).reshape(rows, 427)
    outputs = model.apply({"params": params}, jnp.asarray(features))
    masks = {name: np.ones((rows, size), dtype=np.bool_) for name, size in HEAD_SIZES.items()}
    masks["production_line"][:, 1] = False
    actions = {name: np.arange(rows, dtype=np.int32) % size for name, size in HEAD_SIZES.items()}
    actions["production_line"] = np.asarray(
        [0, 2, 3, 4] * ((rows + 3) // 4), dtype=np.int32
    )[:rows]
    old_logits = {
        name: np.asarray(outputs["actor_logits"][name], dtype=np.float32)
        for name in HEAD_NAMES
    }
    old_logp = {
        name: np.asarray(
            masked_categorical_log_probability(
                jnp.asarray(old_logits[name]),
                jnp.asarray(actions[name]),
                jnp.asarray(masks[name]),
            ),
            dtype=np.float32,
        )
        for name in HEAD_NAMES
    }
    data: dict[str, np.ndarray] = {
        "features": features,
        "old_joint_logp": sum(old_logp.values(), np.zeros(rows, np.float32)),
        "value": np.asarray(outputs["value"], dtype=np.float32),
        "constraint_value": np.asarray(outputs["constraint_value"], dtype=np.float32),
    }
    for name in HEAD_NAMES:
        data[f"mask_{name}"] = masks[name]
        data[f"action_{name}"] = actions[name]
        data[f"old_logits_{name}"] = old_logits[name]
        data[f"old_logp_{name}"] = old_logp[name]
    return data, params


def tiny_episode(catastrophe: bool = False) -> dict[str, np.ndarray]:
    rows = 4
    data, _ = behavior_table(rows)
    data.update(
        {
            "episode_offsets": np.asarray([0, 2, 4], dtype=np.int64),
            "next_value": np.zeros(rows, dtype=np.float32),
            "next_constraint_value": np.zeros(rows, dtype=np.float32),
            "duration_turns": np.asarray([24, 24, 24, 24], dtype=np.int16),
            "terminal": np.asarray([False, True, False, True]),
            "own_money_start": np.asarray([3000, 3300, 3000, 3200], dtype=np.float32),
            "own_money_end": np.asarray([3300, 5000, 3200, 4000], dtype=np.float32),
            "score": np.asarray([1, 1, 0, 0], dtype=np.float32),
            "candidate_reward": np.asarray([5000, 5000, 4000, 4000], dtype=np.float32),
            "opponent_reward": np.asarray([3000, 3000, 6000, 6000], dtype=np.float32),
            "catastrophe": np.asarray([False, False, catastrophe, catastrophe]),
        }
    )
    return data


def actor_batch(
    *, rows: int = 4, masks: dict[str, np.ndarray] | None = None
) -> tuple[dict[str, object], dict[str, jnp.ndarray]]:
    data, _ = behavior_table(rows)
    if masks is not None:
        for name, value in masks.items():
            data[f"mask_{name}"] = value
            data[f"action_{name}"] = np.argmax(value, axis=-1).astype(np.int32)
        # The changed masks/actions define a new synthetic behavior table;
        # rebuild its per-head evidence instead of retaining the old joint row.
        data.pop("old_joint_logp", None)
    old_head = recompute_old_head_logp(data)
    for name in HEAD_NAMES:
        data[f"old_logp_{name}"] = old_head[name]
    data["actor_advantage"] = np.asarray([1.0, -0.7, 0.5, -0.3], dtype=np.float32)[:rows]
    data["reward_return"] = np.asarray(data["value"]) + 1.0
    data["constraint_return"] = np.asarray(data["constraint_value"]) + 0.5
    batch = make_batch(data, np.arange(rows))
    return batch, {name: jnp.asarray(data[f"old_logits_{name}"]) for name in HEAD_NAMES}


class BindingAndRewardTest(unittest.TestCase):
    def test_binding_uses_slash_prefix(self) -> None:
        self.assertEqual(normalization_group("easy/starter"), "easy")
        self.assertEqual(normalization_group("hard_gold/v76"), "hard_gold")
        with self.assertRaisesRegex(ValueError, "layer/member"):
            normalization_group("easy")
        with self.assertRaisesRegex(ValueError, "one of"):
            normalization_group("other/member")

    def test_relative_share_detects_own_growth_but_larger_opponent_growth(self) -> None:
        config = RewardConfig()
        own_more_absolute = terminal_outcome_reward(
            score=0.0,
            own_reward=6000.0,
            opponent_reward=12000.0,
            catastrophe=False,
            config=config,
        )
        balanced = terminal_outcome_reward(
            score=0.5,
            own_reward=5000.0,
            opponent_reward=5000.0,
            catastrophe=False,
            config=config,
        )
        expected = -1.0 + (2.0 * 6000.0 / 18000.0 - 1.0) + 0.1 * math.tanh(0.3)
        self.assertAlmostEqual(own_more_absolute, expected, places=7)
        self.assertLess(own_more_absolute, balanced)


class HeadwiseActorMathTest(unittest.TestCase):
    def test_single_legal_action_has_zero_actor_gradient(self) -> None:
        rows = 4
        single = {
            name: np.eye(size, dtype=np.bool_)[np.zeros(rows, dtype=np.int32)]
            for name, size in HEAD_SIZES.items()
        }
        batch, logits = actor_batch(rows=rows, masks=single)

        def loss_fn(tree: dict[str, jnp.ndarray]) -> jnp.ndarray:
            loss, _ = headwise_actor_objective(tree, batch, config=PPOConfig())
            return loss

        gradients = jax.grad(loss_fn)(logits)
        for name in HEAD_NAMES:
            np.testing.assert_array_equal(np.asarray(gradients[name]), 0.0)

    def test_head_ratios_do_not_couple(self) -> None:
        batch, logits = actor_batch()
        _, baseline = headwise_actor_objective(logits, batch, config=PPOConfig())
        changed = dict(logits)
        changed["worker_cap"] = changed["worker_cap"].at[:, 0].add(2.0)
        _, after = headwise_actor_objective(changed, batch, config=PPOConfig())
        self.assertNotAlmostEqual(
            float(baseline["heads"]["worker_cap"]["mean_ratio"]),
            float(after["heads"]["worker_cap"]["mean_ratio"]),
        )
        for name in HEAD_NAMES:
            if name != "worker_cap":
                self.assertAlmostEqual(
                    float(baseline["heads"][name]["mean_ratio"]),
                    float(after["heads"][name]["mean_ratio"]),
                    places=7,
                )

    def test_active_heads_are_equal_weight_not_sample_weight(self) -> None:
        rows = 4
        masks = {name: np.zeros((rows, size), dtype=np.bool_) for name, size in HEAD_SIZES.items()}
        for name in HEAD_NAMES:
            masks[name][:, 0] = True
        masks["production_line"][:, :2] = True
        masks["worker_cap"][0, :2] = True
        batch, logits = actor_batch(rows=rows, masks=masks)
        loss, metrics = headwise_actor_objective(logits, batch, config=PPOConfig())
        production = metrics["heads"]["production_line"]
        worker = metrics["heads"]["worker_cap"]
        expected = 0.5 * (
            production["policy_loss"] - 0.01 * production["entropy"]
            + worker["policy_loss"] - 0.01 * worker["entropy"]
        )
        self.assertAlmostEqual(float(loss), float(expected), places=7)
        self.assertEqual(float(production["active_samples"]), 4.0)
        self.assertEqual(float(worker["active_samples"]), 1.0)

    def test_responsibility_scope_zeroes_nonselected_actor_gradients(self) -> None:
        batch, logits = actor_batch()

        def loss_fn(tree: dict[str, jnp.ndarray]) -> jnp.ndarray:
            loss, _ = headwise_actor_objective(
                tree,
                batch,
                config=PPOConfig(),
                actor_heads=("production_line",),
            )
            return loss

        gradients = jax.grad(loss_fn)(logits)
        self.assertGreater(
            float(np.max(np.abs(np.asarray(gradients["production_line"])))), 0.0
        )
        for name in HEAD_NAMES:
            if name != "production_line":
                np.testing.assert_array_equal(np.asarray(gradients[name]), 0.0)

    def test_kl_guard_monitors_nonselected_heads(self) -> None:
        batch, logits = actor_batch()
        changed = dict(logits)
        changed["worker_cap"] = changed["worker_cap"].at[:, 0].add(3.0)
        _, metrics = headwise_actor_objective(
            changed,
            batch,
            config=PPOConfig(),
            actor_heads=("production_line",),
        )
        self.assertGreater(
            float(metrics["heads"]["worker_cap"]["exact_kl"]), 0.0
        )
        self.assertGreater(float(metrics["max_active_head_exact_kl"]), 0.0)
        self.assertFalse(metrics["heads"]["worker_cap"]["optimized"])


class AdvantageAndUpdateTest(unittest.TestCase):
    def test_no_catastrophe_disables_constraint_actor_term(self) -> None:
        left = tiny_episode(catastrophe=False)
        prepared, _ = prepare_binding_training_data(
            "easy/starter", left, reward_config=RewardConfig(), ppo_config=PPOConfig()
        )
        combined, report = concatenate_bindings(
            {"easy/starter": left},
            {"easy/starter": prepared},
            constraint_lambda=0.5,
        )
        np.testing.assert_array_equal(combined["constraint_advantage"], 0.0)
        self.assertFalse(report["constraint"]["easy"]["actor_constraint_enabled"])
        np.testing.assert_allclose(
            combined["actor_advantage"], combined["reward_advantage"], atol=0.0
        )

    def test_one_update_and_checkpoint_metadata(self) -> None:
        data, params = behavior_table(16)
        data["actor_advantage"] = np.asarray([1.0, -0.6, 0.8, -0.4] * 4, np.float32)
        data["reward_return"] = np.asarray(data["value"]) + 1.0
        data["constraint_return"] = np.asarray(data["constraint_value"]) + 0.5
        config = PPOConfig(
            actor_learning_rate=1.0e-4,
            critic_learning_rate=3.0e-4,
            minibatch_size=16,
            epochs=1,
        )
        state = create_train_state(params, config)
        updated, metrics = train_minibatch(
            state, make_batch(data, np.arange(16)), config=config
        )
        changes = parameter_change_report(params, updated.params)
        self.assertGreater(changes["actor_changed_leaves"], 0)
        self.assertGreater(changes["critic_changed_leaves"], 0)
        self.assertGreater(float(metrics["heads"]["production_line"]["active_samples"]), 0)

        initial = initialize_payload(114941, policy_seed=114942)
        payload = build_checkpoint_payload(
            initial,
            updated.params,
            initial_checkpoint_sha256="a" * 64,
            source_sha256={"trainer": "b" * 64},
            dataset_sha256={"easy/starter": "c" * 64},
            rollout_report_sha256={"easy/starter": "d" * 64},
            reward_config=RewardConfig(),
            ppo_config=PPOConfig(),
            iteration=2,
            training_seed=114943,
        )
        validate_checkpoint_metadata(payload)
        self.assertIsNone(payload["strategy_parent"])
        self.assertTrue(payload["PPO"])
        self.assertEqual(payload["training_method"], TRAINING_METHOD)
        self.assertIn("relative-share", payload["reward_contract"]["schema"])
        self.assertEqual(payload["training_source_sha256"]["trainer"], "b" * 64)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.msgpack"
            path.write_bytes(serialization.msgpack_serialize(payload))
            restored = serialization.msgpack_restore(path.read_bytes())
            validate_checkpoint_metadata(restored)
            self.assertEqual(restored["training_method"], TRAINING_METHOD)

    def test_scoped_update_freezes_trunk_and_non_target_heads(self) -> None:
        data, params = behavior_table(16)
        data["actor_advantage"] = np.asarray([1.0, -0.6, 0.8, -0.4] * 4, np.float32)
        data["reward_return"] = np.asarray(data["value"]) + 1.0
        data["constraint_return"] = np.asarray(data["constraint_value"]) + 0.5
        config = PPOConfig(
            actor_learning_rate=1.0e-4,
            critic_learning_rate=3.0e-4,
            minibatch_size=16,
            epochs=1,
        )
        state = create_scoped_train_state(
            params, config, actor_heads=("production_line",)
        )
        before_logits = state.apply_fn(
            {"params": state.params}, jnp.asarray(data["features"])
        )["actor_logits"]
        updated, _ = train_minibatch(
            state,
            make_batch(data, np.arange(16)),
            config=config,
            actor_heads=("production_line",),
        )
        changes = parameter_root_changes(params, updated.params)
        self.assertGreater(changes["production_line_head"], 0.0)
        self.assertGreater(changes["value_head"], 0.0)
        self.assertGreater(changes["constraint_value_head"], 0.0)
        for root, change in changes.items():
            if root not in {
                "production_line_head",
                "value_head",
                "constraint_value_head",
            }:
                self.assertEqual(change, 0.0, root)
        after_logits = updated.apply_fn(
            {"params": updated.params}, jnp.asarray(data["features"])
        )["actor_logits"]
        for name in HEAD_NAMES:
            if name != "production_line":
                np.testing.assert_array_equal(
                    np.asarray(before_logits[name]), np.asarray(after_logits[name])
                )


if __name__ == "__main__":
    unittest.main()
