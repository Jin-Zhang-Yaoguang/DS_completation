from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluate_event_program as evaluation  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


def _row(spec, seed, seat, *, margin):
    own = 5000.0 + margin
    opponent = 5000.0
    return {
        "decision_name": spec["name"],
        "decision": dict(spec["decision"]),
        "seed": seed,
        "seat": seat,
        "opponent_id": "builtin:starter",
        "candidate_reward": own,
        "opponent_reward": opponent,
        "margin": margin,
        "score": evaluation.score(margin),
        "catastrophe": own < evaluation.CATASTROPHE_REWARD,
        "error": None,
        "statuses": ["DONE", "DONE"],
        "action_steps": 719,
        "expected_action_steps": 719,
        "environment_states": 720,
        "contract_violations": 0,
        "manager_decision_count": 30,
        "terminal_procurement_count": 0,
    }


def mock_worker(spec, seed, opponent_id):
    del opponent_id
    return [
        _row(spec, seed, 0, margin=100.0),
        _row(spec, seed, 1, margin=-100.0),
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


class EvaluateEventProgramTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        TrackingLedger.reserve_calls = 0
        TrackingLedger.expose_calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def args(self, **overrides):
        values = {
            "decision_spec_json": None,
            "decision_specs": [
                {
                    "name": "wheat_fixed",
                    "decision": {
                        "production_line": "WHEAT",
                        "worker_cap": 4,
                        "cash_reserve": 500,
                        "sell_style": "IMMEDIATE",
                        "terminal_mode": "NORMAL",
                    },
                },
                {
                    "name": "carrot_fixed",
                    "decision": {
                        "production_line": "CARROT",
                        "worker_cap": 4,
                        "cash_reserve": 500,
                        "sell_style": "IMMEDIATE",
                        "terminal_mode": "NORMAL",
                    },
                },
            ],
            "seed_start": 8800,
            "seeds": 2,
            "opponent": "builtin:starter",
            "campaign": "event-program-mock",
            "split": "train",
            "registry_sha256": "a" * 64,
            "ledger": self.root / "ledger.json",
            "output": self.root / "report.json",
            "workers": 2,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_reserves_once_and_runs_dual_seat_for_all_decisions(self):
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
        self.assertEqual(len(report["rows"]), 8)
        for name in ("wheat_fixed", "carrot_fixed"):
            rows = [row for row in report["rows"] if row["decision_name"] == name]
            self.assertEqual({row["seat"] for row in rows}, {0, 1})
            self.assertEqual({row["seed"] for row in rows}, {8800, 8801})
        snapshot = SeedLedger(args.ledger).snapshot()
        self.assertEqual(snapshot["indexes"]["exposed"], [8800, 8801])
        self.assertEqual(len(snapshot["records"]), 2)
        self.assertTrue(args.output.is_file())
        self.assertEqual(json.loads(args.output.read_text())["status"], "VALID")

    def test_worker_exception_is_recorded_and_seeds_are_exposed(self):
        def broken_worker(*_args):
            raise RuntimeError("mock crash")

        args = self.args(decision_specs=self.args().decision_specs[:1], seeds=1)
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
            SeedLedger(args.ledger).snapshot()["indexes"]["exposed"], [8800]
        )
        self.assertTrue(args.output.is_file())

    def test_summary_reports_wdl_score_rewards_p10_and_contract(self):
        spec = self.args().decision_specs[0]
        rows = [
            _row(spec, 1, 0, margin=200.0),
            _row(spec, 1, 1, margin=0.0),
            _row(spec, 2, 0, margin=-200.0),
        ]
        rows[2]["candidate_reward"] = 2500.0
        rows[2]["catastrophe"] = True
        summary = evaluation.summarize_decision(rows, "wheat_fixed")

        self.assertEqual(summary["wdl"], {"wins": 1, "draws": 1, "losses": 1})
        self.assertAlmostEqual(summary["score_rate"], 0.5)
        self.assertEqual(summary["p10_candidate_reward"], 2500.0)
        self.assertEqual(summary["catastrophe_games"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["contract_violations"], 0)

    def test_builtin_specs_are_five_crops_with_fixed_contract(self):
        specs = evaluation.parse_decision_specs(None)
        self.assertEqual(len(specs), 5)
        self.assertEqual(
            {spec["decision"]["production_line"] for spec in specs},
            {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"},
        )
        self.assertTrue(all(spec["decision"]["worker_cap"] == 4 for spec in specs))
        self.assertTrue(all(spec["decision"]["cash_reserve"] == 500 for spec in specs))
        self.assertTrue(
            all(spec["decision"]["sell_style"] == "IMMEDIATE" for spec in specs)
        )


if __name__ == "__main__":
    unittest.main()
