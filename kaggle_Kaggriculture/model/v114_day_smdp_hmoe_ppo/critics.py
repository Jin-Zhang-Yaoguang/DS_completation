"""NumPy critic primitives for V114 PPO v4.

V4-0 intentionally keeps parameters as explicit nested dictionaries.  The
runtime used by the experiment does not currently provide JAX/Flax, while the
dictionary contract remains directly convertible to either framework later.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, Mapping, NamedTuple, Sequence

import numpy as np


Array = np.ndarray
ParameterTree = dict[str, Any]
DEFAULT_VALUE_COEF = 0.5


class CriticOutput(NamedTuple):
    """Value and calibrated catastrophe estimate for one critic scope."""

    value: Array
    margin: Array
    catastrophe_logit: Array
    catastrophe_probability: Array


def validate_value_coef(value_coef: float) -> float:
    """Reject the Stage37 failure mode where the value loss was disabled."""

    value_coef = float(value_coef)
    if not np.isfinite(value_coef) or value_coef <= 0.0:
        raise ValueError("value_coef must be finite and strictly positive")
    return value_coef


def _xavier(rng: np.random.Generator, fan_in: int, fan_out: int) -> Array:
    limit = np.sqrt(6.0 / float(fan_in + fan_out))
    return rng.uniform(-limit, limit, size=(fan_in, fan_out)).astype(np.float32)


def init_mlp(
    input_dim: int,
    layer_dims: Sequence[int],
    rng: np.random.Generator,
) -> ParameterTree:
    """Create a trainable MLP parameter dictionary."""

    if input_dim <= 0 or not layer_dims or any(dim <= 0 for dim in layer_dims):
        raise ValueError("all MLP dimensions must be positive")
    params: ParameterTree = {}
    fan_in = int(input_dim)
    for index, fan_out in enumerate(layer_dims):
        params[f"layer_{index}"] = {
            "weight": _xavier(rng, fan_in, int(fan_out)),
            "bias": np.zeros((int(fan_out),), dtype=np.float32),
        }
        fan_in = int(fan_out)
    return params


def mlp_forward(
    parameters: Mapping[str, Mapping[str, Array]],
    inputs: Array,
    *,
    activate_final: bool = False,
) -> Array:
    """Run an MLP with tanh hidden activations."""

    result = np.asarray(inputs, dtype=np.float32)
    layer_count = len(parameters)
    for index in range(layer_count):
        layer = parameters[f"layer_{index}"]
        result = result @ layer["weight"] + layer["bias"]
        if activate_final or index + 1 < layer_count:
            result = np.tanh(result)
    return result


def stable_sigmoid(logits: Array) -> Array:
    """Numerically stable sigmoid that preserves float32 output."""

    logits = np.asarray(logits, dtype=np.float32)
    positive = logits >= 0
    result = np.empty_like(logits)
    result[positive] = 1.0 / (1.0 + np.exp(-logits[positive]))
    exp_logits = np.exp(logits[~positive])
    result[~positive] = exp_logits / (1.0 + exp_logits)
    return result


def clone_parameters(tree: Mapping[str, Any]) -> ParameterTree:
    """Deep-copy an array-only parameter tree."""

    cloned: ParameterTree = {}
    for key, value in tree.items():
        if isinstance(value, Mapping):
            cloned[key] = clone_parameters(value)
        else:
            cloned[key] = np.asarray(value).copy()
    return cloned


def _flatten_parameters(
    tree: Mapping[str, Any], prefix: str = ""
) -> dict[str, Array]:
    flattened: dict[str, Array] = {}
    for key, value in tree.items():
        path = f"{prefix}/{key}" if prefix else key
        if isinstance(value, Mapping):
            flattened.update(_flatten_parameters(value, path))
        else:
            flattened[path] = np.asarray(value)
    return flattened


def serialize_parameters(tree: Mapping[str, Any]) -> bytes:
    """Serialize an array-only tree without pickle."""

    buffer = BytesIO()
    np.savez_compressed(buffer, **_flatten_parameters(tree))
    return buffer.getvalue()


def deserialize_parameters(payload: bytes) -> ParameterTree:
    """Restore a tree created by :func:`serialize_parameters`."""

    root: ParameterTree = {}
    with np.load(BytesIO(payload), allow_pickle=False) as archive:
        for path in archive.files:
            cursor = root
            parts = path.split("/")
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[parts[-1]] = np.asarray(archive[path]).copy()
    return root


def assert_same_parameter_schema(
    expected: Mapping[str, Any], candidate: Mapping[str, Any], path: str = "params"
) -> None:
    """Validate keys, array shapes and dtypes before loading a checkpoint."""

    if set(expected) != set(candidate):
        raise ValueError(f"parameter keys differ at {path}")
    for key in expected:
        expected_value = expected[key]
        candidate_value = candidate[key]
        child_path = f"{path}/{key}"
        if isinstance(expected_value, Mapping):
            if not isinstance(candidate_value, Mapping):
                raise ValueError(f"expected mapping at {child_path}")
            assert_same_parameter_schema(expected_value, candidate_value, child_path)
        else:
            expected_array = np.asarray(expected_value)
            candidate_array = np.asarray(candidate_value)
            if expected_array.shape != candidate_array.shape:
                raise ValueError(f"parameter shape differs at {child_path}")
            if expected_array.dtype != candidate_array.dtype:
                raise ValueError(f"parameter dtype differs at {child_path}")


class CatastropheValueCritic:
    """Shared implementation; concrete subclasses define independent scopes."""

    scope = "V"

    def __init__(
        self,
        input_dim: int,
        hidden_dims: Sequence[int] = (64, 32),
        *,
        seed: int = 0,
        value_coef: float = DEFAULT_VALUE_COEF,
    ) -> None:
        self.input_dim = int(input_dim)
        self.hidden_dims = tuple(int(dim) for dim in hidden_dims)
        self.value_coef = validate_value_coef(value_coef)
        if self.input_dim <= 0 or not self.hidden_dims:
            raise ValueError("critic dimensions must be positive")
        rng = np.random.default_rng(seed)
        latent_dim = self.hidden_dims[-1]
        self.parameters: ParameterTree = {
            "trunk": init_mlp(self.input_dim, self.hidden_dims, rng),
            "value_head": init_mlp(latent_dim, (1,), rng),
            "margin_head": init_mlp(latent_dim, (1,), rng),
            "catastrophe_head": init_mlp(latent_dim, (1,), rng),
        }

    def __call__(
        self, inputs: Array, parameters: Mapping[str, Any] | None = None
    ) -> CriticOutput:
        params = self.parameters if parameters is None else parameters
        inputs = np.asarray(inputs, dtype=np.float32)
        if inputs.ndim != 2 or inputs.shape[-1] != self.input_dim:
            raise ValueError(
                f"{self.scope} expects [batch, {self.input_dim}], got {inputs.shape}"
            )
        latent = mlp_forward(params["trunk"], inputs, activate_final=True)
        value = mlp_forward(params["value_head"], latent)[..., 0]
        margin = mlp_forward(params["margin_head"], latent)[..., 0]
        catastrophe_logit = mlp_forward(
            params["catastrophe_head"], latent
        )[..., 0]
        return CriticOutput(
            value=value,
            margin=margin,
            catastrophe_logit=catastrophe_logit,
            catastrophe_probability=stable_sigmoid(catastrophe_logit),
        )

    def state_dict(self) -> ParameterTree:
        return clone_parameters(self.parameters)

    def load_state_dict(self, parameters: Mapping[str, Any]) -> None:
        assert_same_parameter_schema(self.parameters, parameters, self.scope)
        self.parameters = clone_parameters(parameters)


class ManagerCritic(CatastropheValueCritic):
    """V_manager: value at day/event option boundaries."""

    scope = "V_manager"


class OptionCritic(CatastropheValueCritic):
    """V_option: value at the end of one expert responsibility window."""

    scope = "V_option"


class ResidualCritic(CatastropheValueCritic):
    """V_residual: local uplift relative to KEEP."""

    scope = "V_residual"


__all__ = [
    "Array",
    "CriticOutput",
    "DEFAULT_VALUE_COEF",
    "ManagerCritic",
    "OptionCritic",
    "ParameterTree",
    "ResidualCritic",
    "assert_same_parameter_schema",
    "clone_parameters",
    "deserialize_parameters",
    "init_mlp",
    "mlp_forward",
    "serialize_parameters",
    "stable_sigmoid",
    "validate_value_coef",
]
