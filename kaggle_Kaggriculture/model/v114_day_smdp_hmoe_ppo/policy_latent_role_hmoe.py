"""Deterministic inference for V114's causal latent-role HMoE.

The option is fixed for a complete episode.  Every unit and market action is
decoded after re-running the model with the already executed, legality-masked
prefix.  Teacher role labels are never supplied at inference time and no
historical policy can provide an action fallback.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Mapping

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
import features  # noqa: E402
from model_latent_role_hmoe import (  # noqa: E402
    NUM_MARKET_ROLES,
    NUM_OPTIONS,
    NUM_UNIT_ROLES,
    LatentRoleHMoE,
)
from policy_factorized import FactorizedV113Policy, masked_argmax  # noqa: E402
from policy_v114 import observation_step, reserve_shadow, with_observation_step  # noqa: E402


def _option_slot(
    output: Mapping[str, np.ndarray], key: str, option_id: int, slot: int,
) -> np.ndarray:
    """Select one ``[option, slot, ...]`` row from a model output."""

    values = np.asarray(output[key])
    if values.ndim < 2 or values.shape[0] != NUM_OPTIONS:
        raise ValueError(f"{key} must start with [option, slot], got {values.shape}")
    if not 0 <= int(slot) < values.shape[1]:
        raise ValueError(f"{key} slot {slot} outside shape {values.shape}")
    return values[int(option_id), int(slot)]


def _latent_role(
    output: Mapping[str, np.ndarray], domain: str, option_id: int, slot: int,
) -> int:
    """Read the model-owned latent role for accounting only.

    The selected role is deliberately not returned to the action decoder.  The
    action logits in ``LatentRoleHMoE`` already use the model's soft latent-role
    distribution, so feeding this argmax back would change the trained policy.
    """

    key = f"{domain}_role_logits"
    logits = _option_slot(output, key, option_id, slot)
    expected = NUM_UNIT_ROLES if domain == "unit" else NUM_MARKET_ROLES
    if logits.shape != (expected,):
        raise ValueError(f"{key} role axis must be {(expected,)}, got {logits.shape}")
    return int(np.argmax(logits))


class LatentRoleOptionPolicy(FactorizedV113Policy):
    """Fixed-option, prefix-causal V114 latent-role inference policy."""

    def __init__(
        self,
        checkpoint: Path,
        option_id: int,
        *,
        cash_reserve: float = 0.0,
        worker_cap: int | None = None,
        terminal_buy_cutoff: int | None = None,
    ) -> None:
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        model_id = str(payload.get("model_id", ""))
        if not model_id.startswith("v114_") or "latent_role" not in model_id:
            raise ValueError("checkpoint is not a V114 latent-role model")
        if payload.get("inherits_v113_checkpoint") is not False:
            raise ValueError("V114 latent-role policy may not inherit a V113 checkpoint")
        if payload.get("online_historical_agent_fallback") is not False:
            raise ValueError("V114 latent-role policy forbids historical-agent fallback")
        if payload.get("teacher_role_conditions_action_decoder") is not False:
            raise ValueError("latent-role action decoder must not consume teacher roles")
        if "params" not in payload:
            raise ValueError("V114 latent-role checkpoint is missing params")
        if not 0 <= int(option_id) < NUM_OPTIONS:
            raise ValueError("option_id outside V114 latent-role option catalog")
        if cash_reserve < 0:
            raise ValueError("cash_reserve must be non-negative")
        if terminal_buy_cutoff is not None and terminal_buy_cutoff < 0:
            raise ValueError("terminal_buy_cutoff must be non-negative")

        self.option_id = int(option_id)
        self.cash_reserve = float(cash_reserve)
        self.terminal_buy_cutoff = terminal_buy_cutoff
        self.option_usage = Counter()
        self.unit_role_usage = Counter()
        self.market_role_usage = Counter()
        self.market_sequence_lengths = Counter()
        self.market_turns = 0
        self.ten_slot_market_turns = 0
        super().__init__(checkpoint, router_period=1, scale_worker_cap=worker_cap)

        self.model = LatentRoleHMoE(timed=True)
        # The model call intentionally ends after token/quantity prefixes.  In
        # particular, no unit_teacher_roles or market_teacher_roles are passed.
        self._apply_conditioned = jax.jit(
            lambda params, g, b, u, m, ut, uq, mt, mq: self.model.apply(
                {"params": params}, g, b, u, m, ut, uq, mt, mq
            )
        )

    def _conditioned(
        self,
        obs,
        unit_tokens,
        unit_quantities,
        market_tokens=None,
        market_quantities=None,
    ) -> Mapping[str, np.ndarray]:
        encoded = features.encode_observation(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        if market_tokens is None:
            market_tokens = np.full(
                (space.MAX_MARKET_SLOTS,),
                space.MARKET_INDEX["STOP"],
                dtype=np.int16,
            )
            market_quantities = np.zeros(
                (space.MAX_MARKET_SLOTS,), dtype=np.int16
            )
        output = self._apply_conditioned(
            self.params,
            state["global"],
            state["board"],
            state["units"],
            state["unit_mask"],
            jnp.asarray(unit_tokens)[None],
            jnp.asarray(unit_quantities)[None],
            jnp.asarray(market_tokens)[None],
            jnp.asarray(market_quantities)[None],
        )
        return jax.tree.map(lambda value: np.asarray(value[0]), output)

    def _market_legal_mask(self, obs, shadow):
        spendable = reserve_shadow(shadow, self.cash_reserve)
        legal = np.asarray(super()._market_legal_mask(obs, spendable), dtype=bool)
        if (
            self.terminal_buy_cutoff is not None
            and observation_step(obs) >= self.terminal_buy_cutoff
        ):
            for index, name in enumerate(space.MARKET_TOKENS):
                if name == "HIRE" or name == "BUY_LAND" or name.startswith("BUY_"):
                    legal[index] = False
        legal[space.MARKET_INDEX["STOP"]] = True
        return legal

    def _market_quantity_mask(self, obs, shadow, token):
        name = space.MARKET_TOKENS[int(token)]
        if name.startswith("SELL:"):
            return super()._market_quantity_mask(obs, shadow, token)
        return super()._market_quantity_mask(
            obs, reserve_shadow(shadow, self.cash_reserve), token
        )

    def _reset_episode_counters(self, step: int) -> None:
        if step <= self.last_step:
            self.option_usage.clear()
            self.unit_role_usage.clear()
            self.market_role_usage.clear()
            self.market_sequence_lengths.clear()
            self.operation_counts.clear()
            self.nonpass_unit_orders = 0
            self.market_turns = 0
            self.ten_slot_market_turns = 0
        self.last_step = step

    @property
    def ten_slot_rate(self) -> float:
        return (
            self.ten_slot_market_turns / self.market_turns
            if self.market_turns else 0.0
        )

    def act(self, obs):
        obs = with_observation_step(obs)
        step = observation_step(obs)
        self._reset_episode_counters(step)
        self.option_usage[self.option_id] += 1

        count = min(features.MAX_UNITS, space.unit_count(obs))
        unit_orders = []
        unit_tokens = np.full(
            (features.MAX_UNITS,), space.UNIT_INDEX["PASS"], dtype=np.int16
        )
        unit_quantities = np.zeros((features.MAX_UNITS,), dtype=np.int16)
        for unit_index in range(count):
            # Re-forward from the prefix actually executed by prior units.
            output = self._conditioned(obs, unit_tokens, unit_quantities)
            role = _latent_role(output, "unit", self.option_id, unit_index)
            token = masked_argmax(
                _option_slot(
                    output, "unit_logits", self.option_id, unit_index
                ),
                self._unit_legal_mask(obs, unit_index, output),
            )
            needs_quantity = space.UNIT_TOKENS[token].startswith(
                ("PICKUP:", "PLACE:")
            )
            quantity = (
                masked_argmax(
                    _option_slot(
                        output,
                        "unit_quantity_logits",
                        self.option_id,
                        unit_index,
                    ),
                    space.unit_quantity_mask(obs, unit_index, token),
                )
                if needs_quantity else 0
            )
            unit_tokens[unit_index] = token
            unit_quantities[unit_index] = quantity
            order = space.decode_unit(obs, unit_index, token, quantity)
            unit_orders.append(order)
            self.unit_role_usage[role] += 1
            self.operation_counts[f"unit:{order[0]}"] += 1
            self.nonpass_unit_orders += int(order[0] != "PASS")

        shadow = space.market_shadow(obs)
        space.project_unit_orders(obs, unit_orders, shadow)
        market = []
        market_tokens = np.full(
            (space.MAX_MARKET_SLOTS,),
            space.MARKET_INDEX["STOP"],
            dtype=np.int16,
        )
        market_quantities = np.zeros(
            (space.MAX_MARKET_SLOTS,), dtype=np.int16
        )
        for slot in range(space.MAX_MARKET_SLOTS):
            # Re-forward from legal orders already applied to the shadow state.
            output = self._conditioned(
                obs,
                unit_tokens,
                unit_quantities,
                market_tokens,
                market_quantities,
            )
            role = _latent_role(output, "market", self.option_id, slot)
            token = masked_argmax(
                _option_slot(
                    output, "market_logits", self.option_id, slot
                ),
                self._market_legal_mask(obs, shadow),
            )
            self.market_role_usage[role] += 1
            market_tokens[slot] = token
            if token == space.MARKET_INDEX["STOP"]:
                # STOP is absorbing at the policy boundary: do not run or read
                # any later market slot, even though the model exposes a tail.
                break
            needs_quantity = space.MARKET_TOKENS[token] not in {
                "HIRE", "BUY_LAND"
            }
            quantity = (
                masked_argmax(
                    _option_slot(
                        output,
                        "market_quantity_logits",
                        self.option_id,
                        slot,
                    ),
                    self._market_quantity_mask(obs, shadow, token),
                )
                if needs_quantity else 0
            )
            market_quantities[slot] = quantity
            order = space.apply_market_token(shadow, token, quantity)
            if order is None:
                break
            market.append(order)
            self.operation_counts[f"market:{order[0]}"] += 1

        market_length = len(market)
        self.market_turns += 1
        self.market_sequence_lengths[market_length] += 1
        self.ten_slot_market_turns += int(
            market_length == space.MAX_MARKET_SLOTS
        )
        return {
            "farmer": unit_orders[0],
            "hands": unit_orders[1:],
            "market": market,
        }

    def __call__(self, obs, configuration=None):
        return self.act(obs)


# Stable short alias for evaluators and future PPO rollout workers.
LatentRoleHMoEPolicy = LatentRoleOptionPolicy
