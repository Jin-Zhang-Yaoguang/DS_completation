import unittest

import numpy as np

import action_space as space
from relabel_expert_semantics import row_votes, semantic_labels


class SemanticExpertRelabelTest(unittest.TestCase):
    def test_row_votes_separates_crop_market_and_terminal(self):
        unit = np.asarray([space.UNIT_INDEX["PLANT:CARROT"], space.UNIT_INDEX["PASS"]])
        market = np.asarray([space.MARKET_INDEX["SELL:CARROT"], space.MARKET_INDEX["STOP"]])
        mask = np.asarray([1, 1])
        votes = row_votes(unit, market, mask, 100)
        self.assertEqual(votes[0], 3.0)
        self.assertEqual(votes[3], 3.0)
        self.assertEqual(row_votes(unit, market, mask, 680)[5], 100)

    def test_semantic_labels_are_constant_inside_day(self):
        unit = np.full((2, 2), space.UNIT_INDEX["PASS"], dtype=np.int16)
        unit[1, 0] = space.UNIT_INDEX["WATER"]
        market = np.full((2, 2), space.MARKET_INDEX["STOP"], dtype=np.int16)
        data = {
            "episode": np.asarray([1, 1]), "seat": np.asarray([0, 0]),
            "step": np.asarray([0, 1]), "unit_tokens": unit,
            "market_tokens": market, "market_mask": np.ones((2, 2), dtype=np.uint8),
        }
        labels, metadata = semantic_labels(data)
        self.assertEqual(labels.tolist(), [0, 0])
        self.assertEqual(metadata["day_counts"]["0"], 1)


if __name__ == "__main__":
    unittest.main()
