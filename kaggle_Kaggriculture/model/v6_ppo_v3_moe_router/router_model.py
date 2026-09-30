"""JAX and NumPy implementations of the PPO v3 MoVE router.

The router predicts one score per production expert and per compatible market
expert.  Expert actions are selected discretely; there is no unsafe averaging
of conflicting action plans.
"""

from __future__ import annotations

from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
from flax import linen as nn

from features import FEATURE_DIM, SCHEMA_VERSION


HIDDEN_DIM = 128
ROUTER_SCHEMA = "kaggriculture-ppo-v3-move-router-1"


class RouterNetwork(nn.Module):
    production_dim: int
    market_dim: int

    @nn.compact
    def __call__(self, features):
        x = jnp.clip(features, -5.0, 5.0)
        x = jnp.tanh(nn.Dense(HIDDEN_DIM, name="enc")(x))
        x = jnp.tanh(nn.Dense(HIDDEN_DIM, name="trunk")(x))
        production = nn.Dense(self.production_dim, name="production")(x)
        market = nn.Dense(self.market_dim, name="market")(x)
        value = nn.Dense(1, name="value")(x)[..., 0]
        return production, market, value


def initial_params(production_dim: int, market_dim: int, seed: int = 0):
    model = RouterNetwork(int(production_dim), int(market_dim))
    return model.init(jax.random.PRNGKey(int(seed)), jnp.zeros((1, FEATURE_DIM), dtype=jnp.float32))


def export_numpy(params, path: str | Path, production_names, market_names) -> dict[str, np.ndarray]:
    """Export a submission-only weight artifact with explicit expert ordering."""
    p = params["params"]
    arrays = {
        "schema": np.asarray(ROUTER_SCHEMA),
        "feature_schema": np.asarray(SCHEMA_VERSION),
        "feature_dim": np.asarray(FEATURE_DIM, dtype=np.int32),
        "production_names": np.asarray(list(production_names)),
        "market_names": np.asarray(list(market_names)),
        "enc_w": np.asarray(p["enc"]["kernel"], dtype=np.float32),
        "enc_b": np.asarray(p["enc"]["bias"], dtype=np.float32),
        "trunk_w": np.asarray(p["trunk"]["kernel"], dtype=np.float32),
        "trunk_b": np.asarray(p["trunk"]["bias"], dtype=np.float32),
        "production_w": np.asarray(p["production"]["kernel"], dtype=np.float32),
        "production_b": np.asarray(p["production"]["bias"], dtype=np.float32),
        "market_w": np.asarray(p["market"]["kernel"], dtype=np.float32),
        "market_b": np.asarray(p["market"]["bias"], dtype=np.float32),
        "value_w": np.asarray(p["value"]["kernel"], dtype=np.float32),
        "value_b": np.asarray(p["value"]["bias"], dtype=np.float32),
    }
    np.savez_compressed(Path(path), **arrays)
    return arrays


class NumpyRouter:
    """Dependency-free deployment implementation."""

    def __init__(self, path: str | Path):
        data = np.load(Path(path), allow_pickle=False)
        if str(data["schema"].item()) != ROUTER_SCHEMA:
            raise ValueError("incompatible router schema")
        if str(data["feature_schema"].item()) != SCHEMA_VERSION:
            raise ValueError("incompatible feature schema")
        if int(data["feature_dim"].item()) != FEATURE_DIM:
            raise ValueError("incompatible feature dimension")
        self.production_names = tuple(str(item) for item in data["production_names"].tolist())
        self.market_names = tuple(str(item) for item in data["market_names"].tolist())
        self.arrays = {key: np.asarray(data[key], dtype=np.float32) for key in data.files if key not in {
            "schema", "feature_schema", "feature_dim", "production_names", "market_names",
        }}
        expected = {
            "enc_w": (FEATURE_DIM, HIDDEN_DIM), "enc_b": (HIDDEN_DIM,),
            "trunk_w": (HIDDEN_DIM, HIDDEN_DIM), "trunk_b": (HIDDEN_DIM,),
            "production_w": (HIDDEN_DIM, len(self.production_names)), "production_b": (len(self.production_names),),
            "market_w": (HIDDEN_DIM, len(self.market_names)), "market_b": (len(self.market_names),),
            "value_w": (HIDDEN_DIM, 1), "value_b": (1,),
        }
        invalid = [key for key, shape in expected.items() if self.arrays.get(key, np.empty(0)).shape != shape or not np.all(np.isfinite(self.arrays[key]))]
        if invalid:
            raise ValueError(f"invalid router arrays: {invalid}")

    def predict(self, features: np.ndarray):
        x = np.clip(np.asarray(features, dtype=np.float32), -5.0, 5.0)
        if x.shape != (FEATURE_DIM,) or not np.all(np.isfinite(x)):
            raise ValueError("invalid feature vector")
        a = self.arrays
        x = np.tanh(x @ a["enc_w"] + a["enc_b"])
        x = np.tanh(x @ a["trunk_w"] + a["trunk_b"])
        production = x @ a["production_w"] + a["production_b"]
        market = x @ a["market_w"] + a["market_b"]
        value = float((x @ a["value_w"] + a["value_b"]).reshape(-1)[0])
        return production.astype(np.float32), market.astype(np.float32), value

    @staticmethod
    def conservative_select(scores, eligible, uncertainty_penalty: float = 0.0):
        """Choose argmax among a boolean mask; return None if no legal action."""
        values = np.asarray(scores, dtype=np.float64)
        mask = np.asarray(eligible, dtype=bool)
        if values.shape != mask.shape:
            raise ValueError("router score/mask shape mismatch")
        values = np.where(mask & np.isfinite(values), values - float(uncertainty_penalty), -np.inf)
        best = int(np.argmax(values)) if values.size else -1
        return None if best < 0 or not np.isfinite(values[best]) else best


def parity_error(params, weight_path: str | Path, production_names, market_names, seed: int = 41, batch: int = 8) -> float:
    rng = np.random.default_rng(int(seed))
    features = rng.normal(size=(int(batch), FEATURE_DIM)).astype(np.float32)
    model = RouterNetwork(len(production_names), len(market_names))
    p_score, m_score, value = model.apply(params, features)
    deployed = NumpyRouter(weight_path)
    rows = [deployed.predict(row) for row in features]
    error = [np.max(np.abs(np.asarray(p_score) - np.stack([row[0] for row in rows])))]
    error.append(np.max(np.abs(np.asarray(m_score) - np.stack([row[1] for row in rows]))))
    error.append(np.max(np.abs(np.asarray(value) - np.asarray([row[2] for row in rows]))))
    return float(max(error))
