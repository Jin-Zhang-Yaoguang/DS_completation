from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate_market_timing_program import parse_variant  # noqa: E402
from policy_market_timing_event_program import (  # noqa: E402
    MarketQueuePlacement,
    MarketTimingMode,
    should_sell,
)


class MarketTimingTest(unittest.TestCase):
    def test_immediate_always_sells(self) -> None:
        self.assertTrue(all(should_sell(MarketTimingMode.IMMEDIATE, step) for step in range(719)))

    def test_post_demand_sells_one_tick_after_each_four_step_demand(self) -> None:
        selected = [step for step in range(12) if should_sell("POST_DEMAND", step)]
        self.assertEqual(selected, [1, 5, 9])

    def test_pre_day_flood_sells_at_hour_23(self) -> None:
        selected = [step for step in range(50) if should_sell("PRE_DAY_FLOOD", step)]
        self.assertEqual(selected, [23, 47])

    def test_parse_legacy_variant_defaults_to_full_front(self) -> None:
        self.assertEqual(
            parse_variant("WHEAT__POST_DEMAND"),
            ("WHEAT", "POST_DEMAND", 1.0, "FRONT"),
        )

    def test_parse_quantity_and_queue_variant(self) -> None:
        self.assertEqual(
            parse_variant("STRAWBERRY__POST_DEMAND__Q50__BACK"),
            ("STRAWBERRY", "POST_DEMAND", 0.5, "BACK"),
        )
        self.assertEqual(MarketQueuePlacement("BACK"), MarketQueuePlacement.BACK)

    def test_rejects_invalid_quantity_or_queue(self) -> None:
        with self.assertRaises(ValueError):
            parse_variant("WHEAT__POST_DEMAND__Q0__FRONT")
        with self.assertRaises(ValueError):
            parse_variant("WHEAT__POST_DEMAND__Q50__MIDDLE")


if __name__ == "__main__":
    unittest.main()
