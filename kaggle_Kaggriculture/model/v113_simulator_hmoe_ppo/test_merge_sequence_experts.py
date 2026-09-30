from __future__ import annotations

import copy
import unittest

import numpy as np

from merge_sequence_experts import assert_shared_params_equal, copy_slice
from model_sequence_action import HIDDEN, NUM_EXPERTS


def payload() -> dict:
    return {
        "params": {
            "shared": {"kernel": np.arange(6, dtype=np.float32).reshape(2, 3)},
            "unit_expert_projection": {
                "kernel": np.zeros((2, NUM_EXPERTS * HIDDEN), dtype=np.float32),
                "bias": np.zeros(NUM_EXPERTS * HIDDEN, dtype=np.float32),
            },
            "market_expert_projection": {
                "kernel": np.zeros((2, NUM_EXPERTS * HIDDEN), dtype=np.float32),
                "bias": np.zeros(NUM_EXPERTS * HIDDEN, dtype=np.float32),
            },
        }
    }


class MergeSequenceExpertsTest(unittest.TestCase):
    def test_copy_slice_only_changes_selected_expert(self) -> None:
        target = payload()
        source = payload()
        source["params"]["unit_expert_projection"]["kernel"][:] = 7
        source["params"]["unit_expert_projection"]["bias"][:] = 9
        copy_slice(target, source, "unit_expert_projection", 3)
        start, stop = 3 * HIDDEN, 4 * HIDDEN
        self.assertTrue(np.all(target["params"]["unit_expert_projection"]["kernel"][:, start:stop] == 7))
        self.assertTrue(np.all(target["params"]["unit_expert_projection"]["bias"][start:stop] == 9))
        self.assertEqual(np.count_nonzero(target["params"]["unit_expert_projection"]["kernel"][:, :start]), 0)
        self.assertEqual(np.count_nonzero(target["params"]["unit_expert_projection"]["kernel"][:, stop:]), 0)

    def test_shared_parameter_change_is_rejected(self) -> None:
        base = payload()
        candidate = copy.deepcopy(base)
        candidate["params"]["shared"]["kernel"][0, 0] = -1
        with self.assertRaisesRegex(ValueError, "changed frozen shared parameters"):
            assert_shared_params_equal(base, candidate, "candidate")


if __name__ == "__main__":
    unittest.main()
