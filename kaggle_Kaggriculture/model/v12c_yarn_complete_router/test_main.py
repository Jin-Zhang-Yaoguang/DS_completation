from __future__ import annotations

import unittest
from unittest.mock import patch

from kaggle_Kaggriculture.model.v12c_yarn_complete_router import main


class _Expert:
    def __init__(self, label: str, mismatch: bool = False) -> None:
        self.label = label
        self.mismatch = mismatch
        self.calls: list[int] = []

    def __call__(self, obs, configuration=None):
        step = int(obs["step"])
        self.calls.append(step)
        marker = self.label if (self.mismatch or step >= main.SWITCH_STEP) else "shared"
        return {"farmer": ["PASS", marker], "hands": [], "market": []}


def _obs(step: int, shops=()):
    return {"step": step, "town": {"unlocked_shops": list(shops)}}


class YarnRouterUnitTests(unittest.TestCase):
    def _agent(self, mismatch: bool = False):
        v8 = _Expert("v8")
        v5 = _Expert("v5", mismatch=mismatch)
        with patch.object(
            main,
            "_load_experts",
            return_value={main.ANCHOR_ID: v8, main.YARN_ID: v5},
        ):
            result = main.YarnCompleteRouterAgent()
        return result, v8, v5

    def test_yarn_selects_complete_v5_once(self):
        agent, v8, v5 = self._agent()
        for step in range(main.SWITCH_STEP):
            self.assertEqual(agent(_obs(step))["farmer"], ["PASS", "shared"])
        self.assertEqual(
            agent(_obs(main.SWITCH_STEP, ["YARN_STORE"]))["farmer"],
            ["PASS", "v5"],
        )
        self.assertEqual(
            agent(_obs(main.SWITCH_STEP + 1, ["YARN_STORE"]))["farmer"],
            ["PASS", "v5"],
        )
        self.assertEqual(agent.diagnostics()["selected"], main.YARN_ID)
        self.assertNotIn(main.SWITCH_STEP + 1, v8.calls)
        self.assertIn(main.SWITCH_STEP + 1, v5.calls)

    def test_non_yarn_selects_complete_v8(self):
        agent, v8, v5 = self._agent()
        for step in range(main.SWITCH_STEP + 1):
            action = agent(_obs(step, ["BAKERY"]))
        self.assertEqual(action["farmer"], ["PASS", "v8"])
        self.assertEqual(agent.diagnostics()["selected"], main.ANCHOR_ID)
        agent(_obs(main.SWITCH_STEP + 1, ["BAKERY"]))
        self.assertIn(main.SWITCH_STEP + 1, v8.calls)
        self.assertNotIn(main.SWITCH_STEP + 1, v5.calls)

    def test_prefix_mismatch_fails_closed_to_v8(self):
        agent, _, _ = self._agent(mismatch=True)
        for step in range(main.SWITCH_STEP + 1):
            agent(_obs(step, ["YARN_STORE"]))
        diagnostics = agent.diagnostics()
        self.assertFalse(diagnostics["prefix_match"])
        self.assertEqual(diagnostics["prefix_first_mismatch"], 0)
        self.assertEqual(diagnostics["selected"], main.ANCHOR_ID)
        self.assertEqual(
            diagnostics["selection_reason"], "prefix_or_yarn_expert_fallback"
        )

    def test_episode_reset_clears_selection(self):
        agent, _, _ = self._agent()
        for step in range(main.SWITCH_STEP + 1):
            agent(_obs(step, ["YARN_STORE"]))
        self.assertEqual(agent.diagnostics()["selected"], main.YARN_ID)
        agent(_obs(0, ["BAKERY"]))
        self.assertIsNone(agent.diagnostics()["selected"])


if __name__ == "__main__":
    unittest.main()

