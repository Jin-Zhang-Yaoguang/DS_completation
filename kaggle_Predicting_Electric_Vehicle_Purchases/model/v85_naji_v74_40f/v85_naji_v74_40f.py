# -*- coding: utf-8 -*-
"""C01-06：把严格 Naji v74 配方的 outer folds 从20提升到40。

默认仅执行 audit。正式训练必须显式传入 ``--mode train``。使用 sklearn
TargetEncoder 的内层交叉拟合，不引入 v6 手工目标编码。
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import gc
import hashlib
import importlib.util
import inspect
import json
import os
import platform
import resource
import tempfile
import time
import warnings
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
from sklearn.preprocessing import TargetEncoder


EXPERIMENT_ID = "v85_naji_v74_40f"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
PROBE_PATH = MODEL_DIR / "v68_naji_accelerated_probe" / "v68_naji_accelerated_probe.py"
V69_SCRIPT_PATH = MODEL_DIR / "v69_naji_lgbm_20f" / "v69_naji_lgbm_20f.py"
V74_DIR = MODEL_DIR / "v74_naji_income_bin10_100_lgbm_20f"
V74_SCRIPT_PATH = V74_DIR / "v74_naji_income_bin10_100_lgbm_20f.py"
V80_DIR = MODEL_DIR / "v80_strict_v61_outer104395303_40f"
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
PROGRESS_PATH = OUT_DIR / "progress.jsonl"
LOG_PATH = OUT_DIR / "train_log.txt"
LOCK_PATH = OUT_DIR / "run.lock"

OUTER_SEED = 42
INNER_TE_SEED_BASE = 42
MODEL_SEED_BASE = 42
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
        "target_encoder_cv": N_INNER_FOLDS,
        "target_encoder_seed_base": INNER_TE_SEED_BASE,
        "model_seed_base": MODEL_SEED_BASE,
    }
    for key, expected in scalar_contract.items():
        if config.get(key) != expected:
            raise ValueError(f"冻结配置 {key}={config.get(key)!r}，runner={expected!r}")
    if config.get("status") != "DESIGN_READY_NOT_STARTED":
        raise ValueError("冻结配置初始状态异常")
    if float(config.get("time_budget_minutes", -1)) != 50.0:
        raise ValueError("冻结墙钟预算必须为50分钟")
    if float(config.get("wall_clock_budget_seconds", -1)) != 3000.0:
        raise ValueError("冻结墙钟预算秒数必须为3000")
    if float(config.get("memory_budget_gb", -1)) != 12.0:
        raise ValueError("冻结内存预算必须为12 GiB")
    if int(config.get("peak_rss_budget_bytes", -1)) != 12 * 1024**3:
        raise ValueError("冻结 peak RSS 字节门槛必须为12 GiB")
    if int(config.get("mechanism_reference_folds", -1)) != 20:
        raise ValueError("机制参考必须是 v74 20折")
    if (
        config.get("base") != config.get("mechanism_reference")
        or float(config.get("base_oof_auc", -1))
        != float(config.get("v74_oof_auc", -2))
    ):
        raise ValueError("标准 base 别名必须明确指向 v74 机制参考")
    if (
        float(config.get("mechanism_signal_minimum_oof_delta_vs_v74", -1))
        != 0.00003
        or int(
            config.get(
                "mechanism_signal_minimum_seed42_bucket_wins_vs_v74", -1
            )
        )
        != 24
    ):
        raise ValueError("v74 mechanism signal 必须冻结为+0.00003且24/40")
    if (
        float(config.get("project_strength_minimum_oof_delta_vs_v80", -1))
        != 0.0001
        or int(
            config.get(
                "project_strength_minimum_seed42_bucket_wins_vs_v80", -1
            )
        )
        != 24
    ):
        raise ValueError("项目单模强度门槛必须相对 v80 为+0.0001且24/40")
    if float(config.get("minimum_oof_for_diversity_path", -1)) != 0.9452:
        raise ValueError("多样性路径单模 OOF 下限必须为0.9452")
    if config.get("cv_results_standard_base_fields") != [
        "base",
        "base_oof_auc",
        "oof_delta_vs_base",
    ]:
        raise ValueError("cv_results 统一 base schema 未冻结")
    permission_contract = {
        "mechanism_signal_authorizes_project_strength_advance": False,
        "mechanism_signal_authorizes_fusion": False,
        "project_strength_pass_allowed_for_fusion": True,
        "diversity_only_allowed_for_fusion": False,
        "diversity_only_eligible_for_separate_preregistration": True,
    }
    for key, expected in permission_contract.items():
        if config.get(key) is not expected:
            raise ValueError(f"冻结权限语义错误：{key}")
    if (
        float(config.get("separate_v80_small_fusion_minimum_delta", -1))
        != 0.0001
        or int(config.get("separate_v80_small_fusion_required_meta_fold_wins", -1))
        != 5
        or int(config.get("separate_v80_small_fusion_meta_fold_count", -1)) != 5
    ):
        raise ValueError("后续 v80 小融合门槛必须冻结为+0.0001且元验证5/5")
    return config


def derive_candidate_decision(
    config: dict[str, Any],
    *,
    oof_auc: float,
    delta_vs_v74: float,
    wins_vs_v74: int,
    delta_vs_v80: float,
    wins_vs_v80: int,
) -> dict[str, Any]:
    """分离机制信号、项目强度和仅供后续预注册的多样性资格。"""
    mechanism_signal = bool(
        delta_vs_v74
        >= float(config["mechanism_signal_minimum_oof_delta_vs_v74"])
        and wins_vs_v74
        >= int(config["mechanism_signal_minimum_seed42_bucket_wins_vs_v74"])
    )
    project_strength = bool(
        delta_vs_v80
        >= float(config["project_strength_minimum_oof_delta_vs_v80"])
        and wins_vs_v80
        >= int(config["project_strength_minimum_seed42_bucket_wins_vs_v80"])
    )
    diversity_screen = bool(
        oof_auc >= float(config["minimum_oof_for_diversity_path"])
    )
    if project_strength:
        decision = "ADVANCE_PROJECT_STRENGTH_PATH"
    elif diversity_screen:
        decision = "ELIGIBLE_FOR_SEPARATE_V80_SMALL_FUSION_PREREGISTRATION_ONLY"
    else:
        decision = "STOP"
    return {
        "mechanism_signal": mechanism_signal,
        "project_strength": project_strength,
        "diversity_screen": diversity_screen,
        "decision": decision,
        "allowed_for_fusion": project_strength,
        "eligible_for_separate_preregistration": diversity_screen,
    }


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


def load_probe() -> Any:
    spec = importlib.util.spec_from_file_location("v85_v68_naji_probe", PROBE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 Naji v68 配方：{PROBE_PATH}")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe


def target_encoder_source_sha256() -> str:
    source = inspect.getsource(TargetEncoder.fit_transform).encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def target_encoder_prior_self_check() -> dict[str, Any]:
    """唯一类别应回退到对应 inner-train 均值，不能使用 full-fit prior。"""
    x = np.asarray([[f"unique_{idx}"] for idx in range(23)], dtype=object)
    y = np.asarray([0] * 15 + [1] * 8, dtype=np.int8)
    seed = INNER_TE_SEED_BASE + 1
    folds = list(
        StratifiedKFold(
            n_splits=N_INNER_FOLDS, shuffle=True, random_state=seed
        ).split(x, y)
    )
    expected = np.empty(len(y), dtype=np.float64)
    for inner_train, inner_hold in folds:
        expected[inner_hold] = float(y[inner_train].mean())
    maximum_errors: dict[str, float] = {}
    for tag, smooth in (("auto", "auto"), ("10", 10.0)):
        encoded = TargetEncoder(
            shuffle=True,
            cv=N_INNER_FOLDS,
            smooth=smooth,
            random_state=seed,
        ).fit_transform(x, y)[:, 0]
        maximum_error = float(np.max(np.abs(encoded - expected)))
        if maximum_error != 0.0:
            raise AssertionError(f"TargetEncoder smooth={tag} inner prior 非严格")
        maximum_errors[tag] = maximum_error
    return {
        "status": "INNER_TRAIN_PRIOR_CONFIRMED",
        "sklearn_version": sklearn.__version__,
        "fit_transform_source_sha256": target_encoder_source_sha256(),
        "unique_category_holdout_max_abs_error": maximum_errors,
        "expected_inner_priors": sorted(set(expected.tolist())),
    }


def encode_naji_fold(
    x: pd.DataFrame,
    y: pd.Series,
    x_test: pd.DataFrame,
    target_encode_columns: list[str],
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    fold: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    x_fit = x.iloc[fit_idx].copy()
    x_valid = x.iloc[valid_idx].copy()
    x_test_fold = x_test.copy()
    y_fit = y.iloc[fit_idx]
    for tag, smooth in (("auto", "auto"), ("10", 10.0)):
        encoder = TargetEncoder(
            shuffle=True,
            cv=N_INNER_FOLDS,
            smooth=smooth,
            random_state=INNER_TE_SEED_BASE + fold,
        )
        fit_encoded = encoder.fit_transform(x_fit[target_encode_columns], y_fit)
        valid_encoded = encoder.transform(x_valid[target_encode_columns])
        test_encoded = encoder.transform(x_test_fold[target_encode_columns])
        fit_columns: dict[str, np.ndarray] = {}
        valid_columns: dict[str, np.ndarray] = {}
        test_columns: dict[str, np.ndarray] = {}
        for column_idx, column in enumerate(target_encode_columns):
            name = f"{column}_TE_{tag}"
            fit_columns[name] = fit_encoded[:, column_idx].astype(np.float32)
            valid_columns[name] = valid_encoded[:, column_idx].astype(np.float32)
            test_columns[name] = test_encoded[:, column_idx].astype(np.float32)
        x_fit = pd.concat([x_fit, pd.DataFrame(fit_columns, index=x_fit.index)], axis=1)
        x_valid = pd.concat(
            [x_valid, pd.DataFrame(valid_columns, index=x_valid.index)], axis=1
        )
        x_test_fold = pd.concat(
            [x_test_fold, pd.DataFrame(test_columns, index=x_test_fold.index)], axis=1
        )
    x_fit = x_fit.drop(columns=target_encode_columns)
    x_valid = x_valid.drop(columns=target_encode_columns)
    x_test_fold = x_test_fold.drop(columns=target_encode_columns)
    if list(x_fit.columns) != list(x_valid.columns) or list(x_fit.columns) != list(
        x_test_fold.columns
    ):
        raise ValueError("Naji fold 编码后三个矩阵 schema 不一致")
    for name, frame in (("fit", x_fit), ("valid", x_valid), ("test", x_test_fold)):
        values = frame.to_numpy(np.float64)
        if not np.isfinite(values).all():
            raise ValueError(f"Naji {name} 特征含 NaN/Inf")
    return x_fit, x_valid, x_test_fold


def validate_reference_contract(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    v74 = json.loads((V74_DIR / "cv_results.json").read_text(encoding="utf-8"))
    v80 = json.loads((V80_DIR / "cv_results.json").read_text(encoding="utf-8"))
    if int(v74["seed"]) != OUTER_SEED or int(v74["n_folds"]) != 20:
        raise ValueError("v74 seed/outer folds 参考合同异常")
    if v74["params"] != config["lightgbm_base_params"]:
        raise ValueError("LightGBM 基础参数未保持 v74")
    if v74["extra_income_bins"] != config["extra_income_bins"]:
        raise ValueError("income bins 未保持 v74")
    if int(v74["target_encode_column_count"]) != int(
        config["target_encode_column_count"]
    ):
        raise ValueError("TargetEncoder 列数未保持 v74")
    if int(v74["feature_count"]) != int(config["expected_final_features"]):
        raise ValueError("最终特征数未保持 v74")
    if not np.isclose(
        v74["oof_auc"], config["v74_oof_auc"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("v74 OOF 冻结值不一致")
    if v80.get("status") != "COMPLETE" or not np.isclose(
        v80["oof_auc"], config["v80_strict_oof_auc"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("v80 strict 项目基准合同异常")
    if sklearn.__version__ != config["required_sklearn_version"]:
        raise RuntimeError("当前 sklearn 版本不是冻结的1.7.2")
    if lgb.__version__ != config["required_lightgbm_version"]:
        raise RuntimeError("当前 LightGBM 版本与冻结配置不一致")
    if target_encoder_source_sha256() != config["target_encoder_fit_transform_sha256"]:
        raise RuntimeError("TargetEncoder.fit_transform 源码哈希漂移")
    forbidden_manual_te_import = "v6_multiscale" + "_te"
    for path in (PROBE_PATH, V69_SCRIPT_PATH, V74_SCRIPT_PATH, Path(__file__)):
        if forbidden_manual_te_import in path.read_text(encoding="utf-8"):
            raise ValueError(f"禁止引入 v6 手工TE：{path}")
    return v74, v80


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
        "naji_v68_probe": PROBE_PATH,
        "naji_v69_runner": V69_SCRIPT_PATH,
        "naji_v74_runner": V74_SCRIPT_PATH,
        "train_csv": DATA_DIR / "train.csv",
        "test_csv": DATA_DIR / "test.csv",
        "sample_submission_csv": DATA_DIR / "sample_submission.csv",
        "original_csv": DATA_DIR
        / "original_dataset"
        / "EV_Adoption_and_Range_Anxiety_Dataset.csv",
        "v74_cv_results": V74_DIR / "cv_results.json",
        "v74_oof": V74_DIR / "oof_proba.npy",
        "v74_test": V74_DIR / "test_proba.npy",
        "v80_config": V80_DIR / "frozen_config.json",
        "v80_cv_results": V80_DIR / "cv_results.json",
        "v80_oof": V80_DIR / "oof_proba.npy",
        "v80_test": V80_DIR / "test_proba.npy",
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
            "target_encoder_fit_transform_sha256": target_encoder_source_sha256(),
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


def validate_data_contract(config: dict[str, Any], probe: Any) -> dict[str, Any]:
    raw_train = pd.read_csv(DATA_DIR / "train.csv")
    raw_test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if len(raw_train) != int(config["expected_train_rows"]):
        raise ValueError("train 行数与冻结配置不一致")
    if len(raw_test) != int(config["expected_test_rows"]):
        raise ValueError("test 行数与冻结配置不一致")
    if (
        raw_train[config["id_column"]].isna().any()
        or raw_test[config["id_column"]].isna().any()
        or not raw_train[config["id_column"]].is_unique
        or not raw_test[config["id_column"]].is_unique
    ):
        raise ValueError("train/test id 必须非空且唯一")
    if not sample[config["id_column"]].equals(raw_test[config["id_column"]]):
        raise ValueError("sample_submission 与 test id 行序不一致")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x, y, x_test, target_encode_columns = probe.build_features(
            extra_income_bins=tuple(config["extra_income_bins"])
        )
    if x.shape != (
        int(config["expected_train_rows"]),
        int(config["expected_pre_te_features"]),
    ) or x_test.shape != (
        int(config["expected_test_rows"]),
        int(config["expected_pre_te_features"]),
    ):
        raise ValueError("Naji v74 pre-TE feature shape 漂移")
    if len(target_encode_columns) != int(config["target_encode_column_count"]):
        raise ValueError("Naji v74 TargetEncoder 列数漂移")
    column_sha = hashlib.sha256("\n".join(x.columns).encode("utf-8")).hexdigest()
    target_column_sha = hashlib.sha256(
        "\n".join(target_encode_columns).encode("utf-8")
    ).hexdigest()
    if column_sha != config["pre_te_column_order_sha256"]:
        raise ValueError("Naji v74 pre-TE 列序哈希漂移")
    if target_column_sha != config["target_encode_column_order_sha256"]:
        raise ValueError("Naji v74 TargetEncoder 列序哈希漂移")
    if not np.array_equal(
        y.to_numpy(np.int8),
        raw_train[config["target"]]
        .eq(config["positive_label"])
        .to_numpy(np.int8),
    ):
        raise ValueError("Naji target 与 raw train 行序不一致")
    final_feature_names = [
        column for column in x.columns if column not in target_encode_columns
    ] + [
        f"{column}_TE_{tag}"
        for tag in ("auto", "10")
        for column in target_encode_columns
    ]
    if len(final_feature_names) != int(config["expected_final_features"]):
        raise ValueError("Naji v74 最终特征数漂移")

    v74_results, v80_results = validate_reference_contract(config)
    v74_oof = np.load(V74_DIR / "oof_proba.npy", mmap_mode="r")
    v74_test = np.load(V74_DIR / "test_proba.npy", mmap_mode="r")
    v80_oof = np.load(V80_DIR / "oof_proba.npy", mmap_mode="r")
    v80_test = np.load(V80_DIR / "test_proba.npy", mmap_mode="r")
    for name, values, expected in (
        ("v74_oof", v74_oof, len(raw_train)),
        ("v74_test", v74_test, len(raw_test)),
        ("v80_oof", v80_oof, len(raw_train)),
        ("v80_test", v80_test, len(raw_test)),
    ):
        validate_probability_array(name, values, expected)
    for name, values, results in (
        ("v74", v74_oof, v74_results),
        ("v80", v80_oof, v80_results),
    ):
        auc = float(roc_auc_score(y, values))
        if not np.isclose(auc, results["oof_auc"], atol=1e-12, rtol=0.0):
            raise ValueError(f"{name} OOF 与 cv_results 不一致")
    return {
        "raw_train": raw_train,
        "raw_test": raw_test,
        "sample": sample,
        "x": x,
        "y": y,
        "x_test": x_test,
        "target_encode_columns": target_encode_columns,
        "final_feature_names": final_feature_names,
        "v74_oof": v74_oof,
        "v74_test": v74_test,
        "v74_results": v74_results,
        "v80_oof": v80_oof,
        "v80_test": v80_test,
        "v80_results": v80_results,
    }


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
            raise RuntimeError(f"已有 v85 实例持有 flock：{owner}") from error
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
    probe = load_probe()
    validate_reference_contract(config)
    prior_audit = target_encoder_prior_self_check()
    run_contract = build_run_contract()
    data = validate_data_contract(config, probe)
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
                "status": "AUDIT_OK_NO_LIGHTGBM_TRAINING",
                "experiment_id": EXPERIMENT_ID,
                "train_rows": len(data["raw_train"]),
                "test_rows": len(data["raw_test"]),
                "outer_split_seed": OUTER_SEED,
                "outer_folds": N_FOLDS,
                "target_encoder_seed_base": INNER_TE_SEED_BASE,
                "model_seed_base": MODEL_SEED_BASE,
                "runtime_lightgbm_version": lgb.__version__,
                "runtime_sklearn_version": sklearn.__version__,
                "target_encoder_prior_audit": prior_audit,
                "pre_te_features": data["x"].shape[1],
                "target_encode_columns": len(data["target_encode_columns"]),
                "final_features": len(data["final_feature_names"]),
                "base": config["base"],
                "base_oof_auc": config["base_oof_auc"],
                "cv_results_required_aliases": config[
                    "cv_results_standard_base_fields"
                ],
                "v74_mechanism_reference_oof": data["v74_results"]["oof_auc"],
                "v80_strict_project_baseline_oof": data["v80_results"]["oof_auc"],
                "decision_contract": {
                    "v74_role": "mechanism_signal_only",
                    "v74_minimum_delta": config[
                        "mechanism_signal_minimum_oof_delta_vs_v74"
                    ],
                    "v74_minimum_bucket_wins": config[
                        "mechanism_signal_minimum_seed42_bucket_wins_vs_v74"
                    ],
                    "v80_role": "project_single_model_strength_gate",
                    "v80_minimum_delta": config[
                        "project_strength_minimum_oof_delta_vs_v80"
                    ],
                    "v80_minimum_bucket_wins": config[
                        "project_strength_minimum_seed42_bucket_wins_vs_v80"
                    ],
                    "diversity_only_allowed_for_fusion": config[
                        "diversity_only_allowed_for_fusion"
                    ],
                    "diversity_only_eligible_for_separate_preregistration": config[
                        "diversity_only_eligible_for_separate_preregistration"
                    ],
                },
                "manual_v6_te_imported": False,
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
    probe = load_probe()
    validate_reference_contract(config)
    prior_audit = target_encoder_prior_self_check()
    run_contract = build_run_contract()
    data = validate_data_contract(config, probe)
    train_idx = np.linspace(0, len(data["x"]) - 1, 5000, dtype=np.int64)
    test_idx = np.linspace(0, len(data["x_test"]) - 1, 2000, dtype=np.int64)
    smoke_x = data["x"].iloc[train_idx].reset_index(drop=True)
    smoke_y = data["y"].iloc[train_idx].reset_index(drop=True)
    smoke_test = data["x_test"].iloc[test_idx].reset_index(drop=True)
    fit_idx, valid_idx = next(
        StratifiedKFold(n_splits=2, shuffle=True, random_state=OUTER_SEED).split(
            smoke_x, smoke_y
        )
    )
    x_fit, x_valid, x_test_fold = encode_naji_fold(
        smoke_x,
        smoke_y,
        smoke_test,
        data["target_encode_columns"],
        fit_idx,
        valid_idx,
        fold=1,
    )
    if {x_fit.shape[1], x_valid.shape[1], x_test_fold.shape[1]} != {
        int(config["expected_final_features"])
    }:
        raise ValueError("smoke 特征宽度不是冻结的148")
    if list(x_fit.columns) != data["final_feature_names"]:
        raise ValueError("smoke 最终特征列序与冻结配方不一致")

    mechanism_only = derive_candidate_decision(
        config,
        oof_auc=float(config["v74_oof_auc"]) + 0.00004,
        delta_vs_v74=0.00004,
        wins_vs_v74=24,
        delta_vs_v80=0.00002,
        wins_vs_v80=23,
    )
    if (
        mechanism_only["mechanism_signal"] is not True
        or mechanism_only["project_strength"] is not False
        or mechanism_only["allowed_for_fusion"] is not False
        or mechanism_only["eligible_for_separate_preregistration"] is not True
        or mechanism_only["decision"]
        != "ELIGIBLE_FOR_SEPARATE_V80_SMALL_FUSION_PREREGISTRATION_ONLY"
    ):
        raise AssertionError("v74 mechanism signal 被错误当作项目强度或融合许可")
    project_strength = derive_candidate_decision(
        config,
        oof_auc=float(config["v80_strict_oof_auc"]) + 0.00011,
        delta_vs_v74=0.00012,
        wins_vs_v74=24,
        delta_vs_v80=0.00011,
        wins_vs_v80=24,
    )
    if (
        project_strength["project_strength"] is not True
        or project_strength["allowed_for_fusion"] is not True
        or project_strength["decision"] != "ADVANCE_PROJECT_STRENGTH_PATH"
    ):
        raise AssertionError("相对 v80 的项目单模强度门槛未生效")
    stop_case = derive_candidate_decision(
        config,
        oof_auc=0.94,
        delta_vs_v74=-0.006,
        wins_vs_v74=0,
        delta_vs_v80=-0.006,
        wins_vs_v80=0,
    )
    if (
        stop_case["decision"] != "STOP"
        or stop_case["allowed_for_fusion"] is not False
        or stop_case["eligible_for_separate_preregistration"] is not False
    ):
        raise AssertionError("低于多样性下限的 STOP 语义未生效")

    fake_valid = np.linspace(0.1, 0.9, len(valid_idx), dtype=np.float64)
    fake_test = np.full(len(smoke_test), 0.5, dtype=np.float64)
    fake_importance = np.zeros(x_fit.shape[1], dtype=np.float64)
    lock_rejection_ok = False
    if classify_resource_breach(config, 3000.0, 0) != ["WALL_CLOCK_BUDGET"]:
        raise AssertionError("50分钟墙钟硬门槛未生效")
    if classify_resource_breach(
        config, 0.0, int(config["peak_rss_budget_bytes"]) + 1
    ) != ["PEAK_RSS_BUDGET"]:
        raise AssertionError("12 GiB peak RSS硬门槛未生效")
    with tempfile.TemporaryDirectory(prefix="v85_smoke_") as temporary_dir:
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
            feature_count=x_fit.shape[1],
            config_sha256=run_contract["frozen_config_sha256"],
            run_contract_sha256=run_contract["run_contract_sha256"],
        )
        try:
            load_checkpoint(
                checkpoint,
                fold=1,
                valid_idx=valid_idx,
                test_rows=len(smoke_test),
                feature_count=x_fit.shape[1],
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
                "wall_elapsed_seconds": 3000.0,
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
            or failed_evidence.get("base") != config["base"]
            or failed_evidence.get("base_oof_auc") != config["base_oof_auc"]
            or "oof_delta_vs_base" not in failed_evidence
            or failed_evidence.get("allowed_for_fusion") is not False
            or failed_evidence.get("eligible_for_separate_preregistration") is not False
            or not fold_40_checkpoint.is_file()
            or (temporary_root / "cv_results.json.tmp").exists()
        ):
            raise AssertionError("资源超限 FAILED 原子证据 smoke 未通过")

    print(
        json.dumps(
            {
                "status": "SMOKE_OK_NO_LIGHTGBM_FIT_NO_METRIC_EVIDENCE",
                "target_encoder_prior_audit": prior_audit,
                "subset_train_rows": len(smoke_x),
                "subset_test_rows": len(smoke_test),
                "pre_te_features": smoke_x.shape[1],
                "target_encode_columns": len(data["target_encode_columns"]),
                "total_features": x_fit.shape[1],
                "manual_v6_te_imported": False,
                "checkpoint_roundtrip": True,
                "mismatched_contract_rejected": True,
                "concurrent_lock_rejected": lock_rejection_ok,
                "runtime_version_contract_verified": True,
                "wall_clock_limit_rejected": True,
                "peak_rss_limit_rejected": True,
                "atomic_failed_evidence_roundtrip": True,
                "fold_40_checkpoint_preserved_on_failure": True,
                "mechanism_signal_not_strength_advance": True,
                "v80_project_strength_gate_verified": True,
                "diversity_only_fusion_permission_false": True,
                "diversity_only_separate_preregistration_true": True,
                "cv_results_base_alias_schema_verified": True,
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
    fold_v74_scores: list[float],
    fold_v80_scores: list[float],
    oof: np.ndarray,
    coverage: np.ndarray,
    y: np.ndarray,
    v74_oof: np.ndarray,
    v80_oof: np.ndarray,
    latest_resource_check: dict[str, Any],
    trained_this_run: int,
    resumed_this_run: int,
) -> None:
    covered = coverage == 1
    partial_auc = float(roc_auc_score(y[covered], oof[covered]))
    v74_auc = float(roc_auc_score(y[covered], v74_oof[covered]))
    v80_auc = float(roc_auc_score(y[covered], v80_oof[covered]))
    v74_wins = int(
        sum(candidate > base for candidate, base in zip(fold_scores, fold_v74_scores))
    )
    v80_wins = int(
        sum(candidate > base for candidate, base in zip(fold_scores, fold_v80_scores))
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
        "v74_auc_same_rows": v74_auc,
        "partial_delta_vs_v74": partial_auc - v74_auc,
        "v74_seed42_bucket_wins": v74_wins,
        "v80_strict_auc_same_rows": v80_auc,
        "partial_delta_vs_v80_strict": partial_auc - v80_auc,
        "v80_project_strength_seed42_bucket_wins": v80_wins,
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
        f"folds={completed}/{N_FOLDS} partial_oof={partial_auc:.9f} "
        f"v74_same_rows={v74_auc:.9f} delta={partial_auc-v74_auc:+.9f} "
        f"wins_v74={v74_wins}/{completed} v80={v80_auc:.9f} "
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
        "WALL_CLOCK_BUDGET": "50分钟墙钟预算已达到或超过门槛",
        "PEAK_RSS_BUDGET": "进程 peak RSS 已超过12 GiB硬门槛",
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
            "params": config["lightgbm_base_params"],
            "base": config["base"],
            "base_oof_auc": config["base_oof_auc"],
            "oof_delta_vs_base": None,
            "strict_project_baseline": config["strict_project_baseline"],
            "strict_project_baseline_oof_auc": config["v80_strict_oof_auc"],
            "oof_delta_vs_v80_strict": None,
            "frozen_config_sha256": config_sha256,
            "run_contract_sha256": run_contract_sha256,
            "allowed_for_fusion": False,
            "eligible_for_separate_preregistration": False,
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
    probe = load_probe()
    validate_reference_contract(config)
    prior_audit = target_encoder_prior_self_check()
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
        data = validate_data_contract(config, probe)
        train_frame = data["raw_train"]
        test_frame = data["raw_test"]
        sample = data["sample"]
        x_train = data["x"]
        y = data["y"]
        x_test = data["x_test"]
        target_encode_columns = data["target_encode_columns"]
        all_features = data["final_feature_names"]
        logger.emit(
            f"data train={train_frame.shape} test={test_frame.shape} "
            f"pre_te={x_train.shape[1]} te_cols={len(target_encode_columns)} "
            f"total={len(all_features)}"
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
        fold_v74_scores: list[float] = []
        fold_v80_scores: list[float] = []
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
                fold_auc = float(roc_auc_score(y.iloc[valid_idx], valid_pred))
                if not np.isclose(fold_auc, saved["fold_auc"], atol=1e-12, rtol=0.0):
                    raise ValueError(f"fold={fold} checkpoint AUC 复算不一致")
                resumed_this_run += 1
                logger.emit(f"fold={fold}/{N_FOLDS} resumed strict_auc={fold_auc:.9f}")
            else:
                fold_started = time.monotonic()
                x_fit, x_valid, x_tst = encode_naji_fold(
                    x_train,
                    y,
                    x_test,
                    target_encode_columns,
                    fit_idx,
                    valid_idx,
                    fold,
                )
                fold_params = dict(config["lightgbm_base_params"])
                for seed_name in config["lightgbm_fold_seed_fields"]:
                    fold_params[seed_name] = MODEL_SEED_BASE + fold
                model = lgb.LGBMClassifier(**fold_params)
                model.fit(
                    x_fit,
                    y.iloc[fit_idx],
                    eval_set=[(x_valid, y.iloc[valid_idx])],
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
                    model.best_iteration_
                    or config["lightgbm_base_params"]["n_estimators"]
                )
                valid_pred = model.predict_proba(
                    x_valid, num_iteration=best_iteration
                )[:, 1]
                fold_test = model.predict_proba(x_tst, num_iteration=best_iteration)[:, 1]
                fold_auc = float(roc_auc_score(y.iloc[valid_idx], valid_pred))
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
                del model, x_fit, x_valid, x_tst
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
            v74_auc = float(roc_auc_score(y.iloc[valid_idx], data["v74_oof"][valid_idx]))
            v80_auc = float(roc_auc_score(y.iloc[valid_idx], data["v80_oof"][valid_idx]))
            fold_scores.append(fold_auc)
            fold_v74_scores.append(v74_auc)
            fold_v80_scores.append(v80_auc)
            best_iterations.append(best_iteration)
            fold_rows.append(
                {
                    "fold": fold,
                    "target_encoder_seed": INNER_TE_SEED_BASE + fold,
                    "model_seed": MODEL_SEED_BASE + fold,
                    "valid_idx_sha256": hashlib.sha256(valid_idx.tobytes()).hexdigest(),
                    "candidate_auc": fold_auc,
                    "v74_auc_same_seed42_bucket": v74_auc,
                    "delta_vs_v74_bucket": fold_auc - v74_auc,
                    "v80_strict_auc_same_seed42_bucket": v80_auc,
                    "delta_vs_v80_project_strength_bucket": fold_auc - v80_auc,
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
                    fold_v74_scores=fold_v74_scores,
                    fold_v80_scores=fold_v80_scores,
                    oof=oof,
                    coverage=coverage,
                    y=y,
                    v74_oof=data["v74_oof"],
                    v80_oof=data["v80_oof"],
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
        v74_auc = float(data["v74_results"]["oof_auc"])
        v80_auc = float(data["v80_results"]["oof_auc"])
        delta_v74 = oof_auc - v74_auc
        delta_v80 = oof_auc - v80_auc
        wins_v74 = int(
            sum(candidate > base for candidate, base in zip(fold_scores, fold_v74_scores))
        )
        wins_v80 = int(
            sum(candidate > base for candidate, base in zip(fold_scores, fold_v80_scores))
        )
        oof_spearman_v74 = float(spearmanr(oof, data["v74_oof"]).statistic)
        test_spearman_v74 = float(
            spearmanr(test_prediction, data["v74_test"]).statistic
        )
        oof_spearman_v80 = float(spearmanr(oof, data["v80_oof"]).statistic)
        test_spearman_v80 = float(
            spearmanr(test_prediction, data["v80_test"]).statistic
        )
        if not all(
            np.isfinite(value)
            for value in (
                oof_spearman_v74,
                test_spearman_v74,
                oof_spearman_v80,
                test_spearman_v80,
            )
        ):
            raise ValueError("与 v74/v80 的 Spearman 非有限值")

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
        if (
            submission.shape != sample.shape
            or list(submission.columns) != [config["id_column"], config["target"]]
            or not submission[config["id_column"]].equals(test_frame[config["id_column"]])
        ):
            raise ValueError("submission schema/id 不一致")
        validate_probability_array(
            "submission", submission[config["target"]].to_numpy(), len(test_frame)
        )

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
        candidate_decision = derive_candidate_decision(
            config,
            oof_auc=oof_auc,
            delta_vs_v74=delta_v74,
            wins_vs_v74=wins_v74,
            delta_vs_v80=delta_v80,
            wins_vs_v80=wins_v80,
        )
        results = {
            "schema_version": 1,
            "status": "COMPLETE",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": True,
            "competition": config["competition"],
            "model": "Naji v74 recipe with 40 outer folds",
            "hypothesis": (
                "raising Naji v74 outer-fit coverage from 95% to 97.5% improves its "
                "honest OOF while preserving the independent sklearn TargetEncoder recipe"
            ),
            "unique_primary_variable": "outer folds: 20 -> 40",
            "base": config["base"],
            "base_oof_auc": v74_auc,
            "mechanism_reference": config["mechanism_reference"],
            "mechanism_reference_oof_auc": v74_auc,
            "strict_project_baseline": config["strict_project_baseline"],
            "strict_project_baseline_oof_auc": v80_auc,
            "n_folds": N_FOLDS,
            "outer_split_seed": OUTER_SEED,
            "target_encoder_cv": N_INNER_FOLDS,
            "target_encoder_seed_base": INNER_TE_SEED_BASE,
            "target_encoder_seeds": [INNER_TE_SEED_BASE + fold for fold in range(1, 41)],
            "model_seed_base": MODEL_SEED_BASE,
            "model_seeds": [MODEL_SEED_BASE + fold for fold in range(1, 41)],
            "target_encoder_contract": config["target_encoder_contract"],
            "target_encoder_prior_audit": prior_audit,
            "params": config["lightgbm_base_params"],
            "lightgbm_fold_seed_fields": config["lightgbm_fold_seed_fields"],
            "extra_income_bins": config["extra_income_bins"],
            "pre_te_feature_count": int(x_train.shape[1]),
            "target_encode_column_count": len(target_encode_columns),
            "feature_count": len(all_features),
            "fold_auc": fold_scores,
            "fold_auc_mean": float(np.mean(fold_scores)),
            "fold_auc_std": float(np.std(fold_scores)),
            "best_iterations": best_iterations,
            "fold_diagnostics": fold_rows,
            "seed42_bucket_wins_vs_v74": wins_v74,
            "seed42_bucket_wins_vs_v80_project_strength": wins_v80,
            "oof_auc": oof_auc,
            "oof_delta_vs_base": delta_v74,
            "oof_delta_vs_v74": delta_v74,
            "oof_spearman_vs_v74": oof_spearman_v74,
            "test_spearman_vs_v74": test_spearman_v74,
            "oof_delta_vs_v80_strict": delta_v80,
            "oof_spearman_vs_v80_strict": oof_spearman_v80,
            "test_spearman_vs_v80_strict": test_spearman_v80,
            "comparison_boundary": (
                "v74 and v85 are full honest OOF predictions; fold wins are scored on a "
                "fixed seed42 40-bucket partition. v74 only decides mechanism signal; v80 "
                "decides project single-model strength. Any blend requires a separate "
                "preregistration"
            ),
            "mechanism_signal": {
                "role": "MECHANISM_SIGNAL_ONLY_NOT_PROJECT_ADVANCE",
                "minimum_oof_delta_vs_v74": config[
                    "mechanism_signal_minimum_oof_delta_vs_v74"
                ],
                "minimum_seed42_bucket_wins_vs_v74": config[
                    "mechanism_signal_minimum_seed42_bucket_wins_vs_v74"
                ],
                "observed_oof_delta_vs_v74": delta_v74,
                "observed_seed42_bucket_wins_vs_v74": wins_v74,
                "passes": candidate_decision["mechanism_signal"],
                "authorizes_project_strength_advance": config[
                    "mechanism_signal_authorizes_project_strength_advance"
                ],
                "authorizes_fusion": config[
                    "mechanism_signal_authorizes_fusion"
                ],
            },
            "project_strength_gate": {
                "base": config["strict_project_baseline"],
                "base_oof_auc": v80_auc,
                "minimum_oof_delta_vs_v80": config[
                    "project_strength_minimum_oof_delta_vs_v80"
                ],
                "minimum_seed42_bucket_wins_vs_v80": config[
                    "project_strength_minimum_seed42_bucket_wins_vs_v80"
                ],
                "observed_oof_delta_vs_v80": delta_v80,
                "observed_seed42_bucket_wins_vs_v80": wins_v80,
                "passes": candidate_decision["project_strength"],
            },
            "diversity_path_screen": {
                "minimum_oof_auc": config["minimum_oof_for_diversity_path"],
                "observed_oof_auc": oof_auc,
                "passes": candidate_decision["diversity_screen"],
                "next_test": "separately preregistered strict small fusion with v80",
                "future_minimum_delta_vs_best_input": config[
                    "separate_v80_small_fusion_minimum_delta"
                ],
                "future_required_meta_fold_wins": config[
                    "separate_v80_small_fusion_required_meta_fold_wins"
                ],
                "future_meta_fold_count": config[
                    "separate_v80_small_fusion_meta_fold_count"
                ],
                "fusion_test_performed_here": False,
            },
            "decision": candidate_decision["decision"],
            "allowed_for_fusion": candidate_decision["allowed_for_fusion"],
            "eligible_for_separate_preregistration": candidate_decision[
                "eligible_for_separate_preregistration"
            ],
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
                "target_encoder_inner_prior_self_check": True,
                "manual_v6_te_imported": False,
                "checkpoint_reconstruction_required": True,
            },
            "runtime": run_contract["runtime"],
        }
        atomic_write_json(results_path, results)
        verify_complete()
        logger.emit(
            f"complete oof={oof_auc:.9f} delta_vs_v74={delta_v74:+.9f} "
            f"wins_v74={wins_v74}/40 mechanism_signal="
            f"{candidate_decision['mechanism_signal']} delta_vs_v80={delta_v80:+.9f} "
            f"wins_v80={wins_v80}/40 project_strength="
            f"{candidate_decision['project_strength']}"
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
    probe = load_probe()
    validate_reference_contract(config)
    prior_audit = target_encoder_prior_self_check()
    data = validate_data_contract(config, probe)
    train = data["raw_train"]
    test = data["raw_test"]
    sample = data["sample"]
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
        "target_encoder_seeds": N_FOLDS,
        "model_seeds": N_FOLDS,
    }
    for key, expected in expected_lengths.items():
        if len(results.get(key, [])) != expected:
            raise ValueError(f"cv_results {key} 长度不是 {expected}")
    if (
        results["outer_split_seed"] != OUTER_SEED
        or results["target_encoder_seed_base"] != INNER_TE_SEED_BASE
        or results["model_seed_base"] != MODEL_SEED_BASE
        or results["target_encoder_contract"] != config["target_encoder_contract"]
        or results["target_encoder_prior_audit"] != prior_audit
    ):
        raise ValueError("cv_results 随机源或 TargetEncoder 合同不一致")
    expected_metadata = {
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "unique_primary_variable": "outer folds: 20 -> 40",
        "base": config["base"],
        "base_oof_auc": config["base_oof_auc"],
        "mechanism_reference": config["mechanism_reference"],
        "mechanism_reference_oof_auc": config["v74_oof_auc"],
        "strict_project_baseline": config["strict_project_baseline"],
        "strict_project_baseline_oof_auc": config["v80_strict_oof_auc"],
        "n_folds": N_FOLDS,
        "target_encoder_cv": N_INNER_FOLDS,
        "params": config["lightgbm_base_params"],
        "lightgbm_fold_seed_fields": config["lightgbm_fold_seed_fields"],
        "extra_income_bins": config["extra_income_bins"],
        "pre_te_feature_count": config["expected_pre_te_features"],
        "target_encode_column_count": config["target_encode_column_count"],
        "feature_count": config["expected_final_features"],
        "counts_toward_cycle": True,
    }
    for key, expected in expected_metadata.items():
        if results.get(key) != expected:
            raise ValueError(f"cv_results {key} 未保持冻结合同")
    if results["target_encoder_seeds"] != [
        INNER_TE_SEED_BASE + fold for fold in range(1, N_FOLDS + 1)
    ]:
        raise ValueError("cv_results TargetEncoder seeds 未保持冻结序列")
    if results["model_seeds"] != [
        MODEL_SEED_BASE + fold for fold in range(1, N_FOLDS + 1)
    ]:
        raise ValueError("cv_results LightGBM seeds 未保持冻结序列")

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
        v74_fold_auc = float(roc_auc_score(y[valid_idx], data["v74_oof"][valid_idx]))
        v80_fold_auc = float(roc_auc_score(y[valid_idx], data["v80_oof"][valid_idx]))
        if (
            int(diagnostic["fold"]) != fold
            or int(diagnostic["target_encoder_seed"]) != INNER_TE_SEED_BASE + fold
            or int(diagnostic["model_seed"]) != MODEL_SEED_BASE + fold
            or int(diagnostic["best_iteration"]) != checkpoint["best_iteration"]
            or not np.isclose(
                diagnostic["candidate_auc"], fold_auc, atol=1e-12, rtol=0.0
            )
            or not np.isclose(
                diagnostic["v74_auc_same_seed42_bucket"],
                v74_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
            or not np.isclose(
                diagnostic["v80_strict_auc_same_seed42_bucket"],
                v80_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
            or not np.isclose(
                diagnostic["delta_vs_v74_bucket"],
                fold_auc - v74_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
            or not np.isclose(
                diagnostic["delta_vs_v80_project_strength_bucket"],
                fold_auc - v80_fold_auc,
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
    v74_auc = float(data["v74_results"]["oof_auc"])
    v80_auc = float(data["v80_results"]["oof_auc"])
    delta_v74 = recomputed_oof_auc - v74_auc
    delta_v80 = recomputed_oof_auc - v80_auc
    for key, expected in (
        ("oof_delta_vs_base", delta_v74),
        ("oof_delta_vs_v74", delta_v74),
        ("oof_delta_vs_v80_strict", delta_v80),
    ):
        if not np.isclose(results[key], expected, atol=1e-12, rtol=0.0):
            raise ValueError(f"{key} 复算不一致")
    spearman_checks = {
        "oof_spearman_vs_v74": float(spearmanr(rebuilt_oof, data["v74_oof"]).statistic),
        "test_spearman_vs_v74": float(
            spearmanr(rebuilt_test, data["v74_test"]).statistic
        ),
        "oof_spearman_vs_v80_strict": float(
            spearmanr(rebuilt_oof, data["v80_oof"]).statistic
        ),
        "test_spearman_vs_v80_strict": float(
            spearmanr(rebuilt_test, data["v80_test"]).statistic
        ),
    }
    for key, expected in spearman_checks.items():
        if not np.isclose(results[key], expected, atol=1e-12, rtol=0.0):
            raise ValueError(f"{key} 复算不一致")

    v74_bucket_scores = [
        float(roc_auc_score(y[valid_idx], data["v74_oof"][valid_idx]))
        for _, valid_idx in folds
    ]
    v80_bucket_scores = [
        float(roc_auc_score(y[valid_idx], data["v80_oof"][valid_idx]))
        for _, valid_idx in folds
    ]
    wins_v74 = int(
        sum(candidate > base for candidate, base in zip(rebuilt_fold_auc, v74_bucket_scores))
    )
    wins_v80 = int(
        sum(candidate > base for candidate, base in zip(rebuilt_fold_auc, v80_bucket_scores))
    )
    if int(results["seed42_bucket_wins_vs_v74"]) != wins_v74:
        raise ValueError("seed42 bucket wins vs v74 复算不一致")
    if int(results["seed42_bucket_wins_vs_v80_project_strength"]) != wins_v80:
        raise ValueError("seed42 bucket wins vs v80 复算不一致")
    expected_decision_contract = derive_candidate_decision(
        config,
        oof_auc=recomputed_oof_auc,
        delta_vs_v74=delta_v74,
        wins_vs_v74=wins_v74,
        delta_vs_v80=delta_v80,
        wins_vs_v80=wins_v80,
    )
    mechanism_signal = results["mechanism_signal"]
    expected_mechanism_payload = {
        "role": "MECHANISM_SIGNAL_ONLY_NOT_PROJECT_ADVANCE",
        "minimum_oof_delta_vs_v74": config[
            "mechanism_signal_minimum_oof_delta_vs_v74"
        ],
        "minimum_seed42_bucket_wins_vs_v74": config[
            "mechanism_signal_minimum_seed42_bucket_wins_vs_v74"
        ],
        "observed_oof_delta_vs_v74": delta_v74,
        "observed_seed42_bucket_wins_vs_v74": wins_v74,
        "passes": expected_decision_contract["mechanism_signal"],
        "authorizes_project_strength_advance": config[
            "mechanism_signal_authorizes_project_strength_advance"
        ],
        "authorizes_fusion": config["mechanism_signal_authorizes_fusion"],
    }
    for key, expected in expected_mechanism_payload.items():
        actual = mechanism_signal.get(key)
        if isinstance(expected, float):
            if not np.isclose(actual, expected, atol=1e-12, rtol=0.0):
                raise ValueError(f"mechanism_signal {key} 复算不一致")
        elif actual != expected:
            raise ValueError(f"mechanism_signal {key} 复算不一致")
    expected_strength_payload = {
        "base": config["strict_project_baseline"],
        "base_oof_auc": v80_auc,
        "minimum_oof_delta_vs_v80": config[
            "project_strength_minimum_oof_delta_vs_v80"
        ],
        "minimum_seed42_bucket_wins_vs_v80": config[
            "project_strength_minimum_seed42_bucket_wins_vs_v80"
        ],
        "observed_oof_delta_vs_v80": delta_v80,
        "observed_seed42_bucket_wins_vs_v80": wins_v80,
        "passes": expected_decision_contract["project_strength"],
    }
    strength_payload = results["project_strength_gate"]
    for key, expected in expected_strength_payload.items():
        actual = strength_payload.get(key)
        if isinstance(expected, float):
            if not np.isclose(actual, expected, atol=1e-12, rtol=0.0):
                raise ValueError(f"project_strength_gate {key} 复算不一致")
        elif actual != expected:
            raise ValueError(f"project_strength_gate {key} 复算不一致")
    expected_diversity_payload = {
        "minimum_oof_auc": config["minimum_oof_for_diversity_path"],
        "observed_oof_auc": recomputed_oof_auc,
        "passes": expected_decision_contract["diversity_screen"],
        "next_test": "separately preregistered strict small fusion with v80",
        "future_minimum_delta_vs_best_input": config[
            "separate_v80_small_fusion_minimum_delta"
        ],
        "future_required_meta_fold_wins": config[
            "separate_v80_small_fusion_required_meta_fold_wins"
        ],
        "future_meta_fold_count": config[
            "separate_v80_small_fusion_meta_fold_count"
        ],
        "fusion_test_performed_here": False,
    }
    diversity_payload = results["diversity_path_screen"]
    for key, expected in expected_diversity_payload.items():
        actual = diversity_payload.get(key)
        if isinstance(expected, float):
            if not np.isclose(actual, expected, atol=1e-12, rtol=0.0):
                raise ValueError(f"diversity_path_screen {key} 复算不一致")
        elif actual != expected:
            raise ValueError(f"diversity_path_screen {key} 复算不一致")
    if results["decision"] != expected_decision_contract["decision"]:
        raise ValueError("decision 未由重建 OOF 正确推导")
    if bool(results["allowed_for_fusion"]) != bool(
        expected_decision_contract["allowed_for_fusion"]
    ):
        raise ValueError("allowed_for_fusion 未由 v80 项目强度正确推导")
    if bool(results["eligible_for_separate_preregistration"]) != bool(
        expected_decision_contract["eligible_for_separate_preregistration"]
    ):
        raise ValueError("eligible_for_separate_preregistration 复算不一致")
    if results["allowed_for_submission"] is not False:
        raise ValueError("allowed_for_submission 必须保持 false，提交预算为0")

    submission = pd.read_csv(paths["submission"])
    if (
        submission.shape != sample.shape
        or list(submission.columns) != [config["id_column"], config["target"]]
        or not submission[config["id_column"]].equals(test[config["id_column"]])
    ):
        raise ValueError("submission schema/id 不一致")
    validate_probability_array(
        "submission", submission[config["target"]].to_numpy(), len(test)
    )
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
                "target_encoder_inner_prior_self_check": True,
                "manual_v6_te_imported": False,
                "oof_delta_vs_v74": delta_v74,
                "oof_delta_vs_base": delta_v74,
                "seed42_bucket_wins_vs_v74": wins_v74,
                "oof_delta_vs_v80_strict": delta_v80,
                "seed42_bucket_wins_vs_v80_project_strength": wins_v80,
                "mechanism_signal": expected_decision_contract[
                    "mechanism_signal"
                ],
                "project_strength": expected_decision_contract[
                    "project_strength"
                ],
                "allowed_for_fusion": expected_decision_contract[
                    "allowed_for_fusion"
                ],
                "eligible_for_separate_preregistration": expected_decision_contract[
                    "eligible_for_separate_preregistration"
                ],
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
