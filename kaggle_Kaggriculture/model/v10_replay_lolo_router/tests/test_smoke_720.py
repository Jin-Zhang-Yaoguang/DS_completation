from __future__ import annotations

import unittest

from kaggle_Kaggriculture.model.v10_replay_lolo_router.expert_registry import (
    EXPERT_SPECS,
    create_agent,
)


class CompleteEpisodeSmokeTest(unittest.TestCase):
    def test_complete_agents_reach_done_after_720_turns(self) -> None:
        """One real-engine episode per registered agent; this is not a score eval."""
        from kaggle_environments import make
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg

        for model_id in sorted(EXPERT_SPECS):
            with self.subTest(model_id=model_id):
                candidate = create_agent(model_id)
                env = make("kaggriculture", configuration={"seed": 10822001}, debug=False)
                steps = env.run([candidate, kg.starter_agent])
                self.assertEqual(len(steps), 720)
                self.assertEqual(
                    [str(state.status) for state in steps[-1]],
                    ["DONE", "DONE"],
                )


if __name__ == "__main__":
    unittest.main()
