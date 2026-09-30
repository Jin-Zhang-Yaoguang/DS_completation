from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy_enterprise_event_program import (  # noqa: E402
    PROFILES,
    EnterpriseEventProgramPolicy,
    _crop_assignment,
)


class EnterpriseProgramTest(unittest.TestCase):
    def test_profiles_are_independent_multi_product_contracts(self) -> None:
        self.assertEqual(set(PROFILES), {"GRAIN_MELON", "DAIRY_BERRY", "WOOL_MELON"})
        for profile in PROFILES.values():
            self.assertEqual(len(profile.crop_weights), 2)
            self.assertEqual(profile.worker_cap, 10)

    def test_crop_assignment_is_deterministic_and_complete(self) -> None:
        coordinates = [(x, y) for y in range(5) for x in range(5)]
        profile = PROFILES["GRAIN_MELON"]
        first = _crop_assignment(coordinates, profile)
        second = _crop_assignment(list(reversed(coordinates)), profile)
        self.assertEqual(first, second)
        self.assertEqual(set(first), set(coordinates))
        self.assertEqual(sum(crop == "WHEAT" for crop in first.values()), 8)
        self.assertEqual(sum(crop == "MELON" for crop in first.values()), 17)

    def test_policy_counters_start_clean(self) -> None:
        policy = EnterpriseEventProgramPolicy("DAIRY_BERRY")
        self.assertEqual(policy.action_steps, 0)
        self.assertEqual(policy.terminal_procurement_count, 0)
        self.assertFalse(any(policy.sale_units.values()))

    def test_terminal_execution_is_one_manager_decision(self) -> None:
        policy = EnterpriseEventProgramPolicy("DAIRY_BERRY")
        for step in range(719):
            policy._record_manager_boundary(step, step >= 671)
        self.assertEqual(policy.manager_decision_count, 29)
        self.assertEqual(policy.terminal_execution_steps, 48)


if __name__ == "__main__":
    unittest.main()
