# -*- coding: utf-8 -*-
"""
v6：多尺度目标编码 + 数字位指纹 + 浅层高分辨率 LightGBM。

核心假设：收入精确值是合成器产生的高基数身份键，但每个键的样本量差异很大。
单一 smoothing 无法同时适配高频与低频键，因此对同一键提供多个收缩尺度，让树模型
结合频次选择可信度。数字位和全局频次只使用协变量，可安全地联合 train/test 构造。

目标编码严格嵌套：外层训练折使用内层 OOF；外层验证和测试只使用外层训练标签。
"""

from __future__ import annotations

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
N_INNER = 5
TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"
SMOOTHS = (5.0, 15.0, 80.0)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent

RAW_FEATURES = [
    "Age",
    "Annual_Income_USD",
    "Daily_Commute_km",
    "Number_of_Cars_Owned",
    "Charging_Stations_Near_Home",
    "Charging_Stations_Near_Work",
    "Environmental_Concern_Level",
    "Gender",
    "City_Type",
    "Current_Car_Type",
    "Home_Charging_Possible",
    "Subsidy_Available",
    "Range_Anxiety_Level",
]
NUMERIC_FEATURES = [
    "Age",
    "Annual_Income_USD",
    "Daily_Commute_km",
    "Number_of_Cars_Owned",
    "Charging_Stations_Near_Home",
    "Charging_Stations_Near_Work",
    "Environmental_Concern_Level",
]
CATEGORICAL_FEATURES = [c for c in RAW_FEATURES if c not in NUMERIC_FEATURES]

# 原始单列多尺度 TE + 本地已验证有效的三个收入结构键。
TE_KEYS = {c: [c] for c in RAW_FEATURES}
TE_KEYS.update(
    {
        "income_bin100": ["_income_bin100"],
        "income_subsidy": ["Annual_Income_USD", "Subsidy_Available"],
        "income_env": ["Annual_Income_USD", "Environmental_Concern_Level"],
    }
)

LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "n_estimators": 12000,
    "learning_rate": 0.02,
    "max_depth": 5,
    "num_leaves": 31,
    "min_child_samples": 10,
    "subsample": 0.812763123433567,
    "subsample_freq": 1,
    "colsample_bytree": 0.3029300829885024,
    "reg_alpha": 0.07094285437903122,
    "reg_lambda": 2.0330390977032425,
    "max_bin": 1024,
    "feature_pre_filter": False,
    "random_state": SEED,
    "bagging_seed": SEED,
    "feature_fraction_seed": SEED,
    "data_random_seed": SEED,
    "deterministic": True,
    "force_col_wise": True,
    "n_jobs": 8,
    "verbosity": -1,
}
EARLY_STOPPING_ROUNDS = 500


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if TARGET not in train or TARGET in test:
        raise ValueError("训练集/测试集目标列异常")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission 与 test 的 id 不一致")
    if train.isna().any().any() or test.isna().any().any():
        raise ValueError("数据含缺失值")
    return train, test, sample


def factorize_joint(train: pd.DataFrame, test: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    parts: list[pd.Series] = []
    for col in cols:
        if col == "_income_bin100":
            values = pd.concat(
                [train["Annual_Income_USD"], test["Annual_Income_USD"]], ignore_index=True
            )
            parts.append((values // 100).astype(np.int64).astype("string"))
        else:
            parts.append(pd.concat([train[col], test[col]], ignore_index=True).astype("string"))
    if len(parts) == 1:
        key = parts[0]
    else:
        key = parts[0]
        for part in parts[1:]:
            key = key.str.cat(part, sep="|")
    codes, _ = pd.factorize(key, sort=True)
    return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)


def build_static_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, np.ndarray], dict[str, np.ndarray]]:
    combined = pd.concat([train[RAW_FEATURES], test[RAW_FEATURES]], ignore_index=True)
    static = pd.DataFrame(index=combined.index)

    for col in NUMERIC_FEATURES:
        static[col] = combined[col].astype(np.float32)
    for col in CATEGORICAL_FEATURES:
        codes, _ = pd.factorize(combined[col].astype("string"), sort=True)
        static[col] = codes.astype(np.int8)

    # 合成器指纹：保留数值各十进制位置。常量列稍后统一删除。
    for col in NUMERIC_FEATURES:
        values = combined[col].fillna(0).to_numpy(np.float64)
        for power in range(-4, 4):
            digit = np.floor(values / (10.0**power)).astype(np.int64) % 10
            static[f"{col}_digit_{power}"] = digit.astype(np.int8)

    # train+test 联合频次不使用标签，可改善身份键支持度估计。
    for col in RAW_FEATURES:
        values = combined[col].astype("string")
        freq = values.value_counts(normalize=True, dropna=False)
        static[f"freq_{col}"] = values.map(freq).astype(np.float32)

    constant = [c for c in static if static[c].nunique(dropna=False) <= 1]
    if constant:
        static = static.drop(columns=constant)
    static = static.astype(np.float32)

    keys_train: dict[str, np.ndarray] = {}
    keys_test: dict[str, np.ndarray] = {}
    for name, cols in TE_KEYS.items():
        tr_code, te_code = factorize_joint(train, test, cols)
        keys_train[name] = tr_code
        keys_test[name] = te_code
        all_code = np.concatenate([tr_code, te_code])
        count = np.bincount(all_code)
        static[f"freq_key_{name}"] = (count[all_code] / len(all_code)).astype(np.float32)

    x_train = static.iloc[: len(train)].reset_index(drop=True)
    x_test = static.iloc[len(train) :].reset_index(drop=True)
    return x_train, x_test, keys_train, keys_test


def encode_key(
    train_codes: np.ndarray,
    test_codes: np.ndarray,
    y: np.ndarray,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    inner_folds: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fit_codes = train_codes[fit_idx]
    valid_codes = train_codes[valid_idx]
    n_categories = int(max(train_codes.max(), test_codes.max())) + 1
    y_fit = y[fit_idx].astype(np.float64)
    prior = float(y_fit.mean())

    total_count = np.bincount(fit_codes, minlength=n_categories).astype(np.float64)
    total_sum = np.bincount(fit_codes, weights=y_fit, minlength=n_categories)
    fit_block = np.empty((len(fit_idx), len(SMOOTHS)), dtype=np.float32)

    for _, hold in inner_folds:
        hold_codes = fit_codes[hold]
        hold_count = np.bincount(hold_codes, minlength=n_categories).astype(np.float64)
        hold_sum = np.bincount(hold_codes, weights=y_fit[hold], minlength=n_categories)
        count = total_count - hold_count
        target_sum = total_sum - hold_sum
        for j, smooth in enumerate(SMOOTHS):
            mapping = (target_sum + smooth * prior) / (count + smooth)
            fit_block[hold, j] = mapping[hold_codes]

    valid_block = np.empty((len(valid_idx), len(SMOOTHS)), dtype=np.float32)
    test_block = np.empty((len(test_codes), len(SMOOTHS)), dtype=np.float32)
    for j, smooth in enumerate(SMOOTHS):
        mapping = (total_sum + smooth * prior) / (total_count + smooth)
        valid_block[:, j] = mapping[valid_codes]
        test_block[:, j] = mapping[test_codes]
    return fit_block, valid_block, test_block


def validate_submission(submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame) -> None:
    if submission.shape != sample.shape or list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError("提交 shape 或列名异常")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 顺序异常")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
        raise ValueError("提交概率非法")


def main() -> None:
    start = time.time()
    train, test, sample = load_data()
    y = (train[TARGET] == POS_LABEL).to_numpy(np.int8)
    x_train, x_test, keys_train, keys_test = build_static_features(train, test)
    te_names = [f"te_{key}_m{smooth:g}" for key in TE_KEYS for smooth in SMOOTHS]
    all_features = list(x_train.columns) + te_names
    print(
        f"train={train.shape}, test={test.shape}, static={x_train.shape[1]}, "
        f"te={len(te_names)}, total={len(all_features)}",
        flush=True,
    )

    splitter = StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED)
    folds = list(splitter.split(x_train, y))
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    importance_frames: list[pd.DataFrame] = []

    for fold, (fit_idx, valid_idx) in enumerate(folds, start=1):
        fold_start = time.time()
        inner = list(
            StratifiedKFold(N_INNER, shuffle=True, random_state=SEED + fold).split(
                np.zeros(len(fit_idx)), y[fit_idx]
            )
        )
        fit_te: list[np.ndarray] = []
        valid_te: list[np.ndarray] = []
        test_te: list[np.ndarray] = []
        for key in TE_KEYS:
            a, b, c = encode_key(
                keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
            )
            fit_te.append(a)
            valid_te.append(b)
            test_te.append(c)

        x_fit = np.column_stack([x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te])
        x_valid = np.column_stack([x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te])
        x_tst = np.column_stack([x_test.to_numpy(np.float32), *test_te])

        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            x_fit,
            y[fit_idx],
            eval_set=[(x_valid, y[valid_idx])],
            eval_metric="auc",
            feature_name=all_features,
            callbacks=[
                lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False),
                lgb.log_evaluation(period=0),
            ],
        )
        best_iter = int(model.best_iteration_ or LGB_PARAMS["n_estimators"])
        valid_pred = model.predict_proba(x_valid, num_iteration=best_iter)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(x_tst, num_iteration=best_iter)[:, 1] / N_FOLDS
        fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(fold_auc)
        best_iterations.append(best_iter)
        importance_frames.append(
            pd.DataFrame(
                {
                    "feature": all_features,
                    "gain": model.booster_.feature_importance(importance_type="gain"),
                    "split": model.booster_.feature_importance(importance_type="split"),
                    "fold": fold,
                }
            )
        )
        print(
            f"fold={fold} auc={fold_auc:.6f} best_iter={best_iter} "
            f"elapsed={time.time() - fold_start:.1f}s",
            flush=True,
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    print(f"OOF AUC={oof_auc:.9f}", flush=True)

    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    importance = pd.concat(importance_frames, ignore_index=True)
    importance_summary = (
        importance.groupby("feature", as_index=False)
        .agg(gain_mean=("gain", "mean"), gain_std=("gain", "std"), split_mean=("split", "mean"))
        .sort_values("gain_mean", ascending=False)
    )
    importance_summary.to_csv(OUT_DIR / "feature_importance.csv", index=False)
    print(importance_summary.head(30).to_string(index=False), flush=True)

    result = {
        "competition": "playground-series-s6e9",
        "model": "multiscale nested TE + digit/frequency fingerprints + shallow LightGBM",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "n_inner_folds": N_INNER,
        "smooths": list(SMOOTHS),
        "te_keys": TE_KEYS,
        "static_feature_count": int(x_train.shape[1]),
        "te_feature_count": len(te_names),
        "feature_count": len(all_features),
        "fold_auc": fold_scores,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iterations,
        "oof_auc": oof_auc,
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "lightgbm_version": lgb.__version__,
        "params": LGB_PARAMS,
        "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
        "public_recipe_note": "digit/frequency and multi-smoothing TE ideas cross-checked against public Kaggle kernels",
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)
    print(f"elapsed={elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
