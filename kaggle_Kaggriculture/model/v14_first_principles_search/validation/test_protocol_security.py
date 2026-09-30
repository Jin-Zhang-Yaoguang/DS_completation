from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import load_registry
from kaggle_Kaggriculture.model.v14_first_principles_search.validation.audit_dual_anchor import (
    unique_object,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.validation.build_panels import (
    validate_panels,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.validation.common import (
    HERE,
    load_json,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.validation.run_dual_anchor import (
    consume_lock,
    require_confirmatory_authorization,
    validate_row_against_task,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.validation.seal_candidates import (
    validate_package_dir,
)


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

    def test_every_semantic_boundary_fails_closed(self) -> None:
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

    def test_source_identity_is_exact(self) -> None:
        row = copy.deepcopy(self.row)
        row["source"]["seed"] = 124
        with self.assertRaises(ValueError):
            validate_row_against_task(row, self.task)

    def test_duplicate_json_key_rejected(self) -> None:
        with self.assertRaises(ValueError):
            json.loads('{"task_id":"a","task_id":"b"}', object_pairs_hook=unique_object)


class FrozenPanelContractTest(unittest.TestCase):
    def test_frozen_panels_are_disjoint_unexposed_and_test_free(self) -> None:
        inventory = load_json(HERE / "exposure_inventory.json")
        screen = load_json(HERE / "screen_panel.json")
        confirm = load_json(HERE / "confirmatory_panel.json")
        checks = validate_panels(inventory, screen, confirm)
        self.assertTrue(all(checks.values()), checks)
        self.assertEqual(screen["date_counts"], {"2026-08-18": 12, "2026-08-19": 12, "2026-08-20": 12})
        self.assertEqual(confirm["date_counts"], {"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33})

    def test_contract_keeps_pure_win_and_score_separate(self) -> None:
        contract = load_json(HERE / "evaluation_contract.json")
        gates = contract["hard_gates"]
        for phase in ("screen", "confirmatory"):
            self.assertEqual(gates[phase]["a2_pure_win_rate_min_inclusive"], 0.65)
            self.assertEqual(gates[phase]["r002_pure_win_rate_min_exclusive"], 0.5)
        self.assertIn("reported only", contract["metric_definitions"]["competition_score_rate"])


class ArtifactAndLockTest(unittest.TestCase):
    def test_missing_candidate_package_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v14-missing-package-") as directory:
            with self.assertRaises(FileNotFoundError):
                validate_package_dir("v14_missing", Path(directory))

    def test_confirmatory_requires_explicit_flag(self) -> None:
        require_confirmatory_authorization("screen", False)
        require_confirmatory_authorization("confirmatory", True)
        with self.assertRaises(PermissionError):
            require_confirmatory_authorization("confirmatory", False)

    def test_atomic_confirmatory_lock_is_globally_single_use(self) -> None:
        protocol = Path("kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol").resolve()
        registry = load_registry(protocol / "clean_screen_registry.json")
        with tempfile.TemporaryDirectory(prefix="v14-lock-test-") as directory:
            root = Path(directory)
            manifest = root / "run_manifest.json"
            manifest.write_text('{"sealed":true}\n', encoding="utf-8")
            fake_candidate_seal = root / "candidate_seal.json"
            fake_candidate_seal.write_text('{"sealed":true}\n', encoding="utf-8")
            games = root / "games.jsonl"
            with patch(
                "kaggle_Kaggriculture.model.v14_first_principles_search.validation.run_dual_anchor.CANDIDATE_SEAL",
                fake_candidate_seal,
            ):
                first = consume_lock(
                    "confirmatory",
                    "v14_candidate",
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
                        "v14_other_candidate",
                        "other-fingerprint",
                        root / "other.jsonl",
                        manifest,
                        registry,
                        False,
                        state_root=root / "state",
                    )
                resumed = consume_lock(
                    "confirmatory",
                    "v14_candidate",
                    "fingerprint",
                    games,
                    manifest,
                    registry,
                    True,
                    state_root=root / "state",
                )
                self.assertEqual(resumed, first)


if __name__ == "__main__":
    unittest.main()

