from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SOURCE = Path(__file__).with_name("evaluate_oof.py")
SPEC = importlib.util.spec_from_file_location("ctboost_evaluate_oof", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_mid_ecdf_is_fit_only_and_handles_ties() -> None:
    state = MODULE.fit_mid_ecdf(np.array([1.0, 2.0, 2.0, 4.0]))
    actual = MODULE.transform_mid_ecdf(state, np.array([0.0, 2.0, 3.0, 5.0]))
    np.testing.assert_allclose(actual, [0.0, 0.5, 0.75, 1.0])


def test_expected_fold_ids_is_complete_and_deterministic() -> None:
    y = np.tile(np.array([0, 1], dtype=np.int8), 50)
    first = MODULE.expected_fold_ids(y)
    second = MODULE.expected_fold_ids(y)
    assert np.array_equal(first, second)
    assert set(first.tolist()) == set(range(5))
    assert np.bincount(first).tolist() == [20, 20, 20, 20, 20]


def test_nested_meta_rejects_reversed_candidate() -> None:
    rng = np.random.default_rng(20260905)
    y = np.tile(np.array([0, 1], dtype=np.int8), 250)
    core = y + rng.normal(0.0, 0.7, size=len(y))
    candidate = -core
    fold_ids = MODULE.expected_fold_ids(y)
    result = MODULE.nested_meta_blend(y, core, candidate, fold_ids)
    assert all(row["selected_candidate_weight"] == 0.0 for row in result["rows"])
    assert result["positive_folds"] == 0
    assert abs(result["delta"]) < 1e-15
