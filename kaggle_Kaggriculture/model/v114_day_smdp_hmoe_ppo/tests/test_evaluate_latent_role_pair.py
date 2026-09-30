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

import evaluate_latent_role_pair as pair_eval  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


ARCHITECTURE = "v114-causal-latent-role-absorbing-stop-hmoe-v1"


def _valid_row(option_id: int, seed: int, seat: int, reward_bias: float) -> dict:
    candidate_reward = 5000.0 + reward_bias + seat
    opponent_reward = 4000.0
    margin = candidate_reward - opponent_reward
    return {
        "option_id": option_id,
        "seed": seed,
        "seat": seat,
        "candidate_reward": candidate_reward,
        "opponent_reward": opponent_reward,
        "margin": margin,
        "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
        "statuses": ["DONE", "DONE"],
        "steps": 720,
        "error": None,
        "catastrophe": candidate_reward < 3000.0,
        "option_usage": {str(option_id): 720},
        "unit_role_usage": {},
        "market_role_usage": {},
        "operation_counts": {},
        "nonpass_unit_orders": 1,
        "market_turns": 30,
        "ten_slot_market_turns": 0,
        "ten_slot_rate": 0.0,
        "market_sequence_lengths": {"0": 30},
    }


def _mock_worker(
    checkpoint_specs,
    option_id,
    seed,
    opponent_id,
    worker_cap,
    cash_reserve,
    terminal_buy_cutoff,
):
    del worker_cap, cash_reserve, terminal_buy_cutoff
    rows = []
    for spec in checkpoint_specs:
        bias = 0.0 if spec["candidate_id"] == "v6" else 100.0
        for seat in (0, 1):
            row = _valid_row(option_id, seed, seat, bias)
            row.update({
                "candidate_id": spec["candidate_id"],
                "checkpoint_sha256": spec["sha256"],
                "opponent_id": opponent_id,
            })
            rows.append(row)
    return rows


class EvaluateLatentRolePairTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.baseline = self.root / "v6.msgpack"
        self.candidate = self.root / "v8.msgpack"
        self._write_checkpoint(self.baseline, "v114_latent_role_v6")
        self._write_checkpoint(self.candidate, "v114_latent_role_v8")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _write_checkpoint(path: Path, model_id: str, **overrides) -> None:
        payload = {
            "model_id": model_id,
            "architecture": ARCHITECTURE,
            "inherits_v113_checkpoint": False,
            "online_historical_agent_fallback": False,
            "teacher_role_conditions_action_decoder": False,
            "params": {},
        }
        payload.update(overrides)
        path.write_bytes(serialization.msgpack_serialize(payload))

    def _args(self, **overrides):
        values = {
            "baseline_checkpoint": self.baseline,
            "candidate_checkpoint": self.candidate,
            "baseline_name": "v6",
            "candidate_name": "v8",
            "options": [1, 2],
            "seed_start": 9000,
            "seeds": 2,
            "opponent": "builtin:starter",
            "worker_cap": 4,
            "cash_reserve": 0.0,
            "terminal_buy_cutoff": 671,
            "campaign": "paired-test",
            "split": "train",
            "registry_sha256": "a" * 64,
            "ledger": self.root / "ledger.json",
            "output": self.root / "report.json",
            "workers": 2,
            "bootstrap_samples": 200,
            "bootstrap_seed": 17,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_one_reservation_pairs_both_checkpoints_on_exact_key(self):
        args = self._args()
        report = pair_eval.run_campaign(
            args, worker_fn=_mock_worker, executor_cls=ThreadPoolExecutor
        )

        self.assertEqual(report["status"], "VALID")
        self.assertEqual(
            report["pair_key_fields"],
            ["option_id", "seed", "seat", "opponent_id"],
        )
        self.assertEqual(len(report["rows"]), 16)
        self.assertEqual(report["paired"]["valid_pairs"], 8)
        self.assertEqual(report["paired"]["invalid_pairs"], 0)
        self.assertTrue(report["checkpoints"]["v6"]["unchanged"])
        self.assertTrue(report["checkpoints"]["v8"]["unchanged"])
        self.assertTrue(args.output.is_file())
        self.assertEqual(json.loads(args.output.read_text())["status"], "VALID")

        ledger = SeedLedger(args.ledger)
        snapshot = ledger.snapshot()
        self.assertEqual(len(snapshot["records"]), 2)
        self.assertEqual(snapshot["indexes"]["exposed"], [9000, 9001])
        self.assertTrue(all(row["seats"] == [0, 1] for row in snapshot["records"]))
        self.assertTrue(
            all(row["campaign_id"] == "paired-test" for row in snapshot["records"])
        )

    def test_future_exception_is_preserved_and_submitted_seed_is_exposed(self):
        def broken_worker(*_args):
            raise RuntimeError("mock worker crash")

        args = self._args(options=[1], seeds=1)
        report = pair_eval.run_campaign(
            args, worker_fn=broken_worker, executor_cls=ThreadPoolExecutor
        )

        self.assertEqual(report["status"], "INVALID")
        self.assertEqual(len(report["worker_failures"]), 1)
        self.assertEqual(len(report["rows"]), 4)
        self.assertTrue(all("mock worker crash" in row["error"] for row in report["rows"]))
        self.assertEqual(report["paired"]["invalid_pairs"], 2)
        self.assertEqual(SeedLedger(args.ledger).snapshot()["indexes"]["exposed"], [9000])
        self.assertTrue(args.output.is_file())

    def test_architecture_mismatch_fails_before_seed_reservation(self):
        self._write_checkpoint(
            self.candidate,
            "v114_latent_role_v8",
            architecture="different-architecture",
        )
        args = self._args()
        with self.assertRaisesRegex(ValueError, "architecture mismatch"):
            pair_eval.run_campaign(
                args, worker_fn=_mock_worker, executor_cls=ThreadPoolExecutor
            )
        self.assertFalse(args.ledger.exists())
        self.assertFalse(args.output.exists())

    def test_missing_teacher_role_contract_is_rejected(self):
        self.candidate.write_bytes(serialization.msgpack_serialize({
            "model_id": "v114_latent_role_v8",
            "architecture": ARCHITECTURE,
            "inherits_v113_checkpoint": False,
            "online_historical_agent_fallback": False,
            "params": {},
        }))
        with self.assertRaisesRegex(
            ValueError, "teacher_role_conditions_action_decoder"
        ):
            pair_eval.validate_checkpoint_pair(self.baseline, self.candidate)

    def test_checkpoint_mutation_is_reported_after_exposure(self):
        args = self._args(options=[1], seeds=1)

        def mutating_worker(*worker_args):
            rows = _mock_worker(*worker_args)
            self.candidate.write_bytes(self.candidate.read_bytes() + b"changed")
            return rows

        report = pair_eval.run_campaign(
            args, worker_fn=mutating_worker, executor_cls=ThreadPoolExecutor
        )
        self.assertEqual(report["status"], "INVALID")
        self.assertFalse(report["checkpoints"]["v8"]["unchanged"])
        self.assertIn(
            "checkpoint SHA256 changed or became unreadable",
            report["validation_errors"],
        )
        self.assertEqual(SeedLedger(args.ledger).snapshot()["indexes"]["exposed"], [9000])

    def test_bootstrap_uses_mean_of_both_seats_per_seed_block(self):
        pairs = []
        for seed, gains in ((1, (1.0, 3.0)), (2, (-1.0, -3.0))):
            for seat, gain in enumerate(gains):
                pairs.append({
                    "option_id": 1,
                    "seed": seed,
                    "seat": seat,
                    "opponent_id": "builtin:starter",
                    "valid": True,
                    "score_gain": gain,
                    "own_reward_gain": gain,
                    "opponent_reward_gain": gain,
                    "margin_gain": gain,
                    "catastrophe_delta": gain,
                })
        analysis = pair_eval.paired_analysis(pairs, samples=200, bootstrap_seed=5)
        self.assertEqual(analysis["seed_blocks"], 2)
        self.assertEqual(
            analysis["score_gain"]["seed_block_values"],
            {"1": 2.0, "2": -2.0},
        )
        self.assertEqual(
            analysis["bootstrap_unit"], "seed_block_preserving_both_seats"
        )

    def test_strict_pair_key_rejects_wrong_opponent_and_missing_candidate(self):
        baseline = _valid_row(1, 12, 0, 0.0)
        baseline.update({
            "candidate_id": "v6",
            "checkpoint_sha256": "a" * 64,
            "opponent_id": "builtin:starter",
        })
        candidate = _valid_row(1, 12, 0, 100.0)
        candidate.update({
            "candidate_id": "v8",
            "checkpoint_sha256": "b" * 64,
            "opponent_id": "builtin:random",
        })
        paired, errors = pair_eval.validate_pair_rows(
            [baseline, candidate],
            candidate_ids=("v6", "v8"),
            options=[1],
            schedule=[{"seed": 12, "opponent_id": "builtin:starter"}],
        )
        self.assertEqual(paired, [])
        self.assertTrue(any("unexpected pair key" in error for error in errors))
        self.assertTrue(any("missing v8 row" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
