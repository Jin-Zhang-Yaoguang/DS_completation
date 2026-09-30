import unittest

import numpy as np

from delayed_tree_router import fit_regression_tree, predict_tree, router_features_from_encoded


class DelayedTreeRouterTest(unittest.TestCase):
    def test_tree_learns_simple_multioutput_split(self):
        x = np.asarray([[0.0], [0.1], [0.2], [0.8], [0.9], [1.0]])
        y = np.asarray([[3, 0], [2, 0], [4, 1], [0, 4], [0, 3], [1, 5]])
        tree = fit_regression_tree(x, y, max_depth=1, min_leaf=2)
        self.assertEqual(int(predict_tree(tree, [0.15]).argmax()), 0)
        self.assertEqual(int(predict_tree(tree, [0.85]).argmax()), 1)

    def test_feature_shape(self):
        encoded = {
            "global": np.zeros(60), "board": np.ones((2, 10, 10, 21)),
            "units": np.ones((16, 121)), "unit_mask": np.r_[np.ones(3), np.zeros(13)],
        }
        vector = router_features_from_encoded(encoded)
        self.assertEqual(vector.shape, (118,))
        np.testing.assert_array_equal(vector[60:102], np.full(42, 100.0))
        np.testing.assert_array_equal(vector[102:], np.full(16, 3.0))


if __name__ == "__main__":
    unittest.main()
