"""Deterministic V114 policy for a fixed high-level option and routed roles."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

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
from policy_factorized import FactorizedV113Policy  # noqa: E402
from model_nested_hmoe import NUM_OPTIONS, NestedOptionRoleHMoE  # noqa: E402
from policy_v114 import observation_step, reserve_shadow, with_observation_step  # noqa: E402


class NestedOptionRolePolicy(FactorizedV113Policy):
    """Run one coherent option while role routers switch functional workers each step."""

    def __init__(
        self, checkpoint: Path, option_id: int, *,
        forced_unit_role: int | None = None, forced_market_role: int | None = None,
        cash_reserve: float = 0.0, worker_cap: int | None = None,
        terminal_buy_cutoff: int | None = None,
    ):
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        if payload.get("model_id") != "v114_day_smdp_hmoe_ppo_nested_bc_v1":
            raise ValueError("checkpoint is not a registered V114 nested HMoE")
        if payload.get("inherits_v113_checkpoint") is not False:
            raise ValueError("V114 nested policy may not inherit a V113 checkpoint")
        if not 0 <= int(option_id) < NUM_OPTIONS:
            raise ValueError("option_id outside V114 option catalog")
        if cash_reserve < 0:
            raise ValueError("cash_reserve must be non-negative")
        self.option_id = int(option_id)
        self.cash_reserve = float(cash_reserve)
        self.terminal_buy_cutoff = terminal_buy_cutoff
        self.option_usage = Counter()
        super().__init__(
            checkpoint,
            forced_unit_expert=forced_unit_role,
            forced_market_expert=forced_market_role,
            router_period=1,
            scale_worker_cap=worker_cap,
        )
        self.model = NestedOptionRoleHMoE(timed=True)
        self._apply = jax.jit(
            lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m)
        )
        self._apply_conditioned = jax.jit(
            lambda params, g, b, u, m, ut, uq, mt, mq: self.model.apply(
                {"params": params}, g, b, u, m, ut, uq, mt, mq
            )
        )

    def _select_option(self, output):
        option = self.option_id
        selected = dict(output)
        selected["unit_router_logits"] = output["unit_role_router_logits"][option]
        selected["market_router_logits"] = output["market_role_router_logits"][option]
        selected["unit_logits"] = output["unit_logits"][option]
        selected["unit_quantity_logits"] = output["unit_quantity_logits"][option]
        selected["market_logits"] = output["market_logits"][option]
        selected["market_quantity_logits"] = output["market_quantity_logits"][option]
        selected["value"] = output["option_value"][option]
        return selected

    def _forward(self, obs):
        encoded = features.encode_observation(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        output = self._apply(
            self.params, state["global"], state["board"], state["units"], state["unit_mask"]
        )
        selected = self._select_option(jax.tree.map(lambda value: np.asarray(value[0]), output))
        self.option_usage[self.option_id] += 1
        return encoded, selected

    def _conditioned(
        self, obs, unit_tokens, unit_quantities,
        market_tokens=None, market_quantities=None,
    ):
        encoded = features.encode_observation(obs)
        state = {key: jnp.asarray(value)[None] for key, value in encoded.items()}
        if market_tokens is None:
            market_tokens = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
            market_quantities = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.int16)
        output = self._apply_conditioned(
            self.params, state["global"], state["board"], state["units"], state["unit_mask"],
            jnp.asarray(unit_tokens)[None], jnp.asarray(unit_quantities)[None],
            jnp.asarray(market_tokens)[None], jnp.asarray(market_quantities)[None],
        )
        return self._select_option(jax.tree.map(lambda value: np.asarray(value[0]), output))

    def _condition_unit_output(self, obs, unit_tokens, unit_quantities, output):
        return self._conditioned(obs, unit_tokens, unit_quantities)

    def _condition_market_output(
        self, obs, unit_tokens, unit_quantities, market_tokens, market_quantities, output,
    ):
        return self._conditioned(
            obs, unit_tokens, unit_quantities, market_tokens, market_quantities
        )

    def _market_legal_mask(self, obs, shadow):
        legal = np.asarray(super()._market_legal_mask(obs, reserve_shadow(shadow, self.cash_reserve)))
        if self.terminal_buy_cutoff is not None and observation_step(obs) >= self.terminal_buy_cutoff:
            for index, name in enumerate(space.MARKET_TOKENS):
                if name == "HIRE" or name == "BUY_LAND" or name.startswith("BUY_"):
                    legal[index] = False
        legal[space.MARKET_INDEX["STOP"]] = True
        return legal

    def _market_quantity_mask(self, obs, shadow, token):
        name = space.MARKET_TOKENS[int(token)]
        if name.startswith("SELL:"):
            return super()._market_quantity_mask(obs, shadow, token)
        return super()._market_quantity_mask(obs, reserve_shadow(shadow, self.cash_reserve), token)

    def act(self, obs):
        return super().act(with_observation_step(obs))

    def sample(self, obs, *args, **kwargs):
        return super().sample(with_observation_step(obs), *args, **kwargs)
