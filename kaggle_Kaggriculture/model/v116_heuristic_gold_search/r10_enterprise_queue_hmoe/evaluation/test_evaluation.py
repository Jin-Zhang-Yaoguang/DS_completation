#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r10_evaluate_test", HERE / "evaluate.py")
assert SPEC and SPEC.loader
evaluate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate)


class EvaluationTest(unittest.TestCase):
    def test_exact_panel_sizes_and_pairing(self) -> None:
        candidate = HERE.parent / "model/main.py"
        p2 = evaluate.build_tasks("p2", candidate)
        p3 = evaluate.build_tasks("p3", candidate)
        self.assertEqual(48, len(p2))
        self.assertEqual(288, len(p3))
        self.assertEqual({0, 1}, {row["candidate_seat"] for row in p3})
        self.assertEqual(set(evaluate.MODES), {row["mode"] for row in p3})
        self.assertEqual(set(evaluate.GOLD_POOL), {row["opponent"] for row in p3})

    def test_action_validator(self) -> None:
        observation = {"player": 0, "farms": [{"hands": [[1, 1]]}, {"hands": []}]}
        valid = {"farmer": ["PASS"], "hands": [["PLANT", "WHEAT"]], "market": [["BUY_SEED", "WHEAT", 2]]}
        self.assertEqual([], evaluate.validate_action(valid, observation))
        invalid = {"farmer": ["PASS", 1], "hands": [], "market": [["SELL", "WHEAT", 0]]}
        self.assertGreaterEqual(len(evaluate.validate_action(invalid, observation)), 3)

    def test_errors_are_nonwins_and_p2_gate(self) -> None:
        rows = []
        for mode in evaluate.MODES:
            for seed in evaluate.P2_SEEDS:
                for seat in (0, 1):
                    rows.append({
                        "status": "DONE", "calls": 719, "mode": mode, "opponent": "idle",
                        "seed": seed, "candidate_seat": seat, "win": 1, "tie": 0, "loss": 0,
                        "own_bank": 120_000.0, "opponent_bank": 3_000.0, "margin": 117_000.0,
                        "candidate_schema_violations": 0, "opponent_schema_violations": 0,
                        "terminal": {"production_assets": 60},
                    })
        summary = evaluate.summarize(rows, "p2")
        self.assertTrue(evaluate.decide(summary)["passed"])
        rows[0] = evaluate.error_row({
            "task_id": "x", "panel": "p2", "mode": "router", "opponent": "idle",
            "seed": 7100, "candidate_seat": 0,
        }, "synthetic")
        failed = evaluate.summarize(rows, "p2")
        self.assertFalse(evaluate.decide(failed)["passed"])
        self.assertEqual(1, failed["overall"]["errors_as_nonwins"])

    def test_refuses_overwrite_before_games(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            existing = Path(raw) / "existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                evaluate.run("p2", HERE.parent / "model/main.py", existing, 1)


if __name__ == "__main__":
    unittest.main()
