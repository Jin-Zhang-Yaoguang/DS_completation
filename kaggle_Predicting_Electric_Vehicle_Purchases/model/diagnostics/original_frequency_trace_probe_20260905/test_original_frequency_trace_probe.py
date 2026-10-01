from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


RUNNER = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("frequency_probe_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def test_income_frequency_trace_is_exact_finite_and_target_invariant() -> None:
    original = pd.DataFrame({"Annual_Income_USD": [10.0, 10.0, 20.0]})
    train = pd.DataFrame(
        {"Annual_Income_USD": [10.0, 20.0], "Will_Buy_EV": ["No", "Yes"]}
    )
    test = pd.DataFrame({"Annual_Income_USD": [10.0, 30.0]})
    block, test_block, profile = PROBE.build_income_frequency_trace(
        train, test, original
    )
    expected = np.asarray(
        [
            [2.0 / 3.0, (2.0 / 4.0) / (2.0 / 3.0), 0.0],
            [1.0 / 3.0, (1.0 / 4.0) / (1.0 / 3.0), 0.0],
        ],
        dtype=np.float32,
    )
    np.testing.assert_allclose(block.to_numpy(), expected, rtol=1e-6, atol=1e-7)
    assert test_block.iloc[1].tolist() == [0.0, 0.0, 1.0]
    assert profile["uses_target"] is False
    flipped = train.copy()
    flipped["Will_Buy_EV"] = ["Yes", "No"]
    flipped_block, _, _ = PROBE.build_income_frequency_trace(flipped, test, original)
    pd.testing.assert_frame_equal(block, flipped_block)
    assert np.isfinite(block.to_numpy()).all()


def test_default_mode_is_audit_and_does_not_create_run_marker() -> None:
    if PROBE.START_MARKER.exists():
        return
    payload = PROBE.audit()
    assert payload["status"] == "AUDIT_OK_NO_TRAINING"
    assert not PROBE.START_MARKER.exists()
