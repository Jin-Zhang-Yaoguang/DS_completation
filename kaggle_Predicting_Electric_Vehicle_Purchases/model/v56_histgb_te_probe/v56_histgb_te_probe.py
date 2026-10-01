# -*- coding: utf-8 -*-
"""v56：在严格嵌套 TE 上检验 HistGradientBoosting 的独立误差。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 15_485_863
OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
REFERENCE = OUT_DIR.parent / "v52_robust_rank_ensemble_v51" / "oof_proba.npy"
CONFIGS = {
    "leaf15_l2_5": {"max_leaf_nodes": 15, "min_samples_leaf": 30, "l2_regularization": 5.0},
    "leaf31_l2_10": {"max_leaf_nodes": 31, "min_samples_leaf": 30, "l2_regularization": 10.0},
    "leaf31_l2_30": {"max_leaf_nodes": 31, "min_samples_leaf": 60, "l2_regularization": 30.0},
}


def load_base():
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.base


def rank(values: np.ndarray) -> np.ndarray:
    return rankdata(np.asarray(values), method="average") / len(values)


def main() -> None:
    start = time.time()
    base = load_base()
    train, test, _ = base.load_data()
    y = (train[base.TARGET] == base.POS_LABEL).to_numpy(np.int8)
    x_train, _x_test, keys_train, keys_test = base.build_static_features(train, test)
    fit_idx, valid_idx = next(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x_train, y)
    )
    inner = list(
        StratifiedKFold(base.N_INNER, shuffle=True, random_state=SEED + 1).split(
            np.zeros(len(fit_idx)), y[fit_idx]
        )
    )
    fit_te: list[np.ndarray] = []
    valid_te: list[np.ndarray] = []
    for key in base.TE_KEYS:
        fit_block, valid_block, _ = base.encode_key(
            keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
        )
        fit_te.append(fit_block)
        valid_te.append(valid_block)
    x_fit = np.column_stack([x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te])
    x_valid = np.column_stack([x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te])
    reference = np.load(REFERENCE)
    reference_auc = float(roc_auc_score(y[valid_idx], reference[valid_idx]))
    rows = []
    print(
        f"fit={x_fit.shape} valid={x_valid.shape} reference_auc={reference_auc:.9f}",
        flush=True,
    )
    for name, override in CONFIGS.items():
        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=1200,
            max_bins=255,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=40,
            tol=1e-7,
            scoring="roc_auc",
            random_state=SEED,
            **override,
        )
        model.fit(x_fit, y[fit_idx])
        pred = model.predict_proba(x_valid)[:, 1]
        auc = float(roc_auc_score(y[valid_idx], pred))
        ref_rank = rank(reference[valid_idx])
        pred_rank = rank(pred)
        blends = []
        for weight in (0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30):
            score = float(
                roc_auc_score(
                    y[valid_idx], (1.0 - weight) * ref_rank + weight * pred_rank
                )
            )
            blends.append({"weight": weight, "auc": score, "delta": score - reference_auc})
        row = {
            "config": name,
            "auc": auc,
            "n_iter": int(model.n_iter_),
            "spearman_vs_reference": float(spearmanr(pred, reference[valid_idx]).statistic),
            "best_blend": max(blends, key=lambda item: item["auc"]),
            "override": override,
            "elapsed_seconds": time.time() - start,
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
    result = {
        "competition": "playground-series-s6e9",
        "model": "single-fold HistGradientBoosting on nested v29 TE features",
        "seed": SEED,
        "fold": 1,
        "reference": "v52_robust_rank_ensemble_v51",
        "reference_fold_auc": reference_auc,
        "rows": rows,
        "elapsed_seconds": time.time() - start,
        "hypothesis": (
            "a separately regularized histogram booster can add independent split errors after exact-value "
            "target encoding, as observed in earlier synthetic Playground generators"
        ),
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
