# -*- coding: utf-8 -*-
"""v52：把稳健的 depth-4 v51 以固定权重加入非负秩集成。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
TARGET = "Will_Buy_EV"
ID_COL = "id"
V51_WEIGHT = 0.192

# v48 阶段以交叉拟合 pairwise-ranking surrogate 得到的非负权重。
BASE_WEIGHTS = {
    "v31": 0.0788,
    "v32": 0.0197,
    "v36": 0.1355,
    "v47": 0.1302,
    "v48": 0.2506,
    "v28": 0.0506,
    "v11": 0.0301,
    "v10": 0.0028,
    "V1": 0.0502,
    "V2": 0.0011,
    "V3": 0.0776,
    "V4": 0.1727,
}

LOCAL_SOURCES = {
    "v31": MODEL_DIR / "v31_income_bin10_te_lgbm_10f_seed2026",
    "v32": MODEL_DIR / "v32_income_bin10_te_lgbm_10f_seed3407",
    "v36": MODEL_DIR / "v36_income_bin10_te_lgbm_10f_fullseed2718",
    "v47": MODEL_DIR / "v47_income_bin10_te_lgbm_10f_fullseed8119",
    "v48": MODEL_DIR / "v48_income_bin10_te_lgbm_20f_fullseed104729",
    "v28": MODEL_DIR / "v28_multiscale_te_lgbm_20f",
    "v11": MODEL_DIR / "v11_mlp_te_10f",
    "v10": MODEL_DIR / "v10_catboost_bag_10f",
}
PUBLIC_OOF = MODEL_DIR / "v7_cv_public_blend" / "public_inputs" / "OOF_Preds.parquet"
PUBLIC_TEST = MODEL_DIR / "v7_cv_public_blend" / "public_inputs" / "Mdl_Preds.parquet"
V51_DIR = MODEL_DIR / "v51_income_bin10_te_lgbm_20f_depth4"
SMART = MODEL_DIR / "v13_pb_v7_smart" / "public_inputs" / "submission.csv"
PB_V35 = MODEL_DIR / "v35_pb_v34_smart" / "submission.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile_rank(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("预测必须是一维有限数值")
    return rankdata(values, method="average") / len(values)


def validate_submission(
    submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame
) -> None:
    if submission.shape != sample.shape or list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError("提交 shape 或列名错误")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 顺序错误")
    prediction = submission[TARGET].to_numpy()
    if not np.isfinite(prediction).all() or ((prediction < 0) | (prediction > 1)).any():
        raise ValueError("提交概率非法")


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[ID_COL, TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == "Yes").to_numpy(np.int8)
    public_oof = pd.read_parquet(PUBLIC_OOF)
    public_test = pd.read_parquet(PUBLIC_TEST)
    if len(public_oof) != len(train) or len(public_test) != len(test):
        raise ValueError("公开 OOF/test 预测长度异常")

    weight_sum = float(sum(BASE_WEIGHTS.values()))
    weights = {name: value / weight_sum for name, value in BASE_WEIGHTS.items()}
    base_oof = np.zeros(len(train), dtype=np.float64)
    base_test = np.zeros(len(test), dtype=np.float64)
    sources: dict[str, dict[str, str | float]] = {}
    for name, weight in weights.items():
        if name in LOCAL_SOURCES:
            oof_path = LOCAL_SOURCES[name] / "oof_proba.npy"
            test_path = LOCAL_SOURCES[name] / "test_proba.npy"
            oof = np.load(oof_path)
            prediction = np.load(test_path)
            sources[name] = {
                "weight": weight,
                "oof": str(oof_path.relative_to(OUT_DIR.parents[1])),
                "oof_sha256": sha256(oof_path),
                "test": str(test_path.relative_to(OUT_DIR.parents[1])),
                "test_sha256": sha256(test_path),
            }
        else:
            oof = public_oof[name].to_numpy()
            prediction = public_test[name].to_numpy()
            sources[name] = {
                "weight": weight,
                "oof": str(PUBLIC_OOF.relative_to(OUT_DIR.parents[1])) + f"::{name}",
                "oof_sha256": sha256(PUBLIC_OOF),
                "test": str(PUBLIC_TEST.relative_to(OUT_DIR.parents[1])) + f"::{name}",
                "test_sha256": sha256(PUBLIC_TEST),
            }
        if len(oof) != len(train) or len(prediction) != len(test):
            raise ValueError(f"{name} 预测长度异常")
        base_oof += weight * percentile_rank(oof)
        base_test += weight * percentile_rank(prediction)

    v51_oof_path = V51_DIR / "oof_proba.npy"
    v51_test_path = V51_DIR / "test_proba.npy"
    v51_oof = percentile_rank(np.load(v51_oof_path))
    v51_test = percentile_rank(np.load(v51_test_path))
    oof = (1.0 - V51_WEIGHT) * base_oof + V51_WEIGHT * v51_oof
    test_prediction = (1.0 - V51_WEIGHT) * base_test + V51_WEIGHT * v51_test

    base_auc = float(roc_auc_score(y, base_oof))
    oof_auc = float(roc_auc_score(y, oof))
    fold_deltas: list[dict[str, float | int]] = []
    seeds = [42, 2026, 3407, 8119, 104729, 130363, 15485863, 271828, 314159, 161803]
    for seed in seeds:
        splitter = StratifiedKFold(5, shuffle=True, random_state=seed)
        for fold, (_, valid_idx) in enumerate(splitter.split(oof, y), 1):
            before = float(roc_auc_score(y[valid_idx], base_oof[valid_idx]))
            after = float(roc_auc_score(y[valid_idx], oof[valid_idx]))
            fold_deltas.append(
                {"seed": seed, "fold": fold, "base_auc": before, "auc": after, "delta": after - before}
            )

    submission = sample.copy()
    submission[TARGET] = test_prediction
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_prediction)

    test_correlations = {}
    for name, path in (("smart", SMART), ("pb_v35", PB_V35)):
        if path.exists():
            frame = pd.read_csv(path).set_index(ID_COL).reindex(test[ID_COL])
            test_correlations[name] = float(
                spearmanr(test_prediction, frame[TARGET].to_numpy()).statistic
            )
    sources["v51"] = {
        "weight": V51_WEIGHT,
        "oof": str(v51_oof_path.relative_to(OUT_DIR.parents[1])),
        "oof_sha256": sha256(v51_oof_path),
        "test": str(v51_test_path.relative_to(OUT_DIR.parents[1])),
        "test_sha256": sha256(v51_test_path),
    }
    results = {
        "competition": "playground-series-s6e9",
        "model": "robust non-negative rank ensemble plus depth-4 v51",
        "base_weights_normalized": weights,
        "v51_weight": V51_WEIGHT,
        "base_oof_auc": base_auc,
        "oof_auc": oof_auc,
        "delta_vs_base": oof_auc - base_auc,
        "repeated_validation_fold_count": len(fold_deltas),
        "repeated_validation_positive_folds": int(sum(row["delta"] > 0 for row in fold_deltas)),
        "repeated_validation_mean_delta": float(np.mean([row["delta"] for row in fold_deltas])),
        "repeated_validation_median_delta": float(np.median([row["delta"] for row in fold_deltas])),
        "repeated_validation_min_delta": float(np.min([row["delta"] for row in fold_deltas])),
        "repeated_validation_max_delta": float(np.max([row["delta"] for row in fold_deltas])),
        "fold_deltas": fold_deltas,
        "test_spearman": test_correlations,
        "prediction_min": float(test_prediction.min()),
        "prediction_max": float(test_prediction.max()),
        "prediction_mean": float(test_prediction.mean()),
        "validation_note": (
            "v51 weight is the mean of five held-out meta-fold optima; repeated folds "
            "test the fixed weight without retuning"
        ),
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "sources.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in results.items() if key != "fold_deltas"}, ensure_ascii=False, indent=2))
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
