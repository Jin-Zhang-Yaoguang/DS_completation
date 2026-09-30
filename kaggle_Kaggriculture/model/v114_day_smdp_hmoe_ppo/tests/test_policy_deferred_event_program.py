from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import policy_deferred_event_program as deferred  # noqa: E402


DECISION = {
    "production_line": "STRAWBERRY",
    "worker_cap": 4,
    "cash_reserve": 500,
    "sell_style": "IMMEDIATE",
    "terminal_mode": "NORMAL",
}


class DeferredFixedEventProgramPolicyTest(unittest.TestCase):
    def test_probe_uses_pass_then_delegates_once_probe_is_complete(self):
        policy = deferred.DeferredFixedEventProgramPolicy(
            DECISION, name="strawberry", probe_steps=24
        )
        expected_pass = {"farmer": ["PASS"], "hands": [], "market": []}
        with (
            mock.patch(
                "kaggle_environments.envs.kaggriculture.kaggriculture.pass_agent",
                return_value=expected_pass,
            ) as pass_agent,
            mock.patch.object(policy.route, "act", return_value={"route": True}) as route,
            mock.patch.object(
                deferred,
                "encode_event_program_features",
                return_value=np.arange(7, dtype=np.float32),
            ) as encode,
            mock.patch.object(deferred, "observation_step", side_effect=[0, 23, 24, 25]),
        ):
            self.assertEqual(policy.act({}), expected_pass)
            self.assertEqual(policy.act({}), expected_pass)
            self.assertEqual(policy.act({}), {"route": True})
            self.assertEqual(policy.act({}), {"route": True})

        self.assertEqual(pass_agent.call_count, 2)
        self.assertEqual(route.call_count, 2)
        self.assertEqual(encode.call_count, 1)
        self.assertIsNone(encode.call_args.kwargs["current_event"])
        self.assertEqual(policy.action_steps, 4)
        self.assertEqual(policy.probe_action_steps, 2)
        np.testing.assert_array_equal(policy.probe_features, np.arange(7, dtype=np.float32))

    def test_probe_steps_must_be_positive_whole_days(self):
        for value in (0, -24, 1, 25):
            with self.subTest(value=value), self.assertRaises(ValueError):
                deferred.DeferredFixedEventProgramPolicy(
                    DECISION, name="bad", probe_steps=value
                )


if __name__ == "__main__":
    unittest.main()
