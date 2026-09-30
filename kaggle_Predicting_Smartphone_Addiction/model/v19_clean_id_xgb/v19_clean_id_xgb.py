#!/usr/bin/env python3
"""v19: 修复 v13 的 ID 入模问题，并做同折受控消融。

本实验只重训 v13 XGBoost 的 clean-ID 版本；with-ID 版本直接读取 v13 已落盘的
OOF/test 预测，避免引入额外训练随机性。随后用 v17 的固定 13%/87% 权重重建
clean 候选，不重新搜索融合权重。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "model"
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "addicted_label"
ID_COL = "id"
SEED = 42
N_FOLDS = 5
V13_WEIGHT = 0.13
V8_WEIGHT = 0.87


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_v13_module():
    source = MODEL_DIR / "v13_fe_single_compare" / "v13_fe_single_compare.py"
    spec = importlib.util.spec_from_file_location("v13_source", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v13 源码: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # build_features 会保存列清单；将其定向到 v19，绝不改写 v13 产物。
    module.OUT_DIR = OUT_DIR
    return module, source


def fold_auc(y: np.ndarray, pred: np.ndarray, folds) -> list[float]:
    return [float(roc_auc_score(y[valid_idx], pred[valid_idx])) for _, valid_idx in folds]


def validate_submission(frame: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame) -> None:
    if frame.shape != sample.shape:
        raise ValueError(f"提交 shape 错误: {frame.shape} != {sample.shape}")
    if list(frame.columns) != [ID_COL, TARGET]:
        raise ValueError(f"提交字段错误: {frame.columns.tolist()}")
    if not frame[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 顺序与 test.csv 不一致")
    values = frame[TARGET].to_numpy(float)
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("提交概率存在 NaN/inf 或越界")


def main() -> None:
    started = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = train[TARGET].to_numpy(np.int8)

    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission.csv 与 test.csv 的 id 顺序不一致")

    v13, v13_source = load_v13_module()
    x_train, x_test = v13.build_features(train, test)
    if ID_COL not in x_train.columns:
        raise AssertionError("未复现 v13 的 ID 入模问题")
    dirty_feature_count = int(x_train.shape[1])
    x_train = x_train.drop(columns=[ID_COL])
    x_test = x_test.drop(columns=[ID_COL])
    if ID_COL in x_train.columns or list(x_train.columns) != list(x_test.columns):
        raise AssertionError("clean-ID 特征构建失败")
    (OUT_DIR / "clean_feature_columns.csv").write_text(
        "\n".join(x_train.columns) + "\n", encoding="utf-8"
    )

    folds = list(
        StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED).split(
            np.zeros(len(y)), y
        )
    )
    print(
        f"[v19] train={train.shape}, test={test.shape}, "
        f"dirty_features={dirty_feature_count}, clean_features={x_train.shape[1]}"
    )

    clean_auc, clean_folds, clean_oof, clean_test, best_iterations, train_seconds = (
        v13.train_xgb(x_train, y, x_test, folds)
    )
    np.save(OUT_DIR / "xgb_clean_oof_proba.npy", clean_oof)
    np.save(OUT_DIR / "xgb_clean_test_proba.npy", clean_test)

    dirty_oof_path = MODEL_DIR / "v13_fe_single_compare" / "xgb_oof_proba.npy"
    dirty_test_path = MODEL_DIR / "v13_fe_single_compare" / "xgb_test_proba.npy"
    v8_oof_path = MODEL_DIR / "v8_three_model_blend" / "oof_proba.npy"
    v8_test_path = MODEL_DIR / "v8_three_model_blend" / "test_proba.npy"
    dirty_oof = np.load(dirty_oof_path).astype(np.float64)
    dirty_test = np.load(dirty_test_path).astype(np.float64)
    v8_oof = np.load(v8_oof_path).astype(np.float64)
    v8_test = np.load(v8_test_path).astype(np.float64)

    for name, values, expected in [
        ("dirty_oof", dirty_oof, len(train)),
        ("dirty_test", dirty_test, len(test)),
        ("v8_oof", v8_oof, len(train)),
        ("v8_test", v8_test, len(test)),
    ]:
        if values.shape != (expected,) or not np.isfinite(values).all():
            raise ValueError(f"{name} 形状或数值非法: {values.shape}")

    dirty_auc = float(roc_auc_score(y, dirty_oof))
    dirty_folds = fold_auc(y, dirty_oof, folds)
    clean_folds_recomputed = fold_auc(y, clean_oof, folds)
    if not np.allclose(clean_folds, clean_folds_recomputed, atol=5e-7):
        raise AssertionError("clean 模型折 AUC 复算不一致")

    dirty_v17_oof = V8_WEIGHT * v8_oof + V13_WEIGHT * dirty_oof
    clean_v17_oof = V8_WEIGHT * v8_oof + V13_WEIGHT * clean_oof
    dirty_v17_auc = float(roc_auc_score(y, dirty_v17_oof))
    clean_v17_auc = float(roc_auc_score(y, clean_v17_oof))
    dirty_v17_folds = fold_auc(y, dirty_v17_oof, folds)
    clean_v17_folds = fold_auc(y, clean_v17_oof, folds)

    clean_submission = sample.copy()
    clean_submission[TARGET] = np.clip(clean_test, 0.0, 1.0)
    validate_submission(clean_submission, test, sample)
    clean_submission.to_csv(OUT_DIR / "submission_xgb_clean.csv", index=False)

    clean_pair_test = V8_WEIGHT * v8_test + V13_WEIGHT * clean_test
    clean_pair_submission = sample.copy()
    clean_pair_submission[TARGET] = np.clip(clean_pair_test, 0.0, 1.0)
    validate_submission(clean_pair_submission, test, sample)
    clean_pair_submission.to_csv(OUT_DIR / "submission_v17_weight_clean_id.csv", index=False)

    id_values = train[ID_COL].to_numpy(np.float64)
    id_auc = float(roc_auc_score(y, id_values))
    id_bins = pd.qcut(train[ID_COL], q=100, labels=False, duplicates="drop")
    id_bin_rates = train.groupby(id_bins, observed=True)[TARGET].mean()

    result = {
        "experiment": "v19_clean_id_xgb",
        "competition": "playground-series-s6e8",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": "v13/v17 的互补增益是否依赖错误纳入的 id",
        "fold_contract": {
            "n_splits": N_FOLDS,
            "shuffle": True,
            "random_state": SEED,
            "row_order": "official train.csv order",
        },
        "feature_contract": {
            "dirty_feature_count": dirty_feature_count,
            "clean_feature_count": int(x_train.shape[1]),
            "removed": [ID_COL],
            "all_other_features_and_xgb_params_identical_to_v13": True,
        },
        "id_diagnostics": {
            "standalone_auc": id_auc,
            "target_rate_by_100_id_bins_min": float(id_bin_rates.min()),
            "target_rate_by_100_id_bins_max": float(id_bin_rates.max()),
            "target_rate_by_100_id_bins_std": float(id_bin_rates.std()),
            "test_id_entirely_outside_train_range": bool(test[ID_COL].min() > train[ID_COL].max()),
        },
        "single_model": {
            "dirty_v13_xgb_oof_auc": dirty_auc,
            "clean_v13_xgb_oof_auc": float(clean_auc),
            "delta_clean_minus_dirty": float(clean_auc - dirty_auc),
            "dirty_fold_auc": dirty_folds,
            "clean_fold_auc": clean_folds,
            "fold_delta_clean_minus_dirty": (
                np.asarray(clean_folds) - np.asarray(dirty_folds)
            ).tolist(),
            "folds_won": int(
                (np.asarray(clean_folds) > np.asarray(dirty_folds)).sum()
            ),
            "best_iterations": [int(x) for x in best_iterations],
        },
        "fixed_v17_weight_comparison": {
            "formula_dirty": "0.87*v8 + 0.13*v13_xgb_with_id",
            "formula_clean": "0.87*v8 + 0.13*v13_xgb_without_id",
            "dirty_oof_auc": dirty_v17_auc,
            "clean_oof_auc": clean_v17_auc,
            "delta_clean_minus_dirty": float(clean_v17_auc - dirty_v17_auc),
            "dirty_fold_auc": dirty_v17_folds,
            "clean_fold_auc": clean_v17_folds,
            "fold_delta_clean_minus_dirty": (
                np.asarray(clean_v17_folds) - np.asarray(dirty_v17_folds)
            ).tolist(),
            "folds_won": int(
                (np.asarray(clean_v17_folds) > np.asarray(dirty_v17_folds)).sum()
            ),
        },
        "outputs": {
            "clean_oof": "xgb_clean_oof_proba.npy",
            "clean_test": "xgb_clean_test_proba.npy",
            "clean_single_submission": "submission_xgb_clean.csv",
            "clean_fixed_pair_submission": "submission_v17_weight_clean_id.csv",
        },
        "source": {
            "v13_code": str(v13_source),
            "v13_code_sha256": sha256(v13_source),
            "dirty_oof_sha256": sha256(dirty_oof_path),
            "dirty_test_sha256": sha256(dirty_test_path),
            "v8_oof_sha256": sha256(v8_oof_path),
            "v8_test_sha256": sha256(v8_test_path),
        },
        "runtime_seconds": float(time.time() - started),
        "xgb_training_seconds": float(train_seconds),
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["single_model"], ensure_ascii=False, indent=2))
    print(json.dumps(result["fixed_v17_weight_comparison"], ensure_ascii=False, indent=2))
    print(f"[v19] results={OUT_DIR / 'cv_results.json'}")


if __name__ == "__main__":
    main()
