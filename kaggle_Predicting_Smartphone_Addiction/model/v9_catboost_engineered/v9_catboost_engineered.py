# -*- coding: utf-8 -*-
"""v9：CatBoost 增强特征版。

在 v3 的双重表示（连续值 + 原始字段精确值字符串）上加入轻量特征工程：
- 屏幕时间预算相关：component_sum / other_screen / 可观测组件数
- 比例特征：social/gaming/work 对总时长占比
- 比例相关的缺失安全分母：避免 0 或 NaN 引发异常
- 强化数值表达：多维 log1p/比率特征，增强非线性关系可分解性
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool, __version__ as catboost_version
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
TARGET = "addicted_label"
ID_COL = "id"
COMPONENT_COLS = ["social_media_hours", "gaming_hours", "work_study_hours"]
RAW_CAT_COLS = ["gender", "stress_level", "academic_work_impact"]

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
V3_RESULTS = OUT_DIR.parent / "v3_dual_catboost" / "cv_results.json"

CAT_PARAMS = {
    "iterations": 2200,
    "learning_rate": 0.045,
    "depth": 8,
    "l2_leaf_reg": 5.0,
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "random_seed": SEED,
    "one_hot_max_size": 4,
    "max_ctr_complexity": 2,
    "od_type": "Iter",
    "od_wait": 220,
    "allow_writing_files": False,
    "thread_count": -1,
    "verbose": 250,
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if TARGET not in train or TARGET in test:
        raise ValueError("训练集/测试集目标列不符合预期")
    if train[ID_COL].duplicated().any() or test[ID_COL].duplicated().any():
        raise ValueError("发现重复 id")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission.csv 的 id 顺序与 test.csv 不一致")
    return train, test, sample


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace(0.0, np.nan)
    return num / den


def build_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    """返回训练特征、测试特征、分类特征索引列表、字段列表。"""
    raw_cols = [c for c in test.columns if c != ID_COL]
    numeric_cols = [c for c in raw_cols if pd.api.types.is_numeric_dtype(train[c])]

    x_train = train[numeric_cols].copy()
    x_test = test[numeric_cols].copy()

    # 时间预算关系特征
    for source, output in ((train, x_train), (test, x_test)):
        parts = source[COMPONENT_COLS]
        output["component_sum"] = parts.fillna(0.0).sum(axis=1)
        output["other_screen"] = source["daily_screen_time_hours"] - output["component_sum"]
        output["n_components_observed"] = parts.notna().sum(axis=1).astype(np.float32)
        output["component_sum_is_zero"] = output["component_sum"].eq(0).astype(np.int8)

    # 比例/缩放特征
    for source, output in ((train, x_train), (test, x_test)):
        denom = source["daily_screen_time_hours"]
        output["social_share"] = _safe_ratio(source["social_media_hours"], denom)
        output["gaming_share"] = _safe_ratio(source["gaming_hours"], denom)
        output["work_share"] = _safe_ratio(source["work_study_hours"], denom)
        output["other_share"] = _safe_ratio(output["other_screen"], denom)
        output["weekend_share"] = _safe_ratio(source["weekend_screen_time"], denom)
        output["open_per_screen"] = _safe_ratio(source["app_opens_per_day"], source["daily_screen_time_hours"])
        output["notif_per_screen"] = _safe_ratio(source["notifications_per_day"], source["daily_screen_time_hours"])
        output["sleep_pressure"] = source["daily_screen_time_hours"] - source["sleep_hours"] * 7.5
        output["social_minus_gaming"] = source["social_media_hours"] - source["gaming_hours"]

    # 非负/对数变体（保留原始值）
    log_features = [
        "daily_screen_time_hours",
        "social_media_hours",
        "gaming_hours",
        "work_study_hours",
        "weekend_screen_time",
        "notifications_per_day",
        "app_opens_per_day",
        "sleep_hours",
        "component_sum",
        "other_screen",
    ]
    for col in log_features:
        for source, output in ((train, x_train), (test, x_test)):
            output[f"log1p_{col}"] = np.log1p(output[col].clip(lower=0.0))

    # 类别列保留字符串精确值通道
    categorical_cols: list[str] = []
    for col in RAW_CAT_COLS:
        key = f"key_{col}"
        x_train[key] = train[col].where(train[col].notna(), "__NA__").astype(str)
        x_test[key] = test[col].where(test[col].notna(), "__NA__").astype(str)
        categorical_cols.append(key)

    if list(x_train.columns) != list(x_test.columns):
        raise ValueError("训练集与测试集特征列不一致")
    return x_train, x_test, categorical_cols, raw_cols


def validate_submission(
    submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame
) -> None:
    if submission.shape != sample.shape:
        raise ValueError(f"提交 shape 错误：{submission.shape} != {sample.shape}")
    if list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError(f"提交列名错误：{submission.columns.tolist()}")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与测试集不一致")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率包含非法值")


def main() -> None:
    start = time.time()
    train, test, sample = load_data()
    x_train, x_test, cat_features, raw_cols = build_features(train, test)
    y = train[TARGET].to_numpy(dtype=np.int8)

    print(
        f"train={train.shape}, test={test.shape}, features={x_train.shape[1]}, "
        f"cat={len(cat_features)}"
    )

    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    test_pool = Pool(x_test, cat_features=cat_features)

    for fold, (train_idx, valid_idx) in enumerate(splitter.split(x_train, y), start=1):
        fold_start = time.time()
        train_pool = Pool(
            x_train.iloc[train_idx],
            y[train_idx],
            cat_features=cat_features,
        )
        valid_pool = Pool(
            x_train.iloc[valid_idx],
            y[valid_idx],
            cat_features=cat_features,
        )

        model = CatBoostClassifier(**CAT_PARAMS)
        model.fit(train_pool, eval_set=valid_pool, use_best_model=True)

        valid_pred = model.predict_proba(valid_pool)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(test_pool)[:, 1] / N_FOLDS
        fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(fold_auc)
        best_iterations.append(int(model.get_best_iteration() + 1))

        print(
            f"fold={fold} auc={fold_auc:.6f} best_iteration={best_iterations[-1]} "
            f"elapsed={time.time()-fold_start:.1f}s"
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    v3 = json.loads(V3_RESULTS.read_text(encoding="utf-8"))
    v3_fold_scores = np.asarray(v3["fold_auc"], dtype=float)
    fold_deltas = np.asarray(fold_scores, dtype=float) - v3_fold_scores
    folds_won = int((fold_deltas > 0).sum())

    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    results = {
        "competition": "playground-series-s6e8",
        "model": "CatBoost engineered ratios + log transforms + dual-value features",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "raw_columns": raw_cols,
        "feature_count": int(x_train.shape[1]),
        "categorical_features": cat_features,
        "catboost_version": catboost_version,
        "fold_auc": [float(x) for x in fold_scores],
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iterations,
        "oof_auc": oof_auc,
        "v3_oof_auc": float(v3["oof_auc"]),
        "oof_delta_vs_v3": oof_auc - float(v3["oof_auc"]),
        "fold_delta_vs_v3": fold_deltas.tolist(),
        "folds_won_vs_v3": folds_won,
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "params": CAT_PARAMS,
    }
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
