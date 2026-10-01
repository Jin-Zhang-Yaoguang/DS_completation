#!/usr/bin/env python3
"""GAM additive vs joint-replacement init_score 的 matched residual-LGBM 五折诊断。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import resource
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
V96_DIR = PROJECT_DIR / "model/v96_strict_v80_outer42_matched_control_40f"
V96_RUNNER = V96_DIR / "v96_strict_v80_outer42_matched_control_40f.py"
V96_CONFIG = V96_DIR / "frozen_config.json"
V98_PROBE_EVIDENCE = (
    PROJECT_DIR / "model/v98_supervised_gam_init_score_40f/probe_archive/evidence.json"
)
STAGE1_DIR = (
    PROJECT_DIR / "model/diagnostics/gam_dominant_joint_replacement_probe_20260905"
)
STAGE1_RUNNER = STAGE1_DIR / "probe.py"
STAGE1_EVIDENCE = STAGE1_DIR / "evidence.json"
START_MARKER = OUT_DIR / "RUN_STARTED.json"
EVIDENCE_PATH = OUT_DIR / "evidence.json"
EXPERIMENT_ID = "TEMP_GAM_JOINT_REPLACEMENT_RESIDUAL_LGBM_5FOLD_SEED42"
MARGIN_CAP = math.log((1.0 - 1e-6) / 1e-6)
GATE_DELTA = 0.0001
GATE_WINS = 4
WALL_BUDGET_SECONDS = 1200.0
MEMORY_BUDGET_BYTES = 12 * 1024**3
EXPECTED_A_OOF = 0.9461008204503822


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return native if sys.platform == "darwin" else native * 1024


def resource_guard(started: float, phase: str) -> dict[str, Any]:
    row = {
        "phase": phase,
        "elapsed_seconds": float(time.monotonic() - started),
        "peak_rss_bytes": peak_rss_bytes(),
    }
    row["wall_ok"] = row["elapsed_seconds"] <= WALL_BUDGET_SECONDS
    row["memory_ok"] = row["peak_rss_bytes"] <= MEMORY_BUDGET_BYTES
    if not row["wall_ok"] or not row["memory_ok"]:
        raise RuntimeError(f"resource budget exceeded: {row}")
    return row


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_design() -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "outer_folds": 5,
        "outer_seed": 42,
        "arm_a": "strict-v96 residual LightGBM with outer-fit v98 additive 39-column GAM init_score",
        "arm_b": "same residual LightGBM with outer-fit 81-column dominant-joint replacement GAM init_score",
        "only_variable": "GAM dominant block representation",
        "expected_a_oof": EXPECTED_A_OOF,
        "gate_delta": GATE_DELTA,
        "gate_wins": GATE_WINS,
        "wall_budget_seconds": WALL_BUDGET_SECONDS,
        "memory_budget_bytes": MEMORY_BUDGET_BYTES,
        "threads": 8,
        "submission_budget": 0,
        "test_prediction_generated": False,
        "oof_arrays_saved": False,
        "no_grid_or_retry": True,
    }


def fit_gam_margin(
    pipeline: Any,
    fit_frame: pd.DataFrame,
    fit_y: np.ndarray,
    valid_frame: pd.DataFrame,
    expected_features: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pipeline.fit(fit_frame, fit_y)
    convergence = [
        str(item.message)
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
    ]
    if convergence:
        raise RuntimeError(f"GAM Logistic 未收敛：{convergence}")
    names = pipeline.named_steps["transform"].get_feature_names_out()
    if len(names) != expected_features:
        raise ValueError(f"GAM features {len(names)} != {expected_features}")
    fit_unclipped = pipeline.decision_function(fit_frame)
    valid_unclipped = pipeline.decision_function(valid_frame)
    fit_margin = np.clip(fit_unclipped, -MARGIN_CAP, MARGIN_CAP)
    valid_margin = np.clip(valid_unclipped, -MARGIN_CAP, MARGIN_CAP)
    if not np.isfinite(fit_margin).all() or not np.isfinite(valid_margin).all():
        raise ValueError("GAM margin 非有限")
    return fit_margin, valid_margin, {
        "features": int(len(names)),
        "iterations": int(pipeline.named_steps["logistic"].n_iter_[0]),
        "fit_clip_count": int(np.count_nonzero(fit_margin != fit_unclipped)),
        "valid_clip_count": int(np.count_nonzero(valid_margin != valid_unclipped)),
    }


def fit_residual(
    params: dict[str, Any],
    early_stopping_rounds: int,
    x_fit: np.ndarray,
    y_fit: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    fit_margin: np.ndarray,
    valid_margin: np.ndarray,
) -> tuple[np.ndarray, int]:
    model = lgb.LGBMClassifier(**params)
    model.fit(
        x_fit,
        y_fit,
        init_score=fit_margin,
        eval_set=[(x_valid, y_valid)],
        eval_init_score=[valid_margin],
        eval_metric="auc",
        callbacks=[
            lgb.early_stopping(early_stopping_rounds, verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )
    iteration = int(model.best_iteration_ or params["n_estimators"])
    residual = model.booster_.predict(x_valid, raw_score=True, num_iteration=iteration)
    prediction = expit(valid_margin + residual)
    auc = float(roc_auc_score(y_valid, prediction))
    if not np.isclose(auc, model.best_score_["valid_0"]["auc"], atol=1e-12, rtol=0.0):
        raise RuntimeError("LightGBM early-stop AUC 与重建不一致")
    return prediction, iteration


def audit() -> dict[str, Any]:
    stage1 = json.loads(STAGE1_EVIDENCE.read_text(encoding="utf-8"))
    v98 = json.loads(V98_PROBE_EVIDENCE.read_text(encoding="utf-8"))
    if stage1.get("aggregate", {}).get("decision") != "STAGE2_GO":
        raise ValueError("stage1 未授权")
    if not np.isclose(v98.get("pooled_auc_b"), EXPECTED_A_OOF, atol=1e-15, rtol=0.0):
        raise ValueError("v98 五折控制漂移")
    payload = {
        "status": "AUDIT_OK_NO_TRAINING",
        "frozen_design": frozen_design(),
        "source_sha256": {
            "v96_runner": sha256_file(V96_RUNNER),
            "v96_config": sha256_file(V96_CONFIG),
            "stage1_runner": sha256_file(STAGE1_RUNNER),
            "stage1_evidence": sha256_file(STAGE1_EVIDENCE),
            "v98_probe_evidence": sha256_file(V98_PROBE_EVIDENCE),
        },
    }
    return payload


def run() -> dict[str, Any]:
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump({"status": "RUN_STARTED_ONE_SHOT", "pid": os.getpid()}, handle)
    except FileExistsError as error:
        raise RuntimeError("one-shot marker 已存在，拒绝重复运行") from error
    started = time.monotonic()
    runner_sha = sha256_file(Path(__file__))
    checks = [resource_guard(started, "START")]
    audit_payload = audit()
    config = json.loads(V96_CONFIG.read_text(encoding="utf-8"))
    v96 = load_module("gam_joint_bound_v96", V96_RUNNER)
    stage1 = load_module("gam_joint_bound_stage1", STAGE1_RUNNER)
    recipe = v96.load_recipe()
    train, test, _sample = recipe.base.load_data()
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    gam_frame = stage1.add_dominant_joint(train.drop(columns=[config["target"]]))
    if gam_frame[stage1.JOINT_COLUMN].nunique() != stage1.JOINT_LEVELS:
        raise ValueError("joint levels 漂移")
    x_train, _x_test, keys_train, keys_test = recipe.base.build_static_features(train, test)
    if x_train.shape != (len(train), config["expected_static_features"]):
        raise ValueError("strict static feature shape 漂移")
    oof_a = np.full(len(train), np.nan, dtype=np.float64)
    oof_b = np.full(len(train), np.nan, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    folds = StratifiedKFold(5, shuffle=True, random_state=42)
    for fold, (fit_idx, valid_idx) in enumerate(folds.split(x_train, y), start=1):
        inner = list(
            StratifiedKFold(
                config["n_inner_folds"],
                shuffle=True,
                random_state=config["inner_te_seed_base"] + fold,
            ).split(np.zeros(len(fit_idx)), y[fit_idx])
        )
        fit_te: list[np.ndarray] = []
        valid_te: list[np.ndarray] = []
        for key in recipe.base.TE_KEYS:
            fit_block, valid_block, _ = v96.strict_encode_key(
                keys_train[key],
                keys_test[key],
                y,
                fit_idx,
                valid_idx,
                inner,
                tuple(config["smooths"]),
            )
            fit_te.append(fit_block)
            valid_te.append(valid_block)
        x_fit = np.column_stack([x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te])
        x_valid = np.column_stack([x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te])
        if x_fit.shape[1] != config["expected_total_features"]:
            raise ValueError("strict total feature shape 漂移")
        del fit_te, valid_te
        checks.append(resource_guard(started, f"FOLD_{fold}_AFTER_TE"))
        fit_frame = gam_frame.iloc[fit_idx]
        valid_frame = gam_frame.iloc[valid_idx]
        margin_a_fit, margin_a_valid, profile_a = fit_gam_margin(
            stage1.make_pipeline(False),
            fit_frame,
            y[fit_idx],
            valid_frame,
            stage1.BASE_FEATURES,
        )
        pred_a, iteration_a = fit_residual(
            dict(config["lightgbm_params"]),
            config["early_stopping_rounds"],
            x_fit,
            y[fit_idx],
            x_valid,
            y[valid_idx],
            margin_a_fit,
            margin_a_valid,
        )
        del margin_a_fit, margin_a_valid
        checks.append(resource_guard(started, f"FOLD_{fold}_AFTER_A"))
        margin_b_fit, margin_b_valid, profile_b = fit_gam_margin(
            stage1.make_pipeline(True),
            fit_frame,
            y[fit_idx],
            valid_frame,
            stage1.JOINT_FEATURES,
        )
        pred_b, iteration_b = fit_residual(
            dict(config["lightgbm_params"]),
            config["early_stopping_rounds"],
            x_fit,
            y[fit_idx],
            x_valid,
            y[valid_idx],
            margin_b_fit,
            margin_b_valid,
        )
        del margin_b_fit, margin_b_valid, x_fit, x_valid
        oof_a[valid_idx] = pred_a
        oof_b[valid_idx] = pred_b
        auc_a = float(roc_auc_score(y[valid_idx], pred_a))
        auc_b = float(roc_auc_score(y[valid_idx], pred_b))
        row = {
            "fold": fold,
            "auc_a": auc_a,
            "auc_b": auc_b,
            "delta_b_minus_a": auc_b - auc_a,
            "best_iteration_a": iteration_a,
            "best_iteration_b": iteration_b,
            "gam_profile_a": profile_a,
            "gam_profile_b": profile_b,
        }
        rows.append(row)
        checks.append(resource_guard(started, f"FOLD_{fold}_COMPLETE"))
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
    if not np.isfinite(oof_a).all() or not np.isfinite(oof_b).all():
        raise RuntimeError("OOF coverage 不完整")
    auc_a = float(roc_auc_score(y, oof_a))
    auc_b = float(roc_auc_score(y, oof_b))
    if not np.isclose(auc_a, EXPECTED_A_OOF, atol=1e-15, rtol=0.0):
        raise RuntimeError(f"A 未精确复现 v98 五折：{auc_a} != {EXPECTED_A_OOF}")
    delta = auc_b - auc_a
    wins = sum(row["delta_b_minus_a"] > 0 for row in rows)
    gate = delta >= GATE_DELTA and wins >= GATE_WINS
    checks.append(resource_guard(started, "COMPLETE"))
    if sha256_file(Path(__file__)) != runner_sha:
        raise RuntimeError("运行期间 runner 漂移")
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "counts_toward_c01": False,
        "frozen_design": frozen_design(),
        "folds": rows,
        "aggregate": {
            "auc_a": auc_a,
            "auc_b": auc_b,
            "delta_b_minus_a": delta,
            "winning_folds": wins,
            "formal_40f_gate_passed": gate,
            "decision": "FORMAL_40F_GO" if gate else "NO_GO",
        },
        "source_sha256": audit_payload["source_sha256"] | {"probe.py": runner_sha},
        "elapsed_seconds": checks[-1]["elapsed_seconds"],
        "peak_rss_bytes": checks[-1]["peak_rss_bytes"],
        "resource_checks": checks,
    }
    atomic_json(EVIDENCE_PATH, payload)
    return payload


def preserve_failure(error: Exception) -> None:
    if EVIDENCE_PATH.exists():
        return
    atomic_json(
        EVIDENCE_PATH,
        {
            "schema_version": 1,
            "status": "FAILED_IMPLEMENTATION",
            "experiment_id": EXPERIMENT_ID,
            "error_type": type(error).__name__,
            "error": str(error),
            "decision": "CLOSE_NO_RERUN",
            "source_sha256": {"probe.py": sha256_file(Path(__file__))},
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "run"), default="audit")
    args = parser.parse_args()
    try:
        payload = run() if args.mode == "run" else audit()
    except Exception as error:
        if args.mode == "run":
            preserve_failure(error)
        raise
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
