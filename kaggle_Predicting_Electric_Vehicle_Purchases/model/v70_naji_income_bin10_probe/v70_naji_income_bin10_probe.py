# -*- coding: utf-8 -*-
"""v70：在加速 Naji 配方上成对检验 income//10 目标编码。"""

from __future__ import annotations

import importlib.util
import json
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder


SEED = 42
OUT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = OUT_DIR.parent / "v68_naji_accelerated_probe" / "v68_naji_accelerated_probe.py"
BASE_PRED = OUT_DIR.parent / "v68_naji_accelerated_probe" / "fold1_valid_proba.npy"


def load_base():
    spec = importlib.util.spec_from_file_location("v68_naji_accelerated_probe", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v68：{BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def main() -> None:
    warnings.filterwarnings("ignore", category=Warning)
    start = time.time()
    base = load_base()
    x, y, _x_test, target_encode_cols = base.build_features(extra_income_bins=(10,))
    fit_idx, valid_idx = next(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
    )
    x_fit = x.iloc[fit_idx].copy()
    x_valid = x.iloc[valid_idx].copy()
    y_fit = y.iloc[fit_idx]
    y_valid = y.iloc[valid_idx]
    for tag, smooth in (("auto", "auto"), ("10", 10.0)):
        encoder = TargetEncoder(shuffle=True, cv=5, smooth=smooth, random_state=SEED)
        fit_encoded = encoder.fit_transform(x_fit[target_encode_cols], y_fit)
        valid_encoded = encoder.transform(x_valid[target_encode_cols])
        fit_columns = {}
        valid_columns = {}
        for column_idx, col in enumerate(target_encode_cols):
            name = f"{col}_TE_{tag}"
            fit_columns[name] = fit_encoded[:, column_idx].astype("float32")
            valid_columns[name] = valid_encoded[:, column_idx].astype("float32")
        x_fit = base.pd.concat(
            [x_fit, base.pd.DataFrame(fit_columns, index=x_fit.index)], axis=1
        )
        x_valid = base.pd.concat(
            [x_valid, base.pd.DataFrame(valid_columns, index=x_valid.index)], axis=1
        )
    x_fit = x_fit.drop(columns=target_encode_cols)
    x_valid = x_valid.drop(columns=target_encode_cols)

    params = {
        "n_estimators": 12_000,
        "learning_rate": 0.02,
        "max_depth": 5,
        "num_leaves": 32,
        "min_child_samples": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.3,
        "reg_alpha": 0.071,
        "reg_lambda": 2.0,
        "max_bin": 1024,
        "random_state": SEED,
        "feature_pre_filter": False,
        "metric": "auc",
        "n_jobs": 8,
        "verbosity": -1,
    }
    model = lgb.LGBMClassifier(**params)
    model.fit(
        x_fit,
        y_fit,
        eval_set=[(x_valid, y_valid)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=350, verbose=False),
            lgb.log_evaluation(period=500),
        ],
    )
    pred = model.predict_proba(x_valid)[:, 1]
    baseline = np.load(BASE_PRED)
    baseline_auc = float(roc_auc_score(y_valid, baseline))
    auc = float(roc_auc_score(y_valid, pred))
    rank_base = percentile_rank(baseline)
    rank_pred = percentile_rank(pred)
    blends = []
    for weight in np.linspace(0.0, 1.0, 41):
        score = float(
            roc_auc_score(y_valid, (1.0 - weight) * rank_base + weight * rank_pred)
        )
        blends.append(
            {"weight": float(weight), "auc": score, "delta": score - baseline_auc}
        )
    result = {
        "competition": "playground-series-s6e9",
        "model": "matched-fold accelerated Naji plus income-bin10 target encoding",
        "fold": 1,
        "seed": SEED,
        "baseline_auc": baseline_auc,
        "auc": auc,
        "delta": auc - baseline_auc,
        "best_baseline_blend": max(blends, key=lambda row: row["auc"]),
        "spearman_vs_baseline": float(spearmanr(pred, baseline).statistic),
        "best_iteration": int(model.best_iteration_),
        "feature_count": int(x_fit.shape[1]),
        "target_encode_column_count": len(target_encode_cols),
        "hypothesis": (
            "the locally validated ten-dollar income neighborhood should improve the "
            "independent Naji representation beyond exact-value and digit encodings"
        ),
        "elapsed_seconds": time.time() - start,
    }
    np.save(OUT_DIR / "fold1_valid_idx.npy", valid_idx)
    np.save(OUT_DIR / "fold1_valid_proba.npy", pred)
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
