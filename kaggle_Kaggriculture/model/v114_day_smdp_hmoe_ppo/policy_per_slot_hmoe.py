"""Deterministic V114 policy for a fixed option and per-slot role routing.

The policy is deliberately self-contained at inference time: it decodes the
V114 network directly through the canonical V113 codec and never delegates an
action to a historical agent.
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
from policy_factorized import FactorizedV113Policy, masked_argmax  # noqa: E402
from policy_v114 import observation_step, reserve_shadow, with_observation_step  # noqa: E402

try:  # The model and policy are intentionally independently testable.
    from model_per_slot_hmoe import (  # type: ignore  # noqa: E402
        NUM_MARKET_ROLES,
        NUM_OPTIONS,
        NUM_UNIT_ROLES,
        PerSlotOptionRoleHMoE,
    )
except ImportError:  # pragma: no cover - exercised only during parallel scaffolding.
    NUM_OPTIONS = 3
    NUM_UNIT_ROLES = 4
    NUM_MARKET_ROLES = 3
    PerSlotOptionRoleHMoE = None


def _first_output(output: Mapping[str, np.ndarray], names: tuple[str, ...]) -> np.ndarray:
    for name in names:
        if name in output:
            return np.asarray(output[name])
    raise KeyError(f"model output is missing all of {names}")


def _role_logits_for_slot(
    output: Mapping[str, np.ndarray], domain: str, option_id: int, slot: int,
) -> np.ndarray:
    """Read ``[option, slot, role]`` while tolerating role-first tensors."""

    slots = features.MAX_UNITS if domain == "unit" else space.MAX_MARKET_SLOTS
    roles = NUM_UNIT_ROLES if domain == "unit" else NUM_MARKET_ROLES
    values = _first_output(
        output, (f"{domain}_role_logits", f"{domain}_role_router_logits")
    )
    if values.ndim != 3 or values.shape[0] != NUM_OPTIONS:
        raise ValueError(
            f"{domain} role logits must be [option, slot, role] or "
            f"[option, role, slot], got {values.shape}"
        )
    option_values = values[int(option_id)]
    if option_values.shape == (slots, roles):
        return option_values[int(slot)]
    if option_values.shape == (roles, slots):
        return option_values[:, int(slot)]
    raise ValueError(
        f"{domain} role logits have incompatible per-option shape "
        f"{option_values.shape}; expected {(slots, roles)} or {(roles, slots)}"
    )


def _action_logits_for_slot(
    output: Mapping[str, np.ndarray], domain: str, option_id: int,
    role_id: int, slot: int, quantity: bool = False,
) -> np.ndarray:
    """Read the action head selected by the model's per-slot role router.

    ``role_id`` is retained in the policy call contract so role accounting and
    action selection are tied to the same forward pass.  The model has already
    conditioned its shared action head on that role, hence action tensors are
    ``[option, slot, vocab]`` rather than duplicating a head per role.
    """

    key = f"{domain}_{'quantity_' if quantity else ''}logits"
    values = np.asarray(output[key])
    slots = features.MAX_UNITS if domain == "unit" else space.MAX_MARKET_SLOTS
    del role_id
    if values.ndim != 3 or values.shape[0] != NUM_OPTIONS:
        raise ValueError(
            f"{key} must be [option, slot, vocab], got {values.shape}"
        )
    option_values = values[int(option_id)]
    if option_values.shape[0] != slots:
        raise ValueError(f"{key} has incompatible per-option shape {option_values.shape}")
    return option_values[int(slot)]


class PerSlotOptionRolePolicy(FactorizedV113Policy):
    """Fix one slow option, then route and decode each unit/order slot."""

    def __init__(
        self,
        checkpoint: Path,
        option_id: int,
        *,
        cash_reserve: float = 0.0,
        worker_cap: int | None = None,
        terminal_buy_cutoff: int | None = None,
    ):
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        if not str(payload.get("model_id", "")).startswith("v114_"):
            raise ValueError("checkpoint is not registered to V114")
        if payload.get("inherits_v113_checkpoint") is not False:
            raise ValueError("V114 per-slot policy may not inherit a V113 checkpoint")
        if "params" not in payload:
            raise ValueError("V114 checkpoint is missing params")
        if not 0 <= int(option_id) < NUM_OPTIONS:
            raise ValueError("option_id outside V114 option catalog")
        if cash_reserve < 0:
            raise ValueError("cash_reserve must be non-negative")
        if terminal_buy_cutoff is not None and terminal_buy_cutoff < 0:
            raise ValueError("terminal_buy_cutoff must be non-negative")
        if PerSlotOptionRoleHMoE is None:
            raise RuntimeError("model_per_slot_hmoe.PerSlotOptionRoleHMoE is unavailable")

        self.option_id = int(option_id)
        self.cash_reserve = float(cash_reserve)
        self.terminal_buy_cutoff = terminal_buy_cutoff
        self.option_usage = Counter()
        self.unit_role_usage = Counter()
        self.market_role_usage = Counter()
        super().__init__(checkpoint, router_period=1, scale_worker_cap=worker_cap)

        self.model = PerSlotOptionRoleHMoE(timed=True)
        self._apply_conditioned = jax.jit(
            lambda params, g, b, u, m, ut, uq, mt, mq: self.model.apply(
                {"params": params}, g, b, u, m, ut, uq, mt, mq
            )
        )

    def _conditioned(
        self, obs, unit_tokens, unit_quantities,
        market_tokens=None, market_quantities=None,
    ):
        encoded = features.encode_observation(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        if market_tokens is None:
            market_tokens = np.full(
                (space.MAX_MARKET_SLOTS,), space.MARKET_INDEX["STOP"], dtype=np.int16
            )
            market_quantities = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
        output = self._apply_conditioned(
            self.params,
            state["global"], state["board"], state["units"], state["unit_mask"],
            jnp.asarray(unit_tokens)[None], jnp.asarray(unit_quantities)[None],
            jnp.asarray(market_tokens)[None], jnp.asarray(market_quantities)[None],
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
            self.operation_counts.clear()
            self.nonpass_unit_orders = 0
        self.last_step = step

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
            output = self._conditioned(obs, unit_tokens, unit_quantities)
            role = int(np.argmax(_role_logits_for_slot(
                output, "unit", self.option_id, unit_index
            )))
            token = masked_argmax(
                _action_logits_for_slot(
                    output, "unit", self.option_id, role, unit_index
                ),
                self._unit_legal_mask(obs, unit_index, output),
            )
            needs_quantity = space.UNIT_TOKENS[token].startswith(("PICKUP:", "PLACE:"))
            quantity = (
                masked_argmax(
                    _action_logits_for_slot(
                        output, "unit", self.option_id, role, unit_index,
                        quantity=True,
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
            (space.MAX_MARKET_SLOTS,), space.MARKET_INDEX["STOP"], dtype=np.int16
        )
        market_quantities = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
        for slot in range(space.MAX_MARKET_SLOTS):
            output = self._conditioned(
                obs, unit_tokens, unit_quantities, market_tokens, market_quantities
            )
            role = int(np.argmax(_role_logits_for_slot(
                output, "market", self.option_id, slot
            )))
            token = masked_argmax(
                _action_logits_for_slot(
                    output, "market", self.option_id, role, slot
                ),
                self._market_legal_mask(obs, shadow),
            )
            market_tokens[slot] = token
            self.market_role_usage[role] += 1
            if token == space.MARKET_INDEX["STOP"]:
                break
            needs_quantity = space.MARKET_TOKENS[token] not in {"HIRE", "BUY_LAND"}
            quantity = (
                masked_argmax(
                    _action_logits_for_slot(
                        output, "market", self.option_id, role, slot,
                        quantity=True,
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

        return {"farmer": unit_orders[0], "hands": unit_orders[1:], "market": market}

    def __call__(self, obs, configuration=None):
        return self.act(obs)


# Short alias for evaluation scripts.
PerSlotHMoEPolicy = PerSlotOptionRolePolicy
