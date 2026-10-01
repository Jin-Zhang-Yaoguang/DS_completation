from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SOURCE = Path(__file__).with_name("v100_v90_ctboost_nested_cv_blend.py")
SPEC = importlib.util.spec_from_file_location("v100", SOURCE)
assert SPEC is not None and SPEC.loader is not None
V100 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V100)


def test_mid_ecdf_ties_and_outside_values() -> None:
    state = V100.fit_mid_ecdf(np.array([1.0, 2.0, 2.0, 4.0]))
    actual = V100.transform_mid_ecdf(state, np.array([0.0, 2.0, 3.0, 5.0]))
    np.testing.assert_allclose(actual, [0.0, 0.5, 0.75, 1.0])


def test_expected_fold_ids_is_deterministic() -> None:
    y = np.tile(np.array([0, 1], dtype=np.int8), 50)
    first = V100.expected_fold_ids(y)
    second = V100.expected_fold_ids(y)
    assert np.array_equal(first, second)
    assert np.bincount(first).tolist() == [20, 20, 20, 20, 20]


def test_choose_weight_tie_prefers_smaller_candidate_weight() -> None:
    y = np.tile(np.array([0, 1], dtype=np.int8), 20)
    core = y.astype(float)
    candidate = core.copy()
    weight, auc = V100.choose_weight(y, core, candidate)
    assert weight == 0.0
    assert auc == 1.0


def test_nested_blend_rejects_reversed_candidate() -> None:
    rng = np.random.default_rng(20260905)
    y = np.tile(np.array([0, 1], dtype=np.int8), 250)
    core = y + rng.normal(0.0, 0.7, len(y))
    candidate = -core
    result = V100.nested_blend(y, core, candidate)
    assert all(row["selected_ctboost_weight"] == 0.0 for row in result["fold_rows"])
    assert result["positive_folds"] == 0
    assert abs(result["delta_vs_baseline"]) < 1e-15
