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


RUNNER = Path(__file__).with_name("v96_strict_v80_outer42_matched_control_40f.py")
SPEC = importlib.util.spec_from_file_location("v96_runner_under_test", RUNNER)
assert SPEC is not None and SPEC.loader is not None
V96 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V96)


def passing_resource_prefix(
    config: dict, pairs: list[tuple[str, int | None]]
) -> tuple[float, list[dict]]:
    started = time.monotonic()
    checks = [
        V96.make_resource_check(
            config,
            started_monotonic=started,
            phase=phase,
            fold=fold,
        )
        for phase, fold in pairs
    ]
    assert all(not check["breaches"] for check in checks)
    return started, checks


def test_history_audit_finds_no_equivalent_pure_v80_seed42() -> None:
    config = V96.load_frozen_config()
    evidence = V96.validate_historical_overlap_audit(config)
    assert evidence["decision"] == "GO_NO_EQUIVALENT_PURE_STRICT_V80_SEED42"
    assert evidence["equivalent_existing_versions"] == []
    assert evidence["evidence"]["v80"]["outer_split_seed"] == 104_395_303
    assert evidence["evidence"]["v81"]["outer_split_seed"] == 7
    assert evidence["evidence"]["v82"]["outer_split_seed"] == 2026
    for name in ("v85", "v86", "v87", "v92", "v93"):
        assert evidence["evidence"][name]["outer_split_seed"] == 42
        assert evidence["evidence"][name]["equivalent_pure_v80_seed42"] is False


def test_zero_column_adapter_leaves_v80_static_features_exactly_unchanged() -> None:
    frame = pd.DataFrame(
        {
            "Annual_Income_USD": [60_000.0, 120_000.0],
            "Daily_Commute_km": [30.0, 20.0],
            "Number_of_Cars_Owned": [1, 3],
            "Will_Buy_EV": ["No", "Yes"],
        }
    )
    block = V96.build_pure_v80_zero_column_adapter(frame)
    assert block.shape == (2, 0)
    flipped = frame.copy()
    flipped["Will_Buy_EV"] = ["Yes", "No"]
    pd.testing.assert_frame_equal(
        block, V96.build_pure_v80_zero_column_adapter(flipped)
    )
    x_train = pd.DataFrame({f"f{i}": [i, i + 1] for i in range(62)})
    x_test = x_train.copy()
    out_train, out_test, profile = V96.assert_pure_v80_static_identity(
        x_train, x_test, frame, frame, V96.load_frozen_config()
    )
    pd.testing.assert_frame_equal(out_train, x_train)
    pd.testing.assert_frame_equal(out_test, x_test)
    assert profile["columns"] == []
    assert profile["identical_to_v80_static_values"] is True


def test_model_recipe_is_v80_exact_except_outer_seed() -> None:
    config = V96.load_frozen_config()
    base = json.loads((V96.V80_DIR / "frozen_config.json").read_text())
    assert config["outer_split_seed"] == 42
    assert base["outer_split_seed"] == 104_395_303
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


def test_comparison_sources_are_hash_only_frozen_and_drift_rejected() -> None:
    config = V96.load_frozen_config()
    evidence = V96.validate_comparison_source_hashes(config)
    assert set(evidence) == set(V96.COMPARISON_DIRS)
    assert all(
        row["prediction_arrays_parsed"] is False for row in evidence.values()
    )
    attacked = json.loads(json.dumps(config))
    attacked["comparison_sources"]["v92_strict_v80_vehicle_demand_affordability_40f"][
        "oof_sha256"
    ] = "0" * 64
    with pytest.raises(ValueError, match="oof_sha256"):
        V96.validate_comparison_source_hashes(attacked)


def test_v80_frozen_source_and_verifier_entrypoint_are_exact(
    tmp_path, monkeypatch
) -> None:
    config = V96.load_frozen_config()
    evidence = V96.validate_v80_source_hashes(config)
    assert evidence["experiment_id"] == "v80_strict_v61_outer104395303_40f"
    assert evidence["verifier"] == "verify_complete"
    assert evidence["prediction_arrays_parsed"] is False
    attacked = json.loads(json.dumps(config))
    attacked["v80_source"]["verifier"] = "forged_verifier"
    attacked_path = tmp_path / "attacked_config.json"
    attacked_path.write_text(json.dumps(attacked), encoding="utf-8")
    monkeypatch.setattr(V96, "CONFIG_PATH", attacked_path)
    with pytest.raises(ValueError, match="v80 verifier"):
        V96.load_frozen_config()


def test_prediction_artifact_access_schema_is_generated_and_verified_exactly() -> None:
    run_contract = V96.build_run_contract()
    train = pd.DataFrame({"id": [1, 2]})
    test = pd.DataFrame({"id": [3]})
    sources = V96.make_source_manifest(run_contract, train, test, {})
    expected = {
        "strict_v80_oof": "HASH_ONLY_BYTES_NOT_PARSED",
        "strict_v80_test": "HASH_ONLY_BYTES_NOT_PARSED",
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
    V96.verify_source_contract(sources, results)
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
        attacked["run_contract_sha256"] = V96.sha256_json(stored_payload)
        attacked_results = dict(results)
        attacked_results["run_contract_sha256"] = attacked["run_contract_sha256"]
        with pytest.raises(ValueError, match="预测产物访问边界"):
            V96.verify_source_contract(attacked, attacked_results)


def test_frozen_comparisons_include_same_fold_deltas_and_v90_gap() -> None:
    y = np.asarray([0, 1] * 20, dtype=np.int8)
    folds = list(
        V96.StratifiedKFold(n_splits=4, shuffle=True, random_state=42).split(
            np.zeros(len(y)), y
        )
    )
    candidate = np.linspace(0.02, 0.98, len(y))
    candidate_test = np.linspace(0.1, 0.9, 11)
    source_oof = {
        "v92_strict_v80_vehicle_demand_affordability_40f": candidate[::-1],
        "v93_strict_v80_income_exact_hierarchical_fallback_40f": np.roll(
            candidate, 1
        ),
        "v90_v89_member_verify_budget_retry": np.clip(candidate + 0.01, 0, 1),
    }
    source_test = {name: candidate_test.copy() for name in source_oof}
    source_results = {}
    for name, values in source_oof.items():
        source_results[name] = {
            "oof_auc": float(V96.roc_auc_score(y, values)),
        }
        if name != "v90_v89_member_verify_budget_retry":
            source_results[name].update(
                {
                    "fold_auc": [
                        float(V96.roc_auc_score(y[idx], values[idx]))
                        for _, idx in folds
                    ],
                    "fold_diagnostics": [
                        {
                            "valid_idx_sha256": V96.hashlib.sha256(
                                idx.tobytes()
                            ).hexdigest()
                        }
                        for _, idx in folds
                    ],
                }
            )
    result = V96.compute_frozen_comparisons(
        y,
        folds,
        candidate,
        candidate_test,
        source_oof,
        source_test,
        source_results,
    )
    assert len(
        result["v92_strict_v80_vehicle_demand_affordability_40f"]["fold_deltas"]
    ) == 4
    assert len(
        result["v93_strict_v80_income_exact_hierarchical_fallback_40f"][
            "fold_deltas"
        ]
    ) == 4
    assert "fold_deltas" not in result["v90_v89_member_verify_budget_retry"]
    assert result["v90_v89_member_verify_budget_retry"]["test_spearman"] == 1.0
    source_results["v92_strict_v80_vehicle_demand_affordability_40f"][
        "fold_diagnostics"
    ][0]["valid_idx_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="validation rows"):
        V96.compute_frozen_comparisons(
            y,
            folds,
            candidate,
            candidate_test,
            source_oof,
            source_test,
            source_results,
        )


def test_project_gate_is_exactly_plus_point0001_and_24_of_40() -> None:
    config = V96.load_frozen_config()
    promoted = V96.derive_candidate_decision(config, 0.9464, 0.0001, 24)
    assert promoted["decision"] == "PROMOTE_SINGLE_MODEL"
    assert promoted["allowed_for_fusion"] is True
    for delta, wins in ((0.000099999, 24), (0.0001, 23)):
        rejected = V96.derive_candidate_decision(config, 0.9464, delta, wins)
        assert rejected["project_strength"] is False
        assert rejected["allowed_for_fusion"] is False


def test_matched_control_disables_formal_futility() -> None:
    config = V96.load_frozen_config()
    assert config["futility_enabled"] is False
    assert config["futility_disabled_reason"].startswith(
        "the seed42 matched control must complete all 40 folds"
    )


def test_nonformal_data_contract_does_not_load_prediction_arrays(monkeypatch) -> None:
    config = V96.load_frozen_config()
    recipe = V96.load_recipe()

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError(f"non-formal path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V96.np, "load", reject_prediction_load)
    _, _, _, baseline_oof, baseline_test, _ = V96.validate_data_contract(
        config, recipe, load_predictions=False
    )
    assert baseline_oof is None
    assert baseline_test is None


def test_v80_hash_drift_rejects_before_any_prediction_load(monkeypatch) -> None:
    config = V96.load_frozen_config()
    config["v80_source"]["oof_sha256"] = "0" * 64
    loads = {"count": 0}

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        loads["count"] += 1
        raise AssertionError(f"drift path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V96.np, "load", reject_prediction_load)
    with pytest.raises(ValueError, match="strict v80 oof_sha256"):
        V96.validate_data_contract(config, V96.load_recipe(), load_predictions=True)
    assert loads["count"] == 0


def test_comparison_hash_drift_rejects_before_any_prediction_load(monkeypatch) -> None:
    config = V96.load_frozen_config()
    source_id = "v92_strict_v80_vehicle_demand_affordability_40f"
    config["comparison_sources"][source_id]["test_sha256"] = "0" * 64
    loads = {"count": 0}

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        loads["count"] += 1
        raise AssertionError(f"drift path called np.load: {args!r} {kwargs!r}")

    monkeypatch.setattr(V96.np, "load", reject_prediction_load)
    with pytest.raises(ValueError, match=f"{source_id} test_sha256"):
        V96.load_verified_comparison_predictions(
            config,
            pd.DataFrame({"id": [1], "Will_Buy_EV": ["No"]}),
            pd.DataFrame({"id": [2]}),
        )
    assert loads["count"] == 0


@pytest.mark.parametrize(
    "source_id",
    [
        "v80_strict_v61_outer104395303_40f",
        "v90_v89_member_verify_budget_retry",
        "v92_strict_v80_vehicle_demand_affordability_40f",
        "v93_strict_v80_income_exact_hierarchical_fallback_40f",
    ],
)
def test_actual_formal_orchestration_rejects_each_source_drift_before_np_load(
    source_id, tmp_path, monkeypatch
) -> None:
    config = V96.load_frozen_config()
    if source_id == config["v80_source"]["experiment_id"]:
        config["v80_source"]["oof_sha256"] = "0" * 64
        expected_error = "strict v80 oof_sha256"
    else:
        config["comparison_sources"][source_id]["oof_sha256"] = "0" * 64
        expected_error = f"{source_id} oof_sha256"
    loads = {"count": 0}

    def reject_prediction_load(*args, **kwargs):  # noqa: ANN002, ANN003
        loads["count"] += 1
        raise AssertionError(f"formal drift path called np.load: {args!r} {kwargs!r}")

    work = tmp_path / source_id
    work.mkdir()
    monkeypatch.setattr(V96, "OUT_DIR", work)
    monkeypatch.setattr(V96, "LOCK_PATH", work / "run.lock")
    monkeypatch.setattr(V96, "LOG_PATH", work / "train_log.txt")
    monkeypatch.setattr(V96, "PROGRESS_PATH", work / "progress.jsonl")
    monkeypatch.setattr(V96, "CHECKPOINT_DIR", work / "checkpoints")
    monkeypatch.setattr(V96, "load_frozen_config", lambda: config)
    monkeypatch.setattr(V96.np, "load", reject_prediction_load)
    with pytest.raises(ValueError, match=expected_error):
        V96._train_impl({})
    assert loads["count"] == 0


def test_guarded_smoke_never_calls_lightgbm_fit(monkeypatch, capsys) -> None:
    def reject_fit(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("smoke called LightGBM.fit")

    monkeypatch.setattr(V96.lgb.LGBMClassifier, "fit", reject_fit)
    V96.smoke()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SMOKE_OK_SYNTHETIC_ONLY_NO_PREDICTION_ARRAYS_READ"


def test_formal_v80_identity_binds_ids_sources_and_artifact_hashes(tmp_path) -> None:
    baseline_dir = V96.OUT_DIR / f"pytest_v80_identity_{tmp_path.name}"
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
                "train_id_sha256": V96.sha256_ids(train["id"]),
                "test_id_sha256": V96.sha256_ids(test["id"]),
            },
            "outputs": {
                "oof_proba": V96.file_record(oof_path),
                "test_proba": V96.file_record(test_path),
            },
        }
        sources_path = baseline_dir / "sources.json"
        V96.atomic_write_json(sources_path, sources)
        baseline = {
            "sources_sha256": V96.sha256_file(sources_path),
            "artifact_sha256": {
                "oof_proba": V96.sha256_file(oof_path),
                "test_proba": V96.sha256_file(test_path),
            },
        }
        V96.validate_v80_prediction_identity(
            train, test, baseline, baseline_dir=baseline_dir
        )
        altered = test.copy()
        altered.loc[1, "id"] = 999
        with pytest.raises(ValueError, match="行身份"):
            V96.validate_v80_prediction_identity(
                train, altered, baseline, baseline_dir=baseline_dir
            )
        baseline["artifact_sha256"]["test_proba"] = "0" * 64
        with pytest.raises(ValueError, match="artifact/source"):
            V96.validate_v80_prediction_identity(
                train, test, baseline, baseline_dir=baseline_dir
            )
    finally:
        for path in baseline_dir.iterdir():
            path.unlink()
        baseline_dir.rmdir()


def test_failed_schemas_and_artifact_invalidation(tmp_path) -> None:
    config = V96.load_frozen_config()
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    for fold in range(1, 11):
        (checkpoints / f"fold_{fold:02d}.npz").write_bytes(b"synthetic")
    _, resources = passing_resource_prefix(
        config, V96.canonical_resource_sequence()[:20]
    )
    results_path = tmp_path / "cv_results.json"
    V96.write_futility_failure(
        config,
        config_sha256=V96.sha256_file(V96.CONFIG_PATH),
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
    V96.validate_failed_result_schema(
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
        V96.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    attacked = json.loads(json.dumps(failure))
    attacked["resource_checks"][3]["fold"] = 999
    with pytest.raises(ValueError, match="冻结域"):
        V96.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    attacked = json.loads(json.dumps(failure))
    attacked["resource_checks"][3]["wall_elapsed_seconds"] = 0.0
    with pytest.raises(ValueError, match="elapsed 序列回退"):
        V96.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    attacked = json.loads(json.dumps(failure))
    attacked["resource_checks"][3]["breaches"] = ["WALL_CLOCK_BUDGET"]
    attacked["resource_checks"][3]["status"] = "FAILED"
    with pytest.raises(ValueError, match="breach 复算"):
        V96.validate_failed_result_schema(
            attacked,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )
    (checkpoints / "fold_01.npz").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="present_artifact_records"):
        V96.validate_failed_result_schema(
            failure,
            config,
            artifact_root=tmp_path,
            checkpoint_dir=checkpoints,
        )


def test_staged_complete_transition_rejects_nonresource_mutation() -> None:
    config = V96.load_frozen_config()
    pre = V96.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_preverify_resource_phase"],
        fold=V96.N_FOLDS,
    )
    post = V96.make_resource_check(
        config,
        started_monotonic=time.monotonic(),
        phase=config["complete_postverify_resource_phase"],
        fold=V96.N_FOLDS,
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
    V96.validate_staged_complete_transition(staged, final, config)
    final["oof_auc"] = 0.91
    with pytest.raises(ValueError, match="非授权字段"):
        V96.validate_staged_complete_transition(staged, final, config)


def test_final_complete_pending_is_fully_verified_immutable_and_once_committed(
    tmp_path, monkeypatch
) -> None:
    config = V96.load_frozen_config()
    work = V96.OUT_DIR / f"pytest_finalize_success_{tmp_path.name}"
    work.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        V96.atomic_write_json(pending, {"status": "COMPLETE", "value": 7})
        _, checks = passing_resource_prefix(
            config, V96.canonical_resource_sequence()[:-1]
        )
        verify_calls = []
        commit_calls = []
        original_commit = V96.commit_complete_pending

        def verify_stub(*, results_path, allow_staged):
            verify_calls.append((results_path, allow_staged))
            assert json.loads(results_path.read_text())["status"] == "COMPLETE"
            return {"status": "SYNTHETIC_FULL_VERIFY_OK"}

        def commit_spy(pending_results_path, results_path):
            commit_calls.append((pending_results_path, results_path))
            original_commit(pending_results_path, results_path)

        monkeypatch.setattr(V96, "verify_complete", verify_stub)
        monkeypatch.setattr(V96, "commit_complete_pending", commit_spy)
        committed = V96.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=time.monotonic(),
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[{} for _ in range(V96.N_FOLDS)],
            fold_scores=[0.5 for _ in range(V96.N_FOLDS)],
            best_iterations=[1 for _ in range(V96.N_FOLDS)],
            resource_checks=checks,
            logger=V96.RunLogger(work / "synthetic.log"),
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
    config = V96.load_frozen_config()
    work = V96.OUT_DIR / f"pytest_finalize_mutation_{tmp_path.name}"
    work.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE"}', encoding="utf-8")
        _, checks = passing_resource_prefix(
            config, V96.canonical_resource_sequence()[:-1]
        )
        commits = {"count": 0}

        def mutating_verify(*, results_path, allow_staged):
            assert allow_staged is False
            results_path.write_text('{"status":"COMPLETE","forged":true}')

        def reject_commit(*args, **kwargs):  # noqa: ANN002, ANN003
            commits["count"] += 1
            raise AssertionError("mutated pending must not commit")

        monkeypatch.setattr(V96, "verify_complete", mutating_verify)
        monkeypatch.setattr(V96, "commit_complete_pending", reject_commit)
        with pytest.raises(RuntimeError, match="FULL_COMPLETE_VERIFIER"):
            V96.finalize_verified_complete(
                config,
                pending_results_path=pending,
                results_path=results,
                started_monotonic=time.monotonic(),
                config_sha256="a" * 64,
                run_contract_sha256="b" * 64,
                fold_rows=[{} for _ in range(V96.N_FOLDS)],
                fold_scores=[0.5 for _ in range(V96.N_FOLDS)],
                best_iterations=[1 for _ in range(V96.N_FOLDS)],
                resource_checks=checks,
                logger=V96.RunLogger(work / "synthetic.log"),
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
    config = V96.load_frozen_config()
    work = V96.OUT_DIR / f"pytest_guard_tamper_{tmp_path.name}"
    work.mkdir()
    checkpoints = work / "checkpoints"
    checkpoints.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE","trusted":true}', encoding="utf-8")
        started, checks = passing_resource_prefix(
            config, V96.canonical_resource_sequence()[:-1]
        )
        original_resource_check = V96.make_resource_check

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

        monkeypatch.setattr(V96, "verify_complete", verify_stub)
        monkeypatch.setattr(V96, "make_resource_check", tampering_guard)
        monkeypatch.setattr(V96, "PROGRESS_PATH", work / "progress.jsonl")
        committed = V96.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=started,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[{} for _ in range(V96.N_FOLDS)],
            fold_scores=[0.5 for _ in range(V96.N_FOLDS)],
            best_iterations=[1 for _ in range(V96.N_FOLDS)],
            resource_checks=checks,
            logger=V96.RunLogger(work / "synthetic.log"),
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
    config = V96.load_frozen_config()
    work = V96.OUT_DIR / f"pytest_post_commit_tamper_{tmp_path.name}"
    work.mkdir()
    checkpoints = work / "checkpoints"
    checkpoints.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE","trusted":true}', encoding="utf-8")
        started, checks = passing_resource_prefix(
            config, V96.canonical_resource_sequence()[:-1]
        )
        original_commit = V96.commit_complete_pending

        def verify_stub(*, results_path, allow_staged):
            assert results_path == pending
            assert allow_staged is False

        def tampering_commit(pending_results_path, results_path):
            original_commit(pending_results_path, results_path)
            results_path.write_text(
                '{"status":"COMPLETE","forged_after_commit":true}',
                encoding="utf-8",
            )

        monkeypatch.setattr(V96, "verify_complete", verify_stub)
        monkeypatch.setattr(V96, "commit_complete_pending", tampering_commit)
        monkeypatch.setattr(V96, "PROGRESS_PATH", work / "progress.jsonl")
        committed = V96.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=started,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[{} for _ in range(V96.N_FOLDS)],
            fold_scores=[0.5 for _ in range(V96.N_FOLDS)],
            best_iterations=[1 for _ in range(V96.N_FOLDS)],
            resource_checks=checks,
            logger=V96.RunLogger(work / "synthetic.log"),
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


def test_post_verify_resource_guard_fails_closed_without_complete_commit(
    tmp_path, monkeypatch
) -> None:
    config = V96.load_frozen_config()
    work = V96.OUT_DIR / f"pytest_finalize_budget_{tmp_path.name}"
    work.mkdir()
    checkpoints = work / "checkpoints"
    checkpoints.mkdir()
    try:
        pending = work / ".cv_results.pending.json"
        results = work / "cv_results.json"
        pending.write_text('{"status":"COMPLETE"}', encoding="utf-8")
        started, checks = passing_resource_prefix(
            config, V96.canonical_resource_sequence()[:-1]
        )
        original_resource_check = V96.make_resource_check
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

        monkeypatch.setattr(V96, "verify_complete", verify_stub)
        monkeypatch.setattr(V96, "make_resource_check", over_budget_check)
        monkeypatch.setattr(V96, "commit_complete_pending", reject_commit)
        monkeypatch.setattr(V96, "PROGRESS_PATH", work / "progress.jsonl")
        committed = V96.finalize_verified_complete(
            config,
            pending_results_path=pending,
            results_path=results,
            started_monotonic=started,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            fold_rows=[{} for _ in range(V96.N_FOLDS)],
            fold_scores=[0.5 for _ in range(V96.N_FOLDS)],
            best_iterations=[1 for _ in range(V96.N_FOLDS)],
            resource_checks=checks,
            logger=V96.RunLogger(work / "synthetic.log"),
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
    config = V96.load_frozen_config()
    run_contract = V96.build_run_contract()
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
    original_writer = V96.write_exception_failure
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

    monkeypatch.setattr(V96, "write_exception_failure", writer_with_concurrency_probe)
    monkeypatch.setattr(V96, "CHECKPOINT_DIR", checkpoints)
    with pytest.raises(RuntimeError, match="staged verify"):
        with V96.exclusive_run_lock(
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
    verified = V96.verify_failed_closed(
        results_path=results_path,
        checkpoint_dir=checkpoints,
    )
    assert verified["status"] == (
        "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ"
    )
