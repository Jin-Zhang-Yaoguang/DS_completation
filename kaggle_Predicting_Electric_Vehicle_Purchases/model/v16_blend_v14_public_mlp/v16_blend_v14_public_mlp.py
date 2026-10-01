# -*- coding: utf-8 -*-
"""v16：10 折多尺度 TE LightGBM、MLP 与两个公开 OOF 模型的严格折外秩融合。"""

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
GRID_STEP = 0.02
TARGET = "Will_Buy_EV"
ID_COL = "id"

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
PUBLIC_DIR = MODEL_DIR / "v7_cv_public_blend" / "public_inputs"
MEMBERS = (
    "v14_multiscale_te_lgbm_10f",
    "public_unified_v3",
    "public_kirill_v4",
    "v11_mlp_te_10f",
)


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def hill_climb(matrix: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    single_auc = [roc_auc_score(y, matrix[:, i]) for i in range(matrix.shape[1])]
    weights = np.zeros(matrix.shape[1], dtype=np.float64)
    weights[int(np.argmax(single_auc))] = 1.0
    best_auc = float(max(single_auc))
    for _ in range(300):
        improved = False
        for idx in range(matrix.shape[1]):
            candidate = weights.copy()
            candidate[idx] += GRID_STEP
            candidate /= candidate.sum()
            candidate_auc = float(roc_auc_score(y, matrix @ candidate))
            if candidate_auc > best_auc + 1e-10:
                weights = candidate
                best_auc = candidate_auc
                improved = True
        if not improved:
            break
    return weights, best_auc


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == "Yes").to_numpy(np.int8)

    public_oof = pd.read_parquet(PUBLIC_DIR / "OOF_Preds.parquet")
    public_test = pd.read_parquet(PUBLIC_DIR / "Mdl_Preds.parquet")
    raw_oof = {
        MEMBERS[0]: np.load(MODEL_DIR / MEMBERS[0] / "oof_proba.npy"),
        MEMBERS[1]: public_oof["V3"].to_numpy(np.float64),
        MEMBERS[2]: public_oof["V4"].to_numpy(np.float64),
        MEMBERS[3]: np.load(MODEL_DIR / MEMBERS[3] / "oof_proba.npy"),
    }
    raw_test = {
        MEMBERS[0]: np.load(MODEL_DIR / MEMBERS[0] / "test_proba.npy"),
        MEMBERS[1]: public_test["V3"].to_numpy(np.float64),
        MEMBERS[2]: public_test["V4"].to_numpy(np.float64),
        MEMBERS[3]: np.load(MODEL_DIR / MEMBERS[3] / "test_proba.npy"),
    }
    for name in MEMBERS:
        if len(raw_oof[name]) != len(train) or len(raw_test[name]) != len(test):
            raise ValueError(f"{name} 的预测行数与比赛数据不一致")

    oof_matrix = np.column_stack([pct_rank(raw_oof[name]) for name in MEMBERS])
    test_matrix = np.column_stack([pct_rank(raw_test[name]) for name in MEMBERS])
    member_auc = {name: float(roc_auc_score(y, raw_oof[name])) for name in MEMBERS}
    correlations = {
        f"{MEMBERS[i]}__{MEMBERS[j]}": float(
            spearmanr(raw_oof[MEMBERS[i]], raw_oof[MEMBERS[j]]).correlation
        )
        for i in range(len(MEMBERS))
        for j in range(i + 1, len(MEMBERS))
    }

    splitter = StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED)
    crossfit_oof = np.zeros(len(y), dtype=np.float64)
    learned_weights: list[np.ndarray] = []
    fold_rows: list[dict] = []
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(oof_matrix, y), 1):
        weights, fit_auc = hill_climb(oof_matrix[fit_idx], y[fit_idx])
        learned_weights.append(weights)
        crossfit_oof[valid_idx] = oof_matrix[valid_idx] @ weights
        valid_auc = float(roc_auc_score(y[valid_idx], crossfit_oof[valid_idx]))
        base_auc = float(roc_auc_score(y[valid_idx], raw_oof[MEMBERS[0]][valid_idx]))
        fold_rows.append(
            {
                "fold": fold,
                "fit_auc": fit_auc,
                "valid_auc": valid_auc,
                "v14_auc": base_auc,
                "delta_vs_v14": valid_auc - base_auc,
                "weights": dict(zip(MEMBERS, weights.tolist())),
            }
        )
        print(
            f"fold={fold} valid={valid_auc:.9f} delta_vs_v14={valid_auc-base_auc:+.9f} "
            f"weights={dict(zip(MEMBERS, np.round(weights, 4)))}",
            flush=True,
        )

    final_weights = np.mean(learned_weights, axis=0)
    final_weights /= final_weights.sum()
    fixed_oof = oof_matrix @ final_weights
    test_pred = test_matrix @ final_weights
    crossfit_auc = float(roc_auc_score(y, crossfit_oof))
    fixed_auc = float(roc_auc_score(y, fixed_oof))
    print(f"crossfit OOF={crossfit_auc:.9f}", flush=True)
    print(f"fixed-weight OOF={fixed_auc:.9f}", flush=True)
    print(f"final_weights={dict(zip(MEMBERS, final_weights))}", flush=True)

    submission = sample.copy()
    submission[TARGET] = test_pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交格式异常")
    if not np.isfinite(test_pred).all() or ((test_pred < 0) | (test_pred > 1)).any():
        raise ValueError("提交概率非法")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", crossfit_oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    results = {
        "competition": "playground-series-s6e9",
        "model": "cross-fitted percentile-rank blend of v14, public V3/V4, and v11 MLP",
        "members": MEMBERS,
        "member_oof_auc": member_auc,
        "member_spearman": correlations,
        "fold_results": fold_rows,
        "final_weights": dict(zip(MEMBERS, final_weights.tolist())),
        "crossfit_oof_auc": crossfit_auc,
        "fixed_weight_oof_auc": fixed_auc,
        "oof_delta_vs_v14": crossfit_auc - member_auc[MEMBERS[0]],
        "folds_won_vs_v14": sum(row["delta_vs_v14"] > 0 for row in fold_rows),
        "grid_step": GRID_STEP,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
