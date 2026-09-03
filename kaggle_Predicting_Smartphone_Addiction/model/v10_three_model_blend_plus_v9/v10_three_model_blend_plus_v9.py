# -*- coding: utf-8 -*-
"""v10：加入 v9 的交叉拟合三模型 rank 融合。

流程与 v8 保持一致，新增候选模型 v9，保持同样的安全规则：
- held-out 外层折选择
- 每步尝试将新模型权重从 0~30% 网格搜索
- 仅当累计增益超过门槛才通过
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
    "v9_catboost_engineered": MODEL_DIR / "v9_catboost_engineered",
}
BASE_CANDIDATES = ["v7_catboost_bag", "v9_catboost_engineered"]
ADDITION_CANDIDATES = ["v2_lgbm", "v5_lookup", "v6_highres_lgbm", "v3_catboost"]


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def load_predictions() -> tuple[pd.Series, dict[str, np.ndarray], dict[str, np.ndarray]]:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    y = train[TARGET].to_numpy(dtype=np.int8)
    oof_raw = {}
    test_raw = {}
    for name, path in MODEL_PATHS.items():
        oof_path = path / "oof_proba.npy"
        test_path = path / "test_proba.npy"
        if not oof_path.exists() or not test_path.exists():
            raise FileNotFoundError(f"{name} 缺少预测文件")
        oof = np.load(oof_path)
        test_pred = np.load(test_path)
        if len(oof) != len(y):
            raise ValueError(f"{name} oof 长度异常")
        oof_raw[name] = oof
        test_raw[name] = test_pred
    return y, oof_raw, test_raw


def main() -> None:
    y, oof_raw, test_raw = load_predictions()
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")

    oof_rank = {name: percentile_rank(pred) for name, pred in oof_raw.items()}
    test_rank = {name: percentile_rank(pred) for name, pred in test_raw.items()}

    single_auc = {name: float(roc_auc_score(y, pred)) for name, pred in oof_raw.items()}
    strongest_base = max(BASE_CANDIDATES, key=lambda name: single_auc[name])
    strongest_base_auc = single_auc[strongest_base]
    correlations = {
        left: {right: float(spearmanr(oof_raw[left], oof_raw[right]).statistic) for right in MODEL_PATHS}
        for left in MODEL_PATHS
    }

    folds = list(StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED).split(np.zeros(len(y)), y))
    crossfit = np.zeros(len(y), dtype=np.float64)
    fold_results = []
    fold_weights: list[dict[str, float]] = []

    for fold, (_, valid_idx) in enumerate(folds, start=1):
        fit_mask = np.ones(len(y), dtype=bool)
        fit_mask[valid_idx] = False
        base = max(
            BASE_CANDIDATES,
            key=lambda name: roc_auc_score(y[fit_mask], oof_rank[name][fit_mask]),
        )
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
                        best = {
                            "candidate": candidate,
                            "weight": float(new_weight),
                            "score": score,
                            "prediction": trial,
                        }
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
        fold_results.append(
            {
                "fold": fold,
                "selected": selected,
                "weights": weights,
                "fit_auc": current_fit_auc,
                "heldout_auc": heldout_auc,
                "heldout_strongest_base_auc": heldout_base_auc,
                "heldout_gain": heldout_auc - heldout_base_auc,
            }
        )
        fold_weights.append(weights)

    crossfit_auc = float(roc_auc_score(y, crossfit))
    crossfit_gain = crossfit_auc - strongest_base_auc
    final_weights = {name: float(np.mean([weights[name] for weights in fold_weights])) for name in MODEL_PATHS}
    weight_sum = sum(final_weights.values())
    final_weights = {name: w / weight_sum for name, w in final_weights.items() if w > 1e-12}
    approved = crossfit_gain >= MIN_BLEND_GAIN

    fixed_oof = sum(weight * oof_rank[name] for name, weight in final_weights.items())
    fixed_oof_auc = float(roc_auc_score(y, fixed_oof))
    results = {
        "competition": "playground-series-s6e8",
        "model": "v10 cross-fitted greedy rank ensemble, include engineered CatBoost",
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
    (OUT_DIR / "blend_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))

    if not approved:
        print("融合未通过门槛，不生成 submission.csv")
        return

    test_pred = sum(weight * test_rank[name] for name, weight in final_weights.items())
    submission = sample.copy()
    submission[TARGET] = test_pred
    if submission.shape != sample.shape:
        raise ValueError("提交 shape 与 sample 不一致")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与 test 不一致")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("预测概率非法")

    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", crossfit)
    np.save(OUT_DIR / "test_proba.npy", test_pred)


if __name__ == "__main__":
    main()
