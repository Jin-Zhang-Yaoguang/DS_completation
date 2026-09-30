from __future__ import annotations

import unittest
from unittest import mock
from pathlib import Path

from kaggle_Kaggriculture.model.v13a_a2_no_wool_throttle import main


class V13ANoWoolTest(unittest.TestCase):
    def test_true_parent_is_a2_no_shop_gate(self) -> None:
        self.assertTrue(issubclass(main.A2NoWoolThrottleAgent, main.a2.NoShopGateAgent))

    def test_removes_only_wool_from_a2_decision(self) -> None:
        agent = object.__new__(main.A2NoWoolThrottleAgent)
        agent.wool_throttle_opportunities = 0
        action = {"market": [["SELL", "WOOL", 8], ["SELL", "MILK", 10]]}
        with mock.patch.object(
            main.a2.NoShopGateAgent,
            "_should_throttle",
            return_value=(True, "a2_approved", frozenset({"EGG", "MILK", "WOOL"})),
        ):
            actual = agent._should_throttle({}, action, "baseline_v8")
        self.assertEqual(actual, (True, "a2_approved", frozenset({"EGG", "MILK"})))
        self.assertEqual(agent.wool_throttle_opportunities, 1)

    def test_v13_failure_returns_a2_decision(self) -> None:
        agent = object.__new__(main.A2NoWoolThrottleAgent)
        agent.wool_throttle_opportunities = 0
        expected = (True, "a2_approved", frozenset({"WOOL"}))
        with mock.patch.object(main.a2.NoShopGateAgent, "_should_throttle", return_value=expected):
            actual = agent._should_throttle({"bad": object()}, {"market": [object()]}, "baseline_v8")
        self.assertEqual(actual, expected)

    def test_serving_main_has_no_file_assumption_and_agent_is_last_callable(self) -> None:
        text = Path(main.__file__).read_text(encoding="utf-8")
        self.assertNotIn("__file__", text)
        self.assertGreater(text.rfind("def agent("), text.rfind("def model_status("))


if __name__ == "__main__":
    unittest.main()
