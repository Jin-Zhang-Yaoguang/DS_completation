from __future__ import annotations

import copy
import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("v88_strict_v80_v85_cv_blend.py")
SPEC = importlib.util.spec_from_file_location("v88_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {MODULE_PATH}")
V88 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V88)


def test_config_freezes_two_atomic_members_and_meta_protocol() -> None:
    config = V88.load_frozen_config()

    assert [member["experiment_id"] for member in config["members"]] == list(
        V88.MEMBER_IDS
    )
    assert all(member["prediction_parent"] is None for member in config["members"])
    assert config["best_input"] == "v85_naji_v74_40f"
    assert config["best_input_oof_auc"] == 0.9462702273556288
    assert config["meta_cv"] == {
        "n_splits": 5,
        "shuffle": True,
        "random_state": 42,
        "selection_scope": "each meta-train only",
        "holdout_role": "evaluation only",
    }
    assert config["transform"]["full_oof_fit_forbidden"] is True
    assert tuple(config["weight_search"]["v85_weight_grid"]) == V88.WEIGHT_GRID
    assert config["fixed_equal_weight_control"]["diagnostic_only"] is True
    assert config["failure_attribution_contract"] == {
        "COMPLETE_PROMOTE": None,
        "COMPLETE_REJECT": (
            "PREREGISTERED_PROMOTION_GATE_NOT_MET__DELTA_BELOW_0.0001_OR_"
            "META_HOLDOUT_WINS_BELOW_5_OF_5"
        ),
        "FAILED_RESOURCE_BUDGET": "RESOURCE_BUDGET_EXCEEDED",
        "FAILED_EXCEPTION": "IMPLEMENTATION_OR_RUNTIME_EXCEPTION",
    }


def test_config_rejects_parent_child_or_extra_member() -> None:
    config = copy.deepcopy(V88.load_frozen_config())
    config["members"][1]["prediction_parent"] = config["members"][0][
        "experiment_id"
    ]

    with pytest.raises(ValueError, match="原子"):
        V88.validate_static_config(config)


def test_mid_ecdf_uses_fit_only_midrank_for_ties_and_unseen_values() -> None:
    state = V88.fit_mid_ecdf(np.array([1.0, 1.0, 3.0, 5.0]))
    transformed = V88.transform_mid_ecdf(
        state, np.array([0.0, 1.0, 2.0, 3.0, 6.0])
    )

    assert np.array_equal(transformed, np.array([0.0, 0.25, 0.5, 0.625, 1.0]))


def test_weight_ties_choose_nearest_half_then_lower_v85_direction() -> None:
    rows = [
        {"v85_weight": weight, "v80_weight": 1.0 - weight, "meta_train_auc": 0.8}
        for weight in V88.WEIGHT_GRID
    ]
    for row in rows:
        if row["v85_weight"] in {0.45, 0.55}:
            row["meta_train_auc"] = 0.9

    assert V88.choose_v85_weight(rows) == 0.45


def test_meta_cv_is_deterministic_and_uses_only_frozen_weight_grid() -> None:
    rng = np.random.default_rng(42)
    y = np.tile(np.array([0, 1], dtype=np.int8), 100)
    common = 0.2 + 0.55 * y + rng.normal(0.0, 0.12, len(y))
    v80 = np.clip(common + rng.normal(0.0, 0.04, len(y)), 0.001, 0.999)
    v85 = np.clip(common + rng.normal(0.0, 0.05, len(y)), 0.001, 0.999)
    v80_test = np.clip(rng.uniform(0.01, 0.99, 43), 0, 1)
    v85_test = np.clip(rng.uniform(0.01, 0.99, 43), 0, 1)

    first = V88.run_meta_cv(y, v80, v85, v80_test, v85_test)
    second = V88.run_meta_cv(y, v80, v85, v80_test, v85_test)

    assert np.array_equal(first["oof"], second["oof"])
    assert np.array_equal(first["test"], second["test"])
    assert np.all(first["coverage"] == 1)
    assert len(first["fold_rows"]) == 5
    assert all(
        row["selected_v85_weight"] in V88.WEIGHT_GRID
        and len(row["weight_grid_train_auc"]) == 21
        for row in first["fold_rows"]
    )


def test_meta_selection_is_fit_before_holdout_evaluation() -> None:
    source = inspect.getsource(V88.run_meta_cv)
    fit_position = source.index("fit_mid_ecdf(v80_oof[train_idx])")
    selection_position = source.index(
        "y[train_idx], v80_train_t, v85_train_t"
    )
    holdout_score_position = source.index(
        "roc_auc_score(y[holdout_idx], hold_prediction)"
    )

    assert fit_position < selection_position < holdout_score_position
    assert "fit_mid_ecdf(v80_oof[holdout_idx])" not in source
    assert "fit_mid_ecdf(v85_oof[holdout_idx])" not in source


def test_promotion_requires_both_point_one_bp_and_five_of_five() -> None:
    config = V88.load_frozen_config()

    assert V88.promotion_decision(0.0001, 5, config) == "PROMOTE"
    assert V88.promotion_decision(0.000099999, 5, config) == "REJECT"
    assert V88.promotion_decision(0.001, 4, config) == "REJECT"


def test_failure_attribution_covers_all_terminal_outcomes() -> None:
    config = V88.load_frozen_config()

    assert V88.failure_attribution_for(config, "COMPLETE", "PROMOTE") is None
    assert V88.failure_attribution_for(config, "COMPLETE", "REJECT") == (
        "PREREGISTERED_PROMOTION_GATE_NOT_MET__DELTA_BELOW_0.0001_OR_"
        "META_HOLDOUT_WINS_BELOW_5_OF_5"
    )
    assert V88.failure_attribution_for(
        config, "FAILED_RESOURCE_BUDGET", "FAILED_RESOURCE_BUDGET"
    ) == "RESOURCE_BUDGET_EXCEEDED"
    assert V88.failure_attribution_for(
        config, "FAILED_EXCEPTION", "FAILED_EXCEPTION"
    ) == "IMPLEMENTATION_OR_RUNTIME_EXCEPTION"
    with pytest.raises(ValueError, match="无法归因"):
        V88.failure_attribution_for(config, "COMPLETE", "UNKNOWN")


def test_audit_hashes_real_predictions_without_loading_arrays(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def forbidden_load(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"audit attempted np.load: {args}, {kwargs}")

    monkeypatch.setattr(V88.np, "load", forbidden_load)
    result = V88.audit()
    capsys.readouterr()

    assert result["status"] == "AUDIT_OK_HASH_ONLY_NO_PREDICTION_ARRAYS_LOADED"
    assert result["formal_outputs_created"] is False
    assert len(result["member_file_records"]) == 12


def test_smoke_is_synthetic_and_creates_no_formal_outputs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = {
        name: (V88.OUT_DIR / name).exists()
        for name in (*V88.MATERIAL_ARTIFACTS, "cv_results.json")
    }
    result = V88.smoke()
    capsys.readouterr()
    after = {
        name: (V88.OUT_DIR / name).exists()
        for name in (*V88.MATERIAL_ARTIFACTS, "cv_results.json")
    }

    assert before == after
    assert result["status"] == "SMOKE_OK_SYNTHETIC_ONLY_NO_REAL_PREDICTIONS_LOADED"
    assert result["formal_outputs_created"] is False
    assert result["failure_attribution_contract_exercised"] is True


def test_failed_result_marks_partial_predictions_invalid(tmp_path: Path) -> None:
    config = V88.load_frozen_config()
    for name in ("oof_proba.npy", "test_proba.npy", "submission.csv"):
        (tmp_path / name).write_bytes(b"synthetic-partial")
    check = V88.resource_check(config, V88.time.monotonic(), "AFTER_ALL_OUTPUTS", 5)
    check.update(
        {
            "wall_elapsed_seconds": config["time_budget_seconds"],
            "status": "FAILED",
            "breaches": ["WALL_CLOCK_BUDGET"],
        }
    )
    failed = V88.build_failed_result(
        config,
        "FAILED_RESOURCE_BUDGET",
        check,
        "ResourceBudgetExceeded",
        "WALL_CLOCK_BUDGET",
        tmp_path,
    )

    V88.validate_failed_result(failed, config, tmp_path)
    assert failed["fold_auc"] is None
    assert failed["oof_auc"] is None
    assert failed["base_oof_auc"] is None
    assert failed["oof_delta_vs_base"] is None
    assert failed["present_artifacts"] == [
        "oof_proba.npy",
        "test_proba.npy",
        "submission.csv",
    ]
    assert failed["present_artifacts_are_invalid_for_use"] is True
    assert failed["allowed_for_fusion"] is False
    assert failed["failure_attribution"] == "RESOURCE_BUDGET_EXCEEDED"

    tampered_failed = copy.deepcopy(failed)
    tampered_failed["failure_attribution"] = None
    with pytest.raises(ValueError, match="归因"):
        V88.validate_failed_result(tampered_failed, config, tmp_path)

    exception_check = V88.resource_check(
        config, V88.time.monotonic(), "FAILED_EXCEPTION", None
    )
    exception = V88.build_failed_result(
        config,
        "FAILED_EXCEPTION",
        exception_check,
        "RuntimeError",
        "synthetic",
        tmp_path,
    )
    V88.validate_failed_result(exception, config, tmp_path)
    assert exception["present_artifacts"] == failed["present_artifacts"]
    assert exception["eligible_for_separate_preregistration"] is False
    assert exception["failure_attribution"] == (
        "IMPLEMENTATION_OR_RUNTIME_EXCEPTION"
    )


@pytest.mark.parametrize(
    ("decision", "expected_attribution"),
    [
        ("PROMOTE", None),
        (
            "REJECT",
            "PREREGISTERED_PROMOTION_GATE_NOT_MET__DELTA_BELOW_0.0001_OR_"
            "META_HOLDOUT_WINS_BELOW_5_OF_5",
        ),
    ],
)
def test_complete_verifier_enforces_frozen_failure_attribution(
    decision: str,
    expected_attribution: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = V88.load_frozen_config()
    meta = {
        "fold_rows": [
            {"holdout_blend_auc": 0.9 + fold * 0.001}
            for fold in range(V88.N_META_FOLDS)
        ]
    }
    evaluation = {
        "decision": decision,
        "oof_auc": 0.9464,
        "v85_oof_auc": config["best_input_oof_auc"],
        "oof_delta_vs_best_input_v85": (
            0.9464 - config["best_input_oof_auc"]
        ),
    }
    check = V88.resource_check(
        config,
        V88.time.monotonic(),
        "AFTER_STAGED_VERIFY_PRE_COMPLETE",
        V88.N_META_FOLDS,
    )
    monkeypatch.setattr(V88, "sha256_file", lambda _path: "a" * 64)
    monkeypatch.setattr(
        V88, "code_and_input_hashes", lambda _config: {"synthetic": "b" * 64}
    )
    result = V88.build_complete_result(
        config, meta, evaluation, check, "c" * 64
    )

    V88.validate_complete_result_schema(
        result, config, meta, evaluation, "c" * 64
    )
    assert result["failure_attribution"] == expected_attribution

    tampered = copy.deepcopy(result)
    tampered["failure_attribution"] = "UNFROZEN_POST_HOC_ATTRIBUTION"
    with pytest.raises(ValueError, match="归因"):
        V88.validate_complete_result_schema(
            tampered, config, meta, evaluation, "c" * 64
        )


def test_formal_complete_is_staged_verified_then_atomically_committed() -> None:
    source = inspect.getsource(V88.run)
    verify_position = source.index("verify_complete_payload(results)")
    stage_position = source.index("_atomic_bytes(")
    commit_position = source.index("os.replace(pending_results, RESULTS_PATH)")

    assert verify_position < stage_position < commit_position
    assert "BEFORE_INPUT_LOAD" in source
    assert "AFTER_INPUT_LOAD" in source
    assert "AFTER_META_FOLD" in source
    assert "AFTER_ALL_OUTPUTS" in source
    assert "AFTER_STAGED_VERIFY_PRE_COMPLETE" in source
    assert "FORMAL_SCOPE_COMPLETE" in source


def test_equal_weight_control_cannot_change_primary_decision() -> None:
    source = inspect.getsource(V88.promotion_decision)

    assert "fixed_equal" not in source
    assert "minimum_oof_delta_vs_best_input" in source
    assert "required_meta_holdout_wins" in source
