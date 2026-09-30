from __future__ import annotations

import unittest

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import AgentHandle


class AgentHandleContractTest(unittest.TestCase):
    def test_one_argument_agent_is_called_once(self) -> None:
        calls: list[object] = []

        def agent(obs):
            calls.append(obs)
            return {"farmer": ["PASS"], "hands": [], "market": []}

        handle = AgentHandle("one", {"id": "one"}, agent)
        self.assertEqual(handle("observation")["farmer"], ["PASS"])
        self.assertEqual(calls, ["observation"])

    def test_internal_type_error_is_not_retried(self) -> None:
        calls = 0

        def broken(obs, configuration=None):
            nonlocal calls
            calls += 1
            raise TypeError("policy defect after state mutation")

        handle = AgentHandle("broken", {"id": "broken"}, broken)
        with self.assertRaisesRegex(TypeError, "policy defect"):
            handle("observation", {})
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
