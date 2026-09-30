from __future__ import annotations

import json
from pathlib import Path
import unittest

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as kg

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent as create_registered_agent,
    load_registry,
)
from kaggle_Kaggriculture.model.v12a_terminal_branch_guard.main import make_agent


HERE = Path(__file__).resolve().parent
REGISTRY = (
    HERE.parent
    / "v11_iterative_league"
    / "runs"
    / "round_002"
    / "strategy"
    / "registry_next.json"
)


class ActionLog:
    def __init__(self, agent):
        self.agent = agent
        self.actions: list[str] = []

    def __call__(self, obs, configuration=None):
        action = self.agent(obs, configuration)
        self.actions.append(
            json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        return action


class ParentEquivalenceIntegrationTest(unittest.TestCase):
    def test_unguarded_mode_reproduces_registered_r002_for_720_steps(self):
        registry = load_registry(REGISTRY)
        registered = ActionLog(
            create_registered_agent(
                registry, "r002_learned_router_topday_animal_throttle"
            )
        )
        reproduction = ActionLog(
            make_agent(enable_guard=False, enable_terminal=False)
        )
        seed = 434439023
        for target in (registered, reproduction):
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            steps = env.run([target, kg.starter_agent])
            self.assertEqual(len(steps), 720)
            self.assertEqual(
                [str(state.status) for state in steps[-1]], ["DONE", "DONE"]
            )
        self.assertEqual(len(registered.actions), 719)
        self.assertEqual(reproduction.actions, registered.actions)


if __name__ == "__main__":
    unittest.main()

