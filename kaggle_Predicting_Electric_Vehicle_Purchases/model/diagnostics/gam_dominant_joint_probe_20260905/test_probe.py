from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SOURCE = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("gam_dominant_joint_probe", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_joint_key_order_is_frozen() -> None:
    frame = pd.DataFrame(
        {
            "Environmental_Concern_Level": [3.0],
            "Subsidy_Available": ["Yes"],
            "Range_Anxiety_Level": ["Medium"],
            "Home_Charging_Possible": ["No"],
        }
    )
    result = MODULE.add_dominant_joint(frame)
    assert result[MODULE.JOINT_COLUMN].iloc[0] == "3.0|Yes|Medium|No"
    assert MODULE.JOINT_PARTS == [
        "Environmental_Concern_Level",
        "Subsidy_Available",
        "Range_Anxiety_Level",
        "Home_Charging_Possible",
    ]


def test_design_has_one_frozen_joint_and_no_grid() -> None:
    design = MODULE.frozen_design()
    assert design["arm_a"] == "v98 additive 39-column GAM"
    assert design["joint_levels"] == 50
    assert design["joint_features"] == 89
    assert design["no_grid_or_retry"] is True
    assert design["test_read"] is False
    assert design["submission_budget"] == 0


def test_audit_uses_no_training() -> None:
    result = MODULE.audit()
    assert result["status"] == "AUDIT_OK_NO_TRAINING"
