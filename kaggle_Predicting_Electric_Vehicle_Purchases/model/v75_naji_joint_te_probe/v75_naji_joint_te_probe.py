# -*- coding: utf-8 -*-
"""v75：在 Naji 双尺度收入模型上成对筛查条件目标编码。"""

from __future__ import annotations

import gc
import importlib.util
import json
import sys
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
MATCHED_BASELINE_PRED = (
    MODEL_DIR / "v73_naji_income_neighborhood_probe" / "bin10_100_fold1_valid_proba.npy"
)

VARIANTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "income_env": (("Annual_Income_USD", "Environmental_Concern_Level"),),
    "income_subsidy": (("Annual_Income_USD", "Subsidy_Available"),),
    "income_env_and_subsidy": (
        ("Annual_Income_USD", "Environmental_Concern_Level"),
        ("Annual_Income_USD", "Subsidy_Available"),
    ),
    "income_env_subsidy_triple": (
        (
            "Annual_Income_USD",
            "Environmental_Concern_Level",
            "Subsidy_Available",
        ),
    ),
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


def add_joint_keys(
    x: pd.DataFrame,
    x_test: pd.DataFrame,
    joints: tuple[tuple[str, ...], ...],
) -> tuple[list[str], list[str]]:
    categories: list[str] = []
    added: list[str] = []
    for columns in joints:
        name = "joint_" + "_x_".join(columns)
        train_key = x[columns[0]].astype(str)
        test_key = x_test[columns[0]].astype(str)
        for column in columns[1:]:
            train_key = train_key.str.cat(x[column].astype(str), sep="|")
            test_key = test_key.str.cat(x_test[column].astype(str), sep="|")
        combined = pd.concat([train_key, test_key], ignore_index=True)
        frequency = combined.value_counts(normalize=True)
        x[name] = train_key
        x_test[name] = test_key
        frequency_name = f"{name}_fe"
        x[frequency_name] = train_key.map(frequency).fillna(0.0).astype(np.float32)
        x_test[frequency_name] = test_key.map(frequency).fillna(0.0).astype(np.float32)
        categories.append(name)
        added.extend((name, frequency_name))
    return categories, added


def best_blend(y: np.ndarray, baseline: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    baseline_rank = percentile_rank(baseline)
    candidate_rank = percentile_rank(candidate)
    baseline_auc = float(roc_auc_score(y, baseline_rank))
    rows = []
    for weight in np.linspace(0.0, 1.0, 41):
        auc = float(
            roc_auc_score(y, (1.0 - weight) * baseline_rank + weight * candidate_rank)
        )
        rows.append(
            {"candidate_weight": float(weight), "auc": auc, "delta": auc - baseline_auc}
        )
    return max(rows, key=lambda row: row["auc"])


def audit_saved_predictions() -> None:
    base = load_base()
    x, y, _x_test, _base_te_cols = base.build_features(extra_income_bins=(10, 100))
    _fit_idx, valid_idx = next(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
    )
    y_valid = y.iloc[valid_idx].to_numpy()
    baseline = np.load(MATCHED_BASELINE_PRED)
    baseline_auc = float(roc_auc_score(y_valid, baseline))
    previous_path = OUT_DIR / "probe_results.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    metadata = {row["name"]: row for row in previous["variants"]}
    rows: list[dict[str, object]] = []
    for name, joints in VARIANTS.items():
        prediction = np.load(OUT_DIR / f"{name}_fold1_valid_proba.npy")
        auc = float(roc_auc_score(y_valid, prediction))
        old = metadata[name]
        rows.append(
            {
                "name": name,
                "joint_keys": [list(columns) for columns in joints],
                "auc": auc,
                "delta_vs_matched_bin10_100": auc - baseline_auc,
                "spearman_vs_matched_bin10_100": float(
                    spearmanr(prediction, baseline).statistic
                ),
                "best_matched_bin10_100_blend": best_blend(
                    y_valid, baseline, prediction
                ),
                "best_iteration": old["best_iteration"],
                "feature_count": old["feature_count"],
                "target_encode_column_count": old["target_encode_column_count"],
                "elapsed_seconds": old["elapsed_seconds"],
            }
        )
    payload = {
        "competition": "playground-series-s6e9",
        "fold": 1,
        "seed": SEED,
        "matched_bin10_100_auc": baseline_auc,
        "variants": rows,
        "audit_note": "all comparisons use the same 5-fold split and 80 percent fit coverage",
    }
    previous_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for row in rows:
        print(
            f"{row['name']}: auc={row['auc']:.12f} "
            f"delta={row['delta_vs_matched_bin10_100']:+.12f} "
            f"blend={row['best_matched_bin10_100_blend']}",
            flush=True,
        )


def main() -> None:
    warnings.filterwarnings("ignore", category=Warning)
    total_start = time.time()
    base = load_base()
    x, y, x_test, base_te_cols = base.build_features(extra_income_bins=(10, 100))
    fit_idx, valid_idx = next(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
    )
    y_fit = y.iloc[fit_idx]
    y_valid = y.iloc[valid_idx].to_numpy()
    baseline = np.load(MATCHED_BASELINE_PRED)
    baseline_auc = float(roc_auc_score(y_valid, baseline))
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
    results: list[dict[str, object]] = []
    for name, joints in VARIANTS.items():
        start = time.time()
        new_te_cols, added = add_joint_keys(x, x_test, joints)
        te_cols = base_te_cols + new_te_cols
        x_fit = x.iloc[fit_idx].copy()
        x_valid = x.iloc[valid_idx].copy()
        for tag, smooth in (("auto", "auto"), ("10", 10.0)):
            encoder = TargetEncoder(shuffle=True, cv=5, smooth=smooth, random_state=SEED)
            fit_encoded = encoder.fit_transform(x_fit[te_cols], y_fit)
            valid_encoded = encoder.transform(x_valid[te_cols])
            fit_columns = {
                f"{column}_TE_{tag}": fit_encoded[:, index].astype(np.float32)
                for index, column in enumerate(te_cols)
            }
            valid_columns = {
                f"{column}_TE_{tag}": valid_encoded[:, index].astype(np.float32)
                for index, column in enumerate(te_cols)
            }
            x_fit = pd.concat([x_fit, pd.DataFrame(fit_columns, index=x_fit.index)], axis=1)
            x_valid = pd.concat(
                [x_valid, pd.DataFrame(valid_columns, index=x_valid.index)], axis=1
            )
        x_fit = x_fit.drop(columns=te_cols)
        x_valid = x_valid.drop(columns=te_cols)
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
        auc = float(roc_auc_score(y_valid, prediction))
        row = {
            "name": name,
            "joint_keys": [list(columns) for columns in joints],
            "auc": auc,
            "delta_vs_v74": auc - baseline_auc,
            "spearman_vs_v74": float(spearmanr(prediction, baseline).statistic),
            "best_v74_blend": best_blend(y_valid, baseline, prediction),
            "best_iteration": int(model.best_iteration_),
            "feature_count": int(x_fit.shape[1]),
            "target_encode_column_count": len(te_cols),
            "elapsed_seconds": time.time() - start,
        }
        results.append(row)
        np.save(OUT_DIR / f"{name}_fold1_valid_proba.npy", prediction)
        payload = {
            "competition": "playground-series-s6e9",
            "fold": 1,
            "seed": SEED,
            "v74_auc": baseline_auc,
            "variants": results,
            "elapsed_seconds": time.time() - total_start,
        }
        (OUT_DIR / "probe_results.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"{name}: auc={auc:.12f} delta={auc - baseline_auc:+.12f} "
            f"blend={row['best_v74_blend']}",
            flush=True,
        )
        x.drop(columns=added, inplace=True)
        x_test.drop(columns=added, inplace=True)
        del x_fit, x_valid, model
        gc.collect()
    print(f"finished {len(results)} variants in {time.time() - total_start:.1f}s", flush=True)


if __name__ == "__main__":
    if "--audit-only" in sys.argv:
        audit_saved_predictions()
    else:
        main()
