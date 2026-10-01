#!/usr/bin/env python3
"""One-shot five-fold matched A/B: strict-v80 vs frozen 39-column GAM init_score."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import resource
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import sklearn
from scipy.special import expit
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler


PROJECT = Path(
    "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/"
    "strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases"
)
OUT_DIR = Path("/tmp/s6e9_gam_init_ab_r0")
EVIDENCE_PATH = OUT_DIR / "evidence.json"
START_MARKER = OUT_DIR / "RUN_STARTED.json"
V96_PATH = (
    PROJECT
    / "model/v96_strict_v80_outer42_matched_control_40f/"
    "v96_strict_v80_outer42_matched_control_40f.py"
)
V96_CONFIG_PATH = (
    PROJECT
    / "model/v96_strict_v80_outer42_matched_control_40f/frozen_config.json"
)

OUTER_FOLDS = 5
OUTER_SEED = 42
WALL_BUDGET_SECONDS = 1800.0
MEMORY_BUDGET_BYTES = 16 * 1024**3
SUBMISSION_BUDGET = 0
GATE_DELTA = 0.0001
GATE_WINS = 4
MARGIN_CAP = math.log((1.0 - 1e-6) / 1e-6)

SPLINE_COLUMNS = ["Age", "Annual_Income_USD", "Daily_Commute_km"]
LINEAR_COLUMNS = [
    "Number_of_Cars_Owned",
    "Charging_Stations_Near_Home",
    "Charging_Stations_Near_Work",
    "Environmental_Concern_Level",
]
CATEGORICAL_COLUMNS = [
    "Gender",
    "City_Type",
    "Current_Car_Type",
    "Home_Charging_Possible",
    "Subsidy_Available",
    "Range_Anxiety_Level",
]
EXPECTED_GAM_FEATURES = 39


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def id_sha256(values: pd.Series) -> str:
    payload = "\n".join(values.astype(str).tolist()) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return native if sys.platform == "darwin" else native * 1024


def write_evidence(payload: dict[str, Any]) -> None:
    temp = EVIDENCE_PATH.with_suffix(".json.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temp, EVIDENCE_PATH)


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("frozen_v96_probe_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_gam_pipeline() -> Pipeline:
    spline = Pipeline(
        [
            (
                "spline",
                SplineTransformer(
                    n_knots=5,
                    degree=3,
                    knots="quantile",
                    extrapolation="linear",
                    include_bias=False,
                    order="C",
                    sparse_output=False,
                ),
            ),
            ("scale", StandardScaler(with_mean=True, with_std=True)),
        ]
    )
    linear = Pipeline(
        [("scale", StandardScaler(with_mean=True, with_std=True))]
    )
    categorical = OneHotEncoder(
        categories="auto",
        drop=None,
        sparse_output=False,
        dtype=np.float64,
        handle_unknown="ignore",
        min_frequency=None,
        max_categories=None,
    )
    transform = ColumnTransformer(
        [
            ("spline", spline, SPLINE_COLUMNS),
            ("linear", linear, LINEAR_COLUMNS),
            ("categorical", categorical, CATEGORICAL_COLUMNS),
        ],
        remainder="drop",
        sparse_threshold=0.0,
        verbose_feature_names_out=True,
    )
    logistic = LogisticRegression(
        penalty="l2",
        C=0.1,
        dual=False,
        tol=1e-8,
        fit_intercept=True,
        class_weight=None,
        random_state=None,
        solver="lbfgs",
        max_iter=1000,
        multi_class="deprecated",
        verbose=0,
        warm_start=False,
        n_jobs=None,
        l1_ratio=None,
    )
    return Pipeline([("transform", transform), ("logistic", logistic)])


def resource_guard(started: float, phase: str) -> dict[str, Any]:
    row = {
        "phase": phase,
        "elapsed_seconds": float(time.monotonic() - started),
        "peak_rss_bytes": peak_rss_bytes(),
    }
    row["wall_ok"] = row["elapsed_seconds"] <= WALL_BUDGET_SECONDS
    row["memory_ok"] = row["peak_rss_bytes"] <= MEMORY_BUDGET_BYTES
    if not row["wall_ok"] or not row["memory_ok"]:
        raise RuntimeError(f"resource budget exceeded at {phase}: {row}")
    return row


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started_wall = time.time()
    started = time.monotonic()
    marker = {
        "status": "RUN_STARTED_ONE_SHOT",
        "pid": os.getpid(),
        "started_unix": started_wall,
        "outer_folds": OUTER_FOLDS,
        "outer_seed": OUTER_SEED,
    }
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump(marker, handle, ensure_ascii=False, indent=2, sort_keys=True)
    except FileExistsError as error:
        raise RuntimeError("one-shot run marker already exists; refusing rerun") from error

    script_sha_at_start = sha256_file(Path(__file__))
    config_sha = sha256_file(V96_CONFIG_PATH)
    config = json.loads(V96_CONFIG_PATH.read_text(encoding="utf-8"))
    source = load_module(V96_PATH)
    recipe = source.load_recipe()
    train, test, _sample = recipe.base.load_data()
    if train.isna().any().any() or test.isna().any().any():
        raise ValueError("missing data violates frozen data contract")
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    if len(train) != int(config["expected_train_rows"]):
        raise ValueError("train row count mismatch")
    if len(test) != int(config["expected_test_rows"]):
        raise ValueError("test row count mismatch")

    x_train, _x_test, keys_train, keys_test = recipe.base.build_static_features(
        train, test
    )
    if x_train.shape != (len(train), int(config["expected_static_features"])):
        raise ValueError(f"strict static shape mismatch: {x_train.shape}")
    if list(recipe.base.TE_KEYS) != list(config["te_keys"]):
        raise ValueError("strict TE key order mismatch")
    if recipe.base.TE_KEYS != config["te_keys"]:
        raise ValueError("strict TE definitions mismatch")
    expected_total = int(config["expected_total_features"])
    strict_checks = {
        "v96_runner_sha256": sha256_file(V96_PATH),
        "v96_config_sha256": config_sha,
        "strict_static_features": int(x_train.shape[1]),
        "strict_te_keys": len(recipe.base.TE_KEYS),
        "strict_te_smooths": list(config["smooths"]),
        "strict_total_features": expected_total,
        "outer_seed": OUTER_SEED,
        "inner_seed_base": int(config["inner_te_seed_base"]),
        "model_seed": int(config["model_seed"]),
        "train_id_sha256": id_sha256(train[config["id_column"]]),
        "test_id_sha256": id_sha256(test[config["id_column"]]),
        "no_test_prediction": True,
    }

    oof_a = np.full(len(train), np.nan, dtype=np.float64)
    oof_b = np.full(len(train), np.nan, dtype=np.float64)
    coverage = np.zeros(len(train), dtype=np.int8)
    rows: list[dict[str, Any]] = []
    resource_checks = [resource_guard(started, "AFTER_DATA_PREP")]
    folds = list(
        StratifiedKFold(
            n_splits=OUTER_FOLDS, shuffle=True, random_state=OUTER_SEED
        ).split(np.zeros(len(train)), y)
    )

    try:
        for fold, (fit_idx, valid_idx) in enumerate(folds, start=1):
            fold_started = time.monotonic()
            resource_checks.append(resource_guard(started, f"FOLD_{fold}_START"))
            inner = list(
                StratifiedKFold(
                    n_splits=int(config["n_inner_folds"]),
                    shuffle=True,
                    random_state=int(config["inner_te_seed_base"]) + fold,
                ).split(np.zeros(len(fit_idx)), y[fit_idx])
            )
            fit_te: list[np.ndarray] = []
            valid_te: list[np.ndarray] = []
            for key in recipe.base.TE_KEYS:
                fit_block, valid_block, _unused_test_block = source.strict_encode_key(
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
            x_fit = np.column_stack(
                [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
            )
            x_valid = np.column_stack(
                [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
            )
            if x_fit.shape[1] != expected_total or x_valid.shape[1] != expected_total:
                raise ValueError("strict feature count mismatch")
            del fit_te, valid_te, _unused_test_block
            resource_checks.append(resource_guard(started, f"FOLD_{fold}_AFTER_TE"))

            gam = make_gam_pipeline()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                gam.fit(train.iloc[fit_idx], y[fit_idx])
            convergence_messages = [
                str(item.message)
                for item in caught
                if issubclass(item.category, ConvergenceWarning)
            ]
            if convergence_messages:
                raise RuntimeError(f"GAM logistic did not converge: {convergence_messages}")
            gam_names = gam.named_steps["transform"].get_feature_names_out()
            if len(gam_names) != EXPECTED_GAM_FEATURES:
                raise ValueError(f"GAM feature count={len(gam_names)}, expected 39")
            margin_fit_unclipped = gam.decision_function(train.iloc[fit_idx])
            margin_valid_unclipped = gam.decision_function(train.iloc[valid_idx])
            margin_fit = np.clip(margin_fit_unclipped, -MARGIN_CAP, MARGIN_CAP)
            margin_valid = np.clip(margin_valid_unclipped, -MARGIN_CAP, MARGIN_CAP)
            if not np.isfinite(margin_fit).all() or not np.isfinite(margin_valid).all():
                raise ValueError("GAM margin contains NaN/Inf")
            resource_checks.append(resource_guard(started, f"FOLD_{fold}_AFTER_GAM"))

            params = dict(config["lightgbm_params"])
            if int(params["n_jobs"]) != 8:
                raise ValueError("LightGBM thread contract drift")
            model_a = lgb.LGBMClassifier(**params)
            a_started = time.monotonic()
            model_a.fit(
                x_fit,
                y[fit_idx],
                eval_set=[(x_valid, y[valid_idx])],
                eval_metric="auc",
                callbacks=[
                    lgb.early_stopping(int(config["early_stopping_rounds"]), verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            a_elapsed = time.monotonic() - a_started
            best_a = int(model_a.best_iteration_ or params["n_estimators"])
            pred_a = model_a.predict_proba(x_valid, num_iteration=best_a)[:, 1]
            auc_a = float(roc_auc_score(y[valid_idx], pred_a))
            eval_a = float(model_a.best_score_["valid_0"]["auc"])
            if not np.isclose(auc_a, eval_a, atol=1e-12, rtol=0.0):
                raise RuntimeError(f"A early-stop metric mismatch: {auc_a} vs {eval_a}")
            resource_checks.append(resource_guard(started, f"FOLD_{fold}_AFTER_A"))

            model_b = lgb.LGBMClassifier(**params)
            b_started = time.monotonic()
            model_b.fit(
                x_fit,
                y[fit_idx],
                init_score=margin_fit,
                eval_set=[(x_valid, y[valid_idx])],
                eval_init_score=[margin_valid],
                eval_metric="auc",
                callbacks=[
                    lgb.early_stopping(int(config["early_stopping_rounds"]), verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            b_elapsed = time.monotonic() - b_started
            best_b = int(model_b.best_iteration_ or params["n_estimators"])
            residual_valid = model_b.booster_.predict(
                x_valid, raw_score=True, num_iteration=best_b
            )
            pred_b_without_readd = model_b.predict_proba(
                x_valid, num_iteration=best_b
            )[:, 1]
            excluded_check = float(
                np.max(np.abs(expit(residual_valid) - pred_b_without_readd))
            )
            if excluded_check > 1e-12:
                raise RuntimeError(
                    "LightGBM raw residual exclusion self-check failed: "
                    f"max_abs={excluded_check}"
                )
            pred_b = expit(margin_valid + residual_valid)
            auc_b = float(roc_auc_score(y[valid_idx], pred_b))
            eval_b = float(model_b.best_score_["valid_0"]["auc"])
            if not np.isclose(auc_b, eval_b, atol=1e-12, rtol=0.0):
                raise RuntimeError(f"B early-stop metric mismatch: {auc_b} vs {eval_b}")
            resource_checks.append(resource_guard(started, f"FOLD_{fold}_AFTER_B"))

            if coverage[valid_idx].any():
                raise RuntimeError("outer validation coverage overlap")
            coverage[valid_idx] = 1
            oof_a[valid_idx] = pred_a
            oof_b[valid_idx] = pred_b
            row = {
                "fold": fold,
                "fit_rows": int(len(fit_idx)),
                "valid_rows": int(len(valid_idx)),
                "fit_id_sha256": id_sha256(train.iloc[fit_idx][config["id_column"]]),
                "valid_id_sha256": id_sha256(train.iloc[valid_idx][config["id_column"]]),
                "inner_seed": int(config["inner_te_seed_base"]) + fold,
                "gam_features": int(len(gam_names)),
                "gam_iterations": int(gam.named_steps["logistic"].n_iter_[0]),
                "gam_margin_fit_min": float(margin_fit.min()),
                "gam_margin_fit_max": float(margin_fit.max()),
                "gam_margin_valid_min": float(margin_valid.min()),
                "gam_margin_valid_max": float(margin_valid.max()),
                "gam_margin_fit_clip_count": int(
                    np.count_nonzero(margin_fit != margin_fit_unclipped)
                ),
                "gam_margin_valid_clip_count": int(
                    np.count_nonzero(margin_valid != margin_valid_unclipped)
                ),
                "auc_a": auc_a,
                "auc_b": auc_b,
                "delta_b_minus_a": auc_b - auc_a,
                "best_iteration_a": best_a,
                "best_iteration_b": best_b,
                "early_stop_auc_a": eval_a,
                "early_stop_auc_b": eval_b,
                "predict_proba_excludes_init_max_abs_error": excluded_check,
                "elapsed_a_seconds": float(a_elapsed),
                "elapsed_b_seconds": float(b_elapsed),
                "elapsed_fold_seconds": float(time.monotonic() - fold_started),
                "peak_rss_bytes": peak_rss_bytes(),
            }
            rows.append(row)
            partial = {
                "status": "RUNNING",
                "script_sha256": script_sha_at_start,
                "frozen_design": frozen_design(),
                "strict_checks": strict_checks,
                "folds": rows,
                "resource_checks": resource_checks,
            }
            write_evidence(partial)
            print(
                f"fold={fold}/5 A={auc_a:.12f} B={auc_b:.12f} "
                f"delta={auc_b-auc_a:+.12f} bestA={best_a} bestB={best_b} "
                f"elapsed={row['elapsed_fold_seconds']:.1f}s",
                flush=True,
            )
            del x_fit, x_valid, gam, model_a, model_b

        if not np.all(coverage == 1):
            raise RuntimeError("outer OOF coverage is not exactly once")
        if not np.isfinite(oof_a).all() or not np.isfinite(oof_b).all():
            raise RuntimeError("OOF contains NaN/Inf")
        pooled_a = float(roc_auc_score(y, oof_a))
        pooled_b = float(roc_auc_score(y, oof_b))
        pooled_delta = pooled_b - pooled_a
        wins = int(sum(row["delta_b_minus_a"] > 0.0 for row in rows))
        gate_pass = pooled_delta >= GATE_DELTA and wins >= GATE_WINS
        resource_checks.append(resource_guard(started, "FINAL"))
        if sha256_file(Path(__file__)) != script_sha_at_start:
            raise RuntimeError("probe script changed during the one-shot run")
        payload = {
            "status": "COMPLETE",
            "decision": "GO" if gate_pass else "NO-GO",
            "script_sha256": script_sha_at_start,
            "frozen_design": frozen_design(),
            "strict_checks": strict_checks,
            "folds": rows,
            "pooled_auc_a": pooled_a,
            "pooled_auc_b": pooled_b,
            "pooled_delta_b_minus_a": pooled_delta,
            "winning_folds": wins,
            "gate": {
                "minimum_delta": GATE_DELTA,
                "minimum_winning_folds": GATE_WINS,
                "delta_pass": pooled_delta >= GATE_DELTA,
                "wins_pass": wins >= GATE_WINS,
                "pass": gate_pass,
            },
            "elapsed_seconds": float(time.monotonic() - started),
            "peak_rss_bytes": peak_rss_bytes(),
            "resource_checks": resource_checks,
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "sklearn": sklearn.__version__,
                "lightgbm": lgb.__version__,
            },
            "artifacts": {
                "test_predictions_generated": False,
                "submission_generated": False,
                "oof_arrays_persisted": False,
            },
        }
        write_evidence(payload)
        return payload
    except Exception as error:
        failure = {
            "status": "FAILED",
            "error_type": type(error).__name__,
            "error": str(error),
            "script_sha256": script_sha_at_start,
            "frozen_design": frozen_design(),
            "strict_checks": strict_checks,
            "folds": rows,
            "elapsed_seconds": float(time.monotonic() - started),
            "peak_rss_bytes": peak_rss_bytes(),
            "resource_checks": resource_checks,
        }
        write_evidence(failure)
        raise


def frozen_design() -> dict[str, Any]:
    return {
        "experiment": "temporary_one_shot_5fold_matched_ab",
        "arm_a": "strict-v80, no init_score",
        "arm_b": "strict-v80 plus outer-fit frozen 39-column GAM init_score",
        "outer_folds": OUTER_FOLDS,
        "outer_seed": OUTER_SEED,
        "forbidden_seeds": [104729, 104743],
        "spline_columns": SPLINE_COLUMNS,
        "spline": {
            "n_knots": 5,
            "degree": 3,
            "knots": "quantile",
            "extrapolation": "linear",
            "include_bias": False,
        },
        "linear_columns": LINEAR_COLUMNS,
        "categorical_columns": CATEGORICAL_COLUMNS,
        "categorical_encoding": "full one-hot, no drop, handle_unknown=ignore",
        "expected_gam_features": EXPECTED_GAM_FEATURES,
        "interactions": [],
        "gam_te_features": [],
        "gam_income_exact_or_bins": [],
        "logistic": {
            "penalty": "l2",
            "C": 0.1,
            "solver": "lbfgs",
            "tol": 1e-8,
            "max_iter": 1000,
            "fit_intercept": True,
            "class_weight": None,
        },
        "margin_cap": MARGIN_CAP,
        "fit_contract": "all GAM transforms and labels fit only on outer-fit",
        "lightgbm_contract": (
            "B uses init_score=m_fit and eval_init_score=[m_valid]; prediction is "
            "expit(m_valid + booster raw residual)"
        ),
        "wall_budget_seconds": WALL_BUDGET_SECONDS,
        "cpu_threads": 8,
        "memory_budget_bytes": MEMORY_BUDGET_BYTES,
        "submission_budget": SUBMISSION_BUDGET,
        "gate_delta": GATE_DELTA,
        "gate_winning_folds": GATE_WINS,
        "no_grid_or_retry": True,
        "no_test_prediction": True,
    }


def audit_only() -> None:
    config = json.loads(V96_CONFIG_PATH.read_text(encoding="utf-8"))
    assert OUTER_FOLDS == 5 and OUTER_SEED == 42
    assert 104729 not in {OUTER_SEED, int(config["inner_te_seed_base"]), int(config["model_seed"])}
    assert 104743 not in {OUTER_SEED, int(config["inner_te_seed_base"]), int(config["model_seed"])}
    assert len(SPLINE_COLUMNS) == 3
    assert len(LINEAR_COLUMNS) == 4
    assert len(CATEGORICAL_COLUMNS) == 6
    assert EXPECTED_GAM_FEATURES == 39
    assert config["expected_static_features"] == 62
    assert config["expected_te_features"] == 51
    assert config["expected_total_features"] == 113
    assert config["lightgbm_params"]["n_jobs"] == 8
    assert config["submission_budget"] == 0
    print(json.dumps({"audit": "PASS", "frozen_design": frozen_design()}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if args.audit_only:
        audit_only()
        return
    result = run()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
