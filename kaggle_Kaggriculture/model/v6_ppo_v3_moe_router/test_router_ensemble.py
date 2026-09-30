"""Fast contract tests for the served bootstrap Router format."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

from router_numpy import HIDDEN_DIM, NumpyRouter, ROUTER_SCHEMA
from features import FEATURE_DIM, SCHEMA_VERSION


def _weights(path: Path, members: int) -> None:
    rng = np.random.default_rng(7)
    p_names, m_names = np.asarray(["E_V1", "E_HIGH"]), np.asarray(["M_NONE", "M_TEST"])
    def sample(shape):
        return rng.normal(scale=0.1, size=((members, *shape) if members > 1 else shape)).astype(np.float32)
    np.savez_compressed(
        path, schema=np.asarray(ROUTER_SCHEMA), feature_schema=np.asarray(SCHEMA_VERSION),
        feature_dim=np.asarray(FEATURE_DIM, dtype=np.int32), production_names=p_names, market_names=m_names,
        ensemble_members=np.asarray(members, dtype=np.int32),
        enc_w=sample((FEATURE_DIM, HIDDEN_DIM)), enc_b=sample((HIDDEN_DIM,)),
        trunk_w=sample((HIDDEN_DIM, HIDDEN_DIM)), trunk_b=sample((HIDDEN_DIM,)),
        production_w=sample((HIDDEN_DIM, 2)), production_b=sample((2,)),
        market_w=sample((HIDDEN_DIM, 2)), market_b=sample((2,)),
        value_w=sample((HIDDEN_DIM, 1)), value_b=sample((1,)),
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ppo_v3_ensemble_test_") as temp:
        path = Path(temp) / "weights.npz"
        _weights(path, 3)
        router = NumpyRouter(path)
        production, market, value, p_std, m_std = router.predict_with_uncertainty(np.zeros(FEATURE_DIM, dtype=np.float32))
        assert router.member_count == 3
        assert production.shape == p_std.shape == (2,)
        assert market.shape == m_std.shape == (2,)
        assert np.isfinite(np.asarray([*production, *market, value, *p_std, *m_std])).all()
        assert np.any(p_std > 0) or np.any(m_std > 0)
        assert NumpyRouter.conservative_select(np.asarray([0.0, 0.2]), np.asarray([True, True]), np.asarray([0.0, 0.1]), 1.0) == 1
        assert NumpyRouter.conservative_select(np.asarray([0.0, 0.2]), np.asarray([True, True]), np.asarray([0.0, 0.3]), 1.0) == 0
    print("router ensemble test passed")


if __name__ == "__main__":
    main()
