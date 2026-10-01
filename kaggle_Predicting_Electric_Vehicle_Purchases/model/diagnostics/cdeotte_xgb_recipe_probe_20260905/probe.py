#!/usr/bin/env python3
"""Seed42 五折三臂 XGBoost generator recipe 诊断。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import norm, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
DATA_DIR = PROJECT_DIR / "data"
START_MARKER = OUT_DIR / "RUN_STARTED.json"
EVIDENCE_PATH = OUT_DIR / "evidence.json"
V90_OOF_PATH = (
    PROJECT_DIR / "model/v90_v89_member_verify_budget_retry/oof_proba.npy"
)

EXPERIMENT_ID = "TEMP_CDEOTTE_XGB_RECIPE_3ARM_SEED42"
TARGET = "Will_Buy_EV"
POSITIVE = "Yes"
SEED = 42
N_FOLDS = 5
WALL_BUDGET_SECONDS = 1800.0
MEMORY_BUDGET_BYTES = 16 * 1024**3
PUBLIC_NOTEBOOK_SHA256 = (
    "08cc650a222b62385a18226871a4481c3050f790d01f7006c6562240c815ae96"
)
GATE_DELTA = 0.0001
GATE_WINS = 4
MIN_DIVERSITY_AUC = 0.9452
META_GATE_WINS = 5
META_WEIGHT_GRID = np.arange(0.0, 0.5000001, 0.025)

PARAMS = {
    "n_estimators": 3000,
    "learning_rate": 0.05,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "tree_method": "hist",
    "device": "cpu",
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "early_stopping_rounds": 100,
    "random_state": SEED,
    "n_jobs": 8,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


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


def make_features(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.drop(
        columns=[column for column in ("id", TARGET) if column in frame],
    ).copy()
    home = frame["Home_Charging_Possible"].eq("Yes").astype(np.int8)
    subsidy = frame["Subsidy_Available"].eq("Yes").astype(np.int8)
    output["worry_score"] = (
        frame["Daily_Commute_km"]
        - 5.0 * frame["Charging_Stations_Near_Home"]
        - 5.0 * frame["Charging_Stations_Near_Work"]
        - 150.0 * home
    )
    output["chargers_total"] = (
        frame["Charging_Stations_Near_Home"]
        + frame["Charging_Stations_Near_Work"]
    )
    output["income_x_subsidy"] = (
        frame["Annual_Income_USD"] / 100_000.0 * subsidy
    )
    output["concern_x_subsidy"] = (
        frame["Environmental_Concern_Level"] * subsidy
    )
    return output


def encode_joint_categories(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    joint = make_features(
        pd.concat([train.drop(columns=[TARGET]), test], ignore_index=True)
    )
    for column in joint.select_dtypes(include="object").columns:
        joint[column] = joint[column].astype("category").cat.codes
    return (
        joint.iloc[: len(train)].reset_index(drop=True),
        joint.iloc[len(train) :].reset_index(drop=True),
    )


def recipe_score(frame: pd.DataFrame) -> np.ndarray:
    score = (
        1.2 * frame["Annual_Income_USD"].to_numpy(np.float64) / 100_000.0
        + 0.6 * frame["Environmental_Concern_Level"].to_numpy(np.float64)
        + 2.0 * frame["Subsidy_Available"].eq("Yes").to_numpy(np.float64)
        - frame["Range_Anxiety_Level"].eq("Medium").to_numpy(np.float64)
        - 3.0 * frame["Range_Anxiety_Level"].eq("High").to_numpy(np.float64)
    )
    if score.shape != (len(frame),) or not np.isfinite(score).all():
        raise ValueError("recipe score 非有限或 shape 漂移")
    return score


def recipe_margin(frame: pd.DataFrame) -> np.ndarray:
    probability = np.clip(norm.cdf(recipe_score(frame) - 5.5), 1e-6, 1 - 1e-6)
    margin = np.log(probability / (1.0 - probability))
    if not np.isfinite(margin).all():
        raise ValueError("recipe margin 非有限")
    return margin


def fit_mid_ecdf(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("ECDF fit 输入非法")
    return np.sort(values)


def transform_mid_ecdf(state: np.ndarray, values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return (
        np.searchsorted(state, values, side="left")
        + np.searchsorted(state, values, side="right")
    ) / (2.0 * len(state))


def nested_meta_blend(
    y: np.ndarray, core_oof: np.ndarray, candidate_oof: np.ndarray
) -> dict[str, Any]:
    blend = np.zeros(len(y), dtype=np.float64)
    baseline = np.zeros(len(y), dtype=np.float64)
    rows: list[dict[str, Any]] = []
    splits = StratifiedKFold(5, shuffle=True, random_state=42).split(
        np.zeros(len(y)), y
    )
    for fold, (fit_idx, hold_idx) in enumerate(splits, start=1):
        core_state = fit_mid_ecdf(core_oof[fit_idx])
        candidate_state = fit_mid_ecdf(candidate_oof[fit_idx])
        core_fit = transform_mid_ecdf(core_state, core_oof[fit_idx])
        candidate_fit = transform_mid_ecdf(candidate_state, candidate_oof[fit_idx])
        core_hold = transform_mid_ecdf(core_state, core_oof[hold_idx])
        candidate_hold = transform_mid_ecdf(
            candidate_state, candidate_oof[hold_idx]
        )
        scores = [
            float(
                roc_auc_score(
                    y[fit_idx], (1.0 - weight) * core_fit + weight * candidate_fit
                )
            )
            for weight in META_WEIGHT_GRID
        ]
        best_index = max(
            range(len(META_WEIGHT_GRID)),
            key=lambda index: (scores[index], -META_WEIGHT_GRID[index]),
        )
        weight = float(META_WEIGHT_GRID[best_index])
        baseline[hold_idx] = core_hold
        blend[hold_idx] = (1.0 - weight) * core_hold + weight * candidate_hold
        baseline_auc = float(roc_auc_score(y[hold_idx], baseline[hold_idx]))
        blend_auc = float(roc_auc_score(y[hold_idx], blend[hold_idx]))
        rows.append(
            {
                "fold": fold,
                "selected_candidate_weight": weight,
                "meta_train_auc": scores[best_index],
                "holdout_baseline_auc": baseline_auc,
                "holdout_blend_auc": blend_auc,
                "holdout_delta": blend_auc - baseline_auc,
            }
        )
    baseline_auc = float(roc_auc_score(y, baseline))
    blend_auc = float(roc_auc_score(y, blend))
    return {
        "baseline_auc": baseline_auc,
        "blend_auc": blend_auc,
        "delta": blend_auc - baseline_auc,
        "positive_folds": sum(row["holdout_delta"] > 0.0 for row in rows),
        "rows": rows,
    }


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
    checks = [resource_guard(started, "START")]
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    y = train[TARGET].eq(POSITIVE).to_numpy(np.int8)
    x_train, _ = encode_joint_categories(train, test)
    score = recipe_score(train)
    margin = recipe_margin(train)
    x_feature = x_train.copy()
    x_feature["recipe_score"] = score
    arms = {
        "baseline": x_train,
        "base_margin": x_train,
        "recipe_feature": x_feature,
    }
    oof = {name: np.full(len(train), np.nan) for name in arms}
    fold_rows: list[dict[str, Any]] = []
    splits = list(
        StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(
            x_train, y
        )
    )
    for fold, (fit_idx, valid_idx) in enumerate(splits, start=1):
        row: dict[str, Any] = {"fold": fold, "valid_rows": len(valid_idx)}
        for arm, features in arms.items():
            model = xgb.XGBClassifier(**PARAMS)
            if arm == "base_margin":
                model.fit(
                    features.iloc[fit_idx],
                    y[fit_idx],
                    eval_set=[(features.iloc[valid_idx], y[valid_idx])],
                    base_margin=margin[fit_idx],
                    base_margin_eval_set=[margin[valid_idx]],
                    verbose=False,
                )
                prediction = model.predict_proba(
                    features.iloc[valid_idx], base_margin=margin[valid_idx]
                )[:, 1]
            else:
                model.fit(
                    features.iloc[fit_idx],
                    y[fit_idx],
                    eval_set=[(features.iloc[valid_idx], y[valid_idx])],
                    verbose=False,
                )
                prediction = model.predict_proba(features.iloc[valid_idx])[:, 1]
            oof[arm][valid_idx] = prediction
            row[f"{arm}_auc"] = float(roc_auc_score(y[valid_idx], prediction))
            row[f"{arm}_best_iteration"] = int(model.best_iteration)
            checks.append(resource_guard(started, f"FOLD_{fold}_{arm}"))
        row["base_margin_delta"] = row["base_margin_auc"] - row["baseline_auc"]
        fold_rows.append(row)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)

    if any(not np.isfinite(prediction).all() for prediction in oof.values()):
        raise RuntimeError("OOF coverage 不完整")
    auc = {name: float(roc_auc_score(y, prediction)) for name, prediction in oof.items()}
    family = np.mean(np.stack(list(oof.values())), axis=0)
    family_auc = float(roc_auc_score(y, family))
    base_margin_delta = auc["base_margin"] - auc["baseline"]
    base_margin_wins = sum(row["base_margin_delta"] > 0.0 for row in fold_rows)
    v90 = np.load(V90_OOF_PATH, allow_pickle=False)
    meta = nested_meta_blend(y, v90, family)
    strength_go = base_margin_delta >= GATE_DELTA and base_margin_wins >= GATE_WINS
    diversity_go = (
        family_auc >= MIN_DIVERSITY_AUC
        and meta["delta"] >= GATE_DELTA
        and meta["positive_folds"] == META_GATE_WINS
    )
    checks.append(resource_guard(started, "COMPLETE"))
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "counts_toward_c01": False,
        "public_source": {
            "ref": "cdeotte/fable-5-1-xgb-starter",
            "url": "https://www.kaggle.com/code/cdeotte/fable-5-1-xgb-starter",
            "notebook_sha256": PUBLIC_NOTEBOOK_SHA256,
            "public_predictions_used": False,
            "leaderboard_used_for_selection": False,
        },
        "protocol": {
            "folds": N_FOLDS,
            "seed": SEED,
            "params": PARAMS,
            "category_encoding": "joint train+test labels absent",
            "test_predictions_generated": False,
            "oof_arrays_saved": False,
            "submission_generated": False,
            "base_margin_gate": {
                "minimum_delta": GATE_DELTA,
                "minimum_positive_folds": GATE_WINS,
            },
            "diversity_gate": {
                "minimum_family_auc": MIN_DIVERSITY_AUC,
                "minimum_nested_meta_delta": GATE_DELTA,
                "required_positive_meta_folds": META_GATE_WINS,
            },
        },
        "folds": fold_rows,
        "aggregate": {
            "auc": auc,
            "family_equal_auc": family_auc,
            "base_margin_delta": base_margin_delta,
            "base_margin_positive_folds": base_margin_wins,
            "spearman_vs_v90": {
                name: float(spearmanr(prediction, v90).statistic)
                for name, prediction in oof.items()
            }
            | {"family_equal": float(spearmanr(family, v90).statistic)},
            "nested_v90_family_blend": meta,
            "strength_gate_passed": strength_go,
            "diversity_gate_passed": diversity_go,
            "decision": (
                "FORMAL_40F_GO" if strength_go or diversity_go else "NO_GO"
            ),
        },
        "source_sha256": {
            "probe.py": sha256_file(Path(__file__)),
            "train.csv": sha256_file(DATA_DIR / "train.csv"),
            "test.csv": sha256_file(DATA_DIR / "test.csv"),
            "v90_oof": sha256_file(V90_OOF_PATH),
        },
        "environment": {
            "python": platform.python_version(),
            "xgboost": xgb.__version__,
            "platform": platform.platform(),
        },
        "resource_checks": checks,
        "elapsed_seconds": checks[-1]["elapsed_seconds"],
        "peak_rss_bytes": checks[-1]["peak_rss_bytes"],
    }
    atomic_json(EVIDENCE_PATH, payload)
    print(json.dumps(payload["aggregate"], ensure_ascii=False, sort_keys=True))
    return payload


def audit() -> dict[str, Any]:
    frame = pd.DataFrame(
        {
            "Annual_Income_USD": [100_000.0, 50_000.0],
            "Environmental_Concern_Level": [5.0, 1.0],
            "Subsidy_Available": ["Yes", "No"],
            "Range_Anxiety_Level": ["Low", "High"],
        }
    )
    expected = np.array([6.2, -1.8])
    score = recipe_score(frame)
    if not np.array_equal(score, expected):
        raise AssertionError("recipe formula audit 失败")
    return {
        "status": "AUDIT_OK_NO_TRAINING",
        "experiment_id": EXPERIMENT_ID,
        "recipe_score_exact": True,
        "base_margin_finite": bool(np.isfinite(recipe_margin(frame)).all()),
        "weight_grid": META_WEIGHT_GRID.tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "run"), default="audit")
    args = parser.parse_args()
    result = run() if args.mode == "run" else audit()
    if args.mode == "audit":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
