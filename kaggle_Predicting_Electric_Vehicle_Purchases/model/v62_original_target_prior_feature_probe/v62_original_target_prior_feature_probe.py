# -*- coding: utf-8 -*-
"""v62：把原始 1 万行的逐特征目标均值作为外部先验加入强 LGBM。"""

from __future__ import annotations

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
ORIGINAL_DATA = OUT_DIR.parents[1] / "data" / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv"


def load_base():
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.base


def main() -> None:
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
    x_train, x_test, keys_train, keys_test = base.build_static_features(train, test)

    original = pd.read_csv(ORIGINAL_DATA)
    original_y = (original[base.TARGET] == base.POS_LABEL).astype(np.float64)
    original_prior = float(original_y.mean())
    prior_names: list[str] = []
    for col in base.RAW_FEATURES:
        mapping = (
            pd.DataFrame({col: original[col], "_target": original_y})
            .groupby(col, dropna=False)["_target"]
            .mean()
        )
        name = f"original_target_mean_{col}"
        x_train[name] = train[col].map(mapping).fillna(original_prior).astype(np.float32)
        x_test[name] = test[col].map(mapping).fillna(original_prior).astype(np.float32)
        prior_names.append(name)

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
    params = dict(base.LGB_PARAMS)
    params.update(
        {
            "max_depth": 4,
            "num_leaves": 15,
            "random_state": SEED,
            "bagging_seed": SEED,
            "feature_fraction_seed": SEED,
            "data_random_seed": SEED,
        }
    )
    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(train, y))
    rows: list[dict] = []
    importance: list[pd.DataFrame] = []
    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
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
        rows.append(
            {
                "fold": fold,
                "baseline_auc": baseline_auc[fold],
                "original_prior_auc": auc,
                "delta": delta,
                "best_iteration": iteration,
            }
        )
        gain = model.booster_.feature_importance(importance_type="gain")
        importance.append(
            pd.DataFrame({"feature": feature_names, "gain": gain, "fold": fold})
        )
        print(
            f"fold={fold} auc={auc:.9f} delta={delta:+.9f} iter={iteration} "
            f"elapsed={time.time() - start:.1f}s",
            flush=True,
        )

    deltas = [row["delta"] for row in rows]
    importance_frame = pd.concat(importance, ignore_index=True)
    prior_gain = (
        importance_frame[importance_frame["feature"].isin(prior_names)]
        .groupby("feature", as_index=False)["gain"]
        .mean()
        .sort_values("gain", ascending=False)
    )
    prior_gain.to_csv(OUT_DIR / "original_prior_importance.csv", index=False)
    result = {
        "competition": "playground-series-s6e9",
        "model": "matched-fold depth-4 LGBM plus original-dataset target priors",
        "seed": SEED,
        "rows": rows,
        "mean_delta": float(np.mean(deltas)),
        "folds_won": int(sum(delta > 0 for delta in deltas)),
        "prior_features": prior_names,
        "hypothesis": (
            "the external income-label prior improved the final rank ensemble; exposing "
            "all original-dataset marginal target priors to LightGBM may learn when that "
            "source-specific random effect is trustworthy"
        ),
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
