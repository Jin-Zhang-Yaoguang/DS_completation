from __future__ import annotations

import importlib.util
from pathlib import Path


SOURCE = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("gam_joint_residual_probe", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_design_is_matched_and_submission_free() -> None:
    design = MODULE.frozen_design()
    assert design["only_variable"] == "GAM dominant block representation"
    assert design["outer_folds"] == 5
    assert design["outer_seed"] == 42
    assert design["submission_budget"] == 0
    assert design["test_prediction_generated"] is False
    assert design["oof_arrays_saved"] is False
    assert design["no_grid_or_retry"] is True


def test_upstream_stage1_is_bound() -> None:
    payload = MODULE.audit()
    assert payload["status"] == "AUDIT_OK_NO_TRAINING"
    assert "stage1_runner" in payload["source_sha256"]
    assert "stage1_evidence" in payload["source_sha256"]
    assert "v98_probe_evidence" in payload["source_sha256"]
