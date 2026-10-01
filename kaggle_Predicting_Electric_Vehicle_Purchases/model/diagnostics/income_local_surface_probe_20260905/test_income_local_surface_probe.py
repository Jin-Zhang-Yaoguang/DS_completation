from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold


RUNNER = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("surface_probe_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def test_surface_shape_finite_and_inner_hold_prior_is_strict() -> None:
    income = np.arange(18, dtype=np.float64) * 10.0
    y = np.asarray([0, 1] * 9, dtype=np.int8)
    splits = list(StratifiedKFold(3, shuffle=True, random_state=42).split(income, y))
    fit, valid, profile = PROBE.build_income_local_surface(
        income, y, np.asarray([15.0, 75.0]), splits, q=8, smooth=2.0
    )
    assert fit.shape == (18, 8)
    assert valid.shape == (2, 8)
    assert np.isfinite(fit).all() and np.isfinite(valid).all()
    assert profile["inner_prior_contract"] == "each inner-train labels only"

    first_hold = splits[0][1]
    flipped = y.copy()
    flipped[first_hold] = 1 - flipped[first_hold]
    changed, _, _ = PROBE.build_income_local_surface(
        income, flipped, np.asarray([15.0, 75.0]), splits, q=8, smooth=2.0
    )
    np.testing.assert_array_equal(fit[first_hold], changed[first_hold])


def test_audit_is_nontraining() -> None:
    payload = PROBE.audit()
    assert payload["status"] == "AUDIT_OK_NO_TRAINING"
    assert payload["all_finite"] is True
