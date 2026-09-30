#!/usr/bin/env python3
"""V21 CatBoost candidate with exact-value, frequency and lattice features.

The candidate deliberately keeps the strongest part of v3: every one of the
12 raw inputs is represented twice where possible -- continuous numeric value
and an exact string category.  It then adds only label-free features:

* three validated screen-time budget quantities;
* exact-value frequency computed on train+test without labels;
* decimal/lattice phase features for the six non-integer hour columns.
* three explicit 0.1-grid pair categories, with optional label-free frequency.

Forbidden inputs are enforced in code: ``id``, row-level missing counts and
explicit missing flags never enter the model.  Categorical missing values are
represented by a string sentinel because CatBoost categorical columns cannot
contain floating NaN; numeric NaN remains native CatBoost missing data.

The default command starts the full five-fold experiment.  During development
use ``--smoke``; it builds the full feature family on a small sample and trains
only the first fixed fold with a tiny iteration budget.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool, __version__ as catboost_version
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "model"
OUT_DIR = Path(__file__).resolve().parent

TARGET = "addicted_label"
ID_COL = "id"
SEED = 42
N_FOLDS = 5
MISSING_CATEGORY = "__NA__"

RAW_COLS = [
    "age",
    "daily_screen_time_hours",
    "social_media_hours",
    "gaming_hours",
    "work_study_hours",
    "sleep_hours",
    "notifications_per_day",
    "app_opens_per_day",
    "weekend_screen_time",
    "gender",
    "stress_level",
    "academic_work_impact",
]
NUMERIC_COLS = [
    "age",
    "daily_screen_time_hours",
    "social_media_hours",
    "gaming_hours",
    "work_study_hours",
    "sleep_hours",
    "notifications_per_day",
    "app_opens_per_day",
    "weekend_screen_time",
]
COMPONENT_COLS = ["social_media_hours", "gaming_hours", "work_study_hours"]
DECIMAL_COLS = [
    "daily_screen_time_hours",
    "social_media_hours",
    "gaming_hours",
    "work_study_hours",
    "sleep_hours",
    "weekend_screen_time",
]
BUDGET_COLS = [
    "component_sum_available",
    "other_screen_available",
    "n_components_observed",
]
PAIR_SPECS = [
    ("daily_social", "daily_screen_time_hours", "social_media_hours"),
    ("social_weekend", "social_media_hours", "weekend_screen_time"),
    ("daily_weekend", "daily_screen_time_hours", "weekend_screen_time"),
]

FEATURE_SETS = {
    "budget": {"frequency": False, "lattice": False},
    "budget_freq": {"frequency": True, "lattice": False},
    "budget_lattice": {"frequency": False, "lattice": True},
    "full": {"frequency": True, "lattice": True},
}

# Identical to v3 for the first paired FE comparison.  Parameter tuning is a
# separate experiment and must not be mixed into the feature ablation.
CAT_PARAMS: dict[str, Any] = {
    "iterations": 3000,
    "learning_rate": 0.05,
    "depth": 8,
    "l2_leaf_reg": 6.0,
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "random_seed": SEED,
    "one_hot_max_size": 4,
    "max_ctr_complexity": 2,
    "od_type": "Iter",
    "od_wait": 200,
    "allow_writing_files": False,
    "thread_count": -1,
    "verbose": 200,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feature-set",
        choices=sorted(FEATURE_SETS),
        default="full",
        help="Paired feature block to train; full is the V21 candidate.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one tiny fixed fold only; never writes OOF/submission files.",
    )
    parser.add_argument("--smoke-train-rows", type=int, default=30000)
    parser.add_argument("--smoke-test-rows", type=int, default=8000)
    parser.add_argument("--smoke-iterations", type=int, default=60)
    parser.add_argument(
        "--pair-frequency",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Include label-free train+test pair frequencies. Default: enabled "
            "for feature sets that include raw frequency, disabled otherwise."
        ),
    )
    parser.add_argument(
        "--fold-only",
        type=int,
        choices=range(1, N_FOLDS + 1),
        default=None,
        help=(
            "Train one complete-data fold for screening. Outputs are explicitly "
            "named screening artifacts and are never called OOF/submission."
        ),
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data(
    train_rows: int | None = None, test_rows: int | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / "train.csv", nrows=train_rows)
    test = pd.read_csv(DATA_DIR / "test.csv", nrows=test_rows)
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv", nrows=test_rows)

    expected_train = [ID_COL, *RAW_COLS, TARGET]
    expected_test = [ID_COL, *RAW_COLS]
    if list(train.columns) != expected_train:
        raise ValueError(f"train 字段或顺序异常: {train.columns.tolist()}")
    if list(test.columns) != expected_test:
        raise ValueError(f"test 字段或顺序异常: {test.columns.tolist()}")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission 与 test 的 id 顺序不一致")
    if train[ID_COL].duplicated().any() or test[ID_COL].duplicated().any():
        raise ValueError("id 存在重复")
    if set(train[TARGET].unique()) != {0, 1}:
        raise ValueError("目标不是完整的 0/1 二分类")
    return train, test, sample


def exact_key(series: pd.Series) -> pd.Series:
    """Return v3-compatible string keys with no categorical NaN."""
    key = series.where(series.notna(), MISSING_CATEGORY).astype(str)
    if key.isna().any() or (key == "nan").any():
        raise AssertionError(f"{series.name} 的精确值 key 仍含未规范化缺失")
    return key


def tenth_grid_pair_key(
    frame: pd.DataFrame, left: str, right: str
) -> pd.Series:
    """Encode a pair as integer 0.1-grid ticks with an explicit NA sentinel."""
    left_values = frame[left].to_numpy(np.float64)
    right_values = frame[right].to_numpy(np.float64)
    valid = np.isfinite(left_values) & np.isfinite(right_values)
    output = np.full(len(frame), MISSING_CATEGORY, dtype=object)
    if valid.any():
        left_tick = np.rint(left_values[valid] * 10.0).astype(np.int32)
        right_tick = np.rint(right_values[valid] * 10.0).astype(np.int32)
        output[valid] = np.char.add(
            np.char.add(left_tick.astype(str), "|"), right_tick.astype(str)
        )
    return pd.Series(output, index=pd.RangeIndex(len(frame)), dtype=object)


def _add_budget_features(
    train_raw: pd.DataFrame,
    test_raw: pd.DataFrame,
    train_numeric: dict[str, np.ndarray],
    test_numeric: dict[str, np.ndarray],
) -> None:
    """Add the three v3 budget features, including component availability."""
    for source, target in (
        (train_raw, train_numeric),
        (test_raw, test_numeric),
    ):
        component_sum = source[COMPONENT_COLS].fillna(0.0).sum(axis=1)
        target["component_sum_available"] = component_sum.to_numpy(np.float64)
        target["other_screen_available"] = (
            source["daily_screen_time_hours"] - component_sum
        ).to_numpy(np.float64)
        target["n_components_observed"] = (
            source[COMPONENT_COLS].notna().sum(axis=1).to_numpy(np.float32)
        )


def _add_lattice_features(
    raw: pd.DataFrame, numeric: dict[str, np.ndarray]
) -> None:
    """Add non-boolean decimal phase features on the observed 0.01 lattice."""
    for col in DECIMAL_COLS:
        values = raw[col].to_numpy(np.float64)
        cents = np.rint(values * 100.0)
        phase_100 = np.mod(cents, 100.0)
        # NaN remains NaN in all three arrays and is handled natively by CatBoost.
        numeric[f"frac100_{col}"] = (phase_100 / 100.0).astype(np.float32)
        numeric[f"tenths_digit_{col}"] = np.floor(phase_100 / 10.0).astype(
            np.float32
        )
        numeric[f"hundredths_digit_{col}"] = np.mod(
            phase_100, 10.0
        ).astype(np.float32)


def build_features(
    train_raw: pd.DataFrame,
    test_raw: pd.DataFrame,
    feature_set: str,
    pair_frequency: bool | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, Any]]:
    """Build features without accepting either IDs or labels as inputs."""
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"未知 feature_set: {feature_set}")
    if list(train_raw.columns) != RAW_COLS or list(test_raw.columns) != RAW_COLS:
        raise ValueError("build_features 只接受严格的 12 个原始输入字段")

    use_frequency = FEATURE_SETS[feature_set]["frequency"]
    use_lattice = FEATURE_SETS[feature_set]["lattice"]
    use_pair_frequency = use_frequency if pair_frequency is None else pair_frequency

    train_numeric = {
        col: train_raw[col].to_numpy(np.float64, copy=True) for col in NUMERIC_COLS
    }
    test_numeric = {
        col: test_raw[col].to_numpy(np.float64, copy=True) for col in NUMERIC_COLS
    }
    _add_budget_features(train_raw, test_raw, train_numeric, test_numeric)
    if use_lattice:
        _add_lattice_features(train_raw, train_numeric)
        _add_lattice_features(test_raw, test_numeric)

    x_train = pd.DataFrame(train_numeric, index=pd.RangeIndex(len(train_raw)))
    x_test = pd.DataFrame(test_numeric, index=pd.RangeIndex(len(test_raw)))
    categorical_cols: list[str] = []
    frequency_cardinality: dict[str, int] = {}
    pair_cardinality: dict[str, int] = {}
    total_rows = len(train_raw) + len(test_raw)

    # Process one raw field at a time.  This avoids a 987k x 12 temporary object
    # matrix while still using the explicitly requested train+test frequencies.
    for col in RAW_COLS:
        train_key = exact_key(train_raw[col]).reset_index(drop=True)
        test_key = exact_key(test_raw[col]).reset_index(drop=True)
        combined_key = pd.concat([train_key, test_key], ignore_index=True)
        counts = combined_key.value_counts(sort=False, dropna=False)
        categories = pd.Index(counts.index, dtype=object)
        key_col = f"key_{col}"

        x_train[key_col] = pd.Categorical(train_key, categories=categories)
        x_test[key_col] = pd.Categorical(test_key, categories=categories)
        categorical_cols.append(key_col)
        frequency_cardinality[col] = int(len(categories))

        if use_frequency:
            freq_col = f"freq_exact_{col}"
            train_freq = train_key.map(counts).to_numpy(np.float32) / float(total_rows)
            test_freq = test_key.map(counts).to_numpy(np.float32) / float(total_rows)
            if not np.isfinite(train_freq).all() or not np.isfinite(test_freq).all():
                raise AssertionError(f"{col} 的 train+test frequency 映射失败")
            x_train[freq_col] = train_freq
            x_test[freq_col] = test_freq

        del train_key, test_key, combined_key, counts, categories

    # Explicit pair keys expose local interactions without asking CatBoost to
    # discover the 0.1 lattice and the cross-feature grouping simultaneously.
    for pair_name, left, right in PAIR_SPECS:
        train_key = tenth_grid_pair_key(train_raw, left, right)
        test_key = tenth_grid_pair_key(test_raw, left, right)
        combined_key = pd.concat([train_key, test_key], ignore_index=True)
        counts = combined_key.value_counts(sort=False, dropna=False)
        categories = pd.Index(counts.index, dtype=object)
        key_col = f"key_pair_{pair_name}_0p1"

        x_train[key_col] = pd.Categorical(train_key, categories=categories)
        x_test[key_col] = pd.Categorical(test_key, categories=categories)
        categorical_cols.append(key_col)
        pair_cardinality[pair_name] = int(len(categories))

        if use_pair_frequency:
            freq_col = f"freq_pair_{pair_name}_0p1"
            train_freq = train_key.map(counts).to_numpy(np.float32) / float(total_rows)
            test_freq = test_key.map(counts).to_numpy(np.float32) / float(total_rows)
            if not np.isfinite(train_freq).all() or not np.isfinite(test_freq).all():
                raise AssertionError(f"{pair_name} 的 pair frequency 映射失败")
            x_train[freq_col] = train_freq
            x_test[freq_col] = test_freq

        del train_key, test_key, combined_key, counts, categories

    # Consolidate numeric blocks after incremental construction.  Category
    # columns stay dictionary encoded, substantially reducing object memory.
    x_train = x_train.copy()
    x_test = x_test.copy()
    _validate_feature_contract(x_train, x_test, categorical_cols)

    memory = feature_memory_report(x_train, x_test)
    metadata = {
        "feature_set": feature_set,
        "uses_train_test_frequency": use_frequency,
        "uses_train_test_pair_frequency": use_pair_frequency,
        "frequency_uses_labels": False,
        "uses_lattice": use_lattice,
        "raw_numeric_count": len(NUMERIC_COLS),
        "budget_features": BUDGET_COLS,
        "raw_exact_key_count": len(RAW_COLS),
        "pair_key_count": len(PAIR_SPECS),
        "categorical_feature_count": len(categorical_cols),
        "frequency_feature_count": len(RAW_COLS) if use_frequency else 0,
        "pair_frequency_feature_count": (
            len(PAIR_SPECS) if use_pair_frequency else 0
        ),
        "lattice_feature_count": 3 * len(DECIMAL_COLS) if use_lattice else 0,
        "feature_count": int(x_train.shape[1]),
        "categorical_features": categorical_cols,
        "frequency_cardinality": frequency_cardinality,
        "pair_cardinality": pair_cardinality,
        "memory": memory,
    }
    return x_train, x_test, categorical_cols, metadata


def _validate_feature_contract(
    x_train: pd.DataFrame, x_test: pd.DataFrame, categorical_cols: list[str]
) -> None:
    if list(x_train.columns) != list(x_test.columns):
        raise AssertionError("训练/测试特征字段未对齐")
    if len(set(x_train.columns)) != len(x_train.columns):
        raise AssertionError("存在重复特征名")
    expected_cat_count = len(RAW_COLS) + len(PAIR_SPECS)
    if len(categorical_cols) != expected_cat_count:
        raise AssertionError("12 个原始 exact key 或三个 pair key 构建不完整")

    forbidden_exact = {ID_COL, TARGET}
    forbidden_tokens = ("missing_count", "n_missing", "_is_missing", "_missing_flag")
    bad = [
        col
        for col in x_train.columns
        if col in forbidden_exact or any(token in col for token in forbidden_tokens)
    ]
    if bad:
        raise AssertionError(f"禁用特征进入模型: {bad}")

    for col in categorical_cols:
        if not isinstance(x_train[col].dtype, pd.CategoricalDtype):
            raise AssertionError(f"{col} 未采用内存友好的 categorical dtype")
        if x_train[col].isna().any() or x_test[col].isna().any():
            raise AssertionError(f"{col} 含 CatBoost 不接受的类别 NaN")
        if MISSING_CATEGORY not in x_train[col].cat.categories:
            raise AssertionError(f"{col} 缺少统一缺失哨兵")

    numeric_cols = [col for col in x_train if col not in categorical_cols]
    train_numeric = x_train[numeric_cols].to_numpy(np.float64, copy=False)
    test_numeric = x_test[numeric_cols].to_numpy(np.float64, copy=False)
    if np.isinf(train_numeric).any() or np.isinf(test_numeric).any():
        raise AssertionError("数值特征含 inf；只允许 CatBoost 原生 NaN")


def feature_memory_report(
    x_train: pd.DataFrame, x_test: pd.DataFrame
) -> dict[str, Any]:
    train_bytes = int(x_train.memory_usage(index=True, deep=True).sum())
    test_bytes = int(x_test.memory_usage(index=True, deep=True).sum())
    return {
        "train_bytes": train_bytes,
        "test_bytes": test_bytes,
        "total_bytes": train_bytes + test_bytes,
        "total_mib": (train_bytes + test_bytes) / (1024**2),
        "train_bytes_per_row": train_bytes / max(len(x_train), 1),
        "test_bytes_per_row": test_bytes / max(len(x_test), 1),
    }


def resolved_pair_frequency(args: argparse.Namespace) -> bool:
    if args.pair_frequency is None:
        return bool(FEATURE_SETS[args.feature_set]["frequency"])
    return bool(args.pair_frequency)


def artifact_stem(args: argparse.Namespace) -> str:
    pair_suffix = "pairfreq" if resolved_pair_frequency(args) else "nopairfreq"
    return f"{args.feature_set}_{pair_suffix}"


def fixed_folds(y: np.ndarray) -> tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray]:
    folds = list(
        StratifiedKFold(
            n_splits=N_FOLDS, shuffle=True, random_state=SEED
        ).split(np.zeros(len(y), dtype=np.int8), y)
    )
    assignment = np.full(len(y), -1, dtype=np.int8)
    for fold_id, (_, valid_idx) in enumerate(folds):
        if (assignment[valid_idx] != -1).any():
            raise AssertionError("固定折发生验证行重复")
        assignment[valid_idx] = fold_id
    if (assignment < 0).any():
        raise AssertionError("固定折未覆盖全部官方训练行")
    return folds, assignment


def make_pool(
    frame: pd.DataFrame,
    categorical_cols: list[str],
    label: np.ndarray | None = None,
) -> Pool:
    return Pool(frame, label=label, cat_features=categorical_cols)


def validate_submission(
    submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame
) -> None:
    if submission.shape != sample.shape:
        raise ValueError(f"提交 shape 异常: {submission.shape} != {sample.shape}")
    if list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError(f"提交字段异常: {submission.columns.tolist()}")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与官方 test 顺序不一致")
    pred = submission[TARGET].to_numpy(np.float64)
    if not np.isfinite(pred).all() or ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率含 NaN/inf 或越界")


def run_smoke(args: argparse.Namespace) -> None:
    started = time.time()
    train, test, _ = load_data(args.smoke_train_rows, args.smoke_test_rows)
    y = train[TARGET].to_numpy(np.int8)
    x_train, x_test, categorical_cols, metadata = build_features(
        train[RAW_COLS].copy(),
        test[RAW_COLS].copy(),
        args.feature_set,
        pair_frequency=resolved_pair_frequency(args),
    )
    folds, assignment = fixed_folds(y)
    fit_idx, valid_idx = folds[0]

    smoke_params = dict(CAT_PARAMS)
    smoke_params.update(
        {
            "iterations": args.smoke_iterations,
            "od_wait": min(15, max(5, args.smoke_iterations // 4)),
            "thread_count": 4,
            "verbose": False,
        }
    )
    model = CatBoostClassifier(**smoke_params)
    train_pool = make_pool(
        x_train.iloc[fit_idx], categorical_cols, label=y[fit_idx]
    )
    valid_pool = make_pool(
        x_train.iloc[valid_idx], categorical_cols, label=y[valid_idx]
    )
    test_pool = make_pool(x_test, categorical_cols)
    model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
    valid_pred = model.predict_proba(valid_pool)[:, 1]
    test_pred = model.predict_proba(test_pool)[:, 1]

    if valid_pred.shape != (len(valid_idx),) or test_pred.shape != (len(test),):
        raise AssertionError("smoke 预测 shape 异常")
    if not np.isfinite(valid_pred).all() or not np.isfinite(test_pred).all():
        raise AssertionError("smoke 预测含非法值")

    full_train_rows = 691369
    full_test_rows = 296302
    linear_memory_estimate = (
        metadata["memory"]["train_bytes_per_row"] * full_train_rows
        + metadata["memory"]["test_bytes_per_row"] * full_test_rows
    )
    report = {
        "mode": "smoke",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "feature_set": args.feature_set,
        "sample_train_rows": len(train),
        "sample_test_rows": len(test),
        "fixed_fold_seed": SEED,
        "fixed_fold_assignment_unique": sorted(np.unique(assignment).tolist()),
        "feature_metadata": metadata,
        "linear_full_feature_frame_estimate_mib": linear_memory_estimate / (1024**2),
        "smoke_iterations": args.smoke_iterations,
        "best_iteration": int(model.get_best_iteration() + 1),
        "valid_auc": float(roc_auc_score(y[valid_idx], valid_pred)),
        "test_prediction_min": float(test_pred.min()),
        "test_prediction_max": float(test_pred.max()),
        "runtime_seconds": float(time.time() - started),
        "catboost_version": catboost_version,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    smoke_path = OUT_DIR / f"smoke_report_{artifact_stem(args)}.json"
    smoke_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def run_fold_screen(args: argparse.Namespace) -> None:
    """Train one full-data fold without creating an incomplete OOF artifact."""
    if args.fold_only is None:
        raise AssertionError("run_fold_screen 需要 --fold-only")
    started = time.time()
    train, test, _ = load_data()
    y = train[TARGET].to_numpy(np.int8)
    x_train, x_test, categorical_cols, metadata = build_features(
        train[RAW_COLS].copy(),
        test[RAW_COLS].copy(),
        args.feature_set,
        pair_frequency=resolved_pair_frequency(args),
    )
    folds, assignment = fixed_folds(y)
    fold_index = args.fold_only - 1
    fit_idx, valid_idx = folds[fold_index]

    train_pool = make_pool(x_train.iloc[fit_idx], categorical_cols, y[fit_idx])
    valid_pool = make_pool(x_train.iloc[valid_idx], categorical_cols, y[valid_idx])
    test_pool = make_pool(x_test, categorical_cols)
    model = CatBoostClassifier(**CAT_PARAMS)
    model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
    valid_pred = model.predict_proba(valid_pool)[:, 1]
    test_pred = model.predict_proba(test_pool)[:, 1]
    valid_auc = float(roc_auc_score(y[valid_idx], valid_pred))

    v3_result_path = MODEL_DIR / "v3_dual_catboost" / "cv_results.json"
    v3 = json.loads(v3_result_path.read_text(encoding="utf-8"))
    v3_fold_auc = float(v3["fold_auc"][fold_index])
    stem = f"{artifact_stem(args)}_fold{args.fold_only}of{N_FOLDS}_screening"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    valid_idx_path = OUT_DIR / f"valid_idx_{stem}.npy"
    valid_pred_path = OUT_DIR / f"valid_pred_{stem}.npy"
    test_pred_path = OUT_DIR / f"test_pred_{stem}.npy"
    assignment_path = OUT_DIR / "fold_assignment_seed42.npy"
    np.save(valid_idx_path, valid_idx)
    np.save(valid_pred_path, valid_pred)
    np.save(test_pred_path, test_pred)
    np.save(assignment_path, assignment)

    report = {
        "experiment": "v21_catboost_exact",
        "mode": "single_full_data_fold_screening",
        "is_complete_oof": False,
        "must_not_submit": True,
        "feature_set": args.feature_set,
        "pair_frequency": resolved_pair_frequency(args),
        "fold": args.fold_only,
        "n_folds_contract": N_FOLDS,
        "random_state": SEED,
        "official_row_order": True,
        "feature_metadata": metadata,
        "params": CAT_PARAMS,
        "valid_auc": valid_auc,
        "v3_same_fold_auc": v3_fold_auc,
        "delta_vs_v3_same_fold": valid_auc - v3_fold_auc,
        "best_iteration": int(model.get_best_iteration() + 1),
        "runtime_seconds": float(time.time() - started),
        "outputs": {
            "valid_idx": valid_idx_path.name,
            "valid_pred": valid_pred_path.name,
            "test_pred_for_diagnostics_only": test_pred_path.name,
            "fold_assignment": assignment_path.name,
        },
    }
    report_path = OUT_DIR / f"screening_results_{stem}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def run_full_cv(args: argparse.Namespace) -> None:
    started = time.time()
    train, test, sample = load_data()
    y = train[TARGET].to_numpy(np.int8)
    train_ids = train[ID_COL].to_numpy(np.int64)
    test_ids = test[ID_COL].to_numpy(np.int64)
    x_train, x_test, categorical_cols, metadata = build_features(
        train[RAW_COLS].copy(),
        test[RAW_COLS].copy(),
        args.feature_set,
        pair_frequency=resolved_pair_frequency(args),
    )
    folds, assignment = fixed_folds(y)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = artifact_stem(args)
    np.save(OUT_DIR / "fold_assignment_seed42.npy", assignment)
    np.save(OUT_DIR / "train_ids.npy", train_ids)
    np.save(OUT_DIR / "test_ids.npy", test_ids)

    oof = np.full(len(train), np.nan, dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[int] = []
    importance: list[np.ndarray] = []
    test_pool = make_pool(x_test, categorical_cols)

    for fold_id, (fit_idx, valid_idx) in enumerate(folds, start=1):
        fold_started = time.time()
        fit_frame = x_train.iloc[fit_idx]
        valid_frame = x_train.iloc[valid_idx]
        train_pool = make_pool(fit_frame, categorical_cols, label=y[fit_idx])
        valid_pool = make_pool(valid_frame, categorical_cols, label=y[valid_idx])
        del fit_frame, valid_frame
        gc.collect()

        model = CatBoostClassifier(**CAT_PARAMS)
        model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
        valid_pred = model.predict_proba(valid_pool)[:, 1]
        fold_test_pred = model.predict_proba(test_pool)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += fold_test_pred / N_FOLDS
        score = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(score)
        best_iterations.append(int(model.get_best_iteration() + 1))
        importance.append(model.get_feature_importance())
        print(
            f"[V21] feature_set={stem} fold={fold_id} auc={score:.6f} "
            f"best={best_iterations[-1]} elapsed={time.time()-fold_started:.1f}s"
        )
        del model, train_pool, valid_pool, valid_pred, fold_test_pred
        gc.collect()

    if not np.isfinite(oof).all() or not np.isfinite(test_pred).all():
        raise AssertionError("完整 CV 预测含 NaN/inf")
    oof_auc = float(roc_auc_score(y, oof))
    np.save(OUT_DIR / f"oof_{stem}.npy", oof)
    np.save(OUT_DIR / f"test_{stem}.npy", test_pred)

    submission = sample.copy()
    submission[TARGET] = np.clip(test_pred, 0.0, 1.0)
    validate_submission(submission, test, sample)
    submission_path = OUT_DIR / f"submission_{stem}.csv"
    submission.to_csv(submission_path, index=False)

    importance_frame = pd.DataFrame(
        {
            "feature": x_train.columns,
            "importance_mean": np.mean(np.vstack(importance), axis=0),
            "importance_std": np.std(np.vstack(importance), axis=0),
        }
    ).sort_values("importance_mean", ascending=False)
    importance_frame.to_csv(OUT_DIR / f"feature_importance_{stem}.csv", index=False)

    v3_result_path = MODEL_DIR / "v3_dual_catboost" / "cv_results.json"
    v3 = json.loads(v3_result_path.read_text(encoding="utf-8"))
    v3_folds = np.asarray(v3["fold_auc"], dtype=np.float64)
    fold_delta = np.asarray(fold_scores) - v3_folds
    result = {
        "experiment": "v21_catboost_exact",
        "feature_set": stem,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fold_contract": {
            "n_splits": N_FOLDS,
            "shuffle": True,
            "random_state": SEED,
            "row_order": "official train.csv order",
            "assignment_file": "fold_assignment_seed42.npy",
        },
        "feature_contract": metadata,
        "params": CAT_PARAMS,
        "fold_auc": fold_scores,
        "oof_auc": oof_auc,
        "best_iterations": best_iterations,
        "v3_reference_oof_auc": float(v3["oof_auc"]),
        "delta_vs_v3": oof_auc - float(v3["oof_auc"]),
        "fold_delta_vs_v3": fold_delta.tolist(),
        "folds_won_vs_v3": int((fold_delta > 0).sum()),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "runtime_seconds": float(time.time() - started),
        "catboost_version": catboost_version,
        "outputs": {
            "oof": f"oof_{stem}.npy",
            "test": f"test_{stem}.npy",
            "submission": submission_path.name,
            "feature_importance": f"feature_importance_{stem}.csv",
        },
        "source_sha256": {
            "script": sha256(Path(__file__)),
            "train": sha256(DATA_DIR / "train.csv"),
            "test": sha256(DATA_DIR / "test.csv"),
            "v3_result": sha256(v3_result_path),
        },
    }
    result_path = OUT_DIR / f"cv_results_{stem}.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    if args.smoke and args.fold_only is not None:
        raise SystemExit("--smoke 与 --fold-only 不能同时使用")
    if args.smoke:
        run_smoke(args)
    elif args.fold_only is not None:
        run_fold_screen(args)
    else:
        run_full_cv(args)


if __name__ == "__main__":
    main()
