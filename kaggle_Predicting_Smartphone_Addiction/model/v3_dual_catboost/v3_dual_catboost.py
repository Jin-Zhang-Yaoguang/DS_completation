# -*- coding: utf-8 -*-
"""
v3：CatBoost 连续值/精确值双重表示 + 时间预算特征。

每个原始字段同时以两种方式提供给模型：
- 数值字段保留连续数值，学习平滑趋势；
- 所有字段复制为字符串类别，利用 CatBoost ordered statistics 学习精确值关联。

不使用手写 target encoding；CatBoost 的类别统计只从训练数据生成。
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

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
V2_RESULTS = OUT_DIR.parent / "v2_budget_lgbm" / "cv_results.json"

COMPONENT_COLS = ["social_media_hours", "gaming_hours", "work_study_hours"]
BUDGET_COLS = [
    "component_sum_available",
    "other_screen_available",
    "n_components_observed",
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
    "thread_count": -1,
    "verbose": 200,
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


def build_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    raw_cols = [c for c in test.columns if c != ID_COL]
    numeric_cols = [c for c in raw_cols if pd.api.types.is_numeric_dtype(train[c])]

    x_train = train[numeric_cols].copy()
    x_test = test[numeric_cols].copy()

    for source, output in ((train, x_train), (test, x_test)):
        parts = source[COMPONENT_COLS]
        output["component_sum_available"] = parts.fillna(0.0).sum(axis=1)
        output["other_screen_available"] = (
            source["daily_screen_time_hours"]
            - output["component_sum_available"]
        )
        output["n_components_observed"] = (
            parts.notna().sum(axis=1).astype(np.float32)
        )

    categorical_cols: list[str] = []
    for col in raw_cols:
        key_col = f"key_{col}"
        x_train[key_col] = train[col].where(train[col].notna(), "__NA__").astype(str)
        x_test[key_col] = test[col].where(test[col].notna(), "__NA__").astype(str)
        categorical_cols.append(key_col)

    if list(x_train.columns) != list(x_test.columns):
        raise ValueError("训练集与测试集特征列不一致")
    if not set(BUDGET_COLS).issubset(x_train.columns):
        raise ValueError("时间预算特征未正确生成")
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
    y = train[TARGET].to_numpy(dtype=np.int8)

    print(
        f"train={train.shape}, test={test.shape}, features={x_train.shape[1]}, "
        f"categorical={len(categorical_cols)}"
    )

    splitter = StratifiedKFold(
        n_splits=N_FOLDS, shuffle=True, random_state=SEED
    )
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    importance_frames: list[pd.DataFrame] = []
    test_pool = Pool(x_test, cat_features=categorical_cols)

    for fold, (train_idx, valid_idx) in enumerate(
        splitter.split(x_train, y), start=1
    ):
        fold_start = time.time()
        train_pool = Pool(
            x_train.iloc[train_idx], y[train_idx], cat_features=categorical_cols
        )
        valid_pool = Pool(
            x_train.iloc[valid_idx], y[valid_idx], cat_features=categorical_cols
        )
        model = CatBoostClassifier(**CAT_PARAMS)
        model.fit(train_pool, eval_set=valid_pool, use_best_model=True)

        valid_pred = model.predict_proba(valid_pool)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(test_pool)[:, 1] / N_FOLDS

        fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
        best_iteration = int(model.get_best_iteration() + 1)
        fold_scores.append(fold_auc)
        best_iterations.append(best_iteration)
        importance_frames.append(
            pd.DataFrame(
                {
                    "feature": x_train.columns,
                    "importance": model.get_feature_importance(),
                    "fold": fold,
                }
            )
        )
        print(
            f"fold={fold} auc={fold_auc:.6f} best_iteration={best_iteration} "
            f"elapsed={time.time() - fold_start:.1f}s"
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    v2 = json.loads(V2_RESULTS.read_text(encoding="utf-8"))
    v2_fold_scores = np.asarray(v2["fold_auc"], dtype=float)
    fold_deltas = np.asarray(fold_scores) - v2_fold_scores
    oof_delta = oof_auc - float(v2["oof_auc"])
    print(f"OOF AUC={oof_auc:.6f}, delta_vs_v2={oof_delta:+.6f}")
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
        .agg(
            importance_mean=("importance", "mean"),
            importance_std=("importance", "std"),
        )
        .sort_values("importance_mean", ascending=False)
    )
    importance_summary.to_csv(OUT_DIR / "feature_importance.csv", index=False)

    results = {
        "competition": "playground-series-s6e8",
        "model": "CatBoost continuous-plus-exact-value dual representation",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "feature_count": int(x_train.shape[1]),
        "categorical_feature_count": len(categorical_cols),
        "budget_features": BUDGET_COLS,
        "fold_auc": fold_scores,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iterations,
        "oof_auc": oof_auc,
        "v2_oof_auc": float(v2["oof_auc"]),
        "oof_delta_vs_v2": oof_delta,
        "fold_delta_vs_v2": fold_deltas.tolist(),
        "folds_won_vs_v2": int((fold_deltas > 0).sum()),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "catboost_version": catboost_version,
        "params": CAT_PARAMS,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"submission={OUT_DIR / 'submission.csv'}")
    print(f"elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
