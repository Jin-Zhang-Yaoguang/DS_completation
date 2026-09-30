"""Multi-checkpoint Product MoE for V113's independently trained specialists."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

import action_space as space
from policy_factorized import FactorizedV113Policy


class FactorizedPortfolioPolicy:
    def __init__(
        self, router_checkpoint: Path, specialist_checkpoints: dict[int, Path],
        router_period: int = 720, forced_expert: int | None = None,
        scale_worker_cap: int = 8, scale_seed_capacity: int = 11,
    ):
        missing = set(range(5)) - set(specialist_checkpoints)
        if missing:
            raise ValueError(f"missing crop specialists: {sorted(missing)}")
        self.router = FactorizedV113Policy(router_checkpoint)
        self.specialists = {
            expert: FactorizedV113Policy(
                checkpoint, forced_unit_expert=expert, forced_market_expert=expert,
                scale_worker_cap=scale_worker_cap,
                scale_seed_capacity=scale_seed_capacity,
            )
            for expert, checkpoint in specialist_checkpoints.items()
        }
        self.router_period = int(router_period)
        self.forced_expert = forced_expert
        self.current_expert = None
        self.last_step = -1
        self.expert_usage = Counter()
        self.operation_counts = Counter()

    def act(self, obs):
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.current_expert = None
            self.expert_usage.clear()
            self.operation_counts.clear()
        self.last_step = step
        if self.current_expert is None or step % self.router_period == 0:
            if self.forced_expert is not None:
                self.current_expert = int(self.forced_expert)
            else:
                _, output = self.router._forward(obs)
                self.current_expert = int(np.argmax(output["unit_router_logits"][:5]))
        specialist = self.specialists[self.current_expert]
        before = specialist.operation_counts.copy()
        action = specialist.act(obs)
        for key, value in specialist.operation_counts.items():
            delta = value - before.get(key, 0)
            if delta > 0:
                self.operation_counts[key] += delta
        self.expert_usage[self.current_expert] += 1
        return action

    def __call__(self, obs, configuration=None):
        return self.act(obs)
