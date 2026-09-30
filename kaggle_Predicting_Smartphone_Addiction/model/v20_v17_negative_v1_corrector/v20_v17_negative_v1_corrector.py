#!/usr/bin/env python3
"""v20: 对当前 v17 增加一个固定的小幅负向低容量校正项。

论坛与本地相关性审计均表明：大量相似强模型只会重复同一误差，而弱但不同的
模型可作为负向误差校正。这里不拟合二层模型，也不在全量模型池上优化权重；
仅验证预先锁定的 -0.075 v1 方向：1.075 * v17 - 0.075 * v1。
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "model"
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "addicted_label"
ID_COL = "id"
SEED = 42
N_FOLDS = 5
CORRECTOR_WEIGHT = -0.075
V17_WEIGHT = 1.0 - CORRECTOR_WEIGHT
V17_V8_WEIGHT = 0.87
V17_XGB_WEIGHT = 0.13
V8_FIXED_WEIGHTS = {
    "v2": 0.056,
    "v6": 0.2832,
    "v7": 0.6608,
}


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return (rankdata(values, method="average") - 0.5) / len(values)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fold_scores(y: np.ndarray, pred: np.ndarray, folds) -> list[float]:
    return [float(roc_auc_score(y[va], pred[va])) for _, va in folds]


def missing_pattern(frame: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    mask = frame[feature_cols].isna().to_numpy(np.uint16)
    powers = (1 << np.arange(len(feature_cols), dtype=np.uint16)).reshape(-1, 1)
    return (mask @ powers).ravel().astype(np.int32)


def density_ratio_weights(
    train_pattern: np.ndarray, test_pattern: np.ndarray, alpha: float
) -> np.ndarray:
    n_patterns = 1 << 12
    train_count = np.bincount(train_pattern, minlength=n_patterns).astype(float)
    test_count = np.bincount(test_pattern, minlength=n_patterns).astype(float)
    p_train = (train_count + alpha) / (len(train_pattern) + alpha * n_patterns)
    p_test = (test_count + alpha) / (len(test_pattern) + alpha * n_patterns)
    ratio = p_test / p_train
    weights = ratio[train_pattern]
    return weights / weights.mean()


def validate_submission(frame: pd.DataFrame, test: pd.DataFrame) -> None:
    if frame.shape != (len(test), 2) or list(frame.columns) != [ID_COL, TARGET]:
        raise ValueError("提交 shape/字段不符合比赛要求")
    if not frame[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 顺序与 test.csv 不一致")
    pred = frame[TARGET].to_numpy(float)
    if not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
        raise ValueError("提交概率含 NaN/inf 或越界")


def main() -> None:
    started = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    y = train[TARGET].to_numpy(np.int8)
    feature_cols = [c for c in test.columns if c != ID_COL]
    folds = list(
        StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(
            np.zeros(len(y)), y
        )
    )

    paths = {
        "v1_oof": MODEL_DIR / "v1_baseline_lgbm" / "oof_proba.npy",
        "v1_test": MODEL_DIR / "v1_baseline_lgbm" / "test_proba.npy",
        "v2_oof": MODEL_DIR / "v2_budget_lgbm" / "oof_proba.npy",
        "v6_oof": MODEL_DIR / "v6_highres_lgbm" / "oof_proba.npy",
        "v7_oof": MODEL_DIR / "v7_catboost_bagging" / "oof_proba.npy",
        "v13_xgb_oof": MODEL_DIR / "v13_fe_single_compare" / "xgb_oof_proba.npy",
        "v17_submission": (
            MODEL_DIR
            / "v17_targeted_pair_v13xgb_13pct_v8_87pct"
            / "submission.csv"
        ),
    }
    arrays = {
        name: np.load(path).astype(np.float64)
        for name, path in paths.items()
        if path.suffix == ".npy"
    }
    for name, pred in arrays.items():
        if pred.shape != (len(train),) or not np.isfinite(pred).all():
            if name == "v1_test" and pred.shape == (len(test),):
                continue
            raise ValueError(f"{name} 形状或数值非法: {pred.shape}")

    fixed_v8_oof = sum(
        V8_FIXED_WEIGHTS[name] * percentile_rank(arrays[f"{name}_oof"])
        for name in V8_FIXED_WEIGHTS
    )
    fixed_v17_oof = (
        V17_V8_WEIGHT * fixed_v8_oof
        + V17_XGB_WEIGHT * arrays["v13_xgb_oof"]
    )
    corrected_oof = (
        V17_WEIGHT * fixed_v17_oof
        + CORRECTOR_WEIGHT * arrays["v1_oof"]
    )

    base_auc = float(roc_auc_score(y, fixed_v17_oof))
    corrected_auc = float(roc_auc_score(y, corrected_oof))
    base_folds = fold_scores(y, fixed_v17_oof, folds)
    corrected_folds = fold_scores(y, corrected_oof, folds)
    fold_delta = np.asarray(corrected_folds) - np.asarray(base_folds)

    train_pattern = missing_pattern(train, feature_cols)
    test_pattern = missing_pattern(test, feature_cols)
    transfer_checks = {}
    for alpha in (1.0, 10.0, 100.0):
        weights = density_ratio_weights(train_pattern, test_pattern, alpha)
        base_weighted = float(
            roc_auc_score(y, fixed_v17_oof, sample_weight=weights)
        )
        corrected_weighted = float(
            roc_auc_score(y, corrected_oof, sample_weight=weights)
        )
        ess = float(weights.sum() ** 2 / np.square(weights).sum())
        transfer_checks[str(int(alpha))] = {
            "base_auc": base_weighted,
            "corrected_auc": corrected_weighted,
            "delta": corrected_weighted - base_weighted,
            "effective_sample_size": ess,
        }

    v17_sub = pd.read_csv(paths["v17_submission"])
    if not v17_sub[ID_COL].equals(test[ID_COL]):
        raise ValueError("v17 归档提交与 test id 未对齐")
    corrected_test_raw = (
        V17_WEIGHT * v17_sub[TARGET].to_numpy(float)
        + CORRECTOR_WEIGHT * arrays["v1_test"]
    )
    # AUC 只依赖排序；全局百分位化消除极少数负值并避免 clipping 产生并列。
    corrected_test = percentile_rank(corrected_test_raw)
    submission = pd.DataFrame({ID_COL: test[ID_COL], TARGET: corrected_test})
    validate_submission(submission, test)
    submission_path = OUT_DIR / "submission.csv"
    submission.to_csv(submission_path, index=False)
    np.save(OUT_DIR / "oof_proba.npy", corrected_oof)
    np.save(OUT_DIR / "test_proba.npy", corrected_test)

    result = {
        "experiment": "v20_v17_negative_v1_corrector",
        "competition": "playground-series-s6e8",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "formula": "1.075*v17 - 0.075*v1, then percentile-rank test scores",
        "selection_policy": (
            "fixed conservative corrector; no meta-model and no full-pool weight fit"
        ),
        "deploy_aligned_oof": {
            "v8_fixed_weights": V8_FIXED_WEIGHTS,
            "v17_formula": "0.87*v8_fixed_rank + 0.13*v13_xgb_probability",
            "base_auc": base_auc,
            "corrected_auc": corrected_auc,
            "delta": corrected_auc - base_auc,
            "base_fold_auc": base_folds,
            "corrected_fold_auc": corrected_folds,
            "fold_delta": fold_delta.tolist(),
            "folds_won": int((fold_delta > 0).sum()),
        },
        "transfer_validation": {
            "method": "importance-weighted AUC by 12-bit train/test missing pattern",
            "laplace_alpha": transfer_checks,
        },
        "diversity": {
            "spearman_v1_vs_fixed_v17": float(
                spearmanr(arrays["v1_oof"], fixed_v17_oof).statistic
            )
        },
        "prediction_diagnostics": {
            "raw_test_min_before_rank": float(corrected_test_raw.min()),
            "raw_test_max_before_rank": float(corrected_test_raw.max()),
            "raw_test_negative_count": int((corrected_test_raw < 0).sum()),
            "submission_unique_predictions": int(submission[TARGET].nunique()),
        },
        "outputs": {
            "submission": submission_path.name,
            "oof": "oof_proba.npy",
            "test": "test_proba.npy",
        },
        "source_sha256": {name: sha256(path) for name, path in paths.items()},
        "runtime_seconds": float(time.time() - started),
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
