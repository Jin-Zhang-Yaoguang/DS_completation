# -*- coding: utf-8 -*-
"""v66：直接用 pairwise ranking loss 检验 AUC 排序目标错配。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import xgboost as xgb
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
LGB_RESULTS = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "cv_results.json"
LGB_OOF = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "oof_proba.npy"

BASE_PARAMS = {
    "n_estimators": 8000,
    "max_depth": 4,
    "learning_rate": 0.02,
    "min_child_weight": 0.5001690675041187,
    "subsample": 0.8509678493503904,
    "colsample_bytree": 0.8275505466758548,
    "colsample_bylevel": 0.7742579918816374,
    "reg_alpha": 0.4708519329042792,
    "reg_lambda": 0.04854531207050869,
    "gamma": 0.5254723720544142,
    "max_bin": 831,
    "objective": "rank:pairwise",
    "eval_metric": "auc",
    "tree_method": "hist",
    "device": "cpu",
    "random_state": SEED,
    "n_jobs": 8,
    "early_stopping_rounds": 300,
    "lambdarank_pair_method": "mean",
}


def load_recipe():
    spec = importlib.util.spec_from_file_location("v29_recipe", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.base.factorize_joint = module.factorize_joint_extended
    module.base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    return module.base


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def main() -> None:
    start = time.time()
    recipe = load_recipe()
    train, test, _ = recipe.load_data()
    y = (train[recipe.TARGET] == recipe.POS_LABEL).to_numpy(np.int8)
    x_train, _, keys_train, keys_test = recipe.build_static_features(train, test)

    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(x_train, y))
    fit_idx, valid_idx = folds[0]
    inner = list(
        StratifiedKFold(5, shuffle=True, random_state=SEED + 1).split(
            np.zeros(len(fit_idx)), y[fit_idx]
        )
    )
    fit_te: list[np.ndarray] = []
    valid_te: list[np.ndarray] = []
    for key in recipe.TE_KEYS:
        encoded_fit, encoded_valid, _ = recipe.encode_key(
            keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
        )
        fit_te.append(encoded_fit)
        valid_te.append(encoded_valid)
    x_fit = np.column_stack([x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te])
    x_valid = np.column_stack(
        [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
    )

    lgb_oof = np.load(LGB_OOF)[valid_idx]
    lgb_auc = float(roc_auc_score(y[valid_idx], lgb_oof))
    rows: list[dict] = []
    predictions: dict[str, np.ndarray] = {}
    print(
        f"fit={x_fit.shape} valid={x_valid.shape} lgb_auc={lgb_auc:.9f}",
        flush=True,
    )

    for pairs in (1, 4, 8):
        name = f"pairwise_mean_{pairs}"
        params = dict(BASE_PARAMS)
        params["lambdarank_num_pair_per_sample"] = pairs
        model = xgb.XGBRanker(**params)
        model.fit(
            x_fit,
            y[fit_idx],
            group=[len(fit_idx)],
            eval_set=[(x_valid, y[valid_idx])],
            eval_group=[[len(valid_idx)]],
            verbose=200,
        )
        pred = model.predict(x_valid)
        predictions[name] = pred
        auc = float(roc_auc_score(y[valid_idx], pred))
        rank_lgb = percentile_rank(lgb_oof)
        rank_pred = percentile_rank(pred)
        blend_grid = []
        for weight in np.linspace(0.0, 0.5, 101):
            blend_auc = float(
                roc_auc_score(
                    y[valid_idx], (1.0 - weight) * rank_lgb + weight * rank_pred
                )
            )
            blend_grid.append(
                {"weight": float(weight), "auc": blend_auc, "delta": blend_auc - lgb_auc}
            )
        best_blend = max(blend_grid, key=lambda row: row["auc"])
        row = {
            "config": name,
            "pairs_per_sample": pairs,
            "auc": auc,
            "delta_vs_lgb": auc - lgb_auc,
            "best_iteration": int(model.best_iteration),
            "spearman_vs_lgb": float(spearmanr(pred, lgb_oof).statistic),
            "best_blend": best_blend,
        }
        rows.append(row)
        np.save(OUT_DIR / f"fold1_{name}_valid_proba.npy", pred)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    pairwise_blends = []
    rank_lgb = percentile_rank(lgb_oof)
    mean_rank = np.mean(
        [percentile_rank(pred) for pred in predictions.values()], axis=0
    )
    for weight in np.linspace(0.0, 0.5, 101):
        auc = float(
            roc_auc_score(y[valid_idx], (1.0 - weight) * rank_lgb + weight * mean_rank)
        )
        pairwise_blends.append(
            {"weight": float(weight), "auc": auc, "delta": auc - lgb_auc}
        )
    result = {
        "competition": "playground-series-s6e9",
        "model": "one-fold XGBoost pairwise ranking objective probe",
        "fold": 1,
        "seed": SEED,
        "lgb_auc": lgb_auc,
        "rows": rows,
        "mean_pairwise_best_blend": max(pairwise_blends, key=lambda row: row["auc"]),
        "params": BASE_PARAMS,
        "decision_rule": (
            "expand only if pairwise training or its blend exceeds matched LightGBM "
            "by at least 1e-4 on the probe fold"
        ),
        "elapsed_seconds": time.time() - start,
    }
    np.save(OUT_DIR / "fold1_valid_idx.npy", valid_idx)
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
