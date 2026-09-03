# -*- coding: utf-8 -*-
"""v7：在 v3(seed=42) 基础上增加 seed=2026 的 CatBoost 袋装实验。"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


NEW_SEED = 2026
N_FOLDS = 5
TARGET = "addicted_label"
ID_COL = "id"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
V3_DIR = MODEL_DIR / "v3_dual_catboost"
sys.path.insert(0, str(V3_DIR))
from v3_dual_catboost import CAT_PARAMS, build_features  # noqa: E402


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def main() -> None:
    start = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    x_train, x_test, categorical_cols = build_features(train, test)
    y = train[TARGET].to_numpy(dtype=np.int8)
    seed42_oof = np.load(V3_DIR / "oof_proba.npy")
    seed42_test = np.load(V3_DIR / "test_proba.npy")
    new_oof = np.zeros(len(train), dtype=np.float64)
    new_test = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
    test_pool = Pool(x_test, cat_features=categorical_cols)
    params = dict(CAT_PARAMS)
    params.update({"random_seed": NEW_SEED, "verbose": 300})

    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(x_train, y), start=1):
        fold_start = time.time()
        train_pool = Pool(x_train.iloc[fit_idx], y[fit_idx], cat_features=categorical_cols)
        valid_pool = Pool(x_train.iloc[valid_idx], y[valid_idx], cat_features=categorical_cols)
        model = CatBoostClassifier(**params)
        model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
        valid_pred = model.predict_proba(valid_pool)[:, 1]
        new_oof[valid_idx] = valid_pred
        new_test += model.predict_proba(test_pool)[:, 1] / N_FOLDS
        score = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(score)
        best_iterations.append(int(model.get_best_iteration() + 1))
        np.save(OUT_DIR / "seed_2026_oof.partial.npy", new_oof)
        np.save(OUT_DIR / "seed_2026_test.partial.npy", new_test)
        print(f"fold={fold} auc={score:.6f} best_iteration={best_iterations[-1]} elapsed={time.time()-fold_start:.1f}s")

    probability_oof = 0.5 * seed42_oof + 0.5 * new_oof
    probability_test = 0.5 * seed42_test + 0.5 * new_test
    rank_oof = 0.5 * percentile_rank(seed42_oof) + 0.5 * percentile_rank(new_oof)
    rank_test = 0.5 * percentile_rank(seed42_test) + 0.5 * percentile_rank(new_test)
    probability_auc = float(roc_auc_score(y, probability_oof))
    rank_auc = float(roc_auc_score(y, rank_oof))
    if rank_auc > probability_auc:
        bag_oof, bag_test, method = rank_oof, rank_test, "rank_average"
        bag_auc = rank_auc
    else:
        bag_oof, bag_test, method = probability_oof, probability_test, "probability_average"
        bag_auc = probability_auc

    np.save(OUT_DIR / "seed_2026_oof.npy", new_oof)
    np.save(OUT_DIR / "seed_2026_test.npy", new_test)
    np.save(OUT_DIR / "oof_proba.npy", bag_oof)
    np.save(OUT_DIR / "test_proba.npy", bag_test)
    submission = sample.copy()
    submission[TARGET] = bag_test
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    v3_auc = float(roc_auc_score(y, seed42_oof))
    results = {
        "competition": "playground-series-s6e8",
        "model": "CatBoost two-seed bagging",
        "seeds": [42, NEW_SEED],
        "new_seed_fold_auc": fold_scores,
        "new_seed_best_iterations": best_iterations,
        "new_seed_oof_auc": float(roc_auc_score(y, new_oof)),
        "seed_rank_correlation": float(spearmanr(seed42_oof, new_oof).statistic),
        "v3_seed42_oof_auc": v3_auc,
        "probability_average_oof_auc": probability_auc,
        "rank_average_oof_auc": rank_auc,
        "selected_method": method,
        "oof_auc": bag_auc,
        "oof_delta_vs_v3": bag_auc - v3_auc,
        "prediction_min": float(bag_test.min()),
        "prediction_max": float(bag_test.max()),
        "prediction_mean": float(bag_test.mean()),
        "elapsed_seconds": time.time() - start,
        "params": params,
    }
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
