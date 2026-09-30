from __future__ import annotations

import unittest
from unittest import mock

from kaggle_Kaggriculture.model.v12a2_no_wool_throttle import main


class NoWoolThrottleTest(unittest.TestCase):
    def test_removes_only_wool_from_approved_products(self) -> None:
        agent = object.__new__(main.NoWoolThrottleAgent)
        with mock.patch.object(
            main.base.BranchGuardAgent,
            "_should_throttle",
            return_value=(True, "approved", frozenset({"WOOL", "MILK"})),
        ):
            result = agent._should_throttle({}, {}, "baseline_v8")
        self.assertEqual(result, (True, "approved", frozenset({"MILK"})))

    def test_wool_only_trigger_is_deleted(self) -> None:
        agent = object.__new__(main.NoWoolThrottleAgent)
        with mock.patch.object(
            main.base.BranchGuardAgent,
            "_should_throttle",
            return_value=(True, "approved", frozenset({"WOOL"})),
        ):
            result = agent._should_throttle({}, {}, "baseline_v8")
        self.assertEqual(
            result,
            (False, "wool_throttle_removed", frozenset()),
        )

    def test_parent_skip_is_unchanged(self) -> None:
        agent = object.__new__(main.NoWoolThrottleAgent)
        expected = (False, "same_turn_shed_deposit", frozenset())
        with mock.patch.object(
            main.base.BranchGuardAgent,
            "_should_throttle",
            return_value=expected,
        ):
            self.assertEqual(agent._should_throttle({}, {}, None), expected)


if __name__ == "__main__":
    unittest.main()
