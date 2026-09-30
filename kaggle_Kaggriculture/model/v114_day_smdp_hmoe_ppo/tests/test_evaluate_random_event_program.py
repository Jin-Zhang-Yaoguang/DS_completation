from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluate_random_event_program as evaluation  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


def _row(seed, seat, *, margin):
    reward = 5000.0 + margin
    opponent = 5000.0
    return {
        "seed": seed,
        "seat": seat,
        "opponent_id": "builtin:starter",
        "reward": reward,
        "opponent": opponent,
        "opponent_reward": opponent,
        "margin": margin,
        "score": evaluation.game_score(margin),
        "catastrophe": reward < evaluation.CATASTROPHE_REWARD,
        "error": None,
        "status": "DONE",
        "opponent_status": "DONE",
        "statuses": ["DONE", "DONE"],
        "steps": 719,
        "decision_count": 30,
        "head_usage": {
            "production_line": {"WHEAT": 20, "CARROT": 10},
            "worker_cap": {"4": 30},
            "cash_reserve": {"500": 30},
            "sell_style": {"IMMEDIATE": 30},
            "terminal_mode": {"NORMAL": 28, "LIQUIDATE": 2},
        },
        "contract_violations": 0,
        "terminal_procurement": 0,
        "environment_states": 720,
    }


def mock_worker(checkpoint, seed, opponent_id):
    del checkpoint, opponent_id
    return [
        _row(seed, 0, margin=100.0),
        _row(seed, 1, margin=-100.0),
    ]


class TrackingLedger(SeedLedger):
    reserve_calls = 0
    expose_calls = 0

    def reserve_schedule(self, *args, **kwargs):
        type(self).reserve_calls += 1
        return super().reserve_schedule(*args, **kwargs)

    def mark_schedule_exposed(self, *args, **kwargs):
        type(self).expose_calls += 1
        return super().mark_schedule_exposed(*args, **kwargs)


class EvaluateRandomEventProgramTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.checkpoint = self.root / "random_event_program.ckpt"
        self.checkpoint.write_bytes(b"mock-checkpoint")
        TrackingLedger.reserve_calls = 0
        TrackingLedger.expose_calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def args(self, **overrides):
        values = {
            "checkpoint": self.checkpoint,
            "seed_start": 9100,
            "seeds": 2,
            "opponent": "builtin:starter",
            "campaign": "random-event-program-mock",
            "split": "train",
            "registry_sha256": "b" * 64,
            "ledger": self.root / "ledger.json",
            "output": self.root / "report.json",
            "workers": 2,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_one_reserve_one_expose_and_dual_seat_rows(self):
        args = self.args()
        report = evaluation.run_campaign(
            args,
            worker_fn=mock_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )

        self.assertEqual(report["status"], "VALID")
        self.assertEqual(TrackingLedger.reserve_calls, 1)
        self.assertEqual(TrackingLedger.expose_calls, 1)
        self.assertEqual(len(report["rows"]), 4)
        self.assertEqual({row["seat"] for row in report["rows"]}, {0, 1})
        self.assertEqual({row["seed"] for row in report["rows"]}, {9100, 9101})
        snapshot = SeedLedger(args.ledger).snapshot()
        self.assertEqual(snapshot["indexes"]["exposed"], [9100, 9101])
        self.assertEqual(json.loads(args.output.read_text())["status"], "VALID")

    def test_report_has_checkpoint_source_shas_and_head_coverage(self):
        args = self.args(seeds=1)
        report = evaluation.run_campaign(
            args,
            worker_fn=mock_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )

        expected_sha = hashlib.sha256(b"mock-checkpoint").hexdigest()
        self.assertEqual(report["checkpoint"]["sha256_before"], expected_sha)
        self.assertEqual(report["checkpoint"]["sha256_after"], expected_sha)
        self.assertTrue(report["checkpoint"]["unchanged"])
        self.assertTrue(report["event_program"]["unchanged"])
        summary = report["summary"]
        self.assertEqual(summary["wdl"], {"wins": 1, "draws": 0, "losses": 1})
        self.assertAlmostEqual(summary["score_rate"], 0.5)
        self.assertEqual(summary["mean_reward"], 5000.0)
        self.assertEqual(summary["p10_reward"], 4900.0)
        self.assertEqual(summary["mean_margin"], 0.0)
        self.assertEqual(summary["catastrophe_games"], 0)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(
            summary["head_coverage"]["production_line"]["used_choices"], 2
        )
        self.assertAlmostEqual(
            summary["head_coverage"]["production_line"]["coverage_rate"], 0.4
        )
        self.assertEqual(
            summary["head_coverage"]["terminal_mode"]["coverage_rate"], 1.0
        )

    def test_worker_exception_is_recorded_and_reserved_seed_is_exposed(self):
        def broken_worker(*_args):
            raise RuntimeError("mock crash")

        args = self.args(seeds=1)
        report = evaluation.run_campaign(
            args,
            worker_fn=broken_worker,
            executor_cls=ThreadPoolExecutor,
            ledger_cls=TrackingLedger,
        )

        self.assertEqual(report["status"], "INVALID")
        self.assertEqual(len(report["worker_failures"]), 1)
        self.assertEqual(len(report["rows"]), 2)
        self.assertTrue(all("mock crash" in row["error"] for row in report["rows"]))
        self.assertEqual(
            SeedLedger(args.ledger).snapshot()["indexes"]["exposed"], [9100]
        )
        self.assertTrue(args.output.is_file())

    def test_summary_excludes_contract_invalid_games(self):
        rows = [_row(1, 0, margin=100.0), _row(1, 1, margin=-100.0)]
        rows[1]["contract_violations"] = 2
        rows[1]["terminal_procurement"] = 1
        summary = evaluation.summarize(rows)

        self.assertEqual(summary["valid_games"], 1)
        self.assertEqual(summary["wdl"], {"wins": 1, "draws": 0, "losses": 0})
        self.assertEqual(summary["contract_violations"], 2)
        self.assertEqual(summary["terminal_procurement"], 1)
        self.assertEqual(summary["incomplete_games"], 1)


if __name__ == "__main__":
    unittest.main()
