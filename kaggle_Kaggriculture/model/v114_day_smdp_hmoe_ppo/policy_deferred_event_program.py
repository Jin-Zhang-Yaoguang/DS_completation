"""Common safe-probe expert followed by one fixed production-route expert."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from event_program import observation_step
from event_program_features import encode_event_program_features
from policy_event_program import FixedEventProgramPolicy


class DeferredFixedEventProgramPolicy:
    """Observe one day with legal PASS actions, then commit to a full route."""

    def __init__(
        self,
        decision: Mapping[str, Any],
        *,
        name: str,
        probe_steps: int = 24,
    ) -> None:
        if int(probe_steps) <= 0 or int(probe_steps) % 24 != 0:
            raise ValueError("probe_steps must be a positive whole number of days")
        self.name = str(name)
        self.probe_steps = int(probe_steps)
        self.route = FixedEventProgramPolicy(decision, name=name)
        self.action_steps = 0
        self.probe_action_steps = 0
        self.probe_features: np.ndarray | None = None

    @property
    def manager_decision_count(self) -> int:
        return int(self.route.manager_decision_count)

    @property
    def contract_violation_count(self) -> int:
        return int(self.route.contract_violation_count)

    @property
    def terminal_procurement_count(self) -> int:
        return int(self.route.terminal_procurement_count)

    def act(self, observation: Any) -> dict[str, Any]:
        from kaggle_environments.envs.kaggriculture import kaggriculture

        step = observation_step(observation)
        if step < self.probe_steps:
            self.probe_action_steps += 1
            action = kaggriculture.pass_agent(observation)
        else:
            if self.probe_features is None:
                self.probe_features = np.asarray(
                    encode_event_program_features(
                        observation,
                        current_decision=None,
                        current_event=None,
                    ),
                    dtype=np.float32,
                )
            action = self.route.act(observation)
        self.action_steps += 1
        return action

    def __call__(self, observation: Any, configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


__all__ = ["DeferredFixedEventProgramPolicy"]
