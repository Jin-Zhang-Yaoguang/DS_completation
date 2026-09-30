from __future__ import annotations

import sys
from pathlib import Path
import unittest

from flax.core import freeze
import jax.numpy as jnp
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
V113 = ROOT.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
from train_latent_awr import (  # noqa: E402
    TRAINABLE_ROOTS,
    V6_ARCHITECTURE,
    V6_MODEL_ID,
    build_parser,
    cap_catastrophe_weights,
    clipped_awr_weights,
    composite_episode_utility,
    normalize_candidate_action_keys,
    opponent_layers_from_report,
    parameter_labels,
    rank_standardized_advantages,
    validate_dataset,
    validate_v6_payload,
)


class LatentAWRTest(unittest.TestCase):
    def test_rank_advantage_is_per_option_per_complete_game(self):
        option = np.asarray([1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        episode = np.asarray([10, 10, 10, 10, 11, 11, 20, 20, 21, 21])
        seat = np.asarray([0, 0, 1, 1, 0, 0, 0, 0, 0, 0])
        returns = np.asarray([100, 100, 300, 300, 200, 200, 7, 7, 7, 7])
        advantage = rank_standardized_advantages(option, episode, seat, returns)

        # Rows in one complete game share one weight; rankings are independent
        # between options.  Option 2 has only tied games and therefore zero A.
        np.testing.assert_allclose(advantage[:2], advantage[0])
        np.testing.assert_allclose(advantage[2:4], advantage[2])
        self.assertLess(float(advantage[0]), float(advantage[4]))
        self.assertLess(float(advantage[4]), float(advantage[2]))
        np.testing.assert_array_equal(advantage[6:], np.zeros(4, dtype=np.float32))

    def test_rank_advantage_rejects_inconsistent_game_return(self):
        with self.assertRaisesRegex(ValueError, "constant"):
            rank_standardized_advantages(
                np.asarray([1, 1]),
                np.asarray([10, 10]),
                np.asarray([0, 0]),
                np.asarray([1.0, 2.0]),
            )

    def test_awr_weight_is_exponential_and_upper_clipped(self):
        advantage = np.asarray([-2.0, 0.0, 2.0], dtype=np.float32)
        weights = clipped_awr_weights(advantage, beta=1.5, clip=4.0)
        self.assertAlmostEqual(float(weights[0]), float(np.exp(-3.0)), places=6)
        self.assertEqual(float(weights[1]), 1.0)
        self.assertEqual(float(weights[2]), 4.0)

    def test_catastrophe_rows_can_never_receive_reinforcing_weight(self):
        weights = cap_catastrophe_weights(
            np.asarray([5.0, 0.2, 3.0]),
            np.asarray([1299.0, 2500.0, 5000.0]),
            catastrophe_threshold=3000.0,
            catastrophe_weight_cap=0.5,
        )
        np.testing.assert_allclose(weights, np.asarray([0.5, 0.2, 3.0]))

    def test_composite_utility_rejects_catastrophic_win(self):
        utility = composite_episode_utility(
            np.asarray([1.003, -1.01, 1.01]),
            np.asarray([1299.0, 5000.0, 6000.0]),
            own_reward_coefficient=0.25,
            catastrophe_penalty=2.0,
            catastrophe_threshold=3000.0,
        )
        self.assertLess(float(utility[0]), float(utility[1]))
        self.assertLess(float(utility[0]), float(utility[2]))

    def test_advantage_is_normalized_within_opponent_layer(self):
        advantage = rank_standardized_advantages(
            np.asarray([1, 1, 1, 1]),
            np.asarray([10, 11, 12, 13]),
            np.asarray([0, 0, 0, 0]),
            np.asarray([-100.0, -90.0, 1.0, 2.0]),
            np.asarray(["gold", "gold", "anchor", "anchor"]),
        )
        np.testing.assert_allclose(
            advantage, np.asarray([-1.0, 1.0, -1.0, 1.0], dtype=np.float32)
        )

    def test_dataset_requires_explicit_candidate_actions_and_returns(self):
        rows = 4
        data = {
            "global": np.zeros((rows, 60), dtype=np.float32),
            "board": np.zeros((rows, 2, 10, 10, 21), dtype=np.float32),
            "units": np.zeros((rows, 16, 121), dtype=np.float32),
            "unit_mask": np.ones((rows, 16), dtype=np.float32),
            "candidate_unit_tokens": np.zeros((rows, 16), dtype=np.int16),
            "candidate_unit_quantities": np.zeros((rows, 16), dtype=np.int16),
            "candidate_market_tokens": np.zeros(
                (rows, space.MAX_MARKET_SLOTS), dtype=np.int16
            ),
            "candidate_market_quantities": np.zeros(
                (rows, space.MAX_MARKET_SLOTS), dtype=np.int16
            ),
            "candidate_market_mask": np.ones(
                (rows, space.MAX_MARKET_SLOTS), dtype=np.uint8
            ),
            "option_id": np.asarray([1, 1, 2, 2], dtype=np.int8),
            "episode": np.asarray([10, 10, 20, 20], dtype=np.int64),
            "seat": np.asarray([0, 0, 1, 1], dtype=np.int8),
            "episode_return": np.asarray([5, 5, 7, 7], dtype=np.float32),
            "candidate_reward": np.asarray([5000, 5000, 6000, 6000], dtype=np.float32),
            "source_kind": np.asarray(["candidate_self_imitation"] * rows),
            # These labels may coexist for provenance, but are never required
            # or substituted for candidate actions.
            "unit_tokens": np.full((rows, 16), 9, dtype=np.int16),
            "teacher_id": np.asarray(["teacher"] * rows),
        }
        self.assertEqual(validate_dataset(data), rows)
        del data["candidate_unit_tokens"]
        with self.assertRaisesRegex(ValueError, "candidate_unit_tokens"):
            validate_dataset(data)

    def test_legacy_collector_actions_require_self_imitation_provenance(self):
        data = {
            "source_kind": np.asarray(["candidate_self_imitation"]),
            "unit_tokens": np.zeros((1, 16), dtype=np.int16),
            "unit_quantities": np.zeros((1, 16), dtype=np.int16),
            "market_tokens": np.zeros((1, space.MAX_MARKET_SLOTS), dtype=np.int16),
            "market_quantities": np.zeros((1, space.MAX_MARKET_SLOTS), dtype=np.int16),
            "market_mask": np.ones((1, space.MAX_MARKET_SLOTS), dtype=np.uint8),
        }
        normalize_candidate_action_keys(data)
        self.assertIn("candidate_unit_tokens", data)
        data["source_kind"] = np.asarray(["teacher"])
        with self.assertRaisesRegex(ValueError, "candidate_self_imitation"):
            normalize_candidate_action_keys(data)

    def test_opponent_layers_follow_episode_seed_contract(self):
        data = {
            "episode": np.asarray([31, 31, 35]),
            "option_id": np.asarray([1, 1, 2]),
        }
        report = {
            "opponent_schedule": [
                {"seed": 10, "layer": "gold_train"},
                {"seed": 11, "layer": "anchor"},
            ]
        }
        np.testing.assert_array_equal(
            opponent_layers_from_report(data, report),
            np.asarray(["gold_train", "gold_train", "anchor"]),
        )

    def test_parameter_scope_freezes_encoder_manager_and_option_router(self):
        params = freeze(
            {
                "own_core_dense": {"kernel": jnp.ones((2, 2))},
                "option_router_head": {"kernel": jnp.ones((2, 3))},
                "catastrophe_head": {"kernel": jnp.ones((2, 3))},
                "unit_gru": {"kernel": jnp.ones((2, 2))},
                "market_role_head": {"kernel": jnp.ones((2, 3))},
                "option_value_head": {"kernel": jnp.ones((2, 1))},
            }
        )
        labels = parameter_labels(params)
        self.assertEqual(labels["own_core_dense"]["kernel"], "freeze")
        self.assertEqual(labels["option_router_head"]["kernel"], "freeze")
        self.assertEqual(labels["catastrophe_head"]["kernel"], "freeze")
        self.assertEqual(labels["unit_gru"]["kernel"], "train")
        self.assertEqual(labels["market_role_head"]["kernel"], "train")
        self.assertEqual(labels["option_value_head"]["kernel"], "train")
        self.assertIn("unit_action_head", TRAINABLE_ROOTS)

    def test_v6_validation_rejects_v7_and_accepts_optimization_anchor(self):
        payload = {
            "params": {"x": np.asarray([1.0])},
            "model_id": V6_MODEL_ID,
            "architecture": V6_ARCHITECTURE,
            "dataset_sha256": "dataset-v6",
            "strategy_parent": None,
            "inherits_v113_checkpoint": False,
            "online_historical_agent_fallback": False,
            "teacher_role_conditions_action_decoder": False,
        }
        validate_v6_payload(
            payload,
            Path("latent_role_bc_v6/checkpoint.msgpack"),
            actual_sha256="checkpoint-v6",
            expected_sha256="checkpoint-v6",
            expected_dataset_sha256="dataset-v6",
        )
        with self.assertRaisesRegex(ValueError, "never from V7"):
            validate_v6_payload(
                payload,
                Path("latent_role_dagger_v7/checkpoint.msgpack"),
                actual_sha256="checkpoint-v6",
                expected_sha256="checkpoint-v6",
                expected_dataset_sha256="dataset-v6",
            )

    def test_cli_pre_registers_epochs_lr_beta_clip_and_kl(self):
        args = build_parser().parse_args(
            [
                "--dataset",
                "rollout.npz",
                "--rollout-report",
                "rollout.json",
                "--output-dir",
                "out",
                "--epochs",
                "3",
                "--lr",
                "0.00002",
                "--beta",
                "1.25",
                "--clip",
                "8",
                "--kl",
                "0.2",
            ]
        )
        self.assertEqual(args.epochs, 3)
        self.assertAlmostEqual(args.learning_rate, 2e-5)
        self.assertAlmostEqual(args.beta, 1.25)
        self.assertAlmostEqual(args.weight_clip, 8.0)
        self.assertAlmostEqual(args.kl_coefficient, 0.2)


if __name__ == "__main__":
    unittest.main()
