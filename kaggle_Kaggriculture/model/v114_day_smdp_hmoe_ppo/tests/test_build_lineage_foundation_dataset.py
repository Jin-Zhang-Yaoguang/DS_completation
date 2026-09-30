from __future__ import annotations

from pathlib import Path
import tempfile

import numpy as np

from build_lineage_foundation_dataset import build_lineage_dataset


def test_filters_one_family_and_builds_pre_action_history() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source, output, manifest = root / "source.npz", root / "lineage.npz", root / "manifest.json"
        rows = 2 * 719
        family = np.asarray(["a"] * 719 + ["b"] * 719)
        episode = np.asarray([10] * 719 + [11] * 719, dtype=np.int64)
        seat = np.zeros((rows,), dtype=np.int8)
        step = np.tile(np.arange(719, dtype=np.int16), 2)
        unit_tokens = np.zeros((rows, 2), dtype=np.int16)
        market_tokens = np.zeros((rows, 3), dtype=np.int16)
        market_quantities = np.zeros((rows, 3), dtype=np.int16)
        np.savez_compressed(
            source,
            **{
                "global": np.zeros((rows, 60), dtype=np.float16),
                "episode": episode,
                "seat": seat,
                "step": step,
                "teacher_family": family,
                "teacher_id": np.asarray(["teacher_a"] * 719 + ["teacher_b"] * 719),
                "unit_tokens": unit_tokens,
                "market_tokens": market_tokens,
                "market_quantities": market_quantities,
                "market_mask": np.asarray([[1, 0, 0]] * rows, dtype=np.uint8),
            },
        )
        report = build_lineage_dataset(source, output, manifest, "a")
        assert report["rows"] == 719
        assert report["games"] == 1
        assert report["augmented_global_features"] == 92
        assert report["strategy_parent"] is None
        with np.load(output, allow_pickle=False) as data:
            assert set(data["teacher_family"].astype(str)) == {"a"}
            assert data["global"].shape == (719, 92)
            np.testing.assert_array_equal(data["step"], np.arange(719, dtype=np.int16))
