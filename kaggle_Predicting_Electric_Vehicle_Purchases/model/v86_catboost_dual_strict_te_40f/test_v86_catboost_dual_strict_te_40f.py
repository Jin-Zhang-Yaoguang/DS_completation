from __future__ import annotations

import copy
import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.model_selection import StratifiedKFold


MODULE_PATH = Path(__file__).with_name("v86_catboost_dual_strict_te_40f.py")
SPEC = importlib.util.spec_from_file_location("v86_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {MODULE_PATH}")
V86 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V86)


def test_config_freezes_v77_recipe_and_only_51_added_features() -> None:
    config = V86.load_frozen_config()

    assert config["baseline"]["experiment_id"] == "v77_catboost_dual_40f"
    assert config["baseline"]["role"] == (
        "ONLY_MODEL_AND_ORIGINAL_FEATURE_RECIPE_BASELINE"
    )
    assert config["only_primary_change"] == (
        "append_51_v80_strict_nested_te_numeric_features"
    )
    assert config["expected_added_te_features"] == 51
    assert config["expected_total_features"] == 71
    assert config["catboost_params"] == V86.EXPECTED_CAT_PARAMS
    assert config["bag_seeds"] == [42, 2026]


def test_config_rejects_catboost_parameter_drift(tmp_path: Path) -> None:
    config = copy.deepcopy(V86.load_frozen_config())
    config["catboost_params"]["depth"] = 7
    changed_path = tmp_path / "frozen_config.json"
    changed_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="CatBoost 参数"):
        original = V86.CONFIG_PATH
        try:
            V86.CONFIG_PATH = changed_path
            V86.load_frozen_config()
        finally:
            V86.CONFIG_PATH = original


def test_strict_prior_counterfactual_self_check() -> None:
    V86.strict_prior_self_check()


def test_ten_fold_stop_uses_both_preregistered_conditions() -> None:
    config = V86.load_frozen_config()

    triggered = V86.ten_fold_stop_decision([0.001] * 4 + [-0.001] * 6, config)
    five_wins = V86.ten_fold_stop_decision([0.001] * 5 + [-0.001] * 5, config)
    positive_mean = V86.ten_fold_stop_decision([0.01] * 4 + [-0.001] * 6, config)

    assert triggered["triggered"] is True
    assert five_wins["triggered"] is False
    assert positive_mean["triggered"] is False


def test_strength_gate_requires_delta_and_24_of_40_buckets() -> None:
    config = V86.load_frozen_config()

    passing = V86.final_decision(0.946, 0.0001, 24, 0.999, 0.999, config)
    weak_delta = V86.final_decision(
        0.946, 0.000099, 40, 0.999, 0.999, config
    )
    weak_buckets = V86.final_decision(
        0.946, 0.001, 23, 0.999, 0.999, config
    )

    assert passing["strength_gate_passes"] is True
    assert weak_delta["strength_gate_passes"] is False
    assert weak_buckets["strength_gate_passes"] is False


def test_diversity_only_cannot_enter_fusion_directly() -> None:
    decision = V86.final_decision(
        0.9453, -0.001, 20, 0.99, 0.999, V86.load_frozen_config()
    )

    assert decision["diversity_signal_only"] is True
    assert decision["allowed_for_fusion"] is False
    assert decision["eligible_for_separate_preregistration"] is True
    assert decision["decision"] == (
        "DIVERSITY_ONLY_REQUIRES_SEPARATE_PREREGISTRATION"
    )


def test_no_strength_and_no_diversity_is_rejected() -> None:
    decision = V86.final_decision(
        0.946, -0.001, 20, 0.999, 0.999, V86.load_frozen_config()
    )

    assert decision["decision"] == "REJECT"
    assert decision["allowed_for_fusion"] is False
    assert decision["eligible_for_separate_preregistration"] is False


def test_low_oof_low_correlation_is_rejected() -> None:
    decision = V86.final_decision(
        0.945199,
        -0.001,
        20,
        0.99,
        0.999,
        V86.load_frozen_config(),
    )

    assert decision["diversity_oof_floor_passes"] is False
    assert decision["diversity_correlation_signal"] is True
    assert decision["diversity_signal_only"] is False
    assert decision["decision"] == "REJECT"
    assert decision["eligible_for_separate_preregistration"] is False


def test_early_stop_schema_is_frozen_and_nulls_unavailable_metrics() -> None:
    config = V86.load_frozen_config()
    run_contract = {
        "run_contract_sha256": "a" * 64,
        "sources": {
            "runner": {"path": "runner.py", "sha256": "b" * 64},
            "train_csv": {"path": "data/train.csv", "sha256": "c" * 64},
        },
    }
    rebuilt = {
        "fold_rows": [
            {"fold": fold, "candidate_auc": 0.94, "delta_vs_v77": -0.001}
            for fold in range(1, 11)
        ]
    }
    check = V86.resource_check(config, 0.0, "EARLY_TEST", 10)
    # Avoid coupling this schema test to the host monotonic clock value.
    check["wall_elapsed_seconds"] = 1.0
    check["status"] = "OK"
    check["breaches"] = []
    result = V86.build_early_stop_result(
        config, run_contract, rebuilt, check, "d" * 64
    )

    V86.validate_early_stop_result_schema(
        result, config, run_contract, rebuilt, "d" * 64
    )
    assert result["model"] == config["model"]
    assert result["n_folds"] == 40
    assert len(result["fold_auc"]) == 10
    assert result["params"] == config["catboost_params"]
    assert result["elapsed_seconds"] == 1.0
    assert result["oof_auc"] is None
    assert result["base_oof_auc"] is None
    assert result["oof_delta_vs_base"] is None
    assert set(result["code_and_input_hashes"]) == {"runner", "train_csv"}

    drifted = copy.deepcopy(result)
    drifted["params"]["depth"] = 7
    with pytest.raises(ValueError, match="schema|不一致"):
        V86.validate_early_stop_result_schema(
            drifted, config, run_contract, rebuilt, "d" * 64
        )


def test_failed_closes_mark_partial_final_artifacts_invalid(tmp_path: Path) -> None:
    config = V86.load_frozen_config()
    for name in ("oof_proba.npy", "test_proba.npy", "submission.csv"):
        (tmp_path / name).write_bytes(b"partial")
    check = {
        "timestamp_utc": "2026-09-04T00:00:00+00:00",
        "phase": "AFTER_FINAL_OUTPUTS",
        "fold": 40,
        "status": "FAILED",
        "breaches": ["WALL_CLOCK_BUDGET"],
        "wall_elapsed_seconds": 21600.0,
        "wall_clock_budget_seconds": 21600,
        "peak_rss_bytes": 1024,
        "peak_rss_gib": 1024 / 1024**3,
        "peak_rss_budget_bytes": 24 * 1024**3,
        "peak_rss_budget_gib": 24,
    }
    run_contract = {
        "run_contract_sha256": "a" * 64,
        "sources": {
            "runner": {"path": "runner.py", "sha256": "b" * 64},
            "train_csv": {"path": "data/train.csv", "sha256": "c" * 64},
        },
    }
    resource_failure = V86.resource_failure_payload(
        config,
        check,
        40,
        run_contract,
        artifact_root=tmp_path,
    )
    exception_check = copy.deepcopy(check)
    exception_check.update(
        {
            "phase": "FAILED_EXCEPTION",
            "status": "OK",
            "breaches": [],
            "wall_elapsed_seconds": 10.0,
        }
    )
    exception_failure = V86.failed_exception_payload(
        config,
        40,
        RuntimeError("synthetic"),
        run_contract,
        exception_check,
        artifact_root=tmp_path,
    )

    for payload in (resource_failure, exception_failure):
        V86.validate_failed_close_schema(
            payload, config, tmp_path, run_contract
        )
        assert payload["model"] == config["model"]
        assert payload["n_folds"] == 40
        assert payload["fold_auc"] is None
        assert payload["oof_auc"] is None
        assert payload["base_oof_auc"] is None
        assert payload["oof_delta_vs_base"] is None
        assert payload["params"] == config["catboost_params"]
        assert payload["elapsed_seconds"] == payload["resource_check"][
            "wall_elapsed_seconds"
        ]
        assert set(payload["code_and_input_hashes"]) == {
            "runner",
            "train_csv",
        }
        assert payload["present_artifacts_are_invalid_for_use"] is True
        assert payload["present_artifacts"] == [
            "oof_proba.npy",
            "test_proba.npy",
            "submission.csv",
        ]
        assert "feature_importance.csv" in payload["missing_artifacts"]
        assert payload["allowed_for_fusion"] is False

    drifted = copy.deepcopy(resource_failure)
    drifted["elapsed_seconds"] = 1.0
    with pytest.raises(ValueError, match="数值不一致"):
        V86.validate_failed_close_schema(
            drifted, config, tmp_path, run_contract
        )


@pytest.mark.parametrize("failure_kind", ["exception", "resource"])
def test_verify_closed_independently_validates_failed_statuses(
    tmp_path: Path, failure_kind: str
) -> None:
    config = V86.load_frozen_config()
    unsigned_contract = {
        "schema_version": 1,
        "experiment_id": V86.EXPERIMENT_ID,
        "sources": {"runner": V86.file_record(MODULE_PATH)},
    }
    run_contract = {
        **unsigned_contract,
        "run_contract_sha256": V86.sha256_json(unsigned_contract),
    }
    (tmp_path / "run_contract.json").write_text(
        json.dumps(run_contract), encoding="utf-8"
    )
    if failure_kind == "exception":
        check = V86.resource_check(
            config, V86.time.monotonic(), "FAILED_EXCEPTION", 0
        )
        failure = V86.failed_exception_payload(
            config,
            0,
            RuntimeError("synthetic-independent-verify"),
            run_contract,
            check,
            artifact_root=tmp_path,
        )
        expected_status = "FAILED_EXCEPTION"
    else:
        check = V86.resource_check(
            config, V86.time.monotonic(), "AFTER_FINAL_OUTPUTS", 40
        )
        check.update(
            {
                "wall_elapsed_seconds": config["wall_clock_budget_seconds"],
                "status": "FAILED",
                "breaches": ["WALL_CLOCK_BUDGET"],
            }
        )
        failure = V86.resource_failure_payload(
            config,
            check,
            40,
            run_contract,
            artifact_root=tmp_path,
        )
        expected_status = "FAILED_RESOURCE_BUDGET"
    results_path = tmp_path / "cv_results.json"
    results_path.write_text(json.dumps(failure), encoding="utf-8")
    original_out_dir = V86.OUT_DIR
    original_results_path = V86.RESULTS_PATH
    try:
        V86.OUT_DIR = tmp_path
        V86.RESULTS_PATH = results_path
        verified = V86.verify_closed()
    finally:
        V86.OUT_DIR = original_out_dir
        V86.RESULTS_PATH = original_results_path

    assert verified["status"] == expected_status
    assert verified["present_artifacts"] == ["run_contract.json"]


def test_resource_limit_is_hard_at_frozen_wall_clock() -> None:
    config = V86.load_frozen_config()
    check = {
        "wall_elapsed_seconds": 21600.0,
        "peak_rss_bytes": 1024,
        "peak_rss_gib": 1024 / 1024**3,
        "breaches": ["WALL_CLOCK_BUDGET"],
        "status": "FAILED",
        "wall_clock_budget_seconds": 21600,
        "peak_rss_budget_bytes": 24 * 1024**3,
        "peak_rss_budget_gib": 24,
    }

    with pytest.raises(ValueError, match="COMPLETE"):
        V86.validate_resource_check(config, check, must_pass=True)


def test_audit_and_smoke_do_not_create_formal_outputs() -> None:
    formal_names = (
        "run.lock",
        "run_contract.json",
        "sources.json",
        "cv_results.json",
        "train_log.txt",
        "oof_proba.npy",
        "test_proba.npy",
        "submission.csv",
        "feature_importance.csv",
    )
    before = {name: (V86.OUT_DIR / name).exists() for name in formal_names}

    audit = V86.audit()
    smoke = V86.smoke()

    after = {name: (V86.OUT_DIR / name).exists() for name in formal_names}
    assert before == after
    assert audit["status"] == "AUDIT_OK_NO_TRAINING_OR_PREDICTION_ARRAYS_READ"
    assert smoke["status"] == "SMOKE_OK_SYNTHETIC_ONLY_NO_TRAINING"


def test_formal_code_keeps_verify_and_resource_guard_before_complete() -> None:
    source = inspect.getsource(V86.train)
    verify_position = source.index("verify_closed(results_override=results)")
    stage_position = source.index("_atomic_bytes(pending_results, encoded)")
    commit_position = source.index("os.replace(pending_results, RESULTS_PATH)")

    assert verify_position < stage_position < commit_position
    assert "AFTER_INPUT_LOAD" in source
    assert "AFTER_TRAIN_BEFORE_CHECKPOINT" in source
    assert "BEFORE_TEN_FOLD_GATE" in source
    assert "AFTER_FINAL_OUTPUTS" in source
    assert "AFTER_FINAL_VERIFY_PRE_COMPLETE" in source
    assert "FORMAL_SCOPE_COMPLETE" in source


def test_final_evaluation_applies_canonical_v80_full_and_bucket_gates() -> None:
    config = V86.load_frozen_config()
    y = np.tile(np.array([0, 1], dtype=np.int8), 200)
    index_noise = np.linspace(0.0, 0.01, len(y))
    candidate = 0.1 + 0.8 * y + index_noise
    v77 = 0.12 + 0.7 * y + index_noise[::-1]
    v80 = np.linspace(0.1, 0.9, len(y))
    candidate_test = np.linspace(0.05, 0.95, 80)
    v77_test = np.linspace(0.06, 0.94, 80) ** 1.01
    v80_test = np.linspace(0.95, 0.05, 80)
    folds = list(
        StratifiedKFold(n_splits=40, shuffle=True, random_state=42).split(
            np.zeros(len(y)), y
        )
    )

    evaluation = V86.evaluate_final(
        config,
        y,
        candidate,
        candidate_test,
        v77,
        v77_test,
        v80,
        v80_test,
        folds,
    )

    assert evaluation["oof_delta_vs_strict_v80"] >= 0.0001
    assert evaluation["buckets_won_vs_strict_v80"] >= 24
    assert evaluation["strength_gate"]["passes"] is True
    assert evaluation["decision"] == "PROMOTE_SINGLE_MODEL"
