#!/usr/bin/env python3
"""No-engine mechanism tests for the R8 search skeleton."""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search


class SearchMechanismTests(unittest.TestCase):
    def test_low_discrepancy_is_deterministic_and_unique(self) -> None:
        space = {
            "x": {"type": "float", "low": 0.0, "high": 1.0},
            "n": {"type": "int", "low": 1, "high": 1000},
        }
        left = search.generate_configs(space, 128, 7)
        right = search.generate_configs(space, 128, 7)
        self.assertEqual(left, right)
        self.assertEqual(128, len({row["param_hash"] for row in left}))

    def test_protocol_stage_contract(self) -> None:
        self.assertEqual((8, 32), (search.STAGE_SPECS["R1"]["seeds"], search.STAGE_SPECS["R1"]["keep"]))
        self.assertEqual((24, 12), (search.STAGE_SPECS["R2"]["seeds"], search.STAGE_SPECS["R2"]["keep"]))
        self.assertEqual((2, 4, "gold_full"), (search.STAGE_SPECS["R3"]["seeds"], search.STAGE_SPECS["R3"]["keep"], search.STAGE_SPECS["R3"]["pool"]))
        self.assertEqual((8, 1, "gold_full"), (search.STAGE_SPECS["R4"]["seeds"], search.STAGE_SPECS["R4"]["keep"], search.STAGE_SPECS["R4"]["pool"]))
        panels, warnings = search.read_seed_manifest(search.DEFAULT_SEED_MANIFEST)
        self.assertEqual([], warnings)
        self.assertEqual(
            {"R1": 8, "R2": 24, "R3": 2, "R4": 8},
            {key: len(value) for key, value in panels.items()},
        )

    def test_error_stays_in_planned_denominator(self) -> None:
        task = {
            "task_id": "x", "cache_key": "k", "stage": "R1", "config_id": "p",
            "param_hash": "h", "executor_hash": "e", "evaluator_hash": "v",
            "mode": "router", "opponent": "idle",
            "opponent_hash": "o", "seed": 1, "candidate_seat": 0,
        }
        error = search.error_row(task, "synthetic")
        win = copy.deepcopy(error)
        win.update({
            "status": "DONE", "error": None, "calls": 719, "win": 1,
            "own_bank": 10.0, "opponent_bank": 0.0, "margin": 10.0,
            "observed_shop": "BAKERY",
        })
        result = search.aggregate([win, error])
        self.assertEqual(2, result["planned_games"])
        self.assertEqual(1, result["completed_games"])
        self.assertEqual(1, result["errors_as_nonwins"])
        self.assertEqual(0.5, result["pure_win_rate"])
        self.assertFalse(result["all_719_calls"])

    def test_cache_key_covers_required_identity(self) -> None:
        kwargs = dict(
            param_hash="p", executor_hash="e", evaluator_hash="v",
            opponent_hash="o", seed=11, seat=0, mode="router",
        )
        base = search.make_cache_key(**kwargs)
        for field, replacement in (
            ("param_hash", "p2"), ("executor_hash", "e2"),
            ("evaluator_hash", "v2"), ("opponent_hash", "o2"),
            ("seed", 12), ("seat", 1), ("mode", "fixed"),
        ):
            changed = dict(kwargs)
            changed[field] = replacement
            self.assertNotEqual(base, search.make_cache_key(**changed))

    def test_schema_validator(self) -> None:
        observation = {"player": 0, "farms": [{"hands": [{}, {}]}, {}]}
        good = {"farmer": ["PASS"], "hands": [["PASS"], ["PASS"]], "market": []}
        self.assertEqual([], search.validate_action(good, observation))
        bad = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 0]]}
        self.assertTrue(search.validate_action(bad, observation))


if __name__ == "__main__":
    unittest.main()
