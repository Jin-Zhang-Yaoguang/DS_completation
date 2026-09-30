"""Local JAX inference policy for V113 BC/PPO checkpoints."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from model import HMoEActorCritic


def _masked_argmax(logits: np.ndarray, mask) -> int:
    valid = np.asarray(mask, dtype=bool)
    if not np.any(valid):
        return 0
    return int(np.argmax(np.where(valid, logits, -1e30)))


def _masked_choice(logits: np.ndarray, mask, rng: np.random.Generator, deterministic: bool) -> tuple[int, float, float]:
    valid = np.asarray(mask, dtype=bool)
    if not np.any(valid):
        valid = np.zeros_like(valid)
        valid[0] = True
    masked = np.where(valid, np.asarray(logits, dtype=np.float64), -1e30)
    shifted = masked - np.max(masked)
    probability = np.exp(shifted) * valid
    probability /= probability.sum()
    token = int(np.argmax(probability)) if deterministic else int(rng.choice(len(probability), p=probability))
    logprob = float(np.log(max(1e-30, probability[token])))
    entropy = float(-np.sum(probability[valid] * np.log(np.maximum(1e-30, probability[valid]))))
    return token, logprob, entropy


class V113Policy:
    def __init__(
        self, checkpoint: Path, forced_expert: int | None = None,
        expert_schedule: list[int] | tuple[int, ...] | None = None,
        opponent_blind: bool = False,
    ):
        payload = serialization.msgpack_restore(checkpoint.read_bytes())
        self.params = payload["params"]
        self.model = HMoEActorCritic()
        self._apply = jax.jit(lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m))
        self.current_expert = None
        self.forced_expert = forced_expert
        self.expert_schedule = tuple(expert_schedule) if expert_schedule is not None else None
        self.opponent_blind = opponent_blind
        self.last_step = -1
        self.expert_usage = Counter()
        self.actions = 0
        self.nonpass_unit_orders = 0
        self.operation_counts = Counter()

    def _forward(self, obs):
        encoded = features.encode_observation(obs, opponent_blind=self.opponent_blind)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        output = self._apply(self.params, state["global"], state["board"], state["units"], state["unit_mask"])
        return encoded, jax.tree.map(lambda value: np.asarray(value[0]), output)

    def act(
        self, obs, rng: np.random.Generator, deterministic: bool = False,
        router_deterministic: bool | None = None, worker_deterministic: bool | None = None,
        router_temperature: float = 1.0, worker_temperature: float = 1.0,
    ):
        router_deterministic = deterministic if router_deterministic is None else router_deterministic
        worker_deterministic = deterministic if worker_deterministic is None else worker_deterministic
        if router_temperature <= 0 or worker_temperature <= 0:
            raise ValueError("policy temperatures must be positive")
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.current_expert = None
            self.expert_usage.clear()
            self.actions = 0
            self.nonpass_unit_orders = 0
            self.operation_counts.clear()
        self.last_step = step
        encoded, output = self._forward(obs)
        router_mask = float(self.current_expert is None or step % 24 == 0)
        router_logprob = 0.0
        day = min(29, max(0, step // 24))
        if self.forced_expert is not None:
            self.current_expert = int(self.forced_expert)
            router_mask = 0.0
        elif self.expert_schedule is not None:
            if len(self.expert_schedule) != 30:
                raise ValueError("expert_schedule must contain exactly 30 day experts")
            self.current_expert = int(self.expert_schedule[day])
            router_mask = 0.0
        elif self.current_expert is None or step % 24 == 0:
            self.current_expert, router_logprob, _ = _masked_choice(
                output["router_logits"] / router_temperature,
                np.ones_like(output["router_logits"], dtype=bool), rng, router_deterministic
            )
        expert = self.current_expert
        self.expert_usage[expert] += 1

        unit_orders = []
        unit_tokens = np.full((features.MAX_UNITS,), space.UNIT_INDEX["PASS"], dtype=np.int16)
        unit_quantities = np.zeros((features.MAX_UNITS,), dtype=np.int16)
        unit_masks = np.zeros((features.MAX_UNITS, len(space.UNIT_TOKENS)), dtype=bool)
        unit_logprobs = np.zeros((features.MAX_UNITS,), dtype=np.float32)
        unit_quantity_logprobs = np.zeros((features.MAX_UNITS,), dtype=np.float32)
        unit_quantity_mask = np.zeros((features.MAX_UNITS,), dtype=np.float32)
        unit_quantity_masks = np.zeros((features.MAX_UNITS, space.QUANTITY_DIM), dtype=bool)
        count = min(features.MAX_UNITS, space.unit_count(obs))
        for unit_index in range(count):
            legal = np.asarray(space.unit_legal_mask(obs, unit_index), dtype=bool)
            token, logprob, _ = _masked_choice(
                output["unit_logits"][expert, unit_index] / worker_temperature,
                legal, rng, worker_deterministic,
            )
            quantity_needed = space.UNIT_TOKENS[token].startswith("PICKUP:") or space.UNIT_TOKENS[token].startswith("PLACE:")
            quantity_legal = np.asarray(space.unit_quantity_mask(obs, unit_index, token), dtype=bool)
            quantity, quantity_logprob, _ = _masked_choice(
                output["unit_quantity_logits"][expert, unit_index] / worker_temperature,
                quantity_legal, rng, worker_deterministic
            ) if quantity_needed else (0, 0.0, 0.0)
            order = space.decode_unit(obs, unit_index, token, quantity)
            unit_orders.append(order)
            self.operation_counts[f"unit:{order[0]}"] += 1
            unit_tokens[unit_index] = token
            unit_quantities[unit_index] = quantity
            unit_masks[unit_index] = legal
            unit_logprobs[unit_index] = logprob
            unit_quantity_logprobs[unit_index] = quantity_logprob
            unit_quantity_mask[unit_index] = float(quantity_needed)
            unit_quantity_masks[unit_index] = quantity_legal
            self.nonpass_unit_orders += int(order[0] != "PASS")

        shadow = space.market_shadow(obs)
        space.project_unit_orders(obs, unit_orders, shadow)
        market = []
        market_tokens = np.full((space.MAX_MARKET_SLOTS,), space.MARKET_INDEX["STOP"], dtype=np.int16)
        market_quantities = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
        market_masks = np.zeros((space.MAX_MARKET_SLOTS, len(space.MARKET_TOKENS)), dtype=bool)
        market_slot_mask = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.float32)
        market_logprobs = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.float32)
        market_quantity_logprobs = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.float32)
        market_quantity_mask = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.float32)
        market_quantity_masks = np.zeros((space.MAX_MARKET_SLOTS, space.QUANTITY_DIM), dtype=bool)
        for slot in range(space.MAX_MARKET_SLOTS):
            legal = np.asarray(space.market_legal_mask(shadow), dtype=bool)
            token, logprob, _ = _masked_choice(
                output["market_logits"][expert, slot] / worker_temperature,
                legal, rng, worker_deterministic,
            )
            market_tokens[slot] = token
            market_masks[slot] = legal
            market_slot_mask[slot] = 1.0
            market_logprobs[slot] = logprob
            if token == space.MARKET_INDEX["STOP"]:
                break
            quantity_needed = space.MARKET_TOKENS[token] not in {"HIRE", "BUY_LAND"}
            quantity_legal = np.asarray(space.market_quantity_mask(shadow, token), dtype=bool)
            quantity, quantity_logprob, _ = _masked_choice(
                output["market_quantity_logits"][expert, slot] / worker_temperature,
                quantity_legal, rng, worker_deterministic
            ) if quantity_needed else (0, 0.0, 0.0)
            market_quantities[slot] = quantity
            market_quantity_logprobs[slot] = quantity_logprob
            market_quantity_mask[slot] = float(quantity_needed)
            market_quantity_masks[slot] = quantity_legal
            order = space.apply_market_token(shadow, token, quantity)
            if order is None:
                break
            market.append(order)
            self.operation_counts[f"market:{order[0]}"] += 1
        self.actions += 1
        action = {"farmer": unit_orders[0], "hands": unit_orders[1:], "market": market}
        trace = {
            **encoded,
            "expert": np.int16(expert),
            "router_mask": np.float32(router_mask),
            "router_logprob": np.float32(router_logprob),
            "unit_tokens": unit_tokens,
            "unit_quantities": unit_quantities,
            "unit_action_masks": unit_masks,
            "unit_logprobs": unit_logprobs,
            "unit_quantity_logprobs": unit_quantity_logprobs,
            "unit_quantity_mask": unit_quantity_mask,
            "unit_quantity_masks": unit_quantity_masks,
            "market_tokens": market_tokens,
            "market_quantities": market_quantities,
            "market_action_masks": market_masks,
            "market_slot_mask": market_slot_mask,
            "market_logprobs": market_logprobs,
            "market_quantity_logprobs": market_quantity_logprobs,
            "market_quantity_mask": market_quantity_mask,
            "market_quantity_masks": market_quantity_masks,
            "value_prediction": np.float32(output["value"]),
        }
        return action, trace

    def __call__(self, obs, configuration=None):
        del configuration
        action, _ = self.act(obs, np.random.default_rng(0), deterministic=True)
        return action
