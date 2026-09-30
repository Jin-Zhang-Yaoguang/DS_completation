from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy_exposure_adaptive_poultry import (  # noqa: E402
    ExposureAdaptivePoultryPolicy,
    TARGET_GEESE,
    _coop_targets,
)


class ExposureAdaptivePoultryTest(unittest.TestCase):
    def test_six_unique_coops_are_inside_initial_quadrant(self) -> None:
        targets = _coop_targets(10)
        self.assertEqual(len(targets), TARGET_GEESE)
        self.assertEqual(len(set(targets)), TARGET_GEESE)
        self.assertTrue(all(0 <= x < 5 and 0 <= y < 5 for x, y in targets))

    def test_policy_starts_without_historical_state(self) -> None:
        policy = ExposureAdaptivePoultryPolicy()
        self.assertIsNone(policy.previous_market_inventory)
        self.assertEqual(policy.max_geese_placed, 0)
        self.assertFalse(any(policy.sale_units.values()))

    def test_terminal_execution_is_one_manager_decision(self) -> None:
        policy = ExposureAdaptivePoultryPolicy()
        for step in range(719):
            policy._record_manager_boundary(step, step >= 671)
        self.assertEqual(policy.manager_decision_count, 29)
        self.assertEqual(policy.terminal_execution_steps, 48)


if __name__ == "__main__":
    unittest.main()
