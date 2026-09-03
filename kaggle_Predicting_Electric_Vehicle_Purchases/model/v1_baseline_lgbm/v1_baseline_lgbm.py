# -*- coding: utf-8 -*-
"""
v1 baseline：原始 13 特征 LightGBM + 5 折分层交叉验证 + 早停。

赛题：Predicting Electric Vehicle Purchases（Playground Series S6E9）
指标：ROC AUC

设计依据：
- 数据无缺失，6 个低基数分类列直接交给 LightGBM 原生 categorical 处理；
- 目标 Will_Buy_EV 为字符串 Yes/No，映射为 1/0，提交 Yes 的概率；
- id 为顺序切分标识，不进入特征；
- 不使用 target encoding、外部数据或人工提交文件，保证 OOF 无标签泄漏；
- 折内早停，记录每折最佳轮数，作为后续方案的轮数参考。
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
TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

CAT_COLS = [
    "Gender",
    "City_Type",
    "Current_Car_Type",
    "Home_Charging_Possible",
    "Subsidy_Available",
    "Range_Anxiety_Level",
]

LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "n_estimators": 4000,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "max_depth": -1,
    "min_child_samples": 50,
    "subsample": 0.9,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
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
EARLY_STOPPING_ROUNDS = 200


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读取并校验官方原始文件。"""
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
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """分类列转为统一类别集合的 category dtype，数值列保持原样。"""
    feat_cols = [c for c in test.columns if c != ID_COL]
    x_train = train[feat_cols].copy()
    x_test = test[feat_cols].copy()

    for col in CAT_COLS:
        categories = sorted(set(x_train[col].unique()) | set(x_test[col].unique()))
        dtype = pd.CategoricalDtype(categories=categories)
        x_train[col] = x_train[col].astype(dtype)
        x_test[col] = x_test[col].astype(dtype)

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
    y = (train[TARGET] == POS_LABEL).to_numpy(dtype=np.int8)

    print(f"train={train.shape}, test={test.shape}, features={x_train.shape[1]}")
    print(f"positive_rate={y.mean():.6f}")

    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iters: list[int] = []
    importance_frames: list[pd.DataFrame] = []

    for fold, (train_idx, valid_idx) in enumerate(splitter.split(x_train, y), start=1):
        fold_start = time.time()
        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            x_train.iloc[train_idx],
            y[train_idx],
            eval_set=[(x_train.iloc[valid_idx], y[valid_idx])],
            eval_metric="auc",
            categorical_feature=CAT_COLS,
            callbacks=[
                lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False),
                lgb.log_evaluation(period=0),
            ],
        )
        best_iter = int(model.best_iteration_ or LGB_PARAMS["n_estimators"])
        best_iters.append(best_iter)

        valid_pred = model.predict_proba(
            x_train.iloc[valid_idx], num_iteration=best_iter
        )[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(x_test, num_iteration=best_iter)[:, 1] / N_FOLDS

        fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(fold_auc)
        importance_frames.append(
            pd.DataFrame(
                {
                    "feature": x_train.columns,
                    "gain": model.booster_.feature_importance(importance_type="gain"),
                    "split": model.booster_.feature_importance(importance_type="split"),
                    "fold": fold,
                }
            )
        )
        print(
            f"fold={fold} auc={fold_auc:.6f} best_iter={best_iter} "
            f"elapsed={time.time() - fold_start:.1f}s"
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    print(f"OOF AUC={oof_auc:.6f}  fold_mean={np.mean(fold_scores):.6f} "
          f"fold_std={np.std(fold_scores):.6f}")

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
            gain_mean=("gain", "mean"),
            gain_std=("gain", "std"),
            split_mean=("split", "mean"),
        )
        .sort_values("gain_mean", ascending=False)
    )
    importance_summary.to_csv(OUT_DIR / "feature_importance.csv", index=False)
    print(importance_summary.to_string(index=False))

    results = {
        "competition": "playground-series-s6e9",
        "model": "LightGBM raw-feature baseline (native categorical, early stopping)",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "train_shape": list(train.shape),
        "test_shape": list(test.shape),
        "feature_count": int(x_train.shape[1]),
        "fold_auc": fold_scores,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iters,
        "oof_auc": oof_auc,
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "lightgbm_version": lgb.__version__,
        "params": LGB_PARAMS,
        "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"submission={OUT_DIR / 'submission.csv'}")
    print(f"elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
