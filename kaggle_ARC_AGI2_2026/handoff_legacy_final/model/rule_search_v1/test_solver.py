"""用未见过的合成网格检查规则搜索、两次预测和协议。"""

import unittest

from run import score, validate
from solver import predict


class SolverTests(unittest.TestCase):
    def test_multitest_protocol_and_rules(self):
        puzzles = {
            "recolor": {"train": [
                {"input": [[1, 0], [0, 1]], "output": [[2, 0], [0, 2]]},
                {"input": [[0, 1], [1, 1]], "output": [[0, 2], [2, 2]]}],
                "test": [{"input": [[1, 1, 0]]}, {"input": [[0], [1]]}]},
            "crop": {"train": [
                {"input": [[0, 0, 0], [0, 3, 0], [0, 0, 0]], "output": [[3]]},
                {"input": [[0, 0, 0, 0], [0, 4, 4, 0], [0, 0, 0, 0]], "output": [[4, 4]]}],
                "test": [{"input": [[0, 0, 0], [0, 5, 5], [0, 0, 0]]}]},
            "scale": {"train": [
                {"input": [[1]], "output": [[1, 1], [1, 1]]},
                {"input": [[2, 0]], "output": [[2, 2, 0, 0], [2, 2, 0, 0]]}],
                "test": [{"input": [[3, 4]]}]},
        }
        expected = {"recolor": [[[2, 2, 0]], [[0], [2]]], "crop": [[[5, 5]]],
                    "scale": [[[3, 3, 4, 4], [3, 3, 4, 4]]]}
        submission = predict(puzzles)
        validate(puzzles, submission)
        result = score(submission, expected)
        self.assertEqual(result["correct"], 4)
        self.assertEqual(result["total"], 4)

    def test_invalid_attempt_rejected(self):
        task = {"t": {"train": [], "test": [{"input": [[1]]}]}}
        with self.assertRaises(ValueError):
            validate(task, {"t": [{"attempt_1": [[1]]}]})


if __name__ == "__main__":
    unittest.main()
