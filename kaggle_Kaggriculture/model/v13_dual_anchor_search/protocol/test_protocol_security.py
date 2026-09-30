from __future__ import annotations

import copy
import math
from pathlib import Path
import tempfile
import unittest

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10
from kaggle_Kaggriculture.model.v13_dual_anchor_search.protocol.run_dual_anchor import (
    consume_lock,
    validate_row_against_task,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import load_registry


class StrictRowContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.task = {
            "task_id": "task",
            "run_fingerprint": "fingerprint",
            "pair_id": "candidate__vs__anchor",
            "model_a": "candidate",
            "model_b": "anchor",
            "model_a_seat": 1,
            "source": {
                "date": "2026-08-18",
                "seed": 123,
                "episode_id": "episode",
                "split": "train",
                "source_path": "2026-08-18/episode.json",
                "lineage_fold": "",
            },
            "registry": "/sealed/registry.json",
        }
        self.row = {
            "schema": v10.SCHEMA,
            "task_id": "task",
            "run_fingerprint": "fingerprint",
            "pair_id": "candidate__vs__anchor",
            "model_a": "candidate",
            "model_b": "anchor",
            "model_a_seat": 1,
            "source": copy.deepcopy(self.task["source"]),
            "engine": "kaggle_environments.make(kaggriculture)",
            "closed_loop": True,
            "trace_agent": False,
            "seat_models": ["anchor", "candidate"],
            "statuses": ["DONE", "DONE"],
            "rewards": [90.0, 100.0],
            "done": True,
            "reward_a": 100.0,
            "reward_b": 90.0,
            "margin_a": 10.0,
            "score_a": 1.0,
            "error": None,
        }

    def test_exact_row_passes(self) -> None:
        validate_row_against_task(copy.deepcopy(self.row), self.task)

    def test_foreign_or_inconsistent_rows_fail(self) -> None:
        mutations = [
            ("schema", "attacker-schema"),
            ("task_id", "foreign-task"),
            ("run_fingerprint", "foreign-fingerprint"),
            ("pair_id", "other__vs__anchor"),
            ("engine", "historical-replay"),
            ("closed_loop", False),
            ("trace_agent", True),
            ("seat_models", ["candidate", "anchor"]),
            ("statuses", ["DONE", "ERROR"]),
            ("done", False),
            ("reward_a", 90.0),
            ("reward_b", 100.0),
            ("margin_a", -10.0),
            ("score_a", 0.0),
            ("error", "forged"),
            ("rewards", [True, 100.0]),
            ("rewards", [math.inf, 100.0]),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                row = copy.deepcopy(self.row)
                row[field] = value
                with self.assertRaises(ValueError):
                    validate_row_against_task(row, self.task)

    def test_source_grain_is_exact(self) -> None:
        row = copy.deepcopy(self.row)
        row["source"]["seed"] = 124
        with self.assertRaises(ValueError):
            validate_row_against_task(row, self.task)

    def test_consume_lock_is_single_use_and_resume_path_bound(self) -> None:
        protocol = Path(
            "kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol"
        ).resolve()
        registry = load_registry(protocol / "clean_screen_registry.json")
        with tempfile.TemporaryDirectory(prefix="v13-lock-test-") as directory:
            root = Path(directory)
            manifest = root / "run_manifest.json"
            manifest.write_text('{"sealed":true}\n', encoding="utf-8")
            games = root / "games.jsonl"
            first = consume_lock(
                "confirmatory",
                "v13a_a2_no_wool_throttle",
                "fingerprint",
                games,
                manifest,
                registry,
                False,
                state_root=root / "state",
            )
            self.assertTrue(first.is_file())
            with self.assertRaises(FileExistsError):
                consume_lock(
                    "confirmatory",
                    "v13a_a2_no_wool_throttle",
                    "fingerprint",
                    games,
                    manifest,
                    registry,
                    False,
                    state_root=root / "state",
                )
            resumed = consume_lock(
                "confirmatory",
                "v13a_a2_no_wool_throttle",
                "fingerprint",
                games,
                manifest,
                registry,
                True,
                state_root=root / "state",
            )
            self.assertEqual(resumed, first)
            with self.assertRaises(FileExistsError):
                consume_lock(
                    "confirmatory",
                    "v13a_a2_no_wool_throttle",
                    "fingerprint",
                    root / "different-games.jsonl",
                    manifest,
                    registry,
                    True,
                    state_root=root / "state",
                )


if __name__ == "__main__":
    unittest.main()
