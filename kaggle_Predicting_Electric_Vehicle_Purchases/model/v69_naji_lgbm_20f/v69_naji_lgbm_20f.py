# -*- coding: utf-8 -*-
"""v69：Naji 独立特征配方的 20 折加速 LightGBM。"""

from __future__ import annotations

import importlib.util
import json
import time
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder


SEED = 42
N_FOLDS = 20
EXTRA_INCOME_BINS: tuple[int, ...] = ()
EXTRA_JOINT_KEYS: tuple[tuple[str, ...], ...] = ()
OUT_DIR = Path(__file__).resolve().parent
PROBE = OUT_DIR.parent / "v68_naji_accelerated_probe" / "v68_naji_accelerated_probe.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("v68_naji_accelerated_probe", PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v68：{PROBE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    warnings.filterwarnings("ignore", category=Warning)
    start = time.time()
    probe = load_probe()
    x, y, x_test, target_encode_cols = probe.build_features(
        extra_income_bins=EXTRA_INCOME_BINS
    )
    for columns in EXTRA_JOINT_KEYS:
        name = "joint_" + "_x_".join(columns)
        train_key = x[columns[0]].astype(str)
        test_key = x_test[columns[0]].astype(str)
        for column in columns[1:]:
            train_key = train_key.str.cat(x[column].astype(str), sep="|")
            test_key = test_key.str.cat(x_test[column].astype(str), sep="|")
        combined = probe.pd.concat([train_key, test_key], ignore_index=True)
        frequency = combined.value_counts(normalize=True)
        x[name] = train_key
        x_test[name] = test_key
        x[f"{name}_fe"] = train_key.map(frequency).fillna(0.0).astype("float32")
        x_test[f"{name}_fe"] = test_key.map(frequency).fillna(0.0).astype("float32")
        target_encode_cols.append(name)
    sample = probe.pd.read_csv(probe.DATA_DIR / "sample_submission.csv")
    folds = list(
        StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(x, y)
    )
    oof = np.zeros(len(x), dtype=np.float64)
    test_pred = np.zeros(len(x_test), dtype=np.float64)
    fold_rows: list[dict] = []
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
        "feature_pre_filter": False,
        "metric": "auc",
        "n_jobs": 8,
        "verbosity": -1,
    }
    print(
        f"static={x.shape} test={x_test.shape} te_cols={len(target_encode_cols)} "
        f"folds={N_FOLDS}",
        flush=True,
    )

    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
        x_fit = x.iloc[fit_idx].copy()
        x_valid = x.iloc[valid_idx].copy()
        x_test_fold = x_test.copy()
        y_fit = y.iloc[fit_idx]
        y_valid = y.iloc[valid_idx]
        for tag, smooth in (("auto", "auto"), ("10", 10.0)):
            encoder = TargetEncoder(
                shuffle=True, cv=5, smooth=smooth, random_state=SEED + fold
            )
            fit_encoded = encoder.fit_transform(x_fit[target_encode_cols], y_fit)
            valid_encoded = encoder.transform(x_valid[target_encode_cols])
            test_encoded = encoder.transform(x_test_fold[target_encode_cols])
            fit_columns = {}
            valid_columns = {}
            test_columns = {}
            for column_idx, col in enumerate(target_encode_cols):
                name = f"{col}_TE_{tag}"
                fit_columns[name] = fit_encoded[:, column_idx].astype("float32")
                valid_columns[name] = valid_encoded[:, column_idx].astype("float32")
                test_columns[name] = test_encoded[:, column_idx].astype("float32")
            x_fit = probe.pd.concat(
                [x_fit, probe.pd.DataFrame(fit_columns, index=x_fit.index)], axis=1
            )
            x_valid = probe.pd.concat(
                [x_valid, probe.pd.DataFrame(valid_columns, index=x_valid.index)], axis=1
            )
            x_test_fold = probe.pd.concat(
                [x_test_fold, probe.pd.DataFrame(test_columns, index=x_test_fold.index)],
                axis=1,
            )
        x_fit = x_fit.drop(columns=target_encode_cols)
        x_valid = x_valid.drop(columns=target_encode_cols)
        x_test_fold = x_test_fold.drop(columns=target_encode_cols)

        fold_params = dict(params)
        fold_params["random_state"] = SEED + fold
        fold_params["bagging_seed"] = SEED + fold
        fold_params["feature_fraction_seed"] = SEED + fold
        fold_params["data_random_seed"] = SEED + fold
        model = lgb.LGBMClassifier(**fold_params)
        model.fit(
            x_fit,
            y_fit,
            eval_set=[(x_valid, y_valid)],
            callbacks=[
                lgb.early_stopping(stopping_rounds=350, verbose=False),
                lgb.log_evaluation(period=0),
            ],
        )
        valid_pred = model.predict_proba(x_valid)[:, 1]
        fold_test = model.predict_proba(x_test_fold)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += fold_test / N_FOLDS
        auc = float(roc_auc_score(y_valid, valid_pred))
        fold_rows.append(
            {
                "fold": fold,
                "auc": auc,
                "best_iteration": int(model.best_iteration_),
                "fit_rows": len(fit_idx),
                "valid_rows": len(valid_idx),
            }
        )
        print(
            f"fold={fold:02d}/{N_FOLDS} auc={auc:.9f} iter={model.best_iteration_} "
            f"elapsed={time.time() - start:.1f}s",
            flush=True,
        )

    oof_auc = float(roc_auc_score(y, oof))
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    submission = sample.copy()
    submission[probe.TARGET] = test_pred
    if not np.isfinite(test_pred).all():
        raise ValueError("test 预测含非有限值")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    result = {
        "competition": "playground-series-s6e9",
        "model": (
            "20-fold accelerated Naji independent-feature LightGBM"
            + (f" plus income bins {EXTRA_INCOME_BINS}" if EXTRA_INCOME_BINS else "")
        ),
        "seed": SEED,
        "n_folds": N_FOLDS,
        "oof_auc": oof_auc,
        "fold_auc_mean": float(np.mean([row["auc"] for row in fold_rows])),
        "fold_auc_std": float(np.std([row["auc"] for row in fold_rows])),
        "fold_rows": fold_rows,
        "feature_count": int(x.shape[1] - len(target_encode_cols) + 2 * len(target_encode_cols)),
        "target_encode_column_count": len(target_encode_cols),
        "extra_income_bins": list(EXTRA_INCOME_BINS),
        "extra_joint_keys": [list(columns) for columns in EXTRA_JOINT_KEYS],
        "params": params,
        "hypothesis": (
            "raising outer-fold training coverage from 80% to 95% should improve the "
            "lower-correlation Naji member while 4x learning rate preserves its ranking; "
            "optional income bins test validated local generator neighborhoods"
        ),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
