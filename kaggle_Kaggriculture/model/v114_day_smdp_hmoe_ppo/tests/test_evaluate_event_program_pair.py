from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

from flax import serialization


ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluate_event_program_pair as pair_eval  # noqa: E402
from event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM  # noqa: E402
from model_event_program_ppo import make_checkpoint_payload  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


def _side(*, reward: float, opponent_reward: float = 5000.0) -> dict:
    margin = reward - opponent_reward
    return {
        "reward": reward,
        "opponent_reward": opponent_reward,
        "margin": margin,
        "score": pair_eval.game_score(margin),
        "catastrophe": reward < pair_eval.CATASTROPHE_REWARD,
        "action_steps": pair_eval.EXPECTED_ACTION_STEPS,
        "decision_count": pair_eval.EXPECTED_DAY_TRANSITIONS,
        "contract_violations": 0,
        "terminal_procurement": 0,
        "status": "DONE",
        "opponent_status": "DONE",
        "statuses": ["DONE", "DONE"],
        "environment_states": 720,
        "error": None,
    }


def mock_worker(checkpoint_specs, seed, opponent_id, rollout_seed):
    del checkpoint_specs, rollout_seed
    rows = []
    for seat in (0, 1):
        episode_key = pair_eval.checkpoint_independent_episode_key(
            seed, seat, opponent_id
        )
        rows.append(
            pair_eval._paired_row(
                seed=seed,
                seat=seat,
                opponent_id=opponent_id,
                episode_key=episode_key,
                incumbent=_side(reward=5000.0 + seat),
                challenger=_side(reward=5200.0 + seat),
            )
        )
    return rows


class TrackingLedger(SeedLedger):
    reserve_calls = 0
    expose_calls = 0

    def reserve_schedule(self, *args, **kwargs):
        type(self).reserve_calls += 1
        return super().reserve_schedule(*args, **kwargs)

    def mark_schedule_exposed(self, *args, **kwargs):
        type(self).expose_calls += 1
        return super().mark_schedule_exposed(*args, **kwargs)


class EvaluateEventProgramPairTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.incumbent = self.root / "incumbent.msgpack"
        self.challenger = self.root / "challenger.msgpack"
        self._write_checkpoint(self.incumbent, marker=1)
        self._write_checkpoint(self.challenger, marker=2)
        TrackingLedger.reserve_calls = 0
        TrackingLedger.expose_calls = 0

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _write_checkpoint(path: Path, *, marker: int, policy_seed: int = 77) -> None:
        payload = make_checkpoint_payload({"test_marker": marker})
        payload.update(
            {
                "input_dim": MANAGER_FEATURE_DIM,
                "feature_schema": FEATURE_SCHEMA,
                "policy_seed": policy_seed,
            }
        )
        path.write_bytes(serialization.msgpack_serialize(payload))

    def args(self, **overrides):
        values = {
            "incumbent": self.incumbent,
            "challenger": self.challenger,
            "seed_start": 99200,
            "seeds": 2,
            "opponent": "builtin:starter",
            "rollout_seed": 114921,
            "campaign": "v114-v9-pair-test",
            "split": "train",
            "ledger": self.root / "ledger.json",
            "output": self.root / "report.json",
            "workers": 2,
            "bootstrap_seed": 19,
            "bootstrap_samples": 200,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_exact_seed_seat_pairing_and_one_ledger_reservation(self):
        args = self.args()
        report = pair_eval.run_campaign(
            args,
            worker_fn=mock_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )

        self.assertEqual(report["status"], "VALID")
        self.assertEqual(TrackingLedger.reserve_calls, 1)
        self.assertEqual(TrackingLedger.expose_calls, 1)
        self.assertEqual(len(report["rows"]), 4)
        self.assertEqual(
            {(row["seed"], row["seat"], row["opponent_id"]) for row in report["rows"]},
            {
                (99200, 0, "builtin:starter"),
                (99200, 1, "builtin:starter"),
                (99201, 0, "builtin:starter"),
                (99201, 1, "builtin:starter"),
            },
        )
        for row in report["rows"]:
            self.assertEqual(row["reward_delta"], 200.0)
            for role in pair_eval.CHECKPOINT_ROLES:
                self.assertIn("reward", row[role])
                self.assertIn("opponent_reward", row[role])
                self.assertIn("action_steps", row[role])
                self.assertIn("decision_count", row[role])
                self.assertIn("contract_violations", row[role])
                self.assertIn("terminal_procurement", row[role])
        self.assertEqual(
            SeedLedger(args.ledger).snapshot()["indexes"]["exposed"],
            [99200, 99201],
        )
        self.assertEqual(json.loads(args.output.read_text())["status"], "VALID")

    def test_episode_key_has_no_checkpoint_or_campaign_identity(self):
        first = pair_eval.checkpoint_independent_episode_key(
            12, 1, "registry:gold-a"
        )
        second = pair_eval.checkpoint_independent_episode_key(
            12, 1, "registry:gold-a"
        )
        self.assertEqual(first, second)
        self.assertNotIn("incumbent", first)
        self.assertNotIn("challenger", first)
        self.assertNotIn(str(self.incumbent), first)
        self.assertNotIn(str(self.challenger), first)
        self.assertNotIn("v114-v9-pair-test", first)
        self.assertNotEqual(
            first,
            pair_eval.checkpoint_independent_episode_key(12, 0, "registry:gold-a"),
        )

    def test_bootstrap_averages_both_seats_before_resampling(self):
        rows = []
        for seed, deltas in ((1, (1.0, 3.0)), (2, (-1.0, -3.0))):
            for seat, delta in enumerate(deltas):
                incumbent = _side(reward=5000.0)
                challenger = _side(reward=5000.0 + delta)
                row = pair_eval._paired_row(
                    seed=seed,
                    seat=seat,
                    opponent_id="builtin:starter",
                    episode_key=pair_eval.checkpoint_independent_episode_key(
                        seed, seat, "builtin:starter"
                    ),
                    incumbent=incumbent,
                    challenger=challenger,
                )
                row["reward_delta"] = delta
                rows.append(row)

        analysis = pair_eval.paired_analysis(
            rows, bootstrap_samples=200, bootstrap_seed=5
        )
        self.assertEqual(analysis["valid_seed_blocks"], 2)
        self.assertEqual(
            analysis["reward_delta"]["seed_block_values"],
            {"1": 2.0, "2": -2.0},
        )
        self.assertEqual(
            analysis["bootstrap_unit"], "seed_block_preserving_both_seats"
        )
        self.assertEqual(
            analysis["reward_delta"]["seed_block_ci95"],
            pair_eval.seed_block_bootstrap_ci(
                [2.0, -2.0], samples=200, seed=7
            ),
        )

    def test_checkpoints_and_critical_sources_remain_unchanged(self):
        args = self.args(seeds=1)
        report = pair_eval.run_campaign(
            args,
            worker_fn=mock_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )
        self.assertTrue(report["checkpoints"]["incumbent"]["unchanged"])
        self.assertTrue(report["checkpoints"]["challenger"]["unchanged"])
        self.assertTrue(all(row["unchanged"] for row in report["sources"].values()))

    def test_checkpoint_mutation_is_fail_closed_after_seed_exposure(self):
        args = self.args(seeds=1)

        def mutating_worker(*worker_args):
            rows = mock_worker(*worker_args)
            self.challenger.write_bytes(self.challenger.read_bytes() + b"changed")
            return rows

        report = pair_eval.run_campaign(
            args,
            worker_fn=mutating_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )
        self.assertEqual(report["status"], "INVALID")
        self.assertFalse(report["checkpoints"]["challenger"]["unchanged"])
        self.assertIn(
            "challenger checkpoint SHA256 changed during evaluation",
            report["validation_errors"],
        )
        self.assertEqual(
            SeedLedger(args.ledger).snapshot()["indexes"]["exposed"], [99200]
        )

    def test_worker_failure_is_preserved_and_seed_is_exposed(self):
        def broken_worker(*_args):
            raise RuntimeError("paired worker crash")

        args = self.args(seeds=1)
        report = pair_eval.run_campaign(
            args,
            worker_fn=broken_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )

        self.assertEqual(report["status"], "INVALID")
        self.assertEqual(len(report["worker_failures"]), 1)
        self.assertEqual(len(report["rows"]), 2)
        for row in report["rows"]:
            self.assertIn("paired worker crash", row["incumbent"]["error"])
            self.assertIn("paired worker crash", row["challenger"]["error"])
        self.assertEqual(report["paired"]["excluded_seed_blocks"], 1)
        self.assertEqual(
            SeedLedger(args.ledger).snapshot()["indexes"]["exposed"], [99200]
        )
        self.assertTrue(args.output.is_file())

    def test_policy_seed_mismatch_fails_before_ledger_write(self):
        self._write_checkpoint(self.challenger, marker=2, policy_seed=78)
        args = self.args()
        with self.assertRaisesRegex(ValueError, "policy_seed mismatch"):
            pair_eval.run_campaign(
                args,
                worker_fn=mock_worker,
                executor_cls=ThreadPoolExecutor,
                ledger_cls=TrackingLedger,
            )
        self.assertFalse(args.ledger.exists())
        self.assertFalse(args.output.exists())


if __name__ == "__main__":
    unittest.main()
