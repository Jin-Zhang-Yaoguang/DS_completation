from __future__ import annotations

import json
from pathlib import Path
import unittest

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import main as core


HERE = Path(__file__).resolve().parent


class Terminal716RejectionTest(unittest.TestCase):
    def test_helper_is_logically_capable_of_filling_a_missing_sale(self) -> None:
        obs = {
            "step": 716,
            "private": {"shed": {"WOOL": 4}},
            "market": {"prices": {"WOOL": 200}},
        }
        parent = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
        changed, orders, quantity = core._terminal_clearance_fill(parent, obs, 716)
        self.assertEqual(changed["market"], [["SELL", "WOOL", 4]])
        self.assertEqual((orders, quantity), (1, 4))

    def test_real_exposed_probe_is_inactive_and_not_packaged(self) -> None:
        report = json.loads(
            (HERE / "mechanism_probe_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["total_added_orders"], 0)
        self.assertEqual(report["total_added_quantity"], 0)
        self.assertFalse(report["operationally_distinct_from_a2"])
        self.assertEqual(
            report["decision"],
            "REJECT_BEFORE_PACKAGING_EQUIVALENT_ON_EXPOSED_QA",
        )
        self.assertFalse((HERE / "submission.tar.gz").exists())
        self.assertFalse((HERE / "registry_entry.json").exists())


if __name__ == "__main__":
    unittest.main()
