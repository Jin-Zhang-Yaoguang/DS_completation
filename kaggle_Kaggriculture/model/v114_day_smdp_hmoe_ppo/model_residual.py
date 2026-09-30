"""Bounded unit/market Residual PPO interface for V114."""

from __future__ import annotations

from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np

from critics import (
    Array,
    DEFAULT_VALUE_COEF,
    ParameterTree,
    ResidualCritic,
    assert_same_parameter_schema,
    clone_parameters,
    init_mlp,
    mlp_forward,
    validate_value_coef,
)


UNIT_RESIDUAL_ACTIONS = (
    "KEEP",
    "REASSIGN_ONE_IDLE_UNIT",
    "TERMINAL_RETURN_OR_SELL",
)
MARKET_RESIDUAL_ACTIONS = (
    "KEEP",
    "MARKET_QTY_UP_1",
    "MARKET_QTY_DOWN_1",
    "DEFER_ONE_MARKET_ORDER",
    "ADVANCE_ONE_SELL",
    "CASH_TIER_UP_1",
    "CASH_TIER_DOWN_1",
    "TERMINAL_RETURN_OR_SELL",
)
MAX_NON_KEEP_PER_DAY = 4


class ResidualOutput(NamedTuple):
    unit_logits: Array
    market_logits: Array
    value: Array
    margin: Array
    catastrophe_logit: Array
    catastrophe_probability: Array


class BoundedResidualActorCritic:
    """Independent unit/market actor branches plus V_residual.

    The model only proposes residual tokens.  Daily modification limits and
    legality fallback remain the safety executor's responsibility.
    """

    def __init__(
        self,
        input_dim: int,
        unit_feature_dim: int,
        market_feature_dim: int,
        *,
        num_unit_actions: int = len(UNIT_RESIDUAL_ACTIONS),
        num_market_actions: int = len(MARKET_RESIDUAL_ACTIONS),
        hidden_dims: Sequence[int] = (96, 64),
        branch_hidden_dim: int = 48,
        seed: int = 1144,
        value_coef: float = DEFAULT_VALUE_COEF,
    ) -> None:
        self.input_dim = int(input_dim)
        self.unit_feature_dim = int(unit_feature_dim)
        self.market_feature_dim = int(market_feature_dim)
        self.num_unit_actions = int(num_unit_actions)
        self.num_market_actions = int(num_market_actions)
        self.hidden_dims = tuple(int(dim) for dim in hidden_dims)
        self.branch_hidden_dim = int(branch_hidden_dim)
        self.value_coef = validate_value_coef(value_coef)
        dimensions = (
            self.input_dim,
            self.unit_feature_dim,
            self.market_feature_dim,
            self.num_unit_actions,
            self.num_market_actions,
            self.branch_hidden_dim,
            *self.hidden_dims,
        )
        if any(dim <= 0 for dim in dimensions):
            raise ValueError("residual dimensions must be positive")

        rng = np.random.default_rng(seed)
        latent_dim = self.hidden_dims[-1]
        self._critic = ResidualCritic(
            self.input_dim,
            hidden_dims=self.hidden_dims,
            seed=seed + 1,
            value_coef=self.value_coef,
        )
        self.parameters: ParameterTree = {
            "context_encoder": init_mlp(
                self.input_dim, self.hidden_dims, rng
            ),
            "unit_branch": init_mlp(
                latent_dim + self.unit_feature_dim,
                (self.branch_hidden_dim, self.num_unit_actions),
                rng,
            ),
            "market_branch": init_mlp(
                latent_dim + self.market_feature_dim,
                (self.branch_hidden_dim, self.num_market_actions),
                rng,
            ),
            "V_residual": self._critic.state_dict(),
        }

    def __call__(
        self,
        state_features: Array,
        unit_features: Array,
        market_features: Array,
        parameters: Mapping[str, Any] | None = None,
    ) -> ResidualOutput:
        params = self.parameters if parameters is None else parameters
        state_features = np.asarray(state_features, dtype=np.float32)
        unit_features = np.asarray(unit_features, dtype=np.float32)
        market_features = np.asarray(market_features, dtype=np.float32)
        if state_features.ndim != 2 or state_features.shape[-1] != self.input_dim:
            raise ValueError(
                f"residual expects [batch, {self.input_dim}], got {state_features.shape}"
            )
        batch_size = state_features.shape[0]
        if (
            unit_features.ndim != 3
            or unit_features.shape[0] != batch_size
            or unit_features.shape[-1] != self.unit_feature_dim
        ):
            raise ValueError("unit feature shape mismatch")
        if (
            market_features.ndim != 3
            or market_features.shape[0] != batch_size
            or market_features.shape[-1] != self.market_feature_dim
        ):
            raise ValueError("market feature shape mismatch")

        context = mlp_forward(
            params["context_encoder"], state_features, activate_final=True
        )
        unit_count = unit_features.shape[1]
        unit_context = np.broadcast_to(
            context[:, None, :], (batch_size, unit_count, context.shape[-1])
        )
        unit_inputs = np.concatenate((unit_context, unit_features), axis=-1)
        unit_logits = mlp_forward(
            params["unit_branch"],
            unit_inputs.reshape((-1, unit_inputs.shape[-1])),
        ).reshape((batch_size, unit_count, self.num_unit_actions))

        market_count = market_features.shape[1]
        market_context = np.broadcast_to(
            context[:, None, :],
            (batch_size, market_count, context.shape[-1]),
        )
        market_inputs = np.concatenate((market_context, market_features), axis=-1)
        market_logits = mlp_forward(
            params["market_branch"],
            market_inputs.reshape((-1, market_inputs.shape[-1])),
        ).reshape((batch_size, market_count, self.num_market_actions))

        critic = self._critic(state_features, params["V_residual"])
        return ResidualOutput(
            unit_logits=unit_logits,
            market_logits=market_logits,
            value=critic.value,
            margin=critic.margin,
            catastrophe_logit=critic.catastrophe_logit,
            catastrophe_probability=critic.catastrophe_probability,
        )

    def state_dict(self) -> ParameterTree:
        return clone_parameters(self.parameters)

    def load_state_dict(self, parameters: Mapping[str, Any]) -> None:
        assert_same_parameter_schema(self.parameters, parameters, "residual")
        self.parameters = clone_parameters(parameters)
        self._critic.load_state_dict(self.parameters["V_residual"])


__all__ = [
    "BoundedResidualActorCritic",
    "MARKET_RESIDUAL_ACTIONS",
    "MAX_NON_KEEP_PER_DAY",
    "ResidualOutput",
    "UNIT_RESIDUAL_ACTIONS",
]
