import unittest

import numpy as np

import action_space as space
from action_history import ActionHistoryState, HISTORY_FEATURES, augment_global


class ActionHistoryTest(unittest.TestCase):
    def test_latches_first_demand_and_records_pre_action_history(self):
        state = ActionHistoryState()
        global_features = np.zeros((60,), dtype=np.float32)
        self.assertEqual(augment_global(global_features, state).shape, (60 + HISTORY_FEATURES,))
        global_features[-9] = 0.125
        first = augment_global(global_features, state)
        global_features[-9:] = 0.0
        later = augment_global(global_features, state)
        self.assertEqual(first[60], 0.125)
        self.assertEqual(later[60], 0.125)

    def test_market_flow_and_unit_categories(self):
        state = ActionHistoryState()
        state.update_tokens(
            [space.UNIT_INDEX["PASS"], space.UNIT_INDEX["NORTH"], space.UNIT_INDEX["WATER"]],
            [space.MARKET_INDEX["SELL:WHEAT"], space.MARKET_INDEX["BUY_PRODUCT:WHEAT"]],
            [5, 2],
        )
        vector = state.observe_global(np.zeros((60,), dtype=np.float32))
        self.assertAlmostEqual(vector[9], 0.03)
        self.assertAlmostEqual(vector[18], 0.003)
        np.testing.assert_allclose(
            vector[-5:], np.asarray([1, 1, 0, 1, 0], dtype=np.float32) / 16
        )


if __name__ == "__main__":
    unittest.main()
