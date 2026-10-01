#!/usr/bin/env python3
"""v98 加性 GAM 与单一主导联合键 GAM 的 seed42 五折诊断。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
TRAIN_PATH = PROJECT_DIR / "data/train.csv"
V98_PROBE_PATH = (
    PROJECT_DIR / "model/v98_supervised_gam_init_score_40f/probe_archive/probe.py"
)
START_MARKER = OUT_DIR / "RUN_STARTED.json"
EVIDENCE_PATH = OUT_DIR / "evidence.json"
EXPERIMENT_ID = "TEMP_GAM_DOMINANT_JOINT_5FOLD_SEED42"
TARGET = "Will_Buy_EV"
POSITIVE = "Yes"
JOINT_COLUMN = "_dominant_joint"
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
JOINT_PARTS = [
    "Environmental_Concern_Level",
    "Subsidy_Available",
    "Range_Anxiety_Level",
    "Home_Charging_Possible",
]
BASE_FEATURES = 39
JOINT_LEVELS = 50
JOINT_FEATURES = BASE_FEATURES + JOINT_LEVELS
GATE_DELTA = 0.0001
GATE_WINS = 4
WALL_BUDGET_SECONDS = 600.0
MEMORY_BUDGET_BYTES = 8 * 1024**3


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


def add_dominant_joint(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(JOINT_PARTS).difference(frame.columns)
    if missing:
        raise ValueError(f"联合键缺列：{sorted(missing)}")
    output = frame.copy()
    output[JOINT_COLUMN] = output[JOINT_PARTS].astype(str).agg("|".join, axis=1)
    return output


def make_pipeline(include_joint: bool) -> Pipeline:
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
    categorical_columns = CATEGORICAL_COLUMNS + ([JOINT_COLUMN] if include_joint else [])
    transform = ColumnTransformer(
        [
            ("spline", spline, SPLINE_COLUMNS),
            (
                "linear",
                StandardScaler(with_mean=True, with_std=True),
                LINEAR_COLUMNS,
            ),
            (
                "categorical",
                OneHotEncoder(
                    categories="auto",
                    drop=None,
                    sparse_output=False,
                    dtype=np.float64,
                    handle_unknown="ignore",
                ),
                categorical_columns,
            ),
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
        verbose=0,
        warm_start=False,
        n_jobs=None,
        l1_ratio=None,
    )
    return Pipeline([("transform", transform), ("logistic", logistic)])


def fit_predict(
    pipeline: Pipeline,
    fit_frame: pd.DataFrame,
    fit_y: np.ndarray,
    valid_frame: pd.DataFrame,
    expected_features: int,
) -> tuple[np.ndarray, int, int]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pipeline.fit(fit_frame, fit_y)
    convergence = [
        str(item.message)
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
    ]
    if convergence:
        raise RuntimeError(f"Logistic 未收敛：{convergence}")
    feature_count = len(pipeline.named_steps["transform"].get_feature_names_out())
    if feature_count != expected_features:
        raise ValueError(f"GAM 特征数 {feature_count} != {expected_features}")
    prediction = pipeline.predict_proba(valid_frame)[:, 1]
    if not np.isfinite(prediction).all():
        raise ValueError("GAM prediction 非有限")
    iterations = int(pipeline.named_steps["logistic"].n_iter_[0])
    return prediction, feature_count, iterations


def frozen_design() -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "outer_folds": 5,
        "outer_seed": 42,
        "arm_a": "v98 additive 39-column GAM",
        "arm_b": "arm A plus one 50-level dominant joint categorical one-hot",
        "joint_parts": JOINT_PARTS,
        "joint_levels": JOINT_LEVELS,
        "base_features": BASE_FEATURES,
        "joint_features": JOINT_FEATURES,
        "logistic_C": 0.1,
        "gate_delta": GATE_DELTA,
        "gate_wins": GATE_WINS,
        "wall_budget_seconds": WALL_BUDGET_SECONDS,
        "memory_budget_bytes": MEMORY_BUDGET_BYTES,
        "submission_budget": 0,
        "test_read": False,
        "oof_arrays_saved": False,
        "no_grid_or_retry": True,
    }


def audit() -> dict[str, Any]:
    frame = pd.DataFrame(
        {
            "Environmental_Concern_Level": [1.0, 5.0],
            "Subsidy_Available": ["No", "Yes"],
            "Range_Anxiety_Level": ["High", "Low"],
            "Home_Charging_Possible": ["No", "Yes"],
        }
    )
    keys = add_dominant_joint(frame)[JOINT_COLUMN].tolist()
    if keys != ["1.0|No|High|No", "5.0|Yes|Low|Yes"]:
        raise AssertionError("联合键公式漂移")
    return {"status": "AUDIT_OK_NO_TRAINING", "frozen_design": frozen_design()}


def run() -> dict[str, Any]:
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump(
                {"status": "RUN_STARTED_ONE_SHOT", "pid": os.getpid()},
                handle,
                ensure_ascii=False,
                indent=2,
            )
    except FileExistsError as error:
        raise RuntimeError("one-shot marker 已存在，拒绝重复运行") from error
    started = time.monotonic()
    runner_sha = sha256_file(Path(__file__))
    checks = [resource_guard(started, "START")]
    train = pd.read_csv(TRAIN_PATH)
    y = train[TARGET].eq(POSITIVE).to_numpy(np.int8)
    frame = add_dominant_joint(train.drop(columns=[TARGET]))
    if frame[JOINT_COLUMN].nunique() != JOINT_LEVELS:
        raise ValueError("联合键完整数据水平数漂移")
    oof_a = np.full(len(train), np.nan, dtype=np.float64)
    oof_b = np.full(len(train), np.nan, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    splitter = StratifiedKFold(5, shuffle=True, random_state=42)
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(frame, y), start=1):
        pred_a, count_a, iter_a = fit_predict(
            make_pipeline(False),
            frame.iloc[fit_idx],
            y[fit_idx],
            frame.iloc[valid_idx],
            BASE_FEATURES,
        )
        pred_b, count_b, iter_b = fit_predict(
            make_pipeline(True),
            frame.iloc[fit_idx],
            y[fit_idx],
            frame.iloc[valid_idx],
            JOINT_FEATURES,
        )
        oof_a[valid_idx] = pred_a
        oof_b[valid_idx] = pred_b
        auc_a = float(roc_auc_score(y[valid_idx], pred_a))
        auc_b = float(roc_auc_score(y[valid_idx], pred_b))
        row = {
            "fold": fold,
            "auc_a": auc_a,
            "auc_b": auc_b,
            "delta_b_minus_a": auc_b - auc_a,
            "features_a": count_a,
            "features_b": count_b,
            "iterations_a": iter_a,
            "iterations_b": iter_b,
        }
        rows.append(row)
        checks.append(resource_guard(started, f"FOLD_{fold}"))
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
    if not np.isfinite(oof_a).all() or not np.isfinite(oof_b).all():
        raise RuntimeError("OOF 覆盖不完整")
    auc_a = float(roc_auc_score(y, oof_a))
    auc_b = float(roc_auc_score(y, oof_b))
    delta = auc_b - auc_a
    wins = sum(row["delta_b_minus_a"] > 0.0 for row in rows)
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
            "stage2_gate_passed": gate,
            "decision": "STAGE2_GO" if gate else "NO_GO",
        },
        "source_sha256": {
            "probe.py": runner_sha,
            "train.csv": sha256_file(TRAIN_PATH),
            "v98_probe.py": sha256_file(V98_PROBE_PATH),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "sklearn": sklearn.__version__,
        },
        "elapsed_seconds": checks[-1]["elapsed_seconds"],
        "peak_rss_bytes": checks[-1]["peak_rss_bytes"],
        "resource_checks": checks,
    }
    atomic_json(EVIDENCE_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "run"), default="audit")
    args = parser.parse_args()
    payload = run() if args.mode == "run" else audit()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
