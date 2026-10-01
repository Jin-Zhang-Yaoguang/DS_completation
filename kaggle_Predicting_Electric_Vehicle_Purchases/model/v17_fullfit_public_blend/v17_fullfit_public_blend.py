# -*- coding: utf-8 -*-
"""v17：沿用 v16 的 OOF 权重，以 v15 全量拟合预测替换 v14 的折均值预测。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr


TARGET = "Will_Buy_EV"
ID_COL = "id"

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
PUBLIC_DIR = MODEL_DIR / "v7_cv_public_blend" / "public_inputs"
VALIDATION_DIR = MODEL_DIR / "v16_blend_v14_public_mlp"
FULLFIT_DIR = MODEL_DIR / "v15_multiscale_te_fullfit"
MEMBERS = (
    "v14_multiscale_te_lgbm_10f",
    "public_unified_v3",
    "public_kirill_v4",
    "v11_mlp_te_10f",
)


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def main() -> None:
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    validation = json.loads((VALIDATION_DIR / "cv_results.json").read_text(encoding="utf-8"))
    weights = np.array([validation["final_weights"][name] for name in MEMBERS], dtype=np.float64)
    weights /= weights.sum()

    public_test = pd.read_parquet(PUBLIC_DIR / "Mdl_Preds.parquet")
    v14_test = np.load(MODEL_DIR / MEMBERS[0] / "test_proba.npy")
    v15_test = np.load(FULLFIT_DIR / "test_proba.npy")
    raw_test = {
        MEMBERS[0]: v15_test,
        MEMBERS[1]: public_test["V3"].to_numpy(np.float64),
        MEMBERS[2]: public_test["V4"].to_numpy(np.float64),
        MEMBERS[3]: np.load(MODEL_DIR / MEMBERS[3] / "test_proba.npy"),
    }
    for name, values in raw_test.items():
        if len(values) != len(test) or not np.isfinite(values).all():
            raise ValueError(f"{name} 的测试预测异常")
    test_matrix = np.column_stack([pct_rank(raw_test[name]) for name in MEMBERS])
    test_pred = test_matrix @ weights

    submission = sample.copy()
    submission[TARGET] = test_pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交格式异常")
    if not np.isfinite(test_pred).all() or ((test_pred < 0) | (test_pred > 1)).any():
        raise ValueError("提交概率非法")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    results = {
        "competition": "playground-series-s6e9",
        "model": "v16 validated blend with v15 full-data refit replacing v14 test predictions",
        "validation_source": "v16_blend_v14_public_mlp",
        "validation_crossfit_oof_auc": validation["crossfit_oof_auc"],
        "validation_fixed_weight_oof_auc": validation["fixed_weight_oof_auc"],
        "fullfit_source": "v15_multiscale_te_fullfit",
        "fullfit_has_independent_oof": False,
        "members": MEMBERS,
        "final_weights": dict(zip(MEMBERS, weights.tolist())),
        "v14_v15_test_spearman": float(spearmanr(v14_test, v15_test).correlation),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
    }
    (OUT_DIR / "run_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
