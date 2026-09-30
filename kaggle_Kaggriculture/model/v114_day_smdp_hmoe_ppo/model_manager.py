"""Day/event-level SMDP Manager for V114 PPO v4."""

from __future__ import annotations

from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np

from critics import (
    Array,
    DEFAULT_VALUE_COEF,
    ManagerCritic,
    ParameterTree,
    assert_same_parameter_schema,
    clone_parameters,
    init_mlp,
    mlp_forward,
    stable_sigmoid,
    validate_value_coef,
)


OPTION_NAMES = (
    "PRODUCTION_LOGISTICS",
    "MARKET_CASH",
    "RECOVERY",
    "TERMINAL_LIQUIDATION",
)
BUDGET_TIERS = ("CONSERVATIVE", "BALANCED", "EXPANSIVE")
RISK_TIERS = ("LOW", "MEDIUM", "HIGH")


class ManagerOutput(NamedTuple):
    option_logits: Array
    budget_logits: Array
    risk_logits: Array
    value: Array
    margin: Array
    catastrophe_logit: Array
    catastrophe_probability: Array


class DaySMDPManager:
    """Minimal trainable Manager with actor heads and an independent V_manager."""

    def __init__(
        self,
        input_dim: int,
        *,
        num_options: int = len(OPTION_NAMES),
        num_budget_tiers: int = len(BUDGET_TIERS),
        num_risk_tiers: int = len(RISK_TIERS),
        hidden_dims: Sequence[int] = (128, 64),
        seed: int = 1140,
        value_coef: float = DEFAULT_VALUE_COEF,
    ) -> None:
        self.input_dim = int(input_dim)
        self.num_options = int(num_options)
        self.num_budget_tiers = int(num_budget_tiers)
        self.num_risk_tiers = int(num_risk_tiers)
        self.hidden_dims = tuple(int(dim) for dim in hidden_dims)
        self.value_coef = validate_value_coef(value_coef)
        dimensions = (
            self.input_dim,
            self.num_options,
            self.num_budget_tiers,
            self.num_risk_tiers,
            *self.hidden_dims,
        )
        if any(dim <= 0 for dim in dimensions):
            raise ValueError("manager dimensions must be positive")

        rng = np.random.default_rng(seed)
        latent_dim = self.hidden_dims[-1]
        self._critic = ManagerCritic(
            self.input_dim,
            hidden_dims=self.hidden_dims,
            seed=seed + 1,
            value_coef=self.value_coef,
        )
        self.parameters: ParameterTree = {
            "actor_encoder": init_mlp(self.input_dim, self.hidden_dims, rng),
            "option_head": init_mlp(latent_dim, (self.num_options,), rng),
            "budget_head": init_mlp(latent_dim, (self.num_budget_tiers,), rng),
            "risk_head": init_mlp(latent_dim, (self.num_risk_tiers,), rng),
            "V_manager": self._critic.state_dict(),
        }

    def __call__(
        self, state_features: Array, parameters: Mapping[str, Any] | None = None
    ) -> ManagerOutput:
        params = self.parameters if parameters is None else parameters
        state_features = np.asarray(state_features, dtype=np.float32)
        if state_features.ndim != 2 or state_features.shape[-1] != self.input_dim:
            raise ValueError(
                f"manager expects [batch, {self.input_dim}], got {state_features.shape}"
            )
        latent = mlp_forward(
            params["actor_encoder"], state_features, activate_final=True
        )
        option_logits = mlp_forward(params["option_head"], latent)
        budget_logits = mlp_forward(params["budget_head"], latent)
        risk_logits = mlp_forward(params["risk_head"], latent)

        critic = self._critic(state_features, params["V_manager"])
        return ManagerOutput(
            option_logits=option_logits,
            budget_logits=budget_logits,
            risk_logits=risk_logits,
            value=critic.value,
            margin=critic.margin,
            catastrophe_logit=critic.catastrophe_logit,
            catastrophe_probability=stable_sigmoid(critic.catastrophe_logit),
        )

    def state_dict(self) -> ParameterTree:
        return clone_parameters(self.parameters)

    def load_state_dict(self, parameters: Mapping[str, Any]) -> None:
        assert_same_parameter_schema(self.parameters, parameters, "manager")
        self.parameters = clone_parameters(parameters)
        self._critic.load_state_dict(self.parameters["V_manager"])


__all__ = [
    "BUDGET_TIERS",
    "DaySMDPManager",
    "ManagerOutput",
    "OPTION_NAMES",
    "RISK_TIERS",
]
