from __future__ import annotations

import unittest
from unittest import mock
from pathlib import Path

from kaggle_Kaggriculture.model.v13d_a2_public_winrisk_gate import main


class V13DPublicWinRiskTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = object.__new__(main.A2PublicWinRiskAgent)
        self.agent.lead_bypass_steps = 0
        self.agent.unknown_public_bank_steps = 0
        self.agent.a2_throttle_eligible_steps = 0
        self.a2_decision = (
            True,
            "a2_approved",
            frozenset({"EGG", "MILK", "WOOL"}),
        )
        self.action = {"market": [["SELL", "MILK", 10]]}

    def decide(self, obs):
        with mock.patch.object(
            main.a2.NoShopGateAgent, "_should_throttle", return_value=self.a2_decision
        ):
            return self.agent._should_throttle(obs, self.action, "baseline_v8")

    def test_seat_zero_strict_lead_bypasses(self) -> None:
        obs = {"player": 0, "farms": [{"money": 101}, {"money": 100}]}
        self.assertEqual(
            self.decide(obs),
            (False, "v13d_strict_public_lead_bypass", frozenset()),
        )

    def test_seat_one_is_not_reversed(self) -> None:
        obs = {"player": 1, "farms": [{"money": 100}, {"money": 101}]}
        self.assertEqual(
            self.decide(obs),
            (False, "v13d_strict_public_lead_bypass", frozenset()),
        )

    def test_tie_and_behind_keep_a2(self) -> None:
        for obs in (
            {"player": 0, "farms": [{"money": 100}, {"money": 100}]},
            {"player": 0, "farms": [{"money": 99}, {"money": 100}]},
        ):
            with self.subTest(obs=obs):
                self.assertEqual(self.decide(obs), self.a2_decision)

    def test_missing_or_invalid_fields_fail_closed_to_a2(self) -> None:
        cases = (
            {},
            {"player": 0, "farms": [{}, {"money": 1}]},
            {"player": 2, "farms": [{"money": 1}, {"money": 2}]},
            {"player": True, "farms": [{"money": 2}, {"money": 1}]},
            {"player": 0, "farms": [{"money": True}, {"money": 1}]},
            {"player": 0, "farms": [{"money": 2}, {"money": False}]},
            {"player": 0, "farms": [{"money": float("nan")}, {"money": 2}]},
        )
        for obs in cases:
            with self.subTest(obs=obs):
                self.assertEqual(self.decide(obs), self.a2_decision)

    def test_serving_contract(self) -> None:
        self.assertTrue(issubclass(main.A2PublicWinRiskAgent, main.a2.NoShopGateAgent))
        text = Path(main.__file__).read_text(encoding="utf-8")
        self.assertNotIn("__file__", text)
        self.assertGreater(text.rfind("def agent("), text.rfind("def model_status("))


if __name__ == "__main__":
    unittest.main()
