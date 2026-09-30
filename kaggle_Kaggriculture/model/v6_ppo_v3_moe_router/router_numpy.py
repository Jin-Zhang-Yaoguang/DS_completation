"""Pure-NumPy MoVE Router inference for Kaggle submissions."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from features import FEATURE_DIM, SCHEMA_VERSION


HIDDEN_DIM = 128
ROUTER_SCHEMA = "kaggriculture-ppo-v3-move-router-1"


class NumpyRouter:
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
        self.member_count = int(data["ensemble_members"].item()) if "ensemble_members" in data.files else 1
        if self.member_count < 1:
            raise ValueError("invalid ensemble member count")
        self.arrays = {key: np.asarray(data[key], dtype=np.float32) for key in data.files if key not in {
            "schema", "feature_schema", "feature_dim", "production_names", "market_names",
            "ensemble_members",
        }}
        expected = {
            "enc_w": (FEATURE_DIM, HIDDEN_DIM), "enc_b": (HIDDEN_DIM,),
            "trunk_w": (HIDDEN_DIM, HIDDEN_DIM), "trunk_b": (HIDDEN_DIM,),
            "production_w": (HIDDEN_DIM, len(self.production_names)), "production_b": (len(self.production_names),),
            "market_w": (HIDDEN_DIM, len(self.market_names)), "market_b": (len(self.market_names),),
            "value_w": (HIDDEN_DIM, 1), "value_b": (1,),
        }
        def valid_shape(array, shape):
            return array.shape == shape if self.member_count == 1 else array.shape == (self.member_count, *shape)
        invalid = [key for key, shape in expected.items() if key not in self.arrays or not valid_shape(self.arrays[key], shape) or not np.all(np.isfinite(self.arrays[key]))]
        if invalid:
            raise ValueError(f"invalid router arrays: {invalid}")

    def predict_with_uncertainty(self, features: np.ndarray):
        x = np.clip(np.asarray(features, dtype=np.float32), -5.0, 5.0)
        if x.shape != (FEATURE_DIM,) or not np.all(np.isfinite(x)):
            raise ValueError("invalid feature vector")
        a = self.arrays
        if self.member_count == 1:
            x = np.tanh(x @ a["enc_w"] + a["enc_b"])
            x = np.tanh(x @ a["trunk_w"] + a["trunk_b"])
            production = x @ a["production_w"] + a["production_b"]
            market = x @ a["market_w"] + a["market_b"]
            value = float((x @ a["value_w"] + a["value_b"]).reshape(-1)[0])
            return production.astype(np.float32), market.astype(np.float32), value, np.zeros_like(production, dtype=np.float32), np.zeros_like(market, dtype=np.float32)
        hidden = np.tanh(np.einsum("f,kfh->kh", x, a["enc_w"]) + a["enc_b"])
        hidden = np.tanh(np.einsum("kh,khj->kj", hidden, a["trunk_w"]) + a["trunk_b"])
        production = np.einsum("kh,khp->kp", hidden, a["production_w"]) + a["production_b"]
        market = np.einsum("kh,khm->km", hidden, a["market_w"]) + a["market_b"]
        value = np.einsum("kh,kho->ko", hidden, a["value_w"]) + a["value_b"]
        return (
            production.mean(axis=0, dtype=np.float32), market.mean(axis=0, dtype=np.float32), float(value.mean()),
            production.std(axis=0, dtype=np.float32), market.std(axis=0, dtype=np.float32),
        )

    def predict(self, features: np.ndarray):
        production, market, value, _, _ = self.predict_with_uncertainty(features)
        return production, market, value

    @staticmethod
    def conservative_select(scores, eligible, uncertainty=None, uncertainty_penalty: float = 0.0):
        values = np.asarray(scores, dtype=np.float64)
        mask = np.asarray(eligible, dtype=bool)
        if values.shape != mask.shape:
            raise ValueError("router score/mask shape mismatch")
        deviation = np.zeros_like(values) if uncertainty is None else np.asarray(uncertainty, dtype=np.float64)
        if deviation.shape != values.shape:
            raise ValueError("router uncertainty shape mismatch")
        values = np.where(mask & np.isfinite(values) & np.isfinite(deviation), values - float(uncertainty_penalty) * deviation, -np.inf)
        best = int(np.argmax(values)) if values.size else -1
        return None if best < 0 or not np.isfinite(values[best]) else best
