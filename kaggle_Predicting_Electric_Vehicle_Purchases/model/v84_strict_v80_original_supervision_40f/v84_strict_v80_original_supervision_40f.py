# -*- coding: utf-8 -*-
"""C01-05：在 v80 严格基线上追加清洗后的 original 标签监督。

默认仅执行 audit。正式训练必须显式传入 ``--mode train``。所有目标编码统计只用
synthetic outer-train 标签；original 只应用既有映射并以权重1加入 fit。
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import gc
import hashlib
import importlib.util
import json
import os
import platform
import resource
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import lightgbm as lgb
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


EXPERIMENT_ID = "v84_strict_v80_original_supervision_40f"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
RECIPE_PATH = MODEL_DIR / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
V80_DIR = MODEL_DIR / "v80_strict_v61_outer104395303_40f"
V80_SCRIPT_PATH = (
    MODEL_DIR
    / "v80_strict_v61_outer104395303_40f"
    / "v80_strict_v61_outer104395303_40f.py"
)
V6_SCRIPT_PATH = MODEL_DIR / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
ORIGINAL_DATA_PATH = (
    DATA_DIR / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv"
)
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
PROGRESS_PATH = OUT_DIR / "progress.jsonl"
LOG_PATH = OUT_DIR / "train_log.txt"
LOCK_PATH = OUT_DIR / "run.lock"

OUTER_SEED = 104_395_303
INNER_TE_SEED_BASE = 104_395_303
MODEL_SEED = 104_395_303
N_FOLDS = 40
N_INNER_FOLDS = 5
ORIGINAL_ID_COLUMN = "Buyer_ID"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_ids(values: pd.Series) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def atomic_save_npy(path: Path, values: np.ndarray) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, values)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def load_frozen_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    scalar_contract = {
        "experiment_id": EXPERIMENT_ID,
        "n_folds": N_FOLDS,
        "outer_split_seed": OUTER_SEED,
        "n_inner_folds": N_INNER_FOLDS,
        "inner_te_seed_base": INNER_TE_SEED_BASE,
        "model_seed": MODEL_SEED,
    }
    for key, expected in scalar_contract.items():
        if config.get(key) != expected:
            raise ValueError(f"冻结配置 {key}={config.get(key)!r}，runner={expected!r}")
    if config.get("status") != "DESIGN_READY_NOT_STARTED":
        raise ValueError("冻结配置初始状态异常")
    if float(config.get("time_budget_minutes", -1)) != 60.0:
        raise ValueError("冻结墙钟预算必须为60分钟")
    if float(config.get("wall_clock_budget_seconds", -1)) != 3600.0:
        raise ValueError("冻结墙钟预算秒数必须为3600")
    if float(config.get("memory_budget_gb", -1)) != 16.0:
        raise ValueError("冻结内存预算必须为16 GiB")
    if int(config.get("peak_rss_budget_bytes", -1)) != 16 * 1024**3:
        raise ValueError("冻结 peak RSS 字节门槛必须为16 GiB")
    if config.get("matched_control") != "v80_strict_v61_outer104395303_40f":
        raise ValueError("matched control 必须冻结为 v80 strict outer104395303")
    if int(config.get("expected_original_raw_rows", -1)) != 10_000:
        raise ValueError("original 原始行数必须冻结为10000")
    if float(config.get("original_sample_weight", -1)) != 1.0:
        raise ValueError("original 样本权重必须固定为1")
    if int(config.get("shared_raw_feature_count", -1)) != 13:
        raise ValueError("共享建模原始特征数必须为13（ID不入模）")
    if float(config.get("minimum_matched_oof_delta", -1)) != 0.0001:
        raise ValueError("matched OOF 晋级门槛必须为+0.0001")
    if int(config.get("minimum_winning_folds", -1)) != 24:
        raise ValueError("逐折胜出门槛必须为24/40")
    if (
        int(config.get("futility_check_after_folds", -1)) != 10
        or float(config.get("futility_delta_below", 0.0)) != -0.00005
        or int(config.get("futility_max_winning_folds", -1)) != 4
    ):
        raise ValueError("10折中停门槛与冻结配置不一致")
    return config


def process_peak_rss_bytes() -> int:
    """返回当前进程历史 peak RSS；macOS 为 bytes，其余常见 Unix 为 KiB。"""
    raw_peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    peak_bytes = raw_peak if platform.system() == "Darwin" else raw_peak * 1024
    if peak_bytes < 0:
        raise ValueError("resource.getrusage 返回负 peak RSS")
    return peak_bytes


def classify_resource_breach(
    config: dict[str, Any], wall_elapsed_seconds: float, peak_rss_bytes: int
) -> list[str]:
    breaches: list[str] = []
    if wall_elapsed_seconds >= float(config["wall_clock_budget_seconds"]):
        breaches.append("WALL_CLOCK_BUDGET")
    if peak_rss_bytes > int(config["peak_rss_budget_bytes"]):
        breaches.append("PEAK_RSS_BUDGET")
    return breaches


def make_resource_check(
    config: dict[str, Any],
    *,
    started_monotonic: float,
    phase: str,
    fold: int | None,
) -> dict[str, Any]:
    wall_elapsed_seconds = float(time.monotonic() - started_monotonic)
    peak_bytes = process_peak_rss_bytes()
    breaches = classify_resource_breach(config, wall_elapsed_seconds, peak_bytes)
    return {
        "timestamp_utc": utc_now(),
        "phase": phase,
        "fold": fold,
        "status": "FAILED" if breaches else "OK",
        "breaches": breaches,
        "wall_elapsed_seconds": wall_elapsed_seconds,
        "wall_clock_budget_seconds": float(config["wall_clock_budget_seconds"]),
        "peak_rss_bytes": peak_bytes,
        "peak_rss_gib": peak_bytes / 1024**3,
        "peak_rss_budget_bytes": int(config["peak_rss_budget_bytes"]),
        "peak_rss_budget_gib": float(config["memory_budget_gb"]),
        "peak_rss_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
        "peak_rss_native_unit": (
            "bytes" if platform.system() == "Darwin" else "KiB"
        ),
    }


def validate_recorded_resource_check(
    config: dict[str, Any],
    check: dict[str, Any],
    *,
    expected_phase: str,
    expected_fold: int | None,
    must_pass: bool,
) -> None:
    if check.get("phase") != expected_phase or check.get("fold") != expected_fold:
        raise ValueError("资源检查 phase/fold 合同不一致")
    wall_elapsed = float(check["wall_elapsed_seconds"])
    peak_bytes = int(check["peak_rss_bytes"])
    if wall_elapsed < 0.0 or peak_bytes < 0:
        raise ValueError("资源检查出现负墙钟或负 peak RSS")
    if not np.isclose(
        float(check["peak_rss_gib"]), peak_bytes / 1024**3, atol=1e-12, rtol=0.0
    ):
        raise ValueError("资源检查 peak RSS bytes/GiB 不一致")
    if (
        float(check["wall_clock_budget_seconds"])
        != float(config["wall_clock_budget_seconds"])
        or int(check["peak_rss_budget_bytes"])
        != int(config["peak_rss_budget_bytes"])
        or float(check["peak_rss_budget_gib"])
        != float(config["memory_budget_gb"])
    ):
        raise ValueError("资源检查预算与冻结配置不一致")
    expected_breaches = classify_resource_breach(config, wall_elapsed, peak_bytes)
    if check.get("breaches") != expected_breaches:
        raise ValueError("资源检查 breach 复算不一致")
    expected_status = "FAILED" if expected_breaches else "OK"
    if check.get("status") != expected_status:
        raise ValueError("资源检查 status 复算不一致")
    if must_pass and expected_breaches:
        raise ValueError("COMPLETE 结果包含资源预算超限")


def record_resource_check(
    resource_checks: list[dict[str, Any]], check: dict[str, Any]
) -> None:
    resource_checks.append(check)
    append_progress({"evidence_level": "RESOURCE_BUDGET_CHECK", **check})


def load_recipe() -> Any:
    spec = importlib.util.spec_from_file_location("v84_v29_recipe", RECIPE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29 配方：{RECIPE_PATH}")
    recipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recipe)
    recipe.base.factorize_joint = recipe.factorize_joint_extended
    recipe.base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    return recipe


def strict_encode_key(
    train_codes: np.ndarray,
    test_codes: np.ndarray,
    original_codes: np.ndarray,
    y: np.ndarray,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    inner_folds: list[tuple[np.ndarray, np.ndarray]],
    smooths: tuple[float, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """严格嵌套TE；original仅应用 synthetic outer-fit 标签映射。"""
    fit_codes = train_codes[fit_idx]
    valid_codes = train_codes[valid_idx]
    y_fit = y[fit_idx].astype(np.float64)
    n_categories = int(
        max(train_codes.max(), test_codes.max(), original_codes.max(initial=-1))
    ) + 1
    fit_block = np.empty((len(fit_idx), len(smooths)), dtype=np.float32)
    inner_coverage = np.zeros(len(fit_idx), dtype=np.int8)

    for inner_train, inner_hold in inner_folds:
        if np.intersect1d(inner_train, inner_hold, assume_unique=True).size:
            raise ValueError("inner train/hold 索引重叠")
        if len(inner_train) + len(inner_hold) != len(fit_idx):
            raise ValueError("inner train/hold 未完整划分 outer-fit")
        inner_train_codes = fit_codes[inner_train]
        inner_train_y = y_fit[inner_train]
        inner_prior = float(inner_train_y.mean())
        inner_count = np.bincount(
            inner_train_codes, minlength=n_categories
        ).astype(np.float64)
        inner_target_sum = np.bincount(
            inner_train_codes, weights=inner_train_y, minlength=n_categories
        )
        hold_codes = fit_codes[inner_hold]
        for column, smooth in enumerate(smooths):
            mapping = (
                inner_target_sum + float(smooth) * inner_prior
            ) / (inner_count + float(smooth))
            fit_block[inner_hold, column] = mapping[hold_codes]
        inner_coverage[inner_hold] += 1

    if not np.all(inner_coverage == 1):
        raise ValueError("inner OOF coverage 不是恰好一次")

    outer_prior = float(y_fit.mean())
    outer_count = np.bincount(fit_codes, minlength=n_categories).astype(np.float64)
    outer_target_sum = np.bincount(
        fit_codes, weights=y_fit, minlength=n_categories
    )
    valid_block = np.empty((len(valid_idx), len(smooths)), dtype=np.float32)
    test_block = np.empty((len(test_codes), len(smooths)), dtype=np.float32)
    original_block = np.empty((len(original_codes), len(smooths)), dtype=np.float32)
    for column, smooth in enumerate(smooths):
        mapping = (
            outer_target_sum + float(smooth) * outer_prior
        ) / (outer_count + float(smooth))
        valid_block[:, column] = mapping[valid_codes]
        test_block[:, column] = mapping[test_codes]
        original_block[:, column] = mapping[original_codes]

    for name, block in (
        ("fit", fit_block),
        ("valid", valid_block),
        ("test", test_block),
        ("original", original_block),
    ):
        if not np.isfinite(block).all() or ((block < 0.0) | (block > 1.0)).any():
            raise ValueError(f"strict TE {name} block 概率非法")
    return fit_block, valid_block, test_block, original_block


def strict_prior_self_check() -> None:
    train_codes = np.asarray([0, 0, 1, 1, 2, 2, 0, 1, 2, 3, 3, 3, 0, 2], dtype=np.int32)
    test_codes = np.asarray([0, 1, 2, 3], dtype=np.int32)
    original_codes = np.asarray([0, 4], dtype=np.int32)
    y = np.asarray([0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1], dtype=np.int8)
    fit_idx = np.arange(12, dtype=np.int64)
    valid_idx = np.arange(12, 14, dtype=np.int64)
    inner_folds = list(
        StratifiedKFold(n_splits=3, shuffle=True, random_state=INNER_TE_SEED_BASE).split(
            np.zeros(len(fit_idx)), y[fit_idx]
        )
    )
    original = strict_encode_key(
        train_codes,
        test_codes,
        original_codes,
        y,
        fit_idx,
        valid_idx,
        inner_folds,
        (5.0, 15.0, 80.0),
    )
    first_inner_train, first_inner_hold = inner_folds[0]
    changed_y = y.copy()
    changed_y[fit_idx[first_inner_hold]] = 1 - changed_y[fit_idx[first_inner_hold]]
    changed = strict_encode_key(
        train_codes,
        test_codes,
        original_codes,
        changed_y,
        fit_idx,
        valid_idx,
        inner_folds,
        (5.0, 15.0, 80.0),
    )
    if not np.array_equal(original[0][first_inner_hold], changed[0][first_inner_hold]):
        raise AssertionError("inner hold 标签改变后自身 TE 发生变化，存在 prior 泄漏")
    if np.array_equal(original[1], changed[1]):
        raise AssertionError("outer-valid TE 未响应 outer-fit 标签变化，自检无效")

    inner_codes = train_codes[fit_idx][first_inner_train]
    inner_y = y[fit_idx][first_inner_train].astype(np.float64)
    held_code = train_codes[fit_idx][first_inner_hold[0]]
    count = float(np.sum(inner_codes == held_code))
    target_sum = float(inner_y[inner_codes == held_code].sum())
    expected = (target_sum + 5.0 * float(inner_y.mean())) / (count + 5.0)
    if not np.isclose(
        float(original[0][first_inner_hold[0], 0]), expected, atol=1e-7, rtol=0.0
    ):
        raise AssertionError("inner-train prior 公式自检失败")
    expected_outer_prior = float(y[fit_idx].mean())
    if not np.allclose(
        original[3][1], expected_outer_prior, atol=1e-7, rtol=0.0
    ):
        raise AssertionError("original 未见 key 未回退到 synthetic outer-fit prior")


def validate_lightgbm_version_contract(
    config: dict[str, Any], control: dict[str, Any], runtime_version: str
) -> None:
    control_version = str(control.get("runtime", {}).get("lightgbm", ""))
    if config.get("required_lightgbm_version") != control_version:
        raise ValueError("冻结 LightGBM 版本与 matched v80 不一致")
    if runtime_version != control_version:
        raise RuntimeError(
            "当前 LightGBM 版本与 matched v80 不一致："
            f"runtime={runtime_version}, control={control_version}"
        )


def validate_v80_contract(config: dict[str, Any], recipe: Any) -> dict[str, Any]:
    control = json.loads((V80_DIR / "cv_results.json").read_text(encoding="utf-8"))
    if control.get("status") != "COMPLETE":
        raise RuntimeError("formal trigger 未满足：matched v80 必须 COMPLETE")
    if control.get("experiment_id") != config["matched_control"]:
        raise ValueError("matched v80 experiment_id 与冻结配置不一致")
    if control["params"] != config["lightgbm_params"]:
        raise ValueError("冻结 LightGBM 参数与 matched v80 不一致")
    if control["te_keys"] != config["te_keys"]:
        raise ValueError("冻结 TE keys 与 matched v80 不一致")
    if control["smooths"] != config["smooths"]:
        raise ValueError("冻结 smoothing 与 matched v80 不一致")
    if int(control["n_folds"]) != N_FOLDS:
        raise ValueError("冻结 outer folds 与 matched v80 不一致")
    if int(control["n_inner_folds"]) != N_INNER_FOLDS:
        raise ValueError("冻结 inner folds 与 matched v80 不一致")
    if int(control["outer_split_seed"]) != OUTER_SEED:
        raise ValueError("冻结 outer seed 与 matched v80 不一致")
    if int(control["inner_te_seed_base"]) != INNER_TE_SEED_BASE:
        raise ValueError("冻结 inner seed base 与 matched v80 不一致")
    if int(control["model_seed"]) != MODEL_SEED:
        raise ValueError("冻结 model seed 与 matched v80 不一致")
    if control["strict_prior_contract"] != config["strict_prior_contract"]:
        raise ValueError("strict prior 合同与 matched v80 不一致")
    if not np.isclose(
        float(control["oof_auc"]),
        float(config["matched_control_oof_auc"]),
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("matched v80 OOF 与冻结配置不一致")
    validate_lightgbm_version_contract(config, control, lgb.__version__)
    if recipe.base.TE_KEYS != config["te_keys"]:
        raise ValueError("运行时 TE keys 与冻结配置不一致")
    if list(recipe.base.SMOOTHS) != config["smooths"]:
        raise ValueError("运行时 smoothing 与冻结配置不一致")
    for key in (
        "random_state",
        "bagging_seed",
        "feature_fraction_seed",
        "data_random_seed",
    ):
        if int(config["lightgbm_params"][key]) != MODEL_SEED:
            raise ValueError(f"{key} 未保持 matched v80 model seed")
    return control


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(PROJECT_DIR)),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def build_run_contract() -> dict[str, Any]:
    source_paths = {
        "candidate_runner": Path(__file__).resolve(),
        "frozen_config": CONFIG_PATH,
        "matched_v80_runner": V80_SCRIPT_PATH,
        "matched_v80_config": V80_DIR / "frozen_config.json",
        "matched_v80_cv_results": V80_DIR / "cv_results.json",
        "matched_v80_oof": V80_DIR / "oof_proba.npy",
        "matched_v80_test": V80_DIR / "test_proba.npy",
        "v29_recipe": RECIPE_PATH,
        "v6_recipe": V6_SCRIPT_PATH,
        "train_csv": DATA_DIR / "train.csv",
        "test_csv": DATA_DIR / "test.csv",
        "sample_submission_csv": DATA_DIR / "sample_submission.csv",
        "original_csv": ORIGINAL_DATA_PATH,
    }
    missing = [str(path) for path in source_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"运行合同来源文件缺失：{missing}")
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "frozen_config_sha256": sha256_file(CONFIG_PATH),
        "sources": {name: file_record(path) for name, path in source_paths.items()},
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "lightgbm": lgb.__version__,
        },
    }
    payload["run_contract_sha256"] = sha256_json(payload)
    return payload


def validate_probability_array(name: str, values: np.ndarray, expected: int) -> None:
    if values.shape != (expected,):
        raise ValueError(f"{name} shape={values.shape}，预期 {(expected,)}")
    if not np.issubdtype(values.dtype, np.number):
        raise ValueError(f"{name} dtype 非数值：{values.dtype}")
    if not np.isfinite(values).all():
        raise ValueError(f"{name} 含 NaN/Inf")
    if ((values < 0.0) | (values > 1.0)).any():
        raise ValueError(f"{name} 含 [0,1] 外概率")


def normalized_key_series(frame: pd.DataFrame, cols: list[str]) -> pd.Series:
    """复现 v29/v6 key 字符串；缺失只在 apply 侧成为未见 key。"""
    parts: list[pd.Series] = []
    for col in cols:
        if col in {"_income_bin10", "_income_bin100"}:
            divisor = 10 if col == "_income_bin10" else 100
            numeric = pd.to_numeric(frame["Annual_Income_USD"], errors="raise")
            part = (numeric // divisor).astype("Int64").astype("string")
        else:
            part = frame[col].astype("string")
        parts.append(part.fillna("__V84_MISSING__"))
    key = parts[0]
    for part in parts[1:]:
        key = key.str.cat(part, sep="|")
    return key


def build_apply_static_features(
    recipe: Any,
    train: pd.DataFrame,
    test: pd.DataFrame,
    apply_frame: pd.DataFrame,
    synthetic_static_columns: list[str],
    keys_train: dict[str, np.ndarray],
    keys_test: dict[str, np.ndarray],
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """仅用 synthetic train+test 拟合无标签变换，再应用到 original。"""
    raw_features = list(recipe.base.RAW_FEATURES)
    combined = pd.concat([train[raw_features], test[raw_features]], ignore_index=True)
    static = pd.DataFrame(index=apply_frame.index)
    for col in recipe.base.NUMERIC_FEATURES:
        static[col] = pd.to_numeric(apply_frame[col], errors="raise").astype(np.float32)
    for col in recipe.base.CATEGORICAL_FEATURES:
        _, uniques = pd.factorize(combined[col].astype("string"), sort=True)
        codes = uniques.get_indexer(apply_frame[col].astype("string"))
        static[col] = codes.astype(np.int8)

    for col in recipe.base.NUMERIC_FEATURES:
        values = apply_frame[col].fillna(0).to_numpy(np.float64)
        for power in range(-4, 4):
            digit = np.floor(values / (10.0**power)).astype(np.int64) % 10
            static[f"{col}_digit_{power}"] = digit.astype(np.int8)

    for col in raw_features:
        synthetic_values = combined[col].astype("string")
        frequencies = synthetic_values.value_counts(normalize=True, dropna=False)
        static[f"freq_{col}"] = (
            apply_frame[col]
            .astype("string")
            .map(frequencies)
            .fillna(0.0)
            .astype(np.float32)
        )
    static = static.astype(np.float32)

    apply_keys: dict[str, np.ndarray] = {}
    for name, cols in recipe.base.TE_KEYS.items():
        if name == "income_bin10":
            synthetic_key = (
                pd.to_numeric(combined["Annual_Income_USD"], errors="raise") // 10
            ).astype(np.int64)
            apply_key = (
                pd.to_numeric(apply_frame["Annual_Income_USD"], errors="raise") // 10
            ).astype("Int64")
        else:
            synthetic_key = normalized_key_series(combined, list(cols))
            apply_key = normalized_key_series(apply_frame, list(cols))
        synthetic_codes, uniques = pd.factorize(synthetic_key, sort=True)
        expected_codes = np.concatenate([keys_train[name], keys_test[name]])
        if not np.array_equal(synthetic_codes.astype(np.int32), expected_codes):
            raise ValueError(f"key={name} apply 编码未复现 synthetic 配方")
        apply_code = uniques.get_indexer(apply_key)
        unseen_code = len(uniques)
        apply_code = np.where(apply_code < 0, unseen_code, apply_code).astype(np.int32)
        apply_keys[name] = apply_code
        counts = np.bincount(synthetic_codes, minlength=len(uniques)).astype(np.float64)
        extended = np.append(counts, 0.0)
        static[f"freq_key_{name}"] = (
            extended[apply_code] / len(synthetic_codes)
        ).astype(np.float32)

    missing_columns = sorted(set(synthetic_static_columns) - set(static.columns))
    if missing_columns:
        raise ValueError(f"original static 缺少列：{missing_columns}")
    static = static[synthetic_static_columns].reset_index(drop=True).astype(np.float32)
    values = static.to_numpy(np.float32)
    if np.isinf(values).any():
        raise ValueError("original static 含 Inf")
    return static, apply_keys


def exact_original_duplicate_mask(
    original: pd.DataFrame,
    train: pd.DataFrame,
    test: pd.DataFrame,
    shared_features: list[str],
) -> np.ndarray:
    synthetic_keys = pd.concat(
        [train[shared_features], test[shared_features]], ignore_index=True
    ).drop_duplicates(ignore_index=True)
    probe = original[shared_features].copy()
    probe["__v84_original_position__"] = np.arange(len(probe), dtype=np.int64)
    matched = probe.merge(
        synthetic_keys.assign(__v84_exact_match__=True),
        on=shared_features,
        how="left",
        sort=False,
        validate="many_to_one",
    ).sort_values("__v84_original_position__")
    if not np.array_equal(
        matched["__v84_original_position__"].to_numpy(np.int64),
        np.arange(len(original), dtype=np.int64),
    ):
        raise ValueError("original 精确重复检查改变了行序")
    return matched["__v84_exact_match__"].eq(True).to_numpy(bool)


def psi_numeric(reference: pd.Series, current: pd.Series) -> tuple[float, int]:
    reference_values = pd.to_numeric(reference, errors="raise")
    current_values = pd.to_numeric(current, errors="raise")
    edges = np.unique(
        np.quantile(reference_values.dropna().to_numpy(), np.linspace(0.0, 1.0, 11))
    )
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_count = np.histogram(reference_values.dropna(), bins=edges)[0].astype(float)
    current_count = np.histogram(current_values.dropna(), bins=edges)[0].astype(float)
    reference_count = np.append(reference_count, reference_values.isna().sum())
    current_count = np.append(current_count, current_values.isna().sum())
    reference_share = np.maximum(reference_count / len(reference_values), 1e-6)
    current_share = np.maximum(current_count / len(current_values), 1e-6)
    psi = np.sum(
        (current_share - reference_share) * np.log(current_share / reference_share)
    )
    return float(psi), len(edges) - 1


def psi_categorical(reference: pd.Series, current: pd.Series) -> tuple[float, int]:
    reference_values = reference.astype("string").fillna("__V84_MISSING__")
    current_values = current.astype("string").fillna("__V84_MISSING__")
    categories = sorted(set(reference_values.tolist()) | set(current_values.tolist()))
    reference_share = np.maximum(
        reference_values.value_counts(normalize=True)
        .reindex(categories, fill_value=0.0)
        .to_numpy(),
        1e-6,
    )
    current_share = np.maximum(
        current_values.value_counts(normalize=True)
        .reindex(categories, fill_value=0.0)
        .to_numpy(),
        1e-6,
    )
    psi = np.sum(
        (current_share - reference_share) * np.log(current_share / reference_share)
    )
    return float(psi), len(categories)


def fixed_source_classifier_diagnostic(
    config: dict[str, Any],
    train: pd.DataFrame,
    original: pd.DataFrame,
    shared_features: list[str],
    numeric_features: list[str],
) -> dict[str, Any]:
    """固定、无调参的来源可分性诊断；禁止影响候选设计。"""
    seed = int(config["source_diagnostic"]["seed"])
    sample_size = int(config["source_diagnostic"]["synthetic_sample_rows"])
    synthetic_sample = train.sample(
        n=sample_size, replace=False, random_state=seed
    )[shared_features]
    sample_index = synthetic_sample.index.to_numpy(np.int64)
    x = pd.concat([synthetic_sample, original[shared_features]], ignore_index=True)
    y_source = np.concatenate(
        [
            np.zeros(len(synthetic_sample), dtype=np.int8),
            np.ones(len(original), dtype=np.int8),
        ]
    )
    categorical_features = [
        feature for feature in shared_features if feature not in numeric_features
    ]
    splitter = StratifiedKFold(
        n_splits=int(config["source_diagnostic"]["n_folds"]),
        shuffle=True,
        random_state=seed,
    )
    oof = np.zeros(len(x), dtype=np.float64)
    fold_auc: list[float] = []
    for fit_idx, valid_idx in splitter.split(x, y_source):
        preprocessor = ColumnTransformer(
            [
                (
                    "numeric",
                    SimpleImputer(strategy="median", add_indicator=True),
                    numeric_features,
                ),
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    categorical_features,
                ),
            ],
            sparse_threshold=0.0,
        )
        model = Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "classifier",
                    HistGradientBoostingClassifier(
                        max_iter=100,
                        learning_rate=0.05,
                        max_leaf_nodes=15,
                        l2_regularization=1.0,
                        random_state=seed,
                    ),
                ),
            ]
        )
        model.fit(x.iloc[fit_idx], y_source[fit_idx])
        oof[valid_idx] = model.predict_proba(x.iloc[valid_idx])[:, 1]
        fold_auc.append(float(roc_auc_score(y_source[valid_idx], oof[valid_idx])))
    return {
        "meaning": "DIAGNOSTIC_ONLY_NOT_FOR_TUNING_OR_GATE",
        "synthetic_sample_index_sha256": hashlib.sha256(
            sample_index.tobytes()
        ).hexdigest(),
        "oof_auc": float(roc_auc_score(y_source, oof)),
        "fold_auc": fold_auc,
    }


def validate_original_data_contract(
    config: dict[str, Any],
    recipe: Any,
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    run_source_classifier: bool,
) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any]]:
    original = pd.read_csv(ORIGINAL_DATA_PATH)
    expected_columns = list(config["original_expected_columns"])
    if list(original.columns) != expected_columns:
        raise ValueError("original schema/列序与冻结配置不一致")
    if len(original) != int(config["expected_original_raw_rows"]):
        raise ValueError("original 行数与冻结配置不一致")
    if original[ORIGINAL_ID_COLUMN].isna().any() or not original[ORIGINAL_ID_COLUMN].is_unique:
        raise ValueError("original Buyer_ID 必须非空且唯一")
    shared_features = list(recipe.base.RAW_FEATURES)
    if shared_features != config["shared_raw_features"]:
        raise ValueError("13个共享建模特征与冻结配置不一致")
    if ORIGINAL_ID_COLUMN in shared_features or config["id_column"] in shared_features:
        raise ValueError("ID 不得进入建模或重复键")
    if set(original[config["target"]].unique()) != set(config["allowed_target_labels"]):
        raise ValueError("original 标签映射不是冻结的 Yes/No")
    duplicate_mask = exact_original_duplicate_mask(
        original, train, test, shared_features
    )
    if int(duplicate_mask.sum()) != int(
        config["expected_original_exact_duplicate_matches"]
    ):
        raise ValueError("original 与 synthetic train/test 精确重复数漂移")
    cleaned = original.loc[~duplicate_mask].reset_index(drop=True)
    if len(cleaned) != int(config["expected_original_clean_rows"]):
        raise ValueError("original 去重后行数与冻结配置不一致")
    if len(cleaned[shared_features].drop_duplicates()) != int(
        config["expected_original_shared_feature_unique_rows"]
    ):
        raise ValueError("original 共享建模特征内部重复数漂移")
    original_y = cleaned[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    class_counts = cleaned[config["target"]].value_counts().sort_index().to_dict()
    missing_counts = {
        key: int(value)
        for key, value in cleaned[shared_features].isna().sum().items()
        if int(value) > 0
    }
    if class_counts != config["expected_original_class_counts"]:
        raise ValueError("original 标签计数与冻结配置不一致")
    if missing_counts != config["expected_original_missing_counts"]:
        raise ValueError("original 缺失值计数与冻结配置不一致")

    psi_by_feature: dict[str, dict[str, float | int]] = {}
    for feature in shared_features:
        if feature in recipe.base.NUMERIC_FEATURES:
            psi, bins = psi_numeric(train[feature], cleaned[feature])
        else:
            psi, bins = psi_categorical(train[feature], cleaned[feature])
        psi_by_feature[feature] = {"psi": psi, "bins": bins}
    frozen_psi = config["preflight_data_diagnostics"]["psi_vs_synthetic_train"]
    for feature, diagnostic in psi_by_feature.items():
        if int(diagnostic["bins"]) != int(frozen_psi[feature]["bins"]) or not np.isclose(
            float(diagnostic["psi"]),
            float(frozen_psi[feature]["psi"]),
            atol=1e-12,
            rtol=0.0,
        ):
            raise ValueError(f"original PSI 漂移：{feature}")

    diagnostics: dict[str, Any] = {
        "evidence_level": "PREFLIGHT_DIAGNOSTIC_NOT_MODEL_EVIDENCE",
        "raw_rows": len(original),
        "exact_duplicates_vs_synthetic_train_test": int(duplicate_mask.sum()),
        "clean_rows": len(cleaned),
        "shared_feature_unique_rows": int(
            len(cleaned[shared_features].drop_duplicates())
        ),
        "shared_feature_count": len(shared_features),
        "dedup_key_excludes_ids": True,
        "original_id_unique_non_null": True,
        "synthetic_ids_unique_non_null": True,
        "class_counts": class_counts,
        "missing_counts": missing_counts,
        "psi_vs_synthetic_train": psi_by_feature,
        "source_classifier": None,
    }
    if run_source_classifier:
        source = fixed_source_classifier_diagnostic(
            config,
            train,
            cleaned,
            shared_features,
            list(recipe.base.NUMERIC_FEATURES),
        )
        frozen_source = config["preflight_data_diagnostics"]["source_classifier"]
        if source["synthetic_sample_index_sha256"] != frozen_source[
            "synthetic_sample_index_sha256"
        ]:
            raise ValueError("source classifier synthetic 样本索引哈希漂移")
        if not np.isclose(
            source["oof_auc"], frozen_source["oof_auc"], atol=1e-12, rtol=0.0
        ) or not np.allclose(
            source["fold_auc"], frozen_source["fold_auc"], atol=1e-12, rtol=0.0
        ):
            raise ValueError("source classifier 固定诊断结果漂移")
        diagnostics["source_classifier"] = source
    return cleaned, original_y, diagnostics


def validate_data_contract(
    config: dict[str, Any], recipe: Any
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, dict[str, Any]]:
    train, test, sample = recipe.base.load_data()
    if len(train) != int(config["expected_train_rows"]):
        raise ValueError("train 行数与冻结配置不一致")
    if len(test) != int(config["expected_test_rows"]):
        raise ValueError("test 行数与冻结配置不一致")
    if not train[config["id_column"]].is_unique or not test[config["id_column"]].is_unique:
        raise ValueError("train/test id 必须唯一")
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample_submission 与 test id 行序不一致")
    control = json.loads((V80_DIR / "cv_results.json").read_text(encoding="utf-8"))
    control_oof = np.load(V80_DIR / "oof_proba.npy", mmap_mode="r")
    control_test = np.load(V80_DIR / "test_proba.npy", mmap_mode="r")
    validate_probability_array("matched_v80_oof", control_oof, len(train))
    validate_probability_array("matched_v80_test", control_test, len(test))
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    recomputed = float(roc_auc_score(y, control_oof))
    if not np.isclose(recomputed, control["oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("matched v80 OOF 复算与 cv_results 不一致")
    if not np.isclose(
        recomputed,
        config["matched_control_oof_auc"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("matched v80 OOF 与冻结参考值不一致")
    return train, test, sample, control_oof, control_test, control


class RunLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def emit(self, message: str) -> None:
        line = f"{utc_now()} {message}"
        print(line, flush=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def append_progress(payload: dict[str, Any]) -> None:
    with PROGRESS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


@contextlib.contextmanager
def exclusive_run_lock(lock_path: Path, run_contract_sha256: str) -> Iterator[None]:
    """以内核 advisory lock 保证单实例；不做 check-then-unlink。"""
    handle = lock_path.open("a+", encoding="utf-8")
    acquired = False
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError as error:
            handle.seek(0)
            owner = handle.read().strip() or "unknown owner"
            raise RuntimeError(f"已有 v80 实例持有 flock：{owner}") from error
        running = {
            "status": "RUNNING",
            "pid": os.getpid(),
            "experiment_id": EXPERIMENT_ID,
            "run_contract_sha256": run_contract_sha256,
            "acquired_at_utc": utc_now(),
        }
        handle.seek(0)
        handle.truncate()
        json.dump(running, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        yield
    finally:
        try:
            if acquired:
                released = {
                    "status": "RELEASED",
                    "pid": os.getpid(),
                    "experiment_id": EXPERIMENT_ID,
                    "run_contract_sha256": run_contract_sha256,
                    "released_at_utc": utc_now(),
                }
                handle.seek(0)
                handle.truncate()
                json.dump(released, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def save_checkpoint(
    path: Path,
    *,
    fold: int,
    valid_idx: np.ndarray,
    valid_pred: np.ndarray,
    test_pred: np.ndarray,
    best_iteration: int,
    gain: np.ndarray,
    split: np.ndarray,
    fold_auc: float,
    elapsed_seconds: float,
    config_sha256: str,
    run_contract_sha256: str,
) -> None:
    temporary = path.with_suffix(".tmp.npz")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            fold=np.asarray(fold, dtype=np.int16),
            valid_idx=valid_idx.astype(np.int64, copy=False),
            valid_idx_sha256=np.asarray(hashlib.sha256(valid_idx.tobytes()).hexdigest()),
            valid_pred=valid_pred.astype(np.float64, copy=False),
            test_pred=test_pred.astype(np.float64, copy=False),
            best_iteration=np.asarray(best_iteration, dtype=np.int32),
            gain=gain.astype(np.float64, copy=False),
            split=split.astype(np.float64, copy=False),
            fold_auc=np.asarray(fold_auc, dtype=np.float64),
            elapsed_seconds=np.asarray(elapsed_seconds, dtype=np.float64),
            config_sha256=np.asarray(config_sha256),
            run_contract_sha256=np.asarray(run_contract_sha256),
        )
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def load_checkpoint(
    path: Path,
    *,
    fold: int,
    valid_idx: np.ndarray,
    test_rows: int,
    feature_count: int,
    config_sha256: str,
    run_contract_sha256: str,
) -> dict[str, Any]:
    required = {
        "fold",
        "valid_idx",
        "valid_idx_sha256",
        "valid_pred",
        "test_pred",
        "best_iteration",
        "gain",
        "split",
        "fold_auc",
        "elapsed_seconds",
        "config_sha256",
        "run_contract_sha256",
    }
    with np.load(path, allow_pickle=False) as saved:
        if set(saved.files) != required:
            raise ValueError(f"{path.name} checkpoint schema 不一致")
        if int(saved["fold"].item()) != fold:
            raise ValueError(f"{path.name} fold 编号不一致")
        if str(saved["config_sha256"].item()) != config_sha256:
            raise ValueError(f"{path.name} 配置哈希不一致，拒绝恢复")
        if str(saved["run_contract_sha256"].item()) != run_contract_sha256:
            raise ValueError(f"{path.name} 代码/输入合同哈希不一致，拒绝恢复")
        stored_idx = saved["valid_idx"].astype(np.int64, copy=True)
        if not np.array_equal(stored_idx, valid_idx):
            raise ValueError(f"{path.name} valid_idx 不一致")
        idx_hash = hashlib.sha256(stored_idx.tobytes()).hexdigest()
        if str(saved["valid_idx_sha256"].item()) != idx_hash:
            raise ValueError(f"{path.name} valid_idx 哈希损坏")
        payload = {
            "valid_pred": saved["valid_pred"].astype(np.float64, copy=True),
            "test_pred": saved["test_pred"].astype(np.float64, copy=True),
            "best_iteration": int(saved["best_iteration"].item()),
            "gain": saved["gain"].astype(np.float64, copy=True),
            "split": saved["split"].astype(np.float64, copy=True),
            "fold_auc": float(saved["fold_auc"].item()),
            "elapsed_seconds": float(saved["elapsed_seconds"].item()),
        }
    validate_probability_array("checkpoint.valid_pred", payload["valid_pred"], len(valid_idx))
    validate_probability_array("checkpoint.test_pred", payload["test_pred"], test_rows)
    if payload["gain"].shape != (feature_count,) or payload["split"].shape != (
        feature_count,
    ):
        raise ValueError(f"{path.name} feature importance shape 不一致")
    if not np.isfinite(payload["gain"]).all() or not np.isfinite(payload["split"]).all():
        raise ValueError(f"{path.name} feature importance 含 NaN/Inf")
    if payload["best_iteration"] <= 0 or not np.isfinite(payload["fold_auc"]):
        raise ValueError(f"{path.name} best_iteration/fold_auc 非法")
    return payload


def make_source_manifest(
    run_contract: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    original: pd.DataFrame,
    original_diagnostics: dict[str, Any],
    output_paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "created_at_utc": utc_now(),
        "frozen_config_sha256": run_contract["frozen_config_sha256"],
        "run_contract_sha256": run_contract["run_contract_sha256"],
        "runtime": run_contract["runtime"],
        "code_and_inputs": run_contract["sources"],
        "row_identity": {
            "train_rows": len(train),
            "test_rows": len(test),
            "train_id_sha256": sha256_ids(train["id"]),
            "test_id_sha256": sha256_ids(test["id"]),
            "original_clean_rows": len(original),
            "original_buyer_id_sha256": sha256_ids(original[ORIGINAL_ID_COLUMN]),
        },
        "original_data_diagnostics": original_diagnostics,
        "outputs": {name: file_record(path) for name, path in output_paths.items()},
    }


def audit() -> None:
    audit_started = time.monotonic()
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v80_contract(config, recipe)
    strict_prior_self_check()
    run_contract = build_run_contract()
    train, test, _, _, _, _ = validate_data_contract(config, recipe)
    original, _, original_diagnostics = validate_original_data_contract(
        config, recipe, train, test, run_source_classifier=True
    )
    x_train, _, keys_train, keys_test = recipe.base.build_static_features(train, test)
    x_original, original_keys = build_apply_static_features(
        recipe,
        train,
        test,
        original,
        list(x_train.columns),
        keys_train,
        keys_test,
    )
    if x_original.shape != (len(original), int(config["expected_static_features"])):
        raise ValueError("original static 特征 shape 与冻结配置不一致")
    if set(original_keys) != set(recipe.base.TE_KEYS):
        raise ValueError("original TE apply keys 不完整")
    audit_resource_check = make_resource_check(
        config,
        started_monotonic=audit_started,
        phase="AUDIT",
        fold=None,
    )
    validate_recorded_resource_check(
        config,
        audit_resource_check,
        expected_phase="AUDIT",
        expected_fold=None,
        must_pass=True,
    )
    print(
        json.dumps(
            {
                "status": "AUDIT_OK_SOURCE_DIAGNOSTIC_ONLY_NO_EV_MODEL_TRAINING",
                "experiment_id": EXPERIMENT_ID,
                "train_rows": len(train),
                "test_rows": len(test),
                "outer_split_seed": OUTER_SEED,
                "inner_te_seed_base": INNER_TE_SEED_BASE,
                "model_seed": MODEL_SEED,
                "original_raw_rows": original_diagnostics["raw_rows"],
                "original_clean_rows": original_diagnostics["clean_rows"],
                "original_exact_duplicates_removed": original_diagnostics[
                    "exact_duplicates_vs_synthetic_train_test"
                ],
                "original_shared_feature_unique_rows": original_diagnostics[
                    "shared_feature_unique_rows"
                ],
                "dedup_shared_features": original_diagnostics[
                    "shared_feature_count"
                ],
                "dedup_ids_excluded": original_diagnostics[
                    "dedup_key_excludes_ids"
                ],
                "original_missing_counts": original_diagnostics["missing_counts"],
                "original_class_counts": original_diagnostics["class_counts"],
                "source_classifier": original_diagnostics["source_classifier"],
                "psi_vs_synthetic_train": original_diagnostics[
                    "psi_vs_synthetic_train"
                ],
                "runtime_lightgbm_version": lgb.__version__,
                "matched_v80_lightgbm_version": config["required_lightgbm_version"],
                "strict_prior_self_check": True,
                "matched_control_is_strict_complete": True,
                "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
                "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
                "audit_peak_rss_bytes": audit_resource_check["peak_rss_bytes"],
                "audit_peak_rss_gib": audit_resource_check["peak_rss_gib"],
                "peak_rss_native_unit": audit_resource_check[
                    "peak_rss_native_unit"
                ],
                "frozen_config_sha256": run_contract["frozen_config_sha256"],
                "run_contract_sha256": run_contract["run_contract_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def smoke() -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    control = validate_v80_contract(config, recipe)
    strict_prior_self_check()
    try:
        validate_lightgbm_version_contract(config, control, "0.0.0-smoke-mismatch")
    except RuntimeError as error:
        if "版本与 matched v80" not in str(error):
            raise
    else:
        raise AssertionError("不匹配的 LightGBM 版本未被拒绝")
    run_contract = build_run_contract()
    train, test, _, _, _, _ = validate_data_contract(config, recipe)
    original, original_y, original_diagnostics = validate_original_data_contract(
        config, recipe, train, test, run_source_classifier=False
    )

    train_extremes = [
        position
        for column in recipe.base.NUMERIC_FEATURES
        for position in (
            int(np.argmin(train[column].to_numpy())),
            int(np.argmax(train[column].to_numpy())),
        )
    ]
    test_extremes = [
        position
        for column in recipe.base.NUMERIC_FEATURES
        for position in (
            int(np.argmin(test[column].to_numpy())),
            int(np.argmax(test[column].to_numpy())),
        )
    ]
    train_idx = np.unique(
        np.concatenate(
            [np.linspace(0, len(train) - 1, 5000, dtype=np.int64), train_extremes]
        )
    )
    test_idx = np.unique(
        np.concatenate(
            [np.linspace(0, len(test) - 1, 2000, dtype=np.int64), test_extremes]
        )
    )
    smoke_train = train.iloc[train_idx].reset_index(drop=True)
    smoke_test = test.iloc[test_idx].reset_index(drop=True)
    y = smoke_train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    x_train, x_test, keys_train, keys_test = recipe.base.build_static_features(
        smoke_train, smoke_test
    )
    original_probe_idx = np.unique(
        np.concatenate(
            ([0, len(original) - 1], np.flatnonzero(original.isna().any(axis=1))[:300])
        )
    )
    smoke_original = original.iloc[original_probe_idx].reset_index(drop=True)
    smoke_original_y = original_y[original_probe_idx]
    x_original, keys_original = build_apply_static_features(
        recipe,
        smoke_train,
        smoke_test,
        smoke_original,
        list(x_train.columns),
        keys_train,
        keys_test,
    )
    synthetic_probe = smoke_train.iloc[:100].reset_index(drop=True)
    synthetic_probe_static, synthetic_probe_keys = build_apply_static_features(
        recipe,
        smoke_train,
        smoke_test,
        synthetic_probe,
        list(x_train.columns),
        keys_train,
        keys_test,
    )
    if not np.allclose(
        synthetic_probe_static.to_numpy(),
        x_train.iloc[:100].to_numpy(),
        equal_nan=True,
        atol=0.0,
        rtol=0.0,
    ):
        raise AssertionError("apply-only static 变换未复现 synthetic 特征")
    for key in keys_train:
        if not np.array_equal(synthetic_probe_keys[key], keys_train[key][:100]):
            raise AssertionError(f"key={key} apply-only 编码未复现 synthetic key")
    fit_idx, valid_idx = next(
        StratifiedKFold(n_splits=2, shuffle=True, random_state=OUTER_SEED).split(
            x_train, y
        )
    )
    inner = list(
        StratifiedKFold(
            n_splits=N_INNER_FOLDS,
            shuffle=True,
            random_state=INNER_TE_SEED_BASE + 1,
        ).split(np.zeros(len(fit_idx)), y[fit_idx])
    )
    fit_te: list[np.ndarray] = []
    valid_te: list[np.ndarray] = []
    test_te: list[np.ndarray] = []
    original_te: list[np.ndarray] = []
    for key in recipe.base.TE_KEYS:
        a, b, c, d = strict_encode_key(
            keys_train[key],
            keys_test[key],
            keys_original[key],
            y,
            fit_idx,
            valid_idx,
            inner,
            tuple(config["smooths"]),
        )
        fit_te.append(a)
        valid_te.append(b)
        test_te.append(c)
        original_te.append(d)
    matrices = {
        "fit": np.column_stack([x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]),
        "valid": np.column_stack(
            [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
        ),
        "test": np.column_stack([x_test.to_numpy(np.float32), *test_te]),
        "original": np.column_stack(
            [x_original.to_numpy(np.float32), *original_te]
        ),
    }
    if {matrix.shape[1] for matrix in matrices.values()} != {
        int(config["expected_total_features"])
    }:
        raise ValueError("smoke 特征宽度不是冻结的113")
    if not all(
        np.isfinite(matrix).all()
        for name, matrix in matrices.items()
        if name != "original"
    ):
        raise ValueError("smoke synthetic 特征矩阵含 NaN/Inf")
    if np.isinf(matrices["original"]).any():
        raise ValueError("smoke original 特征矩阵含 Inf")
    if not np.isfinite(np.column_stack(original_te)).all():
        raise ValueError("smoke original TE 含 NaN/Inf")
    smoke_fit = np.vstack([matrices["fit"], matrices["original"]])
    smoke_y = np.concatenate([y[fit_idx], smoke_original_y])
    smoke_weight = np.ones(len(smoke_y), dtype=np.float32)
    if (
        len(smoke_fit) != len(smoke_y)
        or not np.all(smoke_weight == float(config["original_sample_weight"]))
    ):
        raise AssertionError("original 追加或固定权重1 smoke 失败")

    fake_valid = np.linspace(0.1, 0.9, len(valid_idx), dtype=np.float64)
    fake_test = np.full(len(smoke_test), 0.5, dtype=np.float64)
    fake_importance = np.zeros(matrices["fit"].shape[1], dtype=np.float64)
    lock_rejection_ok = False
    if classify_resource_breach(config, 3600.0, 0) != ["WALL_CLOCK_BUDGET"]:
        raise AssertionError("60分钟墙钟硬门槛未生效")
    if classify_resource_breach(
        config, 0.0, int(config["peak_rss_budget_bytes"]) + 1
    ) != ["PEAK_RSS_BUDGET"]:
        raise AssertionError("16 GiB peak RSS硬门槛未生效")
    with tempfile.TemporaryDirectory(prefix="v84_smoke_") as temporary_dir:
        temporary_root = Path(temporary_dir)
        checkpoint = temporary_root / "fold_01.npz"
        save_checkpoint(
            checkpoint,
            fold=1,
            valid_idx=valid_idx,
            valid_pred=fake_valid,
            test_pred=fake_test,
            best_iteration=1,
            gain=fake_importance,
            split=fake_importance,
            fold_auc=0.5,
            elapsed_seconds=0.0,
            config_sha256=run_contract["frozen_config_sha256"],
            run_contract_sha256=run_contract["run_contract_sha256"],
        )
        load_checkpoint(
            checkpoint,
            fold=1,
            valid_idx=valid_idx,
            test_rows=len(smoke_test),
            feature_count=matrices["fit"].shape[1],
            config_sha256=run_contract["frozen_config_sha256"],
            run_contract_sha256=run_contract["run_contract_sha256"],
        )
        try:
            load_checkpoint(
                checkpoint,
                fold=1,
                valid_idx=valid_idx,
                test_rows=len(smoke_test),
                feature_count=matrices["fit"].shape[1],
                config_sha256=run_contract["frozen_config_sha256"],
                run_contract_sha256="0" * 64,
            )
        except ValueError as error:
            if "合同哈希不一致" not in str(error):
                raise
        else:
            raise AssertionError("错误合同哈希未被 checkpoint 恢复逻辑拒绝")

        smoke_lock = temporary_root / "run.lock"
        with exclusive_run_lock(smoke_lock, run_contract["run_contract_sha256"]):
            try:
                with exclusive_run_lock(smoke_lock, run_contract["run_contract_sha256"]):
                    raise AssertionError("第二实例不应取得 flock")
            except RuntimeError as error:
                if "持有 flock" not in str(error):
                    raise
                lock_rejection_ok = True
        released = json.loads(smoke_lock.read_text(encoding="utf-8"))
        if released.get("status") != "RELEASED":
            raise AssertionError("flock 释放状态未落盘")

        failure_path = temporary_root / "cv_results.json"
        failure_checkpoint_dir = temporary_root / "checkpoints"
        failure_checkpoint_dir.mkdir()
        fold_40_checkpoint = failure_checkpoint_dir / "fold_40.npz"
        fold_40_checkpoint.write_bytes(b"smoke-checkpoint-preservation")
        trigger_check = make_resource_check(
            config,
            started_monotonic=time.monotonic(),
            phase="AFTER_FOLD",
            fold=N_FOLDS,
        )
        trigger_check.update(
            {
                "status": "FAILED",
                "breaches": ["WALL_CLOCK_BUDGET"],
                "wall_elapsed_seconds": 3600.0,
            }
        )
        failure_check = dict(trigger_check)
        failure_check.update({"phase": "FAILED", "timestamp_utc": utc_now()})
        write_resource_failure(
            config,
            run_contract["frozen_config_sha256"],
            run_contract["run_contract_sha256"],
            [],
            [],
            [],
            [trigger_check, failure_check],
            trigger_check,
            failure_check,
            results_path=failure_path,
            checkpoint_dir=failure_checkpoint_dir,
        )
        failed_evidence = json.loads(failure_path.read_text(encoding="utf-8"))
        if (
            failed_evidence.get("status") != "FAILED"
            or failed_evidence.get("failure_fold") != N_FOLDS
            or failed_evidence.get("failure_attribution") != "WALL_CLOCK_BUDGET"
            or failed_evidence.get("preserved_checkpoints") != ["fold_40.npz"]
            or not fold_40_checkpoint.is_file()
            or (temporary_root / "cv_results.json.tmp").exists()
        ):
            raise AssertionError("资源超限 FAILED 原子证据 smoke 未通过")
    if not preregistered_futility_stop(config, 10, -0.000051, 4):
        raise AssertionError("10折中停 true 边界未生效")
    for completed, delta, wins in (
        (9, -1.0, 0),
        (10, -0.00005, 4),
        (10, -0.000051, 5),
    ):
        if preregistered_futility_stop(config, completed, delta, wins):
            raise AssertionError("10折中停 false 边界错误触发")

    print(
        json.dumps(
            {
                "status": "SMOKE_OK_NO_EV_MODEL_FIT_NO_METRIC_EVIDENCE",
                "strict_prior_self_check": True,
                "subset_train_rows": len(smoke_train),
                "subset_test_rows": len(smoke_test),
                "original_raw_rows": original_diagnostics["raw_rows"],
                "original_clean_rows": original_diagnostics["clean_rows"],
                "original_probe_rows": len(smoke_original),
                "exact_duplicates_removed": original_diagnostics[
                    "exact_duplicates_vs_synthetic_train_test"
                ],
                "ids_excluded_from_dedup_and_model": True,
                "apply_only_static_transform_matches_synthetic": True,
                "original_te_uses_synthetic_labels_only": True,
                "original_sample_weight_all_one": True,
                "static_features": x_train.shape[1],
                "te_features": sum(block.shape[1] for block in fit_te),
                "total_features": matrices["fit"].shape[1],
                "checkpoint_roundtrip": True,
                "mismatched_contract_rejected": True,
                "concurrent_lock_rejected": lock_rejection_ok,
                "mismatched_lightgbm_version_rejected": True,
                "wall_clock_limit_rejected": True,
                "peak_rss_limit_rejected": True,
                "atomic_failed_evidence_roundtrip": True,
                "fold_40_checkpoint_preserved_on_failure": True,
                "preregistered_10_fold_futility_boundary_verified": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def emit_five_fold_summary(
    logger: RunLogger,
    *,
    completed: int,
    fold_scores: list[float],
    fold_control_scores: list[float],
    oof: np.ndarray,
    coverage: np.ndarray,
    y: np.ndarray,
    control_oof: np.ndarray,
    latest_resource_check: dict[str, Any],
    trained_this_run: int,
    resumed_this_run: int,
) -> None:
    covered = coverage == 1
    partial_auc = float(roc_auc_score(y[covered], oof[covered]))
    control_auc = float(roc_auc_score(y[covered], control_oof[covered]))
    winning_folds = int(
        sum(row > base for row, base in zip(fold_scores, fold_control_scores))
    )
    payload = {
        "timestamp_utc": utc_now(),
        "evidence_level": "INTERIM_DIAGNOSTIC_NOT_FINAL",
        "completed_folds": completed,
        "total_folds": N_FOLDS,
        "trained_this_run": trained_this_run,
        "resumed_this_run": resumed_this_run,
        "covered_rows": int(covered.sum()),
        "partial_candidate_oof_auc": partial_auc,
        "matched_v80_auc_same_rows": control_auc,
        "partial_delta_vs_matched_v80": partial_auc - control_auc,
        "winning_folds_vs_matched_v80": winning_folds,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "wall_elapsed_seconds": latest_resource_check["wall_elapsed_seconds"],
        "peak_rss_bytes": latest_resource_check["peak_rss_bytes"],
        "peak_rss_gib": latest_resource_check["peak_rss_gib"],
        "rough_eta_seconds": latest_resource_check["wall_elapsed_seconds"]
        / completed
        * (N_FOLDS - completed),
    }
    append_progress(payload)
    logger.emit(
        "INTERIM_DIAGNOSTIC_NOT_FINAL "
        f"folds={completed}/{N_FOLDS} candidate_partial_oof={partial_auc:.9f} "
        f"matched_v80_same_rows={control_auc:.9f} "
        f"delta={partial_auc-control_auc:+.9f} wins={winning_folds}/{completed} "
        f"trained={trained_this_run} resumed={resumed_this_run} "
        f"eta={payload['rough_eta_seconds']:.0f}s"
    )


def preregistered_futility_stop(
    config: dict[str, Any], completed: int, partial_delta: float, winning_folds: int
) -> bool:
    return bool(
        completed == int(config["futility_check_after_folds"])
        and partial_delta < float(config["futility_delta_below"])
        and winning_folds <= int(config["futility_max_winning_folds"])
    )


def write_futility_failure(
    config: dict[str, Any],
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
    partial_candidate_auc: float,
    partial_control_auc: float,
    winning_folds: int,
) -> None:
    preserved_checkpoints = sorted(
        path.name for path in CHECKPOINT_DIR.glob("fold_[0-9][0-9].npz")
    )
    if len(fold_rows) != int(config["futility_check_after_folds"]):
        raise ValueError("中停 FAILED 只能在冻结的第10折写入")
    partial_delta = partial_candidate_auc - partial_control_auc
    if not preregistered_futility_stop(
        config, len(fold_rows), partial_delta, winning_folds
    ):
        raise ValueError("拒绝写入未满足预注册条件的中停 FAILED")
    atomic_write_json(
        OUT_DIR / "cv_results.json",
        {
            "schema_version": 1,
            "status": "FAILED",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": True,
            "failed_at_utc": utc_now(),
            "failure_attribution": "PREREGISTERED_10_FOLD_FUTILITY",
            "failure_reason": (
                "10折 partial matched delta 低于 -0.00005 且胜出折数不超过4/10"
            ),
            "failure_phase": "AFTER_FOLD",
            "failure_fold": int(config["futility_check_after_folds"]),
            "completed_folds": len(fold_rows),
            "fold_auc": fold_scores,
            "best_iterations": best_iterations,
            "fold_diagnostics": fold_rows,
            "partial_candidate_oof_auc": partial_candidate_auc,
            "partial_matched_v80_oof_auc": partial_control_auc,
            "partial_delta_vs_matched_v80": partial_delta,
            "winning_folds_vs_matched_v80": winning_folds,
            "futility_gate": {
                "check_after_folds": config["futility_check_after_folds"],
                "delta_below": config["futility_delta_below"],
                "max_winning_folds": config["futility_max_winning_folds"],
                "triggered": True,
            },
            "resource_checks": resource_checks,
            "params": config["lightgbm_params"],
            "frozen_config_sha256": config_sha256,
            "run_contract_sha256": run_contract_sha256,
            "allowed_for_fusion": False,
            "allowed_for_submission": False,
            "decision": "STOP",
            "preserved_checkpoints": preserved_checkpoints,
        },
    )


def write_resource_failure(
    config: dict[str, Any],
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
    trigger_check: dict[str, Any],
    failure_check: dict[str, Any],
    *,
    results_path: Path | None = None,
    checkpoint_dir: Path | None = None,
) -> None:
    target_results_path = results_path or (OUT_DIR / "cv_results.json")
    target_checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
    breaches = list(dict.fromkeys([*trigger_check["breaches"], *failure_check["breaches"]]))
    if not breaches:
        raise ValueError("拒绝写入没有资源超限证据的 FAILED")
    failure_reasons = {
        "WALL_CLOCK_BUDGET": "60分钟墙钟预算已达到或超过门槛",
        "PEAK_RSS_BUDGET": "进程 peak RSS 已超过16 GiB硬门槛",
    }
    expected_artifacts = {
        "oof_proba.npy": OUT_DIR / "oof_proba.npy",
        "test_proba.npy": OUT_DIR / "test_proba.npy",
        "submission.csv": OUT_DIR / "submission.csv",
        "feature_importance.csv": OUT_DIR / "feature_importance.csv",
        "sources.json": OUT_DIR / "sources.json",
    }
    present_artifacts = [
        name for name, path in expected_artifacts.items() if path.is_file()
    ]
    missing_artifacts = [
        name for name, path in expected_artifacts.items() if not path.is_file()
    ]
    preserved_checkpoints = sorted(
        path.name for path in target_checkpoint_dir.glob("fold_[0-9][0-9].npz")
    )
    atomic_write_json(
        target_results_path,
        {
            "schema_version": 1,
            "status": "FAILED",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": True,
            "failed_at_utc": failure_check["timestamp_utc"],
            "failure_attribution": "+".join(breaches),
            "failure_reason": "；".join(failure_reasons[item] for item in breaches),
            "failure_phase": trigger_check["phase"],
            "failure_fold": trigger_check["fold"],
            "completed_folds": len(fold_rows),
            "fold_auc": fold_scores,
            "best_iterations": best_iterations,
            "fold_diagnostics": fold_rows,
            "resource_checks": resource_checks,
            "resource_at_failure": failure_check,
            "wall_elapsed_seconds": failure_check["wall_elapsed_seconds"],
            "peak_rss_bytes": failure_check["peak_rss_bytes"],
            "peak_rss_gib": failure_check["peak_rss_gib"],
            "resource_budget": {
                "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
                "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
                "peak_rss_budget_gib": config["memory_budget_gb"],
            },
            "params": config["lightgbm_params"],
            "frozen_config_sha256": config_sha256,
            "run_contract_sha256": run_contract_sha256,
            "allowed_for_fusion": False,
            "allowed_for_submission": False,
            "decision": "STOP",
            "preserved_checkpoints": preserved_checkpoints,
            "present_artifacts": present_artifacts,
            "missing_artifacts": missing_artifacts,
            "present_artifacts_are_invalid_for_use": bool(present_artifacts),
        },
    )


def stop_for_resource_breach(
    config: dict[str, Any],
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
    trigger_check: dict[str, Any],
    *,
    started_monotonic: float,
    logger: RunLogger,
) -> bool:
    if not trigger_check["breaches"]:
        return False
    failure_check = make_resource_check(
        config,
        started_monotonic=started_monotonic,
        phase="FAILED",
        fold=trigger_check["fold"],
    )
    record_resource_check(resource_checks, failure_check)
    write_resource_failure(
        config,
        config_sha256,
        run_contract_sha256,
        fold_rows,
        fold_scores,
        best_iterations,
        resource_checks,
        trigger_check,
        failure_check,
    )
    logger.emit(
        "stopped reason="
        f"{'+'.join(trigger_check['breaches'])} phase={trigger_check['phase']} "
        f"fold={trigger_check['fold']} completed_folds={len(fold_rows)}/{N_FOLDS} "
        f"wall={failure_check['wall_elapsed_seconds']:.1f}s "
        f"peak_rss={failure_check['peak_rss_gib']:.3f}GiB"
    )
    return True


def train() -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v80_contract(config, recipe)
    strict_prior_self_check()
    run_contract = build_run_contract()
    config_hash = run_contract["frozen_config_sha256"]
    contract_hash = run_contract["run_contract_sha256"]
    logger = RunLogger(LOG_PATH)

    results_path = OUT_DIR / "cv_results.json"
    if results_path.exists():
        existing = json.loads(results_path.read_text(encoding="utf-8"))
        if existing.get("status") == "COMPLETE":
            verify_complete()
            return
        raise RuntimeError("cv_results.json 已存在且非 COMPLETE，必须先人工审计")

    with exclusive_run_lock(LOCK_PATH, contract_hash):
        if results_path.exists():
            locked_existing = json.loads(results_path.read_text(encoding="utf-8"))
            if locked_existing.get("status") == "COMPLETE":
                verify_complete()
                return
            raise RuntimeError(
                "获得 flock 后发现非 COMPLETE cv_results，必须先人工审计"
            )
        started_monotonic = time.monotonic()
        logger.emit(
            f"start mode=train config_sha256={config_hash} "
            f"run_contract_sha256={contract_hash}"
        )
        (
            train_frame,
            test_frame,
            sample,
            control_oof,
            control_test,
            control_results,
        ) = validate_data_contract(config, recipe)
        original_frame, original_y, original_diagnostics = validate_original_data_contract(
            config, recipe, train_frame, test_frame, run_source_classifier=True
        )
        y = train_frame[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
        x_train, x_test, keys_train, keys_test = recipe.base.build_static_features(
            train_frame, test_frame
        )
        te_names = [
            f"te_{key}_m{smooth:g}"
            for key in recipe.base.TE_KEYS
            for smooth in recipe.base.SMOOTHS
        ]
        all_features = list(x_train.columns) + te_names
        x_original, keys_original = build_apply_static_features(
            recipe,
            train_frame,
            test_frame,
            original_frame,
            list(x_train.columns),
            keys_train,
            keys_test,
        )
        if (
            x_train.shape[1] != int(config["expected_static_features"])
            or len(te_names) != int(config["expected_te_features"])
            or len(all_features) != int(config["expected_total_features"])
        ):
            raise ValueError("完整特征 schema 不是冻结的 62 static + 51 TE")
        logger.emit(
            f"data train={train_frame.shape} test={test_frame.shape} "
            f"original_clean={original_frame.shape} static={x_train.shape[1]} "
            f"te={len(te_names)} total={len(all_features)}"
        )

        folds = list(
            StratifiedKFold(
                n_splits=N_FOLDS, shuffle=True, random_state=OUTER_SEED
            ).split(x_train, y)
        )
        oof = np.zeros(len(train_frame), dtype=np.float64)
        coverage = np.zeros(len(train_frame), dtype=np.int8)
        test_prediction = np.zeros(len(test_frame), dtype=np.float64)
        fold_scores: list[float] = []
        fold_control_scores: list[float] = []
        best_iterations: list[int] = []
        fold_rows: list[dict[str, Any]] = []
        importance_frames: list[pd.DataFrame] = []
        trained_this_run = 0
        resumed_this_run = 0
        resource_checks: list[dict[str, Any]] = []
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

        for fold, (fit_idx, valid_idx) in enumerate(folds, start=1):
            before_fold_check = make_resource_check(
                config,
                started_monotonic=started_monotonic,
                phase="BEFORE_FOLD",
                fold=fold,
            )
            record_resource_check(resource_checks, before_fold_check)
            if stop_for_resource_breach(
                config,
                config_hash,
                contract_hash,
                fold_rows,
                fold_scores,
                best_iterations,
                resource_checks,
                before_fold_check,
                started_monotonic=started_monotonic,
                logger=logger,
            ):
                return
            checkpoint = CHECKPOINT_DIR / f"fold_{fold:02d}.npz"
            was_resumed = checkpoint.exists()
            if was_resumed:
                saved = load_checkpoint(
                    checkpoint,
                    fold=fold,
                    valid_idx=valid_idx,
                    test_rows=len(test_frame),
                    feature_count=len(all_features),
                    config_sha256=config_hash,
                    run_contract_sha256=contract_hash,
                )
                valid_pred = saved["valid_pred"]
                fold_test = saved["test_pred"]
                best_iteration = saved["best_iteration"]
                gain = saved["gain"]
                split = saved["split"]
                fold_elapsed = saved["elapsed_seconds"]
                fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
                if not np.isclose(fold_auc, saved["fold_auc"], atol=1e-12, rtol=0.0):
                    raise ValueError(f"fold={fold} checkpoint AUC 复算不一致")
                resumed_this_run += 1
                logger.emit(f"fold={fold}/{N_FOLDS} resumed strict_auc={fold_auc:.9f}")
            else:
                fold_started = time.monotonic()
                inner = list(
                    StratifiedKFold(
                        n_splits=N_INNER_FOLDS,
                        shuffle=True,
                        random_state=INNER_TE_SEED_BASE + fold,
                    ).split(np.zeros(len(fit_idx)), y[fit_idx])
                )
                fit_te: list[np.ndarray] = []
                valid_te: list[np.ndarray] = []
                test_te: list[np.ndarray] = []
                original_te: list[np.ndarray] = []
                for key in recipe.base.TE_KEYS:
                    a, b, c, d = strict_encode_key(
                        keys_train[key],
                        keys_test[key],
                        keys_original[key],
                        y,
                        fit_idx,
                        valid_idx,
                        inner,
                        tuple(config["smooths"]),
                    )
                    fit_te.append(a)
                    valid_te.append(b)
                    test_te.append(c)
                    original_te.append(d)
                x_synthetic_fit = np.column_stack(
                    [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
                )
                x_original_fit = np.column_stack(
                    [x_original.to_numpy(np.float32), *original_te]
                )
                x_fit = np.vstack([x_synthetic_fit, x_original_fit])
                y_fit = np.concatenate([y[fit_idx], original_y])
                sample_weight = np.ones(len(y_fit), dtype=np.float32)
                x_valid = np.column_stack(
                    [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
                )
                x_tst = np.column_stack([x_test.to_numpy(np.float32), *test_te])
                model = lgb.LGBMClassifier(**config["lightgbm_params"])
                model.fit(
                    x_fit,
                    y_fit,
                    sample_weight=sample_weight,
                    eval_set=[(x_valid, y[valid_idx])],
                    eval_metric="auc",
                    feature_name=all_features,
                    callbacks=[
                        lgb.early_stopping(
                            int(config["early_stopping_rounds"]), verbose=False
                        ),
                        lgb.log_evaluation(period=0),
                    ],
                )
                best_iteration = int(
                    model.best_iteration_ or config["lightgbm_params"]["n_estimators"]
                )
                valid_pred = model.predict_proba(
                    x_valid, num_iteration=best_iteration
                )[:, 1]
                fold_test = model.predict_proba(x_tst, num_iteration=best_iteration)[:, 1]
                fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
                gain = model.booster_.feature_importance(importance_type="gain")
                split = model.booster_.feature_importance(importance_type="split")
                fold_elapsed = time.monotonic() - fold_started
                save_checkpoint(
                    checkpoint,
                    fold=fold,
                    valid_idx=valid_idx,
                    valid_pred=valid_pred,
                    test_pred=fold_test,
                    best_iteration=best_iteration,
                    gain=gain,
                    split=split,
                    fold_auc=fold_auc,
                    elapsed_seconds=fold_elapsed,
                    config_sha256=config_hash,
                    run_contract_sha256=contract_hash,
                )
                trained_this_run += 1
                logger.emit(
                    f"fold={fold}/{N_FOLDS} trained strict_auc={fold_auc:.9f} "
                    f"best_iteration={best_iteration} elapsed={fold_elapsed:.1f}s checkpointed"
                )
                del (
                    model,
                    x_synthetic_fit,
                    x_original_fit,
                    x_fit,
                    y_fit,
                    sample_weight,
                    x_valid,
                    x_tst,
                    fit_te,
                    valid_te,
                    test_te,
                    original_te,
                )
                gc.collect()

            after_fold_check = make_resource_check(
                config,
                started_monotonic=started_monotonic,
                phase="AFTER_FOLD",
                fold=fold,
            )
            record_resource_check(resource_checks, after_fold_check)

            if coverage[valid_idx].any():
                raise ValueError(f"fold={fold} validation coverage 重叠")
            coverage[valid_idx] = 1
            oof[valid_idx] = valid_pred
            test_prediction += fold_test / N_FOLDS
            control_auc = float(
                roc_auc_score(y[valid_idx], control_oof[valid_idx])
            )
            fold_scores.append(fold_auc)
            fold_control_scores.append(control_auc)
            best_iterations.append(best_iteration)
            fold_rows.append(
                {
                    "fold": fold,
                    "inner_te_seed": INNER_TE_SEED_BASE + fold,
                    "valid_idx_sha256": hashlib.sha256(valid_idx.tobytes()).hexdigest(),
                    "candidate_auc": fold_auc,
                    "matched_v80_auc": control_auc,
                    "delta_vs_matched_v80": fold_auc - control_auc,
                    "synthetic_fit_rows": len(fit_idx),
                    "original_fit_rows": len(original_frame),
                    "combined_fit_rows": len(fit_idx) + len(original_frame),
                    "original_sample_weight": config["original_sample_weight"],
                    "valid_rows": len(valid_idx),
                    "validation_source": "SYNTHETIC_ONLY",
                    "te_statistics_source": "SYNTHETIC_OUTER_TRAIN_LABELS_ONLY",
                    "best_iteration": best_iteration,
                    "elapsed_seconds": fold_elapsed,
                    "resumed": was_resumed,
                    "resource_before_fold": before_fold_check,
                    "resource_after_fold": after_fold_check,
                }
            )
            importance_frames.append(
                pd.DataFrame(
                    {"feature": all_features, "gain": gain, "split": split, "fold": fold}
                )
            )
            if fold % int(config["observable_summary_every_folds"]) == 0:
                emit_five_fold_summary(
                    logger,
                    completed=fold,
                    fold_scores=fold_scores,
                    fold_control_scores=fold_control_scores,
                    oof=oof,
                    coverage=coverage,
                    y=y,
                    control_oof=control_oof,
                    latest_resource_check=after_fold_check,
                    trained_this_run=trained_this_run,
                    resumed_this_run=resumed_this_run,
                )
            if stop_for_resource_breach(
                config,
                config_hash,
                contract_hash,
                fold_rows,
                fold_scores,
                best_iterations,
                resource_checks,
                after_fold_check,
                started_monotonic=started_monotonic,
                logger=logger,
            ):
                return
            if fold == int(config["futility_check_after_folds"]):
                covered = coverage == 1
                partial_candidate_auc = float(roc_auc_score(y[covered], oof[covered]))
                partial_control_auc = float(
                    roc_auc_score(y[covered], control_oof[covered])
                )
                partial_delta = partial_candidate_auc - partial_control_auc
                winning_folds = int(
                    sum(
                        candidate > base
                        for candidate, base in zip(
                            fold_scores, fold_control_scores
                        )
                    )
                )
                if preregistered_futility_stop(
                    config, fold, partial_delta, winning_folds
                ):
                    write_futility_failure(
                        config,
                        config_hash,
                        contract_hash,
                        fold_rows,
                        fold_scores,
                        best_iterations,
                        resource_checks,
                        partial_candidate_auc,
                        partial_control_auc,
                        winning_folds,
                    )
                    logger.emit(
                        "stopped reason=PREREGISTERED_10_FOLD_FUTILITY "
                        f"delta={partial_delta:+.9f} wins={winning_folds}/10"
                    )
                    return

        after_folds_check = make_resource_check(
            config,
            started_monotonic=started_monotonic,
            phase="AFTER_ALL_FOLDS",
            fold=N_FOLDS,
        )
        record_resource_check(resource_checks, after_folds_check)
        if stop_for_resource_breach(
            config,
            config_hash,
            contract_hash,
            fold_rows,
            fold_scores,
            best_iterations,
            resource_checks,
            after_folds_check,
            started_monotonic=started_monotonic,
            logger=logger,
        ):
            return

        if not np.all(coverage == 1):
            raise ValueError("完整40折后 OOF coverage 不是恰好一次")
        validate_probability_array("oof_proba", oof, len(train_frame))
        validate_probability_array("test_proba", test_prediction, len(test_frame))
        oof_auc = float(roc_auc_score(y, oof))
        control_auc = float(control_results["oof_auc"])
        matched_delta = oof_auc - control_auc
        winning_folds = int(
            sum(
                candidate > base
                for candidate, base in zip(fold_scores, fold_control_scores)
            )
        )
        oof_spearman = float(spearmanr(oof, control_oof).statistic)
        test_spearman = float(spearmanr(test_prediction, control_test).statistic)
        if not np.isfinite(oof_spearman) or not np.isfinite(test_spearman):
            raise ValueError("与 matched v80 的 Spearman 非有限值")

        importance = pd.concat(importance_frames, ignore_index=True)
        importance_summary = (
            importance.groupby("feature", as_index=False)
            .agg(
                gain_mean=("gain", "mean"),
                gain_std=("gain", "std"),
                split_mean=("split", "mean"),
                split_std=("split", "std"),
            )
            .sort_values("gain_mean", ascending=False)
        )
        submission = sample.copy()
        submission[config["target"]] = test_prediction
        recipe.base.validate_submission(submission, test_frame, sample)

        output_paths = {
            "oof_proba": OUT_DIR / "oof_proba.npy",
            "test_proba": OUT_DIR / "test_proba.npy",
            "submission": OUT_DIR / "submission.csv",
            "feature_importance": OUT_DIR / "feature_importance.csv",
        }
        atomic_save_npy(output_paths["oof_proba"], oof)
        atomic_save_npy(output_paths["test_proba"], test_prediction)
        atomic_write_csv(output_paths["submission"], submission)
        atomic_write_csv(output_paths["feature_importance"], importance_summary)
        sources = make_source_manifest(
            run_contract,
            train_frame,
            test_frame,
            original_frame,
            original_diagnostics,
            output_paths,
        )
        sources_path = OUT_DIR / "sources.json"
        atomic_write_json(sources_path, sources)
        final_resource_check = make_resource_check(
            config,
            started_monotonic=started_monotonic,
            phase="FINAL_BEFORE_COMPLETE",
            fold=N_FOLDS,
        )
        record_resource_check(resource_checks, final_resource_check)
        if stop_for_resource_breach(
            config,
            config_hash,
            contract_hash,
            fold_rows,
            fold_scores,
            best_iterations,
            resource_checks,
            final_resource_check,
            started_monotonic=started_monotonic,
            logger=logger,
        ):
            return
        matched_gate = bool(
            matched_delta >= float(config["minimum_matched_oof_delta"])
            and winning_folds >= int(config["minimum_winning_folds"])
        )
        results = {
            "schema_version": 1,
            "status": "COMPLETE",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": True,
            "competition": config["competition"],
            "model": "strict v80 LightGBM plus original supervision, 40 outer folds",
            "hypothesis": (
                "clean original labels add a small independent supervision signal when "
                "the synthetic validation and target-encoding boundary remain strict"
            ),
            "unique_primary_variable": (
                "append deduplicated original labeled rows at weight 1 to each outer fit"
            ),
            "matched_control": config["matched_control"],
            "matched_control_oof_auc": control_auc,
            "n_folds": N_FOLDS,
            "outer_split_seed": OUTER_SEED,
            "n_inner_folds": N_INNER_FOLDS,
            "inner_te_seed_base": INNER_TE_SEED_BASE,
            "inner_te_seeds": [INNER_TE_SEED_BASE + fold for fold in range(1, 41)],
            "model_seed": MODEL_SEED,
            "strict_prior_contract": config["strict_prior_contract"],
            "original_supervision_contract": config[
                "original_supervision_contract"
            ],
            "params": config["lightgbm_params"],
            "smooths": config["smooths"],
            "te_keys": config["te_keys"],
            "static_feature_count": int(x_train.shape[1]),
            "te_feature_count": len(te_names),
            "feature_count": len(all_features),
            "fold_auc": fold_scores,
            "fold_auc_mean": float(np.mean(fold_scores)),
            "fold_auc_std": float(np.std(fold_scores)),
            "best_iterations": best_iterations,
            "fold_diagnostics": fold_rows,
            "winning_folds_vs_matched_v80": winning_folds,
            "oof_auc": oof_auc,
            "base": config["matched_control"],
            "base_oof_auc": control_auc,
            "oof_delta_vs_base": matched_delta,
            "oof_delta_vs_matched_v80": matched_delta,
            "oof_spearman_vs_base": oof_spearman,
            "oof_spearman_vs_matched_v80": oof_spearman,
            "test_spearman_vs_base": test_spearman,
            "test_spearman_vs_matched_v80": test_spearman,
            "comparison_boundary": (
                "candidate and strict v80 use identical synthetic outer validation rows, "
                "folds, seeds, features, TE recipe, and model parameters"
            ),
            "matched_control_candidate_gate": {
                "minimum_oof_delta": config["minimum_matched_oof_delta"],
                "minimum_winning_folds": config["minimum_winning_folds"],
                "observed_oof_delta": matched_delta,
                "observed_winning_folds": winning_folds,
                "passes": matched_gate,
            },
            "original_data_diagnostics": original_diagnostics,
            "decision": "ADVANCE_TO_STRICT_SMALL_FUSION" if matched_gate else "STOP",
            "allowed_for_fusion": matched_gate,
            "allowed_for_submission": False,
            "cycle_count_update_required": True,
            "elapsed_seconds": final_resource_check["wall_elapsed_seconds"],
            "wall_clock_elapsed_seconds": final_resource_check[
                "wall_elapsed_seconds"
            ],
            "peak_rss_bytes": final_resource_check["peak_rss_bytes"],
            "peak_rss_gib": final_resource_check["peak_rss_gib"],
            "resource_budget": {
                "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
                "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
                "peak_rss_budget_gib": config["memory_budget_gb"],
            },
            "resource_checks": resource_checks,
            "trained_folds_this_run": trained_this_run,
            "resumed_folds_this_run": resumed_this_run,
            "frozen_config_sha256": config_hash,
            "run_contract_sha256": contract_hash,
            "code_and_input_sha256": {
                name: record["sha256"]
                for name, record in run_contract["sources"].items()
            },
            "artifact_sha256": {
                name: sha256_file(path) for name, path in output_paths.items()
            },
            "sources_sha256": sha256_file(sources_path),
            "artifact_validation": {
                "oof_rows": len(oof),
                "test_rows": len(test_prediction),
                "oof_exactly_once_coverage": True,
                "probabilities_finite_and_in_range": True,
                "submission_id_matches_test": True,
                "strict_prior_self_check": True,
                "checkpoint_reconstruction_required": True,
            },
            "runtime": run_contract["runtime"],
        }
        atomic_write_json(results_path, results)
        verify_complete()
        logger.emit(
            f"complete strict_oof={oof_auc:.9f} "
            f"delta_vs_matched_v80={matched_delta:+.9f} "
            f"wins={winning_folds}/40 gate={matched_gate}"
        )


def verify_source_contract(
    sources: dict[str, Any], results: dict[str, Any]
) -> None:
    stored_payload = {
        "experiment_id": sources["experiment_id"],
        "frozen_config_sha256": sources["frozen_config_sha256"],
        "sources": sources["code_and_inputs"],
        "runtime": sources["runtime"],
    }
    if sha256_json(stored_payload) != sources["run_contract_sha256"]:
        raise ValueError("sources.json 运行合同哈希无法复算")
    if results["run_contract_sha256"] != sources["run_contract_sha256"]:
        raise ValueError("cv_results 与 sources 的运行合同哈希不一致")
    if sources["frozen_config_sha256"] != sha256_file(CONFIG_PATH):
        raise ValueError("sources 冻结配置哈希不一致")
    source_hashes = {
        name: record["sha256"] for name, record in sources["code_and_inputs"].items()
    }
    if results["code_and_input_sha256"] != source_hashes:
        raise ValueError("cv_results 与 sources 的代码/输入哈希清单不一致")
    for name, record in sources["code_and_inputs"].items():
        path = PROJECT_DIR / record["path"]
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise ValueError(f"来源文件缺失或已改变：{name}")


def verify_complete() -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v80_contract(config, recipe)
    strict_prior_self_check()
    (
        train,
        test,
        sample,
        control_oof,
        control_test,
        control_results,
    ) = validate_data_contract(config, recipe)
    original, _, original_diagnostics = validate_original_data_contract(
        config, recipe, train, test, run_source_classifier=True
    )
    paths = {
        "cv_results": OUT_DIR / "cv_results.json",
        "sources": OUT_DIR / "sources.json",
        "oof_proba": OUT_DIR / "oof_proba.npy",
        "test_proba": OUT_DIR / "test_proba.npy",
        "submission": OUT_DIR / "submission.csv",
        "feature_importance": OUT_DIR / "feature_importance.csv",
        "train_log": LOG_PATH,
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"COMPLETE 产物缺失：{missing}")
    results = json.loads(paths["cv_results"].read_text(encoding="utf-8"))
    sources = json.loads(paths["sources"].read_text(encoding="utf-8"))
    if results.get("status") != "COMPLETE" or results.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("cv_results COMPLETE/experiment_id 合同不一致")
    if results["frozen_config_sha256"] != sha256_file(CONFIG_PATH):
        raise ValueError("cv_results 冻结配置哈希不一致")
    if results["sources_sha256"] != sha256_file(paths["sources"]):
        raise ValueError("cv_results sources 哈希不一致")
    verify_source_contract(sources, results)

    expected_lengths = {
        "fold_auc": N_FOLDS,
        "best_iterations": N_FOLDS,
        "fold_diagnostics": N_FOLDS,
        "inner_te_seeds": N_FOLDS,
    }
    for key, expected in expected_lengths.items():
        if len(results.get(key, [])) != expected:
            raise ValueError(f"cv_results {key} 长度不是 {expected}")
    if (
        results["outer_split_seed"] != OUTER_SEED
        or results["inner_te_seed_base"] != INNER_TE_SEED_BASE
        or results["model_seed"] != MODEL_SEED
        or results["strict_prior_contract"] != config["strict_prior_contract"]
        or results["original_supervision_contract"]
        != config["original_supervision_contract"]
    ):
        raise ValueError("cv_results 随机源或 strict prior 合同不一致")

    resource_checks = results.get("resource_checks", [])
    expected_resource_checks = N_FOLDS * 2 + 2
    if len(resource_checks) != expected_resource_checks:
        raise ValueError(
            f"cv_results resource_checks 长度不是 {expected_resource_checks}"
        )
    previous_wall_elapsed = -1.0
    previous_peak_rss = -1
    for fold in range(1, N_FOLDS + 1):
        before_check = resource_checks[(fold - 1) * 2]
        after_check = resource_checks[(fold - 1) * 2 + 1]
        validate_recorded_resource_check(
            config,
            before_check,
            expected_phase="BEFORE_FOLD",
            expected_fold=fold,
            must_pass=True,
        )
        validate_recorded_resource_check(
            config,
            after_check,
            expected_phase="AFTER_FOLD",
            expected_fold=fold,
            must_pass=True,
        )
        diagnostic = results["fold_diagnostics"][fold - 1]
        if (
            diagnostic.get("resource_before_fold") != before_check
            or diagnostic.get("resource_after_fold") != after_check
        ):
            raise ValueError(f"fold={fold} 资源检查未写入 fold_diagnostics")
        for check in (before_check, after_check):
            if float(check["wall_elapsed_seconds"]) < previous_wall_elapsed:
                raise ValueError("资源检查墙钟序列非单调")
            if int(check["peak_rss_bytes"]) < previous_peak_rss:
                raise ValueError("资源检查 peak RSS 序列非单调")
            previous_wall_elapsed = float(check["wall_elapsed_seconds"])
            previous_peak_rss = int(check["peak_rss_bytes"])
    after_folds_check = resource_checks[-2]
    final_resource_check = resource_checks[-1]
    validate_recorded_resource_check(
        config,
        after_folds_check,
        expected_phase="AFTER_ALL_FOLDS",
        expected_fold=N_FOLDS,
        must_pass=True,
    )
    validate_recorded_resource_check(
        config,
        final_resource_check,
        expected_phase="FINAL_BEFORE_COMPLETE",
        expected_fold=N_FOLDS,
        must_pass=True,
    )
    for check in (after_folds_check, final_resource_check):
        if float(check["wall_elapsed_seconds"]) < previous_wall_elapsed:
            raise ValueError("最终资源检查墙钟序列非单调")
        if int(check["peak_rss_bytes"]) < previous_peak_rss:
            raise ValueError("最终资源检查 peak RSS 序列非单调")
        previous_wall_elapsed = float(check["wall_elapsed_seconds"])
        previous_peak_rss = int(check["peak_rss_bytes"])
    if (
        not np.isclose(
            results["wall_clock_elapsed_seconds"],
            final_resource_check["wall_elapsed_seconds"],
            atol=1e-12,
            rtol=0.0,
        )
        or int(results["peak_rss_bytes"])
        != int(final_resource_check["peak_rss_bytes"])
        or not np.isclose(
            results["peak_rss_gib"],
            final_resource_check["peak_rss_gib"],
            atol=1e-12,
            rtol=0.0,
        )
    ):
        raise ValueError("COMPLETE 最终资源摘要与资源检查不一致")
    if not np.isclose(
        results["elapsed_seconds"],
        final_resource_check["wall_elapsed_seconds"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("COMPLETE elapsed_seconds 与最终墙钟检查不一致")
    expected_resource_budget = {
        "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
        "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
        "peak_rss_budget_gib": config["memory_budget_gb"],
    }
    if results.get("resource_budget") != expected_resource_budget:
        raise ValueError("COMPLETE 资源预算摘要与冻结配置不一致")

    oof = np.load(paths["oof_proba"], mmap_mode="r")
    test_prediction = np.load(paths["test_proba"], mmap_mode="r")
    validate_probability_array("oof_proba", oof, len(train))
    validate_probability_array("test_proba", test_prediction, len(test))
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)

    folds = list(
        StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=OUTER_SEED).split(
            np.zeros(len(train)), y
        )
    )
    checkpoint_paths = sorted(CHECKPOINT_DIR.glob("fold_[0-9][0-9].npz"))
    if len(checkpoint_paths) != N_FOLDS:
        raise ValueError(f"checkpoint 数量={len(checkpoint_paths)}，预期40")
    rebuilt_oof = np.zeros(len(train), dtype=np.float64)
    rebuilt_test = np.zeros(len(test), dtype=np.float64)
    rebuilt_coverage = np.zeros(len(train), dtype=np.int8)
    rebuilt_fold_auc: list[float] = []
    rebuilt_best_iterations: list[int] = []
    for fold, (_, valid_idx) in enumerate(folds, start=1):
        checkpoint = load_checkpoint(
            CHECKPOINT_DIR / f"fold_{fold:02d}.npz",
            fold=fold,
            valid_idx=valid_idx,
            test_rows=len(test),
            feature_count=int(results["feature_count"]),
            config_sha256=results["frozen_config_sha256"],
            run_contract_sha256=results["run_contract_sha256"],
        )
        if rebuilt_coverage[valid_idx].any():
            raise ValueError(f"fold={fold} checkpoint reconstruction coverage 重叠")
        rebuilt_coverage[valid_idx] = 1
        rebuilt_oof[valid_idx] = checkpoint["valid_pred"]
        rebuilt_test += checkpoint["test_pred"] / N_FOLDS
        fold_auc = float(roc_auc_score(y[valid_idx], checkpoint["valid_pred"]))
        rebuilt_fold_auc.append(fold_auc)
        rebuilt_best_iterations.append(int(checkpoint["best_iteration"]))
        if not np.isclose(fold_auc, checkpoint["fold_auc"], atol=1e-12, rtol=0.0):
            raise ValueError(f"fold={fold} checkpoint fold_auc 复算不一致")
        if not np.isclose(fold_auc, results["fold_auc"][fold - 1], atol=1e-12, rtol=0.0):
            raise ValueError(f"fold={fold} cv_results fold_auc 复算不一致")
        diagnostic = results["fold_diagnostics"][fold - 1]
        control_fold_auc = float(
            roc_auc_score(y[valid_idx], control_oof[valid_idx])
        )
        if (
            int(diagnostic["fold"]) != fold
            or int(diagnostic["inner_te_seed"]) != INNER_TE_SEED_BASE + fold
            or int(diagnostic["best_iteration"]) != checkpoint["best_iteration"]
            or not np.isclose(
                diagnostic["candidate_auc"], fold_auc, atol=1e-12, rtol=0.0
            )
            or not np.isclose(
                diagnostic["matched_v80_auc"],
                control_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
            or not np.isclose(
                diagnostic["delta_vs_matched_v80"],
                fold_auc - control_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
            or int(diagnostic["original_fit_rows"]) != len(original)
            or int(diagnostic["synthetic_fit_rows"]) != len(train) - len(valid_idx)
            or int(diagnostic["combined_fit_rows"])
            != len(train) - len(valid_idx) + len(original)
            or float(diagnostic["original_sample_weight"])
            != float(config["original_sample_weight"])
            or diagnostic["validation_source"] != "SYNTHETIC_ONLY"
            or diagnostic["te_statistics_source"]
            != "SYNTHETIC_OUTER_TRAIN_LABELS_ONLY"
        ):
            raise ValueError(f"fold={fold} cv_results fold diagnostic 复算不一致")
        if diagnostic["valid_idx_sha256"] != hashlib.sha256(valid_idx.tobytes()).hexdigest():
            raise ValueError(f"fold={fold} cv_results valid_idx 哈希不一致")
    if not np.all(rebuilt_coverage == 1):
        raise ValueError("checkpoint 重建 OOF coverage 不是恰好一次")
    if not np.array_equal(rebuilt_oof, np.asarray(oof)):
        raise ValueError("oof_proba 未与40个 checkpoint 逐元素一致")
    if not np.array_equal(rebuilt_test, np.asarray(test_prediction)):
        raise ValueError("test_proba 未与40个 checkpoint 逐元素一致")
    rebuilt_fold_mean = float(np.mean(rebuilt_fold_auc))
    rebuilt_fold_std = float(np.std(rebuilt_fold_auc))
    if not np.isclose(
        rebuilt_fold_mean, results["fold_auc_mean"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("fold_auc_mean 未与 checkpoint 重建结果一致")
    if not np.isclose(
        rebuilt_fold_std, results["fold_auc_std"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("fold_auc_std 未与 checkpoint 重建结果一致")
    if rebuilt_best_iterations != [int(value) for value in results["best_iterations"]]:
        raise ValueError("best_iterations 未与40个 checkpoint 一致")

    recomputed_oof_auc = float(roc_auc_score(y, rebuilt_oof))
    if not np.isclose(recomputed_oof_auc, results["oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("整体 OOF AUC 复算不一致")
    control_auc = float(control_results["oof_auc"])
    matched_delta = recomputed_oof_auc - control_auc
    for key in ("oof_delta_vs_matched_v80", "oof_delta_vs_base"):
        if not np.isclose(
            matched_delta, results[key], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{key} 复算不一致")
    if (
        results["matched_control"] != config["matched_control"]
        or results["base"] != config["matched_control"]
        or not np.isclose(
            results["matched_control_oof_auc"], control_auc, atol=1e-12, rtol=0.0
        )
        or not np.isclose(
            results["base_oof_auc"], control_auc, atol=1e-12, rtol=0.0
        )
    ):
        raise ValueError("matched v80 基准字段复算不一致")
    rebuilt_oof_spearman = float(spearmanr(rebuilt_oof, control_oof).statistic)
    rebuilt_test_spearman = float(spearmanr(rebuilt_test, control_test).statistic)
    for key in (
        "oof_spearman_vs_base",
        "oof_spearman_vs_matched_v80",
    ):
        if not np.isclose(
            rebuilt_oof_spearman, results[key], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{key} 复算不一致")
    for key in (
        "test_spearman_vs_base",
        "test_spearman_vs_matched_v80",
    ):
        if not np.isclose(
            rebuilt_test_spearman, results[key], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{key} 复算不一致")

    rebuilt_control_fold_auc = [
        float(roc_auc_score(y[valid_idx], control_oof[valid_idx]))
        for _, valid_idx in folds
    ]
    winning_folds = int(
        sum(
            candidate > base
            for candidate, base in zip(rebuilt_fold_auc, rebuilt_control_fold_auc)
        )
    )
    expected_gate = bool(
        matched_delta >= float(config["minimum_matched_oof_delta"])
        and winning_folds >= int(config["minimum_winning_folds"])
    )
    gate = results["matched_control_candidate_gate"]
    expected_gate_payload = {
        "minimum_oof_delta": config["minimum_matched_oof_delta"],
        "minimum_winning_folds": config["minimum_winning_folds"],
        "observed_oof_delta": matched_delta,
        "observed_winning_folds": winning_folds,
        "passes": expected_gate,
    }
    for key, expected in expected_gate_payload.items():
        actual = gate.get(key)
        if isinstance(expected, float):
            if not np.isclose(actual, expected, atol=1e-12, rtol=0.0):
                raise ValueError(f"matched gate {key} 复算不一致")
        elif actual != expected:
            raise ValueError(f"matched gate {key} 复算不一致")
    if int(results["winning_folds_vs_matched_v80"]) != winning_folds:
        raise ValueError("winning_folds_vs_matched_v80 复算不一致")
    expected_decision = "ADVANCE_TO_STRICT_SMALL_FUSION" if expected_gate else "STOP"
    if results["decision"] != expected_decision:
        raise ValueError("decision 未由重建 OOF 正确推导")
    if bool(results["allowed_for_fusion"]) != expected_gate:
        raise ValueError("allowed_for_fusion 未由 matched gate 正确推导")
    if results["allowed_for_submission"] is not False:
        raise ValueError("allowed_for_submission 必须保持 false，提交预算为0")

    submission = pd.read_csv(paths["submission"])
    recipe.base.validate_submission(submission, test, sample)
    if not np.allclose(
        submission[config["target"]].to_numpy(np.float64),
        rebuilt_test,
        atol=1e-15,
        rtol=0.0,
    ):
        raise ValueError("submission 与 checkpoint 重建 test 预测不一致")
    importance = pd.read_csv(paths["feature_importance"])
    if list(importance.columns) != [
        "feature",
        "gain_mean",
        "gain_std",
        "split_mean",
        "split_std",
    ] or len(importance) != int(results["feature_count"]):
        raise ValueError("feature_importance schema 不一致")
    if not np.isfinite(importance.iloc[:, 1:].to_numpy(np.float64)).all():
        raise ValueError("feature_importance 含 NaN/Inf")

    expected_outputs = {
        "oof_proba",
        "test_proba",
        "submission",
        "feature_importance",
    }
    if set(sources.get("outputs", {})) != expected_outputs:
        raise ValueError("sources 输出清单不完整")
    for name in expected_outputs:
        actual_hash = sha256_file(paths[name])
        if actual_hash != results["artifact_sha256"][name]:
            raise ValueError(f"cv_results 中 {name} 哈希不一致")
        if actual_hash != sources["outputs"][name]["sha256"]:
            raise ValueError(f"sources 中 {name} 哈希不一致")
    if sources["row_identity"]["train_id_sha256"] != sha256_ids(train["id"]):
        raise ValueError("sources train id 哈希不一致")
    if sources["row_identity"]["test_id_sha256"] != sha256_ids(test["id"]):
        raise ValueError("sources test id 哈希不一致")
    if sources["row_identity"]["original_buyer_id_sha256"] != sha256_ids(
        original[ORIGINAL_ID_COLUMN]
    ):
        raise ValueError("sources original Buyer_ID 哈希不一致")
    if (
        int(sources["row_identity"]["train_rows"]) != len(train)
        or int(sources["row_identity"]["test_rows"]) != len(test)
        or int(sources["row_identity"]["original_clean_rows"]) != len(original)
    ):
        raise ValueError("sources train/test/original 行数不一致")
    if sources.get("original_data_diagnostics") != original_diagnostics:
        raise ValueError("sources original 数据诊断与当前重算不一致")
    if results.get("original_data_diagnostics") != original_diagnostics:
        raise ValueError("cv_results original 数据诊断与当前重算不一致")

    print(
        json.dumps(
            {
                "status": "COMPLETE_REBUILT_FROM_40_CHECKPOINTS_AND_VERIFIED",
                "experiment_id": EXPERIMENT_ID,
                "oof_auc": recomputed_oof_auc,
                "oof_delta_vs_matched_v80": matched_delta,
                "winning_folds_vs_matched_v80": winning_folds,
                "matched_gate_passes": expected_gate,
                "fold_auc_recomputed": len(rebuilt_fold_auc),
                "oof_elementwise_equal": True,
                "test_elementwise_equal": True,
                "strict_prior_self_check": True,
                "resource_checks_verified": len(resource_checks),
                "wall_clock_elapsed_seconds": final_resource_check[
                    "wall_elapsed_seconds"
                ],
                "peak_rss_gib": final_resource_check["peak_rss_gib"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("audit", "smoke", "train", "verify"),
        default="audit",
        help="默认 audit；正式训练必须显式指定 train。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "audit":
        audit()
    elif args.mode == "smoke":
        smoke()
    elif args.mode == "verify":
        verify_complete()
    else:
        train()


if __name__ == "__main__":
    main()
