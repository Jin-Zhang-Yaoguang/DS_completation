# -*- coding: utf-8 -*-
"""v30：把 20 折 v28 作为折叠粒度不同的新成员加入 v16 的固定权重秩融合。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
GRID = np.arange(0.0, 1.0001, 0.02)
TARGET = "Will_Buy_EV"
ID_COL = "id"

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
PUBLIC_DIR = MODEL_DIR / "v7_cv_public_blend" / "public_inputs"


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == "Yes").to_numpy(np.int8)

    v16_results = json.loads(
        (MODEL_DIR / "v16_blend_v14_public_mlp" / "cv_results.json").read_text(
            encoding="utf-8"
        )
    )
    names = v16_results["members"]
    weights = np.array(
        [v16_results["final_weights"][name] for name in names], dtype=np.float64
    )
    public_oof = pd.read_parquet(PUBLIC_DIR / "OOF_Preds.parquet")
    raw_oof = {
        names[0]: np.load(MODEL_DIR / names[0] / "oof_proba.npy"),
        names[1]: public_oof["V3"].to_numpy(np.float64),
        names[2]: public_oof["V4"].to_numpy(np.float64),
        names[3]: np.load(MODEL_DIR / names[3] / "oof_proba.npy"),
    }
    v16_fixed_oof = np.column_stack(
        [pct_rank(raw_oof[name]) for name in names]
    ) @ weights
    v16_test = np.load(MODEL_DIR / "v16_blend_v14_public_mlp" / "test_proba.npy")
    v28_oof = pct_rank(
        np.load(MODEL_DIR / "v28_multiscale_te_lgbm_20f" / "oof_proba.npy")
    )
    v28_test = pct_rank(
        np.load(MODEL_DIR / "v28_multiscale_te_lgbm_20f" / "test_proba.npy")
    )

    folds = list(
        StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(
            np.zeros(len(y)), y
        )
    )
    crossfit_oof = np.zeros(len(y), dtype=np.float64)
    learned_weights: list[float] = []
    fold_rows: list[dict] = []
    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
        scores = [
            roc_auc_score(
                y[fit_idx],
                (1.0 - weight) * v16_fixed_oof[fit_idx] + weight * v28_oof[fit_idx],
            )
            for weight in GRID
        ]
        weight = float(GRID[int(np.argmax(scores))])
        learned_weights.append(weight)
        crossfit_oof[valid_idx] = (
            (1.0 - weight) * v16_fixed_oof[valid_idx] + weight * v28_oof[valid_idx]
        )
        valid_auc = float(roc_auc_score(y[valid_idx], crossfit_oof[valid_idx]))
        base_auc = float(roc_auc_score(y[valid_idx], v16_fixed_oof[valid_idx]))
        fold_rows.append(
            {
                "fold": fold,
                "weight_v28": weight,
                "valid_auc": valid_auc,
                "v16_fixed_auc": base_auc,
                "delta_vs_v16": valid_auc - base_auc,
            }
        )

    final_weight = float(np.mean(learned_weights))
    fixed_oof = (1.0 - final_weight) * v16_fixed_oof + final_weight * v28_oof
    test_pred = (1.0 - final_weight) * v16_test + final_weight * v28_test
    crossfit_auc = float(roc_auc_score(y, crossfit_oof))
    fixed_auc = float(roc_auc_score(y, fixed_oof))
    base_auc = float(roc_auc_score(y, v16_fixed_oof))

    submission = sample.copy()
    submission[TARGET] = test_pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交格式异常")
    if not np.isfinite(test_pred).all() or ((test_pred < 0) | (test_pred > 1)).any():
        raise ValueError("提交概率非法")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", crossfit_oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    results = {
        "competition": "playground-series-s6e9",
        "model": "cross-fitted blend of v16 fixed ensemble and 20-fold v28",
        "fold_results": fold_rows,
        "learned_weights_v28": learned_weights,
        "final_weight_v28": final_weight,
        "v16_fixed_oof_auc": base_auc,
        "v28_oof_auc": float(roc_auc_score(y, v28_oof)),
        "crossfit_oof_auc": crossfit_auc,
        "fixed_weight_oof_auc": fixed_auc,
        "oof_delta_vs_v16": crossfit_auc - base_auc,
        "folds_won_vs_v16": sum(row["delta_vs_v16"] > 0 for row in fold_rows),
        "v16_v28_oof_spearman": float(spearmanr(v16_fixed_oof, v28_oof).statistic),
        "v16_v28_test_spearman": float(spearmanr(v16_test, v28_test).statistic),
        "grid_step": 0.02,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
