import unittest

import action_space as space
from build_per_slot_role_dataset import market_role, unit_role


class PerSlotRoleContractTest(unittest.TestCase):
    def test_unit_roles_cover_semantic_families(self):
        self.assertEqual(unit_role(space.UNIT_INDEX["PASS"]), 0)
        self.assertEqual(unit_role(space.UNIT_INDEX["PLANT:WHEAT"]), 1)
        self.assertEqual(unit_role(space.UNIT_INDEX["HARVEST"]), 1)
        self.assertEqual(unit_role(space.UNIT_INDEX["CARE"]), 2)
        self.assertEqual(unit_role(space.UNIT_INDEX["BUILD_PASTURE"]), 2)
        self.assertEqual(unit_role(space.UNIT_INDEX["NORTH"]), 3)
        self.assertEqual(unit_role(space.UNIT_INDEX["PICKUP:WOOL"]), 3)

    def test_market_roles_cover_stop_procure_sell(self):
        self.assertEqual(market_role(space.MARKET_INDEX["STOP"]), 0)
        self.assertEqual(market_role(space.MARKET_INDEX["HIRE"]), 1)
        self.assertEqual(market_role(space.MARKET_INDEX["BUY_SEED:MELON"]), 1)
        self.assertEqual(market_role(space.MARKET_INDEX["SELL:WOOL"]), 2)


if __name__ == "__main__":
    unittest.main()
