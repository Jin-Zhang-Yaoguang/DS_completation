from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from event_program import MacroActionMask, TERMINAL_START_STEP
from event_program_features import (
    AUX_FEATURE_DIM,
    CRITIC_FEATURE_DIM,
    FEATURE_SCHEMA,
    MANAGER_FEATURE_DIM,
    encode_event_program_features,
    macro_action_mask_arrays,
)
from initialize_event_program_manager import write_checkpoint
from policy_random_event_program import RandomEventProgramPolicy


def observation(step: int = 0, *, money: int = 3000) -> dict:
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[0][0] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 0,
        "yield_units": 2,
        "watered_today": False,
    }
    own = {
        "money": money,
        "farmer": [4, 4],
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": [0],
        "tiles": tiles,
    }
    opponent = {
        "money": 3000,
        "farmer": [5, 5],
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": [0],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [own, opponent],
        "private": {
            "shed": {},
            "seeds": {"WHEAT": 2},
            "inventories": [{}],
        },
        "market": {"inventory": {}, "prices": {}},
        "town": {"unlocked_shops": ["BAKERY", "BAKERY", "PET_CAFE"]},
    }


class RandomEventProgramPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.checkpoint = Path(self.temp.name) / "random_manager.msgpack"
        self.report = write_checkpoint(
            self.checkpoint,
            seed=114009,
            policy_seed=7719,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_feature_dimensions_and_schema(self) -> None:
        features = encode_event_program_features(observation(48))
        self.assertEqual(features.shape, (MANAGER_FEATURE_DIM,))
        self.assertEqual(CRITIC_FEATURE_DIM, 387)
        self.assertEqual(AUX_FEATURE_DIM, 40)
        self.assertEqual(FEATURE_SCHEMA["input_dim"], 427)
        self.assertEqual(float(features[CRITIC_FEATURE_DIM:CRITIC_FEATURE_DIM + 8].sum()), 1.0)

    def test_information_boundary_ignores_forbidden_identity_fields(self) -> None:
        left = observation(0)
        right = copy.deepcopy(left)
        left.update({"seed": 11, "environment_seed": 12, "opponent_id": "alpha"})
        right.update({"seed": 999, "environment_seed": 1000, "opponent_id": "omega"})
        left["opponent_private"] = {"future": [1, 2, 3]}
        right["opponent_private"] = {"future": [999]}
        np.testing.assert_array_equal(
            encode_event_program_features(left),
            encode_event_program_features(right),
        )

    def test_mask_conversion_and_sampled_decision_are_legal(self) -> None:
        obs = observation(0, money=600)
        mask = MacroActionMask.from_observation(obs)
        arrays = macro_action_mask_arrays(mask)
        self.assertEqual([value.shape for value in arrays.values()], [(1, 5), (1, 3), (1, 3), (1, 3), (1, 2)])
        self.assertTrue(all(value.dtype == np.bool_ and value.any() for value in arrays.values()))
        policy = RandomEventProgramPolicy(self.checkpoint)
        policy.act(obs)
        self.assertTrue(mask.allows(policy.state.decision))

    def test_fixed_observation_and_checkpoint_are_reproducible(self) -> None:
        left = RandomEventProgramPolicy(self.checkpoint)
        right = RandomEventProgramPolicy(self.checkpoint)
        left_action = left.act(observation(0))
        right_action = right.act(observation(0))
        self.assertEqual(left_action, right_action)
        self.assertEqual(left.decision, right.decision)
        self.assertEqual(left.last_logits, right.last_logits)

    def test_non_day_boundary_keeps_plan_without_resampling(self) -> None:
        policy = RandomEventProgramPolicy(self.checkpoint)
        policy.act(observation(0))
        first_decision = policy.state.decision
        first_generation = policy.state.generation
        policy.act(observation(1))
        self.assertEqual(policy.manager_decision_count, 1)
        self.assertEqual(policy.state.decision, first_decision)
        self.assertEqual(policy.state.generation, first_generation)
        policy.act(observation(24))
        self.assertEqual(policy.manager_decision_count, 2)
        self.assertEqual(policy.state.generation, first_generation + 1)

    def test_terminal_executor_blocks_procurement_and_resampling(self) -> None:
        policy = RandomEventProgramPolicy(self.checkpoint)
        policy.act(observation(0))
        before = policy.manager_decision_count
        action = policy.act(observation(TERMINAL_START_STEP))
        self.assertEqual(policy.manager_decision_count, before)
        self.assertFalse(
            any(order and str(order[0]).startswith("BUY") for order in action["market"])
        )
        self.assertEqual(policy.terminal_procurement_count, 0)

    def test_checkpoint_metadata_is_independent_and_traceable(self) -> None:
        self.assertIsNone(self.report["strategy_parent"])
        self.assertEqual(self.report["input_dim"], 427)
        self.assertEqual(len(self.report["source_sha256"]), 64)

    def test_implementation_has_no_historical_shortcut_reference(self) -> None:
        for name in (
            "event_program_features.py",
            "initialize_event_program_manager.py",
            "policy_random_event_program.py",
        ):
            source = (HERE / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("v" + "6", source)


if __name__ == "__main__":
    unittest.main()
