"""Independent low-level expert adapters for V114 PPO v4."""

from __future__ import annotations

from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np

from critics import (
    Array,
    DEFAULT_VALUE_COEF,
    OptionCritic,
    ParameterTree,
    assert_same_parameter_schema,
    clone_parameters,
    init_mlp,
    mlp_forward,
    validate_value_coef,
)


class ExpertState(NamedTuple):
    """Expert-private recurrent state; never shared across adapters."""

    memory: Array


class ExpertOutput(NamedTuple):
    unit_logits: Array
    market_logits: Array
    next_state: ExpertState
    value: Array
    margin: Array
    catastrophe_logit: Array
    catastrophe_probability: Array


class ExpertAdapter:
    """Trainable turn-level adapter with private memory and V_option."""

    role = "EXPERT"

    def __init__(
        self,
        input_dim: int,
        unit_feature_dim: int,
        market_feature_dim: int,
        num_unit_actions: int,
        num_market_actions: int,
        *,
        state_dim: int = 32,
        hidden_dims: Sequence[int] = (96, 64),
        seed: int = 0,
        value_coef: float = DEFAULT_VALUE_COEF,
    ) -> None:
        self.input_dim = int(input_dim)
        self.unit_feature_dim = int(unit_feature_dim)
        self.market_feature_dim = int(market_feature_dim)
        self.num_unit_actions = int(num_unit_actions)
        self.num_market_actions = int(num_market_actions)
        self.state_dim = int(state_dim)
        self.hidden_dims = tuple(int(dim) for dim in hidden_dims)
        self.value_coef = validate_value_coef(value_coef)
        dimensions = (
            self.input_dim,
            self.unit_feature_dim,
            self.market_feature_dim,
            self.num_unit_actions,
            self.num_market_actions,
            self.state_dim,
            *self.hidden_dims,
        )
        if any(dim <= 0 for dim in dimensions):
            raise ValueError("expert dimensions must be positive")

        rng = np.random.default_rng(seed)
        latent_dim = self.hidden_dims[-1]
        context_dim = latent_dim + self.state_dim
        self._critic = OptionCritic(
            context_dim,
            hidden_dims=(64, 32),
            seed=seed + 1,
            value_coef=self.value_coef,
        )
        self.parameters: ParameterTree = {
            "observation_encoder": init_mlp(
                self.input_dim, self.hidden_dims, rng
            ),
            "state_update": init_mlp(
                latent_dim + self.state_dim, (self.state_dim,), rng
            ),
            "unit_adapter": init_mlp(
                context_dim + self.unit_feature_dim,
                (64, self.num_unit_actions),
                rng,
            ),
            "market_adapter": init_mlp(
                context_dim + self.market_feature_dim,
                (64, self.num_market_actions),
                rng,
            ),
            "V_option": self._critic.state_dict(),
        }

    def initial_state(self, batch_size: int) -> ExpertState:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        return ExpertState(
            memory=np.zeros((int(batch_size), self.state_dim), dtype=np.float32)
        )

    def __call__(
        self,
        state_features: Array,
        unit_features: Array,
        market_features: Array,
        expert_state: ExpertState,
        parameters: Mapping[str, Any] | None = None,
    ) -> ExpertOutput:
        params = self.parameters if parameters is None else parameters
        state_features = np.asarray(state_features, dtype=np.float32)
        unit_features = np.asarray(unit_features, dtype=np.float32)
        market_features = np.asarray(market_features, dtype=np.float32)
        memory = np.asarray(expert_state.memory, dtype=np.float32)
        if state_features.ndim != 2 or state_features.shape[-1] != self.input_dim:
            raise ValueError(
                f"{self.role} expects state [batch, {self.input_dim}]"
            )
        batch_size = state_features.shape[0]
        if memory.shape != (batch_size, self.state_dim):
            raise ValueError(
                f"{self.role} memory must be {(batch_size, self.state_dim)}"
            )
        if unit_features.ndim != 3 or unit_features.shape[0] != batch_size:
            raise ValueError(f"{self.role} unit features must be rank 3")
        if unit_features.shape[-1] != self.unit_feature_dim:
            raise ValueError(f"{self.role} unit feature dimension mismatch")
        if market_features.ndim != 3 or market_features.shape[0] != batch_size:
            raise ValueError(f"{self.role} market features must be rank 3")
        if market_features.shape[-1] != self.market_feature_dim:
            raise ValueError(f"{self.role} market feature dimension mismatch")

        observation_latent = mlp_forward(
            params["observation_encoder"], state_features, activate_final=True
        )
        next_memory = mlp_forward(
            params["state_update"],
            np.concatenate((observation_latent, memory), axis=-1),
            activate_final=True,
        )
        context = np.concatenate((observation_latent, next_memory), axis=-1)

        unit_count = unit_features.shape[1]
        unit_context = np.broadcast_to(
            context[:, None, :], (batch_size, unit_count, context.shape[-1])
        )
        unit_inputs = np.concatenate((unit_context, unit_features), axis=-1)
        unit_logits = mlp_forward(
            params["unit_adapter"],
            unit_inputs.reshape((-1, unit_inputs.shape[-1])),
        ).reshape((batch_size, unit_count, self.num_unit_actions))

        market_count = market_features.shape[1]
        market_context = np.broadcast_to(
            context[:, None, :],
            (batch_size, market_count, context.shape[-1]),
        )
        market_inputs = np.concatenate((market_context, market_features), axis=-1)
        market_logits = mlp_forward(
            params["market_adapter"],
            market_inputs.reshape((-1, market_inputs.shape[-1])),
        ).reshape((batch_size, market_count, self.num_market_actions))

        critic = self._critic(context, params["V_option"])
        return ExpertOutput(
            unit_logits=unit_logits,
            market_logits=market_logits,
            next_state=ExpertState(memory=next_memory),
            value=critic.value,
            margin=critic.margin,
            catastrophe_logit=critic.catastrophe_logit,
            catastrophe_probability=critic.catastrophe_probability,
        )

    def state_dict(self) -> ParameterTree:
        return clone_parameters(self.parameters)

    def load_state_dict(self, parameters: Mapping[str, Any]) -> None:
        assert_same_parameter_schema(self.parameters, parameters, self.role)
        self.parameters = clone_parameters(parameters)
        self._critic.load_state_dict(self.parameters["V_option"])


class ProductionLogisticsExpert(ExpertAdapter):
    """Independent production and logistics policy adapter."""

    role = "PRODUCTION_LOGISTICS"


class MarketCashExpert(ExpertAdapter):
    """Independent market and cash-management policy adapter."""

    role = "MARKET_CASH"


class IndependentExpertAdapters:
    """Container that enforces distinct parameters and recurrent states."""

    def __init__(
        self,
        input_dim: int,
        unit_feature_dim: int,
        market_feature_dim: int,
        num_unit_actions: int,
        num_market_actions: int,
        *,
        state_dim: int = 32,
        hidden_dims: Sequence[int] = (96, 64),
        seed: int = 1142,
        value_coef: float = DEFAULT_VALUE_COEF,
    ) -> None:
        value_coef = validate_value_coef(value_coef)
        self.production_logistics = ProductionLogisticsExpert(
            input_dim,
            unit_feature_dim,
            market_feature_dim,
            num_unit_actions,
            num_market_actions,
            state_dim=state_dim,
            hidden_dims=hidden_dims,
            seed=seed,
            value_coef=value_coef,
        )
        self.market_cash = MarketCashExpert(
            input_dim,
            unit_feature_dim,
            market_feature_dim,
            num_unit_actions,
            num_market_actions,
            state_dim=state_dim,
            hidden_dims=hidden_dims,
            seed=seed + 10_000,
            value_coef=value_coef,
        )

    def initial_states(self, batch_size: int) -> dict[str, ExpertState]:
        return {
            "production_logistics": self.production_logistics.initial_state(
                batch_size
            ),
            "market_cash": self.market_cash.initial_state(batch_size),
        }

    def __call__(
        self,
        state_features: Array,
        unit_features: Array,
        market_features: Array,
        states: Mapping[str, ExpertState],
    ) -> dict[str, ExpertOutput]:
        return {
            "production_logistics": self.production_logistics(
                state_features,
                unit_features,
                market_features,
                states["production_logistics"],
            ),
            "market_cash": self.market_cash(
                state_features,
                unit_features,
                market_features,
                states["market_cash"],
            ),
        }

    def state_dict(self) -> ParameterTree:
        return {
            "production_logistics": self.production_logistics.state_dict(),
            "market_cash": self.market_cash.state_dict(),
        }

    def load_state_dict(self, parameters: Mapping[str, Any]) -> None:
        if set(parameters) != {"production_logistics", "market_cash"}:
            raise ValueError("expert checkpoint must contain both expert scopes")
        self.production_logistics.load_state_dict(
            parameters["production_logistics"]
        )
        self.market_cash.load_state_dict(parameters["market_cash"])


__all__ = [
    "ExpertAdapter",
    "ExpertOutput",
    "ExpertState",
    "IndependentExpertAdapters",
    "MarketCashExpert",
    "ProductionLogisticsExpert",
]
