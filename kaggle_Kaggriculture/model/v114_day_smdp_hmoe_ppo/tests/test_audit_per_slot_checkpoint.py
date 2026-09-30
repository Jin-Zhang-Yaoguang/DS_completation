"""Tests for the read-only V114 per-slot checkpoint audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from flax import serialization
import numpy as np

import audit_per_slot_checkpoint as audit


def _minimal_data() -> dict[str, np.ndarray]:
    rows = 3
    unit_tokens = np.zeros((rows, 16), dtype=np.int16)
    unit_tokens[:, 1] = np.array([6, 7, 6])  # WATER, HARVEST, WATER
    market_tokens = np.zeros((rows, 10), dtype=np.int16)
    market_tokens[:, 1] = np.array([1, 13, 1])  # HIRE, SELL:WHEAT, HIRE
    return {
        "global": np.zeros((rows, 32), dtype=np.float32),
        "board": np.zeros((rows, 2, 10, 10, 16), dtype=np.float32),
        "units": np.zeros((rows, 16, 12), dtype=np.float32),
        "unit_mask": np.ones((rows, 16), dtype=np.float32),
        "market_mask": np.ones((rows, 10), dtype=np.float32),
        "teacher_family": np.asarray([
            "demand-timing-preemption",
            "procurement-slot-ordering",
            "production-route-router",
        ]),
        "option_id": np.asarray([0, 1, 2], dtype=np.int8),
        "unit_tokens": unit_tokens,
        "unit_quantities": np.zeros((rows, 16), dtype=np.int16),
        "unit_roles": np.where(unit_tokens == 0, 0, 1).astype(np.int8),
        "market_tokens": market_tokens,
        "market_quantities": np.zeros((rows, 10), dtype=np.int16),
        "market_roles": np.where(market_tokens == 0, 0, 1).astype(np.int8),
    }


class ClassificationMetricsTest(unittest.TestCase):
    def test_macro_recall_is_class_balanced_and_critical_is_explicit(self) -> None:
        metrics = audit.classification_metrics(
            np.asarray([0, 0, 0, 1, 2]),
            np.asarray([0, 0, 0, 0, 2]),
            ("PASS", "WATER", "HARVEST"),
            ("WATER", "HARVEST"),
        )
        self.assertEqual(metrics["top1_accuracy"], 0.8)
        self.assertAlmostEqual(metrics["macro_recall"], 2 / 3)
        self.assertEqual(
            metrics["critical_action_recall"]["per_action"]["WATER"]["recall"],
            0.0,
        )
        self.assertEqual(
            metrics["critical_action_recall"]["per_action"]["HARVEST"]["recall"],
            1.0,
        )

    def test_empty_segment_uses_null_not_nan(self) -> None:
        metrics = audit.classification_metrics(
            np.asarray([], dtype=np.int64),
            np.asarray([], dtype=np.int64),
            ("PASS", "WATER"),
            ("WATER",),
        )
        self.assertIsNone(metrics["top1_accuracy"])
        self.assertIsNone(metrics["macro_recall"])
        self.assertIsNone(metrics["critical_action_recall"]["macro_recall"])


class AuditCheckpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.dataset = root / "per_slot.npz"
        self.checkpoint = root / "checkpoint.msgpack"
        np.savez_compressed(self.dataset, **_minimal_data())
        dataset_sha = hashlib.sha256(self.dataset.read_bytes()).hexdigest()
        self.checkpoint.write_bytes(serialization.msgpack_serialize({
            "model_id": "v114_test_per_slot",
            "inherits_v113_checkpoint": False,
            "dataset_sha256": dataset_sha,
            "params": {},
        }))

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _predict(data, checkpoint, batch_size):
        del checkpoint, batch_size
        unit = np.asarray(data["unit_tokens"]).copy()
        market = np.asarray(data["market_tokens"]).copy()
        unit[0, 1] = 0  # miss one WATER while preserving many PASS labels
        market[1, 1] = 0  # miss SELL:WHEAT
        return {
            "unit_tokens": unit,
            "unit_roles": np.asarray(data["unit_roles"]).copy(),
            "market_tokens": market,
            "market_roles": np.asarray(data["market_roles"]).copy(),
        }

    def test_report_is_segmented_and_never_claims_closed_loop(self) -> None:
        report = audit.audit_checkpoint(
            self.dataset, self.checkpoint, batch_size=2, predictor=self._predict
        )
        self.assertEqual(report["epistemic_status"], "TEACHER_FORCED_DIAGNOSTIC_ONLY")
        self.assertFalse(report["closed_loop_qualification"])
        self.assertFalse(report["overall_accuracy_is_closed_loop_gate"])
        self.assertTrue(report["checkpoint_dataset_sha256_matches"])
        self.assertEqual(report["option_family_mismatches"], 0)
        self.assertEqual(len(report["by_option_family"]), 3)
        self.assertIn("by_teacher_role", report["overall"]["unit"])
        self.assertIn("by_teacher_action_type", report["overall"]["market"])
        self.assertIn("idle_vs_nontrivial", report["overall"]["unit"])
        water = report["overall"]["unit"]["action"]["critical_action_recall"][
            "per_action"
        ]["WATER"]
        self.assertEqual(water["support"], 2)
        self.assertEqual(water["recall"], 0.5)
        self.assertEqual(report["data_access"]["opponent_splits_accessed"], [])
        self.assertFalse(report["data_access"]["gold_dev_accessed"])
        self.assertFalse(report["data_access"]["gold_blind_accessed"])

    def test_dataset_contract_is_fail_closed(self) -> None:
        broken = Path(self.temp.name) / "broken.npz"
        values = _minimal_data()
        del values["market_roles"]
        np.savez_compressed(broken, **values)
        with self.assertRaisesRegex(ValueError, "market_roles"):
            audit.audit_checkpoint(broken, self.checkpoint, predictor=self._predict)

    def test_prediction_row_count_is_fail_closed(self) -> None:
        def short_prediction(data, checkpoint, batch_size):
            result = self._predict(data, checkpoint, batch_size)
            result["unit_tokens"] = result["unit_tokens"][:-1]
            return result

        with self.assertRaisesRegex(ValueError, "unit_tokens"):
            audit.audit_checkpoint(
                self.dataset, self.checkpoint, predictor=short_prediction
            )


if __name__ == "__main__":
    unittest.main()
