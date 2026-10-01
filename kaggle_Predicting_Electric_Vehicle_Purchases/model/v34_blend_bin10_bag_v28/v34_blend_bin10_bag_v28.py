# -*- coding: utf-8 -*-
"""v34：用两个 10 折收入-bin10 种子 bag 替换 v16 的 v14，再融合 20 折 v28。"""

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
GRID = np.arange(0.0, 0.6001, 0.02)
TARGET = "Will_Buy_EV"
ID_COL = "id"
BIN10_MEMBERS = (
    "v31_income_bin10_te_lgbm_10f_seed2026",
    "v32_income_bin10_te_lgbm_10f_seed3407",
)

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

    bin10_oof = np.mean(
        [pct_rank(np.load(MODEL_DIR / name / "oof_proba.npy")) for name in BIN10_MEMBERS],
        axis=0,
    )
    bin10_test = np.mean(
        [pct_rank(np.load(MODEL_DIR / name / "test_proba.npy")) for name in BIN10_MEMBERS],
        axis=0,
    )
    v28_oof = pct_rank(
        np.load(MODEL_DIR / "v28_multiscale_te_lgbm_20f" / "oof_proba.npy")
    )
    v28_test = pct_rank(
        np.load(MODEL_DIR / "v28_multiscale_te_lgbm_20f" / "test_proba.npy")
    )

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
    public_test = pd.read_parquet(PUBLIC_DIR / "Mdl_Preds.parquet")
    mlp_oof = pct_rank(np.load(MODEL_DIR / names[3] / "oof_proba.npy"))
    mlp_test = pct_rank(np.load(MODEL_DIR / names[3] / "test_proba.npy"))
    base_oof = np.column_stack(
        [
            bin10_oof,
            pct_rank(public_oof["V3"].to_numpy()),
            pct_rank(public_oof["V4"].to_numpy()),
            mlp_oof,
        ]
    ) @ weights
    base_test = np.column_stack(
        [
            bin10_test,
            pct_rank(public_test["V3"].to_numpy()),
            pct_rank(public_test["V4"].to_numpy()),
            mlp_test,
        ]
    ) @ weights

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
                (1.0 - weight) * base_oof[fit_idx] + weight * v28_oof[fit_idx],
            )
            for weight in GRID
        ]
        weight = float(GRID[int(np.argmax(scores))])
        learned_weights.append(weight)
        crossfit_oof[valid_idx] = (
            (1.0 - weight) * base_oof[valid_idx] + weight * v28_oof[valid_idx]
        )
        valid_auc = float(roc_auc_score(y[valid_idx], crossfit_oof[valid_idx]))
        base_auc = float(roc_auc_score(y[valid_idx], base_oof[valid_idx]))
        fold_rows.append(
            {
                "fold": fold,
                "weight_v28": weight,
                "valid_auc": valid_auc,
                "base_auc": base_auc,
                "delta_vs_base": valid_auc - base_auc,
            }
        )

    final_weight = float(np.mean(learned_weights))
    fixed_oof = (1.0 - final_weight) * base_oof + final_weight * v28_oof
    test_pred = (1.0 - final_weight) * base_test + final_weight * v28_test
    crossfit_auc = float(roc_auc_score(y, crossfit_oof))
    fixed_auc = float(roc_auc_score(y, fixed_oof))
    base_auc = float(roc_auc_score(y, base_oof))

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
        "model": "v16 public/MLP weights with two-seed bin10 bag, then v28 blend",
        "bin10_members": BIN10_MEMBERS,
        "fold_results": fold_rows,
        "learned_weights_v28": learned_weights,
        "final_weight_v28": final_weight,
        "bin10_bag_oof_auc": float(roc_auc_score(y, bin10_oof)),
        "base_oof_auc": base_auc,
        "v28_oof_auc": float(roc_auc_score(y, v28_oof)),
        "crossfit_oof_auc": crossfit_auc,
        "fixed_weight_oof_auc": fixed_auc,
        "folds_won_vs_base": sum(row["delta_vs_base"] > 0 for row in fold_rows),
        "base_v28_test_spearman": float(spearmanr(base_test, v28_test).statistic),
        "grid_step": 0.02,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
