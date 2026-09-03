# -*- coding: utf-8 -*-
"""
v7：v3 CatBoost 双重表示 × 2 种子 bagging（同一外层折划分，模型种子 42 / 2026）。

消融 C1 表明显式联合键类别对 CatBoost 无增益（CTR 组合已覆盖），因此仅做种子 bagging。

赛题：Predicting Electric Vehicle Purchases（Playground Series S6E9）
指标：ROC AUC

每个数值字段同时以两种方式提供给模型：
- 保留连续数值，学习平滑趋势；
- 复制为字符串类别（key_*），利用 CatBoost ordered target statistics 学习精确值关联，
  直接针对合成数据的 value-level 伪影（收入单值、硬阈值等）。
6 个原始分类列直接作为类别特征。不使用手写 target encoding，CatBoost 的类别统计
只在训练折内按 ordered 方式生成，OOF 无标签泄漏。对比基准为 v1（同 seed 同折）。
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
TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
BASE_RESULTS = OUT_DIR.parent / "v3_dual_catboost" / "cv_results.json"
BAG_SEEDS = [42, 2026]

RAW_CAT_COLS = [
    "Gender",
    "City_Type",
    "Current_Car_Type",
    "Home_Charging_Possible",
    "Subsidy_Available",
    "Range_Anxiety_Level",
]

CAT_PARAMS = {
    "iterations": 3000,
    "learning_rate": 0.05,
    "depth": 8,
    "l2_leaf_reg": 6.0,
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "random_seed": SEED,
    "one_hot_max_size": 4,
    "max_ctr_complexity": 2,
    "od_type": "Iter",
    "od_wait": 200,
    "allow_writing_files": False,
    "thread_count": 16,
    "verbose": 500,
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if TARGET not in train or TARGET in test:
        raise ValueError("训练集/测试集目标列不符合预期")
    if train[ID_COL].duplicated().any() or test[ID_COL].duplicated().any():
        raise ValueError("发现重复 id")
    if set(train[TARGET].unique()) != {"No", "Yes"}:
        raise ValueError(f"目标列取值异常：{train[TARGET].unique()}")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission.csv 的 id 顺序与 test.csv 不一致")
    if train.isna().any().any() or test.isna().any().any():
        raise ValueError("数据出现缺失值，与初始化核验不符")
    return train, test, sample


def build_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    raw_cols = [c for c in test.columns if c != ID_COL]
    numeric_cols = [c for c in raw_cols if c not in RAW_CAT_COLS]

    x_train = train[numeric_cols].copy()
    x_test = test[numeric_cols].copy()

    categorical_cols: list[str] = []
    # 数值列的精确值字符串表示
    for col in numeric_cols:
        key_col = f"key_{col}"
        x_train[key_col] = train[col].astype(str)
        x_test[key_col] = test[col].astype(str)
        categorical_cols.append(key_col)
    # 原始分类列
    for col in RAW_CAT_COLS:
        x_train[col] = train[col].astype(str)
        x_test[col] = test[col].astype(str)
        categorical_cols.append(col)

    if list(x_train.columns) != list(x_test.columns):
        raise ValueError("训练集与测试集特征列不一致")
    return x_train, x_test, categorical_cols


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
    x_train, x_test, categorical_cols = build_features(train, test)
    y = (train[TARGET] == POS_LABEL).to_numpy(dtype=np.int8)

    print(
        f"train={train.shape}, test={test.shape}, features={x_train.shape[1]}, "
        f"categorical={len(categorical_cols)}"
    )

    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    importance_frames: list[pd.DataFrame] = []
    test_pool = Pool(x_test, cat_features=categorical_cols)

    for fold, (train_idx, valid_idx) in enumerate(splitter.split(x_train, y), start=1):
        fold_start = time.time()
        train_pool = Pool(x_train.iloc[train_idx], y[train_idx], cat_features=categorical_cols)
        valid_pool = Pool(x_train.iloc[valid_idx], y[valid_idx], cat_features=categorical_cols)
        valid_pred = np.zeros(len(valid_idx), dtype=np.float64)
        fold_test = np.zeros(len(test), dtype=np.float64)
        fold_iters: list[int] = []
        fold_importance = np.zeros(x_train.shape[1], dtype=np.float64)
        for seed in BAG_SEEDS:
            model = CatBoostClassifier(**{**CAT_PARAMS, "random_seed": seed})
            model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
            vp = model.predict_proba(valid_pool)[:, 1]
            valid_pred += vp / len(BAG_SEEDS)
            fold_test += model.predict_proba(test_pool)[:, 1] / len(BAG_SEEDS)
            fold_iters.append(int(model.get_best_iteration() + 1))
            fold_importance += model.get_feature_importance() / len(BAG_SEEDS)
            print(f"  fold={fold} seed={seed} auc={roc_auc_score(y[valid_idx], vp):.6f} best_iteration={fold_iters[-1]}", flush=True)
        oof[valid_idx] = valid_pred
        test_pred += fold_test / N_FOLDS
        best_iteration = int(np.mean(fold_iters))

        fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(fold_auc)
        best_iterations.append(best_iteration)
        importance_frames.append(
            pd.DataFrame(
                {"feature": x_train.columns, "importance": fold_importance, "fold": fold}
            )
        )
        print(
            f"fold={fold} auc={fold_auc:.6f} best_iteration={best_iteration} "
            f"elapsed={time.time() - fold_start:.1f}s",
            flush=True,
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    base = json.loads(BASE_RESULTS.read_text(encoding="utf-8"))
    base_fold = np.asarray(base["fold_auc"], dtype=float)
    fold_deltas = np.asarray(fold_scores) - base_fold
    oof_delta = oof_auc - float(base["oof_auc"])
    print(f"OOF AUC={oof_auc:.6f}, delta_vs_v3={oof_delta:+.6f}, folds_won={(fold_deltas > 0).sum()}/{N_FOLDS}")
    print("fold_deltas=" + ", ".join(f"{d:+.6f}" for d in fold_deltas))

    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    importance = pd.concat(importance_frames, ignore_index=True)
    importance_summary = (
        importance.groupby("feature", as_index=False)
        .agg(importance_mean=("importance", "mean"), importance_std=("importance", "std"))
        .sort_values("importance_mean", ascending=False)
    )
    importance_summary.to_csv(OUT_DIR / "feature_importance.csv", index=False)
    print(importance_summary.to_string(index=False))

    results = {
        "competition": "playground-series-s6e9",
        "model": "CatBoost dual representation, 2-seed bagging",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "feature_count": int(x_train.shape[1]),
        "categorical_feature_count": len(categorical_cols),
        "fold_auc": fold_scores,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iterations,
        "oof_auc": oof_auc,
        "base": "v3_dual_catboost",
        "base_oof_auc": float(base["oof_auc"]),
        "oof_delta_vs_base": oof_delta,
        "fold_delta_vs_base": fold_deltas.tolist(),
        "folds_won_vs_base": int((fold_deltas > 0).sum()),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "catboost_version": catboost_version,
        "params": CAT_PARAMS,
        "bag_seeds": BAG_SEEDS,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"submission={OUT_DIR / 'submission.csv'}")
    print(f"elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
