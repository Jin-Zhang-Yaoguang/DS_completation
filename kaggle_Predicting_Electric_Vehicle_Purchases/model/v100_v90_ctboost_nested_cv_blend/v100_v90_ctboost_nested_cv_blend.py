#!/usr/bin/env python3
"""v100：v90 与私有 GPU CTBoost 的 fit-only mid-ECDF 嵌套小融合。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[1]
CONFIG_PATH = OUT_DIR / "frozen_config.json"
RESULTS_PATH = OUT_DIR / "cv_results.json"
SOURCES_PATH = OUT_DIR / "sources.json"
OOF_PATH = OUT_DIR / "oof_proba.npy"
TEST_PATH = OUT_DIR / "test_proba.npy"
SUBMISSION_PATH = OUT_DIR / "submission.csv"
START_MARKER = OUT_DIR / "RUN_STARTED.json"
TRAIN_PATH = PROJECT_DIR / "data/train.csv"
TEST_CSV_PATH = PROJECT_DIR / "data/test.csv"
SAMPLE_PATH = PROJECT_DIR / "data/sample_submission.csv"
V90_DIR = PROJECT_DIR / "model/v90_v89_member_verify_budget_retry"
V95_DIR = PROJECT_DIR / "model/v95_v94_source_verifier_adapter_retry"
CT_DIR = PROJECT_DIR / "model/diagnostics/ctboost_remote_probe_20260905"
CT_OUTPUT_DIR = CT_DIR / "remote_output"
V90_RUNNER = V90_DIR / "v90_v89_member_verify_budget_retry.py"
V90_OOF = V90_DIR / "oof_proba.npy"
V90_TEST = V90_DIR / "test_proba.npy"
V95_OOF = V95_DIR / "oof_proba.npy"
CT_OOF = CT_OUTPUT_DIR / "oof.npz"
CT_SUBMISSION = CT_OUTPUT_DIR / "submission.csv"
CT_EVIDENCE = CT_DIR / "evidence.json"
EXPERIMENT_ID = "v100_v90_ctboost_nested_cv_blend"
WEIGHT_GRID = np.arange(0.0, 0.5000001, 0.025)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return native if sys.platform == "darwin" else native * 1024


def resource_check(config: dict[str, Any], started: float, phase: str) -> dict[str, Any]:
    row = {
        "phase": phase,
        "elapsed_seconds": float(time.monotonic() - started),
        "peak_rss_bytes": peak_rss_bytes(),
    }
    row["wall_ok"] = row["elapsed_seconds"] <= config["wall_budget_seconds"]
    row["memory_ok"] = row["peak_rss_bytes"] <= config["memory_budget_bytes"]
    if not row["wall_ok"] or not row["memory_ok"]:
        raise RuntimeError(f"resource budget exceeded: {row}")
    return row


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_npy(path: Path, values: np.ndarray) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            np.save(handle, values, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as handle:
            frame.to_csv(handle, index=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("experiment_id 漂移")
    if config.get("runner_sha256") != sha256_file(Path(__file__)):
        raise ValueError("runner SHA 漂移")
    if config.get("meta_weight_grid") != WEIGHT_GRID.tolist():
        raise ValueError("meta weight grid 漂移")
    if config.get("research_promotion_minimum_delta") != 0.0001:
        raise ValueError("研究门槛漂移")
    if config.get("submission_reference_oof_auc") != 0.9463838901455106:
        raise ValueError("提交参考线漂移")
    return config


def source_paths() -> dict[str, Path]:
    return {
        "train.csv": TRAIN_PATH,
        "test.csv": TEST_CSV_PATH,
        "sample_submission.csv": SAMPLE_PATH,
        "v90_runner": V90_RUNNER,
        "v90_config": V90_DIR / "frozen_config.json",
        "v90_cv": V90_DIR / "cv_results.json",
        "v90_sources": V90_DIR / "sources.json",
        "v90_oof": V90_OOF,
        "v90_test": V90_TEST,
        "v95_oof": V95_OOF,
        "ct_evidence": CT_EVIDENCE,
        "ct_oof": CT_OOF,
        "ct_submission": CT_SUBMISSION,
        "ct_run_summary": CT_OUTPUT_DIR / "run_summary.json",
        "ct_log": CT_OUTPUT_DIR / "s6e9-ctboost-oof-audit.log",
        "ct_notebook": CT_DIR / "kernel/s6e9-ctboost-oof-audit.ipynb",
        "ct_kernel_metadata": CT_DIR / "kernel/kernel-metadata.json",
    }


def verify_source_hashes(config: dict[str, Any]) -> dict[str, str]:
    observed = {name: sha256_file(path) for name, path in source_paths().items()}
    if observed != config["source_sha256"]:
        mismatches = {
            name: {"expected": config["source_sha256"].get(name), "observed": value}
            for name, value in observed.items()
            if config["source_sha256"].get(name) != value
        }
        raise ValueError(f"source SHA 漂移：{mismatches}")
    return observed


def invoke_v90_verifier() -> None:
    spec = importlib.util.spec_from_file_location("v100_bound_v90", V90_RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载 v90 verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.verify_complete_payload()
    if result.get("status") != "COMPLETE" or result.get("decision") != "PROMOTE":
        raise ValueError("v90 完整 verifier 结果异常")


def fit_mid_ecdf(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("ECDF fit 输入非法")
    return np.sort(values)


def transform_mid_ecdf(state: np.ndarray, values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("ECDF transform 输入非法")
    return (
        np.searchsorted(state, values, side="left")
        + np.searchsorted(state, values, side="right")
    ) / (2.0 * len(state))


def expected_fold_ids(y: np.ndarray) -> np.ndarray:
    fold_ids = np.full(len(y), -1, dtype=np.int8)
    splitter = StratifiedKFold(5, shuffle=True, random_state=42)
    for fold, (_, valid_idx) in enumerate(splitter.split(np.zeros(len(y)), y)):
        fold_ids[valid_idx] = fold
    if np.any(fold_ids < 0):
        raise AssertionError("fold coverage 不完整")
    return fold_ids


def choose_weight(y: np.ndarray, core: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    scores = [
        float(roc_auc_score(y, (1.0 - weight) * core + weight * candidate))
        for weight in WEIGHT_GRID
    ]
    index = max(
        range(len(WEIGHT_GRID)), key=lambda item: (scores[item], -WEIGHT_GRID[item])
    )
    return float(WEIGHT_GRID[index]), scores[index]


def nested_blend(
    y: np.ndarray,
    core_oof: np.ndarray,
    candidate_oof: np.ndarray,
    core_test: np.ndarray | None = None,
    candidate_test: np.ndarray | None = None,
) -> dict[str, Any]:
    fold_ids = expected_fold_ids(y)
    oof = np.full(len(y), np.nan, dtype=np.float64)
    baseline = np.full(len(y), np.nan, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    for fold in range(5):
        fit_idx = np.flatnonzero(fold_ids != fold)
        hold_idx = np.flatnonzero(fold_ids == fold)
        core_state = fit_mid_ecdf(core_oof[fit_idx])
        candidate_state = fit_mid_ecdf(candidate_oof[fit_idx])
        core_fit = transform_mid_ecdf(core_state, core_oof[fit_idx])
        candidate_fit = transform_mid_ecdf(candidate_state, candidate_oof[fit_idx])
        core_hold = transform_mid_ecdf(core_state, core_oof[hold_idx])
        candidate_hold = transform_mid_ecdf(candidate_state, candidate_oof[hold_idx])
        weight, fit_auc = choose_weight(y[fit_idx], core_fit, candidate_fit)
        baseline[hold_idx] = core_hold
        oof[hold_idx] = (1.0 - weight) * core_hold + weight * candidate_hold
        baseline_auc = float(roc_auc_score(y[hold_idx], baseline[hold_idx]))
        blend_auc = float(roc_auc_score(y[hold_idx], oof[hold_idx]))
        rows.append(
            {
                "fold": fold + 1,
                "selected_ctboost_weight": weight,
                "meta_train_auc": fit_auc,
                "holdout_baseline_auc": baseline_auc,
                "holdout_blend_auc": blend_auc,
                "holdout_delta": blend_auc - baseline_auc,
            }
        )
    if not np.isfinite(oof).all() or not np.isfinite(baseline).all():
        raise AssertionError("meta OOF coverage 不完整")
    core_full_state = fit_mid_ecdf(core_oof)
    candidate_full_state = fit_mid_ecdf(candidate_oof)
    core_full = transform_mid_ecdf(core_full_state, core_oof)
    candidate_full = transform_mid_ecdf(candidate_full_state, candidate_oof)
    final_weight, full_fit_auc = choose_weight(y, core_full, candidate_full)
    test_prediction = None
    if core_test is not None or candidate_test is not None:
        if core_test is None or candidate_test is None:
            raise ValueError("test 成员必须成对提供")
        core_test_rank = transform_mid_ecdf(core_full_state, core_test)
        candidate_test_rank = transform_mid_ecdf(candidate_full_state, candidate_test)
        test_prediction = (
            (1.0 - final_weight) * core_test_rank
            + final_weight * candidate_test_rank
        )
    baseline_auc = float(roc_auc_score(y, baseline))
    oof_auc = float(roc_auc_score(y, oof))
    return {
        "oof": oof,
        "baseline_oof": baseline,
        "test": test_prediction,
        "fold_rows": rows,
        "baseline_auc": baseline_auc,
        "oof_auc": oof_auc,
        "delta_vs_baseline": oof_auc - baseline_auc,
        "positive_folds": sum(row["holdout_delta"] > 0.0 for row in rows),
        "final_ctboost_weight": final_weight,
        "full_fit_apparent_auc": full_fit_auc,
    }


def load_inputs(config: dict[str, Any]) -> dict[str, Any]:
    train = pd.read_csv(TRAIN_PATH)
    test = pd.read_csv(TEST_CSV_PATH)
    sample = pd.read_csv(SAMPLE_PATH)
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    core_oof = np.load(V90_OOF, allow_pickle=False).astype(np.float64, copy=False)
    core_test = np.load(V90_TEST, allow_pickle=False).astype(np.float64, copy=False)
    v95_oof = np.load(V95_OOF, allow_pickle=False).astype(np.float64, copy=False)
    with np.load(CT_OOF, allow_pickle=False) as archive:
        if set(archive.files) != {"id", "target", "prediction", "fold"}:
            raise ValueError("CT OOF schema 漂移")
        ct_ids = np.asarray(archive["id"])
        ct_target = np.asarray(archive["target"])
        ct_oof = np.asarray(archive["prediction"], dtype=np.float64)
        ct_folds = np.asarray(archive["fold"], dtype=np.int8)
    ct_submission = pd.read_csv(CT_SUBMISSION)
    vectors = (core_oof, v95_oof, ct_ids, ct_target, ct_oof, ct_folds)
    if any(vector.shape != (len(train),) for vector in vectors):
        raise ValueError("OOF shape 漂移")
    if core_test.shape != (len(test),):
        raise ValueError("v90 test shape 漂移")
    if not np.array_equal(ct_ids, train[config["id_column"]].to_numpy()):
        raise ValueError("CT OOF ID 顺序漂移")
    if not np.array_equal(ct_target, y):
        raise ValueError("CT OOF target 漂移")
    if not np.array_equal(ct_folds, expected_fold_ids(y)):
        raise ValueError("CT OOF fold 漂移")
    if list(ct_submission.columns) != [config["id_column"], config["target"]]:
        raise ValueError("CT submission schema 漂移")
    if not ct_submission[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("CT test ID 顺序漂移")
    ct_test = ct_submission[config["target"]].to_numpy(np.float64)
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample/test ID 不一致")
    for name, values in {
        "v90_oof": core_oof,
        "v90_test": core_test,
        "v95_oof": v95_oof,
        "ct_oof": ct_oof,
        "ct_test": ct_test,
    }.items():
        if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
            raise ValueError(f"{name} 非有限或越界")
    evidence = json.loads(CT_EVIDENCE.read_text(encoding="utf-8"))
    if (
        evidence.get("status") != "COMPLETE"
        or evidence["aggregate"].get("decision") != "NO_GO"
        or evidence["remote_kernel"].get("competition_submitted") is not False
        or evidence["remote_kernel"].get("private") is not True
    ):
        raise ValueError("CT 诊断证据语义漂移")
    return {
        "train": train,
        "test": test,
        "sample": sample,
        "y": y,
        "core_oof": core_oof,
        "core_test": core_test,
        "v95_oof": v95_oof,
        "ct_oof": ct_oof,
        "ct_test": ct_test,
    }


def build_sources(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "source_sha256": config["source_sha256"],
        "members": {
            "v90": {
                "oof": str(V90_OOF.relative_to(PROJECT_DIR)),
                "test": str(V90_TEST.relative_to(PROJECT_DIR)),
                "role": "strict_promoted_core_ensemble",
            },
            "ctboost": {
                "oof": str(CT_OOF.relative_to(PROJECT_DIR)),
                "test": str(CT_SUBMISSION.relative_to(PROJECT_DIR)) + "::Will_Buy_EV",
                "role": "private_gpu_seed42_fivefold_atomic_model",
            },
        },
        "lineage_policy": "v90 is an ensemble parent and CTBoost is a distinct atomic family; no v90 child is also loaded",
        "public_predictions_used": False,
        "leaderboard_used_for_weight_selection": False,
    }


def compute_result(config: dict[str, Any], inputs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    blend = nested_blend(
        inputs["y"],
        inputs["core_oof"],
        inputs["ct_oof"],
        inputs["core_test"],
        inputs["ct_test"],
    )
    v95_auc = float(roc_auc_score(inputs["y"], inputs["v95_oof"]))
    research_pass = (
        blend["delta_vs_baseline"] >= config["research_promotion_minimum_delta"]
        and blend["positive_folds"] == 5
    )
    submission_authorized = blend["oof_auc"] >= v95_auc
    decision = (
        "PROMOTE"
        if research_pass
        else (
            "REJECT_RESEARCH_PROMOTION_SUBMISSION_AUTHORIZED_BY_USER_THRESHOLD"
            if submission_authorized
            else "REJECT_NO_SUBMISSION"
        )
    )
    evaluation = {
        "oof_auc": blend["oof_auc"],
        "base_oof_auc": blend["baseline_auc"],
        "oof_delta_vs_base": blend["delta_vs_baseline"],
        "positive_meta_folds": blend["positive_folds"],
        "v95_reference_oof_auc": v95_auc,
        "delta_vs_v95_reference": blend["oof_auc"] - v95_auc,
        "ctboost_oof_auc": float(roc_auc_score(inputs["y"], inputs["ct_oof"])),
        "spearman_oof_vs_v90": float(
            spearmanr(inputs["ct_oof"], inputs["core_oof"]).statistic
        ),
        "spearman_test_vs_v90": float(
            spearmanr(inputs["ct_test"], inputs["core_test"]).statistic
        ),
        "final_ctboost_weight": blend["final_ctboost_weight"],
        "full_fit_apparent_auc_diagnostic_only": blend["full_fit_apparent_auc"],
        "research_promotion_gate_passed": research_pass,
        "user_submission_threshold_passed": submission_authorized,
        "decision": decision,
    }
    return blend, evaluation


def audit() -> dict[str, Any]:
    config = load_config()
    verify_source_hashes(config)
    payload = {
        "status": "AUDIT_OK_HASH_ONLY_NO_PREDICTIONS_PARSED",
        "experiment_id": EXPERIMENT_ID,
        "source_count": len(config["source_sha256"]),
        "weight_grid": WEIGHT_GRID.tolist(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def smoke() -> dict[str, Any]:
    rng = np.random.default_rng(20260905)
    y = np.tile(np.array([0, 1], dtype=np.int8), 250)
    core = y + rng.normal(0.0, 0.8, len(y))
    candidate = -core
    result = nested_blend(y, core, candidate)
    if any(row["selected_ctboost_weight"] != 0.0 for row in result["fold_rows"]):
        raise AssertionError("合成反向成员未被拒绝")
    payload = {
        "status": "SMOKE_OK_SYNTHETIC_ONLY",
        "experiment_id": EXPERIMENT_ID,
        "meta_folds": len(result["fold_rows"]),
        "formal_outputs_created": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def run() -> dict[str, Any]:
    config = load_config()
    terminal_outputs = [RESULTS_PATH, SOURCES_PATH, OOF_PATH, TEST_PATH, SUBMISSION_PATH]
    if any(path.exists() for path in terminal_outputs):
        raise RuntimeError("正式产物已存在，拒绝覆盖或重复运行")
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump({"status": "RUN_STARTED_ONE_SHOT", "pid": os.getpid()}, handle)
    except FileExistsError as error:
        raise RuntimeError("RUN_STARTED marker 已存在，拒绝重复运行") from error
    started = time.monotonic()
    checks = [resource_check(config, started, "START")]
    verify_source_hashes(config)
    invoke_v90_verifier()
    verify_source_hashes(config)
    checks.append(resource_check(config, started, "AFTER_SOURCE_VERIFY"))
    inputs = load_inputs(config)
    blend, evaluation = compute_result(config, inputs)
    checks.append(resource_check(config, started, "AFTER_META_CV"))
    atomic_npy(OOF_PATH, blend["oof"])
    if blend["test"] is None:
        raise AssertionError("test prediction 缺失")
    atomic_npy(TEST_PATH, blend["test"])
    submission = inputs["sample"].copy()
    submission[config["target"]] = blend["test"]
    atomic_csv(SUBMISSION_PATH, submission)
    sources = build_sources(config)
    atomic_json(SOURCES_PATH, sources)
    checks.append(resource_check(config, started, "AFTER_OUTPUTS"))
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": "C01",
        "cycle_position": 17,
        "experiment_type": "SMALL_BLEND_2_MEMBER",
        "counts_toward_cycle": True,
        "model": "v90 plus CTBoost fit-only mid-ECDF nested meta blend",
        "n_folds": 5,
        "fold_auc": [row["holdout_blend_auc"] for row in blend["fold_rows"]],
        "oof_auc": evaluation["oof_auc"],
        "base": "v90_v89_member_verify_budget_retry",
        "base_oof_auc": evaluation["base_oof_auc"],
        "oof_delta_vs_base": evaluation["oof_delta_vs_base"],
        "meta_fold_rows": blend["fold_rows"],
        "evaluation": evaluation,
        "params": {
            "transform": "fit-only mid-ECDF per member",
            "meta_folds": "StratifiedKFold(5, shuffle=True, random_state=42)",
            "ctboost_weight_grid": WEIGHT_GRID.tolist(),
            "tie_break": "smallest CTBoost weight",
        },
        "decision": evaluation["decision"],
        "allowed_for_fusion": evaluation["research_promotion_gate_passed"],
        "eligible_for_separate_preregistration": False,
        "allowed_for_submission": evaluation["user_submission_threshold_passed"],
        "submission_budget": 1,
        "online_result_may_change_research_decision": False,
        "source_sha256": config["source_sha256"],
        "artifact_sha256": {
            "oof_proba.npy": sha256_file(OOF_PATH),
            "test_proba.npy": sha256_file(TEST_PATH),
            "submission.csv": sha256_file(SUBMISSION_PATH),
            "sources.json": sha256_file(SOURCES_PATH),
        },
        "resource_checks": checks,
        "elapsed_seconds": checks[-1]["elapsed_seconds"],
        "peak_rss_bytes": checks[-1]["peak_rss_bytes"],
    }
    atomic_json(RESULTS_PATH, payload)
    verify()
    return payload


def verify() -> dict[str, Any]:
    config = load_config()
    verify_source_hashes(config)
    invoke_v90_verifier()
    verify_source_hashes(config)
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    inputs = load_inputs(config)
    blend, evaluation = compute_result(config, inputs)
    stored_oof = np.load(OOF_PATH, allow_pickle=False)
    stored_test = np.load(TEST_PATH, allow_pickle=False)
    if not np.array_equal(stored_oof, blend["oof"]):
        raise ValueError("OOF 无法重建")
    if blend["test"] is None or not np.array_equal(stored_test, blend["test"]):
        raise ValueError("test 无法重建")
    submission = pd.read_csv(SUBMISSION_PATH)
    if (
        not submission[config["id_column"]].equals(inputs["test"][config["id_column"]])
        or not np.allclose(
            submission[config["target"]].to_numpy(np.float64),
            stored_test,
            atol=1e-15,
            rtol=0.0,
        )
    ):
        raise ValueError("submission 无法重建")
    if results.get("status") != "COMPLETE" or results.get("evaluation") != evaluation:
        raise ValueError("cv_results 核心语义无法重建")
    expected_artifacts = {
        "oof_proba.npy": sha256_file(OOF_PATH),
        "test_proba.npy": sha256_file(TEST_PATH),
        "submission.csv": sha256_file(SUBMISSION_PATH),
        "sources.json": sha256_file(SOURCES_PATH),
    }
    if results.get("artifact_sha256") != expected_artifacts:
        raise ValueError("artifact SHA 无法重建")
    if json.loads(SOURCES_PATH.read_text(encoding="utf-8")) != build_sources(config):
        raise ValueError("sources 无法重建")
    return {
        "status": "COMPLETE_VERIFIED",
        "experiment_id": EXPERIMENT_ID,
        "oof_auc": evaluation["oof_auc"],
        "decision": evaluation["decision"],
        "allowed_for_submission": evaluation["user_submission_threshold_passed"],
    }


def preserve_failure(error: Exception) -> None:
    if RESULTS_PATH.exists():
        return
    present = sorted(
        path.name
        for path in (SOURCES_PATH, OOF_PATH, TEST_PATH, SUBMISSION_PATH, START_MARKER)
        if path.exists()
    )
    atomic_json(
        RESULTS_PATH,
        {
            "schema_version": 1,
            "status": "FAILED_EXCEPTION",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": "C01",
            "cycle_position": 17,
            "counts_toward_cycle": True,
            "error_type": type(error).__name__,
            "error": str(error),
            "decision": "FAILED_EXCEPTION",
            "present_artifacts": present,
            "present_artifacts_are_invalid_for_use": True,
            "allowed_for_fusion": False,
            "allowed_for_submission": False,
            "runner_sha256": sha256_file(Path(__file__)),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "smoke", "run", "verify"), default="audit")
    args = parser.parse_args()
    if args.mode == "audit":
        audit()
    elif args.mode == "smoke":
        smoke()
    elif args.mode == "run":
        try:
            payload = run()
        except Exception as error:
            preserve_failure(error)
            raise
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
