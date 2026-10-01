# -*- coding: utf-8 -*-
"""C01-01：严格修复 v61 inner-hold smoothing prior 的40折基线。

默认仅执行 audit。正式训练必须显式传入 ``--mode train``。本 runner 独立实现，
不导入、不调用被设计拒绝的 v79。smoke 不拟合模型、不产生效果指标。
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
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


EXPERIMENT_ID = "v80_strict_v61_outer104395303_40f"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
RECIPE_PATH = MODEL_DIR / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
V61_SCRIPT_PATH = (
    MODEL_DIR
    / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
    / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303.py"
)
V6_SCRIPT_PATH = MODEL_DIR / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
HISTORICAL_DIR = MODEL_DIR / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
PROGRESS_PATH = OUT_DIR / "progress.jsonl"
LOG_PATH = OUT_DIR / "train_log.txt"
LOCK_PATH = OUT_DIR / "run.lock"

OUTER_SEED = 104_395_303
INNER_TE_SEED_BASE = 104_395_303
MODEL_SEED = 104_395_303
N_FOLDS = 40
N_INNER_FOLDS = 5


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
    spec = importlib.util.spec_from_file_location("v80_v29_recipe", RECIPE_PATH)
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
    y: np.ndarray,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    inner_folds: list[tuple[np.ndarray, np.ndarray]],
    smooths: tuple[float, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """生成严格嵌套 TE；inner hold 的 prior 和统计只来自 inner-train。"""
    fit_codes = train_codes[fit_idx]
    valid_codes = train_codes[valid_idx]
    y_fit = y[fit_idx].astype(np.float64)
    n_categories = int(max(train_codes.max(), test_codes.max())) + 1
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
    for column, smooth in enumerate(smooths):
        mapping = (
            outer_target_sum + float(smooth) * outer_prior
        ) / (outer_count + float(smooth))
        valid_block[:, column] = mapping[valid_codes]
        test_block[:, column] = mapping[test_codes]

    for name, block in (
        ("fit", fit_block),
        ("valid", valid_block),
        ("test", test_block),
    ):
        if not np.isfinite(block).all() or ((block < 0.0) | (block > 1.0)).any():
            raise ValueError(f"strict TE {name} block 概率非法")
    return fit_block, valid_block, test_block


def strict_prior_self_check() -> None:
    train_codes = np.asarray([0, 0, 1, 1, 2, 2, 0, 1, 2, 3, 3, 3, 0, 2], dtype=np.int32)
    test_codes = np.asarray([0, 1, 2, 3], dtype=np.int32)
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


def validate_lightgbm_version_contract(
    config: dict[str, Any], historical: dict[str, Any], runtime_version: str
) -> None:
    historical_version = str(historical.get("lightgbm_version", ""))
    if config.get("required_lightgbm_version") != historical_version:
        raise ValueError("冻结 LightGBM 版本与历史 v61 cv_results 不一致")
    if runtime_version != historical_version:
        raise RuntimeError(
            "当前 LightGBM 版本与历史 v61 cv_results 不一致："
            f"runtime={runtime_version}, historical={historical_version}"
        )


def validate_v61_contract(config: dict[str, Any], recipe: Any) -> dict[str, Any]:
    historical = json.loads(
        (HISTORICAL_DIR / "cv_results.json").read_text(encoding="utf-8")
    )
    if historical["params"] != config["lightgbm_params"]:
        raise ValueError("冻结 LightGBM 参数与历史 v61 不一致")
    if historical["te_keys"] != config["te_keys"]:
        raise ValueError("冻结 TE keys 与历史 v61 不一致")
    if historical["smooths"] != config["smooths"]:
        raise ValueError("冻结 smoothing 与历史 v61 不一致")
    if int(historical["n_folds"]) != N_FOLDS:
        raise ValueError("冻结 outer folds 与历史 v61 不一致")
    if int(historical["n_inner_folds"]) != N_INNER_FOLDS:
        raise ValueError("冻结 inner folds 与历史 v61 不一致")
    if int(historical["seed"]) != OUTER_SEED:
        raise ValueError("冻结 outer seed 与历史 v61 不一致")
    validate_lightgbm_version_contract(config, historical, lgb.__version__)
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
            raise ValueError(f"{key} 未保持历史 v61 model seed")
    return historical


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
        "v61_wrapper": V61_SCRIPT_PATH,
        "v29_recipe": RECIPE_PATH,
        "v6_recipe": V6_SCRIPT_PATH,
        "train_csv": DATA_DIR / "train.csv",
        "test_csv": DATA_DIR / "test.csv",
        "sample_submission_csv": DATA_DIR / "sample_submission.csv",
        "historical_v61_cv_results": HISTORICAL_DIR / "cv_results.json",
        "historical_v61_oof": HISTORICAL_DIR / "oof_proba.npy",
        "historical_v61_test": HISTORICAL_DIR / "test_proba.npy",
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
    historical = json.loads(
        (HISTORICAL_DIR / "cv_results.json").read_text(encoding="utf-8")
    )
    historical_oof = np.load(HISTORICAL_DIR / "oof_proba.npy", mmap_mode="r")
    historical_test = np.load(HISTORICAL_DIR / "test_proba.npy", mmap_mode="r")
    validate_probability_array("historical_v61_oof", historical_oof, len(train))
    validate_probability_array("historical_v61_test", historical_test, len(test))
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    recomputed = float(roc_auc_score(y, historical_oof))
    if not np.isclose(recomputed, historical["oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("历史 v61 OOF 复算与 cv_results 不一致")
    if not np.isclose(
        recomputed,
        config["historical_reference_oof_auc"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("历史 v61 OOF 与冻结参考值不一致")
    return train, test, sample, historical_oof, historical_test, historical


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
        },
        "outputs": {name: file_record(path) for name, path in output_paths.items()},
    }


def audit() -> None:
    audit_started = time.monotonic()
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v61_contract(config, recipe)
    strict_prior_self_check()
    run_contract = build_run_contract()
    train, test, _, _, _, _ = validate_data_contract(config, recipe)
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
                "status": "AUDIT_OK_NO_TRAINING",
                "experiment_id": EXPERIMENT_ID,
                "train_rows": len(train),
                "test_rows": len(test),
                "outer_split_seed": OUTER_SEED,
                "inner_te_seed_base": INNER_TE_SEED_BASE,
                "model_seed": MODEL_SEED,
                "runtime_lightgbm_version": lgb.__version__,
                "historical_v61_lightgbm_version": config[
                    "required_lightgbm_version"
                ],
                "strict_prior_self_check": True,
                "historical_reference_is_honest_baseline": False,
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
    historical = validate_v61_contract(config, recipe)
    strict_prior_self_check()
    try:
        validate_lightgbm_version_contract(config, historical, "0.0.0-smoke-mismatch")
    except RuntimeError as error:
        if "版本与历史 v61" not in str(error):
            raise
    else:
        raise AssertionError("不匹配的 LightGBM 版本未被拒绝")
    run_contract = build_run_contract()
    train, test, _, _, _, _ = validate_data_contract(config, recipe)

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
    for key in recipe.base.TE_KEYS:
        a, b, c = strict_encode_key(
            keys_train[key],
            keys_test[key],
            y,
            fit_idx,
            valid_idx,
            inner,
            tuple(config["smooths"]),
        )
        fit_te.append(a)
        valid_te.append(b)
        test_te.append(c)
    matrices = {
        "fit": np.column_stack([x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]),
        "valid": np.column_stack(
            [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
        ),
        "test": np.column_stack([x_test.to_numpy(np.float32), *test_te]),
    }
    if {matrix.shape[1] for matrix in matrices.values()} != {
        int(config["expected_total_features"])
    }:
        raise ValueError("smoke 特征宽度不是冻结的113")
    if not all(np.isfinite(matrix).all() for matrix in matrices.values()):
        raise ValueError("smoke 特征矩阵含 NaN/Inf")

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
    with tempfile.TemporaryDirectory(prefix="v80_smoke_") as temporary_dir:
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

    print(
        json.dumps(
            {
                "status": "SMOKE_OK_NO_MODEL_FIT_NO_METRIC_EVIDENCE",
                "strict_prior_self_check": True,
                "subset_train_rows": len(smoke_train),
                "subset_test_rows": len(smoke_test),
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
    oof: np.ndarray,
    coverage: np.ndarray,
    y: np.ndarray,
    historical_oof: np.ndarray,
    latest_resource_check: dict[str, Any],
    trained_this_run: int,
    resumed_this_run: int,
) -> None:
    covered = coverage == 1
    partial_auc = float(roc_auc_score(y[covered], oof[covered]))
    historical_auc = float(roc_auc_score(y[covered], historical_oof[covered]))
    payload = {
        "timestamp_utc": utc_now(),
        "evidence_level": "INTERIM_DIAGNOSTIC_NOT_FINAL",
        "completed_folds": completed,
        "total_folds": N_FOLDS,
        "trained_this_run": trained_this_run,
        "resumed_this_run": resumed_this_run,
        "covered_rows": int(covered.sum()),
        "partial_strict_oof_auc": partial_auc,
        "historical_non_strict_v61_auc_same_rows": historical_auc,
        "partial_delta_vs_historical_non_strict_v61": partial_auc - historical_auc,
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
        f"folds={completed}/{N_FOLDS} strict_partial_oof={partial_auc:.9f} "
        f"historical_v61_same_rows={historical_auc:.9f} "
        f"delta={partial_auc-historical_auc:+.9f} "
        f"trained={trained_this_run} resumed={resumed_this_run} "
        f"eta={payload['rough_eta_seconds']:.0f}s"
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
            "research_cycle": "C01",
            "cycle_position": 1,
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
    validate_v61_contract(config, recipe)
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
            historical_oof,
            historical_test,
            historical_results,
        ) = validate_data_contract(config, recipe)
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
        if (
            x_train.shape[1] != int(config["expected_static_features"])
            or len(te_names) != int(config["expected_te_features"])
            or len(all_features) != int(config["expected_total_features"])
        ):
            raise ValueError("完整特征 schema 不是冻结的 62 static + 51 TE")
        logger.emit(
            f"data train={train_frame.shape} test={test_frame.shape} "
            f"static={x_train.shape[1]} te={len(te_names)} total={len(all_features)}"
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
                for key in recipe.base.TE_KEYS:
                    a, b, c = strict_encode_key(
                        keys_train[key],
                        keys_test[key],
                        y,
                        fit_idx,
                        valid_idx,
                        inner,
                        tuple(config["smooths"]),
                    )
                    fit_te.append(a)
                    valid_te.append(b)
                    test_te.append(c)
                x_fit = np.column_stack(
                    [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
                )
                x_valid = np.column_stack(
                    [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
                )
                x_tst = np.column_stack([x_test.to_numpy(np.float32), *test_te])
                model = lgb.LGBMClassifier(**config["lightgbm_params"])
                model.fit(
                    x_fit,
                    y[fit_idx],
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
                del model, x_fit, x_valid, x_tst, fit_te, valid_te, test_te
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
            historical_auc = float(
                roc_auc_score(y[valid_idx], historical_oof[valid_idx])
            )
            fold_scores.append(fold_auc)
            best_iterations.append(best_iteration)
            fold_rows.append(
                {
                    "fold": fold,
                    "inner_te_seed": INNER_TE_SEED_BASE + fold,
                    "valid_idx_sha256": hashlib.sha256(valid_idx.tobytes()).hexdigest(),
                    "strict_candidate_auc": fold_auc,
                    "historical_non_strict_v61_auc": historical_auc,
                    "delta_vs_historical_non_strict_v61": fold_auc - historical_auc,
                    "fit_rows": len(fit_idx),
                    "valid_rows": len(valid_idx),
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
                    oof=oof,
                    coverage=coverage,
                    y=y,
                    historical_oof=historical_oof,
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
        historical_auc = float(historical_results["oof_auc"])
        historical_delta = oof_auc - historical_auc
        oof_spearman = float(spearmanr(oof, historical_oof).statistic)
        test_spearman = float(spearmanr(test_prediction, historical_test).statistic)
        if not np.isfinite(oof_spearman) or not np.isfinite(test_spearman):
            raise ValueError("与历史 v61 的 Spearman 非有限值")

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
            run_contract, train_frame, test_frame, output_paths
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
        strict_family_candidate = bool(
            oof_auc >= float(config["minimum_oof_for_strict_family_candidate"])
        )
        historical_alert = bool(
            abs(historical_delta) >= float(config["historical_difference_alert"])
        )
        results = {
            "schema_version": 1,
            "status": "COMPLETE",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": True,
            "competition": config["competition"],
            "model": "strict-prior v61-family LightGBM, 40 outer folds",
            "hypothesis": (
                "repairing the inner-hold prior boundary establishes the first strict "
                "v61-family baseline under otherwise identical training conditions"
            ),
            "unique_primary_variable": (
                "inner-hold smoothing prior: complete outer-fit mean -> inner-train mean"
            ),
            "historical_reference": config["historical_reference"],
            "historical_reference_evidence_status": config[
                "historical_reference_evidence_status"
            ],
            "historical_reference_oof_auc": historical_auc,
            "n_folds": N_FOLDS,
            "outer_split_seed": OUTER_SEED,
            "n_inner_folds": N_INNER_FOLDS,
            "inner_te_seed_base": INNER_TE_SEED_BASE,
            "inner_te_seeds": [INNER_TE_SEED_BASE + fold for fold in range(1, 41)],
            "model_seed": MODEL_SEED,
            "strict_prior_contract": config["strict_prior_contract"],
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
            "folds_above_historical_non_strict_v61": int(
                sum(row["delta_vs_historical_non_strict_v61"] > 0 for row in fold_rows)
            ),
            "oof_auc": oof_auc,
            "base": config["historical_reference"],
            "base_oof_auc": historical_auc,
            "oof_delta_vs_base": historical_delta,
            "oof_delta_vs_historical_non_strict_v61": historical_delta,
            "oof_spearman_vs_base": oof_spearman,
            "oof_spearman_vs_historical_non_strict_v61": oof_spearman,
            "test_spearman_vs_base": test_spearman,
            "test_spearman_vs_historical_non_strict_v61": test_spearman,
            "comparison_boundary": (
                "outer validation rows are identical, but historical v61 used a non-strict "
                "inner prior; delta measures the repair effect and is not a gain over an "
                "honest baseline"
            ),
            "strict_family_candidate_gate": {
                "minimum_oof_auc": config["minimum_oof_for_strict_family_candidate"],
                "passes": strict_family_candidate,
                "meaning": "eligible for a later separately preregistered strict blend test",
            },
            "historical_difference_alert": {
                "absolute_delta_threshold": config["historical_difference_alert"],
                "triggered": historical_alert,
            },
            "decision": (
                "ESTABLISH_STRICT_BASELINE" if strict_family_candidate else "STOP"
            ),
            "allowed_for_fusion": False,
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
            f"delta_vs_historical_non_strict_v61={historical_delta:+.9f} "
            f"strict_family_candidate={strict_family_candidate}"
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
    validate_v61_contract(config, recipe)
    strict_prior_self_check()
    (
        train,
        test,
        sample,
        historical_oof,
        historical_test,
        historical_results,
    ) = validate_data_contract(config, recipe)
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
        historical_fold_auc = float(
            roc_auc_score(y[valid_idx], historical_oof[valid_idx])
        )
        if (
            int(diagnostic["fold"]) != fold
            or int(diagnostic["inner_te_seed"]) != INNER_TE_SEED_BASE + fold
            or int(diagnostic["best_iteration"]) != checkpoint["best_iteration"]
            or not np.isclose(
                diagnostic["strict_candidate_auc"], fold_auc, atol=1e-12, rtol=0.0
            )
            or not np.isclose(
                diagnostic["historical_non_strict_v61_auc"],
                historical_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
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
    historical_delta = recomputed_oof_auc - float(historical_results["oof_auc"])
    if not np.isclose(
        historical_delta,
        results["oof_delta_vs_historical_non_strict_v61"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("相对历史非严格 v61 delta 复算不一致")
    rebuilt_oof_spearman = float(spearmanr(rebuilt_oof, historical_oof).statistic)
    rebuilt_test_spearman = float(spearmanr(rebuilt_test, historical_test).statistic)
    for key in (
        "oof_spearman_vs_base",
        "oof_spearman_vs_historical_non_strict_v61",
    ):
        if not np.isclose(
            rebuilt_oof_spearman, results[key], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{key} 复算不一致")
    for key in (
        "test_spearman_vs_base",
        "test_spearman_vs_historical_non_strict_v61",
    ):
        if not np.isclose(
            rebuilt_test_spearman, results[key], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{key} 复算不一致")

    expected_gate = bool(
        recomputed_oof_auc
        >= float(config["minimum_oof_for_strict_family_candidate"])
    )
    gate = results["strict_family_candidate_gate"]
    if not np.isclose(
        gate["minimum_oof_auc"],
        config["minimum_oof_for_strict_family_candidate"],
        atol=0.0,
        rtol=0.0,
    ) or bool(gate["passes"]) != expected_gate:
        raise ValueError("strict_family_candidate_gate 复算不一致")
    expected_decision = "ESTABLISH_STRICT_BASELINE" if expected_gate else "STOP"
    if results["decision"] != expected_decision:
        raise ValueError("decision 未由重建 OOF 正确推导")
    if results["allowed_for_fusion"] is not False:
        raise ValueError("allowed_for_fusion 必须保持 false，等待独立严格小融合")
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
    if (
        int(sources["row_identity"]["train_rows"]) != len(train)
        or int(sources["row_identity"]["test_rows"]) != len(test)
    ):
        raise ValueError("sources train/test 行数不一致")

    print(
        json.dumps(
            {
                "status": "COMPLETE_REBUILT_FROM_40_CHECKPOINTS_AND_VERIFIED",
                "experiment_id": EXPERIMENT_ID,
                "oof_auc": recomputed_oof_auc,
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
