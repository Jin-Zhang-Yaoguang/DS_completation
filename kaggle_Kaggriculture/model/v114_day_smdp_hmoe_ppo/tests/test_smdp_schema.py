from __future__ import annotations

import math
import unittest

from collect_smdp_rollouts import SMDPRolloutBuilder, visible_summary
from smdp_schema import ManagerDecision, SMDPTransition, paired_seat_contract


def _obs(step: int, player: int = 0) -> dict:
    return {
        "step": step,
        "player": player,
        "farms": [
            {"money": 1000 + step, "hands": [[1, 1]]},
            {"money": 900, "hands": []},
        ],
        "private": {"shed": {"WHEAT": 2}},
        "market": {"inventory": {"WHEAT": 9999}},
    }


class SMDPSchemaTest(unittest.TestCase):
    def test_duration_discount_is_day_aware(self) -> None:
        row = SMDPTransition(
            "e", 1, 0, "starter", "anchor", 0, 24,
            ManagerDecision("PRODUCTION_LOGISTICS", "BALANCED", "NEUTRAL"),
            1.0, 10.0, 9.0, 0.0, False,
        )
        self.assertEqual(row.duration_turns, 24)
        self.assertTrue(math.isclose(row.discount(0.99), 0.99))

    def test_builder_enforces_residual_budget_and_contiguity(self) -> None:
        builder = SMDPRolloutBuilder("e", 1, 0, "starter", "anchor")
        decision = ManagerDecision("PRODUCTION_LOGISTICS", "BALANCED", "NEUTRAL")
        builder.begin(_obs(0), decision)
        for _ in range(4):
            builder.record_residual(True)
        with self.assertRaises(ValueError):
            builder.record_residual(True)
        row = builder.close(_obs(24), reward=1, own_reward=2, opponent_reward=1, catastrophe_cost=0, terminal=False)
        self.assertEqual(row.residual_non_keep, 4)
        builder.begin(_obs(24), decision)
        builder.close(_obs(719), reward=2, own_reward=3, opponent_reward=1, catastrophe_cost=0, terminal=True)
        builder.trajectory.validate_complete()

    def test_visible_summary_uses_only_public_opponent(self) -> None:
        obs = _obs(0)
        obs["farms"][1]["private"] = {"secret": 999}
        first = visible_summary(obs)
        obs["farms"][1]["private"] = {"secret": -1}
        self.assertEqual(visible_summary(obs), first)

    def test_paired_seat_contract(self) -> None:
        paired_seat_contract([
            {"seed": 1, "seat": 0, "opponent_id": "x"},
            {"seed": 1, "seat": 1, "opponent_id": "x"},
        ])
        with self.assertRaises(ValueError):
            paired_seat_contract([{"seed": 1, "seat": 0, "opponent_id": "x"}])


if __name__ == "__main__":
    unittest.main()
