from __future__ import annotations

import importlib.util
from pathlib import Path

import lightgbm as lgb
import numpy as np


SOURCE = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("lgbm_goss_probe", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_override_is_one_matched_rate_sampling_mechanism() -> None:
    payload = MODULE.audit()
    assert payload["status"] == "AUDIT_OK_NO_TRAINING"
    design = payload["frozen_design"]
    assert design["arm_b_override"] == MODULE.GOSS_OVERRIDE
    assert np.isclose(
        design["arm_b_override"]["top_rate"] + design["arm_b_override"]["other_rate"],
        design["matched_expected_sample_rate"],
    )


def test_no_output_or_grid_expansion() -> None:
    design = MODULE.frozen_design()
    assert design["submission_budget"] == 0
    assert design["oof_saved"] is False
    assert design["test_generated"] is False
    assert design["no_grid_or_retry"] is True


def test_goss_override_is_accepted_by_installed_lightgbm() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=(256, 4))
    y = (x[:, 0] + rng.normal(size=256) > 0).astype(np.int8)
    model = lgb.LGBMClassifier(
        n_estimators=5,
        verbosity=-1,
        deterministic=True,
        force_col_wise=True,
        **MODULE.GOSS_OVERRIDE,
    )
    model.fit(x, y)
    assert model.predict_proba(x).shape == (256, 2)
