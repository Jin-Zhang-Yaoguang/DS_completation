from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy_supply_flood_poultry import SupplyFloodPoultryPolicy  # noqa: E402


class SupplyFloodPoultryTest(unittest.TestCase):
    def test_capacity_and_role_are_distinct(self) -> None:
        policy = SupplyFloodPoultryPolicy()
        self.assertEqual(policy.target_geese, 12)
        self.assertEqual(policy.worker_cap, 14)
        self.assertEqual(policy.name, "SUPPLY_FLOOD_POULTRY")
        self.assertEqual(len(policy.coop_targets(10)), 12)


if __name__ == "__main__":
    unittest.main()
