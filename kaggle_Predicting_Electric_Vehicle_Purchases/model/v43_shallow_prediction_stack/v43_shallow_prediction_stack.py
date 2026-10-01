# -*- coding: utf-8 -*-
"""v43：用极浅 LightGBM 学习多模型预测之间的条件融合。"""

from __future__ import annotations

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 917
TARGET = "Will_Buy_EV"
ID_COL = "id"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
PUBLIC_DIR = MODEL_DIR / "v7_cv_public_blend" / "public_inputs"

LOCAL_MEMBERS = (
    "v31_income_bin10_te_lgbm_10f_seed2026",
    "v32_income_bin10_te_lgbm_10f_seed3407",
    "v36_income_bin10_te_lgbm_10f_fullseed2718",
    "v28_multiscale_te_lgbm_20f",
    "v11_mlp_te_10f",
    "v10_catboost_bag_10f",
)

PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "n_estimators": 4000,
    "learning_rate": 0.01,
    "max_depth": 3,
    "num_leaves": 7,
    "min_child_samples": 5000,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "reg_alpha": 2.0,
    "reg_lambda": 10.0,
    "max_bin": 127,
    "random_state": SEED,
    "deterministic": True,
    "force_col_wise": True,
    "n_jobs": 8,
    "verbosity": -1,
}


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def main() -> None:
    start = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == "Yes").to_numpy(np.int8)

    oof_columns: list[np.ndarray] = []
    test_columns: list[np.ndarray] = []
    feature_names: list[str] = []
    for name in LOCAL_MEMBERS:
        oof_columns.append(percentile_rank(np.load(MODEL_DIR / name / "oof_proba.npy")))
        test_columns.append(percentile_rank(np.load(MODEL_DIR / name / "test_proba.npy")))
        feature_names.append(name)

    public_oof = pd.read_parquet(PUBLIC_DIR / "OOF_Preds.parquet")
    public_test = pd.read_parquet(PUBLIC_DIR / "Mdl_Preds.parquet")
    for name in public_oof.columns:
        oof_columns.append(percentile_rank(public_oof[name].to_numpy()))
        test_columns.append(percentile_rank(public_test[name].to_numpy()))
        feature_names.append(f"public_{name}")

    x = np.column_stack(oof_columns).astype(np.float32)
    x_test = np.column_stack(test_columns).astype(np.float32)
    print(f"stack train={x.shape}, test={x_test.shape}", flush=True)

    folds = list(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
    )
    oof = np.zeros(len(y), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_rows: list[dict] = []
    importances: list[np.ndarray] = []
    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
        model = lgb.LGBMClassifier(**PARAMS)
        model.fit(
            x[fit_idx],
            y[fit_idx],
            eval_set=[(x[valid_idx], y[valid_idx])],
            eval_metric="auc",
            feature_name=feature_names,
            callbacks=[
                lgb.early_stopping(200, verbose=False),
                lgb.log_evaluation(period=0),
            ],
        )
        best_iter = int(model.best_iteration_ or PARAMS["n_estimators"])
        valid_pred = model.predict_proba(x[valid_idx], num_iteration=best_iter)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(x_test, num_iteration=best_iter)[:, 1] / 5
        fold_rows.append(
            {
                "fold": fold,
                "auc": float(roc_auc_score(y[valid_idx], valid_pred)),
                "best_iteration": best_iter,
            }
        )
        importances.append(model.booster_.feature_importance(importance_type="gain"))
        print(f"fold={fold} {fold_rows[-1]}", flush=True)

    oof_auc = float(roc_auc_score(y, oof))
    submission = sample.copy()
    submission[TARGET] = test_pred
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 顺序异常")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    mean_importance = np.mean(importances, axis=0)
    importance = dict(
        sorted(
            zip(feature_names, mean_importance.tolist()),
            key=lambda item: item[1],
            reverse=True,
        )
    )
    result = {
        "competition": "playground-series-s6e9",
        "model": "strongly regularized depth-3 prediction stack",
        "seed": SEED,
        "features": feature_names,
        "fold_results": fold_rows,
        "oof_auc": oof_auc,
        "importance_gain_mean": importance,
        "elapsed_seconds": time.time() - start,
        "params": PARAMS,
        "validation_warning": (
            "base OOF vectors are row-wise leak-free, but meta-CV is not a fully "
            "nested regeneration of every base learner; require stable fold gains"
        ),
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
