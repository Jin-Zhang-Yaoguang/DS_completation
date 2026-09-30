# -*- coding: utf-8 -*-
"""v11：XGBoost 工程特征单模。

特征：
- 继承 v9 的预算/比例/log 特征思路
- 类别特征 one-hot（与 LightGBM/CatBoost 保持一致的数据来源）
- 对缺失值仅做每折训练内统计量填充（防泄漏）
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
TARGET = "addicted_label"
ID_COL = "id"
COMPONENT_COLS = ["social_media_hours", "gaming_hours", "work_study_hours"]
CAT_COLS = ["gender", "stress_level", "academic_work_impact"]

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
V7_RESULTS = OUT_DIR.parent / "v7_catboost_bagging" / "cv_results.json"

XGB_PARAMS = {
    "n_estimators": 1600,
    "learning_rate": 0.05,
    "max_depth": 6,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "colsample_bylevel": 0.9,
    "min_child_weight": 20.0,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "gamma": 0.0,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "tree_method": "hist",
    "max_bin": 256,
    "predictor": "cpu_predictor",
    "verbosity": 0,
    "n_jobs": -1,
    "seed": SEED,
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


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0.0, np.nan)


def build_features(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_cols = [c for c in test.columns if c != ID_COL]
    base_numeric = [c for c in raw_cols if c not in CAT_COLS]
    x_train = train[base_numeric].copy()
    x_test = test[base_numeric].copy()

    # 预算与派生特征（全部数值化）
    for source, target in ((train, x_train), (test, x_test)):
        target["component_sum"] = source[COMPONENT_COLS].fillna(0.0).sum(axis=1)
        target["other_screen"] = source["daily_screen_time_hours"] - target["component_sum"]
        target["n_components_observed"] = source[COMPONENT_COLS].notna().sum(axis=1).astype(np.float32)
        target["component_sum_is_zero"] = target["component_sum"].eq(0.0).astype(np.int8)
        target["social_share"] = safe_ratio(source["social_media_hours"], source["daily_screen_time_hours"])
        target["gaming_share"] = safe_ratio(source["gaming_hours"], source["daily_screen_time_hours"])
        target["work_share"] = safe_ratio(source["work_study_hours"], source["daily_screen_time_hours"])
        target["other_share"] = safe_ratio(target["other_screen"], source["daily_screen_time_hours"])
        target["weekend_share"] = safe_ratio(source["weekend_screen_time"], source["daily_screen_time_hours"])
        target["open_per_screen"] = safe_ratio(source["app_opens_per_day"], source["daily_screen_time_hours"])
        target["notif_per_screen"] = safe_ratio(source["notifications_per_day"], source["daily_screen_time_hours"])
        target["sleep_pressure"] = source["daily_screen_time_hours"] - source["sleep_hours"] * 7.5
        target["social_minus_gaming"] = source["social_media_hours"] - source["gaming_hours"]

    for col in [
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
    ]:
        x_train[f"log1p_{col}"] = np.log1p(x_train[col].clip(lower=0.0))
        x_test[f"log1p_{col}"] = np.log1p(x_test[col].clip(lower=0.0))
        x_train[f"sqrt_{col}"] = np.sqrt(np.clip(x_train[col].astype(float), 0.0, None))
        x_test[f"sqrt_{col}"] = np.sqrt(np.clip(x_test[col].astype(float), 0.0, None))

    # 类别 one-hot
    cat_train = train[CAT_COLS].copy()
    cat_test = test[CAT_COLS].copy()
    cat_train = cat_train.fillna("__NA__").astype(str)
    cat_test = cat_test.fillna("__NA__").astype(str)
    all_data = pd.concat([cat_train, cat_test], axis=0, ignore_index=True)
    all_dummies = pd.get_dummies(all_data, columns=CAT_COLS, dummy_na=False, dtype=np.float32)
    cat_train_d = all_dummies.iloc[: len(train)].reset_index(drop=True)
    cat_test_d = all_dummies.iloc[len(train):].reset_index(drop=True)

    # 类别特征与数值特征拼接
    x_train = pd.concat([x_train.reset_index(drop=True), cat_train_d], axis=1)
    x_test = pd.concat([x_test.reset_index(drop=True), cat_test_d], axis=1)
    x_train = x_train.astype(np.float32)
    x_test = x_test.astype(np.float32)

    if list(x_train.columns) != list(x_test.columns):
        raise ValueError("训练集与测试集特征列不一致")
    return x_train, x_test


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
    x_train, x_test = build_features(train, test)
    y = train[TARGET].to_numpy(dtype=np.int8)

    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []

    print(f"train={train.shape}, test={test.shape}, features={x_train.shape[1]}")

    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(x_train, y), start=1):
        fold_start = time.time()

        x_fit = x_train.iloc[fit_idx].copy().reset_index(drop=True)
        x_valid = x_train.iloc[valid_idx].copy().reset_index(drop=True)
        y_fit = y[fit_idx]
        y_valid = y[valid_idx]
        x_test_fold = x_test.reset_index(drop=True)

        # 折内缺失值插补：使用训练折统计量，防止泄漏
        fillers = {}
        for col in x_fit.columns:
            if x_fit[col].dtype.kind in "f":
                med = float(x_fit[col].median())
                fillers[col] = med
                x_fit[col] = x_fit[col].fillna(med)
                x_valid[col] = x_valid[col].fillna(med)
                x_test_fold[col] = x_test_fold[col].fillna(med)
            else:
                mode = x_fit[col].mode(dropna=True)
                fill_val = float(mode.iloc[0]) if len(mode) else 0.0
                fillers[col] = fill_val
                x_fit[col] = x_fit[col].fillna(fill_val)
                x_valid[col] = x_valid[col].fillna(fill_val)
                x_test_fold[col] = x_test_fold[col].fillna(fill_val)

        dtrain = xgb.DMatrix(x_fit, label=y_fit)
        dvalid = xgb.DMatrix(x_valid, label=y_valid)
        test_d = xgb.DMatrix(x_test_fold)
        train_params = {k: v for k, v in XGB_PARAMS.items() if k != "n_estimators"}
        train_params["eval_metric"] = "auc"
        model = xgb.train(
            train_params,
            dtrain,
            num_boost_round=XGB_PARAMS["n_estimators"],
            evals=[(dvalid, "valid")],
            early_stopping_rounds=150,
            verbose_eval=False,
        )
        best_iter = int(model.best_iteration)

        valid_pred = model.predict(dvalid, iteration_range=(0, best_iter + 1))
        oof[valid_idx] = valid_pred
        test_pred += model.predict(test_d, iteration_range=(0, best_iter + 1)) / N_FOLDS

        fold_auc = float(roc_auc_score(y_valid, valid_pred))
        fold_scores.append(fold_auc)
        best_iterations.append(best_iter + 1)
        print(
            f"fold={fold} auc={fold_auc:.6f} best_iteration={best_iterations[-1]} "
            f"elapsed={time.time()-fold_start:.1f}s fillers={len(fillers)}"
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    v7 = json.loads(V7_RESULTS.read_text(encoding="utf-8"))
    v7_fold_key = "fold_auc"
    if v7_fold_key not in v7:
        v7_fold_key = "new_seed_fold_auc" if "new_seed_fold_auc" in v7 else None
    v7_oof_key = "oof_auc"
    if v7_oof_key not in v7:
        v7_oof_key = "new_seed_oof_auc" if "new_seed_oof_auc" in v7 else None
    if v7_fold_key is None or v7_oof_key is None:
        raise ValueError("无法解析 v7_catboost_bagging 的指标字段：缺少 fold_auc/new_seed_fold_auc 或 oof_auc/new_seed_oof_auc")

    fold_deltas = np.asarray(fold_scores) - np.asarray(v7[v7_fold_key], dtype=float)

    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    results = {
        "competition": "playground-series-s6e8",
        "model": "XGBoost engineered numeric+OHE v11",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "feature_count": int(x_train.shape[1]),
        "xgb_params": XGB_PARAMS,
        "fold_auc": [float(x) for x in fold_scores],
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iterations,
        "oof_auc": oof_auc,
        "v7_oof_auc": float(v7[v7_oof_key]),
        "oof_delta_vs_v7": oof_auc - float(v7[v7_oof_key]),
        "fold_delta_vs_v7": fold_deltas.tolist(),
        "folds_won_vs_v7": int((fold_deltas > 0).sum()),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
    }
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
