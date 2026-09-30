"""Independent negative tests for the sealed V12 frozen_v5 protocol.

The suite builds only synthetic JSONL rows from the registered task manifest.
It never creates a Kaggriculture environment and never reads a formal result.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from kaggle_Kaggriculture.model.v10_replay_lolo_router import (
    pairwise_evaluate as v10,
)
from kaggle_Kaggriculture.model.v12_validation.audit_results import audit
from kaggle_Kaggriculture.model.v12_validation.protocol import (
    expected_tasks,
    preflight,
    read_config,
    run_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
)
from kaggle_Kaggriculture.model.v12_validation.targeted_evaluate import (
    require_formal_execution_flag,
)


HERE = Path(__file__).resolve().parents[1]
FROZEN = HERE / "frozen_v5"
CONFIG_PATH = FROZEN / "validation_config.json"


class FrozenV5AttackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = read_config(CONFIG_PATH)
        cls.fingerprint, cls.tasks, cls.panel = expected_tasks(cls.config)
        if len(cls.tasks) != 4_600:
            raise AssertionError("red-team fixture is not the sealed 4,600-task grid")
        cls.rows = [cls._synthetic_row(task) for task in cls.tasks]

    @classmethod
    def _synthetic_row(cls, task: dict) -> dict:
        seat = int(task["model_a_seat"])
        left, right = str(task["model_a"]), str(task["model_b"])
        return {
            "schema": v10.SCHEMA,
            "task_id": task["task_id"],
            "run_fingerprint": cls.fingerprint,
            "pair_id": task["pair_id"],
            "model_a": left,
            "model_b": right,
            "model_a_seat": seat,
            "source": task["source"],
            "engine": "kaggle_environments.make(kaggriculture)",
            "closed_loop": True,
            "trace_agent": False,
            "seat_models": [left, right] if seat == 0 else [right, left],
            "statuses": ["DONE", "DONE"],
            "rewards": [100.0, 100.0],
            "done": True,
            "reward_a": 100.0,
            "reward_b": 100.0,
            "margin_a": 0.0,
            "score_a": 0.5,
            "error": None,
        }

    @staticmethod
    def _fast_ci(values, *_args, **_kwargs):
        mean = float(np.mean(list(values)))
        return [mean, mean]

    def _audit_rows(self, rows: list[dict]) -> dict:
        with tempfile.TemporaryDirectory(prefix="v12-v5-redteam-") as directory:
            path = Path(directory) / "synthetic.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(
                        json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                        + "\n"
                    )
            with patch(
                "kaggle_Kaggriculture.model.v12_validation.audit_results._bootstrap_ci",
                side_effect=self._fast_ci,
            ):
                return audit(CONFIG_PATH, path)

    def _mutated_grid(self, mutate) -> list[dict]:
        first = copy.deepcopy(self.rows[0])
        mutate(first)
        return [first, *self.rows[1:]]

    def test_preflight_and_explicit_execution_lock(self) -> None:
        report = preflight(CONFIG_PATH)
        self.assertTrue(report["passed"])
        self.assertEqual(len(self.tasks), 4_600)
        self.assertEqual(len(self.panel), 100)
        with self.assertRaises(PermissionError):
            require_formal_execution_flag(False)
        require_formal_execution_flag(True)

    def test_exact_synthetic_grid_passes_but_ties_promote_nobody(self) -> None:
        report = self._audit_rows(self.rows)
        self.assertTrue(report["integrity_passed"])
        self.assertFalse(report["fixed_sequence"]["primary_qualified"])
        self.assertFalse(report["fixed_sequence"]["secondary_formally_tested"])
        self.assertFalse(report["fixed_sequence"]["secondary_qualified"])
        primary = next(
            row
            for row in report["candidate_parent_uplift"]
            if row["candidate"] == "v12_incumbent_r002"
        )
        self.assertTrue(primary["promotion_gates"]["direct_parent_score_point"])
        self.assertTrue(primary["promotion_gates"]["direct_parent_score_ci95_low"])
        self.assertFalse(
            primary["promotion_gates"]["common_opponent_uplift_point"]
        )
        self.assertFalse(
            primary["promotion_gates"]["common_opponent_uplift_ci95_low"]
        )
        self.assertTrue(primary["promotion_gates"]["worst_common_opponent_point"])
        secondary = next(
            row
            for row in report["candidate_parent_uplift"]
            if row["candidate"] == "v12a2_no_shop_gate"
        )
        self.assertEqual(secondary["fixed_sequence_status"], "exploratory_only")

    def test_run_fingerprint_binds_thresholds_and_fixed_sequence(self) -> None:
        registry = load_registry(self.config["combined_registry"])
        baseline = run_fingerprint(self.config, registry, self.panel)

        threshold_edit = copy.deepcopy(self.config)
        threshold_edit["quality_thresholds"][
            "common_opponent_uplift_ci95_low_min"
        ] = -1.0
        self.assertNotEqual(
            baseline, run_fingerprint(threshold_edit, registry, self.panel)
        )

        sequence_edit = copy.deepcopy(self.config)
        sequence_edit["fixed_sequence_gate"]["primary"] = "v12a2_no_shop_gate"
        self.assertNotEqual(
            baseline, run_fingerprint(sequence_edit, registry, self.panel)
        )

    def test_identity_and_terminal_semantic_forgeries_fail_closed(self) -> None:
        attacks = {
            "task_id": lambda row: row.__setitem__("task_id", "forged-task"),
            "run": lambda row: row.__setitem__("run_fingerprint", "0" * 64),
            "pair": lambda row: row.__setitem__("pair_id", "forged__vs__pair"),
            "source": lambda row: row["source"].__setitem__(
                "episode_id", "forged-episode"
            ),
            "source_numeric_type": lambda row: row["source"].__setitem__(
                "seed", float(row["source"]["seed"])
            ),
            "seat": lambda row: row.__setitem__(
                "model_a_seat", 1 - int(row["model_a_seat"])
            ),
            "boolean_seat": lambda row: row.__setitem__("model_a_seat", False),
            "seat_models": lambda row: row.__setitem__(
                "seat_models", list(reversed(row["seat_models"]))
            ),
            "status": lambda row: row.__setitem__("statuses", ["DONE", "ERROR"]),
            "closed_loop": lambda row: row.__setitem__("closed_loop", False),
            "engine": lambda row: row.__setitem__("engine", "forged-engine"),
        }
        for label, mutate in attacks.items():
            with self.subTest(attack=label):
                report = self._audit_rows(self._mutated_grid(mutate))
                self.assertFalse(report["integrity_passed"])
                self.assertFalse(report["checks"]["zero_row_errors"])

    def test_reward_margin_score_forgeries_fail_exactly(self) -> None:
        attacks = {
            # Tiny changes deliberately sit inside math.isclose's default
            # tolerance; an audit contract must still reject forged fields.
            "reward_a_tiny": lambda row: row.__setitem__(
                "reward_a", float(row["reward_a"]) + 1e-10
            ),
            "margin_tiny": lambda row: row.__setitem__("margin_a", 1e-10),
            "score_tiny": lambda row: row.__setitem__("score_a", 0.5 + 1e-10),
            "reward_payload": lambda row: row["rewards"].__setitem__(0, 101.0),
            "non_finite": lambda row: row["rewards"].__setitem__(0, float("nan")),
            "boolean_reward": lambda row: row["rewards"].__setitem__(0, True),
        }
        for label, mutate in attacks.items():
            with self.subTest(attack=label):
                report = self._audit_rows(self._mutated_grid(mutate))
                self.assertFalse(report["integrity_passed"])
                self.assertFalse(report["checks"]["zero_row_errors"])

    def test_duplicate_task_replacing_another_task_fails(self) -> None:
        rows = [copy.deepcopy(self.rows[0]), copy.deepcopy(self.rows[0]), *self.rows[2:]]
        report = self._audit_rows(rows)
        self.assertFalse(report["integrity_passed"])
        self.assertFalse(report["checks"]["task_id_exact_unique_set"])
        self.assertFalse(report["checks"]["task_grain_exact_unique_set"])

    def test_duplicate_json_key_is_rejected_before_effect_calculation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v12-v5-duplicate-key-") as directory:
            path = Path(directory) / "synthetic.jsonl"
            first = json.dumps(
                self.rows[0], ensure_ascii=False, separators=(",", ":")
            )
            first = first[:-1] + ',"score_a":0.0}'
            with path.open("w", encoding="utf-8") as handle:
                handle.write(first + "\n")
                for row in self.rows[1:]:
                    handle.write(
                        json.dumps(
                            row, ensure_ascii=False, separators=(",", ":")
                        )
                        + "\n"
                    )
            with self.assertRaisesRegex(ValueError, "duplicate JSON key: score_a"):
                audit(CONFIG_PATH, path)

    def test_executables_have_no_stale_v3_v4_or_old_candidate_dependency(self) -> None:
        forbidden = (
            "runs_v3",
            "runs_v4",
            "v12a_terminal_branch_guard",
            "v12b_market_feedback_router",
            "v12b_v2_winrisk_feedback_gate",
        )
        for name in (
            "protocol.py",
            "targeted_evaluate.py",
            "audit_results.py",
            "run_validation.sh",
        ):
            text = (HERE / name).read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, text, f"{name} still depends on {value}")


if __name__ == "__main__":
    unittest.main()
