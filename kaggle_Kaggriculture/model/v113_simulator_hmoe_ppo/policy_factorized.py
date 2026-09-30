"""Deterministic closed-loop policy for V113's factorized BC checkpoints."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from model_factorized import FactorizedHMoEActorCritic
from policy import _masked_choice


def masked_argmax(logits, mask) -> int:
    legal = np.asarray(mask, dtype=bool)
    if not np.any(legal):
        return 0
    return int(np.argmax(np.where(legal, np.asarray(logits), -1e30)))


def normalize_expert_schedule(schedule):
    """Validate ``(start_step, expert_id)`` pairs used by delayed routers."""
    if schedule is None:
        return None
    normalized = tuple((int(start), int(expert)) for start, expert in schedule)
    if not normalized:
        raise ValueError("expert schedule cannot be empty")
    if normalized[0][0] != 0:
        raise ValueError("expert schedule must start at step 0")
    if any(start < 0 or expert < 0 for start, expert in normalized):
        raise ValueError("expert schedule values must be non-negative")
    if any(left[0] >= right[0] for left, right in zip(normalized, normalized[1:])):
        raise ValueError("expert schedule steps must be strictly increasing")
    return normalized


def scheduled_expert(schedule, step: int) -> int | None:
    if schedule is None:
        return None
    selected = schedule[0][1]
    for start, expert in schedule[1:]:
        if step < start:
            break
        selected = expert
    return int(selected)


class FactorizedV113Policy:
    def __init__(
        self, checkpoint: Path, forced_unit_expert: int | None = None,
        forced_market_expert: int | None = None, market_stop_bias: float = 0.0,
        coupled_product_router: bool = False, router_period: int = 24,
        scale_worker_cap: int | None = None, scale_seed_capacity: int | None = None,
        unit_expert_schedule=None, market_expert_schedule=None,
    ):
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        self.params = payload["params"]
        self.model = FactorizedHMoEActorCritic()
        self._apply = jax.jit(lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m))
        self.forced_unit_expert = forced_unit_expert
        self.forced_market_expert = forced_market_expert
        self.market_stop_bias = float(market_stop_bias)
        self.coupled_product_router = bool(coupled_product_router)
        self.router_period = int(router_period)
        self.scale_worker_cap = scale_worker_cap
        self.scale_seed_capacity = scale_seed_capacity
        self.unit_expert_schedule = normalize_expert_schedule(unit_expert_schedule)
        self.market_expert_schedule = normalize_expert_schedule(market_expert_schedule)
        if self.router_period <= 0:
            raise ValueError("router_period must be positive")
        if self.scale_worker_cap is not None and not 0 <= self.scale_worker_cap <= features.MAX_UNITS - 1:
            raise ValueError("scale_worker_cap is outside the represented unit capacity")
        if self.scale_seed_capacity is not None and self.scale_seed_capacity <= 0:
            raise ValueError("scale_seed_capacity must be positive")
        self.current_unit_expert = None
        self.last_step = -1
        self.unit_expert_usage = Counter()
        self.market_expert_usage = Counter()
        self.operation_counts = Counter()
        self.nonpass_unit_orders = 0

    def _forward(self, obs):
        encoded = features.encode_observation(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        output = self._apply(self.params, state["global"], state["board"], state["units"], state["unit_mask"])
        return encoded, jax.tree.map(lambda value: np.asarray(value[0]), output)

    def _planted_counts(self, obs) -> dict[str, int]:
        counts = {crop: 0 for crop in space.CROPS}
        for row in space.get(space.own_farm(obs), "tiles", []) or []:
            for tile in row:
                if isinstance(tile, dict):
                    crop = str(space.get(tile, "crop", ""))
                    if crop in counts:
                        counts[crop] += 1
        return counts

    def _market_legal_mask(self, obs, shadow):
        legal = np.asarray(space.market_legal_mask(shadow), dtype=bool)
        if self.scale_worker_cap is not None:
            hour = int(space.get(obs, "hour", int(space.get(obs, "step", 0) or 0) % 24) or 0)
            hands = max(0, int(shadow.get("units", 1)) - 1)
            legal[space.MARKET_INDEX["HIRE"]] &= hour == 0 and hands < self.scale_worker_cap
        if self.scale_seed_capacity is not None:
            planted = self._planted_counts(obs)
            for crop in space.CROPS:
                missing = self.scale_seed_capacity - planted[crop] - int(shadow["seeds"].get(crop, 0))
                legal[space.MARKET_INDEX[f"BUY_SEED:{crop}"]] &= missing > 0
        return legal

    def _market_quantity_mask(self, obs, shadow, token):
        name = space.MARKET_TOKENS[int(token)]
        if self.scale_seed_capacity is not None and name.startswith("BUY_SEED:"):
            crop = name.split(":", 1)[1]
            planted = self._planted_counts(obs)[crop]
            missing = max(0, self.scale_seed_capacity - planted - int(shadow["seeds"].get(crop, 0)))
            affordable = int(float(shadow["money"]) // space.SEED_COST[crop])
            return np.asarray(space.quantity_candidate_mask(min(missing, affordable)), dtype=bool)
        return np.asarray(space.market_quantity_mask(shadow, token), dtype=bool)

    def _unit_legal_mask(self, obs, unit_index, output):
        """Extension point for hierarchical policies to enforce option semantics."""
        return np.asarray(space.unit_legal_mask(obs, unit_index), dtype=bool)

    def _condition_unit_output(self, obs, unit_tokens, unit_quantities, output):
        """Extension point for decoders conditioned on the executed unit prefix."""
        return output

    def _condition_market_output(
        self, obs, unit_tokens, unit_quantities,
        market_tokens, market_quantities, output,
    ):
        """Extension point for decoders conditioned on the executed order prefix."""
        return output

    def act(self, obs):
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.current_unit_expert = None
            self.unit_expert_usage.clear()
            self.market_expert_usage.clear()
            self.operation_counts.clear()
            self.nonpass_unit_orders = 0
        self.last_step = step
        _, output = self._forward(obs)
        scheduled_unit = scheduled_expert(self.unit_expert_schedule, step)
        if scheduled_unit is not None:
            self.current_unit_expert = scheduled_unit
        elif self.current_unit_expert is None or step % self.router_period == 0:
            self.current_unit_expert = (
                int(self.forced_unit_expert) if self.forced_unit_expert is not None
                else int(np.argmax(output["unit_router_logits"]))
            )
        unit_expert = self.current_unit_expert
        scheduled_market = scheduled_expert(self.market_expert_schedule, step)
        market_expert = (
            scheduled_market if scheduled_market is not None else (
                unit_expert if self.coupled_product_router else (
                    int(self.forced_market_expert) if self.forced_market_expert is not None
                    else int(np.argmax(output["market_router_logits"]))
                )
            )
        )
        self.unit_expert_usage[unit_expert] += 1
        self.market_expert_usage[market_expert] += 1

        count = min(features.MAX_UNITS, space.unit_count(obs))
        unit_orders = []
        unit_tokens = np.full(
            (features.MAX_UNITS,), space.UNIT_INDEX["PASS"], dtype=np.int16
        )
        unit_quantities = np.zeros((features.MAX_UNITS,), dtype=np.int16)
        for unit_index in range(count):
            unit_output = self._condition_unit_output(
                obs, unit_tokens, unit_quantities, output
            )
            token = masked_argmax(
                unit_output["unit_logits"][unit_expert, unit_index],
                self._unit_legal_mask(obs, unit_index, unit_output),
            )
            unit_tokens[unit_index] = token
            quantity_needed = space.UNIT_TOKENS[token].startswith("PICKUP:") or space.UNIT_TOKENS[token].startswith("PLACE:")
            quantity = masked_argmax(
                unit_output["unit_quantity_logits"][unit_expert, unit_index],
                space.unit_quantity_mask(obs, unit_index, token),
            ) if quantity_needed else 0
            unit_quantities[unit_index] = quantity
            order = space.decode_unit(obs, unit_index, token, quantity)
            unit_orders.append(order)
            self.operation_counts[f"unit:{order[0]}"] += 1
            self.nonpass_unit_orders += int(order[0] != "PASS")

        shadow = space.market_shadow(obs)
        space.project_unit_orders(obs, unit_orders, shadow)
        market = []
        market_tokens = np.full(
            (space.MAX_MARKET_SLOTS,), space.MARKET_INDEX["STOP"], dtype=np.int16
        )
        market_quantities = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
        for slot in range(space.MAX_MARKET_SLOTS):
            slot_output = self._condition_market_output(
                obs, unit_tokens, unit_quantities,
                market_tokens, market_quantities, output
            )
            market_logits = np.asarray(
                slot_output["market_logits"][market_expert, slot]
            ).copy()
            market_logits[space.MARKET_INDEX["STOP"]] += self.market_stop_bias
            token = masked_argmax(market_logits, self._market_legal_mask(obs, shadow))
            market_tokens[slot] = token
            if token == space.MARKET_INDEX["STOP"]:
                break
            quantity_needed = space.MARKET_TOKENS[token] not in {"HIRE", "BUY_LAND"}
            quantity = masked_argmax(
                slot_output["market_quantity_logits"][market_expert, slot],
                self._market_quantity_mask(obs, shadow, token),
            ) if quantity_needed else 0
            market_quantities[slot] = quantity
            order = space.apply_market_token(shadow, token, quantity)
            if order is None:
                break
            market.append(order)
            self.operation_counts[f"market:{order[0]}"] += 1
        return {"farmer": unit_orders[0], "hands": unit_orders[1:], "market": market}

    def sample(
        self, obs, rng: np.random.Generator, worker_temperature: float = 0.2,
        _encoded=None, _output=None,
    ):
        """Sample full actions and retain exact masks/log-probabilities for PPO."""
        if worker_temperature <= 0:
            raise ValueError("worker_temperature must be positive")
        step = int(space.get(obs, "step", 0) or 0)
        if step <= self.last_step:
            self.current_unit_expert = None
            self.unit_expert_usage.clear()
            self.market_expert_usage.clear()
            self.operation_counts.clear()
            self.nonpass_unit_orders = 0
        self.last_step = step
        encoded, output = (
            self._forward(obs) if _encoded is None or _output is None else (_encoded, _output)
        )
        unit_router_probability = jax.nn.softmax(jnp.asarray(output["unit_router_logits"]))
        market_router_probability = jax.nn.softmax(jnp.asarray(output["market_router_logits"]))
        unit_router_mask = float(self.current_unit_expert is None or step % self.router_period == 0)
        scheduled_unit = scheduled_expert(self.unit_expert_schedule, step)
        if scheduled_unit is not None:
            self.current_unit_expert = scheduled_unit
            unit_router_mask = 0.0
        elif self.current_unit_expert is None or step % self.router_period == 0:
            self.current_unit_expert = (
                int(self.forced_unit_expert) if self.forced_unit_expert is not None
                else int(np.argmax(output["unit_router_logits"]))
            )
        unit_expert = self.current_unit_expert
        scheduled_market = scheduled_expert(self.market_expert_schedule, step)
        market_expert = (
            scheduled_market if scheduled_market is not None else (
                unit_expert if self.coupled_product_router else (
                    int(self.forced_market_expert) if self.forced_market_expert is not None
                    else int(np.argmax(output["market_router_logits"]))
                )
            )
        )
        unit_router_logprob = float(np.log(max(1e-30, float(unit_router_probability[unit_expert]))))
        market_router_logprob = float(np.log(max(1e-30, float(market_router_probability[market_expert]))))
        self.unit_expert_usage[unit_expert] += 1
        self.market_expert_usage[market_expert] += 1

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
            unit_output = self._condition_unit_output(
                obs, unit_tokens, unit_quantities, output
            )
            legal = self._unit_legal_mask(obs, unit_index, unit_output)
            token, logprob, _ = _masked_choice(
                unit_output["unit_logits"][unit_expert, unit_index] / worker_temperature,
                legal, rng, False,
            )
            quantity_needed = space.UNIT_TOKENS[token].startswith("PICKUP:") or space.UNIT_TOKENS[token].startswith("PLACE:")
            quantity_legal = np.asarray(space.unit_quantity_mask(obs, unit_index, token), dtype=bool)
            quantity, quantity_logprob, _ = _masked_choice(
                unit_output["unit_quantity_logits"][unit_expert, unit_index] / worker_temperature,
                quantity_legal, rng, False,
            ) if quantity_needed else (0, 0.0, 0.0)
            order = space.decode_unit(obs, unit_index, token, quantity)
            unit_orders.append(order)
            self.operation_counts[f"unit:{order[0]}"] += 1
            self.nonpass_unit_orders += int(order[0] != "PASS")
            unit_tokens[unit_index] = token
            unit_quantities[unit_index] = quantity
            unit_masks[unit_index] = legal
            unit_logprobs[unit_index] = logprob
            unit_quantity_logprobs[unit_index] = quantity_logprob
            unit_quantity_mask[unit_index] = float(quantity_needed)
            unit_quantity_masks[unit_index] = quantity_legal

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
            slot_output = self._condition_market_output(
                obs, unit_tokens, unit_quantities,
                market_tokens, market_quantities, output
            )
            legal = self._market_legal_mask(obs, shadow)
            logits = np.asarray(slot_output["market_logits"][market_expert, slot]).copy()
            logits[space.MARKET_INDEX["STOP"]] += self.market_stop_bias
            token, logprob, _ = _masked_choice(logits / worker_temperature, legal, rng, False)
            market_tokens[slot] = token
            market_masks[slot] = legal
            market_slot_mask[slot] = 1.0
            market_logprobs[slot] = logprob
            if token == space.MARKET_INDEX["STOP"]:
                break
            quantity_needed = space.MARKET_TOKENS[token] not in {"HIRE", "BUY_LAND"}
            quantity_legal = self._market_quantity_mask(obs, shadow, token)
            quantity, quantity_logprob, _ = _masked_choice(
                slot_output["market_quantity_logits"][market_expert, slot] / worker_temperature,
                quantity_legal, rng, False,
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
        trace = {
            **encoded, "unit_expert": np.int16(unit_expert), "market_expert": np.int16(market_expert),
            "unit_router_mask": np.float32(unit_router_mask), "market_router_mask": np.float32(1.0),
            "unit_router_logprob": np.float32(unit_router_logprob),
            "market_router_logprob": np.float32(market_router_logprob),
            "unit_tokens": unit_tokens, "unit_quantities": unit_quantities,
            "unit_action_masks": unit_masks, "unit_logprobs": unit_logprobs,
            "unit_quantity_logprobs": unit_quantity_logprobs,
            "unit_quantity_mask": unit_quantity_mask, "unit_quantity_masks": unit_quantity_masks,
            "market_tokens": market_tokens, "market_quantities": market_quantities,
            "market_action_masks": market_masks, "market_slot_mask": market_slot_mask,
            "market_logprobs": market_logprobs,
            "market_quantity_logprobs": market_quantity_logprobs,
            "market_quantity_mask": market_quantity_mask, "market_quantity_masks": market_quantity_masks,
            "value_prediction": np.float32(output["value"]),
        }
        return {"farmer": unit_orders[0], "hands": unit_orders[1:], "market": market}, trace

    def __call__(self, obs, configuration=None):
        return self.act(obs)
