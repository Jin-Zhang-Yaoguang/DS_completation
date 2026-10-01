from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


RUNNER = Path(__file__).with_name(
    "v93_strict_v80_income_exact_hierarchical_fallback_40f.py"
)
SPEC = importlib.util.spec_from_file_location("v93_runner_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
V93 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V93)


def test_history_manifest_distinguishes_parallel_bins_from_true_fallback() -> None:
    config = V93.load_frozen_config()
    evidence = V93.validate_history_fallback_manifest(config)
    assert evidence["maximum_version_inclusive"] == 92
    assert evidence["required_existing_v84_v90_v92_covered"] is True
    assert evidence["file_count"] >= 100
    assert evidence["hierarchical_fallback_matches"] == []
    assert evidence["parallel_bin_feature_scope_count"] > 0
    assert evidence["whole_file_marker_candidates"] == [
        {
            "path": (
                "model/v84_strict_v80_original_supervision_40f/"
                "v84_strict_v80_original_supervision_40f.py"
            ),
            "classification": "SPLIT_ACROSS_UNRELATED_SCOPES_NOT_HIERARCHICAL",
        }
    ]

    synthetic_source = """
def apply_exact_income_fallback(Annual_Income_USD, income_bin10, income_bin100, y):
    global_prior = y.mean()
    if exact_count == 0:  # unseen exact code
        if income_bin10_count > 0:
            return income_bin10
        if income_bin100_count > 0:
            return income_bin100
        return global_prior
    return Annual_Income_USD
"""
    assert V93.extract_income_fallback_scopes(synthetic_source)[0]["scope"] == (
        "apply_exact_income_fallback"
    )
    parallel_only = """
def parallel_features(Annual_Income_USD, income_bin10, income_bin100):
    return Annual_Income_USD, income_bin10, income_bin100
"""
    assert V93.extract_income_fallback_scopes(parallel_only) == []


def test_hierarchical_fallback_order_exact_value_and_same_smoothing() -> None:
    domain = {
        "exact": np.asarray([0, 0, 1, 1, 2, 2], dtype=np.int32),
        "income_bin10": np.asarray([0, 0, 0, 0, 1, 1], dtype=np.int32),
        "income_bin100": np.asarray([0, 0, 0, 0, 0, 0], dtype=np.int32),
    }
    query = {
        "exact": np.asarray([0, 9, 8, 7], dtype=np.int32),
        "income_bin10": np.asarray([0, 1, 9, 8], dtype=np.int32),
        "income_bin100": np.asarray([0, 0, 0, 9], dtype=np.int32),
    }
    labels = np.asarray([0, 0, 1, 1, 1, 1], dtype=np.int8)
    smooths = (5.0, 15.0, 80.0)
    block, diagnostic = V93._hierarchical_query_encode(domain, query, labels, smooths)
    assert diagnostic["level_counts"] == {
        "exact": 1,
        "income_bin10": 1,
        "income_bin100": 1,
        "global_prior": 1,
    }
    prior = labels.mean()
    for column, smooth in enumerate(smooths):
        expected_exact = (0.0 + smooth * prior) / (2.0 + smooth)
        expected_bin10 = (2.0 + smooth * prior) / (2.0 + smooth)
        np.testing.assert_allclose(
            block[:, column],
            [expected_exact, expected_bin10, prior, prior],
            rtol=0.0,
            atol=1e-7,
        )


def test_hierarchical_inner_hold_prior_is_label_safe() -> None:
    exact = np.asarray([0, 1, 2, 3, 4, 5, 0, 1, 6, 7, 8, 9], dtype=np.int32)
    bin10 = np.asarray([0, 0, 1, 1, 2, 2, 0, 0, 3, 3, 4, 4], dtype=np.int32)
    bin100 = np.asarray([0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int32)
    y = np.asarray([0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0], dtype=np.int8)
    fit_idx = np.arange(10, dtype=np.int64)
    valid_idx = np.arange(10, 12, dtype=np.int64)
    inner = list(
        V93.StratifiedKFold(n_splits=2, shuffle=True, random_state=123).split(
            np.zeros(len(fit_idx)), y[fit_idx]
        )
    )
    train_levels = {"exact": exact, "income_bin10": bin10, "income_bin100": bin100}
    test_levels = {
        "exact": np.asarray([10, 11], dtype=np.int32),
        "income_bin10": np.asarray([5, 5], dtype=np.int32),
        "income_bin100": np.asarray([1, 2], dtype=np.int32),
    }
    original = V93.strict_encode_income_hierarchy(
        train_levels, test_levels, y, fit_idx, valid_idx, inner, (5.0, 15.0, 80.0)
    )
    first_inner_train, first_inner_hold = inner[0]
    changed_y = y.copy()
    changed_y[fit_idx[first_inner_hold]] = 1 - changed_y[fit_idx[first_inner_hold]]
    changed = V93.strict_encode_income_hierarchy(
        train_levels,
        test_levels,
        changed_y,
        fit_idx,
        valid_idx,
        inner,
        (5.0, 15.0, 80.0),
    )
    np.testing.assert_array_equal(
        original[0][first_inner_hold], changed[0][first_inner_hold]
    )
    assert not np.array_equal(original[1], changed[1])
    assert len(first_inner_train) == len(first_inner_hold)


def test_nonformal_data_contract_does_not_load_prediction_arrays(monkeypatch) -> None:
    config = V93.load_frozen_config()
    recipe = V93.load_recipe()

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError(f"non-formal path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V93.np, "load", reject_prediction_load)
    _, _, _, baseline_oof, baseline_test, _ = V93.validate_data_contract(
        config, recipe, load_predictions=False
    )
    assert baseline_oof is None
    assert baseline_test is None


def test_guarded_smoke_never_calls_lightgbm_fit(monkeypatch, capsys) -> None:
    def reject_fit(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("smoke called LightGBM.fit")

    monkeypatch.setattr(V93.lgb.LGBMClassifier, "fit", reject_fit)
    V93.smoke()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SMOKE_OK_SYNTHETIC_ONLY_NO_PREDICTION_ARRAYS_READ"


def test_formal_v80_identity_binds_ids_sources_and_artifact_hashes(tmp_path) -> None:
    baseline_dir = V93.OUT_DIR / f"pytest_v80_identity_{tmp_path.name}"
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
                "train_id_sha256": V93.sha256_ids(train["id"]),
                "test_id_sha256": V93.sha256_ids(test["id"]),
            },
            "outputs": {
                "oof_proba": V93.file_record(oof_path),
                "test_proba": V93.file_record(test_path),
            },
        }
        sources_path = baseline_dir / "sources.json"
        V93.atomic_write_json(sources_path, sources)
        baseline = {
            "sources_sha256": V93.sha256_file(sources_path),
            "artifact_sha256": {
                "oof_proba": V93.sha256_file(oof_path),
                "test_proba": V93.sha256_file(test_path),
            },
        }
        V93.validate_v80_prediction_identity(
            train, test, baseline, baseline_dir=baseline_dir
        )
        altered = test.copy()
        altered.loc[1, "id"] = 999
        with pytest.raises(ValueError, match="行身份"):
            V93.validate_v80_prediction_identity(
                train, altered, baseline, baseline_dir=baseline_dir
            )
        baseline["artifact_sha256"]["test_proba"] = "0" * 64
        with pytest.raises(ValueError, match="artifact/source"):
            V93.validate_v80_prediction_identity(
                train, test, baseline, baseline_dir=baseline_dir
            )
    finally:
        for path in baseline_dir.iterdir():
            path.unlink()
        baseline_dir.rmdir()


def test_failed_schemas_and_artifact_invalidation(tmp_path) -> None:
    config = V93.load_frozen_config()
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    for fold in range(1, 11):
        (checkpoints / f"fold_{fold:02d}.npz").write_bytes(b"synthetic")
    resource = V93.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase="AFTER_FOLD",
        fold=10,
    )
    results_path = tmp_path / "cv_results.json"
    V93.write_futility_failure(
        config,
        config_sha256=V93.sha256_file(V93.CONFIG_PATH),
        run_contract_sha256="a" * 64,
        fold_rows=[{} for _ in range(10)],
        fold_scores=[0.5 for _ in range(10)],
        best_iterations=[1 for _ in range(10)],
        resource_checks=[resource],
        partial_oof_auc=0.499,
        partial_v80_auc=0.5,
        winning_buckets=4,
        results_path=results_path,
        checkpoint_dir=checkpoints,
    )
    failure = json.loads(results_path.read_text(encoding="utf-8"))
    V93.validate_failed_result_schema(
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


def test_staged_complete_transition_rejects_nonresource_mutation() -> None:
    config = V93.load_frozen_config()
    pre = V93.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_preverify_resource_phase"],
        fold=V93.N_FOLDS,
    )
    post = V93.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_postverify_resource_phase"],
        fold=V93.N_FOLDS,
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
    V93.validate_staged_complete_transition(staged, final, config)
    final["oof_auc"] = 0.91
    with pytest.raises(ValueError, match="非授权字段"):
        V93.validate_staged_complete_transition(staged, final, config)


def test_formal_exception_closes_before_flock_release(tmp_path, monkeypatch) -> None:
    config = V93.load_frozen_config()
    run_contract = V93.build_run_contract()
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
        "fold_rows": [{}],
        "fold_scores": [0.5],
        "best_iterations": [1],
        "resource_checks": [],
    }
    original_writer = V93.write_exception_failure
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

    monkeypatch.setattr(V93, "write_exception_failure", writer_with_concurrency_probe)
    monkeypatch.setattr(V93, "CHECKPOINT_DIR", checkpoints)
    with pytest.raises(RuntimeError, match="staged verify"):
        with V93.exclusive_run_lock(
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
    verified = V93.verify_failed_closed(
        results_path=results_path,
        checkpoint_dir=checkpoints,
    )
    assert verified["status"] == (
        "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ"
    )
