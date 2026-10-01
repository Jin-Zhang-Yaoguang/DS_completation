# -*- coding: utf-8 -*-
"""C01-01 / P2-04：v61 配方的 outer split seed=7 稳健性复现。

默认只执行只读 audit。正式运行必须显式传入 ``--mode train``。
outer split、inner TE 与 LightGBM 随机源彼此独立，避免复现 v61 将三者
绑定到同一个 SEED 的实现方式。正式结果只能由完整 40 折拼接，smoke 不拟合模型、
不计算效果指标，也不写正式实验产物。
"""

from __future__ import annotations

import argparse
import contextlib
import gc
import hashlib
import importlib.util
import json
import os
import platform
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


EXPERIMENT_ID = "v79_v61_split7_40f"
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
BASE_DIR = MODEL_DIR / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
PROGRESS_PATH = OUT_DIR / "progress.jsonl"
LOG_PATH = OUT_DIR / "train_log.txt"
LOCK_PATH = OUT_DIR / "run.lock"

OUTER_SEED = 7
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
    required = {
        "experiment_id",
        "n_folds",
        "outer_split_seed",
        "n_inner_folds",
        "inner_te_seed_base",
        "model_seed",
        "lightgbm_params",
        "te_keys",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"frozen_config 缺少字段：{missing}")
    if config["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("experiment_id 与 runner 不一致")
    scalar_contract = {
        "n_folds": N_FOLDS,
        "outer_split_seed": OUTER_SEED,
        "n_inner_folds": N_INNER_FOLDS,
        "inner_te_seed_base": INNER_TE_SEED_BASE,
        "model_seed": MODEL_SEED,
    }
    for key, expected in scalar_contract.items():
        if config[key] != expected:
            raise ValueError(f"冻结配置 {key}={config[key]!r}，runner={expected!r}")
    return config


def load_recipe() -> Any:
    spec = importlib.util.spec_from_file_location("v79_v29_recipe", RECIPE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29 配方：{RECIPE_PATH}")
    recipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recipe)
    recipe.base.factorize_joint = recipe.factorize_joint_extended
    recipe.base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    return recipe


def validate_v61_contract(config: dict[str, Any], recipe: Any) -> None:
    base_results = json.loads((BASE_DIR / "cv_results.json").read_text(encoding="utf-8"))
    if int(base_results["n_folds"]) != N_FOLDS:
        raise ValueError("v61 折数与冻结配置不一致")
    if int(base_results["n_inner_folds"]) != N_INNER_FOLDS:
        raise ValueError("v61 inner 折数与冻结配置不一致")
    if int(base_results["seed"]) != MODEL_SEED:
        raise ValueError("v61 full seed 与冻结 model seed 不一致")
    if base_results["params"] != config["lightgbm_params"]:
        raise ValueError("冻结 LightGBM 参数不是 v61 的完整参数")
    if base_results["smooths"] != config["smooths"]:
        raise ValueError("冻结 smoothing 不是 v61 的设置")
    if base_results["te_keys"] != config["te_keys"]:
        raise ValueError("冻结 TE keys 不是 v61 的设置")
    if recipe.base.TE_KEYS != config["te_keys"]:
        raise ValueError("运行时 v29/v6 TE keys 与冻结配置不一致")
    if list(recipe.base.SMOOTHS) != config["smooths"]:
        raise ValueError("运行时 smoothing 与冻结配置不一致")
    for seed_key in (
        "random_state",
        "bagging_seed",
        "feature_fraction_seed",
        "data_random_seed",
    ):
        if int(config["lightgbm_params"][seed_key]) != MODEL_SEED:
            raise ValueError(f"{seed_key} 未保持 v61 model seed")
    if OUTER_SEED == INNER_TE_SEED_BASE or OUTER_SEED == MODEL_SEED:
        raise ValueError("outer split seed 不得与 inner/model seed 共用")


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(PROJECT_DIR)),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def build_run_contract(config: dict[str, Any]) -> dict[str, Any]:
    source_files = {
        "candidate_runner": Path(__file__).resolve(),
        "frozen_config": CONFIG_PATH,
        "v61_wrapper": V61_SCRIPT_PATH,
        "v29_recipe": RECIPE_PATH,
        "v6_recipe": V6_SCRIPT_PATH,
        "train_csv": DATA_DIR / "train.csv",
        "test_csv": DATA_DIR / "test.csv",
        "sample_submission_csv": DATA_DIR / "sample_submission.csv",
        "base_cv_results": BASE_DIR / "cv_results.json",
        "base_oof": BASE_DIR / "oof_proba.npy",
        "base_test": BASE_DIR / "test_proba.npy",
    }
    missing = [str(path) for path in source_files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"运行合同来源文件缺失：{missing}")
    records = {name: file_record(path) for name, path in source_files.items()}
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "frozen_config_sha256": sha256_file(CONFIG_PATH),
        "sources": records,
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


def validate_base_artifacts(
    config: dict[str, Any], train: pd.DataFrame, test: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    base_results = json.loads((BASE_DIR / "cv_results.json").read_text(encoding="utf-8"))
    base_oof = np.load(BASE_DIR / "oof_proba.npy", mmap_mode="r")
    base_test = np.load(BASE_DIR / "test_proba.npy", mmap_mode="r")
    validate_probability_array("base_oof", base_oof, len(train))
    validate_probability_array("base_test", base_test, len(test))
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    recomputed = float(roc_auc_score(y, base_oof))
    if not np.isclose(recomputed, base_results["oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("v61 OOF 复算结果与 cv_results 不一致")
    if not np.isclose(
        recomputed, config["baseline_oof_auc"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("v61 OOF 与冻结基准不一致")
    return base_oof, base_test, base_results


def validate_data_contract(
    config: dict[str, Any], recipe: Any
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, test, sample = recipe.base.load_data()
    if len(train) != int(config["expected_train_rows"]):
        raise ValueError("train 行数与冻结配置不一致")
    if len(test) != int(config["expected_test_rows"]):
        raise ValueError("test 行数与冻结配置不一致")
    if not train[config["id_column"]].is_unique or not test[config["id_column"]].is_unique:
        raise ValueError("train/test id 必须唯一")
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample_submission 与 test id 行序不一致")
    validate_base_artifacts(config, train, test)
    return train, test, sample


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
def single_instance_lock(run_contract_sha256: str) -> Iterator[None]:
    lock_payload = {
        "pid": os.getpid(),
        "experiment_id": EXPERIMENT_ID,
        "run_contract_sha256": run_contract_sha256,
        "created_at_utc": utc_now(),
    }
    try:
        descriptor = os.open(LOCK_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        existing = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        pid = int(existing.get("pid", -1))
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, ValueError):
            LOCK_PATH.unlink()
            descriptor = os.open(LOCK_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        else:
            raise RuntimeError(f"已有 v79 实例运行，pid={pid}")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(lock_payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        if LOCK_PATH.exists():
            current = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            if int(current.get("pid", -1)) == os.getpid():
                LOCK_PATH.unlink()


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
        stored_idx_hash = hashlib.sha256(stored_idx.tobytes()).hexdigest()
        if str(saved["valid_idx_sha256"].item()) != stored_idx_hash:
            raise ValueError(f"{path.name} valid_idx 哈希损坏")
        valid_pred = saved["valid_pred"].astype(np.float64, copy=True)
        test_pred = saved["test_pred"].astype(np.float64, copy=True)
        gain = saved["gain"].astype(np.float64, copy=True)
        split = saved["split"].astype(np.float64, copy=True)
        best_iteration = int(saved["best_iteration"].item())
        fold_auc = float(saved["fold_auc"].item())
        elapsed_seconds = float(saved["elapsed_seconds"].item())
    validate_probability_array("checkpoint.valid_pred", valid_pred, len(valid_idx))
    validate_probability_array("checkpoint.test_pred", test_pred, test_rows)
    if gain.shape != (feature_count,) or split.shape != (feature_count,):
        raise ValueError(f"{path.name} importance shape 不一致")
    if not np.isfinite(gain).all() or not np.isfinite(split).all():
        raise ValueError(f"{path.name} importance 含 NaN/Inf")
    if best_iteration <= 0 or not np.isfinite(fold_auc):
        raise ValueError(f"{path.name} best_iteration/fold_auc 非法")
    return {
        "valid_pred": valid_pred,
        "test_pred": test_pred,
        "best_iteration": best_iteration,
        "gain": gain,
        "split": split,
        "fold_auc": fold_auc,
        "elapsed_seconds": elapsed_seconds,
    }


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


def audit() -> dict[str, Any]:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v61_contract(config, recipe)
    run_contract = build_run_contract(config)
    train, test, _ = validate_data_contract(config, recipe)
    report = {
        "status": "AUDIT_OK_NO_TRAINING",
        "experiment_id": EXPERIMENT_ID,
        "train_rows": len(train),
        "test_rows": len(test),
        "outer_split_seed": OUTER_SEED,
        "inner_te_seed_base": INNER_TE_SEED_BASE,
        "model_seed": MODEL_SEED,
        "frozen_config_sha256": run_contract["frozen_config_sha256"],
        "run_contract_sha256": run_contract["run_contract_sha256"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def smoke() -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v61_contract(config, recipe)
    run_contract = build_run_contract(config)
    train, test, _ = validate_data_contract(config, recipe)

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
    smoke_train_idx = np.unique(
        np.concatenate(
            [np.linspace(0, len(train) - 1, 5000, dtype=np.int64), train_extremes]
        )
    )
    smoke_test_idx = np.unique(
        np.concatenate(
            [np.linspace(0, len(test) - 1, 2000, dtype=np.int64), test_extremes]
        )
    )
    smoke_train = train.iloc[smoke_train_idx].reset_index(drop=True)
    smoke_test = test.iloc[smoke_test_idx].reset_index(drop=True)
    y = smoke_train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    x_train, x_test, keys_train, keys_test = recipe.base.build_static_features(
        smoke_train, smoke_test
    )
    outer = StratifiedKFold(n_splits=2, shuffle=True, random_state=OUTER_SEED)
    fit_idx, valid_idx = next(outer.split(x_train, y))
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
        a, b, c = recipe.base.encode_key(
            keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
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
    widths = {matrix.shape[1] for matrix in matrices.values()}
    if len(widths) != 1 or not all(np.isfinite(matrix).all() for matrix in matrices.values()):
        raise ValueError("smoke 特征矩阵 shape/有限值校验失败")

    fake_valid = np.linspace(0.1, 0.9, len(valid_idx), dtype=np.float64)
    fake_test = np.full(len(smoke_test), 0.5, dtype=np.float64)
    fake_importance = np.zeros(matrices["fit"].shape[1], dtype=np.float64)
    with tempfile.TemporaryDirectory(prefix="v79_smoke_") as temporary_dir:
        checkpoint = Path(temporary_dir) / "fold_01.npz"
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
    print(
        json.dumps(
            {
                "status": "SMOKE_OK_NO_MODEL_FIT_NO_METRIC_EVIDENCE",
                "subset_train_rows": len(smoke_train),
                "subset_test_rows": len(smoke_test),
                "static_features": x_train.shape[1],
                "te_features": sum(block.shape[1] for block in fit_te),
                "total_features": matrices["fit"].shape[1],
                "checkpoint_roundtrip": True,
                "mismatched_contract_rejected": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def emit_five_fold_summary(
    logger: RunLogger,
    *,
    completed: int,
    folds: list[tuple[np.ndarray, np.ndarray]],
    fold_scores: list[float],
    oof: np.ndarray,
    coverage: np.ndarray,
    y: np.ndarray,
    base_oof: np.ndarray,
    started: float,
    trained_this_run: int,
    resumed_this_run: int,
) -> None:
    covered = coverage == 1
    partial_auc = float(roc_auc_score(y[covered], oof[covered]))
    base_partial_auc = float(roc_auc_score(y[covered], base_oof[covered]))
    elapsed = time.time() - started
    mean_per_completed = elapsed / max(completed, 1)
    payload = {
        "timestamp_utc": utc_now(),
        "event": "five_fold_summary",
        "completed_folds": completed,
        "total_folds": len(folds),
        "trained_this_run": trained_this_run,
        "resumed_this_run": resumed_this_run,
        "covered_rows": int(covered.sum()),
        "partial_oof_auc": partial_auc,
        "base_auc_same_rows": base_partial_auc,
        "partial_delta_vs_base": partial_auc - base_partial_auc,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "elapsed_seconds": elapsed,
        "rough_eta_seconds": mean_per_completed * (len(folds) - completed),
    }
    append_progress(payload)
    logger.emit(
        "summary "
        f"folds={completed}/{len(folds)} partial_oof={partial_auc:.9f} "
        f"base_same_rows={base_partial_auc:.9f} "
        f"delta={partial_auc-base_partial_auc:+.9f} "
        f"trained={trained_this_run} resumed={resumed_this_run} "
        f"eta={payload['rough_eta_seconds']:.0f}s"
    )


def write_budget_failure(
    *,
    config: dict[str, Any],
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
) -> None:
    compute_seconds = float(sum(row["elapsed_seconds"] for row in fold_rows))
    result = {
        "schema_version": 1,
        "status": "FAILED",
        "experiment_id": EXPERIMENT_ID,
        "competition": config["competition"],
        "model": "v61 income-bin10 multiscale nested TE LightGBM, outer split seed 7",
        "hypothesis": (
            "changing only the outer split seed should preserve v61 OOF expectation "
            "while supplying an independent test-side fold average for P2-04"
        ),
        "unique_primary_variable": "outer_split_seed: 104395303 -> 7",
        "base": config["baseline"],
        "base_oof_auc": config["baseline_oof_auc"],
        "n_folds": N_FOLDS,
        "completed_folds": len(fold_rows),
        "outer_split_seed": OUTER_SEED,
        "n_inner_folds": N_INNER_FOLDS,
        "inner_te_seed_base": INNER_TE_SEED_BASE,
        "model_seed": MODEL_SEED,
        "params": config["lightgbm_params"],
        "fold_auc": fold_scores,
        "best_iterations": best_iterations,
        "fold_diagnostics": fold_rows,
        "elapsed_model_fold_seconds": compute_seconds,
        "failure_attribution": "COMPUTE_BUDGET",
        "failure_reason": (
            f"累计 fold 计算时间超过预注册 {config['time_budget_minutes']} 分钟；"
            "停止实验，不生成部分 OOF 效果结论。"
        ),
        "missing_artifacts": [
            "oof_proba.npy",
            "test_proba.npy",
            "submission.csv",
            "sources.json",
        ],
        "decision": "STOP",
        "allowed_for_p2_04_bag": False,
        "allowed_for_submission": False,
        "submission_budget": 0,
        "frozen_config_sha256": config_sha256,
        "run_contract_sha256": run_contract_sha256,
    }
    atomic_write_json(OUT_DIR / "cv_results.json", result)


def train() -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v61_contract(config, recipe)
    run_contract = build_run_contract(config)
    config_hash = run_contract["frozen_config_sha256"]
    contract_hash = run_contract["run_contract_sha256"]
    logger = RunLogger(LOG_PATH)

    complete_path = OUT_DIR / "cv_results.json"
    if complete_path.exists():
        existing = json.loads(complete_path.read_text(encoding="utf-8"))
        if existing.get("status") == "COMPLETE":
            logger.emit("已有 COMPLETE 结果；执行完整校验而非重训")
            verify_complete()
            return
        raise RuntimeError("cv_results.json 已存在但不是 COMPLETE，需先人工审计")

    with single_instance_lock(contract_hash):
        started = time.time()
        logger.emit(
            f"start mode=train config_sha256={config_hash} "
            f"run_contract_sha256={contract_hash}"
        )
        train_frame, test_frame, sample = validate_data_contract(config, recipe)
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
        if len(all_features) != 113 or x_train.shape[1] != 62 or len(te_names) != 51:
            raise ValueError("特征 schema 与 v61 的 62 static + 51 TE 不一致")
        logger.emit(
            f"data train={train_frame.shape} test={test_frame.shape} "
            f"static={x_train.shape[1]} te={len(te_names)} total={len(all_features)}"
        )

        splitter = StratifiedKFold(
            n_splits=N_FOLDS, shuffle=True, random_state=OUTER_SEED
        )
        folds = list(splitter.split(x_train, y))
        oof = np.zeros(len(train_frame), dtype=np.float64)
        coverage = np.zeros(len(train_frame), dtype=np.int8)
        test_prediction = np.zeros(len(test_frame), dtype=np.float64)
        fold_scores: list[float] = []
        best_iterations: list[int] = []
        fold_rows: list[dict[str, Any]] = []
        importance_frames: list[pd.DataFrame] = []
        trained_this_run = 0
        resumed_this_run = 0
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        base_oof, base_test, base_results = validate_base_artifacts(
            config, train_frame, test_frame
        )

        for fold, (fit_idx, valid_idx) in enumerate(folds, start=1):
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
                fold_auc = saved["fold_auc"]
                fold_elapsed = saved["elapsed_seconds"]
                resumed_this_run += 1
                logger.emit(f"fold={fold}/{N_FOLDS} resumed auc={fold_auc:.9f}")
            else:
                fold_started = time.time()
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
                    a, b, c = recipe.base.encode_key(
                        keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
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
                fold_elapsed = time.time() - fold_started
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
                    f"fold={fold}/{N_FOLDS} trained auc={fold_auc:.9f} "
                    f"best_iteration={best_iteration} elapsed={fold_elapsed:.1f}s checkpointed"
                )
                del model, x_fit, x_valid, x_tst, fit_te, valid_te, test_te
                gc.collect()

            if coverage[valid_idx].any():
                raise ValueError(f"fold={fold} 与已有 validation coverage 重叠")
            oof[valid_idx] = valid_pred
            coverage[valid_idx] = 1
            test_prediction += fold_test / N_FOLDS
            base_bucket_auc = float(roc_auc_score(y[valid_idx], base_oof[valid_idx]))
            fold_scores.append(fold_auc)
            best_iterations.append(best_iteration)
            fold_rows.append(
                {
                    "fold": fold,
                    "inner_te_seed": INNER_TE_SEED_BASE + fold,
                    "candidate_auc": fold_auc,
                    "base_auc_same_rows": base_bucket_auc,
                    "diagnostic_delta_vs_base": fold_auc - base_bucket_auc,
                    "fit_rows": len(fit_idx),
                    "valid_rows": len(valid_idx),
                    "valid_idx_sha256": hashlib.sha256(valid_idx.tobytes()).hexdigest(),
                    "best_iteration": best_iteration,
                    "elapsed_seconds": fold_elapsed,
                    "resumed": was_resumed,
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
                    folds=folds,
                    fold_scores=fold_scores,
                    oof=oof,
                    coverage=coverage,
                    y=y,
                    base_oof=base_oof,
                    started=started,
                    trained_this_run=trained_this_run,
                    resumed_this_run=resumed_this_run,
                )
            cumulative_fold_seconds = float(
                sum(row["elapsed_seconds"] for row in fold_rows)
            )
            if (
                fold < N_FOLDS
                and cumulative_fold_seconds
                >= float(config["time_budget_minutes"]) * 60.0
            ):
                write_budget_failure(
                    config=config,
                    config_sha256=config_hash,
                    run_contract_sha256=contract_hash,
                    fold_rows=fold_rows,
                    fold_scores=fold_scores,
                    best_iterations=best_iterations,
                )
                logger.emit(
                    "stopped reason=COMPUTE_BUDGET "
                    f"completed_folds={fold}/{N_FOLDS} "
                    f"fold_compute_seconds={cumulative_fold_seconds:.1f}"
                )
                return

        if not np.all(coverage == 1):
            raise ValueError("完整 40 折后 OOF coverage 不是恰好一次")
        validate_probability_array("oof_proba", oof, len(train_frame))
        validate_probability_array("test_proba", test_prediction, len(test_frame))
        candidate_auc = float(roc_auc_score(y, oof))
        base_auc = float(base_results["oof_auc"])
        oof_delta = candidate_auc - base_auc
        test_correlation = float(spearmanr(test_prediction, base_test).statistic)
        if not np.isfinite(test_correlation):
            raise ValueError("test Spearman 非有限值")

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

        oof_path = OUT_DIR / "oof_proba.npy"
        test_path = OUT_DIR / "test_proba.npy"
        submission_path = OUT_DIR / "submission.csv"
        importance_path = OUT_DIR / "feature_importance.csv"
        atomic_save_npy(oof_path, oof)
        atomic_save_npy(test_path, test_prediction)
        atomic_write_csv(submission_path, submission)
        atomic_write_csv(importance_path, importance_summary)
        output_paths = {
            "oof_proba": oof_path,
            "test_proba": test_path,
            "submission": submission_path,
            "feature_importance": importance_path,
        }
        sources = make_source_manifest(
            run_contract, train_frame, test_frame, output_paths
        )
        sources_path = OUT_DIR / "sources.json"
        atomic_write_json(sources_path, sources)
        output_hashes = {name: sha256_file(path) for name, path in output_paths.items()}
        elapsed = time.time() - started
        stability_passes = bool(
            abs(oof_delta) < float(config["stability_max_abs_oof_delta"])
            and test_correlation >= float(config["minimum_test_spearman"])
        )
        results = {
            "schema_version": 1,
            "status": "COMPLETE",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": config["counts_toward_cycle"],
            "competition": config["competition"],
            "model": "v61 income-bin10 multiscale nested TE LightGBM, outer split seed 7",
            "hypothesis": (
                "changing only the outer split seed should preserve v61 OOF expectation "
                "while supplying an independent test-side fold average for P2-04"
            ),
            "unique_primary_variable": "outer_split_seed: 104395303 -> 7",
            "base": config["baseline"],
            "base_oof_auc": base_auc,
            "n_folds": N_FOLDS,
            "outer_split_seed": OUTER_SEED,
            "n_inner_folds": N_INNER_FOLDS,
            "inner_te_seed_base": INNER_TE_SEED_BASE,
            "inner_te_seeds": [INNER_TE_SEED_BASE + fold for fold in range(1, 41)],
            "model_seed": MODEL_SEED,
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
            "diagnostic_bucket_wins_vs_v61": int(
                sum(row["diagnostic_delta_vs_base"] > 0 for row in fold_rows)
            ),
            "oof_auc": candidate_auc,
            "oof_delta_vs_base": oof_delta,
            "test_spearman_vs_base": test_correlation,
            "validation_boundary": (
                "v79 与 v61 使用不同 outer split；逐桶差异仅为共同样本分区诊断，"
                "不是相同训练折配对证据。正式判断使用整体 OOF 与 test Spearman。"
            ),
            "stability_gate": {
                "max_abs_oof_delta": config["stability_max_abs_oof_delta"],
                "minimum_test_spearman": config["minimum_test_spearman"],
                "passes": stability_passes,
            },
            "decision": "PROMOTE" if stability_passes else "STOP",
            "allowed_for_p2_04_bag": stability_passes,
            "allowed_for_submission": False,
            "submission_budget": 0,
            "elapsed_seconds": elapsed,
            "trained_folds_this_run": trained_this_run,
            "resumed_folds_this_run": resumed_this_run,
            "frozen_config_sha256": config_hash,
            "run_contract_sha256": contract_hash,
            "code_and_input_sha256": {
                name: record["sha256"]
                for name, record in run_contract["sources"].items()
            },
            "sources_sha256": sha256_file(sources_path),
            "artifact_sha256": output_hashes,
            "artifact_validation": {
                "oof_rows": len(oof),
                "test_rows": len(test_prediction),
                "oof_exactly_once_coverage": True,
                "probabilities_finite_and_in_range": True,
                "submission_id_matches_test": True,
            },
            "runtime": run_contract["runtime"],
        }
        atomic_write_json(complete_path, results)
        verify_complete()
        logger.emit(
            f"complete oof={candidate_auc:.9f} delta_vs_v61={oof_delta:+.9f} "
            f"test_spearman={test_correlation:.9f} stability_passes={stability_passes}"
        )


def verify_complete() -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v61_contract(config, recipe)
    train, test, sample = validate_data_contract(config, recipe)
    results_path = OUT_DIR / "cv_results.json"
    sources_path = OUT_DIR / "sources.json"
    required_paths = {
        "cv_results": results_path,
        "sources": sources_path,
        "oof_proba": OUT_DIR / "oof_proba.npy",
        "test_proba": OUT_DIR / "test_proba.npy",
        "submission": OUT_DIR / "submission.csv",
        "feature_importance": OUT_DIR / "feature_importance.csv",
        "train_log": LOG_PATH,
    }
    missing = [name for name, path in required_paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"COMPLETE 产物缺失：{missing}")
    results = json.loads(results_path.read_text(encoding="utf-8"))
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    if results.get("status") != "COMPLETE":
        raise ValueError("cv_results status 不是 COMPLETE")
    if results.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("cv_results experiment_id 不一致")
    if results.get("frozen_config_sha256") != sha256_file(CONFIG_PATH):
        raise ValueError("cv_results 冻结配置哈希不一致")
    if results.get("sources_sha256") != sha256_file(sources_path):
        raise ValueError("cv_results sources.json 哈希不一致")
    stored_contract_payload = {
        "experiment_id": sources["experiment_id"],
        "frozen_config_sha256": sources["frozen_config_sha256"],
        "sources": sources["code_and_inputs"],
        "runtime": sources["runtime"],
    }
    if sha256_json(stored_contract_payload) != sources["run_contract_sha256"]:
        raise ValueError("sources.json 的运行合同哈希无法复算")
    if results.get("run_contract_sha256") != sources["run_contract_sha256"]:
        raise ValueError("cv_results 与 sources.json 的运行合同哈希不一致")
    if sources.get("frozen_config_sha256") != sha256_file(CONFIG_PATH):
        raise ValueError("sources.json 冻结配置哈希不一致")
    expected_result_lengths = {
        "fold_auc": N_FOLDS,
        "best_iterations": N_FOLDS,
        "fold_diagnostics": N_FOLDS,
        "inner_te_seeds": N_FOLDS,
    }
    for key, expected_length in expected_result_lengths.items():
        if len(results.get(key, [])) != expected_length:
            raise ValueError(f"cv_results {key} 长度不是 {expected_length}")
    if (
        int(results.get("n_folds", -1)) != N_FOLDS
        or int(results.get("outer_split_seed", -1)) != OUTER_SEED
        or int(results.get("inner_te_seed_base", -1)) != INNER_TE_SEED_BASE
        or int(results.get("model_seed", -1)) != MODEL_SEED
    ):
        raise ValueError("cv_results 随机源/折数合同不一致")
    if set(sources.get("outputs", {})) != {
        "oof_proba",
        "test_proba",
        "submission",
        "feature_importance",
    }:
        raise ValueError("sources.json 输出清单不完整")
    for name, record in sources["code_and_inputs"].items():
        source_path = PROJECT_DIR / record["path"]
        if not source_path.is_file():
            raise FileNotFoundError(f"来源文件缺失：{name}={source_path}")
        if sha256_file(source_path) != record["sha256"]:
            raise ValueError(f"来源文件 SHA-256 已改变：{name}")
    oof = np.load(required_paths["oof_proba"], mmap_mode="r")
    test_prediction = np.load(required_paths["test_proba"], mmap_mode="r")
    validate_probability_array("oof_proba", oof, len(train))
    validate_probability_array("test_proba", test_prediction, len(test))
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    recomputed_auc = float(roc_auc_score(y, oof))
    if not np.isclose(recomputed_auc, results["oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("完整 OOF AUC 复算不一致")
    submission = pd.read_csv(required_paths["submission"])
    recipe.base.validate_submission(submission, test, sample)
    if not np.allclose(
        submission[config["target"]].to_numpy(np.float64),
        test_prediction,
        atol=1e-15,
        rtol=0.0,
    ):
        raise ValueError("submission 概率与 test_proba 不一致")
    _base_oof, base_test, base_results = validate_base_artifacts(config, train, test)
    recomputed_delta = recomputed_auc - float(base_results["oof_auc"])
    recomputed_test_spearman = float(spearmanr(test_prediction, base_test).statistic)
    if not np.isclose(
        recomputed_delta, results["oof_delta_vs_base"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("OOF delta 复算不一致")
    if not np.isclose(
        recomputed_test_spearman,
        results["test_spearman_vs_base"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("test Spearman 复算不一致")
    recomputed_gate = bool(
        abs(recomputed_delta) < float(config["stability_max_abs_oof_delta"])
        and recomputed_test_spearman >= float(config["minimum_test_spearman"])
    )
    if recomputed_gate != bool(results["stability_gate"]["passes"]):
        raise ValueError("稳定性门槛复算不一致")
    importance = pd.read_csv(required_paths["feature_importance"])
    if list(importance.columns) != [
        "feature",
        "gain_mean",
        "gain_std",
        "split_mean",
        "split_std",
    ]:
        raise ValueError("feature_importance 列 schema 不一致")
    if len(importance) != int(results["feature_count"]):
        raise ValueError("feature_importance 行数与 feature_count 不一致")
    if not np.isfinite(importance.iloc[:, 1:].to_numpy(np.float64)).all():
        raise ValueError("feature_importance 数值含 NaN/Inf")
    folds = list(
        StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=OUTER_SEED).split(
            np.zeros(len(train)), y
        )
    )
    checkpoint_paths = sorted(CHECKPOINT_DIR.glob("fold_*.npz"))
    if len(checkpoint_paths) != N_FOLDS:
        raise ValueError(f"checkpoint 数量为 {len(checkpoint_paths)}，预期 {N_FOLDS}")
    for fold, (_, valid_idx) in enumerate(folds, start=1):
        diagnostic = results["fold_diagnostics"][fold - 1]
        valid_idx_hash = hashlib.sha256(valid_idx.tobytes()).hexdigest()
        if diagnostic.get("valid_idx_sha256") != valid_idx_hash:
            raise ValueError(f"fold={fold} cv_results valid_idx 哈希不一致")
        load_checkpoint(
            CHECKPOINT_DIR / f"fold_{fold:02d}.npz",
            fold=fold,
            valid_idx=valid_idx,
            test_rows=len(test),
            feature_count=int(results["feature_count"]),
            config_sha256=results["frozen_config_sha256"],
            run_contract_sha256=results["run_contract_sha256"],
        )
    for name in ("oof_proba", "test_proba", "submission", "feature_importance"):
        expected = results["artifact_sha256"][name]
        actual = sha256_file(required_paths[name])
        if actual != expected:
            raise ValueError(f"{name} SHA-256 不一致")
        source_expected = sources["outputs"][name]["sha256"]
        if actual != source_expected:
            raise ValueError(f"sources.json 中 {name} SHA-256 不一致")
    if sources["row_identity"]["train_id_sha256"] != sha256_ids(train["id"]):
        raise ValueError("sources.json train id 哈希不一致")
    if sources["row_identity"]["test_id_sha256"] != sha256_ids(test["id"]):
        raise ValueError("sources.json test id 哈希不一致")
    print(
        json.dumps(
            {
                "status": "COMPLETE_ARTIFACTS_VERIFIED",
                "experiment_id": EXPERIMENT_ID,
                "oof_auc": recomputed_auc,
                "oof_rows": len(oof),
                "test_rows": len(test_prediction),
                "sources_sha256": sha256_file(sources_path),
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
