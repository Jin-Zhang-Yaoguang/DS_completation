from __future__ import annotations

import copy
import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("v94_strict_v80_v85_v87_cv_blend.py")
SPEC = importlib.util.spec_from_file_location("v94_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {MODULE_PATH}")
V94 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V94)


def synthetic_predictions() -> tuple[
    np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray]
]:
    y = np.tile(np.array([0, 1], dtype=np.int8), 50)
    trend = np.linspace(0.01, 0.99, len(y))
    rng = np.random.default_rng(42)
    oof = {
        V94.MEMBER_IDS[0]: np.clip(0.18 + 0.60 * y + 0.04 * trend, 0, 1),
        V94.MEMBER_IDS[1]: np.clip(
            0.16 + 0.62 * y + 0.03 * trend[::-1], 0, 1
        ),
        V94.MEMBER_IDS[2]: np.clip(
            0.17 + 0.61 * y + 0.02 * rng.random(len(y)), 0, 1
        ),
    }
    test = {
        V94.MEMBER_IDS[0]: np.linspace(0.05, 0.95, 31),
        V94.MEMBER_IDS[1]: np.linspace(0.95, 0.05, 31),
        V94.MEMBER_IDS[2]: np.linspace(0.10, 0.90, 31) ** 1.1,
    }
    return y, oof, test


def make_resource_check(
    phase: str,
    fold: int | None,
    *,
    elapsed: float = 1.0,
    peak_bytes: int = 1024,
    breaches: list[str] | None = None,
) -> dict[str, object]:
    return {
        "phase": phase,
        "fold": fold,
        "wall_elapsed_seconds": elapsed,
        "wall_budget_seconds": 900,
        "peak_rss_bytes": peak_bytes,
        "peak_rss_gib": peak_bytes / 1024**3,
        "peak_rss_budget_bytes": 12 * 1024**3,
        "peak_rss_budget_gib": 12,
        "breaches": [] if breaches is None else breaches,
    }


def passing_resource_prefix(length: int) -> list[dict[str, object]]:
    return [
        make_resource_check(phase, fold, elapsed=float(index + 1))
        for index, (phase, fold) in enumerate(
            V94.canonical_resource_sequence()[:length]
        )
    ]


def test_config_freezes_distinct_three_member_question_and_v90_baseline() -> None:
    config = V94.load_frozen_config()
    assert tuple(member["experiment_id"] for member in config["members"]) == V94.MEMBER_IDS
    assert all(member["prediction_parent"] is None for member in config["members"])
    assert config["strict_baseline"]["experiment_id"] == V94.BASELINE_ID
    assert config["strict_baseline"]["role"] == "COMPARISON_ONLY_NOT_A_MEMBER"
    assert V94.BASELINE_ID not in V94.MEMBER_IDS
    assert config["base_oof_auc"] == 0.9463720745765888
    assert config["promotion_gate"]["minimum_oof_delta_vs_base"] == 0.0001
    assert config["promotion_gate"]["required_meta_holdout_wins"] == 5


def test_config_rejects_baseline_as_member_or_an_extra_member() -> None:
    config = V94.load_frozen_config()
    bad = copy.deepcopy(config)
    bad["members"].append(copy.deepcopy(bad["strict_baseline"]))
    with pytest.raises(ValueError, match="恰好有三个"):
        V94.validate_static_config(bad)
    bad = copy.deepcopy(config)
    bad["strict_baseline"]["role"] = "PREDICTION_MEMBER"
    with pytest.raises(ValueError, match="只能作为对照"):
        V94.validate_static_config(bad)


def test_simplex_is_exact_frozen_231_point_grid() -> None:
    grid = V94.simplex_grid()
    assert len(grid) == 231
    assert len(set(grid)) == 231
    assert (0.45, 0.55, 0.0) in grid
    assert all(np.isclose(sum(weights), 1.0) for weights in grid)
    assert all(weight >= 0.0 for weights in grid for weight in weights)
    assert all(np.isclose(weight * 20, round(weight * 20)) for weights in grid for weight in weights)


def test_tie_break_returns_v90_branch_before_adding_v87() -> None:
    rows = [
        {
            "v80_weight": weights[0],
            "v85_weight": weights[1],
            "v87_weight": weights[2],
            "meta_train_auc": 0.75,
        }
        for weights in V94.simplex_grid()
    ]
    assert V94.choose_three_weights(rows, (0.45, 0.55, 0.0)) == (
        0.45,
        0.55,
        0.0,
    )


def test_v90_weight_tie_break_is_identical_to_frozen_rule() -> None:
    rows = [
        {
            "v85_weight": weight,
            "v80_weight": 1.0 - weight,
            "meta_train_auc": 0.8,
        }
        for weight in V94.V90_WEIGHT_GRID
    ]
    assert V94.choose_v85_weight(rows) == 0.5
    for row in rows:
        row["meta_train_auc"] = 0.7
    rows[8]["meta_train_auc"] = 0.9
    rows[12]["meta_train_auc"] = 0.9
    assert V94.choose_v85_weight(rows) == 0.4


def test_meta_cv_is_deterministic_and_rebuilds_v90_branch() -> None:
    y, oof, test = synthetic_predictions()
    first = V94.run_meta_cv(y, oof, test)
    second = V94.run_meta_cv(y, oof, test)
    assert np.array_equal(first["oof"], second["oof"])
    assert np.array_equal(first["test"], second["test"])
    assert np.array_equal(first["baseline_oof"], second["baseline_oof"])
    assert np.array_equal(first["baseline_test"], second["baseline_test"])
    assert np.all(first["coverage"] == 1)
    assert len(first["fold_rows"]) == 5
    assert all(
        row["baseline_v90_weights"]["v87"] == 0.0
        for row in first["fold_rows"]
    )


def test_every_ecdf_fit_uses_only_meta_train(monkeypatch: pytest.MonkeyPatch) -> None:
    y, oof, test = synthetic_predictions()
    original = V94.fit_mid_ecdf
    seen_lengths: list[int] = []

    def recording_fit(values: np.ndarray) -> np.ndarray:
        seen_lengths.append(len(values))
        return original(values)

    monkeypatch.setattr(V94, "fit_mid_ecdf", recording_fit)
    V94.run_meta_cv(y, oof, test)
    assert seen_lengths == [80] * 15


def test_baseline_reconstruction_fails_closed_on_one_value_drift() -> None:
    config = V94.load_frozen_config()
    y, oof, test = synthetic_predictions()
    meta = V94.run_meta_cv(y, oof, test)
    bad = meta["baseline_oof"].copy()
    bad[0] += 1e-6
    with pytest.raises(ValueError, match="v90 OOF"):
        V94.assert_baseline_reconstruction(
            config, meta, bad, meta["baseline_test"]
        )


def test_promotion_requires_point_one_bp_and_five_of_five() -> None:
    config = V94.load_frozen_config()
    assert V94.promotion_decision(0.0001, 5, config) == "PROMOTE"
    assert V94.promotion_decision(0.000099999, 5, config) == "REJECT"
    assert V94.promotion_decision(0.0002, 4, config) == "REJECT"


def test_audit_hashes_prediction_files_without_loading_arrays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_load(*args: object, **kwargs: object) -> None:
        raise AssertionError("audit must not call np.load")

    monkeypatch.setattr(V94.np, "load", forbidden_load)
    result = V94.audit()
    assert result["status"] == "AUDIT_OK_HASH_ONLY_NO_PREDICTION_ARRAYS_READ"
    assert result["prediction_access"] == "NO_PREDICTION_ARRAYS_READ"
    assert result["formal_outputs_created"] is False


def test_smoke_is_synthetic_and_creates_no_formal_artifacts() -> None:
    before = {
        name: (V94.OUT_DIR / name).exists() for name in V94.MATERIAL_ARTIFACTS
    }
    result = V94.smoke()
    after = {
        name: (V94.OUT_DIR / name).exists() for name in V94.MATERIAL_ARTIFACTS
    }
    assert result["status"] == "SMOKE_OK_SYNTHETIC_ONLY_NO_REAL_PREDICTIONS_LOADED"
    assert result["simplex_candidate_count"] == 231
    assert before == after


def test_failure_schema_marks_partial_artifacts_invalid(tmp_path: Path) -> None:
    config = V94.load_frozen_config()
    (tmp_path / "oof_proba.npy").write_bytes(b"partial")
    check = make_resource_check("FAILED_EXCEPTION", 0)
    result = V94.build_failed_result(
        config, "FAILED_EXCEPTION", check, "RuntimeError", "synthetic", tmp_path
    )
    V94.validate_failed_result(result, config, tmp_path)
    assert result["present_artifacts"] == ["oof_proba.npy"]
    assert result["present_artifacts_are_invalid_for_use"] is True
    assert result["allowed_for_fusion"] is False
    assert result["oof_delta_vs_base"] is None


def test_resource_failure_requires_real_breach(tmp_path: Path) -> None:
    config = V94.load_frozen_config()
    checks = passing_resource_prefix(7)
    check = make_resource_check(
        "AFTER_META_FOLD",
        5,
        elapsed=901.0,
        breaches=["WALL_CLOCK_BUDGET"],
    )
    checks[-1] = check
    result = V94.build_failed_result(
        config,
        "FAILED_RESOURCE_BUDGET",
        check,
        "ResourceBudgetExceeded",
        "WALL_CLOCK_BUDGET",
        tmp_path,
        resource_checks=checks,
    )
    V94.validate_failed_result(result, config, tmp_path)
    bad = copy.deepcopy(result)
    bad["resource_check"]["breaches"] = []
    with pytest.raises(ValueError, match="独立复算"):
        V94.validate_failed_result(bad, config, tmp_path)


def test_resource_check_rejects_omitted_forged_and_unit_drift() -> None:
    config = V94.load_frozen_config()
    valid = make_resource_check("BEFORE_INPUT_LOAD", None, elapsed=10.0)
    V94.validate_resource_check(config, valid)
    omitted = copy.deepcopy(valid)
    omitted["wall_elapsed_seconds"] = 901.0
    with pytest.raises(ValueError, match="独立复算"):
        V94.validate_resource_check(config, omitted)
    forged = copy.deepcopy(valid)
    forged["breaches"] = ["PEAK_RSS_BUDGET"]
    with pytest.raises(ValueError, match="独立复算"):
        V94.validate_resource_check(config, forged)
    bad_units = copy.deepcopy(valid)
    bad_units["peak_rss_gib"] = 1.0
    with pytest.raises(ValueError, match="bytes/GiB"):
        V94.validate_resource_check(config, bad_units)
    omitted_peak = copy.deepcopy(valid)
    omitted_peak["peak_rss_bytes"] = 13 * 1024**3
    omitted_peak["peak_rss_gib"] = 13.0
    with pytest.raises(ValueError, match="独立复算"):
        V94.validate_resource_check(config, omitted_peak)
    forged_phase = copy.deepcopy(valid)
    forged_phase["phase"] = "FORGED_PHASE"
    with pytest.raises(ValueError, match="白名单"):
        V94.validate_resource_check(config, forged_phase)
    forged_fold = copy.deepcopy(valid)
    forged_fold["fold"] = 999
    with pytest.raises(ValueError, match="phase/fold"):
        V94.validate_resource_check(config, forged_fold)


def test_resource_sequences_reject_gap_reorder_and_wrong_fold() -> None:
    config = V94.load_frozen_config()
    complete = passing_resource_prefix(len(V94.canonical_resource_sequence()))
    V94.validate_resource_sequence(config, complete, "COMPLETE", complete[-1])
    gap = copy.deepcopy(complete)
    del gap[3]
    with pytest.raises(ValueError, match="序列或覆盖"):
        V94.validate_resource_sequence(config, gap, "COMPLETE", gap[-1])
    reordered = copy.deepcopy(complete)
    reordered[2], reordered[3] = reordered[3], reordered[2]
    with pytest.raises(ValueError, match="序列或覆盖|发生回退"):
        V94.validate_resource_sequence(
            config, reordered, "COMPLETE", reordered[-1]
        )
    wrong_fold = copy.deepcopy(complete)
    wrong_fold[2]["fold"] = 5
    with pytest.raises(ValueError, match="序列或覆盖|phase/fold"):
        V94.validate_resource_sequence(
            config, wrong_fold, "COMPLETE", wrong_fold[-1]
        )
    exception = passing_resource_prefix(4)
    exception.append(
        make_resource_check("FAILED_EXCEPTION", 2, elapsed=5.0)
    )
    V94.validate_resource_sequence(
        config, exception, "FAILED_EXCEPTION", exception[-1]
    )
    bad_exception = copy.deepcopy(exception)
    bad_exception[-1]["fold"] = 3
    with pytest.raises(ValueError, match="已完成 meta folds"):
        V94.validate_resource_sequence(
            config, bad_exception, "FAILED_EXCEPTION", bad_exception[-1]
        )


def test_resource_sequence_rejects_elapsed_and_peak_regression_but_allows_equal() -> None:
    config = V94.load_frozen_config()
    equal = [
        make_resource_check(phase, fold, elapsed=10.0, peak_bytes=2048)
        for phase, fold in V94.canonical_resource_sequence()
    ]
    V94.validate_resource_sequence(config, equal, "COMPLETE", equal[-1])
    elapsed_back = copy.deepcopy(equal)
    elapsed_back[5]["wall_elapsed_seconds"] = 9.999999
    with pytest.raises(ValueError, match="elapsed_seconds.*回退"):
        V94.validate_resource_sequence(
            config, elapsed_back, "COMPLETE", elapsed_back[-1]
        )
    peak_back = [
        make_resource_check(
            phase,
            fold,
            elapsed=float(index + 1),
            peak_bytes=2048 + index,
        )
        for index, (phase, fold) in enumerate(V94.canonical_resource_sequence())
    ]
    peak_back[5]["peak_rss_bytes"] = 2048
    peak_back[5]["peak_rss_gib"] = 2048 / 1024**3
    with pytest.raises(ValueError, match="peak_rss_bytes.*回退"):
        V94.validate_resource_sequence(
            config, peak_back, "COMPLETE", peak_back[-1]
        )


def test_landed_complete_payload_rejects_intermediate_resource_regression(
    tmp_path: Path,
) -> None:
    config = V94.load_frozen_config()
    checks = passing_resource_prefix(len(V94.canonical_resource_sequence()))
    checks[5]["wall_elapsed_seconds"] = 2.5
    path = tmp_path / "cv_results.json"
    V94.atomic_write_json(
        path,
        {
            "status": "COMPLETE",
            "resource_checks": checks,
            "final_resource_check": checks[-1],
        },
    )
    landed = V94.json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="elapsed_seconds.*回退"):
        V94.validate_complete_result_schema(
            landed,
            config,
            meta={},
            evaluation={},
            sources_sha256="synthetic",
            allowed_resource_phases={"FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"},
        )


def test_failed_close_survives_hash_collection_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = V94.load_frozen_config()
    check = make_resource_check("FAILED_EXCEPTION", 0)

    def hash_failure(path: Path) -> str:
        raise OSError(f"synthetic hash failure: {path.name}")

    def forbidden_strict_hashes(config: dict[str, object]) -> dict[str, object]:
        raise AssertionError("FAILED close must not call strict hashes")

    monkeypatch.setattr(V94, "sha256_file", hash_failure)
    monkeypatch.setattr(V94, "code_and_input_hashes", forbidden_strict_hashes)
    failure_path = tmp_path / "cv_results.json"
    monkeypatch.setattr(V94, "RESULTS_PATH", failure_path)
    result = V94.write_failed_result(
        config, "FAILED_EXCEPTION", check, ValueError("source drift"), [check]
    )
    assert failure_path.is_file()
    assert V94.json.loads(failure_path.read_text(encoding="utf-8")) == result
    evidence = result["failure_input_evidence"]
    assert evidence["records_with_collection_error"]
    assert all(
        evidence["records"][key]["collection_error"]
        for key in evidence["records_with_collection_error"]
    )


def test_failed_close_records_missing_source_and_expected_hash(tmp_path: Path) -> None:
    config = copy.deepcopy(V94.load_frozen_config())
    config["members"][2]["directory"] = "model/does_not_exist_v94_attack"
    check = make_resource_check("FAILED_EXCEPTION", 0)
    result = V94.build_failed_result(
        config, "FAILED_EXCEPTION", check, "FileNotFoundError", "missing", tmp_path
    )
    V94.validate_failed_result(result, config, tmp_path)
    key = f"source:{V94.MEMBER_IDS[2]}:{config['members'][2]['runner']}"
    record = result["failure_input_evidence"]["records"][key]
    assert record["exists"] is False
    assert record["observed_sha256"] is None
    assert record["expected_sha256"] == config["members"][2]["runner_sha256"]
    assert key in result["failure_input_evidence"]["records_with_collection_error"]


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("path", "model/forged.npy", "path"),
        ("exists", False, "缺失输入状态|实时重采样"),
        ("observed_sha256", "0" * 64, "实时重采样"),
        ("observed_size_bytes", 999999, "实时重采样"),
        ("collection_error", "OSError: forged", "状态不互斥|实时重采样"),
    ],
)
def test_failure_evidence_rejects_readable_record_forgery(
    field: str, replacement: object, message: str
) -> None:
    config = V94.load_frozen_config()
    evidence = V94.collect_failure_input_evidence(config)
    key = "data:data/train.csv"
    evidence["records"][key][field] = replacement
    with pytest.raises(ValueError, match=message):
        V94.validate_failure_input_evidence(evidence, config)


def test_failure_evidence_rejects_missing_error_and_index_forgery() -> None:
    config = copy.deepcopy(V94.load_frozen_config())
    config["members"][2]["directory"] = "model/does_not_exist_v94_attack"
    evidence = V94.collect_failure_input_evidence(config)
    key = f"source:{V94.MEMBER_IDS[2]}:{config['members'][2]['runner']}"
    forged_error = copy.deepcopy(evidence)
    forged_error["records"][key]["collection_error"] = "FileNotFoundError: forged"
    with pytest.raises(ValueError, match="错误文本非法|实时重采样"):
        V94.validate_failure_input_evidence(forged_error, config)
    forged_index = copy.deepcopy(evidence)
    forged_index["records_with_collection_error"].remove(key)
    with pytest.raises(ValueError, match="error 索引"):
        V94.validate_failure_input_evidence(forged_index, config)


def test_failure_evidence_rejects_coherent_fake_nonexistent_claim() -> None:
    config = V94.load_frozen_config()
    evidence = V94.collect_failure_input_evidence(config)
    key = "data:data/train.csv"
    record = evidence["records"][key]
    record["exists"] = False
    record["observed_sha256"] = None
    record["observed_size_bytes"] = None
    record["collection_error"] = f"FileNotFoundError: {record['path']}"
    evidence["records_with_collection_error"] = [key]
    evidence["records_with_hash_mismatch"] = []
    with pytest.raises(ValueError, match="实时重采样"):
        V94.validate_failure_input_evidence(evidence, config)


def test_formal_load_verifies_all_sources_before_prediction_array_load() -> None:
    source = inspect.getsource(V94.load_formal_inputs)
    assert source.index("verify_source_complete(source)") < source.index("np.load(")
    assert source.count("np.load(") == 4
    assert "source_row_identities(config)" in source
    assert "source_result_metadata(config)" in source


def test_complete_is_staged_verified_and_exception_closed_inside_flock() -> None:
    source = inspect.getsource(V94.run)
    assert source.index("with LOCK_PATH.open") < source.index("except Exception as error")
    assert source.count("verify_staged_complete_file(") == 3
    first_verify = source.index("verify_staged_complete_file(")
    second_verify = source.index("verify_staged_complete_file(", first_verify + 1)
    third_verify = source.index("verify_staged_complete_file(", second_verify + 1)
    assert source.index("_atomic_bytes(") < first_verify
    assert first_verify < source.index("AFTER_STAGED_VERIFY_PRE_COMPLETE")
    assert source.index("AFTER_STAGED_VERIFY_PRE_COMPLETE") < second_verify
    assert second_verify < source.index("PRE_COMMIT_AFTER_FINAL_FILE_VERIFY")
    assert source.index("PRE_COMMIT_AFTER_FINAL_FILE_VERIFY") < third_verify
    assert third_verify < source.index("seal_final_guard_and_commit(")
    helper = inspect.getsource(V94.seal_final_guard_and_commit)
    final_guard = helper.index("FINAL_GUARD_AFTER_THIRD_FILE_VERIFY")
    fourth_verify = helper.index("verify_staged_complete_file(")
    post_seal = helper.index("POST_SEAL_COMMIT_GUARD")
    commit = helper.index("commit_complete_file(pending_path, results_path)")
    assert final_guard < helper.index("sealed_payload = payload_builder")
    assert helper.index("sealed_payload = payload_builder") < fourth_verify
    assert fourth_verify < post_seal < commit
    assert "_atomic_bytes(" not in helper[fourth_verify:commit]
    assert "payload_builder(" not in helper[fourth_verify:commit]
    assert "failure_status" in source


def test_dynamic_899_to_901_final_guard_never_commits_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = V94.load_frozen_config()
    checks = passing_resource_prefix(10)
    for index, check in enumerate(checks[:-1]):
        check["wall_elapsed_seconds"] = float(index + 1)
    checks[-1]["wall_elapsed_seconds"] = 899.0
    pending = tmp_path / ".cv_results.complete.123.json"
    results = tmp_path / "cv_results.json"
    V94.atomic_write_json(pending, {"status": "THIRD_VERIFY_PASSED"})
    third_sha = V94.sha256_file(pending)
    replacements: list[tuple[Path, Path]] = []
    builder_called = False

    def final_guard(
        config: dict[str, object],
        started: float,
        phase: str,
        fold: int,
    ) -> dict[str, object]:
        assert phase == "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"
        return make_resource_check(
            phase,
            fold,
            elapsed=901.0,
            breaches=["WALL_CLOCK_BUDGET"],
        )

    def builder(
        check: dict[str, object], rows: list[dict[str, object]]
    ) -> dict[str, object]:
        nonlocal builder_called
        builder_called = True
        return {"unexpected": True}

    def forbidden_replace(source: Path, destination: Path) -> None:
        replacements.append((source, destination))

    monkeypatch.setattr(V94, "resource_check", final_guard)
    monkeypatch.setattr(V94.os, "replace", forbidden_replace)
    with pytest.raises(V94.ResourceBudgetExceeded, match="WALL_CLOCK_BUDGET"):
        V94.seal_final_guard_and_commit(
            config,
            0.0,
            pending,
            results,
            checks,
            third_sha,
            builder,
        )
    assert builder_called is False
    assert replacements == []
    assert not results.exists()
    assert checks[-1]["phase"] == "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"
    assert checks[-1]["wall_elapsed_seconds"] == 901.0


def test_dynamic_fourth_verify_899_to_901_post_seal_closes_failed_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = V94.load_frozen_config()
    checks = passing_resource_prefix(10)
    for index, check in enumerate(checks[:-1]):
        check["wall_elapsed_seconds"] = float(index + 1)
    checks[-1]["wall_elapsed_seconds"] = 898.0
    state = {"elapsed": 899.0}
    pending = tmp_path / ".cv_results.complete.123.json"
    results = tmp_path / "cv_results.json"
    V94.atomic_write_json(pending, {"status": "THIRD_VERIFY_PASSED"})
    third_sha = V94.sha256_file(pending)
    complete_commits: list[tuple[Path, Path]] = []

    monkeypatch.setattr(V94.time, "monotonic", lambda: state["elapsed"])
    monkeypatch.setattr(V94, "process_peak_rss_bytes", lambda: 1024)

    def fourth_verifier(
        path: Path, allowed_resource_phases: set[str]
    ) -> dict[str, object]:
        assert allowed_resource_phases == {
            "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"
        }
        state["elapsed"] = 901.0
        return V94.json.loads(path.read_text(encoding="utf-8"))

    def complete_commit(source: Path, destination: Path) -> None:
        complete_commits.append((source, destination))

    monkeypatch.setattr(V94, "verify_staged_complete_file", fourth_verifier)
    monkeypatch.setattr(V94, "commit_complete_file", complete_commit)
    monkeypatch.setattr(V94, "RESULTS_PATH", results)
    caught: V94.ResourceBudgetExceeded | None = None
    try:
        V94.seal_final_guard_and_commit(
            config,
            0.0,
            pending,
            results,
            checks,
            third_sha,
            lambda guard, rows: {
                "status": "COMPLETE",
                "final_resource_check": guard,
                "resource_checks": rows,
            },
        )
    except V94.ResourceBudgetExceeded as error:
        caught = error
        V94.write_failed_result(
            config,
            "FAILED_RESOURCE_BUDGET",
            error.check,
            error,
            checks,
            artifact_root=tmp_path,
        )
    assert caught is not None
    assert caught.check["phase"] == "POST_SEAL_COMMIT_GUARD"
    assert caught.check["wall_elapsed_seconds"] == 901.0
    assert complete_commits == []
    closed = V94.json.loads(results.read_text(encoding="utf-8"))
    assert closed["status"] == "FAILED_RESOURCE_BUDGET"
    assert closed["decision"] == "FAILED_RESOURCE_BUDGET"
    assert closed["sealed_pending_archive"] == {
        "artifact": V94.FAILED_SEALED_ARCHIVE_NAME,
        "present": True,
        "physical_path_present": True,
        "archive_failed": False,
        "stale_collision": False,
        "invalid_for_use": True,
    }
    assert V94.FAILED_SEALED_ARCHIVE_NAME in closed["present_artifacts"]
    provenance = closed["sealed_archive_provenance"]
    archive = tmp_path / V94.FAILED_SEALED_ARCHIVE_NAME
    assert provenance["sealed_pending_sha256"] == V94.sha256_file(pending)
    assert provenance["sealed_pending_size_bytes"] == pending.stat().st_size
    assert provenance["archive_sha256"] == V94.sha256_file(archive)
    assert provenance["archive_size_bytes"] == archive.stat().st_size
    assert provenance["link_attempted"] is True
    assert provenance["link_succeeded"] is True
    assert provenance["link_error"] is None
    assert provenance["archive_status"] == "LINK_CREATED"
    assert provenance["archive_success"] is True
    assert provenance["archive_failed"] is False
    assert provenance["stale_collision"] is False
    pending.unlink()
    archive.write_bytes(b"tampered after failure close")
    with pytest.raises(ValueError, match="archive SHA/size"):
        V94.validate_failed_result(closed, config, tmp_path)


def test_post_seal_stale_eexist_is_explicit_and_cannot_fake_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = V94.load_frozen_config()
    checks = passing_resource_prefix(10)
    for index, check in enumerate(checks[:-1]):
        check["wall_elapsed_seconds"] = float(index + 1)
    checks[-1]["wall_elapsed_seconds"] = 898.0
    state = {"elapsed": 899.0}
    pending = tmp_path / ".cv_results.complete.456.json"
    results = tmp_path / "cv_results.json"
    archive = tmp_path / V94.FAILED_SEALED_ARCHIVE_NAME
    stale_bytes = b"stale archive from another attempt"
    archive.write_bytes(stale_bytes)
    V94.atomic_write_json(pending, {"status": "THIRD_VERIFY_PASSED"})
    third_sha = V94.sha256_file(pending)
    complete_commits: list[tuple[Path, Path]] = []

    monkeypatch.setattr(V94.time, "monotonic", lambda: state["elapsed"])
    monkeypatch.setattr(V94, "process_peak_rss_bytes", lambda: 1024)

    def fourth_verifier(
        path: Path, allowed_resource_phases: set[str]
    ) -> dict[str, object]:
        assert allowed_resource_phases == {
            "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"
        }
        state["elapsed"] = 901.0
        return V94.json.loads(path.read_text(encoding="utf-8"))

    def complete_commit(source: Path, destination: Path) -> None:
        complete_commits.append((source, destination))

    monkeypatch.setattr(V94, "verify_staged_complete_file", fourth_verifier)
    monkeypatch.setattr(V94, "commit_complete_file", complete_commit)
    monkeypatch.setattr(V94, "RESULTS_PATH", results)
    caught: V94.ResourceBudgetExceeded | None = None
    try:
        V94.seal_final_guard_and_commit(
            config,
            0.0,
            pending,
            results,
            checks,
            third_sha,
            lambda guard, rows: {
                "status": "COMPLETE",
                "final_resource_check": guard,
                "resource_checks": rows,
            },
        )
    except V94.ResourceBudgetExceeded as error:
        caught = error
        V94.write_failed_result(
            config,
            "FAILED_RESOURCE_BUDGET",
            error.check,
            error,
            checks,
            artifact_root=tmp_path,
        )
    assert caught is not None
    assert complete_commits == []
    assert not any(path.name == "cv_results.json" for _, path in complete_commits)
    assert archive.read_bytes() == stale_bytes
    closed = V94.json.loads(results.read_text(encoding="utf-8"))
    provenance = closed["sealed_archive_provenance"]
    assert closed["status"] == "FAILED_RESOURCE_BUDGET"
    assert provenance["link_attempted"] is True
    assert provenance["link_succeeded"] is False
    assert provenance["link_errno"] == V94.errno.EEXIST
    error_payload = V94.json.loads(provenance["link_error"])
    assert error_payload == {
        "type": "FileExistsError",
        "errno": V94.errno.EEXIST,
        "strerror": V94.os.strerror(V94.errno.EEXIST),
        "filename": str(pending),
        "filename2": str(archive),
        "message": (
            f"[Errno {V94.errno.EEXIST}] "
            f"{V94.os.strerror(V94.errno.EEXIST)}: "
            f"{str(pending)!r} -> {str(archive)!r}"
        ),
    }
    assert provenance["link_error"] == V94.canonical_json(error_payload)
    assert provenance["archive_sha256"] == V94.sha256_file(archive)
    assert provenance["archive_size_bytes"] == len(stale_bytes)
    assert provenance["archive_matches_sealed"] is False
    assert provenance["archive_status"] == "STALE_COLLISION"
    assert provenance["archive_success"] is False
    assert provenance["archive_failed"] is True
    assert provenance["stale_collision"] is True
    assert closed["sealed_pending_archive"] == {
        "artifact": V94.FAILED_SEALED_ARCHIVE_NAME,
        "present": False,
        "physical_path_present": True,
        "archive_failed": True,
        "stale_collision": True,
        "invalid_for_use": True,
    }
    forged = copy.deepcopy(closed)
    forged_provenance = forged["sealed_archive_provenance"]
    forged_provenance["archive_status"] = "EXISTING_IDENTICAL"
    forged_provenance["archive_success"] = True
    forged_provenance["archive_failed"] = False
    forged_provenance["stale_collision"] = False
    with pytest.raises(ValueError, match="派生状态伪造"):
        V94.validate_failed_result(forged, config, tmp_path)
    forged_error = copy.deepcopy(closed)
    forged_error["sealed_archive_provenance"]["link_error"] += "forged"
    with pytest.raises(ValueError, match="link_error"):
        V94.validate_failed_result(forged_error, config, tmp_path)


def test_existing_identical_archive_is_verified_before_success(
    tmp_path: Path,
) -> None:
    pending = tmp_path / ".cv_results.complete.789.json"
    archive = tmp_path / V94.FAILED_SEALED_ARCHIVE_NAME
    sealed_bytes = b"identical sealed payload"
    pending.write_bytes(sealed_bytes)
    archive.write_bytes(sealed_bytes)
    provenance = V94.collect_sealed_archive_provenance(pending, archive)
    assert provenance["link_succeeded"] is False
    assert provenance["link_errno"] == V94.errno.EEXIST
    assert provenance["archive_matches_sealed"] is True
    assert provenance["archive_status"] == "EXISTING_IDENTICAL"
    assert provenance["archive_success"] is True
    assert provenance["archive_failed"] is False
    V94.validate_sealed_archive_provenance(provenance, tmp_path)


def test_staged_verifier_checks_actual_file_and_detects_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "pending.json"
    V94.atomic_write_json(path, {"status": "COMPLETE", "marker": 1})
    calls: list[set[str] | None] = []

    def verifier(
        payload: dict[str, object],
        allowed_resource_phases: set[str] | None = None,
    ) -> dict[str, object]:
        calls.append(allowed_resource_phases)
        return payload

    monkeypatch.setattr(V94, "verify_complete_payload", verifier)
    verified = V94.verify_staged_complete_file(path, {"SYNTHETIC_PHASE"})
    assert verified["marker"] == 1
    assert calls == [{"SYNTHETIC_PHASE"}]

    def mutating_verifier(
        payload: dict[str, object],
        allowed_resource_phases: set[str] | None = None,
    ) -> dict[str, object]:
        V94.atomic_write_json(path, {"status": "COMPLETE", "marker": 2})
        return payload

    monkeypatch.setattr(V94, "verify_complete_payload", mutating_verifier)
    with pytest.raises(ValueError, match="发生变化"):
        V94.verify_staged_complete_file(path, {"SYNTHETIC_PHASE"})


def test_source_hashes_and_row_identities_are_current() -> None:
    config = V94.load_frozen_config()
    records = V94.source_file_records(config)
    identities = V94.source_row_identities(config)
    metadata = V94.source_result_metadata(config)
    assert len(records) == 24
    assert set(identities) == {*V94.MEMBER_IDS, V94.BASELINE_ID}
    assert len({V94.canonical_json(value) for value in identities.values()}) == 1
    assert metadata[V94.BASELINE_ID]["decision"] == "PROMOTE"
