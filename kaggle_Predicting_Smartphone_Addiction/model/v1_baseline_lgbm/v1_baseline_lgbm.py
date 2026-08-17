# -*- coding: utf-8 -*-
"""
v1 baseline：原始特征 LightGBM + 5 折分层交叉验证。

赛题：Predicting Smartphone Addiction（Playground Series S6E8）
指标：ROC AUC

设计依据：
- 合成数据表现为平滑概率场，使用 GBDT 拟合非线性关系；
- 公开消融显示 31 leaves 明显优于欠拟合的 15 leaves；
- 数值缺失交给 LightGBM 原生处理，不添加会放大 train/test 偏移的缺失标记；
- 不使用 target encoding、外部数据或人工提交文件，保证 OOF 无标签泄漏。
"""

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
TARGET = "addicted_label"
ID_COL = "id"

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

CAT_COLS = ["gender", "stress_level", "academic_work_impact"]

LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "n_estimators": 1500,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "max_depth": -1,
    "min_child_samples": 40,
    "subsample": 0.9,
    "subsample_freq": 1,
    "colsample_bytree": 0.85,
    "reg_lambda": 1.0,
    "random_state": SEED,
    "bagging_seed": SEED,
    "feature_fraction_seed": SEED,
    "data_random_seed": SEED,
    "deterministic": True,
    "force_col_wise": True,
    "n_jobs": -1,
    "verbosity": -1,
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读取并校验官方原始文件。"""
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")

    if TARGET not in train or TARGET in test:
        raise ValueError("训练集/测试集目标列不符合预期")
    if train[ID_COL].duplicated().any() or test[ID_COL].duplicated().any():
        raise ValueError("发现重复 id")
    if set(train[TARGET].unique()) != {0, 1}:
        raise ValueError("目标列不是预期的二分类 0/1")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission.csv 的 id 顺序与 test.csv 不一致")

    return train, test, sample


def build_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """对类别列做无监督 one-hot，数值 NaN 保持原样。"""
    base_cols = [c for c in test.columns if c != ID_COL]
    combined = pd.concat(
        [train[base_cols], test[base_cols]], axis=0, ignore_index=True
    )
    combined = pd.get_dummies(
        combined,
        columns=CAT_COLS,
        dummy_na=True,
        dtype=np.float32,
    ).astype(np.float32)

    x_train = combined.iloc[: len(train)].reset_index(drop=True)
    x_test = combined.iloc[len(train) :].reset_index(drop=True)

    if list(x_train.columns) != list(x_test.columns):
        raise ValueError("训练集与测试集特征列不一致")
    return x_train, x_test


def validate_submission(
    submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame
) -> None:
    """在写盘前验证提交格式、ID 和概率。"""
    if submission.shape != sample.shape:
        raise ValueError(f"提交 shape 错误：{submission.shape} != {sample.shape}")
    if list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError(f"提交列名错误：{submission.columns.tolist()}")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与测试集不一致")

    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all():
        raise ValueError("提交概率包含 NaN 或无穷值")
    if ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率超出 [0, 1]")


def main() -> None:
    start = time.time()
    train, test, sample = load_data()
    x_train, x_test = build_features(train, test)
    y = train[TARGET].to_numpy(dtype=np.int8)

    print(f"train={train.shape}, test={test.shape}, encoded_features={x_train.shape[1]}")
    print(f"positive_rate={y.mean():.6f}")

    splitter = StratifiedKFold(
        n_splits=N_FOLDS, shuffle=True, random_state=SEED
    )
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    importance_frames: list[pd.DataFrame] = []

    for fold, (train_idx, valid_idx) in enumerate(
        splitter.split(x_train, y), start=1
    ):
        fold_start = time.time()
        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            x_train.iloc[train_idx],
            y[train_idx],
            eval_set=[(x_train.iloc[valid_idx], y[valid_idx])],
            eval_metric="auc",
            callbacks=[lgb.log_evaluation(period=0)],
        )

        valid_pred = model.predict_proba(x_train.iloc[valid_idx])[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(x_test)[:, 1] / N_FOLDS

        fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(fold_auc)
        importance_frames.append(
            pd.DataFrame(
                {
                    "feature": x_train.columns,
                    "gain": model.booster_.feature_importance(importance_type="gain"),
                    "fold": fold,
                }
            )
        )
        print(
            f"fold={fold} auc={fold_auc:.6f} "
            f"elapsed={time.time() - fold_start:.1f}s"
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    print(f"OOF AUC={oof_auc:.6f}")

    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)

    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    importance = pd.concat(importance_frames, ignore_index=True)
    importance_summary = (
        importance.groupby("feature", as_index=False)
        .agg(gain_mean=("gain", "mean"), gain_std=("gain", "std"))
        .sort_values("gain_mean", ascending=False)
    )
    importance_summary.to_csv(OUT_DIR / "feature_importance.csv", index=False)

    results = {
        "competition": "playground-series-s6e8",
        "model": "LightGBM raw-feature baseline",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "train_shape": list(train.shape),
        "test_shape": list(test.shape),
        "encoded_feature_count": int(x_train.shape[1]),
        "fold_auc": fold_scores,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "oof_auc": oof_auc,
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "lightgbm_version": lgb.__version__,
        "params": LGB_PARAMS,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"submission={OUT_DIR / 'submission.csv'}")
    print(f"elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
