# -*- coding: utf-8 -*-
"""v41 探针：在已验证的收入-bin10 多尺度 TE 上测试 XGBoost 的独立价值。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"

XGB_PARAMS = {
    "n_estimators": 15000,
    "max_depth": 4,
    "learning_rate": 0.012720913279298928,
    "min_child_weight": 0.5001690675041187,
    "subsample": 0.8509678493503904,
    "colsample_bytree": 0.8275505466758548,
    "colsample_bylevel": 0.7742579918816374,
    "reg_alpha": 0.4708519329042792,
    "reg_lambda": 0.04854531207050869,
    "gamma": 0.5254723720544142,
    "max_bin": 831,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "tree_method": "hist",
    "device": "cpu",
    "random_state": SEED,
    "n_jobs": 8,
    "early_stopping_rounds": 300,
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


def main() -> None:
    start = time.time()
    recipe = load_recipe()
    train, test, _ = recipe.load_data()
    y = (train[recipe.TARGET] == recipe.POS_LABEL).to_numpy(np.int8)
    x_train, _, keys_train, keys_test = recipe.build_static_features(train, test)

    folds = list(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x_train, y)
    )
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

    x_fit = np.column_stack(
        [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
    )
    x_valid = np.column_stack(
        [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
    )
    print(
        f"fit={x_fit.shape}, valid={x_valid.shape}, features={x_fit.shape[1]}",
        flush=True,
    )

    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(
        x_fit,
        y[fit_idx],
        eval_set=[(x_valid, y[valid_idx])],
        verbose=200,
    )
    valid_pred = model.predict_proba(x_valid)[:, 1]
    valid_auc = float(roc_auc_score(y[valid_idx], valid_pred))
    best_iteration = int(model.best_iteration)
    elapsed = time.time() - start

    np.save(OUT_DIR / "fold1_valid_idx.npy", valid_idx)
    np.save(OUT_DIR / "fold1_valid_proba.npy", valid_pred)
    result = {
        "competition": "playground-series-s6e9",
        "model": "income-bin10 multiscale TE XGBoost one-fold probe",
        "fold": 1,
        "seed": SEED,
        "valid_auc": valid_auc,
        "best_iteration": best_iteration,
        "elapsed_seconds": elapsed,
        "xgboost_version": xgb.__version__,
        "params": XGB_PARAMS,
        "decision_rule": (
            "expand only if fold AUC is competitive with the strong LightGBM path "
            "and its residual ranking is complementary"
        ),
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
