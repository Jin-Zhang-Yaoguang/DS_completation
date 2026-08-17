# -*- coding: utf-8 -*-
"""v6：高分辨率 LightGBM + 严格折外层级编码。"""

import json
import sys
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
V3_RESULTS = OUT_DIR.parent / "v3_dual_catboost" / "cv_results.json"
V5_MODULE_DIR = OUT_DIR.parent / "v5_hierarchical_lookup"
sys.path.insert(0, str(V5_MODULE_DIR))
from v5_hierarchical_lookup import add_budget_features, make_fold_features  # noqa: E402


CAT_COLS = ["gender", "stress_level", "academic_work_impact"]
LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "n_estimators": 3000,
    "learning_rate": 0.025,
    "num_leaves": 63,
    "max_depth": -1,
    "max_bin": 1023,
    "min_data_in_bin": 10,
    "min_child_samples": 100,
    "subsample": 0.9,
    "subsample_freq": 1,
    "colsample_bytree": 0.9,
    "reg_alpha": 0.1,
    "reg_lambda": 2.0,
    "random_state": SEED,
    "bagging_seed": SEED,
    "feature_fraction_seed": SEED,
    "data_random_seed": SEED,
    "deterministic": True,
    "force_col_wise": True,
    "n_jobs": -1,
    "verbosity": -1,
}


def build_base(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_base = add_budget_features(train.drop(columns=[TARGET, ID_COL]))
    test_base = add_budget_features(test.drop(columns=[ID_COL]))
    combined = pd.concat([train_base, test_base], ignore_index=True)
    combined = pd.get_dummies(combined, columns=CAT_COLS, dummy_na=True, dtype=np.float32)
    combined = combined.astype(np.float32)
    return combined.iloc[: len(train)].reset_index(drop=True), combined.iloc[len(train) :].reset_index(drop=True)


def validate_submission(submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame) -> None:
    if submission.shape != sample.shape or list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError("提交结构错误")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与测试集不一致")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率非法")


def main() -> None:
    start = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    raw_cols = [c for c in test.columns if c != ID_COL]
    y = train[TARGET].to_numpy(dtype=np.int8)
    base_train, base_test = build_base(train, test)
    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    importance_frames: list[pd.DataFrame] = []

    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(train, y), start=1):
        fold_start = time.time()
        fit_frame = train.iloc[fit_idx].reset_index(drop=True)
        valid_frame = train.iloc[valid_idx].reset_index(drop=True)
        y_fit = y[fit_idx]
        te_fit_array, (te_valid_array, te_test_array), te_names = make_fold_features(
            fit_frame,
            [valid_frame, test.reset_index(drop=True)],
            y_fit,
            raw_cols,
        )
        # v6 只消费层级编码的前三列/字段；末尾连续基础特征由自身高分辨率矩阵提供。
        n_te_features = 3 * len(raw_cols)
        te_names = te_names[:n_te_features]
        te_fit = pd.DataFrame(te_fit_array[:, :n_te_features], columns=te_names)
        te_valid = pd.DataFrame(te_valid_array[:, :n_te_features], columns=te_names)
        te_test = pd.DataFrame(te_test_array[:, :n_te_features], columns=te_names)
        x_fit = pd.concat([base_train.iloc[fit_idx].reset_index(drop=True), te_fit], axis=1)
        x_valid = pd.concat([base_train.iloc[valid_idx].reset_index(drop=True), te_valid], axis=1)
        x_test = pd.concat([base_test, te_test], axis=1)
        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            x_fit,
            y_fit,
            eval_set=[(x_valid, y[valid_idx])],
            eval_metric="auc",
            callbacks=[lgb.early_stopping(150, verbose=False), lgb.log_evaluation(200)],
        )
        valid_pred = model.predict_proba(x_valid, num_iteration=model.best_iteration_)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(x_test, num_iteration=model.best_iteration_)[:, 1] / N_FOLDS
        score = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(score)
        best_iterations.append(int(model.best_iteration_))
        importance_frames.append(pd.DataFrame({
            "feature": x_fit.columns,
            "gain": model.booster_.feature_importance(importance_type="gain"),
            "fold": fold,
        }))
        print(f"fold={fold} auc={score:.6f} best_iteration={model.best_iteration_} elapsed={time.time()-fold_start:.1f}s")

    oof_auc = float(roc_auc_score(y, oof))
    v3 = json.loads(V3_RESULTS.read_text(encoding="utf-8"))
    fold_deltas = np.asarray(fold_scores) - np.asarray(v3["fold_auc"], dtype=float)
    elapsed = time.time() - start
    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    importance = pd.concat(importance_frames, ignore_index=True)
    importance.groupby("feature", as_index=False).agg(
        gain_mean=("gain", "mean"), gain_std=("gain", "std")
    ).sort_values("gain_mean", ascending=False).to_csv(OUT_DIR / "feature_importance.csv", index=False)
    results = {
        "competition": "playground-series-s6e8",
        "model": "high-resolution LightGBM with fold-safe hierarchical encodings",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "feature_count": int(x_fit.shape[1]),
        "fold_auc": fold_scores,
        "best_iterations": best_iterations,
        "oof_auc": oof_auc,
        "v3_oof_auc": float(v3["oof_auc"]),
        "oof_delta_vs_v3": oof_auc - float(v3["oof_auc"]),
        "fold_delta_vs_v3": fold_deltas.tolist(),
        "folds_won_vs_v3": int((fold_deltas > 0).sum()),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "lightgbm_version": lgb.__version__,
        "params": LGB_PARAMS,
    }
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
