# -*- coding: utf-8 -*-
"""v58：检验对概率语义明确的目标编码施加单调约束。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 15_485_863
OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
BASELINE_RESULTS = OUT_DIR.parent / "v53_income_bin2_range_probe" / "probe_results.json"


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

    # v29 的 10 美元收入键由包装模块实现；这里显式复刻，避免 main() 才发生的绑定。
    original_factorize = base.factorize_joint

    def factorize_joint(train, test, cols):
        if cols != ["_income_bin10"]:
            return original_factorize(train, test, cols)
        import pandas as pd

        values = pd.concat(
            [train["Annual_Income_USD"], test["Annual_Income_USD"]], ignore_index=True
        )
        codes, _ = pd.factorize((values // 10).astype(np.int64), sort=True)
        return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)

    base.factorize_joint = factorize_joint
    base.TE_KEYS["income_bin10"] = ["_income_bin10"]

    train, test, _ = base.load_data()
    y = (train[base.TARGET] == base.POS_LABEL).to_numpy(np.int8)
    x_train, _x_test, keys_train, keys_test = base.build_static_features(train, test)
    te_names = [
        f"te_{key}_m{smooth:g}" for key in base.TE_KEYS for smooth in base.SMOOTHS
    ]
    feature_names = list(x_train.columns) + te_names
    constraints = [0] * x_train.shape[1] + [1] * len(te_names)

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
            "monotone_constraints": constraints,
            "monotone_constraints_method": "advanced",
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
        fit_te: list[np.ndarray] = []
        valid_te: list[np.ndarray] = []
        for key in base.TE_KEYS:
            fit_block, valid_block, _ = base.encode_key(
                keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
            )
            fit_te.append(fit_block)
            valid_te.append(valid_block)

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
        delta = auc - baseline_auc[fold]
        rows.append(
            {
                "fold": fold,
                "baseline_auc": baseline_auc[fold],
                "monotone_te_auc": auc,
                "delta": delta,
                "best_iteration": iteration,
            }
        )
        print(
            f"fold={fold} auc={auc:.9f} delta={delta:+.9f} iter={iteration} "
            f"elapsed={time.time() - start:.1f}s",
            flush=True,
        )

    deltas = [row["delta"] for row in rows]
    result = {
        "competition": "playground-series-s6e9",
        "model": "matched-fold depth-4 LightGBM with monotone target encodings",
        "seed": SEED,
        "rows": rows,
        "mean_delta": float(np.mean(deltas)),
        "folds_won": int(sum(delta > 0 for delta in deltas)),
        "constraint_count": int(sum(value != 0 for value in constraints)),
        "hypothesis": (
            "a target encoding is an estimate of conditional purchase probability; "
            "forcing its partial effect to be nondecreasing may suppress noisy tree splits"
        ),
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
