# -*- coding: utf-8 -*-
"""v8：预注册门槛的交叉拟合三模型 rank 融合。

每个 held-out 外层折只用其余四折：
1. 在 v3 与 v7 中选择更强的 CatBoost 基线；
2. 从 v2/v5/v6 中贪心加入最多两个模型；
3. 每一步只搜索新增模型 0%~30% 的权重。

最终提交权重取五个 held-out 实验权重的均值。只有交叉拟合 OOF 相比最强
CatBoost 单模型提升至少 0.0001 才生成 submission.csv。
"""

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
MIN_STEP_FIT_GAIN = 0.00001
MAX_MODELS = 3
NEW_WEIGHT_GRID = np.linspace(0.0, 0.30, 16)

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
MODEL_PATHS = {
    "v2_lgbm": MODEL_DIR / "v2_budget_lgbm",
    "v3_catboost": MODEL_DIR / "v3_dual_catboost",
    "v5_lookup": MODEL_DIR / "v5_hierarchical_lookup",
    "v6_highres_lgbm": MODEL_DIR / "v6_highres_lgbm",
    "v7_catboost_bag": MODEL_DIR / "v7_catboost_bagging",
}
BASE_CANDIDATES = ["v3_catboost", "v7_catboost_bag"]
ADDITION_CANDIDATES = ["v2_lgbm", "v5_lookup", "v6_highres_lgbm"]


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = train[TARGET].to_numpy(dtype=np.int8)
    oof_raw = {name: np.load(path / "oof_proba.npy") for name, path in MODEL_PATHS.items()}
    test_raw = {name: np.load(path / "test_proba.npy") for name, path in MODEL_PATHS.items()}
    oof_rank = {name: percentile_rank(pred) for name, pred in oof_raw.items()}
    test_rank = {name: percentile_rank(pred) for name, pred in test_raw.items()}
    for name in MODEL_PATHS:
        if len(oof_rank[name]) != len(y) or len(test_rank[name]) != len(test):
            raise ValueError(f"{name} 预测长度不一致")

    single_auc = {name: float(roc_auc_score(y, pred)) for name, pred in oof_raw.items()}
    strongest_base = max(BASE_CANDIDATES, key=single_auc.get)
    strongest_base_auc = single_auc[strongest_base]
    correlations = {
        left: {right: float(spearmanr(oof_raw[left], oof_raw[right]).statistic) for right in MODEL_PATHS}
        for left in MODEL_PATHS
    }

    folds = list(StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED).split(np.zeros(len(y)), y))
    crossfit = np.zeros(len(y), dtype=np.float64)
    fold_results: list[dict] = []
    fold_weights: list[dict[str, float]] = []

    for fold, (_, valid_idx) in enumerate(folds, start=1):
        fit_mask = np.ones(len(y), dtype=bool)
        fit_mask[valid_idx] = False
        base = max(BASE_CANDIDATES, key=lambda name: roc_auc_score(y[fit_mask], oof_rank[name][fit_mask]))
        blend = oof_rank[base].copy()
        weights = {name: 0.0 for name in MODEL_PATHS}
        weights[base] = 1.0
        selected = [base]
        current_fit_auc = float(roc_auc_score(y[fit_mask], blend[fit_mask]))

        while len(selected) < MAX_MODELS:
            best = None
            for candidate in ADDITION_CANDIDATES:
                if candidate in selected:
                    continue
                for new_weight in NEW_WEIGHT_GRID[1:]:
                    trial = (1.0 - new_weight) * blend + new_weight * oof_rank[candidate]
                    score = float(roc_auc_score(y[fit_mask], trial[fit_mask]))
                    if best is None or score > best["score"]:
                        best = {"candidate": candidate, "weight": float(new_weight), "score": score, "prediction": trial}
            if best is None or best["score"] - current_fit_auc < MIN_STEP_FIT_GAIN:
                break
            for name in weights:
                weights[name] *= 1.0 - best["weight"]
            weights[best["candidate"]] += best["weight"]
            blend = best["prediction"]
            current_fit_auc = best["score"]
            selected.append(best["candidate"])

        crossfit[valid_idx] = blend[valid_idx]
        heldout_auc = float(roc_auc_score(y[valid_idx], blend[valid_idx]))
        heldout_base_auc = float(roc_auc_score(y[valid_idx], oof_rank[strongest_base][valid_idx]))
        fold_weights.append(weights)
        fold_results.append({
            "fold": fold,
            "selected": selected,
            "weights": weights,
            "fit_auc": current_fit_auc,
            "heldout_auc": heldout_auc,
            "heldout_strongest_base_auc": heldout_base_auc,
            "heldout_gain": heldout_auc - heldout_base_auc,
        })

    crossfit_auc = float(roc_auc_score(y, crossfit))
    crossfit_gain = crossfit_auc - strongest_base_auc
    final_weights = {name: float(np.mean([weights[name] for weights in fold_weights])) for name in MODEL_PATHS}
    weight_sum = sum(final_weights.values())
    final_weights = {name: weight / weight_sum for name, weight in final_weights.items() if weight > 1e-12}
    approved = crossfit_gain >= MIN_BLEND_GAIN
    fixed_oof = sum(weight * oof_rank[name] for name, weight in final_weights.items())
    fixed_oof_auc = float(roc_auc_score(y, fixed_oof))
    results = {
        "competition": "playground-series-s6e8",
        "model": "cross-fitted greedy rank ensemble, up to three models",
        "single_model_auc": single_auc,
        "strongest_base": strongest_base,
        "strongest_base_auc": strongest_base_auc,
        "rank_correlations": correlations,
        "fold_results": fold_results,
        "final_weights": final_weights,
        "crossfit_oof_auc": crossfit_auc,
        "crossfit_gain_vs_strongest_base": crossfit_gain,
        "fixed_weight_oof_auc": fixed_oof_auc,
        "min_blend_gain": MIN_BLEND_GAIN,
        "min_step_fit_gain": MIN_STEP_FIT_GAIN,
        "approved_for_submission": approved,
    }
    (OUT_DIR / "blend_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not approved:
        print("融合未通过准入门槛，不生成 submission.csv")
        return

    test_pred = sum(weight * test_rank[name] for name, weight in final_weights.items())
    submission = sample.copy()
    submission[TARGET] = test_pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交结构或 id 不一致")
    if not np.isfinite(test_pred).all() or ((test_pred < 0.0) | (test_pred > 1.0)).any():
        raise ValueError("提交概率非法")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", crossfit)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
