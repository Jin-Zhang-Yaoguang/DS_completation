"""Only synthetic records and temporary files. No model or actual prediction access."""
import copy
import tempfile
import unittest
from pathlib import Path
import readiness_gate as gate


def report(delta=0.00001):
    row = {"baseline_auc": 0.9, "candidate_auc": 0.9 + delta, "delta": delta}
    return {**row, "folds": [{**row, "fold": k} for k in range(1, 6)], "positive_folds": 5}


def record():
    return {"status": "COMPLETE_LEGACY_COMPARISON_CONFIRMATION_ONLY", "candidate": "D",
            "baseline": "C", "primary_comparison": "D_MINUS_C", "selection_revision": "R01",
            "selected_candidate": "D", "requires_successful_score_stage_result": True,
            "candidate_rebuild_eligible": True, "B_minus_A_prerequisite_gate_passed": True,
            "D_minus_C_gate_passed": True, "allowed_for_submission": False,
            "actual_test_predictions_generated": False, "is_new_blind_test": False,
            "A_can_replace_D": False, "B_can_replace_D": False,
            "B_minus_A_recomputed": report(), "D_minus_C": report(),
            "D_minus_C_research_gate_passed": False, "research_promotion_gate_passed": False}


class ReadinessTests(unittest.TestCase):
    def test_small_positive_is_eligible_but_not_research_promotion(self):
        result = gate.qualification(record())
        self.assertTrue(result["eligible_to_define_actual_contract"])
        self.assertFalse(result["research_promotion_gate_passed"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["allowed_for_submission"])

    def test_research_classification_does_not_change_scope(self):
        x = record(); x["D_minus_C"] = report(0.0001)
        x["D_minus_C_research_gate_passed"] = x["research_promotion_gate_passed"] = True
        self.assertTrue(gate.qualification(x)["research_promotion_gate_passed"])

    def test_flags_cannot_replace_fold_evidence(self):
        x = record(); x["D_minus_C"]["folds"] = x["D_minus_C"]["folds"][:4]
        with self.assertRaisesRegex(ValueError, "five ordered"):
            gate.qualification(x)

    def test_mixed_fold_direction_rejected(self):
        x = record(); r = x["D_minus_C"]; r["folds"][2].update(candidate_auc=0.89, delta=-0.01)
        r["positive_folds"] = 4
        with self.assertRaisesRegex(ValueError, "D-C primary"):
            gate.qualification(x)

    def test_zero_or_negative_prerequisite_rejected(self):
        for delta in (0, -0.00001):
            with self.subTest(delta=delta):
                x = record(); x["B_minus_A_recomputed"] = report(delta)
                x["B_minus_A_recomputed"]["positive_folds"] = 0
                with self.assertRaisesRegex(ValueError, "B-A prerequisite"):
                    gate.qualification(x)

    def test_wrong_candidate_cannot_replace_d(self):
        for key in ("candidate", "selected_candidate"):
            x = record(); x[key] = "B"
            with self.assertRaises(ValueError):
                gate.qualification(x)

    def test_submission_or_test_flags_rejected(self):
        for key in ("allowed_for_submission", "actual_test_predictions_generated", "is_new_blind_test"):
            x = record(); x[key] = True
            with self.assertRaises(ValueError):
                gate.qualification(x)

    def test_inconsistent_numeric_evidence_rejected(self):
        for value in (float("nan"), float("inf"), True, "0.01"):
            x = record(); x["D_minus_C"]["delta"] = value
            with self.assertRaises(ValueError):
                gate.qualification(x)
        x = record(); x["D_minus_C"]["delta"] = 0.02
        with self.assertRaisesRegex(ValueError, "delta mismatch"):
            gate.qualification(x)

    def test_misreported_research_flag_rejected(self):
        x = record(); x["research_promotion_gate_passed"] = True
        with self.assertRaisesRegex(ValueError, "research flag"):
            gate.qualification(x)

    def test_frozen_source_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); f = root / "source.py"; f.write_text("# synthetic\n")
            expected = {"source.py": gate.digest(f)}
            self.assertEqual(gate.source_snapshot(root, expected), expected)
            f.write_text("# changed\n")
            with self.assertRaisesRegex(ValueError, "source drift"):
                gate.source_snapshot(root, expected)

    def test_missing_and_symlink_sources_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                gate.digest(root / "missing")
            f = root / "real"; f.write_text("synthetic")
            link = root / "link"; link.symlink_to(f)
            with self.assertRaises(ValueError):
                gate.digest(link)


if __name__ == "__main__":
    unittest.main(verbosity=2)
