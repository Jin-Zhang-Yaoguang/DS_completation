from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_residual import (  # noqa: E402
    MarketResidualAction,
    abstaining_action,
    apply_market_residual,
    canonical_action_mask,
    scheduled_demand_quantity,
)


class MarketResidualTest(unittest.TestCase):
    def test_actual_public_demand_uses_center_and_unlocked_shop(self) -> None:
        observation = {
            "step": 25,
            "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]},
        }
        self.assertEqual(scheduled_demand_quantity(observation, "WHEAT"), 2)
        self.assertEqual(scheduled_demand_quantity(observation, "WOOL"), 3)
        self.assertEqual(scheduled_demand_quantity(observation, "STRAWBERRY"), 1)

    def test_no_shop_demand_on_non_periodic_step(self) -> None:
        observation = {"step": 24, "town": {"unlocked_shops": ["BAKERY"]}}
        self.assertEqual(scheduled_demand_quantity(observation, "WHEAT"), 0)

    def test_equivalent_actions_are_masked(self) -> None:
        self.assertEqual(
            canonical_action_mask(available=1, base_market_queue=[], step=25),
            (True, True, False, False, False),
        )
        self.assertEqual(
            canonical_action_mask(available=2, base_market_queue=[["HIRE"]], step=25),
            (True, True, True, True, True),
        )

    def test_terminal_allows_only_deterministic_keep(self) -> None:
        self.assertEqual(
            canonical_action_mask(available=10, base_market_queue=[], step=671),
            (True, False, False, False, False),
        )

    def test_residual_only_changes_target_sell(self) -> None:
        base = [["BUY_SEED", "WHEAT", 3], ["SELL", "STRAWBERRY", 7]]
        result = apply_market_residual(
            base_market_queue=base,
            product="STRAWBERRY",
            available=5,
            action=MarketResidualAction.HALF_BACK,
        )
        self.assertEqual(result, [["BUY_SEED", "WHEAT", 3], ["SELL", "STRAWBERRY", 3]])

    def test_near_uniform_serving_abstains(self) -> None:
        mask = [True] * 5
        self.assertEqual(
            abstaining_action([0.2] * 5, [0, 1, 1, 1, 1], mask),
            MarketResidualAction.KEEP_BASE,
        )
        self.assertEqual(
            abstaining_action([0.1, 0.7, 0.05, 0.1, 0.05], [0, 1, 1, 1, 1], mask),
            MarketResidualAction.SKIP_EVENT,
        )


if __name__ == "__main__":
    unittest.main()
