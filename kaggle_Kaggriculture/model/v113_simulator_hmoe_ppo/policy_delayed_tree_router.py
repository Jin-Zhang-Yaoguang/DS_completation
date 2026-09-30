"""Timed-sequence PPO expert portfolio with a step-72 shallow-tree Router."""

from __future__ import annotations

from pathlib import Path

import features
from delayed_tree_router import load_router, predict_tree, router_features_from_encoded
from policy_sequence_action import TimedSequenceActionV113Policy


class DelayedTreeRouterPolicy(TimedSequenceActionV113Policy):
    def __init__(self, checkpoint: Path, router_model: Path, **kwargs):
        super().__init__(checkpoint, **kwargs)
        payload = load_router(router_model)
        self.router_tree = payload["tree"]
        self.router_combos = [tuple(combo) for combo in payload["combos"]]
        self.router_step = int(payload["router_step"])
        self.reset_step = (
            int(payload["reset_step"]) if payload.get("reset_step") is not None else None
        )
        self.base_combo = tuple(payload["base_combo"])
        self.selected_combo = self.base_combo
        self.router_selection_counts = {}
        self.unit_expert_schedule = ((0, self.base_combo[0]),)
        self.market_expert_schedule = ((0, self.base_combo[1]),)

    def act(self, obs):
        step = int(obs.get("step", 0) or 0)
        if step <= self.last_step:
            self.selected_combo = self.base_combo
            self.unit_expert_schedule = ((0, self.base_combo[0]),)
            self.market_expert_schedule = ((0, self.base_combo[1]),)
        if step == self.router_step:
            encoded = features.encode_observation(obs)
            predictions = predict_tree(
                self.router_tree, router_features_from_encoded(encoded)
            )
            self.selected_combo = self.router_combos[int(predictions.argmax())]
            unit_expert, market_expert = self.selected_combo
            self.unit_expert_schedule = (
                ((0, self.base_combo[0]), (step, unit_expert), (self.reset_step, self.base_combo[0]))
                if self.reset_step is not None else ((0, self.base_combo[0]), (step, unit_expert))
            )
            self.market_expert_schedule = (
                ((0, self.base_combo[1]), (step, market_expert), (self.reset_step, self.base_combo[1]))
                if self.reset_step is not None else ((0, self.base_combo[1]), (step, market_expert))
            )
            key = f"U{unit_expert}M{market_expert}"
            self.router_selection_counts[key] = self.router_selection_counts.get(key, 0) + 1
        return super().act(obs)
