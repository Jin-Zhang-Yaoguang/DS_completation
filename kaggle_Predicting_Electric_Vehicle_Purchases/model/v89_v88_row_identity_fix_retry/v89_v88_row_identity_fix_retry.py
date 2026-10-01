#!/usr/bin/env python3
"""v89: implementation-only row-identity fix retry of v88.

Default mode is hash-only audit. Real prediction arrays are read only in an
explicit ``--mode run`` or ``--mode verify`` invocation.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import platform
import resource
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold


EXPERIMENT_ID = "v89_v88_row_identity_fix_retry"
MEMBER_IDS = (
    "v80_strict_v61_outer104395303_40f",
    "v85_naji_v74_40f",
)
OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
RESULTS_PATH = OUT_DIR / "cv_results.json"
V88_RESULTS_PATH = (
    PROJECT_DIR / "model/v88_strict_v80_v85_cv_blend/cv_results.json"
)
LOCK_PATH = OUT_DIR / "run.lock"
LOG_PATH = OUT_DIR / "train_log.txt"
N_META_FOLDS = 5
META_SEED = 42
WEIGHT_GRID = tuple(round(value * 0.05, 2) for value in range(21))
MATERIAL_ARTIFACTS = (
    "candidate_snapshot.json",
    "lineage.json",
    "meta_folds.json",
    "sources.json",
    "train_log.txt",
    "oof_proba.npy",
    "test_proba.npy",
    "submission.csv",
)


class ResourceBudgetExceeded(RuntimeError):
    def __init__(self, check: dict[str, Any]) -> None:
        super().__init__(",".join(check["breaches"]))
        self.check = check


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_indices(values: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray(values, dtype="<i8").tobytes(order="C")
    ).hexdigest()


def sha256_ids(values: pd.Series) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def resolve_project_path(relative: str) -> Path:
    resolved = (PROJECT_DIR / relative).resolve()
    if PROJECT_DIR.resolve() not in resolved.parents:
        raise ValueError(f"来源路径越界：{relative}")
    return resolved


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
    _atomic_bytes(
        path,
        (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def write_immutable_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != payload:
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
    def emit(self, message: str) -> None:
        line = f"{utc_now()} {message}\n"
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        print(message, flush=True)


def load_frozen_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    validate_static_config(config)
    return config


def validate_static_config(config: dict[str, Any]) -> None:
    expected_scalars = {
        "schema_version": 1,
        "status": "DESIGN_READY_NOT_STARTED",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": "C01",
        "cycle_position": 9,
        "experiment_type": "SMALL_BLEND",
        "counts_toward_cycle_when_formally_closed": False,
        "retry_of": "v88_strict_v80_v85_cv_blend",
        "retry_reason": "IMPLEMENTATION_ONLY_ROW_IDENTITY_HASH_CANONICALIZATION_FIX",
        "sole_implementation_change": (
            "replace v88 length-prefixed ID hashing with the member-source "
            "canonical str(value)+newline SHA-256 and explicitly require both "
            "member row_identity objects to be equal"
        ),
        "competition": "playground-series-s6e9",
        "model": (
            "five-fold cross-fitted mid-ECDF nonnegative grid blend of atomic "
            "v80 and v85"
        ),
        "hypothesis": (
            "v85 Naji prediction diversity adds at least 0.0001 reproducible "
            "OOF AUC beyond best input v85 when combined with strict v80 under "
            "leakage-safe meta cross-fitting"
        ),
        "unique_primary_question": (
            "does v85 diversity provide reproducible marginal gain when "
            "combined with the strict v80 core"
        ),
        "best_input": MEMBER_IDS[1],
        "best_input_oof_auc": 0.9462702273556288,
        "target": "Will_Buy_EV",
        "positive_label": "Yes",
        "id_column": "id",
        "expected_train_rows": 668665,
        "expected_test_rows": 286571,
        "time_budget_seconds": 900,
        "peak_rss_budget_bytes": 4 * 1024**3,
        "memory_budget_gib": 4,
        "cpu_threads": 1,
        "submission_budget": 0,
        "formal_mode": "--mode run",
        "audit_prediction_access": "HASH_ONLY_NO_ARRAY_LOAD",
        "complete_commit_protocol": "STAGED_VERIFY_THEN_ATOMIC_COMPLETE",
        "failed_artifacts_invalid_for_use": True,
        "test_prediction": (
            "mean of five meta-fold test predictions after fold-specific "
            "fit-only transforms and selected weights"
        ),
    }
    for key, expected in expected_scalars.items():
        if config.get(key) != expected:
            raise ValueError(f"冻结配置 {key} 漂移")
    members = config.get("members")
    if not isinstance(members, list) or len(members) != 2:
        raise ValueError("v89 必须恰好有两个成员")
    if tuple(member.get("experiment_id") for member in members) != MEMBER_IDS:
        raise ValueError("成员 ID 或顺序漂移")
    if len({member["experiment_id"] for member in members}) != 2:
        raise ValueError("成员重复")
    expected_members = {
        MEMBER_IDS[0]: {
            "directory": "model/v80_strict_v61_outer104395303_40f",
            "role": "STRICT_CORE_ATOMIC_SINGLE_MODEL",
            "runner": "v80_strict_v61_outer104395303_40f.py",
            "runner_sha256": "808e4fe41ef033da6b6df14edcce3e9f67ced418f9958fddbd0788045af8204a",
            "config_sha256": "79fc1e5451fb823cbde5a59e32b078e8e85cc0ebcef4c500694affab9195e5ab",
            "cv_results_sha256": "52bd098b6b765bffac5efd9f3faa18c4f1773229241fc18f7b2ebfafb41a57e2",
            "sources_sha256": "d1fa6c3203b3e5bf69c673f89e443ed4b94053dd4143e502662d8fffcc9ae1c3",
            "oof_proba_sha256": "403d712897a775fd0869c9b8b89595dd8433ca909202a3313649b6ae77b29ae2",
            "test_proba_sha256": "3dfd38c810276920929e2849ceafdf50de7c3f6f0543636e7efcd96a0ef499cb",
            "required_decision": "ESTABLISH_STRICT_BASELINE",
            "required_model": "strict-prior v61-family LightGBM, 40 outer folds",
            "required_eligible_for_separate_preregistration": None,
            "required_oof_auc": 0.946240610976364,
        },
        MEMBER_IDS[1]: {
            "directory": "model/v85_naji_v74_40f",
            "role": "NAJI_DIVERSITY_ATOMIC_SINGLE_MODEL",
            "runner": "v85_naji_v74_40f.py",
            "runner_sha256": "cadadf826262fbf3f253778bc5764bd48e95b7386f0b92a86eaad02a53f5d30b",
            "config_sha256": "0ed289568d8718b4548442aa843284d31b2282c7ed37a129343cd82a3efcdd8f",
            "cv_results_sha256": "91c22eee2c6d78433f9bf075a6674d0f29e1ce53ea86486b32a32576f9bf8b0b",
            "sources_sha256": "f1d6da96a18382fb89e46aab140099817a50f3742eb52226ebd4183e4e726f1c",
            "oof_proba_sha256": "fee2a13203fd46480906813085181dc9d76e77d1b3d0757bdc43325185ef07b8",
            "test_proba_sha256": "6d31b464324a2a7a61d95cf244b254ec7b3b8e44d3856281b5b6b04d14777a94",
            "required_decision": "ELIGIBLE_FOR_SEPARATE_V80_SMALL_FUSION_PREREGISTRATION_ONLY",
            "required_model": "Naji v74 recipe with 40 outer folds",
            "required_eligible_for_separate_preregistration": True,
            "required_oof_auc": 0.9462702273556288,
        },
    }
    for member in members:
        if member.get("prediction_parent") is not None:
            raise ValueError("v89 只允许原子预测成员")
        if member.get("required_status") != "COMPLETE":
            raise ValueError("成员状态门槛必须为 COMPLETE")
        if (
            member.get("required_n_folds") != 40
            or member.get("required_allowed_for_fusion") is not False
        ):
            raise ValueError("原子成员完成合同漂移")
        for key, expected in expected_members[member["experiment_id"]].items():
            if member.get(key) != expected:
                raise ValueError(f"成员冻结合同漂移：{member['experiment_id']}:{key}")
    expected_forbidden = {
        "v61_income_bin10_te_lgbm_40f_depth4_seed104395303",
        "v64_robust_40f_generator_ensemble",
        "v72_naji_income_bin10_robust_ensemble",
        "v74_naji_income_bin10_100_lgbm_20f",
        "v83_strict_three_split_equal_bag",
    }
    if set(config.get("forbidden_prediction_members", [])) != expected_forbidden:
        raise ValueError("禁止成员列表漂移")
    expected_meta = {
        "n_splits": 5,
        "shuffle": True,
        "random_state": 42,
        "selection_scope": "each meta-train only",
        "holdout_role": "evaluation only",
    }
    if config.get("meta_cv") != expected_meta:
        raise ValueError("meta CV 合同漂移")
    expected_transform = {
        "name": "FIT_ONLY_MID_ECDF",
        "fit_scope": "separately per member inside each meta-train",
        "apply_to": ["meta_train", "meta_holdout", "test"],
        "tie_value": "(count_less + count_less_or_equal) / (2 * n_fit)",
        "full_oof_fit_forbidden": True,
    }
    if config.get("transform") != expected_transform:
        raise ValueError("mid-ECDF 合同漂移")
    search = config.get("weight_search", {})
    if (
        tuple(search.get("v85_weight_grid", [])) != WEIGHT_GRID
        or search.get("v80_weight_formula") != "1 - v85_weight"
        or search.get("objective") != "meta_train_roc_auc"
        or search.get("nonnegative_normalized") is not True
        or search.get("tie_tolerance") != 1e-15
        or search.get("tie_break_1")
        != "minimum absolute distance to v85_weight 0.5"
        or search.get("tie_break_2") != "lower v85_weight"
        or search.get("member_selection") != "NONE"
    ):
        raise ValueError("权重搜索合同漂移")
    if config.get("fixed_equal_weight_control") != {
        "v80_weight": 0.5,
        "v85_weight": 0.5,
        "diagnostic_only": True,
        "cannot_replace_preregistered_primary_method": True,
    }:
        raise ValueError("等权对照合同漂移")
    if config.get("promotion_gate") != {
        "minimum_oof_delta_vs_best_input": 0.0001,
        "required_meta_holdout_wins": 5,
        "meta_holdout_fold_count": 5,
        "all_meta_holdout_deltas_strictly_positive": True,
        "decision_if_pass": "PROMOTE",
        "decision_if_fail": "REJECT",
    }:
        raise ValueError("晋级门槛漂移")
    if config.get("failure_attribution_contract") != {
        "COMPLETE_PROMOTE": None,
        "COMPLETE_REJECT": (
            "PREREGISTERED_PROMOTION_GATE_NOT_MET__DELTA_BELOW_0.0001_OR_"
            "META_HOLDOUT_WINS_BELOW_5_OF_5"
        ),
        "FAILED_RESOURCE_BUDGET": "RESOURCE_BUDGET_EXCEEDED",
        "FAILED_EXCEPTION": "IMPLEMENTATION_OR_RUNTIME_EXCEPTION",
    }:
        raise ValueError("失败归因合同漂移")
    expected_failure_confirmation = {
        "experiment_id": "v88_strict_v80_v85_cv_blend",
        "status": "FAILED_EXCEPTION",
        "decision": "FAILED_EXCEPTION",
        "counts_toward_cycle": True,
        "failure_attribution": "IMPLEMENTATION_OR_RUNTIME_EXCEPTION",
        "error_type": "ValueError",
        "error": "成员行身份不一致：v80_strict_v61_outer104395303_40f",
        "cv_results_path": (
            "model/v88_strict_v80_v85_cv_blend/cv_results.json"
        ),
        "cv_results_sha256": (
            "1b88a95c5d81c74ddee4f3734fc89a217adcbb4aea6b6887981a07401711cad4"
        ),
        "failed_runner_sha256": (
            "2ac29faf8637c87d3bab6a0cc9617069c1ee12e1fb9ca12b5fcf08e3097f077b"
        ),
        "failed_config_sha256": (
            "2787bf3f69ab105e75745f00d609f5d247a9c69c416945a388eb7abddcc08908"
        ),
    }
    if config.get("failure_confirmation") != expected_failure_confirmation:
        raise ValueError("v88 失败确认合同漂移")
    expected_row_identity = {
        "name": "SHA256_CANONICAL_STR_NEWLINE",
        "value_encoding": "str(value).encode('utf-8')",
        "record_separator_hex": "0a",
        "length_prefix": False,
        "members_must_match_each_other_directly": True,
        "expected_row_identity": {
            "train_rows": 668665,
            "test_rows": 286571,
            "train_id_sha256": (
                "a79741ce666add0e6931e07b0facd43e0ecfe75f2dc0c590101895dd1dac3edf"
            ),
            "test_id_sha256": (
                "c414f5a13bb7853a288e8c7951737caace5abcac135455791d93bb57ed3ef718"
            ),
        },
    }
    if config.get("row_identity_hash_contract") != expected_row_identity:
        raise ValueError("行身份哈希合同漂移")
    if config.get("lineage_contract", {}).get("relationship") != (
        "DISTINCT_MODEL_FAMILIES_NO_PARENT_CHILD_PREDICTION_OVERLAP"
    ):
        raise ValueError("血缘合同漂移")
    if config.get("data_sha256") != {
        "data/train.csv": "eae9eaa4e6378df405e755f853771d7e26d212bd93258349fc797b771021946a",
        "data/test.csv": "539263f6caabc40afd5e2f0bc0ab16b10a2d1177c565fc71b866f0181d836b34",
        "data/sample_submission.csv": "a9747a8b947e4e35505e3da4535a5a494978b012a7adb50973f13e598849dda5",
    }:
        raise ValueError("数据冻结 SHA 合同漂移")


def member_file_records(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = {}
    names = {
        "runner": "runner_sha256",
        "frozen_config.json": "config_sha256",
        "cv_results.json": "cv_results_sha256",
        "sources.json": "sources_sha256",
        "oof_proba.npy": "oof_proba_sha256",
        "test_proba.npy": "test_proba_sha256",
    }
    for member in config["members"]:
        directory = resolve_project_path(member["directory"])
        for filename, hash_key in names.items():
            actual_name = member["runner"] if filename == "runner" else filename
            key = f"{member['experiment_id']}:{actual_name}"
            record = file_record(directory / actual_name)
            if record["sha256"] != member[hash_key]:
                raise ValueError(f"成员来源 SHA 漂移：{key}")
            records[key] = record
    return records


def data_file_records(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = {}
    for relative, expected_hash in config["data_sha256"].items():
        record = file_record(resolve_project_path(relative))
        if record["sha256"] != expected_hash:
            raise ValueError(f"数据 SHA 漂移：{relative}")
        records[relative] = record
    return records


def validate_retry_failure_confirmation(config: dict[str, Any]) -> dict[str, Any]:
    confirmation = config["failure_confirmation"]
    path = resolve_project_path(confirmation["cv_results_path"])
    record = file_record(path)
    if path != V88_RESULTS_PATH.resolve():
        raise ValueError("v88 失败确认路径漂移")
    if record["sha256"] != confirmation["cv_results_sha256"]:
        raise ValueError("v88 失败结果 SHA 漂移")
    result = json.loads(path.read_text(encoding="utf-8"))
    for key in (
        "experiment_id",
        "status",
        "decision",
        "counts_toward_cycle",
        "failure_attribution",
        "error_type",
        "error",
    ):
        if result.get(key) != confirmation[key]:
            raise ValueError(f"v88 失败确认字段漂移：{key}")
    hashes = result.get("code_and_input_hashes", {})
    if (
        hashes.get("runner", {}).get("sha256")
        != confirmation["failed_runner_sha256"]
        or hashes.get("frozen_config", {}).get("sha256")
        != confirmation["failed_config_sha256"]
        or result.get("present_artifacts_are_invalid_for_use") is not True
    ):
        raise ValueError("v88 失败实现或产物治理证据漂移")
    return {
        "cv_results": record,
        "status": result["status"],
        "error_type": result["error_type"],
        "error": result["error"],
        "counts_toward_cycle": result["counts_toward_cycle"],
    }


def member_row_identities(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    identities: dict[str, dict[str, Any]] = {}
    for member in config["members"]:
        path = resolve_project_path(member["directory"]) / "sources.json"
        sources = json.loads(path.read_text(encoding="utf-8"))
        identity = sources.get("row_identity")
        if not isinstance(identity, dict):
            raise ValueError(f"成员缺少 row_identity：{member['experiment_id']}")
        identities[member["experiment_id"]] = identity
    if identities[MEMBER_IDS[0]] != identities[MEMBER_IDS[1]]:
        raise ValueError("两个成员 row_identity 直接比较不一致")
    if (
        identities[MEMBER_IDS[0]]
        != config["row_identity_hash_contract"]["expected_row_identity"]
    ):
        raise ValueError("成员 row_identity 与冻结预期不一致")
    return identities


def code_and_input_hashes(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "runner": file_record(Path(__file__)),
        "frozen_config": file_record(CONFIG_PATH),
        "retry_failure_confirmation": validate_retry_failure_confirmation(config),
        "data": data_file_records(config),
        "members": member_file_records(config),
    }


def audit() -> dict[str, Any]:
    config = load_frozen_config()
    records = code_and_input_hashes(config)
    identities = member_row_identities(config)
    snapshot = candidate_snapshot(config)
    result = {
        "status": "AUDIT_OK_HASH_ONLY_NO_PREDICTION_ARRAYS_LOADED",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "counts_toward_cycle": False,
        "retry_of": config["retry_of"],
        "v88_failure_confirmation": records["retry_failure_confirmation"],
        "member_ids": list(MEMBER_IDS),
        "member_file_records": records["members"],
        "member_row_identity_direct_match": (
            identities[MEMBER_IDS[0]] == identities[MEMBER_IDS[1]]
        ),
        "row_identity_hash_contract": config["row_identity_hash_contract"],
        "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
        "method": config["weight_search"],
        "formal_outputs_created": False,
        "formal_mode_required": "--mode run",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def fit_mid_ecdf(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise ValueError("mid-ECDF fit 输入非法")
    return np.sort(array)


def transform_mid_ecdf(sorted_fit: np.ndarray, values: np.ndarray) -> np.ndarray:
    fitted = np.asarray(sorted_fit, dtype=np.float64)
    array = np.asarray(values, dtype=np.float64)
    if fitted.ndim != 1 or len(fitted) == 0 or not np.isfinite(fitted).all():
        raise ValueError("mid-ECDF fitted state 非法")
    if array.ndim != 1 or not np.isfinite(array).all():
        raise ValueError("mid-ECDF transform 输入非法")
    left = np.searchsorted(fitted, array, side="left")
    right = np.searchsorted(fitted, array, side="right")
    return (left + right).astype(np.float64) / (2.0 * len(fitted))


def select_v85_weight(
    y_train: np.ndarray,
    v80_train: np.ndarray,
    v85_train: np.ndarray,
    tie_tolerance: float = 1e-15,
) -> tuple[float, list[dict[str, float]]]:
    rows = []
    for weight in WEIGHT_GRID:
        prediction = (1.0 - weight) * v80_train + weight * v85_train
        rows.append(
            {
                "v85_weight": weight,
                "v80_weight": 1.0 - weight,
                "meta_train_auc": float(roc_auc_score(y_train, prediction)),
            }
        )

    return choose_v85_weight(rows, tie_tolerance), rows


def choose_v85_weight(
    rows: list[dict[str, float]], tie_tolerance: float = 1e-15
) -> float:
    if len(rows) != len(WEIGHT_GRID):
        raise ValueError("权重搜索结果数量错误")
    best_auc = max(row["meta_train_auc"] for row in rows)
    tied = [
        row
        for row in rows
        if abs(row["meta_train_auc"] - best_auc) <= tie_tolerance
    ]
    selected = min(tied, key=lambda row: (abs(row["v85_weight"] - 0.5), row["v85_weight"]))
    return float(selected["v85_weight"])


def validate_probability(name: str, values: np.ndarray, rows: int) -> None:
    array = np.asarray(values)
    if array.shape != (rows,):
        raise ValueError(f"{name} shape 错误：{array.shape}")
    if not np.issubdtype(array.dtype, np.number) or not np.isfinite(array).all():
        raise ValueError(f"{name} 含非有限或非数值内容")
    if ((array < 0.0) | (array > 1.0)).any():
        raise ValueError(f"{name} 超出 [0,1]")


def meta_splits(y: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    return list(
        StratifiedKFold(
            n_splits=N_META_FOLDS, shuffle=True, random_state=META_SEED
        ).split(np.zeros(len(y)), y)
    )


def run_meta_cv(
    y: np.ndarray,
    v80_oof: np.ndarray,
    v85_oof: np.ndarray,
    v80_test: np.ndarray,
    v85_test: np.ndarray,
    fold_guard: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    validate_probability("v80_oof", v80_oof, len(y))
    validate_probability("v85_oof", v85_oof, len(y))
    if len(v80_test) != len(v85_test):
        raise ValueError("成员 test 长度不一致")
    validate_probability("v80_test", v80_test, len(v80_test))
    validate_probability("v85_test", v85_test, len(v85_test))
    oof = np.zeros(len(y), dtype=np.float64)
    equal_oof = np.zeros(len(y), dtype=np.float64)
    coverage = np.zeros(len(y), dtype=np.int8)
    test_prediction = np.zeros(len(v80_test), dtype=np.float64)
    equal_test = np.zeros(len(v80_test), dtype=np.float64)
    fold_rows = []
    for fold, (train_idx, holdout_idx) in enumerate(meta_splits(y), start=1):
        if coverage[holdout_idx].any():
            raise ValueError("meta holdout coverage 重叠")
        v80_state = fit_mid_ecdf(v80_oof[train_idx])
        v85_state = fit_mid_ecdf(v85_oof[train_idx])
        v80_train_t = transform_mid_ecdf(v80_state, v80_oof[train_idx])
        v85_train_t = transform_mid_ecdf(v85_state, v85_oof[train_idx])
        v80_hold_t = transform_mid_ecdf(v80_state, v80_oof[holdout_idx])
        v85_hold_t = transform_mid_ecdf(v85_state, v85_oof[holdout_idx])
        v80_test_t = transform_mid_ecdf(v80_state, v80_test)
        v85_test_t = transform_mid_ecdf(v85_state, v85_test)
        weight, search_rows = select_v85_weight(
            y[train_idx], v80_train_t, v85_train_t
        )
        hold_prediction = (1.0 - weight) * v80_hold_t + weight * v85_hold_t
        fold_test = (1.0 - weight) * v80_test_t + weight * v85_test_t
        equal_hold = 0.5 * v80_hold_t + 0.5 * v85_hold_t
        equal_fold_test = 0.5 * v80_test_t + 0.5 * v85_test_t
        oof[holdout_idx] = hold_prediction
        equal_oof[holdout_idx] = equal_hold
        coverage[holdout_idx] = 1
        test_prediction += fold_test / N_META_FOLDS
        equal_test += equal_fold_test / N_META_FOLDS
        blend_auc = float(roc_auc_score(y[holdout_idx], hold_prediction))
        equal_auc = float(roc_auc_score(y[holdout_idx], equal_hold))
        v85_auc = float(roc_auc_score(y[holdout_idx], v85_oof[holdout_idx]))
        fold_rows.append(
            {
                "fold": fold,
                "meta_train_rows": len(train_idx),
                "meta_holdout_rows": len(holdout_idx),
                "meta_train_idx_sha256_int64_le": sha256_indices(train_idx),
                "meta_holdout_idx_sha256_int64_le": sha256_indices(holdout_idx),
                "selected_v85_weight": weight,
                "selected_v80_weight": 1.0 - weight,
                "weight_grid_train_auc": search_rows,
                "holdout_blend_auc": blend_auc,
                "holdout_v85_auc": v85_auc,
                "holdout_delta_vs_v85": blend_auc - v85_auc,
                "holdout_equal_weight_auc": equal_auc,
                "holdout_equal_weight_delta_vs_v85": equal_auc - v85_auc,
            }
        )
        if fold_guard is not None:
            fold_guard(fold)
    if not np.all(coverage == 1):
        raise ValueError("meta OOF 未恰好覆盖一次")
    validate_probability("blend_oof", oof, len(y))
    validate_probability("blend_test", test_prediction, len(v80_test))
    return {
        "oof": oof,
        "test": test_prediction,
        "equal_oof": equal_oof,
        "equal_test": equal_test,
        "coverage": coverage,
        "fold_rows": fold_rows,
    }


def finite_spearman(left: np.ndarray, right: np.ndarray, name: str) -> float:
    value = float(spearmanr(left, right).statistic)
    if not np.isfinite(value):
        raise ValueError(f"Spearman 不可计算：{name}")
    return value


def calibration(y: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    clipped = np.clip(prediction, 1e-15, 1.0 - 1e-15)
    return {
        "brier_score": float(brier_score_loss(y, prediction)),
        "log_loss": float(log_loss(y, clipped, labels=[0, 1])),
        "mean_prediction": float(np.mean(prediction)),
        "observed_positive_rate": float(np.mean(y)),
        "calibration_bias": float(np.mean(prediction) - np.mean(y)),
    }


def promotion_decision(
    delta_vs_v85: float, meta_holdout_wins: int, config: dict[str, Any]
) -> str:
    gate = config["promotion_gate"]
    passes = bool(
        delta_vs_v85 >= gate["minimum_oof_delta_vs_best_input"]
        and meta_holdout_wins == gate["required_meta_holdout_wins"]
    )
    return gate["decision_if_pass"] if passes else gate["decision_if_fail"]


def evaluate(
    config: dict[str, Any],
    y: np.ndarray,
    meta: dict[str, Any],
    v80_oof: np.ndarray,
    v85_oof: np.ndarray,
    v80_test: np.ndarray,
    v85_test: np.ndarray,
) -> dict[str, Any]:
    candidate_auc = float(roc_auc_score(y, meta["oof"]))
    v80_auc = float(roc_auc_score(y, v80_oof))
    v85_auc = float(roc_auc_score(y, v85_oof))
    equal_auc = float(roc_auc_score(y, meta["equal_oof"]))
    delta = candidate_auc - v85_auc
    wins = sum(row["holdout_delta_vs_v85"] > 0.0 for row in meta["fold_rows"])
    gate = config["promotion_gate"]
    decision = promotion_decision(delta, wins, config)
    passes = decision == gate["decision_if_pass"]
    return {
        "oof_auc": candidate_auc,
        "v80_oof_auc": v80_auc,
        "v85_oof_auc": v85_auc,
        "oof_delta_vs_best_input_v85": delta,
        "meta_holdout_wins_vs_v85": wins,
        "fixed_equal_weight_control_oof_auc": equal_auc,
        "fixed_equal_weight_control_delta_vs_v85": equal_auc - v85_auc,
        "selected_v85_weights": [
            row["selected_v85_weight"] for row in meta["fold_rows"]
        ],
        "selected_weight_frequency": {
            f"{weight:.2f}": count
            for weight, count in sorted(
                Counter(
                    row["selected_v85_weight"] for row in meta["fold_rows"]
                ).items()
            )
        },
        "correlations": {
            "member_oof_spearman_v80_v85": finite_spearman(
                v80_oof, v85_oof, "v80/v85 OOF"
            ),
            "member_test_spearman_v80_v85": finite_spearman(
                v80_test, v85_test, "v80/v85 test"
            ),
            "blend_oof_spearman_vs_v80": finite_spearman(
                meta["oof"], v80_oof, "blend/v80 OOF"
            ),
            "blend_oof_spearman_vs_v85": finite_spearman(
                meta["oof"], v85_oof, "blend/v85 OOF"
            ),
        },
        "calibration": {
            "primary_blend": calibration(y, meta["oof"]),
            "fixed_equal_weight_control": calibration(y, meta["equal_oof"]),
            "v80": calibration(y, v80_oof),
            "v85": calibration(y, v85_oof),
        },
        "promotion_gate": {
            "minimum_oof_delta_vs_best_input": gate[
                "minimum_oof_delta_vs_best_input"
            ],
            "required_meta_holdout_wins": gate["required_meta_holdout_wins"],
            "observed_oof_delta_vs_best_input": delta,
            "observed_meta_holdout_wins": wins,
            "passes": passes,
        },
        "decision": decision,
    }


def import_member_runner(member: dict[str, Any]) -> ModuleType:
    path = resolve_project_path(member["directory"]) / member["runner"]
    spec = importlib.util.spec_from_file_location(
        f"v89_member_{member['experiment_id']}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法导入成员 verifier：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_member_metadata(member: dict[str, Any]) -> None:
    directory = resolve_project_path(member["directory"])
    module = import_member_runner(member)
    verifier = getattr(module, "verify_complete", None)
    if not callable(verifier):
        raise ValueError(f"成员缺少 verify_complete：{member['experiment_id']}")
    verifier()
    results = json.loads((directory / "cv_results.json").read_text(encoding="utf-8"))
    sources = json.loads((directory / "sources.json").read_text(encoding="utf-8"))
    if (
        results.get("schema_version") != 1
        or results.get("experiment_id") != member["experiment_id"]
        or results.get("status") != member["required_status"]
        or results.get("decision") != member["required_decision"]
        or results.get("model") != member["required_model"]
        or results.get("n_folds") != member["required_n_folds"]
        or results.get("allowed_for_fusion")
        is not member["required_allowed_for_fusion"]
        or results.get("allowed_for_submission") is not False
    ):
        raise ValueError(f"成员结果合同错误：{member['experiment_id']}")
    required_eligibility = member[
        "required_eligible_for_separate_preregistration"
    ]
    if required_eligibility is not None and (
        results.get("eligible_for_separate_preregistration")
        is not required_eligibility
    ):
        raise ValueError(f"成员独立小融合资格错误：{member['experiment_id']}")
    validation = results.get("artifact_validation", {})
    if (
        validation.get("oof_exactly_once_coverage") is not True
        or validation.get("probabilities_finite_and_in_range") is not True
        or validation.get("checkpoint_reconstruction_required") is not True
    ):
        raise ValueError(f"成员原子产物验证错误：{member['experiment_id']}")
    if not np.isclose(
        results.get("oof_auc"), member["required_oof_auc"], atol=1e-15, rtol=0.0
    ):
        raise ValueError(f"成员 OOF 元数据漂移：{member['experiment_id']}")
    if (
        results.get("frozen_config_sha256") != member["config_sha256"]
        or results.get("sources_sha256") != member["sources_sha256"]
        or sources.get("schema_version") != 1
        or sources.get("experiment_id") != member["experiment_id"]
    ):
        raise ValueError(f"成员来源元数据错误：{member['experiment_id']}")
    for key, expected_hash in (
        ("oof_proba", member["oof_proba_sha256"]),
        ("test_proba", member["test_proba_sha256"]),
    ):
        if sources.get("outputs", {}).get(key, {}).get("sha256") != expected_hash:
            raise ValueError(f"成员 sources 输出 SHA 错误：{member['experiment_id']}:{key}")


def load_formal_inputs(
    config: dict[str, Any],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    np.ndarray,
    dict[str, tuple[np.ndarray, np.ndarray]],
]:
    member_file_records(config)
    data_file_records(config)
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[config["id_column"], config["target"]])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[config["id_column"]])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if len(train) != config["expected_train_rows"] or len(test) != config["expected_test_rows"]:
        raise ValueError("数据行数错误")
    if config["target"] in test.columns:
        raise ValueError("测试集含目标列")
    if list(sample.columns) != [config["id_column"], config["target"]]:
        raise ValueError("sample submission schema 错误")
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample/test ID 行序错误")
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    expected_row_identity = {
        "train_rows": len(train),
        "test_rows": len(test),
        "train_id_sha256": sha256_ids(train[config["id_column"]]),
        "test_id_sha256": sha256_ids(test[config["id_column"]]),
    }
    frozen_identities = member_row_identities(config)
    if frozen_identities[MEMBER_IDS[0]] != frozen_identities[MEMBER_IDS[1]]:
        raise ValueError("两个成员 row_identity 直接比较不一致")
    if frozen_identities[MEMBER_IDS[0]] != expected_row_identity:
        raise ValueError("成员 row_identity 与本地 canonical-newline ID 不一致")
    predictions = {}
    for member in config["members"]:
        validate_member_metadata(member)
        directory = resolve_project_path(member["directory"])
        member_sources = json.loads(
            (directory / "sources.json").read_text(encoding="utf-8")
        )
        if member_sources.get("row_identity") != frozen_identities[member["experiment_id"]]:
            raise ValueError(f"成员行身份不一致：{member['experiment_id']}")
        oof = np.load(directory / "oof_proba.npy", allow_pickle=False)
        test_prediction = np.load(directory / "test_proba.npy", allow_pickle=False)
        validate_probability(f"{member['experiment_id']}.oof", oof, len(train))
        validate_probability(
            f"{member['experiment_id']}.test", test_prediction, len(test)
        )
        observed_auc = float(roc_auc_score(y, oof))
        if not np.isclose(
            observed_auc, member["required_oof_auc"], atol=1e-15, rtol=0.0
        ):
            raise ValueError(f"成员 OOF 无法重算：{member['experiment_id']}")
        predictions[member["experiment_id"]] = (
            np.asarray(oof, dtype=np.float64),
            np.asarray(test_prediction, dtype=np.float64),
        )
    return train, test, sample, y, predictions


def candidate_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "immutable": True,
        "counts_toward_cycle": False,
        "retry_of": config["retry_of"],
        "sole_implementation_change": config["sole_implementation_change"],
        "v88_failure_confirmation": validate_retry_failure_confirmation(config),
        "row_identity_hash_contract": config["row_identity_hash_contract"],
        "member_row_identities": member_row_identities(config),
        "runner": file_record(Path(__file__)),
        "frozen_config": file_record(CONFIG_PATH),
        "members": member_file_records(config),
        "member_ids": list(MEMBER_IDS),
    }
    payload["snapshot_sha256"] = sha256_json(payload)
    return payload


def lineage_payload(config: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "counts_toward_cycle": False,
        "retry_of": config["retry_of"],
        "members": [
            {
                "experiment_id": member["experiment_id"],
                "role": member["role"],
                "node_type": "ATOMIC_SINGLE_MODEL",
                "prediction_parent": None,
            }
            for member in config["members"]
        ],
        "relationship": config["lineage_contract"]["relationship"],
        "forbidden_prediction_members": config["forbidden_prediction_members"],
        "parent_child_overlap": False,
        "duplicate_member_ids": False,
    }
    payload["lineage_sha256"] = sha256_json(payload)
    return payload


def meta_folds_payload(y: np.ndarray) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "n_splits": N_META_FOLDS,
        "shuffle": True,
        "random_state": META_SEED,
        "folds": [
            {
                "fold": fold,
                "meta_train_rows": len(train_idx),
                "meta_holdout_rows": len(holdout_idx),
                "meta_train_idx_sha256_int64_le": sha256_indices(train_idx),
                "meta_holdout_idx_sha256_int64_le": sha256_indices(holdout_idx),
            }
            for fold, (train_idx, holdout_idx) in enumerate(meta_splits(y), start=1)
        ],
    }
    payload["meta_folds_sha256"] = sha256_json(payload)
    return payload


def build_sources(
    config: dict[str, Any], train: pd.DataFrame, test: pd.DataFrame
) -> dict[str, Any]:
    output_names = [name for name in MATERIAL_ARTIFACTS if name != "sources.json"]
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "immutable": True,
        "counts_toward_cycle": False,
        "retry_of": config["retry_of"],
        "code_and_inputs": code_and_input_hashes(config),
        "row_identity_hash_contract": config["row_identity_hash_contract"],
        "member_row_identities": member_row_identities(config),
        "row_identity": {
            "train_rows": len(train),
            "test_rows": len(test),
            "train_id_sha256": sha256_ids(train[config["id_column"]]),
            "test_id_sha256": sha256_ids(test[config["id_column"]]),
        },
        "outputs": {
            name: file_record(OUT_DIR / name) for name in output_names
        },
    }


def process_peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return native if platform.system() == "Darwin" else native * 1024


def resource_check(
    config: dict[str, Any], started: float, phase: str, fold: int | None
) -> dict[str, Any]:
    elapsed = time.monotonic() - started
    peak = process_peak_rss_bytes()
    breaches = []
    if elapsed >= config["time_budget_seconds"]:
        breaches.append("WALL_CLOCK_BUDGET")
    if peak > config["peak_rss_budget_bytes"]:
        breaches.append("PEAK_RSS_BUDGET")
    return {
        "timestamp_utc": utc_now(),
        "phase": phase,
        "fold": fold,
        "status": "FAILED" if breaches else "OK",
        "breaches": breaches,
        "wall_elapsed_seconds": elapsed,
        "wall_clock_budget_seconds": config["time_budget_seconds"],
        "peak_rss_bytes": peak,
        "peak_rss_gib": peak / 1024**3,
        "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
        "peak_rss_budget_gib": config["memory_budget_gib"],
    }


def validate_resource_check(config: dict[str, Any], check: dict[str, Any]) -> None:
    expected_keys = {
        "timestamp_utc", "phase", "fold", "status", "breaches",
        "wall_elapsed_seconds", "wall_clock_budget_seconds", "peak_rss_bytes",
        "peak_rss_gib", "peak_rss_budget_bytes", "peak_rss_budget_gib",
    }
    if set(check) != expected_keys:
        raise ValueError("资源 check schema 错误")
    if not isinstance(check["timestamp_utc"], str) or not check["timestamp_utc"]:
        raise ValueError("资源 timestamp 非法")
    if not isinstance(check["phase"], str) or not check["phase"]:
        raise ValueError("资源 phase 非法")
    if check["fold"] is not None and (
        isinstance(check["fold"], bool)
        or not isinstance(check["fold"], int)
        or not 0 <= check["fold"] <= N_META_FOLDS
    ):
        raise ValueError("资源 fold 非法")
    elapsed = check["wall_elapsed_seconds"]
    peak = check["peak_rss_bytes"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not np.isfinite(elapsed)
        or elapsed < 0
    ):
        raise ValueError("资源 elapsed 非法")
    if isinstance(peak, bool) or not isinstance(peak, int) or peak < 0:
        raise ValueError("资源 peak RSS 非法")
    breaches = []
    if elapsed >= config["time_budget_seconds"]:
        breaches.append("WALL_CLOCK_BUDGET")
    if peak > config["peak_rss_budget_bytes"]:
        breaches.append("PEAK_RSS_BUDGET")
    if check["breaches"] != breaches or check["status"] != ("FAILED" if breaches else "OK"):
        raise ValueError("资源 breach/status 无法复算")
    if (
        check["wall_clock_budget_seconds"] != config["time_budget_seconds"]
        or check["peak_rss_budget_bytes"] != config["peak_rss_budget_bytes"]
        or check["peak_rss_budget_gib"] != config["memory_budget_gib"]
        or not np.isclose(check["peak_rss_gib"], peak / 1024**3, atol=1e-12, rtol=0)
    ):
        raise ValueError("资源预算或单位无法复算")


def require_resource_pass(config: dict[str, Any], check: dict[str, Any]) -> None:
    validate_resource_check(config, check)
    if check["breaches"]:
        raise ResourceBudgetExceeded(check)


def failure_inventory(root: Path = OUT_DIR) -> dict[str, Any]:
    expected = list(MATERIAL_ARTIFACTS)
    present = [name for name in expected if (root / name).is_file()]
    return {
        "expected_artifacts": expected,
        "present_artifacts": present,
        "missing_artifacts": [name for name in expected if name not in present],
        "present_artifacts_are_invalid_for_use": True,
    }


def failure_attribution_for(
    config: dict[str, Any], status: str, decision: str
) -> str | None:
    if status == "COMPLETE" and decision in {"PROMOTE", "REJECT"}:
        outcome = f"COMPLETE_{decision}"
    elif status in {"FAILED_RESOURCE_BUDGET", "FAILED_EXCEPTION"}:
        if decision != status:
            raise ValueError("失败状态与 decision 不一致")
        outcome = status
    else:
        raise ValueError("无法归因的终态")
    return config["failure_attribution_contract"][outcome]


def build_failed_result(
    config: dict[str, Any],
    status: str,
    check: dict[str, Any],
    error_type: str,
    error: str,
    root: Path = OUT_DIR,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": False,
        "retry_of": config["retry_of"],
        "model": config["model"],
        "hypothesis": config["hypothesis"],
        "n_folds": N_META_FOLDS,
        "fold_auc": None,
        "params": {
            "meta_cv": config["meta_cv"],
            "transform": config["transform"],
            "weight_search": config["weight_search"],
        },
        "elapsed_seconds": check["wall_elapsed_seconds"],
        "oof_auc": None,
        "base": config["best_input"],
        "base_oof_auc": None,
        "oof_delta_vs_base": None,
        "decision": status,
        "failure_attribution": failure_attribution_for(config, status, status),
        "error_type": error_type,
        "error": error,
        "resource_check": check,
        "code_and_input_hashes": code_and_input_hashes(config),
        "allowed_for_fusion": False,
        "eligible_for_separate_preregistration": False,
        "allowed_for_submission": False,
        "submission_budget": 0,
        **failure_inventory(root),
    }


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


def validate_failed_result(
    results: dict[str, Any], config: dict[str, Any], root: Path = OUT_DIR
) -> None:
    status = results.get("status")
    if status not in {"FAILED_RESOURCE_BUDGET", "FAILED_EXCEPTION"}:
        raise ValueError("失败状态非法")
    check = results.get("resource_check")
    if not isinstance(check, dict):
        raise ValueError("失败状态缺少资源 check")
    validate_resource_check(config, check)
    if status == "FAILED_RESOURCE_BUDGET":
        if not check["breaches"]:
            raise ValueError("资源失败没有预算超限")
        error_type = "ResourceBudgetExceeded"
        error = ",".join(check["breaches"])
    else:
        if check["phase"] != "FAILED_EXCEPTION":
            raise ValueError("异常失败 phase 错误")
        error_type = results.get("error_type")
        error = results.get("error")
        if (
            not isinstance(error_type, str)
            or not error_type
            or not isinstance(error, str)
        ):
            raise ValueError("异常失败信息非法")
    expected_attribution = failure_attribution_for(config, status, status)
    if results.get("failure_attribution") != expected_attribution:
        raise ValueError("失败状态归因不符合冻结合同")
    expected = build_failed_result(config, status, check, error_type, error, root)
    assert_nested_close(results, expected, status)


def build_complete_result(
    config: dict[str, Any],
    meta: dict[str, Any],
    evaluation: dict[str, Any],
    final_resource_check: dict[str, Any],
    sources_sha256: str,
) -> dict[str, Any]:
    decision = evaluation["decision"]
    return {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": False,
        "retry_of": config["retry_of"],
        "model": config["model"],
        "hypothesis": config["hypothesis"],
        "n_folds": N_META_FOLDS,
        "fold_auc": [row["holdout_blend_auc"] for row in meta["fold_rows"]],
        "params": {
            "meta_cv": config["meta_cv"],
            "transform": config["transform"],
            "weight_search": config["weight_search"],
            "fixed_equal_weight_control": config["fixed_equal_weight_control"],
        },
        "elapsed_seconds": final_resource_check["wall_elapsed_seconds"],
        "oof_auc": evaluation["oof_auc"],
        "base": config["best_input"],
        "base_oof_auc": evaluation["v85_oof_auc"],
        "oof_delta_vs_base": evaluation["oof_delta_vs_best_input_v85"],
        "meta_fold_rows": meta["fold_rows"],
        "evaluation": evaluation,
        "decision": decision,
        "failure_attribution": failure_attribution_for(
            config, "COMPLETE", decision
        ),
        "allowed_for_fusion": decision == "PROMOTE",
        "eligible_for_separate_preregistration": False,
        "allowed_for_submission": False,
        "submission_budget": 0,
        "fixed_equal_weight_control_is_diagnostic_only": True,
        "candidate_snapshot_sha256": sha256_file(OUT_DIR / "candidate_snapshot.json"),
        "lineage_sha256": sha256_file(OUT_DIR / "lineage.json"),
        "meta_folds_sha256": sha256_file(OUT_DIR / "meta_folds.json"),
        "sources_sha256": sources_sha256,
        "code_and_input_hashes": code_and_input_hashes(config),
        "artifact_sha256": {
            name: sha256_file(OUT_DIR / name) for name in MATERIAL_ARTIFACTS
        },
        "artifact_validation": {
            "oof_exactly_once_coverage": True,
            "probabilities_finite_and_in_range": True,
            "submission_id_matches_test": True,
            "member_status_and_frozen_verifiers_passed": True,
            "member_hashes_and_sources_passed": True,
            "no_parent_child_or_duplicate_member": True,
            "all_transforms_fit_on_meta_train_only": True,
            "equal_weight_control_not_used_for_selection": True,
        },
        "final_resource_check": final_resource_check,
    }


def validate_complete_result_schema(
    results: dict[str, Any],
    config: dict[str, Any],
    meta: dict[str, Any],
    evaluation: dict[str, Any],
    sources_sha256: str,
    allowed_resource_phases: set[str] | None = None,
) -> None:
    check = results.get("final_resource_check")
    if not isinstance(check, dict):
        raise ValueError("COMPLETE 缺少资源 check")
    validate_resource_check(config, check)
    if check["breaches"]:
        raise ValueError("COMPLETE 含资源超限")
    phases = allowed_resource_phases or {"AFTER_STAGED_VERIFY_PRE_COMPLETE"}
    if check["phase"] not in phases or check["fold"] != N_META_FOLDS:
        raise ValueError("COMPLETE 最终资源 phase/fold 错误")
    expected_attribution = failure_attribution_for(
        config, "COMPLETE", evaluation["decision"]
    )
    if results.get("failure_attribution") != expected_attribution:
        raise ValueError("COMPLETE 归因不符合冻结合同")
    expected = build_complete_result(config, meta, evaluation, check, sources_sha256)
    assert_nested_close(results, expected, "COMPLETE")


def verify_complete_payload(results: dict[str, Any] | None = None) -> dict[str, Any]:
    config = load_frozen_config()
    is_override = results is not None
    if results is None:
        results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    if results.get("status") in {"FAILED_RESOURCE_BUDGET", "FAILED_EXCEPTION"}:
        validate_failed_result(results, config, OUT_DIR)
        return results
    if results.get("status") != "COMPLETE":
        raise ValueError("verify 只接受 COMPLETE 或两类 FAILED")
    train, test, sample, y, predictions = load_formal_inputs(config)
    v80_oof, v80_test = predictions[MEMBER_IDS[0]]
    v85_oof, v85_test = predictions[MEMBER_IDS[1]]
    snapshot = candidate_snapshot(config)
    lineage = lineage_payload(config)
    folds_manifest = meta_folds_payload(y)
    for name, expected in (
        ("candidate_snapshot.json", snapshot),
        ("lineage.json", lineage),
        ("meta_folds.json", folds_manifest),
    ):
        actual = json.loads((OUT_DIR / name).read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError(f"{name} 无法重建")
    meta = run_meta_cv(y, v80_oof, v85_oof, v80_test, v85_test)
    evaluation = evaluate(
        config, y, meta, v80_oof, v85_oof, v80_test, v85_test
    )
    stored_oof = np.load(OUT_DIR / "oof_proba.npy", allow_pickle=False)
    stored_test = np.load(OUT_DIR / "test_proba.npy", allow_pickle=False)
    if not np.array_equal(stored_oof, meta["oof"]):
        raise ValueError("OOF 无法由冻结 meta CV 重建")
    if not np.array_equal(stored_test, meta["test"]):
        raise ValueError("test 无法由冻结 meta CV 重建")
    submission = pd.read_csv(OUT_DIR / "submission.csv")
    if list(submission.columns) != [config["id_column"], config["target"]]:
        raise ValueError("submission schema 错误")
    if (
        not submission[config["id_column"]].equals(test[config["id_column"]])
        or not sample[config["id_column"]].equals(submission[config["id_column"]])
        or not np.allclose(
            submission[config["target"]].to_numpy(np.float64),
            meta["test"],
            atol=1e-15,
            rtol=0.0,
        )
    ):
        raise ValueError("submission 行序或概率错误")
    stored_sources = json.loads((OUT_DIR / "sources.json").read_text(encoding="utf-8"))
    expected_sources = build_sources(config, train, test)
    if stored_sources != expected_sources:
        raise ValueError("sources 无法重建")
    validate_complete_result_schema(
        results,
        config,
        meta,
        evaluation,
        sha256_file(OUT_DIR / "sources.json"),
        (
            {"AFTER_ALL_OUTPUTS", "AFTER_STAGED_VERIFY_PRE_COMPLETE"}
            if is_override
            else {"AFTER_STAGED_VERIFY_PRE_COMPLETE"}
        ),
    )
    return results


def write_failed_result(
    config: dict[str, Any], status: str, check: dict[str, Any], error: Exception
) -> dict[str, Any]:
    error_type = (
        "ResourceBudgetExceeded"
        if status == "FAILED_RESOURCE_BUDGET"
        else type(error).__name__
    )
    message = ",".join(check["breaches"]) if status == "FAILED_RESOURCE_BUDGET" else str(error)
    payload = build_failed_result(config, status, check, error_type, message)
    validate_failed_result(payload, config)
    atomic_write_json(RESULTS_PATH, payload)
    return payload


def run() -> None:
    config = load_frozen_config()
    if RESULTS_PATH.exists():
        verify_complete_payload()
        return
    with LOCK_PATH.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("v89 已有 formal run 持有 flock") from error
        if RESULTS_PATH.exists():
            raise RuntimeError("取得锁后发现 cv_results.json，拒绝重复 formal")
        started = time.monotonic()
        logger = RunLogger()
        pending_results = OUT_DIR / f".cv_results.complete.{os.getpid()}.json"
        try:
            logger.emit(
                "formal retry start; v88 protocol unchanged; "
                "canonical-newline row identity fix only"
            )
            require_resource_pass(
                config, resource_check(config, started, "BEFORE_INPUT_LOAD", None)
            )
            train, test, sample, y, predictions = load_formal_inputs(config)
            require_resource_pass(
                config, resource_check(config, started, "AFTER_INPUT_LOAD", None)
            )
            v80_oof, v80_test = predictions[MEMBER_IDS[0]]
            v85_oof, v85_test = predictions[MEMBER_IDS[1]]

            def guard(fold: int) -> None:
                require_resource_pass(
                    config,
                    resource_check(config, started, "AFTER_META_FOLD", fold),
                )

            meta = run_meta_cv(
                y, v80_oof, v85_oof, v80_test, v85_test, fold_guard=guard
            )
            evaluation = evaluate(
                config, y, meta, v80_oof, v85_oof, v80_test, v85_test
            )
            write_immutable_json(
                OUT_DIR / "candidate_snapshot.json", candidate_snapshot(config)
            )
            write_immutable_json(OUT_DIR / "lineage.json", lineage_payload(config))
            write_immutable_json(
                OUT_DIR / "meta_folds.json", meta_folds_payload(y)
            )
            atomic_save_npy(OUT_DIR / "oof_proba.npy", meta["oof"])
            atomic_save_npy(OUT_DIR / "test_proba.npy", meta["test"])
            submission = sample.copy()
            submission[config["target"]] = meta["test"]
            atomic_write_csv(OUT_DIR / "submission.csv", submission)
            logger.emit(
                f"meta CV complete oof={evaluation['oof_auc']:.9f} "
                f"delta_vs_v85={evaluation['oof_delta_vs_best_input_v85']:+.9f} "
                f"wins={evaluation['meta_holdout_wins_vs_v85']}/5 "
                f"decision={evaluation['decision']}"
            )
            after_outputs = resource_check(
                config, started, "AFTER_ALL_OUTPUTS", N_META_FOLDS
            )
            require_resource_pass(config, after_outputs)
            sources = build_sources(config, train, test)
            write_immutable_json(OUT_DIR / "sources.json", sources)
            sources_sha = sha256_file(OUT_DIR / "sources.json")
            results = build_complete_result(
                config, meta, evaluation, after_outputs, sources_sha
            )
            verify_complete_payload(results)
            after_verify = resource_check(
                config, started, "AFTER_STAGED_VERIFY_PRE_COMPLETE", N_META_FOLDS
            )
            require_resource_pass(config, after_verify)
            results = build_complete_result(
                config, meta, evaluation, after_verify, sources_sha
            )
            validate_complete_result_schema(
                results, config, meta, evaluation, sources_sha
            )
            _atomic_bytes(
                pending_results,
                (json.dumps(results, ensure_ascii=False, indent=2) + "\n").encode(
                    "utf-8"
                ),
            )
            require_resource_pass(
                config,
                resource_check(
                    config, started, "COMPLETE_RESULT_STAGED", N_META_FOLDS
                ),
            )
            os.replace(pending_results, RESULTS_PATH)
            final_scope = resource_check(
                config, started, "FORMAL_SCOPE_COMPLETE", N_META_FOLDS
            )
            if final_scope["breaches"]:
                write_failed_result(
                    config,
                    "FAILED_RESOURCE_BUDGET",
                    final_scope,
                    ResourceBudgetExceeded(final_scope),
                )
                return
            print(
                json.dumps(
                    {
                        "status": "COMPLETE_AND_VERIFIED",
                        "experiment_id": EXPERIMENT_ID,
                        "oof_auc": evaluation["oof_auc"],
                        "delta_vs_v85": evaluation[
                            "oof_delta_vs_best_input_v85"
                        ],
                        "meta_holdout_wins": evaluation[
                            "meta_holdout_wins_vs_v85"
                        ],
                        "decision": evaluation["decision"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        except ResourceBudgetExceeded as error:
            failure = write_failed_result(
                config, "FAILED_RESOURCE_BUDGET", error.check, error
            )
            print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
        except Exception as error:
            check = resource_check(config, started, "FAILED_EXCEPTION", None)
            failure = write_failed_result(config, "FAILED_EXCEPTION", check, error)
            print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
            raise
        finally:
            if pending_results.exists():
                pending_results.unlink()


def smoke() -> dict[str, Any]:
    config = load_frozen_config()
    member_file_records(config)
    failure_confirmation = validate_retry_failure_confirmation(config)
    identities = member_row_identities(config)
    y = np.tile(np.array([0, 1], dtype=np.int8), 50)
    base = np.linspace(0.05, 0.95, len(y))
    v80 = np.clip(0.15 + 0.65 * y + 0.04 * base, 0, 1)
    v85 = np.clip(0.12 + 0.70 * y + 0.03 * base[::-1], 0, 1)
    v80_test = np.linspace(0.05, 0.95, 31)
    v85_test = np.linspace(0.95, 0.05, 31)
    meta = run_meta_cv(y, v80, v85, v80_test, v85_test)
    evaluation = evaluate(config, y, meta, v80, v85, v80_test, v85_test)
    if not np.all(meta["coverage"] == 1):
        raise AssertionError("smoke coverage 失败")
    if any(row["selected_v85_weight"] not in WEIGHT_GRID for row in meta["fold_rows"]):
        raise AssertionError("smoke 权重不在冻结网格")
    result = {
        "status": "SMOKE_OK_SYNTHETIC_ONLY_NO_REAL_PREDICTIONS_LOADED",
        "experiment_id": EXPERIMENT_ID,
        "counts_toward_cycle": False,
        "retry_of": config["retry_of"],
        "v88_failure_confirmation_verified": (
            failure_confirmation["status"] == "FAILED_EXCEPTION"
        ),
        "canonical_newline_id_hash_verified": (
            sha256_ids(pd.Series([1, "two"]))
            == hashlib.sha256(b"1\ntwo\n").hexdigest()
        ),
        "member_row_identity_direct_match": (
            identities[MEMBER_IDS[0]] == identities[MEMBER_IDS[1]]
        ),
        "meta_fold_count": len(meta["fold_rows"]),
        "fit_only_mid_ecdf": True,
        "weight_grid_and_tie_break": True,
        "equal_weight_control_diagnostic_only": True,
        "promotion_gate_exercised": evaluation["decision"] in {"PROMOTE", "REJECT"},
        "failure_attribution_contract_exercised": (
            failure_attribution_for(config, "COMPLETE", "PROMOTE") is None
            and isinstance(
                failure_attribution_for(config, "COMPLETE", "REJECT"), str
            )
            and isinstance(
                failure_attribution_for(
                    config,
                    "FAILED_RESOURCE_BUDGET",
                    "FAILED_RESOURCE_BUDGET",
                ),
                str,
            )
            and isinstance(
                failure_attribution_for(
                    config, "FAILED_EXCEPTION", "FAILED_EXCEPTION"
                ),
                str,
            )
        ),
        "formal_outputs_created": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("audit", "smoke", "run", "verify"), default="audit"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "audit":
        audit()
    elif args.mode == "smoke":
        smoke()
    elif args.mode == "run":
        run()
    else:
        result = verify_complete_payload()
        print(
            json.dumps(
                {
                    "status": f"{result['status']}_VERIFIED",
                    "experiment_id": EXPERIMENT_ID,
                    "decision": result["decision"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
