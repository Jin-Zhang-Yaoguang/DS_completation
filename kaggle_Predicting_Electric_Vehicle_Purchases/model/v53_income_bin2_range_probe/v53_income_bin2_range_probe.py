# -*- coding: utf-8 -*-
"""v53：成对检验 income-bin2 × range-anxiety TE 是否改善 depth-4 LGBM。"""

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
    train, test, _ = base.load_data()
    y = (train[base.TARGET] == base.POS_LABEL).to_numpy(np.int8)

    original_factorize = base.factorize_joint

    def factorize_joint(
        train_frame: pd.DataFrame, test_frame: pd.DataFrame, cols: list[str]
    ) -> tuple[np.ndarray, np.ndarray]:
        if cols != ["_income_bin2", "Range_Anxiety_Level"]:
            return original_factorize(train_frame, test_frame, cols)
        income = pd.concat(
            [train_frame["Annual_Income_USD"], test_frame["Annual_Income_USD"]],
            ignore_index=True,
        )
        anxiety = pd.concat(
            [train_frame["Range_Anxiety_Level"], test_frame["Range_Anxiety_Level"]],
            ignore_index=True,
        ).astype("string")
        key = (income // 2).astype(np.int64).astype("string").str.cat(anxiety, sep="|")
        codes, _ = pd.factorize(key, sort=True)
        return codes[: len(train_frame)].astype(np.int32), codes[len(train_frame) :].astype(np.int32)

    base.factorize_joint = factorize_joint
    baseline_keys = dict(base.TE_KEYS)
    extended_keys = {
        **baseline_keys,
        "income_bin2_range": ["_income_bin2", "Range_Anxiety_Level"],
    }

    configs: dict[str, tuple[dict[str, list[str]], pd.DataFrame, pd.DataFrame, dict, dict]] = {}
    for name, keys in (("baseline", baseline_keys), ("income_bin2_range", extended_keys)):
        base.TE_KEYS = keys
        x_train, x_test, keys_train, keys_test = base.build_static_features(train, test)
        configs[name] = (keys, x_train, x_test, keys_train, keys_test)

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

    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
        inner = list(
            StratifiedKFold(base.N_INNER, shuffle=True, random_state=SEED + fold).split(
                np.zeros(len(fit_idx)), y[fit_idx]
            )
        )
        for name, (keys, x_train, _x_test, keys_train, keys_test) in configs.items():
            fit_te: list[np.ndarray] = []
            valid_te: list[np.ndarray] = []
            for key in keys:
                fit_block, valid_block, _ = base.encode_key(
                    keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
                )
                fit_te.append(fit_block)
                valid_te.append(valid_block)
            feature_names = list(x_train.columns) + [
                f"te_{key}_m{smooth:g}" for key in keys for smooth in base.SMOOTHS
            ]
            x_fit = np.column_stack(
                [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
            )
            x_valid = np.column_stack(
                [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
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
            rows.append(
                {
                    "fold": fold,
                    "config": name,
                    "auc": auc,
                    "best_iteration": iteration,
                }
            )
            print(
                f"fold={fold} config={name} auc={auc:.9f} iter={iteration} "
                f"elapsed={time.time() - start:.1f}s",
                flush=True,
            )

    baseline = {r["fold"]: r["auc"] for r in rows if r["config"] == "baseline"}
    extended = [r for r in rows if r["config"] == "income_bin2_range"]
    deltas = [r["auc"] - baseline[r["fold"]] for r in extended]
    result = {
        "competition": "playground-series-s6e9",
        "model": "matched-fold depth-4 LightGBM feature probe",
        "seed": SEED,
        "rows": rows,
        "fold_deltas": deltas,
        "mean_delta": float(np.mean(deltas)),
        "folds_won": int(sum(delta > 0 for delta in deltas)),
        "hypothesis": (
            "range anxiety changes the conditional purchase curve within the two-dollar "
            "income neighborhoods; a nested TE should add signal beyond the raw interaction"
        ),
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
