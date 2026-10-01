#!/usr/bin/env python3
"""v83: strict three-split raw-probability equal bag.

The default mode is static audit. Real member outputs are read only after an
explicit ``--mode run`` or ``--mode verify`` request.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import resource
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold


EXPERIMENT_ID = "v83_strict_three_split_equal_bag"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
PREFLIGHT_PATH = OUT_DIR / "preflight_r1.json"
LOCK_PATH = OUT_DIR / "run.lock"

EXPECTED_MEMBER_IDS = (
    "v80_strict_v61_outer104395303_40f",
    "v81_strict_v61_split7_40f",
    "v82_strict_v61_split2026_40f",
)
FORBIDDEN_MEMBER_IDS = {
    "v61_income_bin10_te_lgbm_40f_depth4_seed104395303",
    "v64_robust_40f_generator_ensemble",
    "v72_naji_income_bin10_robust_ensemble",
}
FORMAL_FILENAMES = (
    "candidate_snapshot.json",
    "lineage.json",
    "sources.json",
    "oof_proba.npy",
    "test_proba.npy",
    "submission.csv",
    "cv_results.json",
    "train_log.txt",
)


class ResourceBudgetExceeded(RuntimeError):
    """Raised before a formal COMPLETE commit when a frozen budget is exceeded."""


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_ids(values: pd.Series) -> str:
    digest = hashlib.sha256()
    for value in values.astype(str):
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="little", signed=False))
        digest.update(encoded)
    return digest.hexdigest()


def relative_path(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_DIR.resolve()))


def file_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        "path": relative_path(path),
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
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_bytes(path, encoded)


def write_immutable_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValueError(f"不可变 JSON 已存在且内容不同：{path.name}")
        return
    atomic_write_json(path, payload)


def write_immutable_text(path: Path, payload: str) -> None:
    encoded = payload.encode("utf-8")
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError(f"不可变文本已存在且内容不同：{path.name}")
        return
    _atomic_bytes(path, encoded)


def atomic_save_npy(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    encoded = frame.to_csv(index=False).encode("utf-8")
    _atomic_bytes(path, encoded)


def load_frozen_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    validate_static_config(config)
    return config


def validate_static_config(config: dict[str, Any]) -> None:
    required_scalars = {
        "schema_version": 1,
        "status": "DESIGN_READY_NOT_STARTED",
        "preflight_revision": "R1",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": "C01",
        "cycle_position": 4,
        "experiment_type": "SMALL_BLEND",
        "counts_toward_cycle_when_formally_closed": True,
        "competition": "playground-series-s6e9",
        "canonical_base": EXPECTED_MEMBER_IDS[0],
        "target": "Will_Buy_EV",
        "positive_label": "Yes",
        "id_column": "id",
        "expected_train_rows": 668665,
        "expected_test_rows": 286571,
        "time_budget_seconds": 900,
        "cpu_threads": 1,
        "memory_budget_gib": 4,
        "submission_budget": 0,
    }
    for key, expected in required_scalars.items():
        if config.get(key) != expected:
            raise ValueError(f"冻结配置 {key}={config.get(key)!r}，预期 {expected!r}")

    members = config.get("members")
    if not isinstance(members, list) or len(members) != 3:
        raise ValueError("冻结成员必须恰好为三个")
    member_ids = tuple(member.get("experiment_id") for member in members)
    if member_ids != EXPECTED_MEMBER_IDS:
        raise ValueError(f"冻结成员或顺序错误：{member_ids}")
    if FORBIDDEN_MEMBER_IDS.intersection(member_ids):
        raise ValueError("禁止的历史模型或父集成进入成员列表")
    if set(config.get("forbidden_prediction_members", [])) != FORBIDDEN_MEMBER_IDS:
        raise ValueError("forbidden_prediction_members 合同错误")
    for member in members:
        if member.get("role") != "ATOMIC_SIBLING":
            raise ValueError("成员必须全部标记为 ATOMIC_SIBLING")
        if member.get("required_status") != "COMPLETE":
            raise ValueError("成员 required_status 必须为 COMPLETE")
        if member["experiment_id"] == EXPECTED_MEMBER_IDS[0]:
            if member.get("required_robustness_gate") is not False:
                raise ValueError("canonical v80 不应声明 split robustness gate")
        elif (
            member.get("required_robustness_gate") is not True
            or member.get("required_decision") != "ROBUSTNESS_REPLICATION_PASSED"
        ):
            raise ValueError("v81/v82 必须冻结 robustness gate 和 decision")

    method = config.get("method", {})
    expected_method = {
        "prediction_space": "RAW_PROBABILITY",
        "operator": "FIXED_ARITHMETIC_MEAN",
        "weights": [1.0 / 3.0] * 3,
        "member_selection": "NONE",
        "weight_fitting": "NONE",
        "rank_or_ecdf": "NONE",
        "calibration_transform": "NONE",
        "oof_and_test_use_identical_operator": True,
    }
    if method != expected_method:
        raise ValueError("融合方法不是冻结的原始概率固定 1/3 算术平均")
    expected_trigger = {
        "all_members_status": "COMPLETE",
        "all_frozen_verifiers_must_pass": True,
        "v81_split_seed_robustness_gate_passes": True,
        "v82_split_seed_robustness_gate_passes": True,
    }
    if config.get("formal_trigger") != expected_trigger:
        raise ValueError("formal trigger 合同与预注册不一致")
    meta = config.get("meta_buckets", {})
    if (
        meta.get("n_splits") != 5
        or meta.get("shuffle") is not True
        or meta.get("random_state") != 42
        or meta.get("purpose") != "evaluation_only_no_selection_or_fitting"
    ):
        raise ValueError("meta bucket 合同不是冻结 seed42 五折纯评估")
    gate = config.get("promotion_gate", {})
    if (
        gate.get("minimum_oof_delta_vs_canonical_v80") != 0.0001
        or gate.get("all_meta_bucket_deltas_strictly_positive") is not True
        or gate.get("decision_if_pass") != "PROMOTE"
        or gate.get("decision_if_fail") != "REJECT"
    ):
        raise ValueError("晋级门槛与预注册不一致")
    expected_calibration = {
        "fixed_width_bins": 20,
        "metrics": [
            "brier_score",
            "log_loss",
            "mean_prediction",
            "observed_positive_rate",
            "calibration_bias",
            "fixed_width_ece",
        ],
        "diagnostic_only": True,
    }
    if config.get("calibration_report") != expected_calibration:
        raise ValueError("校准报告合同与预注册不一致")


def validate_static_member_contracts(config: dict[str, Any]) -> None:
    for member in config["members"]:
        directory = PROJECT_DIR / member["directory"]
        runner_path = directory / member["runner"]
        member_config_path = directory / "frozen_config.json"
        if directory.parent != MODEL_DIR or not directory.is_dir():
            raise ValueError(f"成员目录不在 model 根目录：{directory}")
        if sha256_file(runner_path) != member["runner_sha256"]:
            raise ValueError(f"冻结 runner SHA 改变：{member['experiment_id']}")
        if sha256_file(member_config_path) != member["config_sha256"]:
            raise ValueError(f"冻结 config SHA 改变：{member['experiment_id']}")


def validate_preflight_record() -> dict[str, Any]:
    if not PREFLIGHT_PATH.is_file():
        raise FileNotFoundError("缺少冻结 Preflight R1 记录")
    record = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "status": "PREFLIGHT_R1_COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "preflight_revision": "R1",
        "runner_sha256": sha256_file(Path(__file__)),
        "config_sha256": sha256_file(CONFIG_PATH),
        "real_member_predictions_read": False,
        "formal_run_executed": False,
    }
    if record != expected:
        raise ValueError("Preflight R1 记录或 runner/config SHA 已改变")
    return record


def audit() -> dict[str, Any]:
    config = load_frozen_config()
    validate_static_member_contracts(config)
    preflight = validate_preflight_record()
    result = {
        "status": "AUDIT_OK_NO_REAL_MEMBER_OUTPUTS_READ",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "members": [member["experiment_id"] for member in config["members"]],
        "method": config["method"],
        "preflight_revision": preflight["preflight_revision"],
        "runner_sha256": preflight["runner_sha256"],
        "config_sha256": preflight["config_sha256"],
        "formal_outputs_created": False,
        "formal_mode_required": "--mode run",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def validate_probability_array(name: str, values: np.ndarray, expected: int) -> None:
    array = np.asarray(values)
    if array.ndim != 1 or len(array) != expected:
        raise ValueError(f"{name} shape={array.shape}，预期 ({expected},)")
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError(f"{name} 不是数值数组")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} 含 NaN/Inf")
    if ((array < 0.0) | (array > 1.0)).any():
        raise ValueError(f"{name} 概率超出 [0,1]")


def fixed_equal_mean(arrays: list[np.ndarray]) -> np.ndarray:
    if len(arrays) != 3:
        raise ValueError("固定等权融合必须恰好接收三个数组")
    shapes = [np.asarray(array).shape for array in arrays]
    if len(set(shapes)) != 1 or len(shapes[0]) != 1:
        raise ValueError(f"成员数组 shape 不一致：{shapes}")
    converted = [np.asarray(array, dtype=np.float64) for array in arrays]
    for index, array in enumerate(converted, start=1):
        validate_probability_array(f"member_{index}", array, len(converted[0]))
    result = np.add.reduce(converted, dtype=np.float64) / 3.0
    validate_probability_array("equal_bag", result, len(converted[0]))
    return result


def calibration_summary(y: np.ndarray, prediction: np.ndarray, bins: int) -> dict[str, float]:
    y_array = np.asarray(y, dtype=np.int8)
    pred = np.asarray(prediction, dtype=np.float64)
    validate_probability_array("calibration_prediction", pred, len(y_array))
    if set(np.unique(y_array)) != {0, 1}:
        raise ValueError("校准标签必须同时包含二分类 0/1")
    if bins <= 1:
        raise ValueError("校准分箱数必须大于1")
    clipped = np.clip(pred, 1e-15, 1.0 - 1e-15)
    bin_index = np.minimum((pred * bins).astype(np.int64), bins - 1)
    ece = 0.0
    for index in range(bins):
        mask = bin_index == index
        if mask.any():
            ece += float(mask.mean()) * abs(float(pred[mask].mean() - y_array[mask].mean()))
    mean_prediction = float(pred.mean())
    observed_rate = float(y_array.mean())
    return {
        "brier_score": float(brier_score_loss(y_array, pred)),
        "log_loss": float(log_loss(y_array, clipped, labels=[0, 1])),
        "mean_prediction": mean_prediction,
        "observed_positive_rate": observed_rate,
        "calibration_bias": mean_prediction - observed_rate,
        "fixed_width_ece": ece,
    }


def pairwise_spearman(arrays: dict[str, np.ndarray]) -> dict[str, float]:
    names = list(arrays)
    result: dict[str, float] = {}
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            correlation = float(spearmanr(arrays[left], arrays[right]).statistic)
            if not np.isfinite(correlation):
                raise ValueError(f"Spearman 不可计算：{left} vs {right}")
            result[f"{left}__{right}"] = correlation
    return result


def evaluate_predictions(
    config: dict[str, Any],
    y: np.ndarray,
    member_oof: dict[str, np.ndarray],
    member_test: dict[str, np.ndarray],
    bag_oof: np.ndarray,
    bag_test: np.ndarray,
) -> dict[str, Any]:
    member_ids = list(EXPECTED_MEMBER_IDS)
    if list(member_oof) != member_ids or list(member_test) != member_ids:
        raise ValueError("评估成员顺序不等于冻结 allowlist")
    member_auc = {
        member_id: float(roc_auc_score(y, member_oof[member_id]))
        for member_id in member_ids
    }
    canonical_auc = member_auc[config["canonical_base"]]
    best_member = max(member_ids, key=lambda name: member_auc[name])
    best_member_auc = member_auc[best_member]
    bag_auc = float(roc_auc_score(y, bag_oof))

    splitter = StratifiedKFold(
        n_splits=config["meta_buckets"]["n_splits"],
        shuffle=config["meta_buckets"]["shuffle"],
        random_state=config["meta_buckets"]["random_state"],
    )
    bucket_rows: list[dict[str, Any]] = []
    canonical = member_oof[config["canonical_base"]]
    for bucket, (_, valid_idx) in enumerate(
        splitter.split(np.zeros(len(y)), y), start=1
    ):
        base_auc = float(roc_auc_score(y[valid_idx], canonical[valid_idx]))
        blend_auc = float(roc_auc_score(y[valid_idx], bag_oof[valid_idx]))
        bucket_rows.append(
            {
                "bucket": bucket,
                "rows": len(valid_idx),
                "canonical_v80_auc": base_auc,
                "blend_auc": blend_auc,
                "delta_vs_canonical_v80": blend_auc - base_auc,
            }
        )

    minimum_gain = config["promotion_gate"][
        "minimum_oof_delta_vs_canonical_v80"
    ]
    delta_vs_canonical = bag_auc - canonical_auc
    full_oof_passes = bool(delta_vs_canonical >= minimum_gain)
    buckets_pass = bool(
        all(row["delta_vs_canonical_v80"] > 0.0 for row in bucket_rows)
    )
    passes = full_oof_passes and buckets_pass
    decision = (
        config["promotion_gate"]["decision_if_pass"]
        if passes
        else config["promotion_gate"]["decision_if_fail"]
    )

    oof_for_correlation = {**member_oof, EXPERIMENT_ID: bag_oof}
    test_for_correlation = {**member_test, EXPERIMENT_ID: bag_test}
    bins = config["calibration_report"]["fixed_width_bins"]
    calibration = {
        name: calibration_summary(y, prediction, bins)
        for name, prediction in oof_for_correlation.items()
    }
    return {
        "member_oof_auc": member_auc,
        "canonical_base": config["canonical_base"],
        "canonical_v80_oof_auc": canonical_auc,
        "best_input_member": best_member,
        "best_input_oof_auc": best_member_auc,
        "oof_auc": bag_auc,
        "oof_delta_vs_canonical_v80": delta_vs_canonical,
        "oof_delta_vs_best_input": bag_auc - best_member_auc,
        "meta_buckets": bucket_rows,
        "correlation": {
            "oof_spearman": pairwise_spearman(oof_for_correlation),
            "test_spearman": pairwise_spearman(test_for_correlation),
        },
        "calibration": calibration,
        "promotion_gate": {
            "minimum_oof_delta_vs_canonical_v80": minimum_gain,
            "full_oof_delta_passes": full_oof_passes,
            "all_meta_bucket_deltas_strictly_positive": buckets_pass,
            "meta_buckets_won": sum(
                row["delta_vs_canonical_v80"] > 0.0 for row in bucket_rows
            ),
            "meta_buckets_total": len(bucket_rows),
            "passes": passes,
        },
        "decision": decision,
    }


def smoke() -> dict[str, Any]:
    config = load_frozen_config()
    validate_static_member_contracts(config)
    validate_preflight_record()
    y = np.tile(np.array([0, 1], dtype=np.int8), 10)
    base = np.linspace(0.05, 0.95, len(y), dtype=np.float64)
    member_one = np.clip(base + 0.01, 0.0, 1.0)
    member_two = np.clip(base - 0.01, 0.0, 1.0)
    bag = fixed_equal_mean([base, member_one, member_two])
    if not np.allclose(bag, base, atol=1e-15, rtol=0.0):
        raise AssertionError("合成等权平均不符合固定算子")
    calibration = calibration_summary(y, bag, 5)
    status = {
        "status": "SMOKE_OK_SYNTHETIC_ONLY_NO_REAL_OUTPUTS_READ",
        "experiment_id": EXPERIMENT_ID,
        "synthetic_rows": len(y),
        "operator_verified": True,
        "calibration_fields": sorted(calibration),
        "formal_outputs_created": False,
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


def import_member_runner(member: dict[str, Any]) -> ModuleType:
    runner_path = PROJECT_DIR / member["directory"] / member["runner"]
    module_name = f"v83_verify_{member['experiment_id']}"
    spec = importlib.util.spec_from_file_location(module_name, runner_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法导入冻结 verifier：{runner_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "verify_complete", None)):
        raise ValueError(f"成员没有 verify_complete：{member['experiment_id']}")
    return module


def validate_member_result(
    member: dict[str, Any], results: dict[str, Any]
) -> None:
    member_id = member["experiment_id"]
    if results.get("experiment_id") != member_id:
        raise ValueError(f"成员 experiment_id 错误：{member_id}")
    if results.get("status") != member["required_status"]:
        raise ValueError(f"成员未 COMPLETE：{member_id}")
    validation = results.get("artifact_validation", {})
    required_validation = (
        "oof_exactly_once_coverage",
        "probabilities_finite_and_in_range",
        "submission_id_matches_test",
        "strict_prior_self_check",
        "checkpoint_reconstruction_required",
    )
    if any(validation.get(key) is not True for key in required_validation):
        raise ValueError(f"成员 artifact_validation 未通过：{member_id}")
    if member["required_robustness_gate"]:
        robustness = results.get("split_seed_robustness_gate", {})
        if robustness.get("passes") is not True:
            raise ValueError(f"成员 robustness gate 未通过：{member_id}")
        if results.get("decision") != member["required_decision"]:
            raise ValueError(f"成员 robustness decision 错误：{member_id}")


def verify_members(config: dict[str, Any]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for member in config["members"]:
        directory = PROJECT_DIR / member["directory"]
        module = import_member_runner(member)
        module.verify_complete()
        results_path = directory / "cv_results.json"
        sources_path = directory / "sources.json"
        results = json.loads(results_path.read_text(encoding="utf-8"))
        sources = json.loads(sources_path.read_text(encoding="utf-8"))
        validate_member_result(member, results)
        files = {
            "runner": file_record(directory / member["runner"]),
            "frozen_config": file_record(directory / "frozen_config.json"),
            "cv_results": file_record(results_path),
            "sources": file_record(sources_path),
            "oof_proba": file_record(directory / "oof_proba.npy"),
            "test_proba": file_record(directory / "test_proba.npy"),
        }
        if files["runner"]["sha256"] != member["runner_sha256"]:
            raise ValueError(f"verifier 后 runner SHA 改变：{member['experiment_id']}")
        if files["frozen_config"]["sha256"] != member["config_sha256"]:
            raise ValueError(f"verifier 后 config SHA 改变：{member['experiment_id']}")
        row_identity = sources.get("row_identity")
        if not isinstance(row_identity, dict):
            raise ValueError(f"成员缺少 row_identity：{member['experiment_id']}")
        verified.append(
            {
                "member": member,
                "module": module,
                "results": results,
                "row_identity": row_identity,
                "files": files,
            }
        )
    return verified


def load_data_contract(
    config: dict[str, Any], verified: list[dict[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray]:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[config["id_column"], config["target"]])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[config["id_column"]])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if len(train) != config["expected_train_rows"]:
        raise ValueError("train 行数与冻结配置不一致")
    if len(test) != config["expected_test_rows"]:
        raise ValueError("test 行数与冻结配置不一致")
    if not train[config["id_column"]].is_unique or not test[config["id_column"]].is_unique:
        raise ValueError("train/test id 不唯一")
    if list(sample.columns) != [config["id_column"], config["target"]]:
        raise ValueError("sample_submission schema 错误")
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample_submission 与 test id 行序不一致")
    labels = set(train[config["target"]].astype(str).unique())
    if config["positive_label"] not in labels or len(labels) != 2:
        raise ValueError(f"目标标签不是预期二分类：{labels}")
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)

    proof_rows = []
    for entry in verified:
        member_id = entry["member"]["experiment_id"]
        module = entry["module"]
        row_identity = entry["row_identity"]
        if not callable(getattr(module, "sha256_ids", None)):
            raise ValueError(f"成员缺少 sha256_ids：{member_id}")
        expected_train_hash = module.sha256_ids(train[config["id_column"]])
        expected_test_hash = module.sha256_ids(test[config["id_column"]])
        if row_identity.get("train_id_sha256") != expected_train_hash:
            raise ValueError(f"成员 train 行序证明错误：{member_id}")
        if row_identity.get("test_id_sha256") != expected_test_hash:
            raise ValueError(f"成员 test 行序证明错误：{member_id}")
        if row_identity.get("train_rows") != len(train):
            raise ValueError(f"成员 train 行数证明错误：{member_id}")
        if row_identity.get("test_rows") != len(test):
            raise ValueError(f"成员 test 行数证明错误：{member_id}")
        proof_rows.append(row_identity)
    if any(row != proof_rows[0] for row in proof_rows[1:]):
        raise ValueError("三个成员的规范行序证明不一致")
    return train, test, sample, y


def member_snapshot(verified: list[dict[str, Any]]) -> dict[str, Any]:
    members = []
    for entry in verified:
        member = entry["member"]
        results = entry["results"]
        members.append(
            {
                "experiment_id": member["experiment_id"],
                "role": member["role"],
                "outer_split_seed": member["outer_split_seed"],
                "status": results["status"],
                "frozen_verifier_passed": True,
                "required_robustness_gate": member["required_robustness_gate"],
                "required_decision": member["required_decision"],
                "robustness_gate_passes": (
                    results.get("split_seed_robustness_gate", {}).get("passes")
                    if member["required_robustness_gate"]
                    else None
                ),
                "decision": results.get("decision"),
                "files": entry["files"],
            }
        )
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "snapshot_policy": "IMMUTABLE_AFTER_FORMAL_TRIGGER",
        "candidate_kind": "THREE_ATOMIC_SIBLINGS_ONLY",
        "members": members,
        "method": {
            "prediction_space": "RAW_PROBABILITY",
            "operator": "FIXED_ARITHMETIC_MEAN",
            "weights": [1.0 / 3.0] * 3,
            "member_selection": "NONE",
            "weight_fitting": "NONE",
            "rank_or_ecdf": "NONE",
            "calibration_transform": "NONE",
            "oof_and_test_use_identical_operator": True,
        },
    }


def lineage_payload(config: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        {
            "id": member["experiment_id"],
            "type": "ATOMIC_SINGLE_MODEL",
            "family": "STRICT_V61_SPLIT_SEED_SIBLING",
        }
        for member in config["members"]
    ]
    nodes.append({"id": EXPERIMENT_ID, "type": "SMALL_BLEND"})
    edges = [
        {
            "source": member["experiment_id"],
            "target": EXPERIMENT_ID,
            "role": "RAW_PROBABILITY_PREDICTION",
            "weight": 1.0 / 3.0,
        }
        for member in config["members"]
    ]
    node_ids = {node["id"] for node in nodes}
    if node_ids.intersection(FORBIDDEN_MEMBER_IDS):
        raise ValueError("lineage 意外包含禁止的历史模型或父集成")
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "nodes": nodes,
        "prediction_edges": edges,
        "no_parent_ensemble_member": True,
        "forbidden_prediction_members": sorted(FORBIDDEN_MEMBER_IDS),
        "note": (
            "v80/v81/v82 are independently trained outer-split siblings; upstream "
            "diagnostic references are not prediction inputs to v83"
        ),
    }


def load_member_arrays(
    config: dict[str, Any], train_rows: int, test_rows: int
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    oof: dict[str, np.ndarray] = {}
    test: dict[str, np.ndarray] = {}
    for member in config["members"]:
        member_id = member["experiment_id"]
        directory = PROJECT_DIR / member["directory"]
        oof_values = np.load(directory / "oof_proba.npy", mmap_mode="r")
        test_values = np.load(directory / "test_proba.npy", mmap_mode="r")
        validate_probability_array(f"{member_id}.oof", oof_values, train_rows)
        validate_probability_array(f"{member_id}.test", test_values, test_rows)
        oof[member_id] = oof_values
        test[member_id] = test_values
    return oof, test


def peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        return native
    return native * 1024


def resource_usage(started: float) -> dict[str, float | int]:
    peak_bytes = peak_rss_bytes()
    return {
        "elapsed_seconds": time.monotonic() - started,
        "peak_rss_bytes": peak_bytes,
        "peak_rss_gib": peak_bytes / 1024**3,
    }


def validate_resource_values(
    usage: dict[str, Any], config: dict[str, Any], stage: str
) -> None:
    elapsed = usage.get("elapsed_seconds")
    peak_bytes = usage.get("peak_rss_bytes")
    peak_gib = usage.get("peak_rss_gib")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not np.isfinite(elapsed)
        or elapsed < 0.0
    ):
        raise ValueError(f"{stage}: elapsed_seconds 非法")
    if (
        isinstance(peak_bytes, bool)
        or not isinstance(peak_bytes, int)
        or peak_bytes <= 0
    ):
        raise ValueError(f"{stage}: peak_rss_bytes 非法")
    if (
        isinstance(peak_gib, bool)
        or not isinstance(peak_gib, (int, float))
        or not np.isfinite(peak_gib)
        or not np.isclose(peak_gib, peak_bytes / 1024**3, atol=1e-12, rtol=0.0)
    ):
        raise ValueError(f"{stage}: peak_rss_gib 与 bytes 不一致")
    if elapsed > config["time_budget_seconds"]:
        raise ResourceBudgetExceeded(
            f"{stage}: elapsed_seconds={elapsed:.6f} 超过 "
            f"{config['time_budget_seconds']} 秒"
        )
    memory_limit = int(config["memory_budget_gib"] * 1024**3)
    if peak_bytes > memory_limit:
        raise ResourceBudgetExceeded(
            f"{stage}: peak_rss_bytes={peak_bytes} 超过 {memory_limit}"
        )


def enforce_resource_budget(
    started: float, config: dict[str, Any], stage: str
) -> dict[str, float | int]:
    usage = resource_usage(started)
    validate_resource_values(usage, config, stage)
    return usage


def expected_artifact_validation(train_rows: int, test_rows: int) -> dict[str, Any]:
    return {
        "oof_rows": train_rows,
        "test_rows": test_rows,
        "probabilities_finite_and_in_range": True,
        "submission_id_matches_test": True,
        "member_verifiers_rebuilt_atomic_outputs": True,
        "blend_reconstruction_required": True,
        "no_member_selection_or_weight_fitting": True,
    }


def validate_sources_header(sources: dict[str, Any]) -> None:
    if sources.get("schema_version") != 1:
        raise ValueError("sources schema_version 错误")
    if sources.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("sources experiment_id 错误")
    if sources.get("immutable") is not True:
        raise ValueError("sources 未声明不可变")


def validate_completed_result_contract(
    results: dict[str, Any],
    recomputed: dict[str, Any],
    config: dict[str, Any],
    train_rows: int,
    test_rows: int,
) -> None:
    expected_result_contract = {
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": True,
        "cycle_count_update_required": True,
        "canonical_base": config["canonical_base"],
        "members": list(EXPECTED_MEMBER_IDS),
        "member_weights": {name: 1.0 / 3.0 for name in EXPECTED_MEMBER_IDS},
        "formal_trigger_verified": True,
        "member_verifiers": {name: "PASSED" for name in EXPECTED_MEMBER_IDS},
        "base": config["canonical_base"],
        "submission_budget": 0,
    }
    for key, expected in expected_result_contract.items():
        if results.get(key) != expected:
            raise ValueError(f"v83 cv_results {key} 合同不一致")
    expected_top_metrics = {
        "oof_auc": recomputed["oof_auc"],
        "base_oof_auc": recomputed["canonical_v80_oof_auc"],
        "oof_delta_vs_base": recomputed["oof_delta_vs_canonical_v80"],
    }
    for key, expected in expected_top_metrics.items():
        assert_nested_close(results.get(key), expected, key)
    expected_validation = expected_artifact_validation(train_rows, test_rows)
    if results.get("artifact_validation") != expected_validation:
        raise ValueError("v83 artifact_validation 字段或值不一致")
    expected_budget = {
        "time_budget_seconds": config["time_budget_seconds"],
        "memory_budget_gib": config["memory_budget_gib"],
        "cpu_threads": config["cpu_threads"],
    }
    if results.get("resource_budget") != expected_budget:
        raise ValueError("v83 resource_budget 合同不一致")
    validate_resource_values(results, config, "stored_complete_result")


def formal_output_paths() -> dict[str, Path]:
    return {name: OUT_DIR / name for name in FORMAL_FILENAMES}


def build_sources(
    snapshot_path: Path,
    lineage_path: Path,
    output_paths: dict[str, Path],
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "immutable": True,
        "code_and_inputs": {
            "runner": file_record(Path(__file__)),
            "frozen_config": file_record(CONFIG_PATH),
            "preflight_r1": file_record(PREFLIGHT_PATH),
            "train_csv": file_record(DATA_DIR / "train.csv"),
            "test_csv": file_record(DATA_DIR / "test.csv"),
            "sample_submission_csv": file_record(DATA_DIR / "sample_submission.csv"),
            "candidate_snapshot": file_record(snapshot_path),
            "lineage": file_record(lineage_path),
        },
        "members": [
            {
                "experiment_id": member["experiment_id"],
                "directory": member["directory"],
                "cv_results": file_record(
                    PROJECT_DIR / member["directory"] / "cv_results.json"
                ),
                "sources": file_record(
                    PROJECT_DIR / member["directory"] / "sources.json"
                ),
                "oof_proba": file_record(
                    PROJECT_DIR / member["directory"] / "oof_proba.npy"
                ),
                "test_proba": file_record(
                    PROJECT_DIR / member["directory"] / "test_proba.npy"
                ),
            }
            for member in config["members"]
        ],
        "row_identity": {
            "train_rows": len(train),
            "test_rows": len(test),
            "train_id_sha256": sha256_ids(train[config["id_column"]]),
            "test_id_sha256": sha256_ids(test[config["id_column"]]),
        },
        "outputs": {
            name: file_record(path)
            for name, path in output_paths.items()
            if name in {"oof_proba.npy", "test_proba.npy", "submission.csv", "train_log.txt"}
        },
    }


def failed_result_payload(
    config: dict[str, Any], stage: str, error: Exception, started: float
) -> dict[str, Any]:
    usage = resource_usage(started)
    return {
        "schema_version": 1,
        "status": "FAILED",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": False,
        "formal_stage": stage,
        "error_type": type(error).__name__,
        "error": str(error),
        "formal_outputs_complete": False,
        "allowed_for_further_fusion": False,
        "allowed_for_submission": False,
        "resource_budget": {
            "time_budget_seconds": config["time_budget_seconds"],
            "memory_budget_gib": config["memory_budget_gib"],
            "cpu_threads": config["cpu_threads"],
        },
        **usage,
    }


def run_formal() -> None:
    started = time.monotonic()
    config = load_frozen_config()
    validate_static_member_contracts(config)
    validate_preflight_record()
    with LOCK_PATH.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("v83 已有正式 run 实例持有 flock") from error

        results_path = OUT_DIR / "cv_results.json"
        if results_path.exists():
            existing = json.loads(results_path.read_text(encoding="utf-8"))
            if existing.get("status") == "COMPLETE":
                verify_complete()
                return
            raise RuntimeError("cv_results.json 已存在且非 COMPLETE，必须人工审计")

        pending_results_path = OUT_DIR / f".cv_results.complete.{os.getpid()}.json"
        stage = "FORMAL_TRIGGER"
        try:
            verified = verify_members(config)
            train, test, sample, y = load_data_contract(config, verified)
            enforce_resource_budget(started, config, "MEMBERS_AND_DATA_LOADED")

            snapshot = member_snapshot(verified)
            lineage = lineage_payload(config)
            snapshot_path = OUT_DIR / "candidate_snapshot.json"
            lineage_path = OUT_DIR / "lineage.json"
            write_immutable_json(snapshot_path, snapshot)
            write_immutable_json(lineage_path, lineage)

            stage = "PREDICTIONS_LOADED_AND_EVALUATED"
            member_oof, member_test = load_member_arrays(
                config, len(train), len(test)
            )
            bag_oof = fixed_equal_mean(list(member_oof.values()))
            bag_test = fixed_equal_mean(list(member_test.values()))
            evaluation = evaluate_predictions(
                config, y, member_oof, member_test, bag_oof, bag_test
            )
            enforce_resource_budget(started, config, stage)

            stage = "ALL_NON_RESULT_OUTPUTS_WRITTEN"
            output_paths = formal_output_paths()
            atomic_save_npy(output_paths["oof_proba.npy"], bag_oof)
            atomic_save_npy(output_paths["test_proba.npy"], bag_test)
            submission = sample.copy()
            submission[config["target"]] = bag_test
            atomic_write_csv(output_paths["submission.csv"], submission)
            log_payload = (
                f"experiment_id={EXPERIMENT_ID}\n"
                "formal_trigger=ALL_THREE_FROZEN_VERIFIERS_PASSED\n"
                "method=RAW_PROBABILITY_FIXED_ONE_THIRD_ARITHMETIC_MEAN\n"
                f"oof_auc={evaluation['oof_auc']:.15f}\n"
                f"delta_vs_v80={evaluation['oof_delta_vs_canonical_v80']:+.15f}\n"
                f"meta_buckets_won="
                f"{evaluation['promotion_gate']['meta_buckets_won']}/5\n"
                f"decision={evaluation['decision']}\n"
            )
            write_immutable_text(output_paths["train_log.txt"], log_payload)

            sources = build_sources(
                snapshot_path, lineage_path, output_paths, train, test, config
            )
            sources_path = OUT_DIR / "sources.json"
            write_immutable_json(sources_path, sources)
            usage = enforce_resource_budget(started, config, stage)
            results = {
                "schema_version": 1,
                "status": "COMPLETE",
                "experiment_id": EXPERIMENT_ID,
                "research_cycle": config["research_cycle"],
                "cycle_position": config["cycle_position"],
                "experiment_type": config["experiment_type"],
                "counts_toward_cycle": True,
                "cycle_count_update_required": True,
                "competition": config["competition"],
                "model": "strict three-split raw-probability fixed equal bag",
                "hypothesis": (
                    "averaging three strict outer-split sibling predictions in raw "
                    "probability space reduces split variance without meta fitting"
                ),
                "canonical_base": config["canonical_base"],
                "members": list(EXPECTED_MEMBER_IDS),
                "member_weights": {
                    name: 1.0 / 3.0 for name in EXPECTED_MEMBER_IDS
                },
                "method": config["method"],
                "formal_trigger_verified": True,
                "member_verifiers": {
                    entry["member"]["experiment_id"]: "PASSED"
                    for entry in verified
                },
                "evaluation": evaluation,
                "oof_auc": evaluation["oof_auc"],
                "base": config["canonical_base"],
                "base_oof_auc": evaluation["canonical_v80_oof_auc"],
                "oof_delta_vs_base": evaluation[
                    "oof_delta_vs_canonical_v80"
                ],
                "decision": evaluation["decision"],
                "allowed_for_further_fusion": evaluation["promotion_gate"][
                    "passes"
                ],
                "allowed_for_submission": False,
                "submission_budget": config["submission_budget"],
                "resource_budget": {
                    "time_budget_seconds": config["time_budget_seconds"],
                    "memory_budget_gib": config["memory_budget_gib"],
                    "cpu_threads": config["cpu_threads"],
                },
                **usage,
                "frozen_config_sha256": sha256_file(CONFIG_PATH),
                "candidate_snapshot_sha256": sha256_file(snapshot_path),
                "lineage_sha256": sha256_file(lineage_path),
                "sources_sha256": sha256_file(sources_path),
                "artifact_sha256": {
                    name: sha256_file(path)
                    for name, path in output_paths.items()
                    if name
                    in {
                        "oof_proba.npy",
                        "test_proba.npy",
                        "submission.csv",
                        "train_log.txt",
                    }
                },
                "artifact_validation": expected_artifact_validation(
                    len(bag_oof), len(bag_test)
                ),
            }

            stage = "FINAL_REBUILD_VERIFY"
            _verify_complete(
                config,
                verified,
                train,
                test,
                sample,
                y,
                results_override=results,
            )
            usage = enforce_resource_budget(started, config, stage)
            results.update(usage)
            validate_completed_result_contract(
                results, evaluation, config, len(train), len(test)
            )

            stage = "COMPLETE_RESULT_STAGED"
            encoded_results = (
                json.dumps(results, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
            _atomic_bytes(pending_results_path, encoded_results)
            enforce_resource_budget(started, config, stage)

            stage = "FORMAL_SCOPE_COMPLETE"
            os.replace(pending_results_path, results_path)
            enforce_resource_budget(started, config, stage)
        except Exception as error:
            failure = failed_result_payload(config, stage, error, started)
            atomic_write_json(results_path, failure)
            print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
            raise
        finally:
            if pending_results_path.exists():
                pending_results_path.unlink()

        print(
            json.dumps(
                {
                    "status": "COMPLETE_AND_VERIFIED",
                    "experiment_id": EXPERIMENT_ID,
                    "oof_auc": evaluation["oof_auc"],
                    "oof_delta_vs_canonical_v80": evaluation[
                        "oof_delta_vs_canonical_v80"
                    ],
                    "meta_buckets_won": evaluation["promotion_gate"][
                        "meta_buckets_won"
                    ],
                    "decision": evaluation["decision"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )


def assert_nested_close(actual: Any, expected: Any, path: str = "root") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{path} 字典 schema 不一致")
        for key, value in expected.items():
            assert_nested_close(actual[key], value, f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{path} 列表 schema 不一致")
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
            raise ValueError(f"{path} 数值不一致：{actual} != {expected}")
        return
    if actual != expected:
        raise ValueError(f"{path} 不一致：{actual!r} != {expected!r}")


def _verify_complete(
    config: dict[str, Any],
    verified: list[dict[str, Any]],
    train: pd.DataFrame,
    test: pd.DataFrame,
    sample: pd.DataFrame,
    y: np.ndarray,
    results_override: dict[str, Any] | None = None,
) -> None:
    output_paths = formal_output_paths()
    required_outputs = set(FORMAL_FILENAMES)
    if results_override is not None:
        required_outputs.remove("cv_results.json")
    missing = [
        name
        for name, output_path in output_paths.items()
        if name in required_outputs and not output_path.is_file()
    ]
    if missing:
        raise FileNotFoundError(f"v83 COMPLETE 产物缺失：{missing}")
    results = (
        results_override
        if results_override is not None
        else json.loads(
            output_paths["cv_results.json"].read_text(encoding="utf-8")
        )
    )
    snapshot = json.loads(
        output_paths["candidate_snapshot.json"].read_text(encoding="utf-8")
    )
    lineage = json.loads(output_paths["lineage.json"].read_text(encoding="utf-8"))
    sources = json.loads(output_paths["sources.json"].read_text(encoding="utf-8"))
    if results.get("status") != "COMPLETE":
        raise ValueError("v83 cv_results 状态不是 COMPLETE")
    if results.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("v83 cv_results experiment_id 错误")
    if snapshot != member_snapshot(verified):
        raise ValueError("candidate_snapshot 与当前冻结来源不一致")
    if lineage != lineage_payload(config):
        raise ValueError("lineage 与固定三 sibling 合同不一致")
    if results["frozen_config_sha256"] != sha256_file(CONFIG_PATH):
        raise ValueError("cv_results frozen_config SHA 不一致")
    if results["candidate_snapshot_sha256"] != sha256_file(
        output_paths["candidate_snapshot.json"]
    ):
        raise ValueError("cv_results candidate_snapshot SHA 不一致")
    if results["lineage_sha256"] != sha256_file(output_paths["lineage.json"]):
        raise ValueError("cv_results lineage SHA 不一致")
    if results["sources_sha256"] != sha256_file(output_paths["sources.json"]):
        raise ValueError("cv_results sources SHA 不一致")

    member_oof, member_test = load_member_arrays(config, len(train), len(test))
    rebuilt_oof = fixed_equal_mean(list(member_oof.values()))
    rebuilt_test = fixed_equal_mean(list(member_test.values()))
    stored_oof = np.load(output_paths["oof_proba.npy"], mmap_mode="r")
    stored_test = np.load(output_paths["test_proba.npy"], mmap_mode="r")
    validate_probability_array("v83.oof", stored_oof, len(train))
    validate_probability_array("v83.test", stored_test, len(test))
    if not np.array_equal(rebuilt_oof, np.asarray(stored_oof)):
        raise ValueError("v83 OOF 无法由三个原子输出逐元素重建")
    if not np.array_equal(rebuilt_test, np.asarray(stored_test)):
        raise ValueError("v83 test 无法由三个原子输出逐元素重建")
    submission = pd.read_csv(output_paths["submission.csv"])
    if list(submission.columns) != [config["id_column"], config["target"]]:
        raise ValueError("v83 submission schema 错误")
    if not submission[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("v83 submission id 行序错误")
    if not np.allclose(
        submission[config["target"]].to_numpy(np.float64),
        rebuilt_test,
        atol=1e-15,
        rtol=0.0,
    ):
        raise ValueError("v83 submission 与重建 test 不一致")
    if not sample[config["id_column"]].equals(submission[config["id_column"]]):
        raise ValueError("v83 submission 与 sample id 不一致")

    recomputed = evaluate_predictions(
        config, y, member_oof, member_test, rebuilt_oof, rebuilt_test
    )
    assert_nested_close(results["evaluation"], recomputed, "evaluation")
    validate_completed_result_contract(
        results, recomputed, config, len(train), len(test)
    )
    expected_decision = recomputed["decision"]
    if results["decision"] != expected_decision:
        raise ValueError("v83 decision 未由冻结门槛推导")
    if results["allowed_for_further_fusion"] is not recomputed["promotion_gate"]["passes"]:
        raise ValueError("allowed_for_further_fusion 与门槛不一致")
    if results["allowed_for_submission"] is not False:
        raise ValueError("提交预算为0，allowed_for_submission 必须为 false")
    if results["method"] != config["method"]:
        raise ValueError("cv_results 融合方法合同不一致")

    validate_sources_header(sources)
    expected_code_inputs = {
        "runner": file_record(Path(__file__)),
        "frozen_config": file_record(CONFIG_PATH),
        "preflight_r1": file_record(PREFLIGHT_PATH),
        "train_csv": file_record(DATA_DIR / "train.csv"),
        "test_csv": file_record(DATA_DIR / "test.csv"),
        "sample_submission_csv": file_record(DATA_DIR / "sample_submission.csv"),
        "candidate_snapshot": file_record(output_paths["candidate_snapshot.json"]),
        "lineage": file_record(output_paths["lineage.json"]),
    }
    if sources.get("code_and_inputs") != expected_code_inputs:
        raise ValueError("sources code_and_inputs 不一致")
    expected_source_members = [
        {
            "experiment_id": member["experiment_id"],
            "directory": member["directory"],
            "cv_results": file_record(
                PROJECT_DIR / member["directory"] / "cv_results.json"
            ),
            "sources": file_record(
                PROJECT_DIR / member["directory"] / "sources.json"
            ),
            "oof_proba": file_record(
                PROJECT_DIR / member["directory"] / "oof_proba.npy"
            ),
            "test_proba": file_record(
                PROJECT_DIR / member["directory"] / "test_proba.npy"
            ),
        }
        for member in config["members"]
    ]
    if sources.get("members") != expected_source_members:
        raise ValueError("sources 成员 allowlist、顺序或文件哈希不一致")
    expected_output_names = {
        "oof_proba.npy",
        "test_proba.npy",
        "submission.csv",
        "train_log.txt",
    }
    if set(sources.get("outputs", {})) != expected_output_names:
        raise ValueError("sources 输出清单不完整")
    if set(results.get("artifact_sha256", {})) != expected_output_names:
        raise ValueError("cv_results artifact_sha256 schema 不完整")
    for name in expected_output_names:
        record = file_record(output_paths[name])
        if sources["outputs"][name] != record:
            raise ValueError(f"sources 输出哈希不一致：{name}")
        if results["artifact_sha256"][name] != record["sha256"]:
            raise ValueError(f"cv_results 输出哈希不一致：{name}")
    expected_row_identity = {
        "train_rows": len(train),
        "test_rows": len(test),
        "train_id_sha256": sha256_ids(train[config["id_column"]]),
        "test_id_sha256": sha256_ids(test[config["id_column"]]),
    }
    if sources.get("row_identity") != expected_row_identity:
        raise ValueError("sources 规范行序证明不一致")


def verify_complete() -> None:
    config = load_frozen_config()
    validate_static_member_contracts(config)
    validate_preflight_record()
    verified = verify_members(config)
    train, test, sample, y = load_data_contract(config, verified)
    _verify_complete(config, verified, train, test, sample, y)
    results = json.loads((OUT_DIR / "cv_results.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": "COMPLETE_REBUILT_FROM_THREE_ATOMIC_MEMBERS_AND_VERIFIED",
                "experiment_id": EXPERIMENT_ID,
                "oof_auc": results["oof_auc"],
                "decision": results["decision"],
                "member_verifiers": results["member_verifiers"],
                "blend_elementwise_equal": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("audit", "smoke", "run", "verify"),
        default="audit",
        help="默认 audit；正式融合必须显式使用 run",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "audit":
        audit()
    elif args.mode == "smoke":
        smoke()
    elif args.mode == "run":
        run_formal()
    else:
        verify_complete()


if __name__ == "__main__":
    main()
