import unittest

import numpy as np

from policy_factorized import normalize_expert_schedule, scheduled_expert
from evaluate_factorized import RouterSnapshotPolicy


class ExpertScheduleTest(unittest.TestCase):
    def test_delayed_switch(self):
        schedule = normalize_expert_schedule(((0, 3), (72, 4), (216, 5)))
        self.assertEqual(scheduled_expert(schedule, 0), 3)
        self.assertEqual(scheduled_expert(schedule, 71), 3)
        self.assertEqual(scheduled_expert(schedule, 72), 4)
        self.assertEqual(scheduled_expert(schedule, 215), 4)
        self.assertEqual(scheduled_expert(schedule, 216), 5)

    def test_rejects_ambiguous_schedules(self):
        for schedule in ((), ((1, 3),), ((0, 3), (0, 4)), ((0, 3), (-1, 4))):
            with self.subTest(schedule=schedule), self.assertRaises(ValueError):
                normalize_expert_schedule(schedule)

    def test_snapshot_wrapper_captures_before_action(self):
        class DummyPolicy:
            def __call__(self, obs, configuration=None):
                return {"farmer": ["PASS"], "hands": [], "market": []}

        wrapper = RouterSnapshotPolicy(DummyPolicy(), 72)
        import evaluate_factorized

        original = evaluate_factorized.features.encode_observation
        evaluate_factorized.features.encode_observation = lambda obs: {
            "global": np.asarray([obs["step"]], dtype=np.float32)
        }
        try:
            wrapper({"step": 71})
            self.assertIsNone(wrapper.snapshot)
            wrapper({"step": 72})
            self.assertEqual(wrapper.snapshot, {"global": [72.0]})
        finally:
            evaluate_factorized.features.encode_observation = original


if __name__ == "__main__":
    unittest.main()
