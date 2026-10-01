from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("xgb_recipe_probe", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {MODULE_PATH}")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def test_recipe_formula_is_exact() -> None:
    frame = pd.DataFrame(
        {
            "Annual_Income_USD": [100_000.0, 50_000.0],
            "Environmental_Concern_Level": [5.0, 1.0],
            "Subsidy_Available": ["Yes", "No"],
            "Range_Anxiety_Level": ["Low", "High"],
        }
    )
    assert np.array_equal(PROBE.recipe_score(frame), np.array([6.2, -1.8]))
    assert np.isfinite(PROBE.recipe_margin(frame)).all()


def test_feature_builder_has_only_rowwise_unlabelled_features() -> None:
    frame = pd.DataFrame(
        {
            "id": [1],
            "Will_Buy_EV": ["Yes"],
            "Daily_Commute_km": [20.0],
            "Charging_Stations_Near_Home": [2],
            "Charging_Stations_Near_Work": [3],
            "Home_Charging_Possible": ["Yes"],
            "Subsidy_Available": ["Yes"],
            "Annual_Income_USD": [100_000.0],
            "Environmental_Concern_Level": [5.0],
        }
    )
    output = PROBE.make_features(frame)
    assert "id" not in output and "Will_Buy_EV" not in output
    assert output.loc[0, "worry_score"] == -155.0
    assert output.loc[0, "chargers_total"] == 5
    assert output.loc[0, "income_x_subsidy"] == 1.0
    assert output.loc[0, "concern_x_subsidy"] == 5.0


def test_nested_meta_blend_selects_weight_inside_meta_train() -> None:
    source = inspect.getsource(PROBE.nested_meta_blend)
    assert source.index("roc_auc_score(\n                    y[fit_idx]") < source.index(
        "blend[hold_idx]"
    )
    assert "y[hold_idx]" not in source[: source.index("blend[hold_idx]")]


def test_protocol_is_fixed_and_has_no_test_training_path() -> None:
    assert PROBE.N_FOLDS == 5
    assert PROBE.SEED == 42
    assert PROBE.PARAMS["random_state"] == 42
    assert PROBE.PARAMS["device"] == "cpu"
    assert np.array_equal(PROBE.META_WEIGHT_GRID, np.arange(0, 0.5000001, 0.025))
    source = inspect.getsource(PROBE.run)
    assert "test_proba" not in source
    assert "submission.csv" not in source


def test_audit_does_not_train() -> None:
    source = inspect.getsource(PROBE.audit)
    assert "XGBClassifier" not in source
    result = PROBE.audit()
    assert result["status"] == "AUDIT_OK_NO_TRAINING"
