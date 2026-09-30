"""Deterministic executed-prefix policy for V113's joint sequence model."""

from __future__ import annotations

from pathlib import Path

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from model_sequence_action import SequenceActionHMoEActorCritic
from policy_factorized import FactorizedV113Policy


class SequenceActionV113Policy(FactorizedV113Policy):
    def __init__(self, *args, **kwargs):
        checkpoint = args[0] if args else kwargs.get("checkpoint")
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        self.functional_router_contract = payload.get("router_granularity") == "step"
        # Sequence-action experts are supervised with a per-step functional
        # label.  Holding a route for the factorized policy's default 24 steps
        # is therefore a train/deploy protocol mismatch.
        kwargs.setdefault("router_period", 1)
        super().__init__(*args, **kwargs)
        self.model = SequenceActionHMoEActorCritic()
        self._apply = jax.jit(
            lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m)
        )
        self._apply_conditioned = jax.jit(
            lambda params, g, b, u, m, ut, uq, mt, mq: self.model.apply(
                {"params": params}, g, b, u, m, ut, uq, mt, mq,
            )
        )

    def _forward(self, obs):
        encoded, output = super()._forward(obs)
        if not self.functional_router_contract:
            return encoded, output
        step = int(space.get(obs, "step", 0) or 0)
        unit_logits = np.asarray(output["unit_router_logits"]).copy()
        market_logits = np.asarray(output["market_router_logits"]).copy()
        if step < 671:
            unit_logits[[3, 5]] = -1e30
            market_logits[[0, 1, 2, 5]] = -1e30
        else:
            unit_logits[:] = -1e30
            market_logits[:] = -1e30
            unit_logits[5] = 0.0
            market_logits[5] = 0.0
        output["unit_router_logits"] = unit_logits
        output["market_router_logits"] = market_logits
        return encoded, output

    def _conditioned(self, obs, unit_tokens, unit_quantities, market_tokens=None, market_quantities=None):
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
        return jax.tree.map(lambda value: np.asarray(value[0]), output)

    def _condition_unit_output(self, obs, unit_tokens, unit_quantities, output):
        return self._conditioned(obs, unit_tokens, unit_quantities)

    def _condition_market_output(
        self, obs, unit_tokens, unit_quantities,
        market_tokens, market_quantities, output,
    ):
        return self._conditioned(
            obs, unit_tokens, unit_quantities, market_tokens, market_quantities
        )


class TimedSequenceActionV113Policy(SequenceActionV113Policy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = SequenceActionHMoEActorCritic(timed=True)
        self._apply = jax.jit(
            lambda params, g, b, u, m: self.model.apply({"params": params}, g, b, u, m)
        )
        self._apply_conditioned = jax.jit(
            lambda params, g, b, u, m, ut, uq, mt, mq: self.model.apply(
                {"params": params}, g, b, u, m, ut, uq, mt, mq,
            )
        )
