from __future__ import annotations

import ast
import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
from scipy.stats import norm


RUNNER = Path(__file__).with_name("v97_lgbm_fixed_generator_init_score_40f.py")
SPEC = importlib.util.spec_from_file_location("v97_runner_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
V97 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V97)


class CapturingModel:
    def __init__(self, raw: np.ndarray | None = None) -> None:
        self.fit_args: tuple = ()
        self.fit_kwargs: dict = {}
        self.raw = raw

    def fit(self, *args, **kwargs):
        self.fit_args = args
        self.fit_kwargs = kwargs
        return self

    def predict_proba(self, features, **kwargs):
        assert kwargs == {"num_iteration": 11, "raw_score": True}
        if self.raw is not None:
            return self.raw
        return np.linspace(-0.4, 0.4, len(features), dtype=np.float64)


def synthetic_formula_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Annual_Income_USD": [0.0, 50_000.0, 100_000.0, 200_000.0],
            "Environmental_Concern_Level": [1.0, 2.0, 4.0, 5.0],
            "Subsidy_Available": ["No", "Yes", "No", "Yes"],
            "Range_Anxiety_Level": ["Low", "Medium", "High", "Low"],
            "Will_Buy_EV": ["No", "Yes", "No", "Yes"],
        }
    )


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


def test_frozen_preregistration_and_evidence_hashes_are_exact() -> None:
    config = V97.load_frozen_config()
    assert config["experiment_id"] == V97.EXPERIMENT_ID
    assert config["base"] == "v96_strict_v80_outer42_matched_control_40f"
    assert config["base_oof_auc"] == 0.9462430073165773
    assert config["outer_split_seed"] == 42
    assert config["n_folds"] == 40
    assert config["inner_te_seed_base"] == 104_395_303
    assert config["expected_static_features"] == 62
    assert config["expected_te_features"] == 51
    assert config["expected_total_features"] == 113
    assert config["wall_clock_budget_seconds"] == 3600
    assert config["peak_rss_budget_bytes"] == 16 * 1024**3
    assert config["cpu_threads"] == 8
    assert config["submission_budget"] == 0
    assert config["complete_post_seal_commit_guard_phase"] == "POST_SEAL_COMMIT_GUARD"
    assert config["training_authorized_in_creation_task"] is False
    assert config["formal_requires_complete_40_folds"] is True
    evidence = config["preflight_evidence"]
    assert V97.sha256_file(V97.PREFLIGHT_PROBE_PATH) == evidence[
        "temporary_probe_sha256"
    ]
    assert V97.sha256_file(V97.PUBLIC_SOURCE_EVIDENCE_PATH) == evidence[
        "public_source_sha256"
    ]
    probe = json.loads(V97.PREFLIGHT_PROBE_PATH.read_text())
    source = json.loads(V97.PUBLIC_SOURCE_EVIDENCE_PATH.read_text())
    assert probe["decision"] == "FORMAL_CANDIDATE_GO"
    assert probe["n_folds"] == 5
    assert probe["no_test_prediction"] is True
    assert source["kaggle_notebook_ref"] == "cdeotte/fable-5-1-xgb-starter"
    assert source["kaggle_notebook_version"] == 1
    assert source["notebook_sha256"] == evidence["public_notebook_sha256"]
    assert source["formula_sha256"] == config["fixed_margin"]["formula_sha256"]


def test_v96_recipe_and_all_frozen_source_hashes_are_current() -> None:
    config = V97.load_frozen_config()
    baseline = V97.validate_v96_contract(config, V97.load_recipe())
    assert baseline["status"] == "COMPLETE"
    assert baseline["oof_auc"] == config["base_oof_auc"]
    assert V97.validate_v96_source_hashes(config)["prediction_arrays_parsed"] is False
    comparison = V97.validate_comparison_source_hashes(config)
    assert set(comparison) == set(V97.COMPARISON_DIRS)
    assert all(not row["prediction_arrays_parsed"] for row in comparison.values())


def test_history_manifest_is_recomputed_and_no_equivalent_v1_v96_exists() -> None:
    config = V97.load_frozen_config()
    evidence = V97.validate_historical_overlap_audit(config)
    assert evidence["decision"].endswith("IN_V1_V96")
    assert evidence["equivalent_existing_versions"] == []
    assert evidence["manifest"]["maximum_version_inclusive"] == 96
    assert evidence["manifest"]["required_v80_v96_covered"] is True


def test_fixed_generator_formula_is_exact_rowwise_and_label_free() -> None:
    frame = synthetic_formula_frame()
    margin = V97.build_fixed_generator_margin(frame)
    score = np.asarray([0.6, 2.8, 0.6, 7.4])
    p0 = np.clip(norm.cdf(score - 5.5), 1e-6, 1 - 1e-6)
    expected = np.log(p0 / (1 - p0))
    np.testing.assert_allclose(margin, expected, atol=1e-15, rtol=0.0)
    changed = frame.copy()
    changed["Will_Buy_EV"] = ["Yes", "No", "Yes", "No"]
    assert np.array_equal(margin, V97.build_fixed_generator_margin(changed))
    with pytest.raises(ValueError, match="缺列"):
        V97.build_fixed_generator_margin(frame.drop(columns="Annual_Income_USD"))


def test_fit_api_forces_train_and_validation_init_scores() -> None:
    model = CapturingModel()
    x_fit = np.zeros((3, 2), dtype=np.float32)
    x_valid = np.zeros((2, 2), dtype=np.float32)
    y_fit = np.asarray([0, 1, 0], dtype=np.int8)
    y_valid = np.asarray([1, 0], dtype=np.int8)
    train_margin = np.asarray([-2.0, -1.0, 0.5])
    valid_margin = np.asarray([0.3, 0.7])
    V97.fit_lgbm_residual_with_fixed_margin(
        model,
        x_fit,
        y_fit,
        x_valid,
        y_valid,
        train_margin,
        valid_margin,
        feature_name=["a", "b"],
        early_stopping_rounds=500,
    )
    assert np.array_equal(model.fit_kwargs["init_score"], train_margin)
    assert len(model.fit_kwargs["eval_init_score"]) == 1
    assert np.array_equal(model.fit_kwargs["eval_init_score"][0], valid_margin)
    assert model.fit_kwargs["eval_set"][0][0] is x_valid
    with pytest.raises(ValueError, match="长度"):
        V97.fit_lgbm_residual_with_fixed_margin(
            model,
            x_fit,
            y_fit,
            x_valid,
            y_valid,
            train_margin[:2],
            valid_margin,
            feature_name=["a", "b"],
            early_stopping_rounds=500,
        )


def test_predict_api_forces_raw_score_then_adds_same_margin() -> None:
    x = np.zeros((4, 2), dtype=np.float32)
    margin = np.asarray([-3.0, -1.0, 0.0, 2.0])
    model = CapturingModel()
    probability, raw = V97.predict_probability_from_margin_and_raw_residual(
        model, x, margin, best_iteration=11
    )
    np.testing.assert_array_equal(probability, expit(margin + raw))
    assert not np.array_equal(probability, expit(raw))
    with pytest.raises(ValueError, match="shape"):
        V97.predict_probability_from_margin_and_raw_residual(
            CapturingModel(np.zeros((4, 2))), x, margin, best_iteration=11
        )


def test_checkpoint_independently_rebuilds_margin_plus_raw_and_rejects_attack(
    tmp_path: Path,
) -> None:
    valid_idx = np.asarray([1, 5, 8], dtype=np.int64)
    valid_margin = np.asarray([-2.0, 0.1, 1.2])
    test_margin = np.asarray([-1.3, 0.7])
    valid_raw = np.asarray([0.2, -0.4, 0.8])
    test_raw = np.asarray([0.5, -0.2])
    valid_pred = expit(valid_margin + valid_raw)
    test_pred = expit(test_margin + test_raw)
    path = tmp_path / "fold_01.npz"
    V97.save_checkpoint(
        path,
        fold=1,
        valid_idx=valid_idx,
        valid_pred=valid_pred,
        test_pred=test_pred,
        valid_raw_residual=valid_raw,
        test_raw_residual=test_raw,
        eval_auc=0.75,
        best_iteration=11,
        gain=np.zeros(4),
        split=np.zeros(4),
        fold_auc=0.75,
        elapsed_seconds=1.0,
        config_sha256="a" * 64,
        run_contract_sha256="b" * 64,
    )
    loaded = V97.load_checkpoint(
        path,
        fold=1,
        valid_idx=valid_idx,
        test_rows=2,
        feature_count=4,
        config_sha256="a" * 64,
        run_contract_sha256="b" * 64,
        valid_margin=valid_margin,
        test_margin=test_margin,
    )
    np.testing.assert_array_equal(loaded["valid_pred"], valid_pred)
    with pytest.raises(ValueError, match=r"margin \+ raw residual"):
        V97.load_checkpoint(
            path,
            fold=1,
            valid_idx=valid_idx,
            test_rows=2,
            feature_count=4,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            valid_margin=valid_margin + 0.01,
            test_margin=test_margin,
        )
    with pytest.raises(ValueError, match="合同哈希"):
        V97.load_checkpoint(
            path,
            fold=1,
            valid_idx=valid_idx,
            test_rows=2,
            feature_count=4,
            config_sha256="a" * 64,
            run_contract_sha256="0" * 64,
            valid_margin=valid_margin,
            test_margin=test_margin,
        )


def test_prediction_source_is_parsed_from_same_sha_verified_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.npy"
    expected = np.asarray([0.1, 0.2, 0.3], dtype=np.float64)
    with path.open("wb") as handle:
        np.save(handle, expected)
    frozen_sha256 = V97.sha256_file(path)
    real_np_load = np.load

    def attacked_np_load(file, *args, **kwargs):
        loaded = real_np_load(file, *args, **kwargs)
        if isinstance(file, (str, Path)):
            return loaded[::-1]
        return loaded

    monkeypatch.setattr(V97.np, "load", attacked_np_load)
    np.testing.assert_array_equal(V97.np.load(path), expected[::-1])
    sealed = V97.load_npy_from_sha_verified_bytes(
        path, expected_sha256=frozen_sha256, label="synthetic"
    )
    np.testing.assert_array_equal(sealed, expected)
    formal_loader = inspect.getsource(
        V97.load_all_prediction_arrays_after_verification
    )
    assert "np.load(" not in formal_loader
    assert formal_loader.count("load_npy_from_sha_verified_bytes(") == 4


def test_post_seal_commit_guard_blocks_3599_to_3601_attack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = V97.load_frozen_config()
    pending = tmp_path / ".cv_results.staged.json"
    results = tmp_path / "cv_results.json"
    pending.write_text("{}", encoding="utf-8")
    resource_checks: list[dict] = []
    committed = {"called": False}
    captured: dict = {}

    monkeypatch.setattr(V97, "verify_complete", lambda **kwargs: {})
    seal = {
        "device": 1,
        "inode": 1,
        "mode": 1,
        "size_bytes": 2,
        "mtime_ns": 1,
        "sha256": "a" * 64,
        "content": b"{}",
    }
    monkeypatch.setattr(V97, "capture_regular_file_seal", lambda path: seal)
    monkeypatch.setattr(
        V97,
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

    monkeypatch.setattr(V97, "make_resource_check", fake_resource_check)

    def forbidden_commit(*args, **kwargs):
        committed["called"] = True

    monkeypatch.setattr(V97, "commit_complete_pending", forbidden_commit)

    def capture_failure(*args, **kwargs):
        captured["trigger_check"] = args[7]
        captured["failure_check"] = args[8]

    monkeypatch.setattr(V97, "write_resource_failure", capture_failure)

    class Logger:
        def emit(self, message: str) -> None:
            captured["log"] = message

    outcome = V97.finalize_verified_complete(
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


def test_exception_failure_closes_after_resource_pair_before_fold_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = V97.load_frozen_config()
    checks = [
        synthetic_resource_check(config, "BEFORE_FOLD", 1, 1.0),
        synthetic_resource_check(config, "AFTER_FOLD", 1, 2.0),
    ]
    monkeypatch.setattr(
        V97,
        "make_resource_check",
        lambda config, *, started_monotonic, phase, fold: synthetic_resource_check(
            config, phase, fold, 3.0
        ),
    )
    results_path = tmp_path / "cv_results.json"
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    payload = V97.write_exception_failure(
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
        item["phase"] for item in payload["interrupted_state"]["dropped_resource_tail"]
    ] == ["BEFORE_FOLD", "AFTER_FOLD"]
    assert json.loads(results_path.read_text(encoding="utf-8")) == payload


def test_candidate_outputs_bind_path_size_and_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(V97, "PROJECT_DIR", tmp_path)
    output = tmp_path / "oof_proba.npy"
    output.write_bytes(b"candidate-output")
    record = V97.candidate_output_record(output)
    results = {"artifact_sha256": {"oof_proba": record["sha256"]}}
    paths = {"oof_proba": output}
    V97.validate_candidate_output_records(
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
            V97.validate_candidate_output_records(
                {"outputs": {"oof_proba": attacked}}, results, paths
            )


def test_formal_runner_has_single_guarded_fit_and_predict_paths() -> None:
    train_source = inspect.getsource(V97._train_impl)
    fit_source = inspect.getsource(V97.fit_lgbm_residual_with_fixed_margin)
    predict_source = inspect.getsource(
        V97.predict_probability_from_margin_and_raw_residual
    )
    assert "model.fit(" not in train_source
    assert "fit_lgbm_residual_with_fixed_margin(" in train_source
    assert "init_score=train_margin" in fit_source
    assert "eval_init_score=[valid_margin]" in fit_source
    assert "raw_score=True" in predict_source
    assert "expit(margin + raw)" in predict_source
    assert train_source.count("predict_probability_from_margin_and_raw_residual(") == 2


def test_smoke_ast_has_no_statements_after_terminal_return() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    smoke_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "smoke"
    )
    direct_returns = [
        index
        for index, statement in enumerate(smoke_node.body)
        if isinstance(statement, ast.Return)
    ]
    assert direct_returns == []
    assert isinstance(smoke_node.body[-1], ast.Expr)
    assert isinstance(smoke_node.body[-1].value, ast.Call)
    assert isinstance(smoke_node.body[-1].value.func, ast.Name)
    assert smoke_node.body[-1].value.func.id == "print"


def test_formal_train_ast_has_no_disabled_futility_path_or_keys() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    train_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_train_impl"
    )
    identifiers = {
        node.id.lower() for node in ast.walk(train_node) if isinstance(node, ast.Name)
    }
    string_literals = {
        node.value.lower()
        for node in ast.walk(train_node)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert not any("futility" in identifier for identifier in identifiers)
    assert not any("futility" in literal for literal in string_literals)
    assert {
        "futility_enabled",
        "futility_disabled_reason",
        "futility_check_after_folds",
        "futility_delta_below",
        "futility_max_winning_buckets",
    }.isdisjoint(string_literals)


def test_gate_boundaries_and_permissions_are_frozen() -> None:
    config = V97.load_frozen_config()
    promoted = V97.derive_candidate_decision(config, 0.9465, 0.0001, 24)
    assert promoted["decision"] == "PROMOTE_SINGLE_MODEL"
    assert promoted["allowed_for_fusion"] is True
    below_v90 = V97.derive_candidate_decision(config, 0.9463, 0.0001, 24)
    assert (
        below_v90["decision"]
        == "ELIGIBLE_FOR_SEPARATE_SMALL_FUSION_PREREGISTRATION_ONLY"
    )
    assert below_v90["allowed_for_fusion"] is False
    assert below_v90["eligible_for_separate_small_fusion_preregistration"] is True
    assert V97.derive_candidate_decision(config, 0.947, 0.000099999, 40)[
        "decision"
    ] == "STOP"
    assert V97.derive_candidate_decision(config, 0.947, 0.001, 23)[
        "decision"
    ] == "STOP"


def test_run_contract_includes_preflight_history_and_base_without_loading_arrays() -> None:
    contract = V97.build_run_contract()
    assert contract["prediction_artifact_access"] == V97.expected_prediction_artifact_access()
    for key in (
        "v96_runner",
        "v96_oof",
        "v96_test",
        "preflight_probe_evidence",
        "public_source_evidence",
        "history_formula_manifest",
    ):
        assert key in contract["sources"]
    assert len(contract["run_contract_sha256"]) == 64


def test_no_forbidden_seed_or_formal_artifact_exists_at_preregistration() -> None:
    forbidden = ("104" + "743", "104" + "729")
    for path in RUNNER.parent.iterdir():
        if path.is_file() and path.suffix in {".py", ".json", ".md"}:
            text = path.read_text(encoding="utf-8")
            assert not any(seed in text for seed in forbidden)
    for name in (
        "cv_results.json",
        "oof_proba.npy",
        "test_proba.npy",
        "submission.csv",
        "train_log.txt",
        "progress.jsonl",
        "run.lock",
    ):
        assert not (RUNNER.parent / name).exists()
