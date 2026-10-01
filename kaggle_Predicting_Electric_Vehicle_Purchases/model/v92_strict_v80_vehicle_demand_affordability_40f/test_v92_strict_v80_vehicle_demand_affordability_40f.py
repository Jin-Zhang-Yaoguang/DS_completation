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


RUNNER = Path(__file__).with_name("v92_strict_v80_vehicle_demand_affordability_40f.py")
SPEC = importlib.util.spec_from_file_location("v92_runner_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
V92 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V92)


def test_history_manifest_is_complete_and_ast_finds_all_three_target_ratios() -> None:
    config = V92.load_frozen_config()
    evidence = V92.validate_history_formula_manifest(config)
    assert evidence["maximum_version_inclusive"] == 90
    assert evidence["required_v84_v90_covered"] is True
    assert evidence["file_count"] >= 100
    assert all(not rows for rows in evidence["target_ratio_matches"].values())

    synthetic_source = """
def differently_named_builder(frame):
    cash = frame["Annual_Income_USD"].to_numpy()
    distance = frame["Daily_Commute_km"].to_numpy()
    fleet = frame["Number_of_Cars_Owned"].to_numpy()
    after_purchase = fleet + 1.0
    ratio_a = distance / fleet
    ratio_b = cash / after_purchase
    ratio_c = cash / (after_purchase * distance)
    return ratio_a, ratio_b, ratio_c
"""
    ratios = V92.extract_cross_field_ratios(synthetic_source)
    signatures = {row["signature"] for row in ratios}
    assert set(V92.TARGET_RATIO_SIGNATURES).issubset(signatures)


def test_vehicle_demand_affordability_block_is_exact_and_target_invariant() -> None:
    frame = pd.DataFrame(
        {
            "Annual_Income_USD": [60_000.0, 120_000.0],
            "Daily_Commute_km": [30.0, 20.0],
            "Number_of_Cars_Owned": [1, 3],
            "Will_Buy_EV": ["No", "Yes"],
        }
    )
    block = V92.build_vehicle_demand_affordability_block(frame)
    expected = np.asarray(
        [[30.0, 30_000.0, 1_000.0], [20.0 / 3.0, 30_000.0, 1_500.0]],
        dtype=np.float32,
    )
    assert list(block.columns) == [
        "mobility_commute_per_owned_car",
        "afford_income_per_postpurchase_car",
        "afford_income_per_postpurchase_car_km",
    ]
    np.testing.assert_allclose(block.to_numpy(), expected, rtol=0.0, atol=1e-5)
    flipped = frame.copy()
    flipped["Will_Buy_EV"] = ["Yes", "No"]
    pd.testing.assert_frame_equal(
        block, V92.build_vehicle_demand_affordability_block(flipped)
    )
    invalid = frame.copy()
    invalid.loc[0, "Number_of_Cars_Owned"] = 0
    with pytest.raises(ValueError, match="严格为正"):
        V92.build_vehicle_demand_affordability_block(invalid)


def test_nonformal_data_contract_does_not_load_prediction_arrays(monkeypatch) -> None:
    config = V92.load_frozen_config()
    recipe = V92.load_recipe()

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError(f"non-formal path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V92.np, "load", reject_prediction_load)
    _, _, _, baseline_oof, baseline_test, _ = V92.validate_data_contract(
        config, recipe, load_predictions=False
    )
    assert baseline_oof is None
    assert baseline_test is None


def test_guarded_smoke_never_calls_lightgbm_fit(monkeypatch, capsys) -> None:
    def reject_fit(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("smoke called LightGBM.fit")

    monkeypatch.setattr(V92.lgb.LGBMClassifier, "fit", reject_fit)
    V92.smoke()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SMOKE_OK_SYNTHETIC_ONLY_NO_PREDICTION_ARRAYS_READ"


def test_formal_v80_identity_binds_ids_sources_and_artifact_hashes(tmp_path) -> None:
    baseline_dir = V92.OUT_DIR / f"pytest_v80_identity_{tmp_path.name}"
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
                "train_id_sha256": V92.sha256_ids(train["id"]),
                "test_id_sha256": V92.sha256_ids(test["id"]),
            },
            "outputs": {
                "oof_proba": V92.file_record(oof_path),
                "test_proba": V92.file_record(test_path),
            },
        }
        sources_path = baseline_dir / "sources.json"
        V92.atomic_write_json(sources_path, sources)
        baseline = {
            "sources_sha256": V92.sha256_file(sources_path),
            "artifact_sha256": {
                "oof_proba": V92.sha256_file(oof_path),
                "test_proba": V92.sha256_file(test_path),
            },
        }
        V92.validate_v80_prediction_identity(
            train, test, baseline, baseline_dir=baseline_dir
        )
        altered = test.copy()
        altered.loc[1, "id"] = 999
        with pytest.raises(ValueError, match="行身份"):
            V92.validate_v80_prediction_identity(
                train, altered, baseline, baseline_dir=baseline_dir
            )
        baseline["artifact_sha256"]["test_proba"] = "0" * 64
        with pytest.raises(ValueError, match="artifact/source"):
            V92.validate_v80_prediction_identity(
                train, test, baseline, baseline_dir=baseline_dir
            )
    finally:
        for path in baseline_dir.iterdir():
            path.unlink()
        baseline_dir.rmdir()


def test_failed_schemas_and_artifact_invalidation(tmp_path) -> None:
    config = V92.load_frozen_config()
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    for fold in range(1, 11):
        (checkpoints / f"fold_{fold:02d}.npz").write_bytes(b"synthetic")
    resource = V92.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase="AFTER_FOLD",
        fold=10,
    )
    results_path = tmp_path / "cv_results.json"
    V92.write_futility_failure(
        config,
        config_sha256=V92.sha256_file(V92.CONFIG_PATH),
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
    V92.validate_failed_result_schema(
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
    config = V92.load_frozen_config()
    pre = V92.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_preverify_resource_phase"],
        fold=V92.N_FOLDS,
    )
    post = V92.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_postverify_resource_phase"],
        fold=V92.N_FOLDS,
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
    V92.validate_staged_complete_transition(staged, final, config)
    final["oof_auc"] = 0.91
    with pytest.raises(ValueError, match="非授权字段"):
        V92.validate_staged_complete_transition(staged, final, config)


def test_formal_exception_closes_before_flock_release(
    tmp_path, monkeypatch
) -> None:
    config = V92.load_frozen_config()
    run_contract = V92.build_run_contract()
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
    original_writer = V92.write_exception_failure
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

    monkeypatch.setattr(V92, "write_exception_failure", writer_with_concurrency_probe)
    monkeypatch.setattr(V92, "CHECKPOINT_DIR", checkpoints)
    with pytest.raises(RuntimeError, match="staged verify"):
        with V92.exclusive_run_lock(
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
    verified = V92.verify_failed_closed(
        results_path=results_path,
        checkpoint_dir=checkpoints,
    )
    assert verified["status"] == (
        "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ"
    )
