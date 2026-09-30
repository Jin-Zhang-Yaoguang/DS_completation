from __future__ import annotations

import unittest
from unittest import mock
from pathlib import Path

from kaggle_Kaggriculture.model.v13c_a2_v8_no_wool_throttle import main


class V13CV8NoWoolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = object.__new__(main.A2V8NoWoolThrottleAgent)
        self.agent.v8_wool_throttle_opportunities = 0
        self.action = {"market": [["SELL", "WOOL", 8], ["SELL", "MILK", 10]]}
        self.a2_decision = (
            True,
            "a2_approved",
            frozenset({"EGG", "MILK", "WOOL"}),
        )

    def test_v8_removes_only_wool(self) -> None:
        with mock.patch.object(
            main.a2.NoShopGateAgent, "_should_throttle", return_value=self.a2_decision
        ):
            actual = self.agent._should_throttle({}, self.action, "baseline_v8")
        self.assertEqual(actual, (True, "a2_approved", frozenset({"EGG", "MILK"})))
        self.assertEqual(self.agent.v8_wool_throttle_opportunities, 1)

    def test_v5_is_byte_semantically_a2(self) -> None:
        with mock.patch.object(
            main.a2.NoShopGateAgent, "_should_throttle", return_value=self.a2_decision
        ):
            actual = self.agent._should_throttle({}, self.action, "baseline_v5")
        self.assertEqual(actual, self.a2_decision)
        self.assertEqual(self.agent.v8_wool_throttle_opportunities, 0)

    def test_bad_v13_input_falls_back_to_a2_decision(self) -> None:
        with mock.patch.object(
            main.a2.NoShopGateAgent, "_should_throttle", return_value=self.a2_decision
        ):
            actual = self.agent._should_throttle({}, {"market": [object()]}, "baseline_v8")
        self.assertEqual(actual, self.a2_decision)

    def test_true_parent_and_serving_contract(self) -> None:
        self.assertTrue(issubclass(main.A2V8NoWoolThrottleAgent, main.a2.NoShopGateAgent))
        text = Path(main.__file__).read_text(encoding="utf-8")
        self.assertNotIn("__file__", text)
        self.assertGreater(text.rfind("def agent("), text.rfind("def model_status("))


if __name__ == "__main__":
    unittest.main()
