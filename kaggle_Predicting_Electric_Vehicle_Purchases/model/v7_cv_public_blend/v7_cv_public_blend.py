# -*- coding: utf-8 -*-
"""v7：v6 与两个可核验公开 OOF 模型的严格折外秩融合。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
TARGET = "Will_Buy_EV"
ID_COL = "id"
GRID_STEP = 0.02

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
PUBLIC_DIR = OUT_DIR / "public_inputs"
MEMBERS = ("v6_multiscale_te_lgbm", "public_unified_v3", "public_kirill_v4")


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def hill_climb(matrix: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    single = [roc_auc_score(y, matrix[:, j]) for j in range(matrix.shape[1])]
    weights = np.zeros(matrix.shape[1], dtype=np.float64)
    weights[int(np.argmax(single))] = 1.0
    best = float(max(single))
    for _ in range(300):
        improved = False
        for j in range(matrix.shape[1]):
            candidate = weights.copy()
            candidate[j] += GRID_STEP
            candidate /= candidate.sum()
            score = float(roc_auc_score(y, matrix @ candidate))
            if score > best + 1e-10:
                weights, best, improved = candidate, score, True
        if not improved:
            break
    return weights, best


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == "Yes").to_numpy(np.int8)

    public_oof = pd.read_parquet(PUBLIC_DIR / "OOF_Preds.parquet")
    public_test = pd.read_parquet(PUBLIC_DIR / "Mdl_Preds.parquet")
    if len(public_oof) != len(train) or len(public_test) != len(test):
        raise ValueError("公开预测文件的行数与比赛数据不一致")

    raw_oof = {
        MEMBERS[0]: np.load(MODEL_DIR / MEMBERS[0] / "oof_proba.npy"),
        MEMBERS[1]: public_oof["V3"].to_numpy(np.float64),
        MEMBERS[2]: public_oof["V4"].to_numpy(np.float64),
    }
    raw_test = {
        MEMBERS[0]: np.load(MODEL_DIR / MEMBERS[0] / "test_proba.npy"),
        MEMBERS[1]: public_test["V3"].to_numpy(np.float64),
        MEMBERS[2]: public_test["V4"].to_numpy(np.float64),
    }
    oof_matrix = np.column_stack([pct_rank(raw_oof[name]) for name in MEMBERS])
    test_matrix = np.column_stack([pct_rank(raw_test[name]) for name in MEMBERS])

    splitter = StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED)
    crossfit_oof = np.zeros(len(y), dtype=np.float64)
    fold_rows: list[dict] = []
    learned_weights: list[np.ndarray] = []
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(oof_matrix, y), start=1):
        weights, fit_auc = hill_climb(oof_matrix[fit_idx], y[fit_idx])
        learned_weights.append(weights)
        crossfit_oof[valid_idx] = oof_matrix[valid_idx] @ weights
        valid_auc = float(roc_auc_score(y[valid_idx], crossfit_oof[valid_idx]))
        v6_auc = float(roc_auc_score(y[valid_idx], raw_oof[MEMBERS[0]][valid_idx]))
        row = {
            "fold": fold,
            "fit_auc": fit_auc,
            "valid_auc": valid_auc,
            "v6_auc": v6_auc,
            "delta_vs_v6": valid_auc - v6_auc,
            "weights": dict(zip(MEMBERS, weights.tolist())),
        }
        fold_rows.append(row)
        print(
            f"fold={fold} valid={valid_auc:.9f} delta_vs_v6={valid_auc-v6_auc:+.9f} "
            f"weights={dict(zip(MEMBERS, np.round(weights, 4)))}",
            flush=True,
        )

    final_weights = np.mean(learned_weights, axis=0)
    final_weights /= final_weights.sum()
    fixed_oof = oof_matrix @ final_weights
    test_pred = test_matrix @ final_weights
    crossfit_auc = float(roc_auc_score(y, crossfit_oof))
    fixed_auc = float(roc_auc_score(y, fixed_oof))
    member_auc = {name: float(roc_auc_score(y, raw_oof[name])) for name in MEMBERS}
    print(f"crossfit OOF={crossfit_auc:.9f}", flush=True)
    print(f"fixed-weight OOF={fixed_auc:.9f}", flush=True)
    print(f"final_weights={dict(zip(MEMBERS, final_weights))}", flush=True)

    submission = sample.copy()
    submission[TARGET] = test_pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交格式异常")
    if not np.isfinite(test_pred).all() or ((test_pred < 0) | (test_pred > 1)).any():
        raise ValueError("提交概率非法")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", crossfit_oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    result = {
        "competition": "playground-series-s6e9",
        "model": "cross-fitted percentile-rank blend of local v6 and two public OOF models",
        "members": MEMBERS,
        "member_oof_auc": member_auc,
        "fold_results": fold_rows,
        "final_weights": dict(zip(MEMBERS, final_weights.tolist())),
        "crossfit_oof_auc": crossfit_auc,
        "fixed_weight_oof_auc": fixed_auc,
        "v6_oof_auc": member_auc[MEMBERS[0]],
        "oof_delta_vs_v6": crossfit_auc - member_auc[MEMBERS[0]],
        "folds_won_vs_v6": sum(row["delta_vs_v6"] > 0 for row in fold_rows),
        "grid_step": GRID_STEP,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
