from __future__ import annotations

import importlib.util
from pathlib import Path


SOURCE = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("lgbm_extra_trees_probe", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_only_parameter_override_is_extra_trees_mechanism() -> None:
    payload = MODULE.audit()
    assert payload["status"] == "AUDIT_OK_NO_TRAINING"
    assert payload["frozen_design"]["arm_b_override"] == {
        "extra_trees": True,
        "extra_seed": 104395303,
    }


def test_no_output_or_grid_expansion() -> None:
    design = MODULE.frozen_design()
    assert design["submission_budget"] == 0
    assert design["oof_saved"] is False
    assert design["test_generated"] is False
    assert design["no_grid_or_retry"] is True
