"""Fast infrastructure/red-team tests; no Kaggriculture game is started."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from kaggle_Kaggriculture.model.v12_validation.audit_results import audit
from kaggle_Kaggriculture.model.v12_validation.protocol import (
    expected_tasks,
    preflight,
    read_config,
    target_pairs,
)
from kaggle_Kaggriculture.model.v12_validation.build_validation_assets import (
    _assert_formal_exposure_disjoint,
)
from kaggle_Kaggriculture.model.v12_validation.targeted_evaluate import (
    require_formal_execution_flag,
)


HERE = Path(__file__).resolve().parent
FROZEN = HERE / "frozen_v5"


class ValidationInfrastructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = FROZEN / "validation_config.json"
        cls.config = read_config(cls.config_path)
        cls.panel = json.loads(
            (FROZEN / "formal_panel.json").read_text(encoding="utf-8")
        )

    def test_preflight_and_frozen_panel_contract(self) -> None:
        self.assertTrue(preflight(self.config_path)["passed"])
        records = self.panel["records"]
        self.assertEqual(len(records), 100)
        self.assertEqual(len({row["seed"] for row in records}), 100)
        self.assertEqual(
            {
                date: sum(row["date"] == date for row in records)
                for date in self.panel["dates"]
            },
            {"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33},
        )
        self.assertTrue(
            all(row["split"] in {"train", "validation"} for row in records)
        )
        self.assertEqual(len(target_pairs(self.config)), 23)
        self.assertEqual(self.config["formal_protocol"]["expected_games"], 4600)

    def test_new_exposure_collision_fails_closed_and_execution_needs_flag(self) -> None:
        formal_seed = int(self.panel["records"][0]["seed"])
        with self.assertRaisesRegex(ValueError, "refusing replacement selection"):
            _assert_formal_exposure_disjoint(self.panel["records"], {formal_seed})
        with self.assertRaises(PermissionError):
            require_formal_execution_flag(False)
        self.assertIsNone(require_formal_execution_flag(True))

    def _synthetic_grid(self, path: Path) -> None:
        fingerprint, tasks, _ = expected_tasks(self.config)
        self.assertEqual(len(tasks), 4600)
        with path.open("w", encoding="utf-8") as handle:
            for task in tasks:
                seat = int(task["model_a_seat"])
                pair = [task["model_a"], task["model_b"]]
                row = {
                    "schema": "kaggriculture-v10-pairwise-closed-loop-1",
                    "task_id": task["task_id"],
                    "run_fingerprint": fingerprint,
                    "pair_id": task["pair_id"],
                    "model_a": task["model_a"],
                    "model_b": task["model_b"],
                    "model_a_seat": seat,
                    "source": task["source"],
                    "engine": "kaggle_environments.make(kaggriculture)",
                    "closed_loop": True,
                    "trace_agent": False,
                    "seat_models": pair if seat == 0 else list(reversed(pair)),
                    "statuses": ["DONE", "DONE"],
                    "rewards": [100.0, 100.0],
                    "done": True,
                    "reward_a": 100.0,
                    "reward_b": 100.0,
                    "margin_a": 0.0,
                    "score_a": 0.5,
                    "error": None,
                }
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")

    @staticmethod
    def _fast_ci(values, *_args, **_kwargs):
        mean = float(np.mean(list(values)))
        return [mean, mean]

    def test_auditor_accepts_exact_manifest_and_rejects_duplicate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v12-validation-test-") as directory:
            path = Path(directory) / "games.jsonl"
            self._synthetic_grid(path)
            with patch(
                "kaggle_Kaggriculture.model.v12_validation.audit_results._bootstrap_ci",
                side_effect=self._fast_ci,
            ):
                report = audit(self.config_path, path)
            self.assertTrue(report["integrity_passed"])
            self.assertEqual(report["observed"]["physical_rows"], 4600)
            first = path.read_text(encoding="utf-8").splitlines()[0]
            with path.open("a", encoding="utf-8") as handle:
                handle.write(first + "\n")
            duplicate_report = audit(self.config_path, path)
            self.assertFalse(duplicate_report["integrity_passed"])
            self.assertFalse(
                duplicate_report["checks"]["task_id_exact_unique_set"]
            )

    def test_forged_fingerprint_and_orientation_swap_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v12-validation-redteam-") as directory:
            original = Path(directory) / "original.jsonl"
            self._synthetic_grid(original)
            rows = original.read_text(encoding="utf-8").splitlines()

            forged = json.loads(rows[0])
            forged["run_fingerprint"] = "synthetic-forgery"
            forged_path = Path(directory) / "forged.jsonl"
            forged_path.write_text(
                "\n".join([json.dumps(forged, separators=(",", ":")), *rows[1:]])
                + "\n",
                encoding="utf-8",
            )
            self.assertFalse(audit(self.config_path, forged_path)["integrity_passed"])

            swapped = json.loads(rows[1])
            swapped["model_a"], swapped["model_b"] = (
                swapped["model_b"],
                swapped["model_a"],
            )
            swapped_path = Path(directory) / "swapped.jsonl"
            swapped_path.write_text(
                "\n".join([rows[0], json.dumps(swapped, separators=(",", ":")), *rows[2:]])
                + "\n",
                encoding="utf-8",
            )
            self.assertFalse(audit(self.config_path, swapped_path)["integrity_passed"])


if __name__ == "__main__":
    unittest.main()
