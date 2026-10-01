# -*- coding: utf-8 -*-
"""v68：单折复现 Naji 公共配方，并检验 4 倍学习率的无损加速。"""

from __future__ import annotations

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder


SEED = 42
OUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUT_DIR.parents[1] / "data"
ORIGINAL_DATA = DATA_DIR / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv"
PUBLIC_OOF = (
    OUT_DIR.parent
    / "v64_robust_40f_generator_ensemble"
    / "public_inputs"
    / "oof_LIGHTGBM.csv"
)
V52_OOF = OUT_DIR.parent / "v52_robust_rank_ensemble_v51" / "oof_proba.npy"
TARGET = "Will_Buy_EV"


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def build_features(
    extra_income_bins: tuple[int, ...] = (),
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, list[str]]:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    original = pd.read_csv(ORIGINAL_DATA)
    train[TARGET] = train[TARGET].map({"Yes": 1, "No": 0})
    original[TARGET] = original[TARGET].map({"Yes": 1, "No": 0})

    train["is_train"] = 1
    test["is_train"] = 0
    test[TARGET] = np.nan
    combined = pd.concat([train, test], ignore_index=True)
    combined.drop(columns=["Number_of_Cars_Owned"], inplace=True, errors="ignore")

    cat_cols = combined.select_dtypes(include=["object", "string"]).columns.tolist()
    num_cols = [
        col
        for col in combined.columns
        if col not in cat_cols + ["id", "is_train", TARGET]
    ]
    digit_features: list[str] = []
    for col in list(num_cols):
        values = combined[col].fillna(0)
        for power in range(-4, 4):
            name = f"{col}_digit{power}"
            combined[name] = (values // (10**power) % 10).astype("int8")
            digit_features.append(name)
    num_cols.extend(digit_features)

    original_mean = float(original[TARGET].mean())
    for col in cat_cols + num_cols:
        if col in original.columns:
            mapping = original.groupby(col, observed=False)[TARGET].mean()
            combined[f"{col}_org_mean"] = (
                combined[col].map(mapping).fillna(original_mean).astype(float)
            )

    num_to_cat_cols: list[str] = []
    for col in num_cols:
        name = f"{col}_cat"
        combined[name] = combined[col].fillna("NaN").astype(str)
        num_to_cat_cols.append(name)
    for width in extra_income_bins:
        name = f"Annual_Income_USD_bin{width}_cat"
        combined[name] = (
            (combined["Annual_Income_USD"] // width).astype(np.int64).astype(str)
        )
        num_to_cat_cols.append(name)
    all_cats = cat_cols + num_to_cat_cols
    for col in all_cats:
        frequency = combined[col].value_counts(normalize=True)
        combined[f"{col}_fe"] = combined[col].map(frequency).fillna(0.0).astype(float)

    combined["is_30k_spike"] = (combined["Annual_Income_USD"] == 30_000.0).astype("int8")
    combined["is_millionaire_cliff"] = (combined["Annual_Income_USD"] >= 170_537.0).astype("int8")
    combined["is_dead_zone"] = (
        combined["Annual_Income_USD"].between(38_000.0, 42_000.0)
    ).astype("int8")
    combined["is_env_hater"] = (
        combined["Environmental_Concern_Level"] == 1
    ).astype("int8")

    train_frame = combined[combined["is_train"] == 1].drop(columns=["is_train"])
    test_frame = combined[combined["is_train"] == 0].drop(
        columns=["is_train", TARGET]
    )
    eval_cols = [
        col
        for col in train_frame.columns
        if col not in ["id", TARGET]
        and pd.api.types.is_numeric_dtype(train_frame[col])
    ]
    corr = train_frame[eval_cols].corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    drop_corr = [col for col in upper if (upper[col] == 1.0).any()]
    drop_const = [col for col in train_frame if train_frame[col].nunique() == 1]
    drop_const += [col for col in test_frame if test_frame[col].nunique() == 1]
    drop = sorted(set(drop_corr).union(drop_const) - {"id", TARGET})
    train_frame = train_frame.drop(columns=drop, errors="ignore")
    test_frame = test_frame.drop(columns=drop, errors="ignore")
    target_encode_cols = [col for col in all_cats if col not in drop]
    features = [col for col in test_frame if col != "id"]
    return train_frame[features], train_frame[TARGET].astype(np.int8), test_frame[features], target_encode_cols


def main() -> None:
    start = time.time()
    x, y, _x_test, target_encode_cols = build_features()
    fit_idx, valid_idx = next(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
    )
    x_fit = x.iloc[fit_idx].copy()
    x_valid = x.iloc[valid_idx].copy()
    y_fit = y.iloc[fit_idx]
    y_valid = y.iloc[valid_idx]
    print(
        f"static={x.shape} te_cols={len(target_encode_cols)} fit={len(fit_idx)} "
        f"valid={len(valid_idx)}",
        flush=True,
    )

    for tag, smooth in (("auto", "auto"), ("10", 10.0)):
        encoder = TargetEncoder(shuffle=True, cv=5, smooth=smooth, random_state=SEED)
        fit_encoded = encoder.fit_transform(x_fit[target_encode_cols], y_fit)
        valid_encoded = encoder.transform(x_valid[target_encode_cols])
        for column_idx, col in enumerate(target_encode_cols):
            x_fit[f"{col}_TE_{tag}"] = fit_encoded[:, column_idx].astype("float32")
            x_valid[f"{col}_TE_{tag}"] = valid_encoded[:, column_idx].astype("float32")
        print(f"target_encoder={tag} elapsed={time.time() - start:.1f}s", flush=True)
    x_fit = x_fit.drop(columns=target_encode_cols)
    x_valid = x_valid.drop(columns=target_encode_cols)

    params = {
        "n_estimators": 12_000,
        "learning_rate": 0.02,
        "max_depth": 5,
        "num_leaves": 32,
        "min_child_samples": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.3,
        "reg_alpha": 0.071,
        "reg_lambda": 2.0,
        "max_bin": 1024,
        "random_state": SEED,
        "feature_pre_filter": False,
        "metric": "auc",
        "n_jobs": 8,
        "verbosity": -1,
    }
    model = lgb.LGBMClassifier(**params)
    model.fit(
        x_fit,
        y_fit,
        eval_set=[(x_valid, y_valid)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=350, verbose=False),
            lgb.log_evaluation(period=500),
        ],
    )
    pred = model.predict_proba(x_valid)[:, 1]
    auc = float(roc_auc_score(y_valid, pred))
    public_oof = pd.read_csv(PUBLIC_OOF)["OOF_Pred"].to_numpy()[valid_idx]
    public_auc = float(roc_auc_score(y_valid, public_oof))
    v52 = np.load(V52_OOF)[valid_idx]
    v52_auc = float(roc_auc_score(y_valid, v52))
    rank_pred = percentile_rank(pred)
    rank_v52 = percentile_rank(v52)
    blend_rows = []
    for weight in np.linspace(0.0, 0.3, 61):
        blend_auc = float(
            roc_auc_score(y_valid, (1.0 - weight) * rank_v52 + weight * rank_pred)
        )
        blend_rows.append(
            {"weight": float(weight), "auc": blend_auc, "delta": blend_auc - v52_auc}
        )
    result = {
        "competition": "playground-series-s6e9",
        "model": "Naji public LightGBM recipe at 4x learning rate, one-fold probe",
        "fold": 1,
        "seed": SEED,
        "auc": auc,
        "public_naji_auc": public_auc,
        "delta_vs_public_naji": auc - public_auc,
        "v52_auc": v52_auc,
        "best_v52_blend": max(blend_rows, key=lambda row: row["auc"]),
        "spearman_vs_public_naji": float(spearmanr(pred, public_oof).statistic),
        "spearman_vs_v52": float(spearmanr(pred, v52).statistic),
        "best_iteration": int(model.best_iteration_),
        "feature_count": int(x_fit.shape[1]),
        "target_encode_column_count": len(target_encode_cols),
        "params": params,
        "decision_rule": (
            "promote to 20 folds only if accelerated fold quality is not materially "
            "below the public recipe and retains positive blend value"
        ),
        "elapsed_seconds": time.time() - start,
    }
    np.save(OUT_DIR / "fold1_valid_idx.npy", valid_idx)
    np.save(OUT_DIR / "fold1_valid_proba.npy", pred)
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
