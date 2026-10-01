# -*- coding: utf-8 -*-
"""v67：以类别总权重平衡作为高效 AUC pairwise 代理。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 15_485_863
OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
BASELINE_RESULTS = OUT_DIR.parent / "v53_income_bin2_range_probe" / "probe_results.json"
WEIGHTS = (1.5, 2.0, 3.0, 4.726)


def load_base():
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.folds <= 5:
        raise ValueError("--folds 必须在 1 到 5 之间")

    start = time.time()
    base = load_base()
    original_factorize = base.factorize_joint

    def factorize_joint(train, test, cols):
        if cols != ["_income_bin10"]:
            return original_factorize(train, test, cols)
        values = pd.concat(
            [train["Annual_Income_USD"], test["Annual_Income_USD"]], ignore_index=True
        )
        codes, _ = pd.factorize((values // 10).astype(np.int64), sort=True)
        return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)

    base.factorize_joint = factorize_joint
    base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    train, test, _ = base.load_data()
    y = (train[base.TARGET] == base.POS_LABEL).to_numpy(np.int8)
    x_train, _, keys_train, keys_test = base.build_static_features(train, test)
    te_names = [
        f"te_{key}_m{smooth:g}" for key in base.TE_KEYS for smooth in base.SMOOTHS
    ]
    feature_names = list(x_train.columns) + te_names
    baseline_json = json.loads(BASELINE_RESULTS.read_text(encoding="utf-8"))
    baseline_auc = {
        int(row["fold"]): float(row["auc"])
        for row in baseline_json["rows"]
        if row["config"] == "baseline"
    }
    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(train, y))
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
        x_valid = np.column_stack(
            [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
        )

        for weight in WEIGHTS:
            params = dict(base.LGB_PARAMS)
            params.update(
                {
                    "max_depth": 4,
                    "num_leaves": 15,
                    "scale_pos_weight": weight,
                    "random_state": SEED,
                    "bagging_seed": SEED,
                    "feature_fraction_seed": SEED,
                    "data_random_seed": SEED,
                }
            )
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
            delta = auc - baseline_auc[fold]
            row = {
                "fold": fold,
                "scale_pos_weight": weight,
                "baseline_auc": baseline_auc[fold],
                "auc": auc,
                "delta": delta,
                "best_iteration": iteration,
            }
            rows.append(row)
            print(
                f"fold={fold} weight={weight:g} auc={auc:.9f} delta={delta:+.9f} "
                f"iter={iteration} elapsed={time.time() - start:.1f}s",
                flush=True,
            )

    summary = {}
    for weight in WEIGHTS:
        selected = [row for row in rows if row["scale_pos_weight"] == weight]
        deltas = [row["delta"] for row in selected]
        summary[str(weight)] = {
            "mean_auc": float(np.mean([row["auc"] for row in selected])),
            "mean_delta": float(np.mean(deltas)),
            "folds_won": int(sum(delta > 0 for delta in deltas)),
            "fold_deltas": deltas,
            "mean_best_iteration": float(
                np.mean([row["best_iteration"] for row in selected])
            ),
        }
    result = {
        "competition": "playground-series-s6e9",
        "model": "matched-fold class-weighted depth-4 LightGBM AUC proxy probe",
        "seed": SEED,
        "screened_folds": args.folds,
        "positive_rate": float(y.mean()),
        "balanced_scale_pos_weight": float((y == 0).sum() / (y == 1).sum()),
        "rows": rows,
        "summary": summary,
        "hypothesis": (
            "equal total class weights align the finite-capacity binary objective more "
            "closely with AUC, which weights every positive-negative pair equally"
        ),
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
