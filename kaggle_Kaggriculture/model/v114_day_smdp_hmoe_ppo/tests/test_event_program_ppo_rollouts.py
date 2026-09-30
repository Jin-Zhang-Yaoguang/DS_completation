from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np


HERE = Path(__file__).resolve().parents[1]
import sys

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import collect_event_program_ppo_rollouts as collector  # noqa: E402
from event_program import MacroActionMask, ProductionLine  # noqa: E402
from event_program_features import DECISION_HEAD_VALUES  # noqa: E402
from initialize_event_program_manager import write_checkpoint  # noqa: E402
from policy_trainable_event_program import (  # noqa: E402
    TrainableEventProgramPolicy,
    qualified_macro_action_masks,
)
from seed_ledger import SeedLedger  # noqa: E402


def observation(step: int = 0, *, money: int = 3000, planted: bool = True) -> dict:
    tiles = [[None for _ in range(10)] for _ in range(10)]
    if planted:
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
        "town": {"unlocked_shops": ["BAKERY", "PET_CAFE"]},
    }


def mock_transition(index: int = 0) -> dict:
    actions = {
        "production_line": 0,
        "worker_cap": 0,
        "cash_reserve": 0,
        "sell_style": 0,
        "terminal_mode": 0,
    }
    masks = {
        name: np.ones(size, dtype=np.bool_)
        for name, size in collector.HEAD_SIZES.items()
    }
    masks["production_line"][1] = False
    return {
        "features": np.full(427, index, dtype=np.float32),
        "masks": masks,
        "actions": actions,
        "old_joint_logp": -1.25,
        "old_logits": {
            name: np.arange(size, dtype=np.float32)
            for name, size in collector.HEAD_SIZES.items()
        },
        "value": 10.0,
        "constraint_value": -1.0,
        "start_step": index * 24,
        "start_day": index,
        "end_step": (index + 1) * 24,
        "duration_turns": 24,
        "next_value": 11.0,
        "next_constraint_value": -0.5,
        "terminal": False,
        "own_money_start": 3000.0,
        "own_money_end": 3010.0,
        "reward_delta_money": 10.0,
        "training_reward_raw": 10.0,
        "training_reward_source": "public_own_money_delta",
        "candidate_reward": 5000.0,
        "opponent_reward": 4000.0,
        "margin": 1000.0,
        "score": 1.0,
        "catastrophe": False,
    }


class TrackingLedger(SeedLedger):
    reserve_calls = 0
    expose_calls = 0

    def reserve_schedule(self, *args, **kwargs):
        type(self).reserve_calls += 1
        return super().reserve_schedule(*args, **kwargs)

    def mark_schedule_exposed(self, *args, **kwargs):
        type(self).expose_calls += 1
        return super().mark_schedule_exposed(*args, **kwargs)


class EventProgramPPORolloutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.checkpoint = cls.root / "manager.msgpack"
        write_checkpoint(cls.checkpoint, seed=114901, policy_seed=7719)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_carrot_is_false_but_production_head_stays_five_wide(self) -> None:
        obs = observation(0, planted=False)
        masks = qualified_macro_action_masks(obs)
        carrot = DECISION_HEAD_VALUES["production_line"].index(ProductionLine.CARROT)
        self.assertEqual(masks["production_line"].shape, (1, 5))
        self.assertFalse(bool(masks["production_line"][0, carrot]))
        self.assertEqual(int(masks["production_line"].sum()), 4)

    def test_sampled_action_is_legal_and_reproducible_by_rollout_key(self) -> None:
        obs = observation(0, planted=False)
        left = TrainableEventProgramPolicy(
            self.checkpoint, rollout_seed=90, episode_key="episode-a"
        )
        right = TrainableEventProgramPolicy(
            self.checkpoint, rollout_seed=90, episode_key="episode-a"
        )
        left.act(copy.deepcopy(obs))
        right.act(copy.deepcopy(obs))
        self.assertEqual(left.transitions[0]["actions"], right.transitions[0]["actions"])
        self.assertEqual(left.transitions[0]["old_joint_logp"], right.transitions[0]["old_joint_logp"])
        np.testing.assert_array_equal(
            left.transitions[0]["features"], right.transitions[0]["features"]
        )
        decision = left.state.decision
        self.assertTrue(MacroActionMask.from_observation(obs).allows(decision))
        self.assertIsNot(decision.production_line, ProductionLine.CARROT)
        for head, action in left.transitions[0]["actions"].items():
            self.assertTrue(bool(left.transitions[0]["masks"][head][action]))

        signatures = set()
        for key_index in range(12):
            policy = TrainableEventProgramPolicy(
                self.checkpoint,
                rollout_seed=90,
                episode_key=f"episode-{key_index}",
            )
            policy.act(copy.deepcopy(obs))
            signatures.add(tuple(policy.transitions[0]["actions"].values()))
        self.assertGreater(len(signatures), 1)

    def test_full_season_has_28_transitions_and_duration_sum_719(self) -> None:
        policy = TrainableEventProgramPolicy(
            self.checkpoint, rollout_seed=91, episode_key="full-season"
        )
        final_obs = None
        for step in range(719):
            final_obs = observation(step)
            action = policy.act(final_obs)
            if step >= 671:
                self.assertFalse(
                    any(order and str(order[0]).startswith("BUY") for order in action["market"])
                )
        transitions = policy.finalize_episode(
            candidate_reward=5200,
            opponent_reward=4800,
            final_observation=final_obs,
            terminal_step=719,
        )
        self.assertEqual(len(transitions), 28)
        self.assertEqual([row["start_step"] for row in transitions], list(range(0, 672, 24)))
        self.assertEqual(sum(row["duration_turns"] for row in transitions), 719)
        self.assertTrue(transitions[-1]["terminal"])
        self.assertEqual(transitions[-1]["duration_turns"], 71)
        self.assertTrue(all(row["candidate_reward"] == 5200 for row in transitions))
        self.assertTrue(all(row["training_reward_source"] == "public_own_money_delta" for row in transitions))
        self.assertEqual(policy.terminal_procurement_count, 0)

    def test_npz_roundtrip_has_fixed_offsets_and_no_pickle(self) -> None:
        transition = mock_transition()
        transition["terminal"] = True
        episode = {
            "episode_id": "roundtrip:seed-1:seat-0",
            "seed": 1,
            "seat": 0,
            "opponent_id": "builtin:starter",
            "status": "DONE",
            "error": None,
            "transitions": [transition],
        }
        empty_episode = {
            "episode_id": "roundtrip:seed-1:seat-1",
            "seed": 1,
            "seat": 1,
            "opponent_id": "builtin:starter",
            "status": "ERROR",
            "error": "mock failure",
            "transitions": [],
        }
        arrays = collector.build_npz_arrays([episode, empty_episode])
        path = self.root / "roundtrip.npz"
        collector.atomic_npz(path, arrays)
        with np.load(path, allow_pickle=False) as restored:
            self.assertEqual(str(restored["schema"]), collector.NPZ_SCHEMA)
            np.testing.assert_array_equal(restored["episode_offsets"], [0, 1, 1])
            self.assertEqual(restored["features"].shape, (1, 427))
            self.assertEqual(restored["mask_production_line"].shape, (1, 5))
            self.assertFalse(bool(restored["mask_production_line"][0, 1]))
            self.assertEqual(int(restored["action_worker_cap"][0]), 0)
            self.assertEqual(str(restored["episode_error"][1]), "mock failure")

    def test_worker_failure_is_persisted_and_seed_is_exposed(self) -> None:
        def broken_worker(*_args):
            raise RuntimeError("deliberate rollout crash")

        TrackingLedger.reserve_calls = 0
        TrackingLedger.expose_calls = 0
        ledger = self.root / "failure-ledger.json"
        output_npz = self.root / "failure.npz"
        output_report = self.root / "failure.json"
        args = argparse.Namespace(
            checkpoint=self.checkpoint,
            seed_start=99100,
            seeds=1,
            rollout_seed=321,
            opponent="builtin:starter",
            campaign="failure-exposure-test",
            split="train",
            registry_sha256="f" * 64,
            ledger=ledger,
            output_npz=output_npz,
            output_report=output_report,
            workers=1,
        )
        report = collector.run_campaign(
            args,
            worker_fn=broken_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )
        self.assertEqual(report["status"], "INVALID")
        self.assertEqual(TrackingLedger.reserve_calls, 1)
        self.assertEqual(TrackingLedger.expose_calls, 1)
        self.assertEqual(report["summary"]["errors"], 2)
        self.assertTrue(any("deliberate rollout crash" in row["error"] for row in report["episodes"]))
        self.assertEqual(SeedLedger(ledger).snapshot()["indexes"]["exposed"], [99100])
        self.assertTrue(output_npz.is_file())
        self.assertTrue(output_report.is_file())
        with np.load(output_npz, allow_pickle=False) as restored:
            np.testing.assert_array_equal(restored["episode_offsets"], [0, 0, 0])
            self.assertEqual(restored["features"].shape, (0, 427))


if __name__ == "__main__":
    unittest.main()
