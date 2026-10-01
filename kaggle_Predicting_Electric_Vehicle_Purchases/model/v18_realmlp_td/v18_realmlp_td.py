# -*- coding: utf-8 -*-
"""v18：RealMLP-TD + 精确值类别 + 嵌套目标编码，支持逐折断点续跑。"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytabkit
import torch
from pytabkit import RealMLP_TD_Classifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
N_INNER = 5
TARGET = "Will_Buy_EV"
ID_COL = "id"
INCOME = "Annual_Income_USD"
TE_SMOOTH = 10.0

OUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUT_DIR.parents[1] / "data"
TE_KEYS = {
    "te_income": [INCOME],
    "te_income_bin100": ["_income_bin100"],
    "te_income_subsidy": [INCOME, "Subsidy_Available"],
    "te_income_env": [INCOME, "Environmental_Concern_Level"],
    "te_commute": ["Daily_Commute_km"],
    "te_age": ["Age"],
}
RAW_CATEGORICAL = [
    "Gender",
    "City_Type",
    "Current_Car_Type",
    "Home_Charging_Possible",
    "Subsidy_Available",
    "Range_Anxiety_Level",
]
EXACT_CATEGORICAL = [
    INCOME,
    "Daily_Commute_km",
    "Age",
    "Charging_Stations_Near_Home",
    "Charging_Stations_Near_Work",
    "Environmental_Concern_Level",
]


def key_series(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    parts: list[pd.Series] = []
    for column in columns:
        if column == "_income_bin100":
            parts.append((frame[INCOME] // 100).astype(np.int64).astype("string"))
        else:
            parts.append(frame[column].astype("string"))
    key = parts[0]
    for part in parts[1:]:
        key = key.str.cat(part, sep="|")
    return key


def smoothed_te(
    key_fit: pd.Series, y_fit: np.ndarray, key_apply: pd.Series, prior: float
) -> np.ndarray:
    stats = pd.DataFrame({"key": key_fit.to_numpy(), "y": y_fit}).groupby("key")["y"].agg(["sum", "count"])
    target_sum = key_apply.map(stats["sum"]).fillna(0.0).to_numpy()
    count = key_apply.map(stats["count"]).fillna(0.0).to_numpy()
    return (target_sum + prior * TE_SMOOTH) / (count + TE_SMOOTH)


def nested_target_encoding(
    key_fit: pd.Series,
    y_fit: np.ndarray,
    key_valid: pd.Series,
    key_test: pd.Series,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    key_fit = key_fit.reset_index(drop=True)
    prior = float(y_fit.mean())
    fit_encoded = np.zeros(len(key_fit), dtype=np.float32)
    inner = StratifiedKFold(N_INNER, shuffle=True, random_state=seed)
    for inner_fit, inner_valid in inner.split(np.zeros(len(key_fit)), y_fit):
        fit_encoded[inner_valid] = smoothed_te(
            key_fit.iloc[inner_fit], y_fit[inner_fit], key_fit.iloc[inner_valid], prior
        )
    valid_encoded = smoothed_te(key_fit, y_fit, key_valid, prior)
    test_encoded = smoothed_te(key_fit, y_fit, key_test, prior)
    return fit_encoded, valid_encoded, test_encoded


def build_target_free_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    raw_features = [c for c in test.columns if c != ID_COL]
    combined = pd.concat([train[raw_features], test[raw_features]], ignore_index=True)
    features = combined.copy()
    features["log_income"] = np.log1p(combined[INCOME]).astype(np.float32)
    features["income_mod_10"] = (combined[INCOME].astype(np.int64) % 10).astype(np.float32)
    features["income_mod_100"] = (combined[INCOME].astype(np.int64) % 100).astype(np.float32)
    features["income_bin_100"] = (combined[INCOME] // 100).astype(np.float32)
    features["income_bin_500"] = (combined[INCOME] // 500).astype(np.float32)
    commute10 = np.rint(combined["Daily_Commute_km"].to_numpy(np.float64) * 10).astype(np.int64)
    features["commute_tenth_digit"] = (commute10 % 10).astype(np.float32)
    features["commute_ones_digit"] = ((commute10 // 10) % 10).astype(np.float32)
    features["commute_tens_digit"] = ((commute10 // 100) % 10).astype(np.float32)

    for column in raw_features:
        strings = combined[column].astype("string")
        frequency = strings.value_counts(normalize=True, dropna=False)
        features[f"freq_{column}"] = strings.map(frequency).astype(np.float32)

    exact_names: list[str] = []
    for column in EXACT_CATEGORICAL:
        name = f"exact_{column}"
        features[name] = combined[column].astype("string")
        exact_names.append(name)
    for column in RAW_CATEGORICAL:
        features[column] = features[column].astype("string")
    categorical = RAW_CATEGORICAL + exact_names
    return (
        features.iloc[: len(train)].reset_index(drop=True),
        features.iloc[len(train) :].reset_index(drop=True),
        categorical,
    )


def validate_submission(submission: pd.DataFrame, test: pd.DataFrame) -> None:
    if list(submission.columns) != [ID_COL, TARGET] or len(submission) != len(test):
        raise ValueError("提交 shape 或列名异常")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 顺序异常")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
        raise ValueError("提交概率非法")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-folds", type=int, default=N_FOLDS)
    args = parser.parse_args()
    start = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == "Yes").to_numpy(np.int8)
    base_train, base_test, categorical = build_target_free_features(train, test)
    keys_train = {name: key_series(train, cols) for name, cols in TE_KEYS.items()}
    keys_test = {name: key_series(test, cols) for name, cols in TE_KEYS.items()}
    folds = list(StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(base_train, y))

    fold_rows: list[dict] = []
    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
        valid_path = OUT_DIR / f"fold_{fold}_valid.npy"
        test_path = OUT_DIR / f"fold_{fold}_test.npy"
        if valid_path.exists() and test_path.exists():
            valid_pred = np.load(valid_path)
            fold_rows.append(
                {"fold": fold, "auc": float(roc_auc_score(y[valid_idx], valid_pred)), "reused": True}
            )
            print(f"fold={fold} 已有结果，复用 AUC={fold_rows[-1]['auc']:.9f}", flush=True)
            continue
        if fold > args.max_folds:
            continue

        x_fit = base_train.iloc[fit_idx].copy()
        x_valid = base_train.iloc[valid_idx].copy()
        x_test = base_test.copy()
        for name in TE_KEYS:
            fit_te, valid_te, test_te = nested_target_encoding(
                keys_train[name].iloc[fit_idx],
                y[fit_idx],
                keys_train[name].iloc[valid_idx],
                keys_test[name],
                SEED + fold,
            )
            for block, values in ((x_fit, fit_te), (x_valid, valid_te), (x_test, test_te)):
                clipped = np.clip(values, 1e-4, 1 - 1e-4)
                block[name] = np.log(clipped / (1 - clipped)).astype(np.float32)

        model = RealMLP_TD_Classifier(
            device="mps" if torch.backends.mps.is_available() else "cpu",
            random_state=SEED + fold,
            n_cv=1,
            n_refit=0,
            n_epochs=40,
            batch_size=4096,
            predict_batch_size=65536,
            hidden_width=512,
            n_hidden_layers=3,
            use_plr_embeddings=True,
            val_metric_name="1-auc_ovr",
            use_ls=False,
            tmp_folder=OUT_DIR / "tmp",
            verbosity=2,
        )
        model.fit(
            x_fit,
            y[fit_idx],
            X_val=x_valid,
            y_val=y[valid_idx],
            cat_col_names=categorical,
        )
        valid_pred = model.predict_proba(x_valid)[:, 1]
        test_pred = model.predict_proba(x_test)[:, 1]
        auc = float(roc_auc_score(y[valid_idx], valid_pred))
        np.save(valid_path, valid_pred)
        np.save(test_path, test_pred)
        fold_rows.append({"fold": fold, "auc": auc, "reused": False})
        print(f"fold={fold} AUC={auc:.9f} elapsed={time.time()-start:.1f}s", flush=True)

    completed = [fold for fold in range(1, N_FOLDS + 1) if (OUT_DIR / f"fold_{fold}_valid.npy").exists()]
    partial = {
        "competition": "playground-series-s6e9",
        "model": "RealMLP-TD with exact-value categorical views and nested target encoding",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "completed_folds": completed,
        "fold_results": fold_rows,
        "te_keys": TE_KEYS,
        "categorical_features": categorical,
        "pytabkit_version": getattr(pytabkit, "__version__", "unknown"),
        "torch_version": torch.__version__,
        "device": "mps" if torch.backends.mps.is_available() else "cpu",
        "hyperparameters": {
            "n_epochs": 40,
            "batch_size": 4096,
            "hidden_width": 512,
            "n_hidden_layers": 3,
            "use_plr_embeddings": True,
            "use_ls": False,
        },
        "elapsed_seconds_this_run": time.time() - start,
    }
    (OUT_DIR / "progress.json").write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    if len(completed) != N_FOLDS:
        print(f"当前完成 {len(completed)}/{N_FOLDS} 折；未生成提交。", flush=True)
        return

    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_auc: list[float] = []
    for fold, (_, valid_idx) in enumerate(folds, 1):
        valid_pred = np.load(OUT_DIR / f"fold_{fold}_valid.npy")
        oof[valid_idx] = valid_pred
        test_pred += np.load(OUT_DIR / f"fold_{fold}_test.npy") / N_FOLDS
        fold_auc.append(float(roc_auc_score(y[valid_idx], valid_pred)))
    oof_auc = float(roc_auc_score(y, oof))
    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    partial.update(
        {
            "fold_auc": fold_auc,
            "fold_auc_mean": float(np.mean(fold_auc)),
            "fold_auc_std": float(np.std(fold_auc)),
            "oof_auc": oof_auc,
            "prediction_min": float(test_pred.min()),
            "prediction_max": float(test_pred.max()),
            "prediction_mean": float(test_pred.mean()),
        }
    )
    (OUT_DIR / "cv_results.json").write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OOF AUC={oof_auc:.9f}", flush=True)
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
