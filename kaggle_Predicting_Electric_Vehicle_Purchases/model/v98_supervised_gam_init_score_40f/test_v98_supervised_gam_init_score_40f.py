from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


RUNNER = Path(__file__).with_name("v98_supervised_gam_init_score_40f.py")
SPEC = importlib.util.spec_from_file_location("v98_runner_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
V98 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V98)


def passing_resource_prefix(
    config: dict, pairs: list[tuple[str, int | None]]
) -> tuple[float, list[dict]]:
    started = time.monotonic()
    checks = [
        V98.make_resource_check(
            config,
            started_monotonic=started,
            phase=phase,
            fold=fold,
        )
        for phase, fold in pairs
    ]
    assert all(not check["breaches"] for check in checks)
    return started, checks


def synthetic_resource_check(
    config: dict,
    phase: str,
    fold: int,
    elapsed: float,
    breaches: list[str] | None = None,
) -> dict:
    active_breaches = [] if breaches is None else breaches
    return {
        "timestamp_utc": "2026-09-04T00:00:00+00:00",
        "phase": phase,
        "fold": fold,
        "status": "FAILED" if active_breaches else "OK",
        "breaches": active_breaches,
        "wall_elapsed_seconds": elapsed,
        "wall_clock_budget_seconds": float(config["wall_clock_budget_seconds"]),
        "peak_rss_bytes": 1024,
        "peak_rss_gib": 1024 / 1024**3,
        "peak_rss_budget_bytes": int(config["peak_rss_budget_bytes"]),
        "peak_rss_budget_gib": float(config["memory_budget_gb"]),
        "peak_rss_source": "synthetic",
        "peak_rss_native_unit": "bytes",
    }


def test_unique_probe_archive_is_hash_frozen() -> None:
    config = V98.load_frozen_config()
    evidence = V98.validate_historical_overlap_audit(config)
    assert evidence["decision"] == "GO"
    assert evidence["winning_folds"] == 5
    assert evidence["formal_predictions_reused"] is False
    assert evidence["files"] == config["preflight_probe"]["files"]
    attacked = json.loads(json.dumps(config))
    attacked["preflight_probe"]["files"]["probe.py"] = "0" * 64
    with pytest.raises(ValueError, match="探针归档 SHA"):
        V98.validate_probe_archive(attacked)


def test_ready_status_binds_exact_v97_as_comparison_not_fusion() -> None:
    config = V98.load_frozen_config()
    source_id = "v97_lgbm_fixed_generator_init_score_40f"
    assert config["status"] == "DESIGN_READY_NOT_STARTED"
    assert config["same_mechanism_reference"] == source_id
    assert config["same_mechanism_reference_oof_auc"] == 0.9463024378137885
    assert config["v97_reference_policy"] == (
        "MANDATORY_WHOLE_OOF_COMPARISON_ONLY_NOT_FUSION_MEMBER"
    )
    assert source_id in V98.COMPARISON_DIRS
    assert config["comparison_sources"][source_id]["verifier"] == "verify_complete"


def test_ready_status_rejects_any_frozen_v97_binding_drift(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    config["comparison_sources"]["v97_lgbm_fixed_generator_init_score_40f"][
        "oof_sha256"
    ] = "0" * 64
    path = tmp_path / "forged_ready.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(V98, "CONFIG_PATH", path)
    with pytest.raises(ValueError, match="精确绑定冻结 v97"):
        V98.load_frozen_config()


def test_zero_column_adapter_leaves_v80_static_features_exactly_unchanged() -> None:
    frame = pd.DataFrame(
        {
            "Annual_Income_USD": [60_000.0, 120_000.0],
            "Daily_Commute_km": [30.0, 20.0],
            "Number_of_Cars_Owned": [1, 3],
            "Will_Buy_EV": ["No", "Yes"],
        }
    )
    block = V98.build_pure_v96_zero_column_adapter(frame)
    assert block.shape == (2, 0)
    flipped = frame.copy()
    flipped["Will_Buy_EV"] = ["Yes", "No"]
    pd.testing.assert_frame_equal(
        block, V98.build_pure_v96_zero_column_adapter(flipped)
    )
    x_train = pd.DataFrame({f"f{i}": [i, i + 1] for i in range(62)})
    x_test = x_train.copy()
    out_train, out_test, profile = V98.assert_pure_v96_static_identity(
        x_train, x_test, frame, frame, V98.load_frozen_config()
    )
    pd.testing.assert_frame_equal(out_train, x_train)
    pd.testing.assert_frame_equal(out_test, x_test)
    assert profile["columns"] == []
    assert profile["identical_to_v80_static_values"] is True


def test_tree_recipe_is_v96_exact_and_only_gam_objective_offset_is_added() -> None:
    config = V98.load_frozen_config()
    base = json.loads((V98.V96_DIR / "frozen_config.json").read_text())
    assert config["outer_split_seed"] == 42
    assert base["outer_split_seed"] == 42
    for key in (
        "n_folds",
        "n_inner_folds",
        "inner_te_seed_base",
        "inner_te_seed_formula",
        "model_seed",
        "strict_prior_contract",
        "smooths",
        "te_keys",
        "lightgbm_params",
        "early_stopping_rounds",
        "expected_static_features",
        "expected_te_features",
        "expected_total_features",
        "wall_clock_budget_seconds",
        "peak_rss_budget_bytes",
        "submission_budget",
    ):
        assert config[key] == base[key]
    assert config["supervised_gam"]["expected_feature_count"] == 39
    assert config["supervised_gam"]["interactions"] == []
    assert config["unique_primary_variable"].endswith(
        "expit(margin + raw residual)"
    )


def test_gam_is_exactly_39_columns_and_outer_valid_labels_are_unused() -> None:
    config = V98.load_frozen_config()
    recipe = V98.load_recipe()
    train, test, _ = recipe.base.load_data()
    train = train.iloc[:5000].reset_index(drop=True)
    test = test.iloc[:100].reset_index(drop=True)
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    fit_idx, valid_idx = next(
        V98.StratifiedKFold(n_splits=2, shuffle=True, random_state=42).split(
            np.zeros(len(train)), y
        )
    )
    original = V98.fit_supervised_gam_margins(
        train, test, y, fit_idx, valid_idx, config
    )
    attacked_y = y.copy()
    attacked_y[valid_idx] = 1 - attacked_y[valid_idx]
    attacked = V98.fit_supervised_gam_margins(
        train, test, attacked_y, fit_idx, valid_idx, config
    )
    assert original["profile"]["feature_count"] == 39
    assert original["profile"]["outer_fit_only"] is True
    for name in ("fit_margin", "valid_margin", "test_margin"):
        np.testing.assert_array_equal(original[name], attacked[name])


def test_lgbm_receives_frozen_init_and_eval_init_scores() -> None:
    captured = {}

    class FakeModel:
        def fit(self, x, y, **kwargs):
            captured.update({"x": x, "y": y, **kwargs})

    x_fit = np.zeros((4, 3))
    x_valid = np.ones((2, 3))
    y_fit = np.asarray([0, 1, 0, 1])
    y_valid = np.asarray([0, 1])
    fit_margin = np.asarray([-1.0, 1.0, -0.5, 0.5])
    valid_margin = np.asarray([-0.25, 0.25])
    V98.fit_lgbm_residual_with_gam(
        FakeModel(),
        x_fit,
        y_fit,
        x_valid,
        y_valid,
        fit_margin,
        valid_margin,
        ["a", "b", "c"],
        500,
    )
    np.testing.assert_array_equal(captured["init_score"], fit_margin)
    np.testing.assert_array_equal(captured["eval_init_score"][0], valid_margin)
    assert captured["eval_set"][0][0] is x_valid
    assert captured["eval_set"][0][1] is y_valid


def test_prediction_requires_raw_residual_and_manually_adds_margin() -> None:
    class FakeBooster:
        def predict(self, features, **kwargs):
            assert kwargs == {"raw_score": True, "num_iteration": 7}
            return np.asarray([0.2, -0.4])

    class FakeModel:
        booster_ = FakeBooster()

        def predict_proba(self, features, **kwargs):
            assert kwargs == {"num_iteration": 7}
            residual_probability = V98.expit(np.asarray([0.2, -0.4]))
            return np.column_stack([1.0 - residual_probability, residual_probability])

    margin = np.asarray([0.3, 0.1])
    probability, raw = V98.predict_probability_from_margin_and_raw_residual(
        FakeModel(), np.zeros((2, 3)), margin, 7
    )
    np.testing.assert_array_equal(raw, np.asarray([0.2, -0.4]))
    np.testing.assert_array_equal(probability, V98.expit(margin + raw))


def test_comparison_sources_are_hash_only_frozen_and_drift_rejected() -> None:
    config = V98.load_frozen_config()
    evidence = V98.validate_comparison_source_hashes(config)
    assert set(evidence) == set(V98.COMPARISON_DIRS)
    assert all(
        row["prediction_arrays_parsed"] is False for row in evidence.values()
    )
    attacked = json.loads(json.dumps(config))
    source_id = next(iter(V98.COMPARISON_DIRS))
    attacked["comparison_sources"][source_id]["oof_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="oof_sha256"):
        V98.validate_comparison_source_hashes(attacked)


def test_v96_frozen_source_and_verifier_entrypoint_are_exact(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    evidence = V98.validate_v96_source_hashes(config)
    assert evidence["experiment_id"] == "v96_strict_v80_outer42_matched_control_40f"
    assert evidence["verifier"] == "verify_complete"
    assert evidence["prediction_arrays_parsed"] is False
    attacked = json.loads(json.dumps(config))
    attacked["v96_source"]["verifier"] = "forged_verifier"
    attacked_path = tmp_path / "attacked_config.json"
    attacked_path.write_text(json.dumps(attacked), encoding="utf-8")
    monkeypatch.setattr(V98, "CONFIG_PATH", attacked_path)
    with pytest.raises(ValueError, match="v96 verifier"):
        V98.load_frozen_config()


def test_prediction_artifact_access_schema_is_generated_and_verified_exactly() -> None:
    run_contract = V98.build_run_contract()
    train = pd.DataFrame({"id": [1, 2]})
    test = pd.DataFrame({"id": [3]})
    sources = V98.make_source_manifest(run_contract, train, test, {})
    expected = {
        "strict_v96_oof": "HASH_ONLY_BYTES_NOT_PARSED",
        "strict_v96_test": "HASH_ONLY_BYTES_NOT_PARSED",
        "comparison_oof_test": "HASH_ONLY_BYTES_NOT_PARSED",
        "non_formal_modes": ["audit", "smoke"],
    }
    assert sources["prediction_artifact_access"] == expected
    results = {
        "run_contract_sha256": run_contract["run_contract_sha256"],
        "code_and_input_sha256": {
            name: record["sha256"]
            for name, record in run_contract["sources"].items()
        },
    }
    V98.verify_source_contract(sources, results)
    for mutation in ("missing", "extra"):
        attacked = json.loads(json.dumps(sources))
        if mutation == "missing":
            del attacked["prediction_artifact_access"]["comparison_oof_test"]
        else:
            attacked["prediction_artifact_access"]["forged"] = "HASH_ONLY"
        stored_payload = {
            "experiment_id": attacked["experiment_id"],
            "frozen_config_sha256": attacked["frozen_config_sha256"],
            "sources": attacked["code_and_inputs"],
            "prediction_artifact_access": attacked["prediction_artifact_access"],
            "runtime": attacked["runtime"],
        }
        attacked["run_contract_sha256"] = V98.sha256_json(stored_payload)
        attacked_results = dict(results)
        attacked_results["run_contract_sha256"] = attacked["run_contract_sha256"]
        with pytest.raises(ValueError, match="预测产物访问边界"):
            V98.verify_source_contract(attacked, attacked_results)


def test_prediction_sources_are_parsed_from_same_sha_verified_bytes(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "source.npy"
    expected = np.asarray([0.1, 0.2, 0.3], dtype=np.float64)
    with path.open("wb") as handle:
        np.save(handle, expected)
    frozen_sha256 = V98.sha256_file(path)
    real_np_load = np.load

    def attacked_np_load(file, *args, **kwargs):
        loaded = real_np_load(file, *args, **kwargs)
        if isinstance(file, (str, Path)):
            return loaded[::-1]
        return loaded

    monkeypatch.setattr(V98.np, "load", attacked_np_load)
    np.testing.assert_array_equal(V98.np.load(path), expected[::-1])
    sealed = V98.load_npy_from_sha_verified_bytes(
        path, expected_sha256=frozen_sha256, label="synthetic"
    )
    np.testing.assert_array_equal(sealed, expected)
    formal_loader = inspect.getsource(
        V98.load_all_prediction_arrays_after_verification
    )
    assert "np.load(" not in formal_loader
    assert formal_loader.count("load_npy_from_sha_verified_bytes(") == 4


def test_checkpoint_rejects_margin_or_raw_residual_tamper(tmp_path) -> None:
    fit_idx = np.asarray([0, 1, 3, 4], dtype=np.int64)
    valid_idx = np.asarray([2, 5], dtype=np.int64)
    valid_margin = np.asarray([-0.2, 0.4])
    test_margin = np.asarray([0.1, -0.3, 0.5])
    valid_raw = np.asarray([0.3, -0.1])
    test_raw = np.asarray([0.2, 0.4, -0.2])
    path = tmp_path / "fold_01.npz"
    profile = {
        "feature_count": 39,
        "feature_names_sha256": "a" * 64,
        "fit_rows": 4,
        "valid_rows": 2,
        "test_rows": 3,
        "fit_idx_sha256": V98.hashlib.sha256(fit_idx.tobytes()).hexdigest(),
        "valid_idx_sha256": V98.hashlib.sha256(valid_idx.tobytes()).hexdigest(),
        "logistic_iterations": 3,
        "fit_clip_count": 0,
        "valid_clip_count": 0,
        "test_clip_count": 0,
        "outer_fit_only": True,
    }
    V98.save_checkpoint(
        path,
        fold=1,
        valid_idx=valid_idx,
        valid_pred=V98.expit(valid_margin + valid_raw),
        test_pred=V98.expit(test_margin + test_raw),
        valid_margin=valid_margin,
        test_margin=test_margin,
        valid_raw_residual=valid_raw,
        test_raw_residual=test_raw,
        gam_profile=profile,
        best_iteration=7,
        gain=np.zeros(3),
        split=np.zeros(3),
        fold_auc=0.5,
        early_stop_auc=0.5,
        elapsed_seconds=1.0,
        config_sha256="c" * 64,
        run_contract_sha256="d" * 64,
    )
    V98.load_checkpoint(
        path,
        fold=1,
        fit_idx=fit_idx,
        valid_idx=valid_idx,
        test_rows=3,
        feature_count=3,
        config_sha256="c" * 64,
        run_contract_sha256="d" * 64,
    )
    with pytest.raises(ValueError, match="GAM profile"):
        V98.load_checkpoint(
            path,
            fold=1,
            fit_idx=fit_idx[::-1].copy(),
            valid_idx=valid_idx,
            test_rows=3,
            feature_count=3,
            config_sha256="c" * 64,
            run_contract_sha256="d" * 64,
        )
    with np.load(path, allow_pickle=False) as saved:
        payload = {name: saved[name].copy() for name in saved.files}
    payload["valid_raw_residual"][0] += 0.01
    np.savez_compressed(path, **payload)
    with pytest.raises(ValueError, match=r"margin\+raw residual"):
        V98.load_checkpoint(
            path,
            fold=1,
            fit_idx=fit_idx,
            valid_idx=valid_idx,
            test_rows=3,
            feature_count=3,
            config_sha256="c" * 64,
            run_contract_sha256="d" * 64,
        )


def test_frozen_comparisons_report_all_sources_and_absolute_gap() -> None:
    y = np.asarray([0, 1] * 20, dtype=np.int8)
    folds = list(
        V98.StratifiedKFold(n_splits=4, shuffle=True, random_state=42).split(
            np.zeros(len(y)), y
        )
    )
    candidate = np.linspace(0.02, 0.98, len(y))
    candidate_test = np.linspace(0.1, 0.9, 11)
    source_oof = {
        name: np.roll(candidate, shift)
        for shift, name in enumerate(V98.COMPARISON_DIRS, start=1)
    }
    source_test = {name: candidate_test.copy() for name in source_oof}
    source_results = {}
    for name, values in source_oof.items():
        source_results[name] = {
            "oof_auc": float(V98.roc_auc_score(y, values)),
        }
    result = V98.compute_frozen_comparisons(
        y,
        folds,
        candidate,
        candidate_test,
        source_oof,
        source_test,
        source_results,
    )
    assert set(result) == {*V98.COMPARISON_DIRS, "absolute_target_0.947"}
    assert result["v90_v89_member_verify_budget_retry"]["test_spearman"] == 1.0
    assert result["absolute_target_0.947"]["candidate_oof_gap"] == pytest.approx(
        V98.roc_auc_score(y, candidate) - 0.947
    )


def test_mechanism_gate_is_exactly_plus_point0001_and_24_of_40() -> None:
    config = V98.load_frozen_config()
    promoted = V98.derive_candidate_decision(config, 0.9464, 0.0001, 24)
    assert promoted["decision"] == "PROMOTE_SINGLE_MODEL"
    assert promoted["allowed_for_fusion"] is True
    for delta, wins in ((0.000099999, 24), (0.0001, 23)):
        rejected = V98.derive_candidate_decision(config, 0.9464, delta, wins)
        assert rejected["mechanism_gate"] is False
        assert rejected["allowed_for_fusion"] is False


def test_complete_mechanism_gate_disables_formal_futility() -> None:
    config = V98.load_frozen_config()
    assert config["futility_enabled"] is False
    assert config["futility_disabled_reason"] == (
        "the supervised GAM init-score mechanism gate requires complete 40-fold OOF evidence"
    )


def test_nonformal_data_contract_does_not_load_prediction_arrays(monkeypatch) -> None:
    config = V98.load_frozen_config()
    recipe = V98.load_recipe()

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError(f"non-formal path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V98.np, "load", reject_prediction_load)
    _, _, _, baseline_oof, baseline_test, _ = V98.validate_data_contract(
        config, recipe, load_predictions=False
    )
    assert baseline_oof is None
    assert baseline_test is None


def test_metadata_drift_after_source_verification_still_rejects_before_np_load(
    monkeypatch,
) -> None:
    config = V98.load_frozen_config()
    loads = {"count": 0}

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        loads["count"] += 1
        raise AssertionError(f"TOCTOU path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V98.np, "load", reject_prediction_load)
    forged_token = {
        "all_configured_sources_fully_verified_before_candidate_np_load": True,
        "baseline_results": {"status": "FORGED"},
        "comparison_results": {},
    }
    with pytest.raises(ValueError, match="metadata.*漂移"):
        V98.load_all_prediction_arrays_after_verification(
            config,
            pd.DataFrame({"id": [1], "Will_Buy_EV": ["No"]}),
            pd.DataFrame({"id": [2]}),
            forged_token,
        )
    assert loads["count"] == 0


def test_v96_hash_drift_rejects_before_any_prediction_load(monkeypatch) -> None:
    config = V98.load_frozen_config()
    config["v96_source"]["oof_sha256"] = "0" * 64
    loads = {"count": 0}

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        loads["count"] += 1
        raise AssertionError(f"drift path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V98.np, "load", reject_prediction_load)
    with pytest.raises(ValueError, match="strict v96 oof_sha256"):
        V98.validate_data_contract(config, V98.load_recipe(), load_predictions=True)
    assert loads["count"] == 0


def test_comparison_hash_drift_rejects_before_any_prediction_load(monkeypatch) -> None:
    config = V98.load_frozen_config()
    source_id = "v95_v94_source_verifier_adapter_retry"
    config["comparison_sources"][source_id]["test_sha256"] = "0" * 64
    loads = {"count": 0}

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        loads["count"] += 1
        raise AssertionError(f"drift path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V98.np, "load", reject_prediction_load)
    with pytest.raises(ValueError, match=f"{source_id} test_sha256"):
        V98.load_verified_comparison_predictions(
            config,
            pd.DataFrame({"id": [1], "Will_Buy_EV": ["No"]}),
            pd.DataFrame({"id": [2]}),
        )
    assert loads["count"] == 0


@pytest.mark.parametrize(
    "source_id",
    [
        "v96_strict_v80_outer42_matched_control_40f",
        *V98.COMPARISON_DIRS,
    ],
)
def test_actual_formal_orchestration_rejects_each_source_drift_before_np_load(
    source_id, tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    config["status"] = "DESIGN_READY_NOT_STARTED"
    if source_id == config["v96_source"]["experiment_id"]:
        config["v96_source"]["oof_sha256"] = "0" * 64
        expected_error = "strict v96 oof_sha256"
    else:
        config["comparison_sources"][source_id]["oof_sha256"] = "0" * 64
        expected_error = f"{source_id} oof_sha256"
    loads = {"count": 0}

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        loads["count"] += 1
        raise AssertionError(f"formal drift path called np.load: {args!r} {kwargs!r}")

    work = tmp_path / source_id
    work.mkdir()
    monkeypatch.setattr(V98, "OUT_DIR", work)
    monkeypatch.setattr(V98, "LOCK_PATH", work / "run.lock")
    monkeypatch.setattr(V98, "LOG_PATH", work / "train_log.txt")
    monkeypatch.setattr(V98, "PROGRESS_PATH", work / "progress.jsonl")
    monkeypatch.setattr(V98, "CHECKPOINT_DIR", work / "checkpoints")
    monkeypatch.setattr(V98, "load_frozen_config", lambda: config)
    monkeypatch.setattr(V98.np, "load", reject_prediction_load)
    with pytest.raises(ValueError, match=expected_error):
        V98._train_impl({})
    assert loads["count"] == 0


def test_guarded_smoke_never_calls_lightgbm_fit(monkeypatch, capsys) -> None:
    def reject_fit(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("smoke called LightGBM.fit")

    monkeypatch.setattr(V98.lgb.LGBMClassifier, "fit", reject_fit)
    V98.smoke()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == (
        "SMOKE_OK_GUARDED_SUBSET_NO_FORMAL_PREDICTION_ARRAYS_READ"
    )


def test_formal_v80_identity_binds_ids_sources_and_artifact_hashes(tmp_path) -> None:
    baseline_dir = V98.OUT_DIR / f"pytest_v80_identity_{tmp_path.name}"
    baseline_dir.mkdir()
    try:
        train = pd.DataFrame({"id": [101, 102, 103]})
        test = pd.DataFrame({"id": [201, 202]})
        oof_path = baseline_dir / "oof_proba.npy"
        test_path = baseline_dir / "test_proba.npy"
        np.save(oof_path, np.asarray([0.1, 0.5, 0.9]))
        np.save(test_path, np.asarray([0.2, 0.8]))
        sources = {
            "row_identity": {
                "train_rows": len(train),
                "test_rows": len(test),
                "train_id_sha256": V98.sha256_ids(train["id"]),
                "test_id_sha256": V98.sha256_ids(test["id"]),
            },
            "outputs": {
                "oof_proba": V98.file_record(oof_path),
                "test_proba": V98.file_record(test_path),
            },
        }
        sources_path = baseline_dir / "sources.json"
        V98.atomic_write_json(sources_path, sources)
        baseline = {
            "sources_sha256": V98.sha256_file(sources_path),
            "artifact_sha256": {
                "oof_proba": V98.sha256_file(oof_path),
                "test_proba": V98.sha256_file(test_path),
            },
        }
        V98.validate_v96_prediction_identity(
            train, test, baseline, baseline_dir=baseline_dir
        )
        altered = test.copy()
        altered.loc[1, "id"] = 999
        with pytest.raises(ValueError, match="行身份"):
            V98.validate_v96_prediction_identity(
                train, altered, baseline, baseline_dir=baseline_dir
            )
        baseline["artifact_sha256"]["test_proba"] = "0" * 64
        with pytest.raises(ValueError, match="artifact/source"):
            V98.validate_v96_prediction_identity(
                train, test, baseline, baseline_dir=baseline_dir
            )
    finally:
        for path in baseline_dir.iterdir():
            path.unlink()
        baseline_dir.rmdir()


def test_failed_schemas_and_artifact_invalidation(tmp_path) -> None:
    config = V98.load_frozen_config()
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    for fold in range(1, 11):
        (checkpoints / f"fold_{fold:02d}.npz").write_bytes(b"synthetic")
    _, resources = passing_resource_prefix(
        config, V98.canonical_resource_sequence()[:20]
    )
    results_path = tmp_path / "cv_results.json"
    V98.write_futility_failure(
        config,
        config_sha256=V98.sha256_file(V98.CONFIG_PATH),
        run_contract_sha256="a" * 64,
        fold_rows=[{} for _ in range(10)],
        fold_scores=[0.5 for _ in range(10)],
        best_iterations=[1 for _ in range(10)],
        resource_checks=resources,
        partial_oof_auc=0.499,
        partial_v80_auc=0.5,
        winning_buckets=4,
        results_path=results_path,
        checkpoint_dir=checkpoints,
    )
    failure = json.loads(results_path.read_text(encoding="utf-8"))
    V98.validate_failed_result_schema(
        failure,
        config,
        artifact_root=tmp_path,
        checkpoint_dir=checkpoints,
    )
    assert failure["present_artifacts_are_invalid_for_use"] is True
    assert failure["oof_auc"] is None
    assert failure["oof_delta_vs_base"] is None
    assert failure["present_artifacts"] == [
        f"checkpoints/fold_{fold:02d}.npz" for fold in range(1, 11)
    ]
    attacked = json.loads(json.dumps(failure))
    attacked["resource_checks"][3]["phase"] = "FORGED_PHASE"
    with pytest.raises(ValueError, match="冻结域"):
        V98.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    attacked = json.loads(json.dumps(failure))
    attacked["resource_checks"][3]["fold"] = 999
    with pytest.raises(ValueError, match="冻结域"):
        V98.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    attacked = json.loads(json.dumps(failure))
    attacked["resource_checks"][3]["wall_elapsed_seconds"] = 0.0
    with pytest.raises(ValueError, match="elapsed 序列回退"):
        V98.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    attacked = json.loads(json.dumps(failure))
    attacked["resource_checks"][3]["breaches"] = ["WALL_CLOCK_BUDGET"]
    attacked["resource_checks"][3]["status"] = "FAILED"
    with pytest.raises(ValueError, match="breach 复算"):
        V98.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    (checkpoints / "fold_01.npz").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="present_artifact_records"):
        V98.validate_failed_result_schema(
            failure,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )


def test_exception_failure_closes_after_resource_pair_before_fold_commit(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    checks = [
        synthetic_resource_check(config, "BEFORE_FOLD", 1, 1.0),
        synthetic_resource_check(config, "AFTER_FOLD", 1, 2.0),
    ]
    monkeypatch.setattr(
        V98,
        "make_resource_check",
        lambda config, *, started_monotonic, phase, fold: synthetic_resource_check(
            config, phase, fold, 3.0
        ),
    )
    results_path = tmp_path / "cv_results.json"
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    payload = V98.write_exception_failure(
        config,
        error=RuntimeError("attack window"),
        started_monotonic=0.0,
        config_sha256="a" * 64,
        run_contract_sha256="b" * 64,
        fold_rows=[],
        fold_scores=[],
        best_iterations=[],
        resource_checks=checks,
        results_path=results_path,
        checkpoint_dir=checkpoint_dir,
    )
    assert payload["status"] == "FAILED"
    assert payload["completed_folds"] == 0
    assert [check["phase"] for check in payload["resource_checks"]] == [
        "FAILED_EXCEPTION"
    ]
    assert payload["interrupted_state"]["dropped_resource_checks"] == 2
    assert [
        item["phase"]
        for item in payload["interrupted_state"]["dropped_resource_tail"]
    ] == ["BEFORE_FOLD", "AFTER_FOLD"]
    assert json.loads(results_path.read_text(encoding="utf-8")) == payload


def test_candidate_outputs_bind_path_size_and_sha(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(V98, "PROJECT_DIR", tmp_path)
    output = tmp_path / "oof_proba.npy"
    output.write_bytes(b"candidate-output")
    record = V98.candidate_output_record(output)
    results = {"artifact_sha256": {"oof_proba": record["sha256"]}}
    paths = {"oof_proba": output}
    V98.validate_candidate_output_records(
        {"outputs": {"oof_proba": dict(record)}}, results, paths
    )
    attacks = {
        "path": "model/attacker/oof_proba.npy",
        "size_bytes": record["size_bytes"] + 1,
        "sha256": "0" * 64,
    }
    for field, replacement in attacks.items():
        attacked = dict(record)
        attacked[field] = replacement
        with pytest.raises(ValueError, match="path/size_bytes/sha256"):
            V98.validate_candidate_output_records(
                {"outputs": {"oof_proba": attacked}}, results, paths
            )


def test_staged_complete_transition_rejects_nonresource_mutation() -> None:
    config = V98.load_frozen_config()
    pre = V98.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_preverify_resource_phase"],
        fold=V98.N_FOLDS,
    )
    post = V98.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_postverify_resource_phase"],
        fold=V98.N_FOLDS,
    )
    staged = {
        "status": "STAGED_COMPLETE_PENDING_VERIFY",
        "elapsed_seconds": pre["wall_elapsed_seconds"],
        "wall_clock_elapsed_seconds": pre["wall_elapsed_seconds"],
        "peak_rss_bytes": pre["peak_rss_bytes"],
        "peak_rss_gib": pre["peak_rss_gib"],
        "resource_checks": [pre],
        "final_resource_check": pre,
        "oof_auc": 0.9,
    }
    final = json.loads(json.dumps(staged))
    final.update(
        {
            "status": "COMPLETE",
            "elapsed_seconds": post["wall_elapsed_seconds"],
            "wall_clock_elapsed_seconds": post["wall_elapsed_seconds"],
            "peak_rss_bytes": post["peak_rss_bytes"],
            "peak_rss_gib": post["peak_rss_gib"],
            "resource_checks": [pre, post],
            "final_resource_check": post,
        }
    )
    V98.validate_staged_complete_transition(staged, final, config)
    final["oof_auc"] = 0.91
    with pytest.raises(ValueError, match="非授权字段"):
        V98.validate_staged_complete_transition(staged, final, config)


def test_final_complete_pending_is_fully_verified_immutable_and_once_committed(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    work = V98.OUT_DIR / f"pytest_finalize_success_{tmp_path.name}"
    work.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        V98.atomic_write_json(pending, {"status": "COMPLETE", "value": 7})
        _, checks = passing_resource_prefix(
            config, V98.canonical_resource_sequence()[:-2]
        )
        verify_calls = []
        commit_calls = []
        original_commit = V98.commit_complete_pending

        def verify_stub(*, results_path, allow_staged):
            verify_calls.append((results_path, allow_staged))
            assert json.loads(results_path.read_text())["status"] == "COMPLETE"
            return {"status": "SYNTHETIC_FULL_VERIFY_OK"}

        def commit_spy(pending_results_path, results_path):
            commit_calls.append((pending_results_path, results_path))
            original_commit(pending_results_path, results_path)

        monkeypatch.setattr(V98, "verify_complete", verify_stub)
        monkeypatch.setattr(V98, "commit_complete_pending", commit_spy)
        monkeypatch.setattr(V98, "PROGRESS_PATH", work / "progress.jsonl")
        committed = V98.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=time.monotonic(),
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[
                {"strict_candidate_auc": 0.5, "best_iteration": 1}
                for _ in range(V98.N_FOLDS)
            ],
            fold_scores=[0.5 for _ in range(V98.N_FOLDS)],
            best_iterations=[1 for _ in range(V98.N_FOLDS)],
            resource_checks=checks,
            logger=V98.RunLogger(work / "synthetic.log"),
            checkpoint_dir=work / "checkpoints",
        )
        assert committed is True
        assert verify_calls == [(pending, False)]
        assert commit_calls == [(pending, results)]
        assert not pending.exists()
        assert json.loads(results.read_text())["status"] == "COMPLETE"
    finally:
        for path in sorted(work.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        work.rmdir()


def test_final_complete_rejects_verifier_mutation_without_commit(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    work = V98.OUT_DIR / f"pytest_finalize_mutation_{tmp_path.name}"
    work.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE"}', encoding="utf-8")
        _, checks = passing_resource_prefix(
            config, V98.canonical_resource_sequence()[:-2]
        )
        commits = {"count": 0}

        def mutating_verify(*, results_path, allow_staged):
            assert allow_staged is False
            results_path.write_text('{"status":"COMPLETE","forged":true}')

        def reject_commit(*args, **kwargs):  # noqa: ANN002, ANN003
            commits["count"] += 1
            raise AssertionError("mutated pending must not commit")

        monkeypatch.setattr(V98, "verify_complete", mutating_verify)
        monkeypatch.setattr(V98, "commit_complete_pending", reject_commit)
        with pytest.raises(RuntimeError, match="FULL_COMPLETE_VERIFIER"):
            V98.finalize_verified_complete(
                config,
                pending_results_path=pending,
                results_path=results,
                started_monotonic=time.monotonic(),
                config_sha256="a" * 64,
                run_contract_sha256="b" * 64,
                fold_rows=[{} for _ in range(V98.N_FOLDS)],
                fold_scores=[0.5 for _ in range(V98.N_FOLDS)],
                best_iterations=[1 for _ in range(V98.N_FOLDS)],
                resource_checks=checks,
                logger=V98.RunLogger(work / "synthetic.log"),
                checkpoint_dir=work / "checkpoints",
            )
        assert commits["count"] == 0
        assert not results.exists()
    finally:
        for path in sorted(work.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        work.rmdir()


def test_guard_period_pending_tamper_fails_closed_without_forged_complete(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    work = V98.OUT_DIR / f"pytest_guard_tamper_{tmp_path.name}"
    work.mkdir()
    checkpoints = work / "checkpoints"
    checkpoints.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE","trusted":true}', encoding="utf-8")
        started, checks = passing_resource_prefix(
            config, V98.canonical_resource_sequence()[:-2]
        )
        original_resource_check = V98.make_resource_check

        def verify_stub(*, results_path, allow_staged):
            assert results_path == pending
            assert allow_staged is False

        def tampering_guard(config, *, started_monotonic, phase, fold):
            if phase == config["complete_commit_guard_phase"]:
                pending.write_text(
                    '{"status":"COMPLETE","forged":true}', encoding="utf-8"
                )
            return original_resource_check(
                config,
                started_monotonic=started_monotonic,
                phase=phase,
                fold=fold,
            )

        monkeypatch.setattr(V98, "verify_complete", verify_stub)
        monkeypatch.setattr(V98, "make_resource_check", tampering_guard)
        monkeypatch.setattr(V98, "PROGRESS_PATH", work / "progress.jsonl")
        committed = V98.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=started,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[
                {"strict_candidate_auc": 0.5, "best_iteration": 1}
                for _ in range(V98.N_FOLDS)
            ],
            fold_scores=[0.5 for _ in range(V98.N_FOLDS)],
            best_iterations=[1 for _ in range(V98.N_FOLDS)],
            resource_checks=checks,
            logger=V98.RunLogger(work / "synthetic.log"),
            checkpoint_dir=checkpoints,
        )
        assert committed is False
        failure = json.loads(results.read_text())
        assert failure["status"] == "FAILED"
        assert failure["failure_attribution"] == "FAILED_EXCEPTION"
        assert "FINAL_PENDING_SEAL_DRIFT" in failure["error"]
        assert not pending.exists()
        assert '"forged":true' not in results.read_text()
    finally:
        for path in sorted(work.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        work.rmdir()


def test_post_commit_tamper_is_rolled_back_to_failed_not_left_complete(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    work = V98.OUT_DIR / f"pytest_post_commit_tamper_{tmp_path.name}"
    work.mkdir()
    checkpoints = work / "checkpoints"
    checkpoints.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE","trusted":true}', encoding="utf-8")
        started, checks = passing_resource_prefix(
            config, V98.canonical_resource_sequence()[:-2]
        )
        original_commit = V98.commit_complete_pending

        def verify_stub(*, results_path, allow_staged):
            assert results_path == pending
            assert allow_staged is False

        def tampering_commit(pending_results_path, results_path):
            original_commit(pending_results_path, results_path)
            results_path.write_text(
                '{"status":"COMPLETE","forged_after_commit":true}',
                encoding="utf-8",
            )

        monkeypatch.setattr(V98, "verify_complete", verify_stub)
        monkeypatch.setattr(V98, "commit_complete_pending", tampering_commit)
        monkeypatch.setattr(V98, "PROGRESS_PATH", work / "progress.jsonl")
        committed = V98.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=started,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[
                {"strict_candidate_auc": 0.5, "best_iteration": 1}
                for _ in range(V98.N_FOLDS)
            ],
            fold_scores=[0.5 for _ in range(V98.N_FOLDS)],
            best_iterations=[1 for _ in range(V98.N_FOLDS)],
            resource_checks=checks,
            logger=V98.RunLogger(work / "synthetic.log"),
            checkpoint_dir=checkpoints,
        )
        assert committed is False
        failure = json.loads(results.read_text())
        assert failure["status"] == "FAILED"
        assert failure["failure_attribution"] == "FAILED_EXCEPTION"
        assert "POST_COMMIT_SEAL_DRIFT" in failure["error"]
        assert "forged_after_commit" not in results.read_text()
    finally:
        for path in sorted(work.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        work.rmdir()


def test_post_seal_commit_guard_blocks_3599_to_3601_attack(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    pending = tmp_path / ".cv_results.staged.json"
    results = tmp_path / "cv_results.json"
    pending.write_text("{}", encoding="utf-8")
    resource_checks: list[dict] = []
    committed = {"called": False}
    captured: dict = {}

    monkeypatch.setattr(V98, "verify_complete", lambda **kwargs: {})
    seal = {
        "device": 1,
        "inode": 1,
        "mode": 1,
        "size_bytes": 2,
        "mtime_ns": 1,
        "sha256": "a" * 64,
        "content": b"{}",
    }
    monkeypatch.setattr(V98, "capture_regular_file_seal", lambda path: seal)
    monkeypatch.setattr(
        V98,
        "record_resource_check",
        lambda checks, check: checks.append(check),
    )

    def fake_resource_check(config, *, started_monotonic, phase, fold):
        elapsed = 3599.0
        breaches: list[str] = []
        if phase in {"POST_SEAL_COMMIT_GUARD", "FAILED"}:
            elapsed = 3601.0
            breaches = ["WALL_CLOCK_BUDGET"]
        return synthetic_resource_check(config, phase, fold, elapsed, breaches)

    monkeypatch.setattr(V98, "make_resource_check", fake_resource_check)

    def forbidden_commit(*args, **kwargs):  # noqa: ANN002, ANN003
        committed["called"] = True

    monkeypatch.setattr(V98, "commit_complete_pending", forbidden_commit)

    def capture_failure(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["trigger_check"] = args[7]
        captured["failure_check"] = args[8]

    monkeypatch.setattr(V98, "write_resource_failure", capture_failure)

    class Logger:
        def emit(self, message: str) -> None:
            captured["log"] = message

    outcome = V98.finalize_verified_complete(
        config,
        pending_results_path=pending,
        results_path=results,
        started_monotonic=0.0,
        config_sha256="a" * 64,
        run_contract_sha256="b" * 64,
        fold_rows=[],
        fold_scores=[],
        best_iterations=[],
        resource_checks=resource_checks,
        logger=Logger(),
        checkpoint_dir=tmp_path / "checkpoints",
    )
    assert outcome is False
    assert committed["called"] is False
    assert not pending.exists()
    assert captured["trigger_check"]["phase"] == "POST_SEAL_COMMIT_GUARD"
    assert captured["trigger_check"]["wall_elapsed_seconds"] == 3601.0
    assert [check["phase"] for check in resource_checks] == [
        "POST_COMPLETE_FILE_VERIFY_GUARD",
        "POST_SEAL_COMMIT_GUARD",
        "FAILED",
    ]


def test_post_verify_resource_guard_fails_closed_without_complete_commit(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    work = V98.OUT_DIR / f"pytest_finalize_budget_{tmp_path.name}"
    work.mkdir()
    checkpoints = work / "checkpoints"
    checkpoints.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE"}', encoding="utf-8")
        started, checks = passing_resource_prefix(
            config, V98.canonical_resource_sequence()[:-2]
        )
        original_resource_check = V98.make_resource_check
        commits = {"count": 0}

        def verify_stub(*, results_path, allow_staged):
            assert results_path == pending
            assert allow_staged is False

        def over_budget_check(config, *, started_monotonic, phase, fold):
            check = original_resource_check(
                config,
                started_monotonic=started_monotonic,
                phase=phase,
                fold=fold,
            )
            check["wall_elapsed_seconds"] = 3600.0
            check["breaches"] = ["WALL_CLOCK_BUDGET"]
            check["status"] = "FAILED"
            return check

        def reject_commit(*args, **kwargs):  # noqa: ANN002, ANN003
            commits["count"] += 1
            raise AssertionError("over-budget pending must not commit")

        monkeypatch.setattr(V98, "verify_complete", verify_stub)
        monkeypatch.setattr(V98, "make_resource_check", over_budget_check)
        monkeypatch.setattr(V98, "commit_complete_pending", reject_commit)
        monkeypatch.setattr(V98, "PROGRESS_PATH", work / "progress.jsonl")
        committed = V98.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=started,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[{} for _ in range(V98.N_FOLDS)],
            fold_scores=[0.5 for _ in range(V98.N_FOLDS)],
            best_iterations=[1 for _ in range(V98.N_FOLDS)],
            resource_checks=checks,
            logger=V98.RunLogger(work / "synthetic.log"),
            checkpoint_dir=checkpoints,
        )
        assert committed is False
        assert commits["count"] == 0
        assert not pending.exists()
        failure = json.loads(results.read_text())
        assert failure["status"] == "FAILED"
        assert failure["failure_phase"] == "POST_COMPLETE_FILE_VERIFY_GUARD"
        assert failure["failure_attribution"] == "WALL_CLOCK_BUDGET"
    finally:
        for path in sorted(work.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        work.rmdir()


def test_formal_exception_closes_before_flock_release(
    tmp_path, monkeypatch
) -> None:
    config = V98.load_frozen_config()
    run_contract = V98.build_run_contract()
    results_path = tmp_path / "cv_results.json"
    pending_path = tmp_path / ".cv_results.staged.synthetic.json"
    pending_path.write_text("staged-but-unverified", encoding="utf-8")
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    (checkpoints / "fold_01.npz").write_bytes(b"synthetic-checkpoint")
    lock_path = tmp_path / "run.lock"
    state = {
        "formal_scope_started": True,
        "started_monotonic": time.monotonic(),
        "config": config,
        "config_hash": run_contract["frozen_config_sha256"],
        "run_contract_hash": run_contract["run_contract_sha256"],
        "results_path": results_path,
        "pending_results_path": pending_path,
        "fold_rows": [],
        "fold_scores": [],
        "best_iterations": [],
        "resource_checks": [],
    }
    original_writer = V98.write_exception_failure
    observed = {"second_instance_blocked_during_close": False}

    def writer_with_concurrency_probe(*args, **kwargs):  # noqa: ANN002, ANN003
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import fcntl,sys; "
                    "h=open(sys.argv[1],'a+'); "
                    "\ntry: fcntl.flock(h.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)"
                    "\nexcept BlockingIOError: sys.exit(7)"
                    "\nsys.exit(0)"
                ),
                str(lock_path),
            ],
            check=False,
        )
        if probe.returncode != 7:
            raise AssertionError("FAILED_EXCEPTION 写入时 flock 已释放")
        observed["second_instance_blocked_during_close"] = True
        return original_writer(*args, **kwargs)

    monkeypatch.setattr(V98, "write_exception_failure", writer_with_concurrency_probe)
    monkeypatch.setattr(V98, "CHECKPOINT_DIR", checkpoints)
    with pytest.raises(RuntimeError, match="staged verify"):
        with V98.exclusive_run_lock(
            lock_path,
            run_contract["run_contract_sha256"],
            failure_state=state,
        ):
            raise RuntimeError("synthetic staged verify exception")
    failure = json.loads(results_path.read_text(encoding="utf-8"))
    assert failure["status"] == "FAILED"
    assert failure["failure_attribution"] == "FAILED_EXCEPTION"
    assert failure["error_type"] == "RuntimeError"
    assert failure["present_artifacts_are_invalid_for_use"] is True
    assert not pending_path.exists()
    assert state["exception_closed_inside_flock"] is True
    assert observed["second_instance_blocked_during_close"] is True
    verified = V98.verify_failed_closed(
        results_path=results_path,
        checkpoint_dir=checkpoints,
    )
    assert verified["status"] == (
        "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ"
    )
