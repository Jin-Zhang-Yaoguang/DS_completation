# -*- coding: utf-8 -*-
"""v15：基于 v14 验证结果，在 100% 训练数据上重训多尺度 TE LightGBM。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.model_selection import StratifiedKFold


BAG_SEEDS = (42, 2026, 7)
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
V6_SOURCE = MODEL_DIR / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
V14_RESULTS = MODEL_DIR / "v14_multiscale_te_lgbm_10f" / "cv_results.json"


def load_v6_module():
    spec = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm", V6_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v6：{V6_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    start = time.time()
    recipe = load_v6_module()
    train, test, sample = recipe.load_data()
    y = (train[recipe.TARGET] == recipe.POS_LABEL).to_numpy(np.int8)
    x_train, x_test, keys_train, keys_test = recipe.build_static_features(train, test)

    fit_idx = np.arange(len(train), dtype=np.int64)
    empty_idx = np.array([], dtype=np.int64)
    inner = list(
        StratifiedKFold(recipe.N_INNER, shuffle=True, random_state=recipe.SEED).split(
            np.zeros(len(train)), y
        )
    )
    fit_te: list[np.ndarray] = []
    test_te: list[np.ndarray] = []
    for key in recipe.TE_KEYS:
        encoded_fit, _, encoded_test = recipe.encode_key(
            keys_train[key], keys_test[key], y, fit_idx, empty_idx, inner
        )
        fit_te.append(encoded_fit)
        test_te.append(encoded_test)

    x_fit = np.column_stack([x_train.to_numpy(np.float32), *fit_te])
    x_tst = np.column_stack([x_test.to_numpy(np.float32), *test_te])
    feature_names = list(x_train.columns) + [
        f"te_{key}_m{smooth:g}" for key in recipe.TE_KEYS for smooth in recipe.SMOOTHS
    ]
    v14 = json.loads(V14_RESULTS.read_text(encoding="utf-8"))
    n_estimators = int(round(float(np.mean(v14["best_iterations"]))))
    print(
        f"train={x_fit.shape}, test={x_tst.shape}, estimators={n_estimators}, "
        f"seeds={BAG_SEEDS}",
        flush=True,
    )

    test_pred = np.zeros(len(test), dtype=np.float64)
    for seed in BAG_SEEDS:
        params = {
            **recipe.LGB_PARAMS,
            "n_estimators": n_estimators,
            "random_state": seed,
            "bagging_seed": seed,
            "feature_fraction_seed": seed,
            "data_random_seed": seed,
        }
        model = lgb.LGBMClassifier(**params)
        seed_start = time.time()
        model.fit(x_fit, y, feature_name=feature_names)
        pred = model.predict_proba(x_tst)[:, 1]
        np.save(OUT_DIR / f"test_seed_{seed}.npy", pred)
        test_pred += pred / len(BAG_SEEDS)
        print(
            f"seed={seed} elapsed={time.time()-seed_start:.1f}s "
            f"range=[{pred.min():.6g}, {pred.max():.6g}]",
            flush=True,
        )

    submission = sample.copy()
    submission[recipe.TARGET] = test_pred
    recipe.validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    result = {
        "competition": "playground-series-s6e9",
        "model": "v14 multiscale TE LightGBM full-data refit, 3-seed bagging",
        "validation_source": "v14_multiscale_te_lgbm_10f",
        "validation_oof_auc": v14["oof_auc"],
        "fullfit_has_independent_oof": False,
        "bag_seeds": list(BAG_SEEDS),
        "n_estimators": n_estimators,
        "train_rows": len(train),
        "feature_count": len(feature_names),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "run_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
