# -*- coding: utf-8 -*-
"""v13：更完善 FE 的单模型对比实验。

目标：
1) 用一套统一特征工程统一对比 LightGBM / CatBoost / XGBoost。
2) 所有变换可复现、无标签泄漏（按折内插补）。
3) 输出每个单模的 OOF AUC 与折内波动，用于下一步模型融合前的基准选择。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
import xgboost as xgb


TARGET = "addicted_label"
ID_COL = "id"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

N_FOLDS = 5
SEED = 42

NUMERIC_COLS: list[str] = [
    "age",
    "daily_screen_time_hours",
    "weekend_screen_time",
    "social_media_hours",
    "gaming_hours",
    "work_study_hours",
    "notifications_per_day",
    "app_opens_per_day",
    "sleep_hours",
]
CAT_COLS: list[str] = ["gender", "stress_level", "academic_work_impact"]
COMPONENT_COLS: list[str] = ["social_media_hours", "gaming_hours", "work_study_hours"]


LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "n_estimators": 1000,
    "learning_rate": 0.03,
    "num_leaves": 40,
    "max_depth": -1,
    "min_child_samples": 140,
    "subsample": 0.9,
    "subsample_freq": 1,
    "colsample_bytree": 0.9,
    "reg_alpha": 0.2,
    "reg_lambda": 1.6,
    "random_state": SEED,
    "bagging_seed": SEED,
    "feature_fraction_seed": SEED,
    "data_random_seed": SEED,
    "deterministic": True,
    "force_col_wise": True,
    "verbosity": -1,
    "n_jobs": 16,
}

CAT_PARAMS = {
    "iterations": 1200,
    "learning_rate": 0.05,
    "depth": 8,
    "l2_leaf_reg": 4.5,
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "random_seed": SEED,
    "one_hot_max_size": 2,
    "max_ctr_complexity": 2,
    "od_type": "Iter",
    "od_wait": 180,
    "allow_writing_files": False,
    "thread_count": 16,
    "verbose": 200,
}

XGB_PARAMS: dict[str, Any] = {
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "learning_rate": 0.05,
    "max_depth": 7,
    "min_child_weight": 4.0,
    "subsample": 0.88,
    "colsample_bytree": 0.88,
    "colsample_bylevel": 0.88,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "gamma": 0.0,
    "tree_method": "hist",
    "max_bin": 256,
    "n_jobs": -1,
    "seed": SEED,
}


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    if isinstance(den, (int, float, np.float64, np.float32)):
        if float(den) == 0.0:
            return num / np.nan
        return num / den
    den = den.replace(0.0, np.nan)
    return num / den


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")

    if TARGET not in train or TARGET in test:
        raise ValueError("训练/测试字段不符合预期")
    if train[ID_COL].duplicated().any() or test[ID_COL].duplicated().any():
        raise ValueError("id 存在重复")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission 与 test 的 id 顺序不一致")
    if not set(train[TARGET].unique()) <= {0, 1}:
        raise ValueError("目标列不是 0/1")
    return train, test, sample


def add_core_features(df: pd.DataFrame, is_train: bool) -> pd.DataFrame:
    out = df.copy()

    for col in NUMERIC_COLS:
        out[f"na_{col}"] = out[col].isna().astype(np.int8)
    for col in CAT_COLS:
        out[f"na_{col}"] = out[col].isna().astype(np.int8)

    out["n_missing_num"] = out[[f"na_{c}" for c in NUMERIC_COLS]].sum(axis=1).astype(np.int8)
    out["n_missing_cat"] = out[[f"na_{c}" for c in CAT_COLS]].sum(axis=1).astype(np.int8)
    out["n_missing_total"] = out["n_missing_num"] + out["n_missing_cat"]

    # 组件与总预算结构
    comp = out[COMPONENT_COLS]
    out["component_sum"] = comp.fillna(0.0).sum(axis=1)
    out["other_screen"] = out["daily_screen_time_hours"] - out["component_sum"]
    out["n_components_observed"] = comp.notna().sum(axis=1).astype(np.float32)
    out["n_components_missing"] = 3 - out["n_components_observed"]
    out["component_sum_is_zero"] = (out["component_sum"].eq(0.0)).astype(np.int8)
    out["other_screen_is_negative"] = (out["other_screen"] < 0.0).astype(np.int8)
    out["other_screen_abs"] = out["other_screen"].abs()

    # 预留字段，未来可作为诊断，不参与目标条件（当前不会用到）。
    if is_train and "addicted_label" in out.columns:
        out["y_interaction_proxy"] = (
            out["addicted_label"] * out["daily_screen_time_hours"].fillna(0.0)
        )
        out.drop(columns=["y_interaction_proxy"], inplace=True)

    screen = out["daily_screen_time_hours"]
    weekend = out["weekend_screen_time"]
    social = out["social_media_hours"]
    gaming = out["gaming_hours"]
    work = out["work_study_hours"]
    notif = out["notifications_per_day"]
    opens = out["app_opens_per_day"]
    sleep = out["sleep_hours"]

    # 比例与密度特征
    out["social_share"] = safe_ratio(social, screen)
    out["gaming_share"] = safe_ratio(gaming, screen)
    out["work_share"] = safe_ratio(work, screen)
    out["other_share"] = safe_ratio(out["other_screen"], screen)
    out["weekend_share"] = safe_ratio(weekend, screen)
    out["open_share"] = safe_ratio(opens, screen)
    out["notif_share"] = safe_ratio(notif, screen)
    out["notif_per_open"] = safe_ratio(notif, opens)
    out["open_per_hour"] = safe_ratio(opens, screen)
    out["notif_per_work_hour"] = safe_ratio(notif, work)
    out["open_per_work_hour"] = safe_ratio(opens, work)

    out["weekend_minus_daily"] = weekend - screen
    out["weekend_ratio"] = safe_ratio(weekend, screen)
    out["screen_minus_weekend"] = screen - weekend

    out["social_vs_gaming"] = safe_ratio(social, gaming)
    out["gaming_vs_social"] = safe_ratio(gaming, social)
    out["social_vs_work"] = safe_ratio(social, work)
    out["work_vs_gaming"] = safe_ratio(work, gaming)

    out["sleep_deficit_7"] = 7.0 - sleep
    out["sleep_deficit_8"] = 8.0 - sleep
    out["sleep_excess_8"] = sleep - 8.0
    out["sleep_pressure_7_5x"] = out["daily_screen_time_hours"] - sleep * 7.5

    out["age_x_screen"] = out["age"] * safe_ratio(screen, 1.0)
    out["age_x_social"] = out["age"] * safe_ratio(social, 1.0)
    out["age_x_gaming"] = out["age"] * safe_ratio(gaming, 1.0)
    out["age_x_work"] = out["age"] * safe_ratio(work, 1.0)

    # 非线性与残差型特征（保留原始数值，不替换）
    log_cols = [
        "daily_screen_time_hours",
        "weekend_screen_time",
        "social_media_hours",
        "gaming_hours",
        "work_study_hours",
        "notifications_per_day",
        "app_opens_per_day",
        "sleep_hours",
        "component_sum",
        "other_screen",
        "other_screen_abs",
    ]
    for col in log_cols:
        out[f"log1p_{col}"] = np.log1p(out[col].clip(lower=0.0))
        out[f"sqrt_{col}"] = np.sqrt(np.clip(out[col].astype(float), 0.0, None))
        out[f"sq_{col}"] = out[col] ** 2

    # 生成器伪影友好特征：小数部分/整数性（主要针对时长/活动/睡眠）
    frac_cols = [
        "daily_screen_time_hours",
        "weekend_screen_time",
        "social_media_hours",
        "gaming_hours",
        "work_study_hours",
        "notifications_per_day",
        "app_opens_per_day",
        "sleep_hours",
    ]
    for col in frac_cols:
        frac = out[col].astype(float) - np.floor(out[col].astype(float))
        out[f"{col}_frac"] = frac
        out[f"{col}_frac_100"] = np.floor(frac * 100).clip(lower=0, upper=99).astype("float32")
        out[f"{col}_is_int"] = (
            (out[col].notna() & (frac.abs() <= 1e-6)).astype(np.int8)
        )

    return out.copy()


def build_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_base = train.drop(columns=[TARGET])
    train_fe = add_core_features(train_base, is_train=True)
    test_fe = add_core_features(test, is_train=False)

    # 合并后统一 One-Hot 与列顺序，避免折内外列错位
    combined = pd.concat([train_fe, test_fe], axis=0, ignore_index=True)
    combined = pd.get_dummies(
        combined,
        columns=CAT_COLS,
        dummy_na=True,
        dtype=np.float32,
    )
    train_enc = combined.iloc[: len(train_fe)].reset_index(drop=True)
    test_enc = combined.iloc[len(train_fe) :].reset_index(drop=True)
    if list(train_enc.columns) != list(test_enc.columns):
        raise ValueError("训练与测试特征列顺序不一致")

    # 保存 FE 字段，便于复现
    (OUT_DIR / "feature_columns.csv").write_text(
        "\n".join(train_enc.columns), encoding="utf-8"
    )
    return train_enc, test_enc


def build_features_for_catboost(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    train_fe = add_core_features(train.drop(columns=[TARGET]), is_train=True)
    test_fe = add_core_features(test, is_train=False)

    for col in CAT_COLS:
        train_fe[f"key_{col}"] = train_fe[col].fillna("__NA__").astype(str)
        test_fe[f"key_{col}"] = test_fe[col].fillna("__NA__").astype(str)
    cat_features = [f"key_{c}" for c in CAT_COLS]

    # 保留数值与工程特征，移除原始类别列，避免重复信息
    train_fe = train_fe.drop(columns=CAT_COLS).reset_index(drop=True)
    test_fe = test_fe.drop(columns=CAT_COLS).reset_index(drop=True)

    if set(cat_features) - set(train_fe.columns):
        raise ValueError("CatBoost 类别列构建失败")
    if list(train_fe.columns) != list(test_fe.columns):
        raise ValueError("CatBoost 训练/测试列顺序不一致")
    return train_fe, test_fe, cat_features


def fold_fill_na(
    df_fit: pd.DataFrame, df_valid: pd.DataFrame, df_test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for col in df_fit.columns:
        if pd.api.types.is_numeric_dtype(df_fit[col].dtype):
            med = float(df_fit[col].median())
            if not pd.notna(med):
                med = 0.0
            df_fit[col] = df_fit[col].fillna(med)
            df_valid[col] = df_valid[col].fillna(med)
            df_test[col] = df_test[col].fillna(med)
    return df_fit, df_valid, df_test


def train_lgbm(
    x_train: pd.DataFrame,
    y: np.ndarray,
    x_test: pd.DataFrame,
    splitter: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, list[float], np.ndarray, np.ndarray, list[int], float]:
    oof = np.zeros(len(y), dtype=np.float64)
    test_pred = np.zeros(len(x_test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    started = time.time()

    for fold, (fit_idx, valid_idx) in enumerate(splitter, start=1):
        fold_start = time.time()
        x_fit = x_train.iloc[fit_idx].copy().reset_index(drop=True)
        x_valid = x_train.iloc[valid_idx].copy().reset_index(drop=True)
        y_fit = y[fit_idx]
        y_valid = y[valid_idx]

        x_fit, x_valid, x_test_fold = fold_fill_na(
            x_fit,
            x_valid,
            x_test.reset_index(drop=True).copy(),
        )

        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            x_fit,
            y_fit,
            eval_set=[(x_valid, y_valid)],
            eval_metric="auc",
            callbacks=[
                lgb.early_stopping(120, verbose=False),
                lgb.log_evaluation(0),
            ],
        )
        preds_valid = model.predict_proba(x_valid, num_iteration=model.best_iteration_)[:, 1]
        preds_test = model.predict_proba(x_test_fold, num_iteration=model.best_iteration_)[:, 1]
        oof[valid_idx] = preds_valid
        test_pred += preds_test / N_FOLDS
        auc = float(roc_auc_score(y_valid, preds_valid))
        fold_scores.append(auc)
        best_iterations.append(int(model.best_iteration_))
        print(
            f"[LGBM] fold={fold} auc={auc:.6f} best={model.best_iteration_} "
            f"elapsed={time.time()-fold_start:.1f}s"
        )

    return (
        float(roc_auc_score(y, oof)),
        fold_scores,
        oof,
        test_pred,
        best_iterations,
        float(time.time() - started),
    )


def train_catboost(
    x_train: pd.DataFrame,
    y: np.ndarray,
    x_test: pd.DataFrame,
    cat_features: list[str],
    splitter: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, list[float], np.ndarray, np.ndarray, list[int], float]:
    oof = np.zeros(len(y), dtype=np.float64)
    test_pred = np.zeros(len(x_test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    cat_indices = [x_train.columns.get_loc(c) for c in cat_features]
    started = time.time()

    for fold, (fit_idx, valid_idx) in enumerate(splitter, start=1):
        fold_start = time.time()
        x_fit = x_train.iloc[fit_idx].reset_index(drop=True)
        x_valid = x_train.iloc[valid_idx].reset_index(drop=True)
        y_fit = y[fit_idx]
        y_valid = y[valid_idx]
        test_fold = x_test.reset_index(drop=True).copy()

        # 缺失值：CatBoost 原生处理，保持折内结构不加额外插补
        model = CatBoostClassifier(**CAT_PARAMS)
        model.fit(
            Pool(x_fit, y_fit, cat_features=cat_indices),
            eval_set=Pool(x_valid, y_valid, cat_features=cat_indices),
            use_best_model=True,
        )

        preds_valid = model.predict_proba(Pool(x_valid, cat_features=cat_indices))[:, 1]
        preds_test = model.predict_proba(Pool(test_fold, cat_features=cat_indices))[:, 1]
        oof[valid_idx] = preds_valid
        test_pred += preds_test / N_FOLDS
        auc = float(roc_auc_score(y_valid, preds_valid))
        fold_scores.append(auc)
        best_iterations.append(int(model.get_best_iteration() + 1))
        print(
            f"[CatBoost] fold={fold} auc={auc:.6f} best={best_iterations[-1]} "
            f"elapsed={time.time()-fold_start:.1f}s"
        )

    return (
        float(roc_auc_score(y, oof)),
        fold_scores,
        oof,
        test_pred,
        best_iterations,
        float(time.time() - started),
    )


def train_xgb(
    x_train: pd.DataFrame,
    y: np.ndarray,
    x_test: pd.DataFrame,
    splitter: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, list[float], np.ndarray, np.ndarray, list[int], float]:
    oof = np.zeros(len(y), dtype=np.float64)
    test_pred = np.zeros(len(x_test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    started = time.time()

    for fold, (fit_idx, valid_idx) in enumerate(splitter, start=1):
        fold_start = time.time()
        x_fit = x_train.iloc[fit_idx].copy().reset_index(drop=True)
        x_valid = x_train.iloc[valid_idx].copy().reset_index(drop=True)
        y_fit = y[fit_idx]
        y_valid = y[valid_idx]

        x_fit, x_valid, x_test_fold = fold_fill_na(
            x_fit,
            x_valid,
            x_test.reset_index(drop=True).copy(),
        )

        dtrain = xgb.DMatrix(x_fit, label=y_fit, nthread=-1)
        dvalid = xgb.DMatrix(x_valid, label=y_valid, nthread=-1)
        dtest = xgb.DMatrix(x_test_fold, nthread=-1)
        model = xgb.train(
            {k: v for k, v in XGB_PARAMS.items()},
            dtrain,
            num_boost_round=2600,
            evals=[(dvalid, "valid")],
            early_stopping_rounds=150,
            verbose_eval=False,
        )
        best_iter = int(model.best_iteration + 1)
        valid_pred = model.predict(dvalid, iteration_range=(0, best_iter))
        test_fold_pred = model.predict(dtest, iteration_range=(0, best_iter))
        valid_pred = np.clip(valid_pred, 0.0, 1.0)
        test_fold_pred = np.clip(test_fold_pred, 0.0, 1.0)
        oof[valid_idx] = valid_pred
        test_pred += test_fold_pred / N_FOLDS
        auc = float(roc_auc_score(y_valid, valid_pred))
        fold_scores.append(auc)
        best_iterations.append(best_iter)
        print(
            f"[XGB] fold={fold} auc={auc:.6f} best={best_iter} "
            f"elapsed={time.time()-fold_start:.1f}s"
        )

    return (
        float(roc_auc_score(y, oof)),
        fold_scores,
        oof,
        test_pred,
        best_iterations,
        float(time.time() - started),
    )


def validate_submission(submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame) -> None:
    if submission.shape != sample.shape:
        raise ValueError(f"提交 shape 错误：{submission.shape} != {sample.shape}")
    if list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError(f"提交列名错误：{submission.columns.tolist()}")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与测试集不一致")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all():
        raise ValueError("提交概率含 NaN/inf")
    if ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率越界")


def main() -> None:
    start = time.time()
    train, test, sample = load_data()
    y = train[TARGET].to_numpy(dtype=np.int8)

    splitter = list(
        StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED).split(
            train[[ID_COL] + NUMERIC_COLS], y
        )
    )

    ranking: list[dict[str, Any]] = []
    models_summary: list[dict[str, Any]] = []

    # LightGBM
    x_train_lgb, x_test_lgb = build_features(train, test)
    print(f"[LGBM] feature shape train={x_train_lgb.shape}, test={x_test_lgb.shape}")
    lgb_auc, lgb_folds, lgb_oof, lgb_test_pred, lgb_best, lgb_elapsed = train_lgbm(
        x_train_lgb, y, x_test_lgb, splitter
    )
    models_summary.append(
        {
            "name": "v13_lgbm",
            "oof_auc": lgb_auc,
            "fold_auc": lgb_folds,
            "fold_auc_mean": float(np.mean(lgb_folds)),
            "fold_auc_std": float(np.std(lgb_folds)),
            "best_iterations": lgb_best,
            "feature_count": int(x_train_lgb.shape[1]),
            "elapsed_seconds": float(lgb_elapsed),
            "params": LGB_PARAMS,
        }
    )
    np.save(OUT_DIR / "lgbm_oof_proba.npy", lgb_oof)
    np.save(OUT_DIR / "lgbm_test_proba.npy", lgb_test_pred)
    submission = sample.copy()
    submission[TARGET] = lgb_test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission_lgbm.csv", index=False)

    # CatBoost
    x_train_cat, x_test_cat, cat_features = build_features_for_catboost(train, test)
    print(f"[CatBoost] feature shape train={x_train_cat.shape}, test={x_test_cat.shape}")
    cat_auc, cat_folds, cat_oof, cat_test_pred, cat_best, cat_elapsed = train_catboost(
        x_train_cat, y, x_test_cat, cat_features, splitter
    )
    models_summary.append(
        {
            "name": "v13_catboost",
            "oof_auc": cat_auc,
            "fold_auc": cat_folds,
            "fold_auc_mean": float(np.mean(cat_folds)),
            "fold_auc_std": float(np.std(cat_folds)),
            "best_iterations": cat_best,
            "feature_count": int(x_train_cat.shape[1]),
            "cat_features": cat_features,
            "elapsed_seconds": float(cat_elapsed),
            "params": CAT_PARAMS,
        }
    )
    np.save(OUT_DIR / "cat_oof_proba.npy", cat_oof)
    np.save(OUT_DIR / "cat_test_proba.npy", cat_test_pred)
    submission = sample.copy()
    submission[TARGET] = cat_test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission_cat.csv", index=False)

    # XGBoost
    x_train_xgb, x_test_xgb = build_features(train, test)
    print(f"[XGB] feature shape train={x_train_xgb.shape}, test={x_test_xgb.shape}")
    xgb_auc, xgb_folds, xgb_oof, xgb_test_pred, xgb_best, xgb_elapsed = train_xgb(
        x_train_xgb, y, x_test_xgb, splitter
    )
    models_summary.append(
        {
            "name": "v13_xgboost",
            "oof_auc": xgb_auc,
            "fold_auc": xgb_folds,
            "fold_auc_mean": float(np.mean(xgb_folds)),
            "fold_auc_std": float(np.std(xgb_folds)),
            "best_iterations": xgb_best,
            "feature_count": int(x_train_xgb.shape[1]),
            "elapsed_seconds": float(xgb_elapsed),
            "params": XGB_PARAMS,
        }
    )
    np.save(OUT_DIR / "xgb_oof_proba.npy", xgb_oof)
    np.save(OUT_DIR / "xgb_test_proba.npy", xgb_test_pred)
    submission = sample.copy()
    submission[TARGET] = xgb_test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission_xgb.csv", index=False)

    ranking = sorted(models_summary, key=lambda x: x["oof_auc"], reverse=True)
    overall = {
        "competition": "playground-series-s6e8",
        "experiment": "v13 FE single-model comparison",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "train_shape": list(train.shape),
        "test_shape": list(test.shape),
        "feature_count_lgbm": int(x_train_lgb.shape[1]),
        "feature_count_catboost": int(x_train_cat.shape[1]),
        "feature_count_xgb": int(x_train_xgb.shape[1]),
        "ranking": [
            {
                "name": item["name"],
                "oof_auc": item["oof_auc"],
                "fold_auc_mean": item["fold_auc_mean"],
                "fold_auc_std": item["fold_auc_std"],
            }
            for item in ranking
        ],
        "models": models_summary,
        "elapsed_seconds": float(time.time() - start),
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(overall, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"单模对比完成，排行榜={overall['ranking']}")
    print(f"总耗时: {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
