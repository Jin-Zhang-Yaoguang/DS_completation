# -*- coding: utf-8 -*-
"""v73：在同一验证折筛查 Naji 收入邻域的尺度与分箱边界。"""

from __future__ import annotations

import gc
import importlib.util
import json
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder


SEED = 42
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
BASE_SCRIPT = MODEL_DIR / "v68_naji_accelerated_probe" / "v68_naji_accelerated_probe.py"
BASE_PRED = MODEL_DIR / "v68_naji_accelerated_probe" / "fold1_valid_proba.npy"
BIN10_PRED = MODEL_DIR / "v70_naji_income_bin10_probe" / "fold1_valid_proba.npy"
TARGET = "Will_Buy_EV"

VARIANTS: dict[str, tuple[tuple[int, int], ...]] = {
    "bin5": ((5, 0),),
    "bin20": ((20, 0),),
    "bin10_shift5": ((10, 5),),
    "bin10_plus_shift5": ((10, 0), (10, 5)),
    "bin5_10_20": ((5, 0), (10, 0), (20, 0)),
    "bin10_100": ((10, 0), (100, 0)),
}


def load_base():
    spec = importlib.util.spec_from_file_location("v68_naji_accelerated_probe", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v68：{BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def percentile_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values, method="average") / len(values)


def add_income_neighborhoods(
    x: pd.DataFrame,
    x_test: pd.DataFrame,
    specifications: tuple[tuple[int, int], ...],
) -> tuple[list[str], list[str]]:
    category_columns: list[str] = []
    added_columns: list[str] = []
    for width, shift in specifications:
        name = f"Annual_Income_USD_bin{width}_shift{shift}_cat"
        train_values = ((x["Annual_Income_USD"] + shift) // width).astype(np.int64).astype(str)
        test_values = ((x_test["Annual_Income_USD"] + shift) // width).astype(np.int64).astype(str)
        combined = pd.concat([train_values, test_values], ignore_index=True)
        frequency = combined.value_counts(normalize=True)
        x[name] = train_values
        x_test[name] = test_values
        frequency_name = f"{name}_fe"
        x[frequency_name] = train_values.map(frequency).fillna(0.0).astype(np.float32)
        x_test[frequency_name] = test_values.map(frequency).fillna(0.0).astype(np.float32)
        category_columns.append(name)
        added_columns.extend((name, frequency_name))
    return category_columns, added_columns


def fit_variant(
    base,
    x: pd.DataFrame,
    x_test: pd.DataFrame,
    y: pd.Series,
    base_target_encode_cols: list[str],
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    name: str,
    specifications: tuple[tuple[int, int], ...],
) -> tuple[np.ndarray, dict[str, object]]:
    start = time.time()
    new_target_cols, added_columns = add_income_neighborhoods(x, x_test, specifications)
    target_encode_cols = base_target_encode_cols + new_target_cols
    x_fit = x.iloc[fit_idx].copy()
    x_valid = x.iloc[valid_idx].copy()
    y_fit = y.iloc[fit_idx]
    y_valid = y.iloc[valid_idx]
    for tag, smooth in (("auto", "auto"), ("10", 10.0)):
        encoder = TargetEncoder(shuffle=True, cv=5, smooth=smooth, random_state=SEED)
        fit_encoded = encoder.fit_transform(x_fit[target_encode_cols], y_fit)
        valid_encoded = encoder.transform(x_valid[target_encode_cols])
        encoded_fit = {}
        encoded_valid = {}
        for column_idx, column in enumerate(target_encode_cols):
            encoded_name = f"{column}_TE_{tag}"
            encoded_fit[encoded_name] = fit_encoded[:, column_idx].astype(np.float32)
            encoded_valid[encoded_name] = valid_encoded[:, column_idx].astype(np.float32)
        x_fit = pd.concat([x_fit, pd.DataFrame(encoded_fit, index=x_fit.index)], axis=1)
        x_valid = pd.concat([x_valid, pd.DataFrame(encoded_valid, index=x_valid.index)], axis=1)
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
    prediction = model.predict_proba(x_valid)[:, 1]
    importance = sorted(
        zip(x_fit.columns, model.booster_.feature_importance(importance_type="gain")),
        key=lambda pair: pair[1],
        reverse=True,
    )
    result = {
        "name": name,
        "specifications": [
            {"width": width, "shift": shift} for width, shift in specifications
        ],
        "auc": float(roc_auc_score(y_valid, prediction)),
        "best_iteration": int(model.best_iteration_),
        "feature_count": int(x_fit.shape[1]),
        "target_encode_column_count": len(target_encode_cols),
        "top_feature_gain": [
            {"feature": feature, "gain": float(gain)} for feature, gain in importance[:20]
        ],
        "elapsed_seconds": time.time() - start,
    }
    x.drop(columns=added_columns, inplace=True)
    x_test.drop(columns=added_columns, inplace=True)
    del x_fit, x_valid, model
    gc.collect()
    return prediction, result


def best_pair_blend(
    y: np.ndarray, baseline: np.ndarray, candidate: np.ndarray
) -> dict[str, float]:
    baseline_rank = percentile_rank(baseline)
    candidate_rank = percentile_rank(candidate)
    baseline_auc = float(roc_auc_score(y, baseline_rank))
    rows = []
    for weight in np.linspace(0.0, 1.0, 41):
        score = float(
            roc_auc_score(y, (1.0 - weight) * baseline_rank + weight * candidate_rank)
        )
        rows.append(
            {"candidate_weight": float(weight), "auc": score, "delta": score - baseline_auc}
        )
    return max(rows, key=lambda row: row["auc"])


def main() -> None:
    warnings.filterwarnings("ignore", category=Warning)
    start = time.time()
    base = load_base()
    x, y, x_test, base_target_encode_cols = base.build_features()
    fit_idx, valid_idx = next(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
    )
    y_valid = y.iloc[valid_idx].to_numpy()
    baseline = np.load(BASE_PRED)
    bin10 = np.load(BIN10_PRED)
    if len(baseline) != len(valid_idx) or len(bin10) != len(valid_idx):
        raise ValueError("基线预测与验证折不匹配")
    baseline_auc = float(roc_auc_score(y_valid, baseline))
    bin10_auc = float(roc_auc_score(y_valid, bin10))
    results: list[dict[str, object]] = []
    for name, specifications in VARIANTS.items():
        prediction, result = fit_variant(
            base,
            x,
            x_test,
            y,
            base_target_encode_cols,
            fit_idx,
            valid_idx,
            name,
            specifications,
        )
        np.save(OUT_DIR / f"{name}_fold1_valid_proba.npy", prediction)
        result.update(
            {
                "delta_vs_plain": result["auc"] - baseline_auc,
                "delta_vs_bin10": result["auc"] - bin10_auc,
                "spearman_vs_plain": float(spearmanr(prediction, baseline).statistic),
                "spearman_vs_bin10": float(spearmanr(prediction, bin10).statistic),
                "best_plain_blend": best_pair_blend(y_valid, baseline, prediction),
                "best_bin10_blend": best_pair_blend(y_valid, bin10, prediction),
            }
        )
        results.append(result)
        partial = {
            "competition": "playground-series-s6e9",
            "fold": 1,
            "seed": SEED,
            "plain_auc": baseline_auc,
            "bin10_auc": bin10_auc,
            "variants": results,
            "elapsed_seconds": time.time() - start,
        }
        (OUT_DIR / "probe_results.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"{name}: auc={result['auc']:.12f} "
            f"vs_plain={result['delta_vs_plain']:+.12f} "
            f"vs_bin10={result['delta_vs_bin10']:+.12f} "
            f"bin10_blend={result['best_bin10_blend']}",
            flush=True,
        )
    print(f"finished {len(results)} variants in {time.time() - start:.1f}s", flush=True)


if __name__ == "__main__":
    main()
