import unittest

import numpy as np

import action_space as space
from build_factorized_dataset import factorized_labels, market_votes


class FactorizedDatasetTest(unittest.TestCase):
    def test_market_router_is_independent_of_unit_router(self):
        self.assertEqual(market_votes(
            np.asarray([space.MARKET_INDEX["SELL:CARROT"]]), np.asarray([1])
        )[1], 1)
        self.assertEqual(market_votes(
            np.asarray([space.MARKET_INDEX["BUY_ANIMAL:COW"]]), np.asarray([1])
        )[5], 1)

    def test_unit_label_is_day_constant_while_market_can_change(self):
        unit = np.full((2, 2), space.UNIT_INDEX["PASS"], dtype=np.int16)
        unit[:, 0] = space.UNIT_INDEX["WATER"]
        market = np.asarray([
            [space.MARKET_INDEX["BUY_SEED:CARROT"]],
            [space.MARKET_INDEX["SELL:CARROT"]],
        ])
        data = {
            "episode": np.asarray([1, 1]), "seat": np.asarray([0, 0]),
            "step": np.asarray([0, 1]), "unit_tokens": unit,
            "market_tokens": market, "market_mask": np.ones((2, 1), dtype=np.uint8),
        }
        unit_expert, market_expert, _ = factorized_labels(data)
        self.assertEqual(unit_expert.tolist(), [1, 1])
        self.assertEqual(market_expert.tolist(), [1, 1])


if __name__ == "__main__":
    unittest.main()
