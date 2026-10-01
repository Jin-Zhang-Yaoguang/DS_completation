# -*- coding: utf-8 -*-
"""v22：复用完全相同的 v6 折内特征，筛选加入多尺度 TE 后的 LightGBM 容量参数。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
OUT_DIR = Path(__file__).resolve().parent
BASE_PATH = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

CONFIGS = {
    "baseline": {},
    "colsample_050": {"colsample_bytree": 0.50},
    "colsample_070": {"colsample_bytree": 0.70},
    "depth4": {"max_depth": 4, "num_leaves": 15},
    "depth6": {"max_depth": 6, "num_leaves": 63},
    "minchild30": {"min_child_samples": 30},
    "minchild100": {"min_child_samples": 100},
    "no_bagging": {"subsample": 1.0, "subsample_freq": 0},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.folds <= 5:
        raise ValueError("--folds 必须在 1 到 5 之间")
    start = time.time()
    train, test, _ = base.load_data()
    y = (train[base.TARGET] == base.POS_LABEL).to_numpy(np.int8)
    x_train, x_test, keys_train, keys_test = base.build_static_features(train, test)
    te_names = [f"te_{key}_m{smooth:g}" for key in base.TE_KEYS for smooth in base.SMOOTHS]
    feature_names = list(x_train.columns) + te_names
    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(x_train, y))
    rows: list[dict] = []

    for fold, (fit_idx, valid_idx) in enumerate(folds[: args.folds], 1):
        inner = list(
            StratifiedKFold(base.N_INNER, shuffle=True, random_state=SEED + fold).split(
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

        for name, override in CONFIGS.items():
            params = dict(base.LGB_PARAMS)
            params.update(override)
            model = lgb.LGBMClassifier(**params)
            model.fit(
                x_fit,
                y[fit_idx],
                eval_set=[(x_valid, y[valid_idx])],
                eval_metric="auc",
                feature_name=feature_names,
                callbacks=[
                    lgb.early_stopping(base.EARLY_STOPPING_ROUNDS, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            iteration = int(model.best_iteration_ or params["n_estimators"])
            pred = model.predict_proba(x_valid, num_iteration=iteration)[:, 1]
            auc = float(roc_auc_score(y[valid_idx], pred))
            row = {
                "fold": fold,
                "config": name,
                "auc": auc,
                "best_iteration": iteration,
                "override": override,
            }
            rows.append(row)
            print(
                f"fold={fold} config={name} auc={auc:.9f} iter={iteration} "
                f"elapsed={time.time()-start:.1f}s",
                flush=True,
            )

    summary = {}
    baseline = {row["fold"]: row["auc"] for row in rows if row["config"] == "baseline"}
    for name in CONFIGS:
        selected = [row for row in rows if row["config"] == name]
        deltas = [row["auc"] - baseline[row["fold"]] for row in selected]
        summary[name] = {
            "mean_auc": float(np.mean([row["auc"] for row in selected])),
            "mean_delta_vs_baseline": float(np.mean(deltas)),
            "fold_deltas_vs_baseline": deltas,
            "folds_won": int(sum(delta > 0 for delta in deltas)),
            "mean_best_iteration": float(np.mean([row["best_iteration"] for row in selected])),
            "override": CONFIGS[name],
        }
    result = {
        "competition": "playground-series-s6e9",
        "model": "matched-fold LightGBM parameter screen on frozen v6 features",
        "screened_folds": args.folds,
        "rows": rows,
        "summary": summary,
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "screen_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
