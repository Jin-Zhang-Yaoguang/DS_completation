from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold


RUNNER = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("strict_mlp_probe_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def test_inner_hold_prior_excludes_inner_hold_labels() -> None:
    key = pd.Series(["a", "a", "b", "b", "c", "c", "d", "d", "e", "e", "f", "f"])
    y = np.asarray([0, 1] * 6, dtype=np.int8)
    splits = list(StratifiedKFold(3, shuffle=True, random_state=42).split(key, y))
    fit, _ = PROBE.strict_fold_target_encoding(key, y, pd.Series(["a"]), splits)
    first_hold = splits[0][1]
    flipped = y.copy()
    flipped[first_hold] = 1 - flipped[first_hold]
    changed, _ = PROBE.strict_fold_target_encoding(
        key, flipped, pd.Series(["a"]), splits
    )
    np.testing.assert_array_equal(fit[first_hold], changed[first_hold])


def test_income_trace_is_target_free_and_finite() -> None:
    train = pd.DataFrame({"Annual_Income_USD": [10.0, 20.0], "Will_Buy_EV": ["No", "Yes"]})
    test = pd.DataFrame({"Annual_Income_USD": [10.0, 30.0]})
    original = pd.DataFrame({"Annual_Income_USD": [10.0, 10.0, 20.0, np.nan]})
    block = PROBE.build_income_trace(train, test, original)
    flipped = train.copy()
    flipped["Will_Buy_EV"] = ["Yes", "No"]
    pd.testing.assert_frame_equal(block, PROBE.build_income_trace(flipped, test, original))
    assert np.isfinite(block.to_numpy()).all()


def test_audit_is_nontraining() -> None:
    payload = PROBE.audit()
    assert payload["status"] == "AUDIT_OK_NO_TRAINING"
    assert payload["same_input_width_formula"] == 23
