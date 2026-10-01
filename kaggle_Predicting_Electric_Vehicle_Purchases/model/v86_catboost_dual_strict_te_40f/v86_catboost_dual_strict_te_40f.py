#!/usr/bin/env python3
"""v86: frozen v77 CatBoost recipe plus 51 strict nested-TE features.

The default mode is a static audit. Formal training requires ``--mode train``.
"""

from __future__ import annotations

import argparse
import fcntl
import gc
import hashlib
import importlib.util
import json
import os
import platform
import resource
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool, __version__ as catboost_version
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


EXPERIMENT_ID = "v86_catboost_dual_strict_te_40f"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
RUN_CONTRACT_PATH = OUT_DIR / "run_contract.json"
SOURCES_PATH = OUT_DIR / "sources.json"
RESULTS_PATH = OUT_DIR / "cv_results.json"
LOG_PATH = OUT_DIR / "train_log.txt"
LOCK_PATH = OUT_DIR / "run.lock"

N_FOLDS = 40
OUTER_SEED = 42
N_INNER_FOLDS = 5
INNER_TE_SEED_BASE = 42
BAG_SEEDS = [42, 2026]
FINAL_ARTIFACT_PATHS = (
    "run_contract.json",
    "sources.json",
    "train_log.txt",
    "oof_proba.npy",
    "test_proba.npy",
    "submission.csv",
    "feature_importance.csv",
    *(f"checkpoints/fold_{fold:02d}.npz" for fold in range(1, N_FOLDS + 1)),
)
EXPECTED_CAT_PARAMS = {
    "iterations": 3000,
    "learning_rate": 0.05,
    "depth": 8,
    "l2_leaf_reg": 6.0,
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "random_seed": 42,
    "one_hot_max_size": 4,
    "max_ctr_complexity": 2,
    "od_type": "Iter",
    "od_wait": 200,
    "allow_writing_files": False,
    "thread_count": 16,
    "verbose": 500,
}


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


def sha256_indices(values: np.ndarray) -> str:
    normalized = np.asarray(values, dtype="<i8")
    return hashlib.sha256(normalized.tobytes(order="C")).hexdigest()


def sha256_ids(values: pd.Series) -> str:
    digest = hashlib.sha256()
    for value in values.astype(str):
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        "path": str(path.resolve().relative_to(PROJECT_DIR.resolve())),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    _atomic_bytes(path, encoded)


def write_immutable_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValueError(f"不可变 JSON 内容漂移：{path.name}")
        return
    atomic_write_json(path, payload)


def atomic_save_npy(path: Path, values: np.ndarray) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            np.save(handle, values, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    _atomic_bytes(path, frame.to_csv(index=False).encode("utf-8"))


class RunLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def emit(self, message: str) -> None:
        line = f"{utc_now()} {message}\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        print(message, flush=True)


def load_frozen_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    scalars = {
        "schema_version": 1,
        "status": "DESIGN_READY_NOT_STARTED",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": "C01",
        "cycle_position": 7,
        "experiment_type": "SINGLE_MODEL",
        "counts_toward_cycle_when_formally_closed": True,
        "model": (
            "CatBoost dual representation plus 51 strict nested-TE numeric "
            "features, 2-seed bagging, 40 outer folds"
        ),
        "only_primary_change": "append_51_v80_strict_nested_te_numeric_features",
        "n_folds": N_FOLDS,
        "outer_split_seed": OUTER_SEED,
        "n_inner_folds": N_INNER_FOLDS,
        "inner_te_seed_base": INNER_TE_SEED_BASE,
        "expected_added_te_features": 51,
        "expected_total_features": 71,
        "catboost_version": "1.2.10",
        "wall_clock_budget_seconds": 21600,
        "memory_budget_gib": 24,
        "peak_rss_budget_bytes": 24 * 1024**3,
        "cpu_threads": 16,
        "submission_budget": 0,
    }
    for key, expected in scalars.items():
        if config.get(key) != expected:
            raise ValueError(f"冻结配置 {key}={config.get(key)!r}，预期 {expected!r}")
    if config.get("catboost_params") != EXPECTED_CAT_PARAMS:
        raise ValueError("CatBoost 参数未完全保持 v77")
    if catboost_version != config["catboost_version"]:
        raise RuntimeError(
            f"CatBoost runtime={catboost_version}，冻结={config['catboost_version']}"
        )
    if config.get("bag_seeds") != BAG_SEEDS:
        raise ValueError("双模型种子未完全保持 v77")
    if len(config.get("te_keys", {})) * len(config.get("smooths", [])) != 51:
        raise ValueError("冻结 TE schema 不是 17 keys × 3 smooths")
    if config.get("inner_te_seed_formula") != (
        "inner_te_seed_base + one_based_outer_fold"
    ):
        raise ValueError("inner TE seed 公式错误")
    expected_prior = {
        "inner_hold": (
            "prior and category statistics use only that inner-train partition"
        ),
        "outer_valid": (
            "prior and category statistics use the complete outer-fit partition"
        ),
        "test": "prior and category statistics use the complete outer-fit partition",
    }
    if config.get("strict_prior_contract") != expected_prior:
        raise ValueError("strict prior 合同错误")
    original = config.get("original_feature_contract", {})
    if (
        original.get("expected_features") != 20
        or original.get("expected_categorical_features") != 13
    ):
        raise ValueError("v77 原始特征合同错误")
    stop = config.get("ten_fold_stop_gate", {})
    if (
        stop.get("evaluate_after_completed_folds") != 10
        or stop.get("stop_if_mean_delta_lte") != 0.0
        or stop.get("stop_if_wins_lte") != 4
        or stop.get("combination") != "AND"
    ):
        raise ValueError("10折止损合同错误")
    strength = config.get("project_strength_gate", {})
    if (
        strength.get("canonical_base")
        != "v80_strict_v61_outer104395303_40f"
        or strength.get("minimum_full_oof_delta") != 0.0001
        or strength.get("comparison_buckets") != 40
        or strength.get("comparison_bucket_seed") != 42
        or strength.get("minimum_buckets_won") != 24
    ):
        raise ValueError("项目强度门槛错误")
    expected_diversity = {
        "minimum_oof_for_diversity_path": 0.9452,
        "max_spearman_for_signal": 0.995,
        "comparisons": ["v77", "strict_v80"],
        "if_strength_fails_but_signal_exists": {
            "allowed_for_fusion": False,
            "eligible_for_separate_preregistration": True,
            "decision": "DIVERSITY_ONLY_REQUIRES_SEPARATE_PREREGISTRATION",
        },
        "diagnostic_only": True,
    }
    if config.get("diversity_diagnostic") != expected_diversity:
        raise ValueError("多样性诊断门槛错误")
    blend = config.get("separate_small_blend_contract", {})
    if (
        blend.get("must_be_separate_experiment") is not True
        or blend.get("minimum_full_oof_delta") != 0.0001
        or blend.get("meta_buckets") != 5
        or blend.get("meta_bucket_seed") != 42
        or blend.get("all_meta_bucket_deltas_strictly_positive") is not True
        or blend.get("v86_does_not_fit_or_evaluate_blend") is not True
    ):
        raise ValueError("独立小融合边界错误")
    return config


def resolve_project_path(relative: str) -> Path:
    resolved = (PROJECT_DIR / relative).resolve()
    if PROJECT_DIR.resolve() not in resolved.parents:
        raise ValueError(f"来源路径越界：{relative}")
    return resolved


def validate_static_sources(config: dict[str, Any]) -> dict[str, Any]:
    baseline = config["baseline"]
    strict_source = config["strict_te_source"]
    expected = {
        baseline["runner_path"]: baseline["runner_sha256"],
        baseline["recipe_path"]: baseline["recipe_sha256"],
        baseline["audit_results_path"]: baseline["audit_results_sha256"],
        baseline["audit_sources_path"]: baseline["audit_sources_sha256"],
        strict_source["runner_path"]: strict_source["runner_sha256"],
        strict_source["config_path"]: strict_source["config_sha256"],
        **config["data_sha256"],
    }
    records = {}
    for relative, expected_hash in expected.items():
        path = resolve_project_path(relative)
        record = file_record(path)
        if record["sha256"] != expected_hash:
            raise ValueError(f"冻结来源 SHA 漂移：{relative}")
        records[relative] = record
    audit = json.loads(
        resolve_project_path(baseline["audit_results_path"]).read_text(encoding="utf-8")
    )
    if (
        audit.get("audit_id") != baseline["independent_audit_id"]
        or audit.get("status") != baseline["required_audit_status"]
        or audit.get("errors") != []
        or audit.get("frozen_hash_mismatches") != []
        or audit.get("source_manifest_sha256") != baseline["audit_sources_sha256"]
    ):
        raise ValueError("v77 独立审计不再是冻结 PASS")
    audit_sources = json.loads(
        resolve_project_path(baseline["audit_sources_path"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        audit_sources.get("audit_id") != baseline["independent_audit_id"]
        or audit_sources.get("frozen_hash_mismatches") != []
        or audit_sources.get("frozen_sha256", {}).get(baseline["runner_path"])
        != baseline["runner_sha256"]
        or audit_sources.get("frozen_sha256", {}).get(baseline["recipe_path"])
        != baseline["recipe_sha256"]
    ):
        raise ValueError("v77 独立审计来源合同错误")
    return records


def import_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法导入：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_recipes(config: dict[str, Any]) -> tuple[Any, Any, ModuleType]:
    v77_module = import_module(
        resolve_project_path(config["baseline"]["runner_path"]), "v86_v77_recipe"
    )
    v77_recipe = v77_module.load_recipe()
    if v77_recipe.CAT_PARAMS != config["catboost_params"]:
        raise ValueError("运行时 v77 CatBoost 参数漂移")
    if v77_recipe.BAG_SEEDS != config["bag_seeds"]:
        raise ValueError("运行时 v77 双 seed 漂移")
    v80_module = import_module(
        resolve_project_path(config["strict_te_source"]["runner_path"]),
        "v86_v80_strict_recipe",
    )
    v80_recipe = v80_module.load_recipe()
    if v80_recipe.base.TE_KEYS != config["te_keys"]:
        raise ValueError("运行时 v80 TE keys 漂移")
    if list(v80_recipe.base.SMOOTHS) != config["smooths"]:
        raise ValueError("运行时 v80 smoothing 漂移")
    strict_recipe_parity_self_check(v80_module)
    return v77_recipe, v80_recipe, v80_module


def strict_encode_key(
    train_codes: np.ndarray,
    test_codes: np.ndarray,
    y: np.ndarray,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    inner_folds: list[tuple[np.ndarray, np.ndarray]],
    smooths: tuple[float, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Encode with both statistics and prior restricted to each inner-train."""
    fit_codes = train_codes[fit_idx]
    valid_codes = train_codes[valid_idx]
    y_fit = y[fit_idx].astype(np.float64)
    n_categories = int(max(train_codes.max(), test_codes.max())) + 1
    fit_block = np.empty((len(fit_idx), len(smooths)), dtype=np.float32)
    coverage = np.zeros(len(fit_idx), dtype=np.int8)
    for inner_train, inner_hold in inner_folds:
        if np.intersect1d(inner_train, inner_hold, assume_unique=True).size:
            raise ValueError("inner train/hold 索引重叠")
        if len(inner_train) + len(inner_hold) != len(fit_idx):
            raise ValueError("inner train/hold 未完整划分 outer-fit")
        inner_codes = fit_codes[inner_train]
        inner_y = y_fit[inner_train]
        inner_prior = float(inner_y.mean())
        counts = np.bincount(inner_codes, minlength=n_categories).astype(np.float64)
        sums = np.bincount(
            inner_codes, weights=inner_y, minlength=n_categories
        )
        for column, smooth in enumerate(smooths):
            mapping = (sums + smooth * inner_prior) / (counts + smooth)
            fit_block[inner_hold, column] = mapping[fit_codes[inner_hold]]
        coverage[inner_hold] += 1
    if not np.all(coverage == 1):
        raise ValueError("inner OOF coverage 不是恰好一次")

    outer_prior = float(y_fit.mean())
    counts = np.bincount(fit_codes, minlength=n_categories).astype(np.float64)
    sums = np.bincount(fit_codes, weights=y_fit, minlength=n_categories)
    valid_block = np.empty((len(valid_idx), len(smooths)), dtype=np.float32)
    test_block = np.empty((len(test_codes), len(smooths)), dtype=np.float32)
    for column, smooth in enumerate(smooths):
        mapping = (sums + smooth * outer_prior) / (counts + smooth)
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
    train_codes = np.array([0, 0, 1, 1, 2, 2, 0, 1, 2, 3, 3, 3, 0, 2])
    test_codes = np.array([0, 1, 2, 3])
    y = np.array([0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1], dtype=np.int8)
    fit_idx = np.arange(12, dtype=np.int64)
    valid_idx = np.arange(12, 14, dtype=np.int64)
    inner = list(
        StratifiedKFold(n_splits=3, shuffle=True, random_state=42).split(
            np.zeros(len(fit_idx)), y[fit_idx]
        )
    )
    original = strict_encode_key(
        train_codes, test_codes, y, fit_idx, valid_idx, inner, (5.0, 15.0, 80.0)
    )
    inner_train, inner_hold = inner[0]
    changed_y = y.copy()
    changed_y[fit_idx[inner_hold]] = 1 - changed_y[fit_idx[inner_hold]]
    changed = strict_encode_key(
        train_codes,
        test_codes,
        changed_y,
        fit_idx,
        valid_idx,
        inner,
        (5.0, 15.0, 80.0),
    )
    if not np.array_equal(original[0][inner_hold], changed[0][inner_hold]):
        raise AssertionError("inner-hold 自身标签影响其 TE")
    if np.array_equal(original[1], changed[1]):
        raise AssertionError("strict prior 自检没有扰动外层映射")
    codes = train_codes[fit_idx][inner_train]
    inner_y = y[fit_idx][inner_train].astype(np.float64)
    held_code = train_codes[fit_idx][inner_hold[0]]
    count = float(np.sum(codes == held_code))
    target_sum = float(inner_y[codes == held_code].sum())
    expected = (target_sum + 5.0 * float(inner_y.mean())) / (count + 5.0)
    if not np.isclose(
        original[0][inner_hold[0], 0], expected, atol=1e-7, rtol=0.0
    ):
        raise AssertionError("inner-train prior 公式自检失败")


def strict_recipe_parity_self_check(v80_module: ModuleType) -> None:
    train_codes = np.array([0, 0, 1, 1, 2, 2, 0, 1, 2, 3, 3, 3, 0, 2])
    test_codes = np.array([0, 1, 2, 3])
    y = np.array([0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1], dtype=np.int8)
    fit_idx = np.arange(12, dtype=np.int64)
    valid_idx = np.arange(12, 14, dtype=np.int64)
    inner = list(
        StratifiedKFold(n_splits=3, shuffle=True, random_state=42).split(
            np.zeros(len(fit_idx)), y[fit_idx]
        )
    )
    expected = v80_module.strict_encode_key(
        train_codes,
        test_codes,
        y,
        fit_idx,
        valid_idx,
        inner,
        (5.0, 15.0, 80.0),
    )
    actual = strict_encode_key(
        train_codes,
        test_codes,
        y,
        fit_idx,
        valid_idx,
        inner,
        (5.0, 15.0, 80.0),
    )
    if not all(np.array_equal(left, right) for left, right in zip(actual, expected)):
        raise AssertionError("v86 strict TE 与冻结 v80 实现不一致")


def validate_probability(name: str, values: np.ndarray, rows: int) -> None:
    array = np.asarray(values)
    if array.shape != (rows,):
        raise ValueError(f"{name} shape={array.shape}，预期 {(rows,)}")
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError(f"{name} 不是数值数组")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} 含 NaN/Inf")
    if ((array < 0.0) | (array > 1.0)).any():
        raise ValueError(f"{name} 概率超出 [0,1]")


def process_peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return native if platform.system() == "Darwin" else native * 1024


def resource_check(
    config: dict[str, Any], started: float, phase: str, fold: int | None
) -> dict[str, Any]:
    elapsed = time.monotonic() - started
    peak_bytes = process_peak_rss_bytes()
    breaches = []
    if elapsed >= config["wall_clock_budget_seconds"]:
        breaches.append("WALL_CLOCK_BUDGET")
    if peak_bytes > config["peak_rss_budget_bytes"]:
        breaches.append("PEAK_RSS_BUDGET")
    return {
        "timestamp_utc": utc_now(),
        "phase": phase,
        "fold": fold,
        "status": "FAILED" if breaches else "OK",
        "breaches": breaches,
        "wall_elapsed_seconds": elapsed,
        "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
        "peak_rss_bytes": peak_bytes,
        "peak_rss_gib": peak_bytes / 1024**3,
        "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
        "peak_rss_budget_gib": config["memory_budget_gib"],
    }


def validate_resource_check(
    config: dict[str, Any], check: dict[str, Any], must_pass: bool
) -> None:
    elapsed = check.get("wall_elapsed_seconds")
    peak_bytes = check.get("peak_rss_bytes")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not np.isfinite(elapsed)
        or elapsed < 0.0
    ):
        raise ValueError("资源墙钟字段非法")
    if (
        isinstance(peak_bytes, bool)
        or not isinstance(peak_bytes, int)
        or peak_bytes < 0
    ):
        raise ValueError("资源 peak RSS 字段非法")
    if not np.isclose(
        check.get("peak_rss_gib"), peak_bytes / 1024**3, atol=1e-12, rtol=0.0
    ):
        raise ValueError("资源 bytes/GiB 不一致")
    breaches = []
    if elapsed >= config["wall_clock_budget_seconds"]:
        breaches.append("WALL_CLOCK_BUDGET")
    if peak_bytes > config["peak_rss_budget_bytes"]:
        breaches.append("PEAK_RSS_BUDGET")
    if check.get("breaches") != breaches:
        raise ValueError("资源 breach 无法复算")
    if check.get("status") != ("FAILED" if breaches else "OK"):
        raise ValueError("资源 status 无法复算")
    if (
        check.get("wall_clock_budget_seconds")
        != config["wall_clock_budget_seconds"]
        or check.get("peak_rss_budget_bytes")
        != config["peak_rss_budget_bytes"]
        or check.get("peak_rss_budget_gib") != config["memory_budget_gib"]
    ):
        raise ValueError("资源预算未冻结")
    if must_pass and breaches:
        raise ValueError("COMPLETE 记录含资源超限")


def save_checkpoint(
    path: Path,
    *,
    fold: int,
    inner_te_seed: int,
    valid_idx: np.ndarray,
    valid_pred: np.ndarray,
    test_pred: np.ndarray,
    best_iterations: list[int],
    importance: np.ndarray,
    candidate_auc: float,
    baseline_v77_auc: float,
    elapsed_seconds: float,
    resource_after: dict[str, Any],
    config_sha256: str,
    run_contract_sha256: str,
    feature_schema_sha256: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}.npz")
    try:
        with temporary.open("wb") as handle:
            np.savez_compressed(
                handle,
                fold=np.asarray(fold, dtype=np.int16),
                inner_te_seed=np.asarray(inner_te_seed, dtype=np.int64),
                valid_idx=np.asarray(valid_idx, dtype=np.int64),
                valid_pred=np.asarray(valid_pred, dtype=np.float64),
                test_pred=np.asarray(test_pred, dtype=np.float64),
                best_iterations=np.asarray(best_iterations, dtype=np.int32),
                importance=np.asarray(importance, dtype=np.float64),
                candidate_auc=np.asarray(candidate_auc, dtype=np.float64),
                baseline_v77_auc=np.asarray(baseline_v77_auc, dtype=np.float64),
                elapsed_seconds=np.asarray(elapsed_seconds, dtype=np.float64),
                resource_after_json=np.asarray(
                    json.dumps(resource_after, ensure_ascii=False, sort_keys=True)
                ),
                config_sha256=np.asarray(config_sha256),
                run_contract_sha256=np.asarray(run_contract_sha256),
                feature_schema_sha256=np.asarray(feature_schema_sha256),
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def scalar_string(value: np.ndarray) -> str:
    if np.asarray(value).shape != ():
        raise ValueError("checkpoint 字符串字段不是标量")
    return str(np.asarray(value).item())


def load_checkpoint(
    path: Path,
    *,
    config: dict[str, Any],
    fold: int,
    inner_te_seed: int,
    valid_idx: np.ndarray,
    test_rows: int,
    feature_count: int,
    config_sha256: str,
    run_contract_sha256: str,
    feature_schema_sha256: str,
    y: np.ndarray,
    baseline_v77_oof: np.ndarray,
) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as saved:
        required = {
            "fold",
            "inner_te_seed",
            "valid_idx",
            "valid_pred",
            "test_pred",
            "best_iterations",
            "importance",
            "candidate_auc",
            "baseline_v77_auc",
            "elapsed_seconds",
            "resource_after_json",
            "config_sha256",
            "run_contract_sha256",
            "feature_schema_sha256",
        }
        if set(saved.files) != required:
            raise ValueError(f"fold={fold} checkpoint schema 不一致")
        if int(saved["fold"]) != fold or int(saved["inner_te_seed"]) != inner_te_seed:
            raise ValueError(f"fold={fold} checkpoint fold/inner seed 不一致")
        if not np.array_equal(saved["valid_idx"], valid_idx):
            raise ValueError(f"fold={fold} checkpoint valid_idx 不一致")
        valid_pred = saved["valid_pred"].astype(np.float64)
        test_pred = saved["test_pred"].astype(np.float64)
        importance = saved["importance"].astype(np.float64)
        best_iterations = saved["best_iterations"].astype(int).tolist()
        validate_probability(f"fold={fold}.valid_pred", valid_pred, len(valid_idx))
        validate_probability(f"fold={fold}.test_pred", test_pred, test_rows)
        if importance.shape != (feature_count,) or not np.isfinite(importance).all():
            raise ValueError(f"fold={fold} importance 非法")
        if len(best_iterations) != 2 or any(value <= 0 for value in best_iterations):
            raise ValueError(f"fold={fold} 双 seed best_iterations 非法")
        if scalar_string(saved["config_sha256"]) != config_sha256:
            raise ValueError(f"fold={fold} config SHA 不一致")
        if scalar_string(saved["run_contract_sha256"]) != run_contract_sha256:
            raise ValueError(f"fold={fold} run-contract SHA 不一致")
        if scalar_string(saved["feature_schema_sha256"]) != feature_schema_sha256:
            raise ValueError(f"fold={fold} feature schema SHA 不一致")
        candidate_auc = float(saved["candidate_auc"])
        baseline_auc = float(saved["baseline_v77_auc"])
        if not np.isclose(
            candidate_auc,
            roc_auc_score(y[valid_idx], valid_pred),
            atol=1e-12,
            rtol=0.0,
        ):
            raise ValueError(f"fold={fold} candidate AUC 复算不一致")
        if not np.isclose(
            baseline_auc,
            roc_auc_score(y[valid_idx], baseline_v77_oof[valid_idx]),
            atol=1e-12,
            rtol=0.0,
        ):
            raise ValueError(f"fold={fold} v77 AUC 复算不一致")
        resource_after = json.loads(scalar_string(saved["resource_after_json"]))
        validate_resource_check(config, resource_after, must_pass=True)
        if (
            resource_after.get("phase") != "AFTER_TRAIN_BEFORE_CHECKPOINT"
            or resource_after.get("fold") != fold
        ):
            raise ValueError(f"fold={fold} checkpoint resource phase/fold 不一致")
        elapsed_seconds = float(saved["elapsed_seconds"])
        if elapsed_seconds < 0.0 or not np.isfinite(elapsed_seconds):
            raise ValueError(f"fold={fold} elapsed 非法")
    return {
        "valid_pred": valid_pred,
        "test_pred": test_pred,
        "importance": importance,
        "best_iterations": best_iterations,
        "candidate_auc": candidate_auc,
        "baseline_v77_auc": baseline_auc,
        "delta_vs_v77": candidate_auc - baseline_auc,
        "elapsed_seconds": elapsed_seconds,
        "resource_after": resource_after,
    }


def ten_fold_stop_decision(deltas: list[float], config: dict[str, Any]) -> dict[str, Any]:
    required = config["ten_fold_stop_gate"]["evaluate_after_completed_folds"]
    if len(deltas) != required:
        raise ValueError(f"10折止损必须恰好收到 {required} 个 delta")
    mean_delta = float(np.mean(deltas))
    wins = int(sum(delta > 0.0 for delta in deltas))
    triggered = bool(
        mean_delta <= config["ten_fold_stop_gate"]["stop_if_mean_delta_lte"]
        and wins <= config["ten_fold_stop_gate"]["stop_if_wins_lte"]
    )
    return {
        "completed_folds": required,
        "mean_delta_vs_v77": mean_delta,
        "wins_vs_v77": wins,
        "triggered": triggered,
        "decision": (
            config["ten_fold_stop_gate"]["decision_if_triggered"]
            if triggered
            else "CONTINUE_TO_40F"
        ),
    }


def final_decision(
    candidate_oof_auc: float,
    full_delta_vs_v80: float,
    buckets_won_vs_v80: int,
    spearman_vs_v77: float,
    spearman_vs_v80: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    gate = config["project_strength_gate"]
    strength_passes = bool(
        full_delta_vs_v80 >= gate["minimum_full_oof_delta"]
        and buckets_won_vs_v80 >= gate["minimum_buckets_won"]
    )
    diversity_threshold = config["diversity_diagnostic"][
        "max_spearman_for_signal"
    ]
    diversity_oof_floor_passes = bool(
        candidate_oof_auc
        >= config["diversity_diagnostic"]["minimum_oof_for_diversity_path"]
    )
    correlation_signal = bool(
        min(spearman_vs_v77, spearman_vs_v80) < diversity_threshold
    )
    diversity_signal = bool(diversity_oof_floor_passes and correlation_signal)
    if strength_passes:
        decision = gate["decision_if_pass"]
        allowed_for_fusion = True
        eligible_for_separate_preregistration = False
    elif diversity_signal:
        diversity = config["diversity_diagnostic"][
            "if_strength_fails_but_signal_exists"
        ]
        decision = diversity["decision"]
        allowed_for_fusion = diversity["allowed_for_fusion"]
        eligible_for_separate_preregistration = diversity[
            "eligible_for_separate_preregistration"
        ]
    else:
        decision = "REJECT"
        allowed_for_fusion = False
        eligible_for_separate_preregistration = False
    return {
        "strength_gate_passes": strength_passes,
        "diversity_oof_floor_passes": diversity_oof_floor_passes,
        "diversity_correlation_signal": correlation_signal,
        "diversity_signal_only": bool(not strength_passes and diversity_signal),
        "decision": decision,
        "allowed_for_fusion": allowed_for_fusion,
        "eligible_for_separate_preregistration": (
            eligible_for_separate_preregistration
        ),
    }


def audit() -> dict[str, Any]:
    config = load_frozen_config()
    records = validate_static_sources(config)
    strict_prior_self_check()
    result = {
        "status": "AUDIT_OK_NO_TRAINING_OR_PREDICTION_ARRAYS_READ",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "baseline": config["baseline"]["experiment_id"],
        "added_features": config["expected_added_te_features"],
        "catboost_params_unchanged": True,
        "bag_seeds": config["bag_seeds"],
        "static_source_records": records,
        "formal_outputs_created": False,
        "formal_mode_required": "--mode train",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def smoke() -> dict[str, Any]:
    config = load_frozen_config()
    validate_static_sources(config)
    strict_prior_self_check()
    load_recipes(config)
    if not ten_fold_stop_decision([-0.001] * 10, config)["triggered"]:
        raise AssertionError("合成10折止损未触发")
    if ten_fold_stop_decision([0.001] * 5 + [-0.001] * 5, config)["triggered"]:
        raise AssertionError("胜折超过4时不应触发 AND 止损")
    diversity = final_decision(0.9453, -0.001, 20, 0.99, 0.999, config)
    if (
        diversity["allowed_for_fusion"] is not False
        or diversity["eligible_for_separate_preregistration"] is not True
    ):
        raise AssertionError("多样性-only 边界错误")
    low_oof = final_decision(0.9451, -0.001, 20, 0.99, 0.999, config)
    if (
        low_oof["decision"] != "REJECT"
        or low_oof["diversity_correlation_signal"] is not True
        or low_oof["diversity_oof_floor_passes"] is not False
    ):
        raise AssertionError("低 OOF 不得仅凭低相关进入多样性路径")
    if resource_check(config, time.monotonic(), "SMOKE", None)["breaches"]:
        raise AssertionError("smoke 意外资源超限")
    with tempfile.TemporaryDirectory(prefix="v86_smoke_") as temp_dir:
        root = Path(temp_dir)
        checkpoint = root / "fold_01.npz"
        y = np.tile(np.array([0, 1], dtype=np.int8), 10)
        valid_idx = np.arange(10, dtype=np.int64)
        baseline = np.linspace(0.1, 0.9, len(y))
        valid_pred = np.linspace(0.2, 0.8, len(valid_idx))
        test_pred = np.linspace(0.1, 0.9, 7)
        resource_after = resource_check(
            config, time.monotonic(), "AFTER_TRAIN_BEFORE_CHECKPOINT", 1
        )
        save_checkpoint(
            checkpoint,
            fold=1,
            inner_te_seed=43,
            valid_idx=valid_idx,
            valid_pred=valid_pred,
            test_pred=test_pred,
            best_iterations=[10, 11],
            importance=np.zeros(71),
            candidate_auc=float(roc_auc_score(y[valid_idx], valid_pred)),
            baseline_v77_auc=float(roc_auc_score(y[valid_idx], baseline[valid_idx])),
            elapsed_seconds=1.0,
            resource_after=resource_after,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            feature_schema_sha256="c" * 64,
        )
        loaded = load_checkpoint(
            checkpoint,
            config=config,
            fold=1,
            inner_te_seed=43,
            valid_idx=valid_idx,
            test_rows=7,
            feature_count=71,
            config_sha256="a" * 64,
            run_contract_sha256="b" * 64,
            feature_schema_sha256="c" * 64,
            y=y,
            baseline_v77_oof=baseline,
        )
        if not np.array_equal(loaded["valid_pred"], valid_pred):
            raise AssertionError("checkpoint 合成恢复失败")
        base_train = pd.DataFrame(
            np.zeros((12, 20)), columns=[f"base_{index}" for index in range(20)]
        )
        base_test = pd.DataFrame(
            np.zeros((7, 20)), columns=[f"base_{index}" for index in range(20)]
        )
        blocks_fit = [np.zeros((10, 3), dtype=np.float32) for _ in range(17)]
        blocks_valid = [np.zeros((2, 3), dtype=np.float32) for _ in range(17)]
        blocks_test = [np.zeros((7, 3), dtype=np.float32) for _ in range(17)]
        te_names = [f"te_{index}" for index in range(51)]
        frames = build_fold_frames(
            base_train,
            base_test,
            np.arange(10),
            np.arange(10, 12),
            blocks_fit,
            blocks_valid,
            blocks_test,
            te_names,
        )
        if {frame.shape[1] for frame in frames} != {71}:
            raise AssertionError("合成特征宽度不是71")
        if not all(
            all(np.issubdtype(frame[name].dtype, np.number) for name in te_names)
            for frame in frames
        ):
            raise AssertionError("51个 strict TE 未保持数值 dtype")
        for name in ("oof_proba.npy", "test_proba.npy", "submission.csv"):
            (root / name).write_bytes(b"synthetic-partial-artifact")
        failed_check = {
            **resource_check(config, time.monotonic(), "AFTER_FINAL_OUTPUTS", 40),
            "wall_elapsed_seconds": config["wall_clock_budget_seconds"],
            "status": "FAILED",
            "breaches": ["WALL_CLOCK_BUDGET"],
        }
        smoke_contract = {
            "run_contract_sha256": "d" * 64,
            "sources": {
                "runner": {
                    "path": "synthetic/runner.py",
                    "sha256": "e" * 64,
                }
            },
        }
        failed = resource_failure_payload(
            config,
            failed_check,
            40,
            smoke_contract,
            artifact_root=root,
        )
        exception_check = resource_check(
            config, time.monotonic(), "FAILED_EXCEPTION", 40
        )
        failed_exception = failed_exception_payload(
            config,
            40,
            RuntimeError("synthetic"),
            smoke_contract,
            exception_check,
            artifact_root=root,
        )
        for failure in (failed, failed_exception):
            if (
                failure["present_artifacts"]
                != ["oof_proba.npy", "test_proba.npy", "submission.csv"]
                or failure["present_artifacts_are_invalid_for_use"] is not True
            ):
                raise AssertionError("失败关闭未隔离已写出的正式产物")
    result = {
        "status": "SMOKE_OK_SYNTHETIC_ONLY_NO_TRAINING",
        "strict_prior_self_check": True,
        "strict_v80_recipe_parity": True,
        "feature_schema_20_plus_51": True,
        "checkpoint_resume_contract": True,
        "ten_fold_stop_gate": True,
        "diversity_boundary": True,
        "diversity_oof_floor": True,
        "resource_hard_stop_contract": True,
        "failed_phase2_minimum_schema": True,
        "failed_independent_verify_supported": True,
        "failed_artifact_governance": True,
        "formal_outputs_created": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def v77_audit_file_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    path = resolve_project_path(config["baseline"]["audit_sources_path"])
    sources = json.loads(path.read_text(encoding="utf-8"))
    rows = sources.get("files")
    if not isinstance(rows, list):
        raise ValueError("v77 audit sources 缺少 files")
    mapping = {row.get("path"): row for row in rows}
    if None in mapping or len(mapping) != len(rows):
        raise ValueError("v77 audit sources 路径重复或缺失")
    return mapping


def validate_audited_file(
    relative: str, audited: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    if relative not in audited:
        raise ValueError(f"v77 audit 未冻结文件：{relative}")
    record = file_record(resolve_project_path(relative))
    frozen = audited[relative]
    if (
        frozen.get("exists") is not True
        or frozen.get("sha256") != record["sha256"]
        or frozen.get("size_bytes") != record["size_bytes"]
    ):
        raise ValueError(f"v77 已审计文件漂移：{relative}")
    return record


def load_v77_baseline(
    config: dict[str, Any],
    folds: list[tuple[np.ndarray, np.ndarray]],
    train_rows: int,
    test_rows: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, dict[str, Any]]]:
    audited = v77_audit_file_map(config)
    root = "model/v77_catboost_dual_40f"
    records: dict[str, dict[str, Any]] = {}
    oof = np.zeros(train_rows, dtype=np.float64)
    coverage = np.zeros(train_rows, dtype=np.int8)
    test_prediction = np.zeros(test_rows, dtype=np.float64)
    for fold, (_, expected_valid_idx) in enumerate(folds, start=1):
        relative = f"{root}/checkpoints/fold_{fold:02d}.npz"
        records[relative] = validate_audited_file(relative, audited)
        with np.load(resolve_project_path(relative), allow_pickle=False) as saved:
            valid_idx = saved["valid_idx"].astype(np.int64)
            valid_pred = saved["valid_pred"].astype(np.float64)
            test_pred = saved["test_pred"].astype(np.float64)
            best_iterations = saved["best_iterations"]
        if not np.array_equal(valid_idx, expected_valid_idx):
            raise ValueError(f"v77 fold={fold} 不是相同 seed42 outer fold")
        validate_probability(f"v77.fold={fold}.valid", valid_pred, len(valid_idx))
        validate_probability(f"v77.fold={fold}.test", test_pred, test_rows)
        if np.asarray(best_iterations).shape != (2,):
            raise ValueError(f"v77 fold={fold} 不含两个 seed iteration")
        if coverage[valid_idx].any():
            raise ValueError(f"v77 fold={fold} coverage 重叠")
        coverage[valid_idx] = 1
        oof[valid_idx] = valid_pred
        test_prediction += test_pred / N_FOLDS
    if not np.all(coverage == 1):
        raise ValueError("v77 checkpoint 未恰好覆盖全部训练行")
    for name in ("oof_proba.npy", "test_proba.npy", "cv_results.json"):
        relative = f"{root}/{name}"
        records[relative] = validate_audited_file(relative, audited)
    stored_oof = np.load(resolve_project_path(f"{root}/oof_proba.npy"), mmap_mode="r")
    stored_test = np.load(
        resolve_project_path(f"{root}/test_proba.npy"), mmap_mode="r"
    )
    if not np.array_equal(oof, np.asarray(stored_oof)):
        raise ValueError("v77 OOF 不能由已审计 checkpoint 重建")
    if not np.allclose(
        test_prediction, np.asarray(stored_test), atol=1e-15, rtol=0.0
    ):
        raise ValueError("v77 test 不能由已审计 checkpoint 重建")
    return oof, test_prediction, records


def load_v80_canonical(
    config: dict[str, Any],
    module: ModuleType,
    train_rows: int,
    test_rows: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, dict[str, Any]]]:
    source = config["strict_te_source"]
    module.verify_complete()
    directory = resolve_project_path("model/v80_strict_v61_outer104395303_40f")
    expected = {
        "cv_results.json": source["cv_results_sha256"],
        "sources.json": source["sources_sha256"],
        "oof_proba.npy": source["oof_proba_sha256"],
        "test_proba.npy": source["test_proba_sha256"],
    }
    records = {}
    for name, frozen_hash in expected.items():
        record = file_record(directory / name)
        if record["sha256"] != frozen_hash:
            raise ValueError(f"strict v80 文件 SHA 漂移：{name}")
        records[name] = record
    results = json.loads((directory / "cv_results.json").read_text(encoding="utf-8"))
    if results.get("status") != source["required_status"]:
        raise ValueError("strict v80 不是 COMPLETE")
    oof = np.load(directory / "oof_proba.npy", mmap_mode="r")
    test = np.load(directory / "test_proba.npy", mmap_mode="r")
    validate_probability("strict_v80.oof", oof, train_rows)
    validate_probability("strict_v80.test", test, test_rows)
    return np.asarray(oof), np.asarray(test), records


def validate_data_and_features(
    config: dict[str, Any], v77_recipe: Any, v80_recipe: Any
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    np.ndarray,
    pd.DataFrame,
    pd.DataFrame,
    list[str],
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    list[str],
]:
    train, test, sample = v77_recipe.load_data()
    if config["target"] in test.columns:
        raise ValueError("测试集包含目标列，禁止读取测试标签")
    if len(train) != config["expected_train_rows"]:
        raise ValueError("train 行数错误")
    if len(test) != config["expected_test_rows"]:
        raise ValueError("test 行数错误")
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample/test id 行序错误")
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    base_train, base_test, categorical = v77_recipe.build_features(train, test)
    if (
        base_train.shape[1]
        != config["original_feature_contract"]["expected_features"]
        or len(categorical)
        != config["original_feature_contract"]["expected_categorical_features"]
        or list(base_train.columns) != list(base_test.columns)
    ):
        raise ValueError("v77 原始特征 schema 漂移")
    static_train, static_test, keys_train, keys_test = (
        v80_recipe.base.build_static_features(train, test)
    )
    del static_train, static_test
    if list(keys_train) != list(config["te_keys"]):
        raise ValueError("strict TE key 顺序漂移")
    te_names = [
        f"te_{key}_m{smooth:g}"
        for key in config["te_keys"]
        for smooth in config["smooths"]
    ]
    if len(te_names) != config["expected_added_te_features"]:
        raise ValueError("strict TE 特征数不是51")
    if set(base_train.columns).intersection(te_names):
        raise ValueError("strict TE 名称与 v77 原始特征冲突")
    if len(base_train.columns) + len(te_names) != config["expected_total_features"]:
        raise ValueError("总特征数不是71")
    return (
        train,
        test,
        sample,
        y,
        base_train,
        base_test,
        categorical,
        keys_train,
        keys_test,
        te_names,
    )


def build_fold_frames(
    base_train: pd.DataFrame,
    base_test: pd.DataFrame,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    fit_blocks: list[np.ndarray],
    valid_blocks: list[np.ndarray],
    test_blocks: list[np.ndarray],
    te_names: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fit_te = np.column_stack(fit_blocks)
    valid_te = np.column_stack(valid_blocks)
    test_te = np.column_stack(test_blocks)
    if (
        fit_te.shape[1] != 51
        or valid_te.shape[1] != 51
        or test_te.shape[1] != 51
    ):
        raise ValueError("fold strict TE 宽度不是51")
    x_fit = pd.concat(
        [
            base_train.iloc[fit_idx].copy(),
            pd.DataFrame(fit_te, index=base_train.index[fit_idx], columns=te_names),
        ],
        axis=1,
    )
    x_valid = pd.concat(
        [
            base_train.iloc[valid_idx].copy(),
            pd.DataFrame(
                valid_te, index=base_train.index[valid_idx], columns=te_names
            ),
        ],
        axis=1,
    )
    x_test = pd.concat(
        [base_test.copy(), pd.DataFrame(test_te, index=base_test.index, columns=te_names)],
        axis=1,
    )
    return x_fit, x_valid, x_test


def build_run_contract(
    config: dict[str, Any],
    v77_records: dict[str, dict[str, Any]],
    v80_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    sources = {
        "runner": file_record(Path(__file__)),
        "frozen_config": file_record(CONFIG_PATH),
        "train_csv": file_record(DATA_DIR / "train.csv"),
        "test_csv": file_record(DATA_DIR / "test.csv"),
        "sample_submission_csv": file_record(DATA_DIR / "sample_submission.csv"),
        "v77_audit_results": file_record(
            resolve_project_path(config["baseline"]["audit_results_path"])
        ),
        "v77_audit_sources": file_record(
            resolve_project_path(config["baseline"]["audit_sources_path"])
        ),
        "v77_runner": file_record(
            resolve_project_path(config["baseline"]["runner_path"])
        ),
        "v77_recipe": file_record(
            resolve_project_path(config["baseline"]["recipe_path"])
        ),
        "v80_runner": file_record(
            resolve_project_path(config["strict_te_source"]["runner_path"])
        ),
        "v80_config": file_record(
            resolve_project_path(config["strict_te_source"]["config_path"])
        ),
    }
    payload = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "immutable": True,
        "config_sha256": sha256_file(CONFIG_PATH),
        "sources": sources,
        "v77_audited_artifacts": v77_records,
        "v80_verified_artifacts": v80_records,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "catboost": catboost_version,
        },
    }
    payload["run_contract_sha256"] = sha256_json(payload)
    return payload


def rebuild_candidate_from_checkpoints(
    config: dict[str, Any],
    folds: list[tuple[np.ndarray, np.ndarray]],
    y: np.ndarray,
    test_rows: int,
    baseline_v77_oof: np.ndarray,
    feature_count: int,
    config_sha256: str,
    run_contract_sha256: str,
    feature_schema_sha256: str,
    completed_folds: int,
) -> dict[str, Any]:
    oof = np.zeros(len(y), dtype=np.float64)
    coverage = np.zeros(len(y), dtype=np.int8)
    test_prediction = np.zeros(test_rows, dtype=np.float64)
    fold_rows = []
    importance = []
    for fold in range(1, completed_folds + 1):
        valid_idx = folds[fold - 1][1]
        loaded = load_checkpoint(
            CHECKPOINT_DIR / f"fold_{fold:02d}.npz",
            config=config,
            fold=fold,
            inner_te_seed=INNER_TE_SEED_BASE + fold,
            valid_idx=valid_idx,
            test_rows=test_rows,
            feature_count=feature_count,
            config_sha256=config_sha256,
            run_contract_sha256=run_contract_sha256,
            feature_schema_sha256=feature_schema_sha256,
            y=y,
            baseline_v77_oof=baseline_v77_oof,
        )
        if coverage[valid_idx].any():
            raise ValueError(f"candidate fold={fold} coverage 重叠")
        coverage[valid_idx] = 1
        oof[valid_idx] = loaded["valid_pred"]
        test_prediction += loaded["test_pred"] / N_FOLDS
        importance.append(loaded["importance"])
        fold_rows.append(
            {
                "fold": fold,
                "inner_te_seed": INNER_TE_SEED_BASE + fold,
                "valid_idx_sha256_int64_le": sha256_indices(valid_idx),
                "candidate_auc": loaded["candidate_auc"],
                "v77_same_fold_auc": loaded["baseline_v77_auc"],
                "delta_vs_v77": loaded["delta_vs_v77"],
                "best_iterations": loaded["best_iterations"],
                "elapsed_seconds": loaded["elapsed_seconds"],
                "resource_after": loaded["resource_after"],
            }
        )
    expected_coverage = np.zeros(len(y), dtype=np.int8)
    for _, valid_idx in folds[:completed_folds]:
        expected_coverage[valid_idx] = 1
    if not np.array_equal(coverage, expected_coverage):
        raise ValueError("candidate checkpoint coverage 与 outer folds 不一致")
    return {
        "oof": oof,
        "coverage": coverage,
        "test_prediction": test_prediction,
        "fold_rows": fold_rows,
        "importance": importance,
    }


def finite_spearman(left: np.ndarray, right: np.ndarray, name: str) -> float:
    correlation = float(spearmanr(left, right).statistic)
    if not np.isfinite(correlation):
        raise ValueError(f"Spearman 不可计算：{name}")
    return correlation


def evaluate_final(
    config: dict[str, Any],
    y: np.ndarray,
    candidate_oof: np.ndarray,
    candidate_test: np.ndarray,
    v77_oof: np.ndarray,
    v77_test: np.ndarray,
    v80_oof: np.ndarray,
    v80_test: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
) -> dict[str, Any]:
    validate_probability("candidate_oof", candidate_oof, len(y))
    validate_probability("candidate_test", candidate_test, len(v80_test))
    candidate_auc = float(roc_auc_score(y, candidate_oof))
    v77_auc = float(roc_auc_score(y, v77_oof))
    v80_auc = float(roc_auc_score(y, v80_oof))
    buckets = []
    for fold, (_, valid_idx) in enumerate(folds, start=1):
        candidate_bucket_auc = float(roc_auc_score(y[valid_idx], candidate_oof[valid_idx]))
        v80_bucket_auc = float(roc_auc_score(y[valid_idx], v80_oof[valid_idx]))
        buckets.append(
            {
                "bucket": fold,
                "valid_idx_sha256_int64_le": sha256_indices(valid_idx),
                "candidate_auc": candidate_bucket_auc,
                "strict_v80_auc": v80_bucket_auc,
                "delta_vs_strict_v80": candidate_bucket_auc - v80_bucket_auc,
            }
        )
    buckets_won = int(sum(row["delta_vs_strict_v80"] > 0.0 for row in buckets))
    correlations = {
        "oof_spearman_vs_v77": finite_spearman(
            candidate_oof, v77_oof, "candidate/v77 OOF"
        ),
        "test_spearman_vs_v77": finite_spearman(
            candidate_test, v77_test, "candidate/v77 test"
        ),
        "oof_spearman_vs_strict_v80": finite_spearman(
            candidate_oof, v80_oof, "candidate/v80 OOF"
        ),
        "test_spearman_vs_strict_v80": finite_spearman(
            candidate_test, v80_test, "candidate/v80 test"
        ),
    }
    full_delta_vs_v80 = candidate_auc - v80_auc
    decision = final_decision(
        candidate_auc,
        full_delta_vs_v80,
        buckets_won,
        correlations["oof_spearman_vs_v77"],
        correlations["oof_spearman_vs_strict_v80"],
        config,
    )
    return {
        "oof_auc": candidate_auc,
        "v77_oof_auc": v77_auc,
        "oof_delta_vs_v77": candidate_auc - v77_auc,
        "strict_v80_oof_auc": v80_auc,
        "oof_delta_vs_strict_v80": full_delta_vs_v80,
        "strict_v80_seed42_common_sample_buckets": buckets,
        "buckets_won_vs_strict_v80": buckets_won,
        "correlations": correlations,
        "strength_gate": {
            "minimum_full_oof_delta": config["project_strength_gate"][
                "minimum_full_oof_delta"
            ],
            "minimum_buckets_won": config["project_strength_gate"][
                "minimum_buckets_won"
            ],
            "full_oof_delta_passes": bool(
                full_delta_vs_v80
                >= config["project_strength_gate"]["minimum_full_oof_delta"]
            ),
            "bucket_wins_pass": bool(
                buckets_won
                >= config["project_strength_gate"]["minimum_buckets_won"]
            ),
            "passes": decision["strength_gate_passes"],
        },
        **decision,
    }


def build_sources(
    config: dict[str, Any],
    run_contract: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    completed_folds: int,
    output_names: list[str],
) -> dict[str, Any]:
    checkpoint_records = {
        f"fold_{fold:02d}": file_record(CHECKPOINT_DIR / f"fold_{fold:02d}.npz")
        for fold in range(1, completed_folds + 1)
    }
    outputs = {
        name: file_record(OUT_DIR / name)
        for name in output_names
        if (OUT_DIR / name).is_file()
    }
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "immutable": True,
        "run_contract": file_record(RUN_CONTRACT_PATH),
        "run_contract_sha256": run_contract["run_contract_sha256"],
        "row_identity": {
            "train_rows": len(train),
            "test_rows": len(test),
            "train_id_sha256": sha256_ids(train[config["id_column"]]),
            "test_id_sha256": sha256_ids(test[config["id_column"]]),
        },
        "checkpoints": checkpoint_records,
        "outputs": outputs,
    }


def code_and_input_hashes(run_contract: dict[str, Any]) -> dict[str, Any]:
    sources = run_contract.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("run_contract 缺少代码/输入来源")
    result = {}
    for name, record in sources.items():
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("path"), str)
            or not isinstance(record.get("sha256"), str)
            or len(record["sha256"]) != 64
        ):
            raise ValueError(f"run_contract 来源记录非法：{name}")
        result[name] = {
            "path": record["path"],
            "sha256": record["sha256"],
        }
    return result


def fallback_failure_code_and_input_hashes(
    config: dict[str, Any],
) -> dict[str, Any]:
    records = {
        "runner": file_record(Path(__file__)),
        "frozen_config": file_record(CONFIG_PATH),
        **validate_static_sources(config),
    }
    return {
        name: {"path": record["path"], "sha256": record["sha256"]}
        for name, record in records.items()
    }


def failure_artifact_inventory(root: Path = OUT_DIR) -> dict[str, Any]:
    expected = list(FINAL_ARTIFACT_PATHS)
    present = [name for name in expected if (root / name).is_file()]
    missing = [name for name in expected if name not in present]
    return {
        "expected_artifacts": expected,
        "present_artifacts": present,
        "missing_artifacts": missing,
        "present_artifacts_are_invalid_for_use": True,
    }


def validate_failure_resource_check(
    config: dict[str, Any], check: dict[str, Any]
) -> None:
    expected_keys = {
        "timestamp_utc",
        "phase",
        "fold",
        "status",
        "breaches",
        "wall_elapsed_seconds",
        "wall_clock_budget_seconds",
        "peak_rss_bytes",
        "peak_rss_gib",
        "peak_rss_budget_bytes",
        "peak_rss_budget_gib",
    }
    if set(check) != expected_keys:
        raise ValueError("失败关闭资源 check schema 不完整")
    if not isinstance(check["timestamp_utc"], str) or not check["timestamp_utc"]:
        raise ValueError("失败关闭资源 timestamp 非法")
    if not isinstance(check["phase"], str) or not check["phase"]:
        raise ValueError("失败关闭资源 phase 非法")
    if check["fold"] is not None and (
        isinstance(check["fold"], bool)
        or not isinstance(check["fold"], int)
        or not 0 <= check["fold"] <= N_FOLDS
    ):
        raise ValueError("失败关闭资源 fold 非法")
    validate_resource_check(config, check, must_pass=False)


def failed_close_payload(
    config: dict[str, Any],
    status: str,
    completed_folds: int,
    check: dict[str, Any],
    error_type: str,
    error: str,
    run_contract: dict[str, Any] | None,
    artifact_root: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": True,
        "model": config["model"],
        "hypothesis": config["hypothesis"],
        "completed_folds": completed_folds,
        "n_folds": N_FOLDS,
        "fold_auc": None,
        "params": config["catboost_params"],
        "elapsed_seconds": check["wall_elapsed_seconds"],
        "oof_auc": None,
        "base": config["project_strength_gate"]["canonical_base"],
        "base_oof_auc": None,
        "oof_delta_vs_base": None,
        "unavailable_reason": "FAILED_RUN_ARTIFACTS_INVALID_FOR_USE",
        "decision": status,
        "error_type": error_type,
        "error": error,
        "resource_check": check,
        "code_and_input_hashes": (
            fallback_failure_code_and_input_hashes(config)
            if run_contract is None
            else code_and_input_hashes(run_contract)
        ),
        "run_contract_sha256": (
            None
            if run_contract is None
            else run_contract["run_contract_sha256"]
        ),
        "allowed_for_fusion": False,
        "eligible_for_separate_preregistration": False,
        "allowed_for_submission": False,
        "submission_budget": 0,
        **failure_artifact_inventory(artifact_root),
    }


def validate_failed_close_schema(
    payload: dict[str, Any],
    config: dict[str, Any],
    root: Path = OUT_DIR,
    run_contract: dict[str, Any] | None = None,
) -> None:
    status = payload.get("status")
    if status not in {"FAILED_RESOURCE_BUDGET", "FAILED_EXCEPTION"}:
        raise ValueError("失败关闭 status 非法")
    check = payload.get("resource_check")
    if not isinstance(check, dict):
        raise ValueError("失败关闭缺少资源 check")
    validate_failure_resource_check(config, check)
    completed_folds = payload.get("completed_folds")
    if (
        isinstance(completed_folds, bool)
        or not isinstance(completed_folds, int)
        or not 0 <= completed_folds <= N_FOLDS
    ):
        raise ValueError("失败关闭 completed_folds 非法")
    if status == "FAILED_RESOURCE_BUDGET":
        if not check["breaches"] or check["status"] != "FAILED":
            raise ValueError("资源失败关闭没有可复算的预算超限")
        error_type = "ResourceBudgetExceeded"
        error = ",".join(check["breaches"])
    else:
        if check["phase"] != "FAILED_EXCEPTION" or check["fold"] != completed_folds:
            raise ValueError("异常失败的资源 phase/fold 不一致")
        error_type = payload.get("error_type")
        error = payload.get("error")
        if not isinstance(error_type, str) or not error_type:
            raise ValueError("异常失败 error_type 非法")
        if not isinstance(error, str):
            raise ValueError("异常失败 error 非法")
    expected = failed_close_payload(
        config,
        status,
        completed_folds,
        check,
        error_type,
        error,
        run_contract,
        root,
    )
    assert_nested_close(payload, expected, status)


def resource_failure_payload(
    config: dict[str, Any],
    check: dict[str, Any],
    completed_folds: int,
    run_contract: dict[str, Any],
    artifact_root: Path = OUT_DIR,
) -> dict[str, Any]:
    payload = failed_close_payload(
        config,
        "FAILED_RESOURCE_BUDGET",
        completed_folds,
        check,
        "ResourceBudgetExceeded",
        ",".join(check["breaches"]),
        run_contract,
        artifact_root,
    )
    validate_failed_close_schema(payload, config, artifact_root, run_contract)
    return payload


def failed_exception_payload(
    config: dict[str, Any],
    completed_folds: int,
    error: Exception,
    run_contract: dict[str, Any] | None,
    check: dict[str, Any],
    artifact_root: Path = OUT_DIR,
) -> dict[str, Any]:
    payload = failed_close_payload(
        config,
        "FAILED_EXCEPTION",
        completed_folds,
        check,
        type(error).__name__,
        str(error),
        run_contract,
        artifact_root,
    )
    validate_failed_close_schema(payload, config, artifact_root, run_contract)
    return payload


def build_early_stop_result(
    config: dict[str, Any],
    run_contract: dict[str, Any],
    rebuilt: dict[str, Any],
    final_resource_check: dict[str, Any],
    sources_sha256: str,
) -> dict[str, Any]:
    validate_resource_check(config, final_resource_check, must_pass=True)
    fold_rows = rebuilt["fold_rows"]
    stop = ten_fold_stop_decision(
        [row["delta_vs_v77"] for row in fold_rows], config
    )
    if not stop["triggered"]:
        raise ValueError("EARLY_STOPPED_REJECT 构建时止损未触发")
    return {
        "schema_version": 1,
        "status": "EARLY_STOPPED_REJECT",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": True,
        "model": config["model"],
        "hypothesis": config["hypothesis"],
        "completed_folds": 10,
        "n_folds": N_FOLDS,
        "fold_auc": [row["candidate_auc"] for row in fold_rows],
        "params": config["catboost_params"],
        "elapsed_seconds": final_resource_check["wall_elapsed_seconds"],
        "oof_auc": None,
        "base": config["baseline"]["experiment_id"],
        "base_oof_auc": None,
        "oof_delta_vs_base": None,
        "unavailable_reason": "FULL_40F_OOF_NOT_AVAILABLE_AFTER_TEN_FOLD_STOP",
        "fold_rows": fold_rows,
        "ten_fold_stop_gate": stop,
        "decision": "EARLY_STOPPED_REJECT",
        "allowed_for_fusion": False,
        "eligible_for_separate_preregistration": False,
        "allowed_for_submission": False,
        "submission_budget": 0,
        "final_resource_check": final_resource_check,
        "code_and_input_hashes": code_and_input_hashes(run_contract),
        "run_contract_sha256": run_contract["run_contract_sha256"],
        "sources_sha256": sources_sha256,
        "artifact_validation": {
            "completed_checkpoint_count": 10,
            "full_oof_available": False,
            "full_test_prediction_available": False,
            "full_submission_available": False,
            "strict_prior_self_check": True,
            "v77_same_fold_indices_verified": True,
        },
    }


def validate_early_stop_result_schema(
    results: dict[str, Any],
    config: dict[str, Any],
    run_contract: dict[str, Any],
    rebuilt: dict[str, Any],
    sources_sha256: str,
) -> None:
    check = results.get("final_resource_check")
    if not isinstance(check, dict):
        raise ValueError("EARLY_STOPPED_REJECT 缺少 final_resource_check")
    expected = build_early_stop_result(
        config,
        run_contract,
        rebuilt,
        check,
        sources_sha256,
    )
    assert_nested_close(results, expected, "EARLY_STOPPED_REJECT")


def stop_on_resource_breach(
    config: dict[str, Any],
    check: dict[str, Any],
    completed_folds: int,
    run_contract: dict[str, Any],
    logger: RunLogger,
) -> bool:
    validate_resource_check(config, check, must_pass=False)
    if not check["breaches"]:
        return False
    payload = resource_failure_payload(
        config, check, completed_folds, run_contract
    )
    atomic_write_json(RESULTS_PATH, payload)
    logger.emit(
        f"FAILED_RESOURCE_BUDGET phase={check['phase']} fold={check['fold']} "
        f"breaches={','.join(check['breaches'])}"
    )
    return True


def assert_nested_close(actual: Any, expected: Any, path: str = "root") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{path} dict schema 不一致")
        for key, value in expected.items():
            assert_nested_close(actual[key], value, f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{path} list schema 不一致")
        for index, value in enumerate(expected):
            assert_nested_close(actual[index], value, f"{path}[{index}]")
        return
    if isinstance(expected, float):
        if (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or not np.isfinite(actual)
            or not np.isclose(actual, expected, atol=1e-12, rtol=0.0)
        ):
            raise ValueError(f"{path} 数值不一致")
        return
    if actual != expected:
        raise ValueError(f"{path} 不一致")


def validate_result_policy(results: dict[str, Any], evaluation: dict[str, Any]) -> None:
    for key in (
        "decision",
        "allowed_for_fusion",
        "eligible_for_separate_preregistration",
    ):
        if results.get(key) != evaluation[key]:
            raise ValueError(f"结果政策字段不一致：{key}")
    if results.get("allowed_for_submission") is not False:
        raise ValueError("submission budget 0 必须禁止提交")
    if evaluation["diversity_signal_only"]:
        if (
            results["allowed_for_fusion"] is not False
            or results["eligible_for_separate_preregistration"] is not True
        ):
            raise ValueError("diversity-only 边界不合规")


def validate_sources(
    config: dict[str, Any],
    sources: dict[str, Any],
    run_contract: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    completed_folds: int,
    output_names: list[str],
) -> None:
    expected = build_sources(
        config,
        run_contract,
        train,
        test,
        completed_folds,
        output_names,
    )
    if sources != expected:
        raise ValueError("sources 路径、行序或 SHA 不一致")


def verify_failed_close(
    results: dict[str, Any], config: dict[str, Any], root: Path = OUT_DIR
) -> dict[str, Any]:
    contract_hash = results.get("run_contract_sha256")
    stored_contract: dict[str, Any] | None = None
    if contract_hash is not None:
        if not isinstance(contract_hash, str) or len(contract_hash) != 64:
            raise ValueError("失败关闭 run-contract SHA 非法")
        contract_path = root / "run_contract.json"
        if not contract_path.is_file():
            raise ValueError("失败关闭引用的 run_contract 不存在")
        stored_contract = json.loads(contract_path.read_text(encoding="utf-8"))
        claimed_hash = stored_contract.get("run_contract_sha256")
        unsigned_contract = dict(stored_contract)
        unsigned_contract.pop("run_contract_sha256", None)
        if (
            claimed_hash != contract_hash
            or sha256_json(unsigned_contract) != contract_hash
        ):
            raise ValueError("失败关闭 run_contract 内容哈希不一致")
        expected_hashes = code_and_input_hashes(stored_contract)
        if results.get("code_and_input_hashes") != expected_hashes:
            raise ValueError("失败关闭代码/输入哈希清单不一致")
    else:
        expected_hashes = fallback_failure_code_and_input_hashes(config)
        if results.get("code_and_input_hashes") != expected_hashes:
            raise ValueError("无 run-contract 时的回退代码/输入哈希不一致")
    for name, record in expected_hashes.items():
        path = resolve_project_path(record["path"])
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise ValueError(f"失败关闭代码/输入来源漂移：{name}")
    validate_failed_close_schema(
        results,
        config,
        root,
        stored_contract,
    )
    return results


def verify_closed(results_override: dict[str, Any] | None = None) -> dict[str, Any]:
    config = load_frozen_config()
    validate_static_sources(config)
    strict_prior_self_check()
    results = (
        results_override
        if results_override is not None
        else json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    )
    if results.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("cv_results experiment_id 错误")
    failed_statuses = {"FAILED_RESOURCE_BUDGET", "FAILED_EXCEPTION"}
    if results.get("status") in failed_statuses:
        return verify_failed_close(results, config, OUT_DIR)
    if results.get("status") not in {"EARLY_STOPPED_REJECT", "COMPLETE"}:
        raise ValueError("verify 不接受未知关闭状态")
    v77_recipe, v80_recipe, v80_module = load_recipes(config)
    (
        train,
        test,
        sample,
        y,
        base_train,
        base_test,
        categorical,
        keys_train,
        keys_test,
        te_names,
    ) = validate_data_and_features(config, v77_recipe, v80_recipe)
    del base_test, keys_train, keys_test
    folds = list(
        StratifiedKFold(n_splits=40, shuffle=True, random_state=42).split(
            base_train, y
        )
    )
    v77_oof, v77_test, v77_records = load_v77_baseline(
        config, folds, len(train), len(test)
    )
    v80_oof, v80_test, v80_records = load_v80_canonical(
        config, v80_module, len(train), len(test)
    )
    expected_contract = build_run_contract(config, v77_records, v80_records)
    stored_contract = json.loads(RUN_CONTRACT_PATH.read_text(encoding="utf-8"))
    if stored_contract != expected_contract:
        raise ValueError("run_contract 与当前冻结来源不一致")
    expected_common = {
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": True,
        "allowed_for_submission": False,
        "submission_budget": 0,
    }
    for key, expected in expected_common.items():
        if results.get(key) != expected:
            raise ValueError(f"cv_results 通用合同错误：{key}")
    feature_names = list(base_train.columns) + te_names
    if len(feature_names) != 71 or len(categorical) != 13:
        raise ValueError("verify 特征 schema 不是 71/13")
    feature_schema_sha256 = sha256_json(
        {"features": feature_names, "categorical": categorical}
    )
    config_sha256 = sha256_file(CONFIG_PATH)
    contract_sha256 = stored_contract["run_contract_sha256"]
    completed_folds = int(results["completed_folds"])
    expected_completed = 10 if results["status"] == "EARLY_STOPPED_REJECT" else 40
    if completed_folds != expected_completed:
        raise ValueError("关闭状态的 completed_folds 错误")
    rebuilt = rebuild_candidate_from_checkpoints(
        config,
        folds,
        y,
        len(test),
        v77_oof,
        len(feature_names),
        config_sha256,
        contract_sha256,
        feature_schema_sha256,
        completed_folds,
    )
    for row in rebuilt["fold_rows"]:
        validate_resource_check(config, row["resource_after"], must_pass=True)
    if results.get("fold_rows") != rebuilt["fold_rows"]:
        raise ValueError("cv_results fold_rows 无法由 checkpoint 重建")

    output_names = ["train_log.txt"]
    if results["status"] == "EARLY_STOPPED_REJECT":
        stop = ten_fold_stop_decision(
            [row["delta_vs_v77"] for row in rebuilt["fold_rows"]], config
        )
        if not stop["triggered"] or results.get("ten_fold_stop_gate") != stop:
            raise ValueError("EARLY_STOPPED_REJECT 无法由前10折复算")
        validate_early_stop_result_schema(
            results,
            config,
            stored_contract,
            rebuilt,
            sha256_file(SOURCES_PATH),
        )
    else:
        output_names.extend(
            [
                "oof_proba.npy",
                "test_proba.npy",
                "submission.csv",
                "feature_importance.csv",
            ]
        )
        if not np.all(rebuilt["coverage"] == 1):
            raise ValueError("COMPLETE OOF coverage 不是恰好一次")
        stored_oof = np.load(OUT_DIR / "oof_proba.npy", mmap_mode="r")
        stored_test = np.load(OUT_DIR / "test_proba.npy", mmap_mode="r")
        if not np.array_equal(rebuilt["oof"], np.asarray(stored_oof)):
            raise ValueError("OOF 不能由 checkpoint 重建")
        if not np.array_equal(rebuilt["test_prediction"], np.asarray(stored_test)):
            raise ValueError("test 不能由 checkpoint 重建")
        submission = pd.read_csv(OUT_DIR / "submission.csv")
        if list(submission.columns) != [config["id_column"], config["target"]]:
            raise ValueError("submission schema 错误")
        if not submission[config["id_column"]].equals(test[config["id_column"]]):
            raise ValueError("submission/test id 行序错误")
        if not sample[config["id_column"]].equals(submission[config["id_column"]]):
            raise ValueError("submission/sample id 行序错误")
        if not np.allclose(
            submission[config["target"]].to_numpy(np.float64),
            rebuilt["test_prediction"],
            atol=1e-15,
            rtol=0.0,
        ):
            raise ValueError("submission 概率不能由 checkpoint 重建")
        evaluation = evaluate_final(
            config,
            y,
            rebuilt["oof"],
            rebuilt["test_prediction"],
            v77_oof,
            v77_test,
            v80_oof,
            v80_test,
            folds,
        )
        assert_nested_close(results.get("evaluation"), evaluation, "evaluation")
        validate_result_policy(results, evaluation)
        expected_model_contract = {
            "model": config["model"],
            "hypothesis": config["hypothesis"],
            "n_folds": N_FOLDS,
            "fold_auc": [row["candidate_auc"] for row in rebuilt["fold_rows"]],
            "params": config["catboost_params"],
            "outer_split_seed": OUTER_SEED,
            "n_inner_folds": N_INNER_FOLDS,
            "inner_te_seeds": [
                INNER_TE_SEED_BASE + fold for fold in range(1, N_FOLDS + 1)
            ],
            "feature_count": 71,
            "categorical_feature_count": 13,
            "added_strict_te_features": 51,
            "bag_seeds": BAG_SEEDS,
            "separate_small_blend_evaluated": False,
            "code_and_input_hashes": code_and_input_hashes(stored_contract),
        }
        for key, expected in expected_model_contract.items():
            if results.get(key) != expected:
                raise ValueError(f"cv_results 模型合同错误：{key}")
        expected_validation = {
            "oof_exactly_once_coverage": True,
            "probabilities_finite_and_in_range": True,
            "submission_id_matches_test": True,
            "checkpoint_reconstruction_required": True,
            "strict_prior_self_check": True,
            "v77_same_fold_indices_verified": True,
            "v80_frozen_verifier_passed": True,
        }
        if results.get("artifact_validation") != expected_validation:
            raise ValueError("artifact_validation 字段或值错误")
        stop = ten_fold_stop_decision(
            [row["delta_vs_v77"] for row in rebuilt["fold_rows"][:10]], config
        )
        if stop["triggered"] or results.get("ten_fold_stop_gate") != stop:
            raise ValueError("完成40折与预注册10折止损复算矛盾")
        for key, expected in (
            ("oof_auc", evaluation["oof_auc"]),
            ("base_oof_auc", evaluation["strict_v80_oof_auc"]),
            ("oof_delta_vs_base", evaluation["oof_delta_vs_strict_v80"]),
        ):
            assert_nested_close(results.get(key), expected, key)
        if results.get("base") != config["project_strength_gate"]["canonical_base"]:
            raise ValueError("顶层 base 不是 canonical strict v80")
        if results.get("separate_small_blend_evaluated") is not False:
            raise ValueError("v86 不得评价小融合")
        importance = pd.read_csv(OUT_DIR / "feature_importance.csv")
        expected_importance = pd.DataFrame(
            {
                "feature": feature_names,
                "importance_mean": np.mean(rebuilt["importance"], axis=0),
                "importance_std": np.std(rebuilt["importance"], axis=0, ddof=1),
            }
        ).sort_values("importance_mean", ascending=False, ignore_index=True)
        if list(importance.columns) != list(expected_importance.columns):
            raise ValueError("feature_importance schema 错误")
        if importance["feature"].tolist() != expected_importance["feature"].tolist():
            raise ValueError("feature_importance 特征顺序错误")
        for column in ("importance_mean", "importance_std"):
            if not np.allclose(
                importance[column], expected_importance[column], atol=1e-12, rtol=0.0
            ):
                raise ValueError(f"feature_importance {column} 无法重建")
        validate_resource_check(
            config, results["final_resource_check"], must_pass=True
        )
        assert_nested_close(
            results.get("elapsed_seconds"),
            results["final_resource_check"]["wall_elapsed_seconds"],
            "elapsed_seconds",
        )
        expected_artifact_names = set(output_names)
        if set(results.get("artifact_sha256", {})) != expected_artifact_names:
            raise ValueError("artifact_sha256 schema 不完整")
        for name in expected_artifact_names:
            if results["artifact_sha256"][name] != sha256_file(OUT_DIR / name):
                raise ValueError(f"artifact SHA 不一致：{name}")
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    validate_sources(
        config,
        sources,
        stored_contract,
        train,
        test,
        completed_folds,
        output_names,
    )
    if results.get("sources_sha256") != sha256_file(SOURCES_PATH):
        raise ValueError("cv_results sources SHA 不一致")
    if results.get("run_contract_sha256") != contract_sha256:
        raise ValueError("cv_results run-contract SHA 不一致")
    return results


def close_early_stop(
    config: dict[str, Any],
    run_contract: dict[str, Any],
    rebuilt: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    logger: RunLogger,
    started: float,
) -> None:
    stop = ten_fold_stop_decision(
        [row["delta_vs_v77"] for row in rebuilt["fold_rows"]], config
    )
    if not stop["triggered"]:
        raise ValueError("close_early_stop 在未触发时被调用")
    logger.emit(
        f"EARLY_STOPPED_REJECT folds=10 mean_delta_vs_v77="
        f"{stop['mean_delta_vs_v77']:+.9f} wins={stop['wins_vs_v77']}/10"
    )
    sources = build_sources(
        config, run_contract, train, test, 10, ["train_log.txt"]
    )
    write_immutable_json(SOURCES_PATH, sources)
    preverify_check = resource_check(
        config, started, "BEFORE_EARLY_STOP_VERIFY", 10
    )
    if stop_on_resource_breach(
        config, preverify_check, 10, run_contract, logger
    ):
        return
    sources_sha256 = sha256_file(SOURCES_PATH)
    results = build_early_stop_result(
        config, run_contract, rebuilt, preverify_check, sources_sha256
    )
    validate_early_stop_result_schema(
        results, config, run_contract, rebuilt, sources_sha256
    )
    verify_closed(results_override=results)
    final_check = resource_check(
        config, started, "AFTER_EARLY_STOP_VERIFY_PRE_CLOSE", 10
    )
    if stop_on_resource_breach(
        config, final_check, 10, run_contract, logger
    ):
        return
    results = build_early_stop_result(
        config, run_contract, rebuilt, final_check, sources_sha256
    )
    validate_early_stop_result_schema(
        results, config, run_contract, rebuilt, sources_sha256
    )
    atomic_write_json(RESULTS_PATH, results)


def train() -> None:
    config = load_frozen_config()
    validate_static_sources(config)
    strict_prior_self_check()
    if RESULTS_PATH.exists():
        existing = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        if existing.get("status") in {
            "COMPLETE",
            "EARLY_STOPPED_REJECT",
            "FAILED_RESOURCE_BUDGET",
            "FAILED_EXCEPTION",
        }:
            verify_closed()
            return
        raise RuntimeError("cv_results.json 已存在且不是可验证关闭状态")

    with LOCK_PATH.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("v86 已有 formal train 持有 flock") from error
        if RESULTS_PATH.exists():
            raise RuntimeError("取得锁后发现 cv_results.json，拒绝重复 formal")

        started = time.monotonic()
        logger = RunLogger(LOG_PATH)
        run_contract: dict[str, Any] | None = None
        completed_folds = 0
        pending_results = OUT_DIR / f".cv_results.complete.{os.getpid()}.json"
        try:
            logger.emit("formal train start; v77 recipe + 51 strict nested-TE")
            v77_recipe, v80_recipe, v80_module = load_recipes(config)
            (
                train_frame,
                test_frame,
                sample,
                y,
                base_train,
                base_test,
                categorical,
                keys_train,
                keys_test,
                te_names,
            ) = validate_data_and_features(config, v77_recipe, v80_recipe)
            feature_names = list(base_train.columns) + te_names
            feature_schema_sha256 = sha256_json(
                {"features": feature_names, "categorical": categorical}
            )
            folds = list(
                StratifiedKFold(
                    n_splits=N_FOLDS, shuffle=True, random_state=OUTER_SEED
                ).split(base_train, y)
            )
            v77_oof, v77_test, v77_records = load_v77_baseline(
                config, folds, len(train_frame), len(test_frame)
            )
            v80_oof, v80_test, v80_records = load_v80_canonical(
                config, v80_module, len(train_frame), len(test_frame)
            )
            run_contract = build_run_contract(config, v77_records, v80_records)
            write_immutable_json(RUN_CONTRACT_PATH, run_contract)
            config_sha256 = sha256_file(CONFIG_PATH)
            contract_sha256 = run_contract["run_contract_sha256"]

            initial_check = resource_check(config, started, "AFTER_INPUT_LOAD", None)
            if stop_on_resource_breach(
                config, initial_check, 0, run_contract, logger
            ):
                return

            candidate_scores: list[float] = []
            baseline_scores: list[float] = []
            deltas: list[float] = []
            CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
            for fold, (fit_idx, valid_idx) in enumerate(folds, start=1):
                before = resource_check(config, started, "BEFORE_FOLD", fold)
                if stop_on_resource_breach(
                    config, before, fold - 1, run_contract, logger
                ):
                    return
                checkpoint = CHECKPOINT_DIR / f"fold_{fold:02d}.npz"
                if checkpoint.exists():
                    loaded = load_checkpoint(
                        checkpoint,
                        config=config,
                        fold=fold,
                        inner_te_seed=INNER_TE_SEED_BASE + fold,
                        valid_idx=valid_idx,
                        test_rows=len(test_frame),
                        feature_count=len(feature_names),
                        config_sha256=config_sha256,
                        run_contract_sha256=contract_sha256,
                        feature_schema_sha256=feature_schema_sha256,
                        y=y,
                        baseline_v77_oof=v77_oof,
                    )
                else:
                    fold_started = time.monotonic()
                    inner = list(
                        StratifiedKFold(
                            n_splits=N_INNER_FOLDS,
                            shuffle=True,
                            random_state=INNER_TE_SEED_BASE + fold,
                        ).split(np.zeros(len(fit_idx)), y[fit_idx])
                    )
                    fit_blocks = []
                    valid_blocks = []
                    test_blocks = []
                    for key in config["te_keys"]:
                        fit_block, valid_block, test_block = strict_encode_key(
                            keys_train[key],
                            keys_test[key],
                            y,
                            fit_idx,
                            valid_idx,
                            inner,
                            tuple(config["smooths"]),
                        )
                        fit_blocks.append(fit_block)
                        valid_blocks.append(valid_block)
                        test_blocks.append(test_block)
                    x_fit, x_valid, x_test = build_fold_frames(
                        base_train,
                        base_test,
                        fit_idx,
                        valid_idx,
                        fit_blocks,
                        valid_blocks,
                        test_blocks,
                        te_names,
                    )
                    if (
                        x_fit.shape[1] != 71
                        or x_valid.shape[1] != 71
                        or x_test.shape[1] != 71
                    ):
                        raise ValueError(f"fold={fold} 特征宽度不是71")
                    train_pool = Pool(
                        x_fit, y[fit_idx], cat_features=categorical
                    )
                    valid_pool = Pool(
                        x_valid, y[valid_idx], cat_features=categorical
                    )
                    test_pool = Pool(x_test, cat_features=categorical)
                    valid_pred = np.zeros(len(valid_idx), dtype=np.float64)
                    fold_test = np.zeros(len(test_frame), dtype=np.float64)
                    importance = np.zeros(len(feature_names), dtype=np.float64)
                    best_iterations = []
                    for seed in BAG_SEEDS:
                        params = {**config["catboost_params"], "random_seed": seed}
                        model = CatBoostClassifier(**params)
                        model.fit(
                            train_pool, eval_set=valid_pool, use_best_model=True
                        )
                        valid_pred += (
                            model.predict_proba(valid_pool)[:, 1] / len(BAG_SEEDS)
                        )
                        fold_test += (
                            model.predict_proba(test_pool)[:, 1] / len(BAG_SEEDS)
                        )
                        best_iterations.append(int(model.get_best_iteration() + 1))
                        importance += (
                            model.get_feature_importance() / len(BAG_SEEDS)
                        )
                    candidate_auc = float(
                        roc_auc_score(y[valid_idx], valid_pred)
                    )
                    baseline_auc = float(
                        roc_auc_score(y[valid_idx], v77_oof[valid_idx])
                    )
                    fold_elapsed = time.monotonic() - fold_started
                    after_train = resource_check(
                        config, started, "AFTER_TRAIN_BEFORE_CHECKPOINT", fold
                    )
                    if stop_on_resource_breach(
                        config, after_train, fold - 1, run_contract, logger
                    ):
                        return
                    save_checkpoint(
                        checkpoint,
                        fold=fold,
                        inner_te_seed=INNER_TE_SEED_BASE + fold,
                        valid_idx=valid_idx,
                        valid_pred=valid_pred,
                        test_pred=fold_test,
                        best_iterations=best_iterations,
                        importance=importance,
                        candidate_auc=candidate_auc,
                        baseline_v77_auc=baseline_auc,
                        elapsed_seconds=fold_elapsed,
                        resource_after=after_train,
                        config_sha256=config_sha256,
                        run_contract_sha256=contract_sha256,
                        feature_schema_sha256=feature_schema_sha256,
                    )
                    loaded = {
                        "candidate_auc": candidate_auc,
                        "baseline_v77_auc": baseline_auc,
                        "delta_vs_v77": candidate_auc - baseline_auc,
                    }
                    del (
                        model,
                        train_pool,
                        valid_pool,
                        test_pool,
                        x_fit,
                        x_valid,
                        x_test,
                        fit_blocks,
                        valid_blocks,
                        test_blocks,
                    )
                    gc.collect()
                completed_folds = fold
                candidate_scores.append(loaded["candidate_auc"])
                baseline_scores.append(loaded["baseline_v77_auc"])
                deltas.append(loaded["delta_vs_v77"])
                after = resource_check(config, started, "AFTER_FOLD", fold)
                if stop_on_resource_breach(
                    config, after, completed_folds, run_contract, logger
                ):
                    return
                if fold % config["observable_summary_every_folds"] == 0:
                    recent = slice(fold - 5, fold)
                    logger.emit(
                        f"summary folds={fold-4}-{fold} "
                        f"candidate_mean={np.mean(candidate_scores[recent]):.9f} "
                        f"v77_mean={np.mean(baseline_scores[recent]):.9f} "
                        f"mean_delta={np.mean(deltas[recent]):+.9f} "
                        f"wins={sum(delta > 0 for delta in deltas[recent])}/5 "
                        f"elapsed={after['wall_elapsed_seconds']:.1f}s "
                        f"peak_rss={after['peak_rss_gib']:.3f}GiB"
                    )
                if fold == 10:
                    ten_fold_check = resource_check(
                        config, started, "BEFORE_TEN_FOLD_GATE", 10
                    )
                    if stop_on_resource_breach(
                        config, ten_fold_check, 10, run_contract, logger
                    ):
                        return
                    stop = ten_fold_stop_decision(deltas, config)
                    if stop["triggered"]:
                        rebuilt = rebuild_candidate_from_checkpoints(
                            config,
                            folds,
                            y,
                            len(test_frame),
                            v77_oof,
                            len(feature_names),
                            config_sha256,
                            contract_sha256,
                            feature_schema_sha256,
                            10,
                        )
                        close_early_stop(
                            config,
                            run_contract,
                            rebuilt,
                            train_frame,
                            test_frame,
                            logger,
                            started,
                        )
                        return

            rebuilt = rebuild_candidate_from_checkpoints(
                config,
                folds,
                y,
                len(test_frame),
                v77_oof,
                len(feature_names),
                config_sha256,
                contract_sha256,
                feature_schema_sha256,
                40,
            )
            if not np.all(rebuilt["coverage"] == 1):
                raise ValueError("40折完成后 OOF coverage 不是恰好一次")
            evaluation = evaluate_final(
                config,
                y,
                rebuilt["oof"],
                rebuilt["test_prediction"],
                v77_oof,
                v77_test,
                v80_oof,
                v80_test,
                folds,
            )
            before_outputs = resource_check(
                config, started, "BEFORE_FINAL_OUTPUTS", 40
            )
            if stop_on_resource_breach(
                config, before_outputs, 40, run_contract, logger
            ):
                return

            atomic_save_npy(OUT_DIR / "oof_proba.npy", rebuilt["oof"])
            atomic_save_npy(
                OUT_DIR / "test_proba.npy", rebuilt["test_prediction"]
            )
            submission = sample.copy()
            submission[config["target"]] = rebuilt["test_prediction"]
            v77_recipe.validate_submission(submission, test_frame, sample)
            atomic_write_csv(OUT_DIR / "submission.csv", submission)
            importance = pd.DataFrame(
                {
                    "feature": feature_names,
                    "importance_mean": np.mean(rebuilt["importance"], axis=0),
                    "importance_std": np.std(
                        rebuilt["importance"], axis=0, ddof=1
                    ),
                }
            ).sort_values("importance_mean", ascending=False, ignore_index=True)
            atomic_write_csv(OUT_DIR / "feature_importance.csv", importance)
            logger.emit(
                f"formal folds complete oof={evaluation['oof_auc']:.9f} "
                f"delta_vs_v80={evaluation['oof_delta_vs_strict_v80']:+.9f} "
                f"bucket_wins={evaluation['buckets_won_vs_strict_v80']}/40 "
                f"decision={evaluation['decision']}"
            )
            after_outputs = resource_check(
                config, started, "AFTER_FINAL_OUTPUTS", 40
            )
            if stop_on_resource_breach(
                config, after_outputs, 40, run_contract, logger
            ):
                return

            output_names = [
                "train_log.txt",
                "oof_proba.npy",
                "test_proba.npy",
                "submission.csv",
                "feature_importance.csv",
            ]
            sources = build_sources(
                config,
                run_contract,
                train_frame,
                test_frame,
                40,
                output_names,
            )
            write_immutable_json(SOURCES_PATH, sources)
            results = {
                "schema_version": 1,
                "status": "COMPLETE",
                "experiment_id": EXPERIMENT_ID,
                "research_cycle": config["research_cycle"],
                "cycle_position": config["cycle_position"],
                "experiment_type": config["experiment_type"],
                "counts_toward_cycle": True,
                "model": config["model"],
                "hypothesis": config["hypothesis"],
                "completed_folds": 40,
                "n_folds": N_FOLDS,
                "fold_auc": [
                    row["candidate_auc"] for row in rebuilt["fold_rows"]
                ],
                "params": config["catboost_params"],
                "elapsed_seconds": after_outputs["wall_elapsed_seconds"],
                "outer_split_seed": OUTER_SEED,
                "n_inner_folds": N_INNER_FOLDS,
                "inner_te_seeds": [INNER_TE_SEED_BASE + fold for fold in range(1, 41)],
                "feature_count": len(feature_names),
                "categorical_feature_count": len(categorical),
                "added_strict_te_features": len(te_names),
                "bag_seeds": BAG_SEEDS,
                "fold_rows": rebuilt["fold_rows"],
                "ten_fold_stop_gate": ten_fold_stop_decision(deltas[:10], config),
                "evaluation": evaluation,
                "oof_auc": evaluation["oof_auc"],
                "base": config["project_strength_gate"]["canonical_base"],
                "base_oof_auc": evaluation["strict_v80_oof_auc"],
                "oof_delta_vs_base": evaluation["oof_delta_vs_strict_v80"],
                "decision": evaluation["decision"],
                "allowed_for_fusion": evaluation["allowed_for_fusion"],
                "eligible_for_separate_preregistration": evaluation[
                    "eligible_for_separate_preregistration"
                ],
                "separate_small_blend_evaluated": False,
                "allowed_for_submission": False,
                "submission_budget": 0,
                "final_resource_check": after_outputs,
                "code_and_input_hashes": code_and_input_hashes(run_contract),
                "run_contract_sha256": contract_sha256,
                "sources_sha256": sha256_file(SOURCES_PATH),
                "artifact_sha256": {
                    name: sha256_file(OUT_DIR / name) for name in output_names
                },
                "artifact_validation": {
                    "oof_exactly_once_coverage": True,
                    "probabilities_finite_and_in_range": True,
                    "submission_id_matches_test": True,
                    "checkpoint_reconstruction_required": True,
                    "strict_prior_self_check": True,
                    "v77_same_fold_indices_verified": True,
                    "v80_frozen_verifier_passed": True,
                },
            }
            verify_closed(results_override=results)
            final_check = resource_check(
                config, started, "AFTER_FINAL_VERIFY_PRE_COMPLETE", 40
            )
            if stop_on_resource_breach(
                config, final_check, 40, run_contract, logger
            ):
                return
            results["final_resource_check"] = final_check
            results["elapsed_seconds"] = final_check["wall_elapsed_seconds"]
            validate_resource_check(config, final_check, must_pass=True)
            encoded = (
                json.dumps(results, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
            _atomic_bytes(pending_results, encoded)
            staged_check = resource_check(
                config, started, "COMPLETE_RESULT_STAGED", 40
            )
            if stop_on_resource_breach(
                config, staged_check, 40, run_contract, logger
            ):
                return
            os.replace(pending_results, RESULTS_PATH)
            final_scope = resource_check(
                config, started, "FORMAL_SCOPE_COMPLETE", 40
            )
            if stop_on_resource_breach(
                config, final_scope, 40, run_contract, logger
            ):
                return
            print(
                json.dumps(
                    {
                        "status": "COMPLETE_AND_VERIFIED",
                        "experiment_id": EXPERIMENT_ID,
                        "oof_auc": evaluation["oof_auc"],
                        "delta_vs_strict_v80": evaluation[
                            "oof_delta_vs_strict_v80"
                        ],
                        "bucket_wins": evaluation[
                            "buckets_won_vs_strict_v80"
                        ],
                        "decision": evaluation["decision"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        except Exception as error:
            exception_check = resource_check(
                config, started, "FAILED_EXCEPTION", completed_folds
            )
            failure = failed_exception_payload(
                config,
                completed_folds,
                error,
                run_contract,
                exception_check,
            )
            atomic_write_json(RESULTS_PATH, failure)
            print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
            raise
        finally:
            if pending_results.exists():
                pending_results.unlink()


def verify_complete() -> None:
    results = verify_closed()
    print(
        json.dumps(
            {
                "status": f"{results['status']}_VERIFIED",
                "experiment_id": EXPERIMENT_ID,
                "completed_folds": results["completed_folds"],
                "decision": results["decision"],
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
        help="默认 audit；正式训练必须显式使用 train",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "audit":
        audit()
    elif args.mode == "smoke":
        smoke()
    elif args.mode == "train":
        train()
    else:
        verify_complete()


if __name__ == "__main__":
    main()
