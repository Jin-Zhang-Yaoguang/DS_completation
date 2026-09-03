# -*- coding: utf-8 -*-
"""v4：v2 LightGBM 与 v3 CatBoost 的防过拟合 rank blend。"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
TARGET = "addicted_label"
ID_COL = "id"
MIN_BLEND_GAIN = 0.0001
MAX_RANK_CORRELATION = 0.995

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
V2_DIR = MODEL_DIR / "v2_budget_lgbm"
V3_DIR = MODEL_DIR / "v3_dual_catboost"


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def validate_submission(
    submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame
) -> None:
    if submission.shape != sample.shape:
        raise ValueError(f"提交 shape 错误：{submission.shape} != {sample.shape}")
    if list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError(f"提交列名错误：{submission.columns.tolist()}")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与测试集不一致")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率包含非法值")


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = train[TARGET].to_numpy(dtype=np.int8)

    oof_v2 = np.load(V2_DIR / "oof_proba.npy")
    test_v2 = np.load(V2_DIR / "test_proba.npy")
    oof_v3 = np.load(V3_DIR / "oof_proba.npy")
    test_v3 = np.load(V3_DIR / "test_proba.npy")

    if not (len(oof_v2) == len(oof_v3) == len(y)):
        raise ValueError("OOF 长度不一致")
    if not (len(test_v2) == len(test_v3) == len(test)):
        raise ValueError("测试预测长度不一致")

    rank_oof_v2 = percentile_rank(oof_v2)
    rank_oof_v3 = percentile_rank(oof_v3)
    rank_test_v2 = percentile_rank(test_v2)
    rank_test_v3 = percentile_rank(test_v3)

    auc_v2 = float(roc_auc_score(y, oof_v2))
    auc_v3 = float(roc_auc_score(y, oof_v3))
    rank_correlation = float(spearmanr(oof_v2, oof_v3).statistic)

    # 对每个 held-out fold，权重只在其余四折的 OOF 预测上选择。
    # 这样可以避免在同一批标签上同时选权重并汇报融合收益。
    grid = np.linspace(0.0, 1.0, 51)
    splitter = StratifiedKFold(
        n_splits=N_FOLDS, shuffle=True, random_state=SEED
    )
    folds = list(splitter.split(np.zeros(len(y)), y))
    crossfit_blend = np.zeros(len(y), dtype=np.float64)
    selected_v2_weights: list[float] = []
    fold_results: list[dict] = []

    for fold, (_, valid_idx) in enumerate(folds, start=1):
        fit_mask = np.ones(len(y), dtype=bool)
        fit_mask[valid_idx] = False
        fit_scores = [
            roc_auc_score(
                y[fit_mask],
                weight * rank_oof_v2[fit_mask]
                + (1.0 - weight) * rank_oof_v3[fit_mask],
            )
            for weight in grid
        ]
        v2_weight = float(grid[int(np.argmax(fit_scores))])
        v3_weight = 1.0 - v2_weight
        selected_v2_weights.append(v2_weight)
        crossfit_blend[valid_idx] = (
            v2_weight * rank_oof_v2[valid_idx]
            + v3_weight * rank_oof_v3[valid_idx]
        )
        fold_results.append(
            {
                "fold": fold,
                "v2_weight": v2_weight,
                "v3_weight": v3_weight,
                "heldout_blend_auc": float(
                    roc_auc_score(y[valid_idx], crossfit_blend[valid_idx])
                ),
                "heldout_v3_auc": float(
                    roc_auc_score(y[valid_idx], rank_oof_v3[valid_idx])
                ),
            }
        )

    crossfit_auc = float(roc_auc_score(y, crossfit_blend))
    crossfit_gain = crossfit_auc - auc_v3
    final_v2_weight = float(np.mean(selected_v2_weights))
    final_v3_weight = 1.0 - final_v2_weight

    approved = (
        rank_correlation < MAX_RANK_CORRELATION
        and crossfit_gain >= MIN_BLEND_GAIN
    )

    results = {
        "competition": "playground-series-s6e8",
        "model": "cross-fitted rank blend of v2 LightGBM and v3 CatBoost",
        "v2_oof_auc": auc_v2,
        "v3_oof_auc": auc_v3,
        "rank_correlation": rank_correlation,
        "selected_v2_weights": selected_v2_weights,
        "final_v2_weight": final_v2_weight,
        "final_v3_weight": final_v3_weight,
        "crossfit_oof_auc": crossfit_auc,
        "crossfit_gain_vs_v3": crossfit_gain,
        "max_rank_correlation": MAX_RANK_CORRELATION,
        "min_blend_gain": MIN_BLEND_GAIN,
        "approved_for_submission": approved,
        "fold_results": fold_results,
    }
    (OUT_DIR / "blend_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not approved:
        print("融合未通过准入门槛，不生成 submission.csv")
        return

    test_pred = (
        final_v2_weight * rank_test_v2 + final_v3_weight * rank_test_v3
    )
    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", crossfit_blend)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
