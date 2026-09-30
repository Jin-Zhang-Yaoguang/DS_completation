"""Fast contract tests for D2 orchestration; no Kaggle game is simulated."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from merge_d2_shards import merge
from orchestrate_d2 import ORCHESTRATOR_SCHEMA, _normalise_config


class D2OrchestratorTests(unittest.TestCase):
    def test_tiny_shard_does_not_concatenate_expert_schema(self) -> None:
        """N == P == M is the case that exposed the old merge corruption."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(2):
                np.savez_compressed(
                    root / ("shard_%d.npz" % index),
                    features=np.full((2, 3), index, dtype=np.float32),
                    production_mask=np.ones((2, 2), dtype=bool),
                    market_mask=np.ones((2, 2), dtype=bool),
                    production_uplift=np.zeros((2, 2), dtype=np.float32),
                    market_uplift=np.zeros((2, 2), dtype=np.float32),
                    state_ids=np.asarray(["s%d_a" % index, "s%d_b" % index]),
                    production_names=np.asarray(["E_V1"]),
                    market_names=np.asarray(["M_NONE", "M_ANIMAL_HALF_TOPDAYS"]),
                )
            output = root / "merged.npz"
            report = merge([root / "shard_0.npz", root / "shard_1.npz"], output)
            self.assertEqual(report["rows"], 4)
            with np.load(output, allow_pickle=False) as data:
                self.assertEqual(tuple(data["features"].shape), (4, 3))
                self.assertEqual(tuple(data["production_names"].tolist()), ("E_V1",))
                self.assertEqual(tuple(data["market_names"].tolist()), ("M_NONE", "M_ANIMAL_HALF_TOPDAYS"))

    def test_explicit_coverage_gate_does_not_inherit_other_experts(self) -> None:
        config = _normalise_config({
            "schema": ORCHESTRATOR_SCHEMA,
            "seeds": [7],
            "opponents": ["starter"],
            "production_days": [3],
            "market_days": [3, 4],
            "production": ["E_V1"],
            "market": ["M_NONE", "M_ANIMAL_HALF_TOPDAYS"],
            "min_coverage": {"effective_market": {"M_ANIMAL_HALF_TOPDAYS": 0}},
        })
        self.assertEqual(config["min_coverage"], {"effective_market": {"M_ANIMAL_HALF_TOPDAYS": 0}})
        self.assertEqual(config["sample_days"], [3, 4])


if __name__ == "__main__":
    unittest.main()
