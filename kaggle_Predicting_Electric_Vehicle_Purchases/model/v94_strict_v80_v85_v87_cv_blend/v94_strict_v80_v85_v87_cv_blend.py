#!/usr/bin/env python3
"""v94: strict v80/v85/v87 cross-fitted small blend.

The default mode is a hash-only audit. Real prediction arrays are read only by
an explicit ``--mode run`` or ``--mode verify`` invocation.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold


EXPERIMENT_ID = "v94_strict_v80_v85_v87_cv_blend"
MEMBER_IDS = (
    "v80_strict_v61_outer104395303_40f",
    "v85_naji_v74_40f",
    "v87_strict_v80_commute_charging_burden_40f",
)
BASELINE_ID = "v90_v89_member_verify_budget_retry"
OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
RESULTS_PATH = OUT_DIR / "cv_results.json"
LOCK_PATH = OUT_DIR / "run.lock"
LOG_PATH = OUT_DIR / "train_log.txt"
N_META_FOLDS = 5
META_SEED = 42
WEIGHT_UNITS = 20
WEIGHT_STEP = 0.05
V90_WEIGHT_GRID = tuple(round(unit * WEIGHT_STEP, 2) for unit in range(21))
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
FAILED_SEALED_ARCHIVE_NAME = "sealed_complete.invalid.json"
FAILURE_ONLY_ARTIFACTS = (FAILED_SEALED_ARCHIVE_NAME,)
RESOURCE_PHASE_FOLD_POLICY: dict[str, set[int | None]] = {
    "BEFORE_INPUT_LOAD": {None},
    "AFTER_INPUT_LOAD": {None},
    "AFTER_META_FOLD": set(range(1, N_META_FOLDS + 1)),
    "AFTER_ALL_OUTPUTS": {N_META_FOLDS},
    "AFTER_STAGED_VERIFY_PRE_COMPLETE": {N_META_FOLDS},
    "PRE_COMMIT_AFTER_FINAL_FILE_VERIFY": {N_META_FOLDS},
    "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY": {N_META_FOLDS},
    "POST_SEAL_COMMIT_GUARD": {N_META_FOLDS},
    "FAILED_EXCEPTION": set(range(0, N_META_FOLDS + 1)),
}


class ResourceBudgetExceeded(RuntimeError):
    def __init__(
        self,
        check: dict[str, Any],
        sealed_archive_provenance: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(",".join(check["breaches"]))
        self.check = check
        self.sealed_archive_provenance = sealed_archive_provenance


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
        "cycle_position": 12,
        "experiment_type": "SMALL_BLEND",
        "counts_toward_cycle_when_formally_closed": True,
        "competition": "playground-series-s6e9",
        "model": (
            "five-fold cross-fitted fit-only mid-ECDF nonnegative simplex "
            "blend of atomic v80, v85, and v87"
        ),
        "unique_primary_question": (
            "does the frozen v87 infrastructure representation add "
            "reproducible marginal signal beyond strict best v90 without "
            "changing any base model"
        ),
        "target": "Will_Buy_EV",
        "positive_label": "Yes",
        "id_column": "id",
        "expected_train_rows": 668665,
        "expected_test_rows": 286571,
        "base": BASELINE_ID,
        "base_oof_auc": 0.9463720745765888,
        "time_budget_seconds": 900,
        "peak_rss_budget_bytes": 12 * 1024**3,
        "memory_budget_gib": 12,
        "cpu_threads": 1,
        "submission_budget": 0,
        "formal_mode": "--mode run",
        "audit_prediction_access": "HASH_ONLY_NO_ARRAY_LOAD",
        "complete_commit_protocol": "STAGED_VERIFY_THEN_ATOMIC_COMPLETE",
        "failed_artifacts_invalid_for_use": True,
    }
    for key, expected in expected_scalars.items():
        if config.get(key) != expected:
            raise ValueError(f"冻结配置 {key} 漂移")

    members = config.get("members")
    if not isinstance(members, list) or len(members) != 3:
        raise ValueError("v94 必须恰好有三个原子成员")
    if tuple(member.get("experiment_id") for member in members) != MEMBER_IDS:
        raise ValueError("成员 ID 或顺序漂移")
    if len({member["experiment_id"] for member in members}) != 3:
        raise ValueError("成员重复")
    if any(member.get("prediction_parent") is not None for member in members):
        raise ValueError("v94 只允许原子预测成员")
    if any(member.get("required_status") != "COMPLETE" for member in members):
        raise ValueError("成员必须正式关闭")
    if any(member.get("required_n_folds") != 40 for member in members):
        raise ValueError("成员必须为冻结 40 折结果")

    baseline = config.get("strict_baseline")
    if not isinstance(baseline, dict) or baseline.get("experiment_id") != BASELINE_ID:
        raise ValueError("strict baseline 漂移")
    if baseline.get("role") != "COMPARISON_ONLY_NOT_A_MEMBER":
        raise ValueError("v90 只能作为对照")
    if baseline["experiment_id"] in MEMBER_IDS:
        raise ValueError("v90 不得同时作为成员")
    for entry in [*members, baseline]:
        required_hashes = (
            "runner_sha256",
            "config_sha256",
            "cv_results_sha256",
            "sources_sha256",
            "oof_proba_sha256",
            "test_proba_sha256",
        )
        if any(len(str(entry.get(key, ""))) != 64 for key in required_hashes):
            raise ValueError(f"来源 SHA 合同不完整：{entry.get('experiment_id')}")

    if config.get("meta_cv") != {
        "n_splits": 5,
        "shuffle": True,
        "random_state": 42,
        "selection_scope": "each meta-train only",
        "holdout_role": "evaluation only",
    }:
        raise ValueError("meta CV 合同漂移")
    transform = config.get("transform", {})
    if (
        transform.get("name") != "FIT_ONLY_MID_ECDF"
        or transform.get("full_oof_fit_forbidden") is not True
        or transform.get("fit_scope")
        != "separately per member inside each meta-train"
    ):
        raise ValueError("mid-ECDF 合同漂移")
    search = config.get("weight_search", {})
    if (
        tuple(search.get("members_in_order", [])) != MEMBER_IDS
        or search.get("simplex_step") != WEIGHT_STEP
        or search.get("simplex_units") != WEIGHT_UNITS
        or search.get("candidate_count") != 231
        or search.get("objective") != "meta_train_roc_auc"
        or search.get("tie_tolerance") != 1e-15
        or search.get("member_selection") != "NONE"
    ):
        raise ValueError("simplex 权重合同漂移")
    reconstruction = config.get("baseline_reconstruction", {})
    if (
        tuple(reconstruction.get("v85_weight_grid", [])) != V90_WEIGHT_GRID
        or reconstruction.get("must_match_stored_v90_oof_elementwise") is not True
        or reconstruction.get("must_match_stored_v90_test_elementwise") is not True
        or reconstruction.get("absolute_tolerance") != 1e-12
    ):
        raise ValueError("v90 重建合同漂移")
    if config.get("promotion_gate") != {
        "minimum_oof_delta_vs_base": 0.0001,
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
            "PREREGISTERED_PROMOTION_GATE_NOT_MET__DELTA_VS_V90_BELOW_"
            "0.0001_OR_META_HOLDOUT_WINS_BELOW_5_OF_5"
        ),
        "FAILED_RESOURCE_BUDGET": "RESOURCE_BUDGET_EXCEEDED",
        "FAILED_EXCEPTION": "IMPLEMENTATION_OR_RUNTIME_EXCEPTION",
    }:
        raise ValueError("失败归因合同漂移")
    row_contract = config.get("row_identity_hash_contract", {})
    if (
        row_contract.get("name") != "SHA256_CANONICAL_STR_NEWLINE"
        or row_contract.get("members_and_baseline_must_match_each_other_directly")
        is not True
    ):
        raise ValueError("行身份合同漂移")
    if config.get("data_sha256") != {
        "data/train.csv": (
            "eae9eaa4e6378df405e755f853771d7e26d212bd93258349fc797b771021946a"
        ),
        "data/test.csv": (
            "539263f6caabc40afd5e2f0bc0ab16b10a2d1177c565fc71b866f0181d836b34"
        ),
        "data/sample_submission.csv": (
            "a9747a8b947e4e35505e3da4535a5a494978b012a7adb50973f13e598849dda5"
        ),
    }:
        raise ValueError("数据冻结 SHA 合同漂移")


def source_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [*config["members"], config["strict_baseline"]]


def source_file_records(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    names = {
        "runner": "runner_sha256",
        "frozen_config.json": "config_sha256",
        "cv_results.json": "cv_results_sha256",
        "sources.json": "sources_sha256",
        "oof_proba.npy": "oof_proba_sha256",
        "test_proba.npy": "test_proba_sha256",
    }
    for source in source_entries(config):
        directory = resolve_project_path(source["directory"])
        for filename, hash_key in names.items():
            actual_name = source["runner"] if filename == "runner" else filename
            key = f"{source['experiment_id']}:{actual_name}"
            record = file_record(directory / actual_name)
            if record["sha256"] != source[hash_key]:
                raise ValueError(f"来源 SHA 漂移：{key}")
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


def source_row_identities(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    identities: dict[str, dict[str, Any]] = {}
    for source in source_entries(config):
        path = resolve_project_path(source["directory"]) / "sources.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        identity = payload.get("row_identity")
        if not isinstance(identity, dict):
            raise ValueError(f"来源缺少 row_identity：{source['experiment_id']}")
        identities[source["experiment_id"]] = identity
    expected = config["row_identity_hash_contract"]["expected_row_identity"]
    if any(identity != expected for identity in identities.values()):
        raise ValueError("来源 row_identity 未直接匹配冻结预期")
    return identities


def source_result_metadata(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for source in source_entries(config):
        path = resolve_project_path(source["directory"]) / "cv_results.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        required = {
            "status": source["required_status"],
            "decision": source["required_decision"],
            "model": source["required_model"],
            "allowed_for_fusion": source["required_allowed_for_fusion"],
        }
        if "required_n_folds" in source:
            required["n_folds"] = source["required_n_folds"]
        if "required_eligible_for_separate_preregistration" in source:
            required["eligible_for_separate_preregistration"] = source[
                "required_eligible_for_separate_preregistration"
            ]
        for key, expected in required.items():
            if payload.get(key) != expected:
                raise ValueError(f"来源结果合同漂移：{source['experiment_id']}:{key}")
        if not np.isclose(
            payload.get("oof_auc"), source["required_oof_auc"], atol=1e-15, rtol=0.0
        ):
            raise ValueError(f"来源 OOF 漂移：{source['experiment_id']}")
        metadata[source["experiment_id"]] = {
            "status": payload["status"],
            "decision": payload["decision"],
            "model": payload["model"],
            "oof_auc": payload["oof_auc"],
        }
    return metadata


def code_and_input_hashes(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "runner": file_record(Path(__file__)),
        "frozen_config": file_record(CONFIG_PATH),
        "data": data_file_records(config),
        "sources": source_file_records(config),
    }


def candidate_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "status": config["status"],
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle_when_formally_closed": True,
        "hypothesis": config["hypothesis"],
        "unique_primary_question": config["unique_primary_question"],
        "member_ids": list(MEMBER_IDS),
        "strict_baseline": BASELINE_ID,
        "meta_cv": config["meta_cv"],
        "transform": config["transform"],
        "weight_search": config["weight_search"],
        "promotion_gate": config["promotion_gate"],
        "submission_budget": 0,
        "config_sha256": sha256_file(CONFIG_PATH),
        "runner_sha256": sha256_file(Path(__file__)),
        "source_file_records": source_file_records(config),
    }
    payload["snapshot_sha256"] = sha256_json(payload)
    return payload


def audit() -> dict[str, Any]:
    config = load_frozen_config()
    records = code_and_input_hashes(config)
    identities = source_row_identities(config)
    metadata = source_result_metadata(config)
    snapshot = candidate_snapshot(config)
    result = {
        "status": "AUDIT_OK_HASH_ONLY_NO_PREDICTION_ARRAYS_READ",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": "C01",
        "cycle_position": config["cycle_position"],
        "counts_toward_cycle_when_formally_closed": True,
        "member_ids": list(MEMBER_IDS),
        "strict_baseline": BASELINE_ID,
        "source_file_records": records["sources"],
        "source_result_metadata": metadata,
        "source_row_identities": identities,
        "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
        "simplex_candidate_count": len(simplex_grid()),
        "formal_outputs_created": False,
        "formal_mode_required": "--mode run",
        "prediction_access": "NO_PREDICTION_ARRAYS_READ",
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


def choose_v85_weight(
    rows: list[dict[str, float]], tie_tolerance: float = 1e-15
) -> float:
    if len(rows) != len(V90_WEIGHT_GRID):
        raise ValueError("v90 权重搜索结果数量错误")
    best_auc = max(row["meta_train_auc"] for row in rows)
    tied = [
        row
        for row in rows
        if abs(row["meta_train_auc"] - best_auc) <= tie_tolerance
    ]
    selected = min(
        tied,
        key=lambda row: (
            abs(row["v85_weight"] - 0.5),
            row["v85_weight"],
        ),
    )
    return float(selected["v85_weight"])


def select_v85_weight(
    y_train: np.ndarray,
    v80_train: np.ndarray,
    v85_train: np.ndarray,
    tie_tolerance: float = 1e-15,
) -> tuple[float, list[dict[str, float]]]:
    rows = []
    for weight in V90_WEIGHT_GRID:
        prediction = (1.0 - weight) * v80_train + weight * v85_train
        rows.append(
            {
                "v85_weight": weight,
                "v80_weight": 1.0 - weight,
                "meta_train_auc": float(roc_auc_score(y_train, prediction)),
            }
        )
    return choose_v85_weight(rows, tie_tolerance), rows


def simplex_grid() -> tuple[tuple[float, float, float], ...]:
    weights = []
    for v80_units in range(WEIGHT_UNITS + 1):
        for v85_units in range(WEIGHT_UNITS - v80_units + 1):
            v87_units = WEIGHT_UNITS - v80_units - v85_units
            weights.append(
                (
                    v80_units / WEIGHT_UNITS,
                    v85_units / WEIGHT_UNITS,
                    v87_units / WEIGHT_UNITS,
                )
            )
    return tuple(weights)


def choose_three_weights(
    rows: list[dict[str, float]],
    baseline_weights: tuple[float, float, float],
    tie_tolerance: float = 1e-15,
) -> tuple[float, float, float]:
    if len(rows) != 231:
        raise ValueError("三成员 simplex 搜索结果数量错误")
    best_auc = max(row["meta_train_auc"] for row in rows)
    tied = [
        row
        for row in rows
        if abs(row["meta_train_auc"] - best_auc) <= tie_tolerance
    ]

    def tie_key(row: dict[str, float]) -> tuple[float, float, float, float]:
        weights = (row["v80_weight"], row["v85_weight"], row["v87_weight"])
        l1 = sum(
            abs(value - base) for value, base in zip(weights, baseline_weights)
        )
        return (
            l1,
            row["v87_weight"],
            abs(row["v85_weight"] - 0.5),
            row["v85_weight"],
        )

    selected = min(tied, key=tie_key)
    return (
        float(selected["v80_weight"]),
        float(selected["v85_weight"]),
        float(selected["v87_weight"]),
    )


def select_three_weights(
    y_train: np.ndarray,
    transformed_train: dict[str, np.ndarray],
    baseline_weights: tuple[float, float, float],
    tie_tolerance: float = 1e-15,
) -> tuple[tuple[float, float, float], list[dict[str, float]]]:
    rows = []
    for v80_weight, v85_weight, v87_weight in simplex_grid():
        prediction = (
            v80_weight * transformed_train[MEMBER_IDS[0]]
            + v85_weight * transformed_train[MEMBER_IDS[1]]
            + v87_weight * transformed_train[MEMBER_IDS[2]]
        )
        rows.append(
            {
                "v80_weight": v80_weight,
                "v85_weight": v85_weight,
                "v87_weight": v87_weight,
                "meta_train_auc": float(roc_auc_score(y_train, prediction)),
            }
        )
    return choose_three_weights(rows, baseline_weights, tie_tolerance), rows


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


def weighted_prediction(
    arrays: dict[str, np.ndarray], weights: tuple[float, float, float]
) -> np.ndarray:
    return sum(
        weight * arrays[member_id]
        for member_id, weight in zip(MEMBER_IDS, weights)
    )


def run_meta_cv(
    y: np.ndarray,
    member_oof: dict[str, np.ndarray],
    member_test: dict[str, np.ndarray],
    fold_guard: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    if set(member_oof) != set(MEMBER_IDS) or set(member_test) != set(MEMBER_IDS):
        raise ValueError("成员预测集合漂移")
    test_rows = len(member_test[MEMBER_IDS[0]])
    for member_id in MEMBER_IDS:
        validate_probability(f"{member_id}:oof", member_oof[member_id], len(y))
        validate_probability(f"{member_id}:test", member_test[member_id], test_rows)

    oof = np.zeros(len(y), dtype=np.float64)
    baseline_oof = np.zeros(len(y), dtype=np.float64)
    equal_oof = np.zeros(len(y), dtype=np.float64)
    test_prediction = np.zeros(test_rows, dtype=np.float64)
    baseline_test = np.zeros(test_rows, dtype=np.float64)
    equal_test = np.zeros(test_rows, dtype=np.float64)
    coverage = np.zeros(len(y), dtype=np.int8)
    fold_rows: list[dict[str, Any]] = []

    for fold, (train_idx, holdout_idx) in enumerate(meta_splits(y), start=1):
        if coverage[holdout_idx].any():
            raise ValueError("meta holdout coverage 重叠")
        train_t: dict[str, np.ndarray] = {}
        hold_t: dict[str, np.ndarray] = {}
        test_t: dict[str, np.ndarray] = {}
        for member_id in MEMBER_IDS:
            state = fit_mid_ecdf(member_oof[member_id][train_idx])
            train_t[member_id] = transform_mid_ecdf(
                state, member_oof[member_id][train_idx]
            )
            hold_t[member_id] = transform_mid_ecdf(
                state, member_oof[member_id][holdout_idx]
            )
            test_t[member_id] = transform_mid_ecdf(state, member_test[member_id])

        baseline_v85_weight, baseline_search = select_v85_weight(
            y[train_idx], train_t[MEMBER_IDS[0]], train_t[MEMBER_IDS[1]]
        )
        baseline_weights = (
            1.0 - baseline_v85_weight,
            baseline_v85_weight,
            0.0,
        )
        selected_weights, search_rows = select_three_weights(
            y[train_idx], train_t, baseline_weights
        )
        hold_prediction = weighted_prediction(hold_t, selected_weights)
        fold_test = weighted_prediction(test_t, selected_weights)
        baseline_hold = weighted_prediction(hold_t, baseline_weights)
        baseline_fold_test = weighted_prediction(test_t, baseline_weights)
        equal_weights = (1.0 / 3.0,) * 3
        equal_hold = weighted_prediction(hold_t, equal_weights)
        equal_fold_test = weighted_prediction(test_t, equal_weights)

        oof[holdout_idx] = hold_prediction
        baseline_oof[holdout_idx] = baseline_hold
        equal_oof[holdout_idx] = equal_hold
        coverage[holdout_idx] = 1
        test_prediction += fold_test / N_META_FOLDS
        baseline_test += baseline_fold_test / N_META_FOLDS
        equal_test += equal_fold_test / N_META_FOLDS
        blend_auc = float(roc_auc_score(y[holdout_idx], hold_prediction))
        baseline_auc = float(roc_auc_score(y[holdout_idx], baseline_hold))
        equal_auc = float(roc_auc_score(y[holdout_idx], equal_hold))
        fold_rows.append(
            {
                "fold": fold,
                "meta_train_rows": len(train_idx),
                "meta_holdout_rows": len(holdout_idx),
                "meta_train_idx_sha256_int64_le": sha256_indices(train_idx),
                "meta_holdout_idx_sha256_int64_le": sha256_indices(holdout_idx),
                "baseline_v90_weights": {
                    "v80": baseline_weights[0],
                    "v85": baseline_weights[1],
                    "v87": baseline_weights[2],
                },
                "selected_weights": {
                    "v80": selected_weights[0],
                    "v85": selected_weights[1],
                    "v87": selected_weights[2],
                },
                "baseline_weight_grid_train_auc": baseline_search,
                "simplex_weight_grid_train_auc": search_rows,
                "holdout_blend_auc": blend_auc,
                "holdout_v90_auc": baseline_auc,
                "holdout_delta_vs_v90": blend_auc - baseline_auc,
                "holdout_equal_weight_auc": equal_auc,
                "holdout_equal_weight_delta_vs_v90": equal_auc - baseline_auc,
            }
        )
        if fold_guard is not None:
            fold_guard(fold)

    if not np.all(coverage == 1):
        raise ValueError("meta OOF 未恰好覆盖一次")
    for name, values, rows in (
        ("blend_oof", oof, len(y)),
        ("blend_test", test_prediction, test_rows),
        ("baseline_oof", baseline_oof, len(y)),
        ("baseline_test", baseline_test, test_rows),
        ("equal_oof", equal_oof, len(y)),
        ("equal_test", equal_test, test_rows),
    ):
        validate_probability(name, values, rows)
    return {
        "oof": oof,
        "test": test_prediction,
        "baseline_oof": baseline_oof,
        "baseline_test": baseline_test,
        "equal_oof": equal_oof,
        "equal_test": equal_test,
        "coverage": coverage,
        "fold_rows": fold_rows,
    }


def assert_baseline_reconstruction(
    config: dict[str, Any],
    meta: dict[str, Any],
    stored_baseline_oof: np.ndarray,
    stored_baseline_test: np.ndarray,
) -> None:
    tolerance = config["baseline_reconstruction"]["absolute_tolerance"]
    validate_probability("stored_v90_oof", stored_baseline_oof, len(meta["oof"]))
    validate_probability("stored_v90_test", stored_baseline_test, len(meta["test"]))
    if not np.allclose(
        meta["baseline_oof"], stored_baseline_oof, atol=tolerance, rtol=0.0
    ):
        raise ValueError("独立重建 v90 OOF 与冻结数组不一致")
    if not np.allclose(
        meta["baseline_test"], stored_baseline_test, atol=tolerance, rtol=0.0
    ):
        raise ValueError("独立重建 v90 test 与冻结数组不一致")


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
    delta_vs_base: float, meta_holdout_wins: int, config: dict[str, Any]
) -> str:
    gate = config["promotion_gate"]
    passes = bool(
        delta_vs_base >= gate["minimum_oof_delta_vs_base"]
        and meta_holdout_wins == gate["required_meta_holdout_wins"]
    )
    return gate["decision_if_pass"] if passes else gate["decision_if_fail"]


def evaluate(
    config: dict[str, Any],
    y: np.ndarray,
    meta: dict[str, Any],
    member_oof: dict[str, np.ndarray],
    member_test: dict[str, np.ndarray],
) -> dict[str, Any]:
    oof_auc = float(roc_auc_score(y, meta["oof"]))
    base_auc = float(roc_auc_score(y, meta["baseline_oof"]))
    equal_auc = float(roc_auc_score(y, meta["equal_oof"]))
    if not np.isclose(base_auc, config["base_oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("重建 v90 AUC 与冻结基准不一致")
    delta = oof_auc - base_auc
    wins = sum(row["holdout_delta_vs_v90"] > 0.0 for row in meta["fold_rows"])
    decision = promotion_decision(delta, wins, config)
    selected = [row["selected_weights"] for row in meta["fold_rows"]]
    return {
        "oof_auc": oof_auc,
        "base": BASELINE_ID,
        "base_oof_auc": base_auc,
        "oof_delta_vs_base": delta,
        "meta_holdout_wins_vs_base": wins,
        "meta_holdout_fold_count": N_META_FOLDS,
        "all_meta_holdout_deltas_strictly_positive": wins == N_META_FOLDS,
        "decision": decision,
        "selected_weights_by_fold": selected,
        "v87_positive_weight_fold_count": sum(row["v87"] > 0.0 for row in selected),
        "v87_zero_weight_fold_count": sum(row["v87"] == 0.0 for row in selected),
        "equal_weight_control": {
            "oof_auc": equal_auc,
            "oof_delta_vs_base": equal_auc - base_auc,
            "diagnostic_only": True,
        },
        "oof_spearman": {
            member_id: finite_spearman(
                meta["oof"], member_oof[member_id], f"oof:{member_id}"
            )
            for member_id in MEMBER_IDS
        }
        | {
            "v90": finite_spearman(
                meta["oof"], meta["baseline_oof"], "oof:v90"
            )
        },
        "test_spearman": {
            member_id: finite_spearman(
                meta["test"], member_test[member_id], f"test:{member_id}"
            )
            for member_id in MEMBER_IDS
        }
        | {
            "v90": finite_spearman(
                meta["test"], meta["baseline_test"], "test:v90"
            )
        },
        "calibration": calibration(y, meta["oof"]),
        "baseline_reconstruction": {
            "oof_elementwise_match": True,
            "test_elementwise_match": True,
            "absolute_tolerance": config["baseline_reconstruction"][
                "absolute_tolerance"
            ],
        },
    }


def import_source_runner(source: dict[str, Any]) -> ModuleType:
    path = resolve_project_path(source["directory"]) / source["runner"]
    name = f"_v94_source_{source['experiment_id']}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法导入来源 runner：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_source_complete(source: dict[str, Any]) -> dict[str, Any]:
    module = import_source_runner(source)
    verifier = getattr(module, "verify_complete_payload", None)
    if not callable(verifier):
        raise ValueError(f"来源缺少 verify_complete_payload：{source['experiment_id']}")
    result = verifier()
    if result.get("status") != source["required_status"]:
        raise ValueError(f"来源 verifier 状态错误：{source['experiment_id']}")
    return result


def load_formal_inputs(
    config: dict[str, Any],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    np.ndarray,
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    np.ndarray,
    np.ndarray,
]:
    source_file_records(config)
    source_row_identities(config)
    source_result_metadata(config)
    for source in source_entries(config):
        verify_source_complete(source)

    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if (
        len(train) != config["expected_train_rows"]
        or len(test) != config["expected_test_rows"]
    ):
        raise ValueError("数据行数漂移")
    if (
        config["target"] not in train
        or config["id_column"] not in train
        or config["id_column"] not in test
    ):
        raise ValueError("数据 schema 漂移")
    y = train[config["target"]].map({"No": 0, "Yes": 1})
    if y.isna().any() or set(y.unique()) != {0, 1}:
        raise ValueError("目标标签映射漂移")
    expected_identity = config["row_identity_hash_contract"]["expected_row_identity"]
    actual_identity = {
        "train_rows": len(train),
        "test_rows": len(test),
        "train_id_sha256": sha256_ids(train[config["id_column"]]),
        "test_id_sha256": sha256_ids(test[config["id_column"]]),
    }
    if actual_identity != expected_identity:
        raise ValueError("真实数据 row_identity 漂移")
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample submission ID 与 test 不一致")

    member_oof: dict[str, np.ndarray] = {}
    member_test: dict[str, np.ndarray] = {}
    for member in config["members"]:
        directory = resolve_project_path(member["directory"])
        member_oof[member["experiment_id"]] = np.load(
            directory / "oof_proba.npy", allow_pickle=False
        ).astype(np.float64, copy=False)
        member_test[member["experiment_id"]] = np.load(
            directory / "test_proba.npy", allow_pickle=False
        ).astype(np.float64, copy=False)
    baseline_dir = resolve_project_path(config["strict_baseline"]["directory"])
    baseline_oof = np.load(
        baseline_dir / "oof_proba.npy", allow_pickle=False
    ).astype(np.float64, copy=False)
    baseline_test = np.load(
        baseline_dir / "test_proba.npy", allow_pickle=False
    ).astype(np.float64, copy=False)
    return (
        train,
        test,
        sample,
        y.to_numpy(np.int8),
        member_oof,
        member_test,
        baseline_oof,
        baseline_test,
    )


def lineage_payload(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "node_type": "SMALL_BLEND",
        "members": [
            {
                "experiment_id": member["experiment_id"],
                "node_type": "ATOMIC_SINGLE_MODEL",
                "role": member["role"],
                "prediction_parent": None,
            }
            for member in config["members"]
        ],
        "strict_baseline": {
            "experiment_id": BASELINE_ID,
            "role": "COMPARISON_ONLY_NOT_A_MEMBER",
        },
        "relationship": config["lineage_contract"]["relationship"],
        "v87_is_independently_trained_not_a_prediction_wrapper": True,
        "downstream_if_promoted": config["lineage_contract"][
            "downstream_if_promoted"
        ],
        "forbidden_prediction_members": config["forbidden_prediction_members"],
    }


def meta_folds_payload(y: np.ndarray) -> dict[str, Any]:
    rows = []
    coverage = np.zeros(len(y), dtype=np.int8)
    for fold, (train_idx, holdout_idx) in enumerate(meta_splits(y), start=1):
        coverage[holdout_idx] += 1
        rows.append(
            {
                "fold": fold,
                "meta_train_rows": len(train_idx),
                "meta_holdout_rows": len(holdout_idx),
                "meta_train_positive_rate": float(np.mean(y[train_idx])),
                "meta_holdout_positive_rate": float(np.mean(y[holdout_idx])),
                "meta_train_idx_sha256_int64_le": sha256_indices(train_idx),
                "meta_holdout_idx_sha256_int64_le": sha256_indices(holdout_idx),
            }
        )
    if not np.all(coverage == 1):
        raise ValueError("meta folds coverage 非恰好一次")
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "n_splits": N_META_FOLDS,
        "shuffle": True,
        "random_state": META_SEED,
        "rows": rows,
        "coverage_exactly_once": True,
    }


def build_sources(
    config: dict[str, Any], train: pd.DataFrame, test: pd.DataFrame
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "created_at_utc": utc_now(),
        "row_identity": {
            "train_rows": len(train),
            "test_rows": len(test),
            "train_id_sha256": sha256_ids(train[config["id_column"]]),
            "test_id_sha256": sha256_ids(test[config["id_column"]]),
        },
        "row_identity_hash_contract": config["row_identity_hash_contract"],
        "data": data_file_records(config),
        "source_predictions": source_file_records(config),
        "source_result_metadata": source_result_metadata(config),
        "code": {
            "runner": file_record(Path(__file__)),
            "frozen_config": file_record(CONFIG_PATH),
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "prediction_access_boundary": (
            "real arrays loaded only after all source hashes, metadata, row identities, "
            "and full source verifiers passed in formal run or verify"
        ),
    }


def process_peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def resource_check(
    config: dict[str, Any], started: float, phase: str, fold: int | None
) -> dict[str, Any]:
    elapsed = float(time.monotonic() - started)
    peak = process_peak_rss_bytes()
    breaches = []
    if elapsed > config["time_budget_seconds"]:
        breaches.append("WALL_CLOCK_BUDGET")
    if peak > config["peak_rss_budget_bytes"]:
        breaches.append("PEAK_RSS_BUDGET")
    return {
        "phase": phase,
        "fold": fold,
        "wall_elapsed_seconds": elapsed,
        "wall_budget_seconds": config["time_budget_seconds"],
        "peak_rss_bytes": peak,
        "peak_rss_gib": peak / 1024**3,
        "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
        "peak_rss_budget_gib": config["memory_budget_gib"],
        "breaches": breaches,
    }


def validate_resource_check(config: dict[str, Any], check: dict[str, Any]) -> None:
    required = {
        "phase",
        "fold",
        "wall_elapsed_seconds",
        "wall_budget_seconds",
        "peak_rss_bytes",
        "peak_rss_gib",
        "peak_rss_budget_bytes",
        "peak_rss_budget_gib",
        "breaches",
    }
    if set(check) != required:
        raise ValueError("资源 check schema 漂移")
    phase = check.get("phase")
    fold = check.get("fold")
    if not isinstance(phase, str) or phase not in RESOURCE_PHASE_FOLD_POLICY:
        raise ValueError("资源 phase 不在冻结白名单")
    if isinstance(fold, bool) or (fold is not None and not isinstance(fold, int)):
        raise ValueError("资源 fold 类型非法")
    if fold not in RESOURCE_PHASE_FOLD_POLICY[phase]:
        raise ValueError("资源 phase/fold 组合不在冻结域")
    elapsed = check.get("wall_elapsed_seconds")
    peak_bytes = check.get("peak_rss_bytes")
    peak_gib = check.get("peak_rss_gib")
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
        raise ValueError("资源 peak RSS bytes 字段非法")
    if (
        isinstance(peak_gib, bool)
        or not isinstance(peak_gib, (int, float))
        or not np.isfinite(peak_gib)
        or not np.isclose(
            peak_gib, peak_bytes / 1024**3, atol=1e-12, rtol=0.0
        )
    ):
        raise ValueError("资源 peak RSS bytes/GiB 换算不一致")
    if (
        check["wall_budget_seconds"] != config["time_budget_seconds"]
        or check["peak_rss_budget_bytes"] != config["peak_rss_budget_bytes"]
        or check["peak_rss_budget_gib"] != config["memory_budget_gib"]
        or not isinstance(check["breaches"], list)
    ):
        raise ValueError("资源 check 冻结值漂移")
    recomputed_breaches = []
    if elapsed > config["time_budget_seconds"]:
        recomputed_breaches.append("WALL_CLOCK_BUDGET")
    if peak_bytes > config["peak_rss_budget_bytes"]:
        recomputed_breaches.append("PEAK_RSS_BUDGET")
    if check["breaches"] != recomputed_breaches:
        raise ValueError("资源 breaches 无法由原始测量独立复算")


def canonical_resource_sequence() -> list[tuple[str, int | None]]:
    return [
        ("BEFORE_INPUT_LOAD", None),
        ("AFTER_INPUT_LOAD", None),
        *[("AFTER_META_FOLD", fold) for fold in range(1, N_META_FOLDS + 1)],
        ("AFTER_ALL_OUTPUTS", N_META_FOLDS),
        ("AFTER_STAGED_VERIFY_PRE_COMPLETE", N_META_FOLDS),
        ("PRE_COMMIT_AFTER_FINAL_FILE_VERIFY", N_META_FOLDS),
        ("FINAL_GUARD_AFTER_THIRD_FILE_VERIFY", N_META_FOLDS),
    ]


def validate_resource_sequence(
    config: dict[str, Any],
    checks: list[dict[str, Any]],
    status: str,
    final_check: dict[str, Any],
) -> None:
    if not isinstance(checks, list) or not checks:
        raise ValueError("资源 phase 序列为空")
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("资源 phase 序列元素非法")
        validate_resource_check(config, check)
    for previous, current in zip(checks, checks[1:]):
        if current["wall_elapsed_seconds"] < previous["wall_elapsed_seconds"]:
            raise ValueError("资源 elapsed_seconds 序列发生回退")
        if current["peak_rss_bytes"] < previous["peak_rss_bytes"]:
            raise ValueError("资源 peak_rss_bytes 序列发生回退")
        if current["peak_rss_gib"] < previous["peak_rss_gib"]:
            raise ValueError("资源 peak_rss_gib 序列发生回退")
    if checks[-1] != final_check:
        raise ValueError("final_resource_check 不是资源序列末项")
    observed = [(check["phase"], check["fold"]) for check in checks]
    canonical = canonical_resource_sequence()
    if status == "COMPLETE_PREFIX":
        if observed != canonical[: len(observed)]:
            raise ValueError("COMPLETE prefix 资源 phase/fold 序列或覆盖漂移")
        if any(check["breaches"] for check in checks):
            raise ValueError("COMPLETE prefix 资源序列含超限")
        return
    if status == "COMPLETE":
        if observed != canonical:
            raise ValueError("COMPLETE 资源 phase/fold 序列或覆盖漂移")
        if any(check["breaches"] for check in checks):
            raise ValueError("COMPLETE 资源序列含超限")
        return
    if status == "FAILED_RESOURCE_BUDGET":
        if observed[-1] == ("POST_SEAL_COMMIT_GUARD", N_META_FOLDS):
            prefix = observed[:-1]
            if prefix != canonical:
                raise ValueError("post-seal 资源失败前缀漂移")
        elif observed[-1][0] == "FAILED_EXCEPTION":
            prefix = observed[:-1]
            if prefix != canonical[: len(prefix)]:
                raise ValueError("资源失败 phase/fold 前缀或次序漂移")
            completed_folds = sum(
                phase == "AFTER_META_FOLD" for phase, _ in prefix
            )
            if observed[-1] != ("FAILED_EXCEPTION", completed_folds):
                raise ValueError("异常关闭时资源失败 fold 漂移")
        elif observed != canonical[: len(observed)]:
            raise ValueError("资源失败 phase/fold 前缀或次序漂移")
        if any(check["breaches"] for check in checks[:-1]):
            raise ValueError("资源失败前已有未关闭超限")
        if not checks[-1]["breaches"]:
            raise ValueError("资源失败末项没有预算超限")
        return
    if status == "FAILED_EXCEPTION":
        prefix = observed[:-1]
        if prefix != canonical[: len(prefix)]:
            raise ValueError("异常失败 phase/fold 前缀或次序漂移")
        if any(check["breaches"] for check in checks[:-1]):
            raise ValueError("异常失败前存在应先关闭的资源超限")
        completed_folds = sum(
            phase == "AFTER_META_FOLD" for phase, _ in prefix
        )
        if observed[-1] != ("FAILED_EXCEPTION", completed_folds):
            raise ValueError("异常失败 fold 未对应已完成 meta folds")
        if checks[-1]["breaches"]:
            raise ValueError("普通异常关闭不得掩盖资源超限")
        return
    raise ValueError(f"未知资源终态：{status}")


def require_resource_pass(config: dict[str, Any], check: dict[str, Any]) -> None:
    validate_resource_check(config, check)
    if check["breaches"]:
        raise ResourceBudgetExceeded(check)


def failure_inventory(root: Path = OUT_DIR) -> dict[str, Any]:
    expected = [*MATERIAL_ARTIFACTS, *FAILURE_ONLY_ARTIFACTS]
    present = [name for name in expected if (root / name).is_file()]
    missing = [name for name in expected if name not in present]
    return {
        "expected_artifacts": expected,
        "present_artifacts": present,
        "missing_artifacts": missing,
        "present_artifacts_are_invalid_for_use": True,
    }


def failure_attribution_for(
    config: dict[str, Any], status: str, decision: str
) -> str | None:
    key = f"{status}_{decision}" if status == "COMPLETE" else status
    if key not in config["failure_attribution_contract"]:
        raise ValueError(f"失败归因状态未冻结：{key}")
    return config["failure_attribution_contract"][key]


def best_effort_hash_evidence(
    path: Path, expected_sha256: str | None
) -> dict[str, Any]:
    try:
        display_path = str(path.resolve().relative_to(PROJECT_DIR.resolve()))
    except (OSError, ValueError) as error:
        display_path = str(path)
        path_error = f"{type(error).__name__}: {error}"
    else:
        path_error = None
    record: dict[str, Any] = {
        "path": display_path,
        "expected_sha256": expected_sha256,
        "exists": path.is_file(),
        "observed_sha256": None,
        "observed_size_bytes": None,
        "collection_error": path_error,
    }
    if not record["exists"]:
        record["collection_error"] = record["collection_error"] or (
            f"FileNotFoundError: {display_path}"
        )
        return record
    try:
        observed_sha256 = sha256_file(path)
        observed_size_bytes = path.stat().st_size
    except Exception as error:  # failure close must survive evidence I/O errors
        record["collection_error"] = f"{type(error).__name__}: {error}"
    else:
        record["observed_sha256"] = observed_sha256
        record["observed_size_bytes"] = observed_size_bytes
    return record


def expected_failure_evidence_paths(
    config: dict[str, Any],
) -> dict[str, tuple[Path, str | None]]:
    expected: dict[str, tuple[Path, str | None]] = {
        "runner": (Path(__file__), None),
        "frozen_config": (CONFIG_PATH, None),
    }
    for relative, expected_hash in config["data_sha256"].items():
        expected[f"data:{relative}"] = (
            PROJECT_DIR / relative,
            expected_hash,
        )
    hash_names = {
        "runner": "runner_sha256",
        "frozen_config.json": "config_sha256",
        "cv_results.json": "cv_results_sha256",
        "sources.json": "sources_sha256",
        "oof_proba.npy": "oof_proba_sha256",
        "test_proba.npy": "test_proba_sha256",
    }
    for source in source_entries(config):
        directory = PROJECT_DIR / source["directory"]
        for filename, hash_key in hash_names.items():
            actual_name = source["runner"] if filename == "runner" else filename
            expected[f"source:{source['experiment_id']}:{actual_name}"] = (
                directory / actual_name,
                source[hash_key],
            )
    return expected


def collect_failure_input_evidence(config: dict[str, Any]) -> dict[str, Any]:
    records = {
        key: best_effort_hash_evidence(path, expected_hash)
        for key, (path, expected_hash) in expected_failure_evidence_paths(config).items()
    }
    return {
        "schema_version": 1,
        "mode": "BEST_EFFORT_NON_THROWING_FAILURE_SNAPSHOT",
        "records": records,
        "record_count": len(records),
        "records_with_collection_error": sorted(
            key for key, record in records.items() if record["collection_error"]
        ),
        "records_with_hash_mismatch": sorted(
            key
            for key, record in records.items()
            if record["expected_sha256"] is not None
            and record["observed_sha256"] is not None
            and record["expected_sha256"] != record["observed_sha256"]
        ),
    }


def validate_failure_input_evidence(
    evidence: dict[str, Any], config: dict[str, Any]
) -> None:
    if (
        evidence.get("schema_version") != 1
        or evidence.get("mode") != "BEST_EFFORT_NON_THROWING_FAILURE_SNAPSHOT"
        or not isinstance(evidence.get("records"), dict)
    ):
        raise ValueError("FAILED 输入证据 schema 非法")
    expected = expected_failure_evidence_paths(config)
    records = evidence["records"]
    if set(records) != set(expected) or evidence.get("record_count") != len(expected):
        raise ValueError("FAILED 输入证据清单漂移")
    errors = []
    mismatches = []
    for key, (_, expected_hash) in expected.items():
        record = records[key]
        if not isinstance(record, dict) or set(record) != {
            "path",
            "expected_sha256",
            "exists",
            "observed_sha256",
            "observed_size_bytes",
            "collection_error",
        }:
            raise ValueError(f"FAILED 输入证据记录 schema 非法：{key}")
        expected_path, _ = expected[key]
        expected_live_record = best_effort_hash_evidence(
            expected_path, expected_hash
        )
        if record["path"] != expected_live_record["path"]:
            raise ValueError(f"FAILED 输入证据冻结 path 漂移：{key}")
        if record["expected_sha256"] != expected_hash:
            raise ValueError(f"FAILED 输入证据预期 SHA 漂移：{key}")
        observed_hash = record["observed_sha256"]
        observed_size = record["observed_size_bytes"]
        error = record["collection_error"]
        if not isinstance(record["path"], str) or not record["path"]:
            raise ValueError(f"FAILED 输入证据 path 非法：{key}")
        if not isinstance(record["exists"], bool):
            raise ValueError(f"FAILED 输入证据 exists 非法：{key}")
        if observed_hash is not None and (
            not isinstance(observed_hash, str) or len(observed_hash) != 64
        ):
            raise ValueError(f"FAILED 输入证据 observed SHA 非法：{key}")
        if observed_size is not None and (
            isinstance(observed_size, bool)
            or not isinstance(observed_size, int)
            or observed_size < 0
        ):
            raise ValueError(f"FAILED 输入证据 size 非法：{key}")
        if error is not None and (not isinstance(error, str) or not error):
            raise ValueError(f"FAILED 输入证据 error 非法：{key}")
        if record["exists"]:
            successful = (
                observed_hash is not None
                and observed_size is not None
                and error is None
            )
            failed = (
                observed_hash is None
                and observed_size is None
                and error is not None
            )
            if not (successful or failed):
                raise ValueError(f"FAILED 可见输入采集状态不互斥：{key}")
        elif not (
            observed_hash is None
            and observed_size is None
            and error
            == f"FileNotFoundError: {expected_live_record['path']}"
        ):
            raise ValueError(f"FAILED 缺失输入状态或错误文本非法：{key}")
        if record != expected_live_record:
            raise ValueError(f"FAILED 输入证据与实时重采样不一致：{key}")
        if error is not None:
            errors.append(key)
        if (
            expected_hash is not None
            and observed_hash is not None
            and expected_hash != observed_hash
        ):
            mismatches.append(key)
    if evidence.get("records_with_collection_error") != sorted(errors):
        raise ValueError("FAILED 输入证据 error 索引无法复算")
    if evidence.get("records_with_hash_mismatch") != sorted(mismatches):
        raise ValueError("FAILED 输入证据 hash drift 索引无法复算")


def exact_link_error(error: OSError) -> str:
    """Serialize every stable OSError field instead of dropping link errors."""
    return canonical_json(
        {
            "type": type(error).__name__,
            "errno": error.errno,
            "strerror": error.strerror,
            "filename": error.filename,
            "filename2": error.filename2,
            "message": str(error),
        }
    )


def archive_file_snapshot(path: Path) -> dict[str, Any]:
    """Collect a deterministic, non-throwing snapshot of an archive path."""
    resolved = Path(os.path.abspath(os.fspath(path)))
    present = path.exists() or path.is_symlink()
    snapshot: dict[str, Any] = {
        "archive_present": present,
        "archive_sha256": None,
        "archive_size_bytes": None,
        "archive_collection_error": None,
    }
    if not present:
        snapshot["archive_collection_error"] = f"FileNotFoundError: {resolved}"
        return snapshot
    if not path.is_file() or path.is_symlink():
        snapshot["archive_collection_error"] = (
            f"NotRegularFileError: {resolved}"
        )
        return snapshot
    try:
        snapshot["archive_sha256"] = sha256_file(path)
        snapshot["archive_size_bytes"] = path.stat().st_size
    except Exception as error:  # failure close must preserve the link outcome
        snapshot["archive_collection_error"] = (
            f"{type(error).__name__}: {error}"
        )
    return snapshot


def collect_sealed_archive_provenance(
    pending_path: Path, archive_path: Path
) -> dict[str, Any]:
    """Hard-link a sealed pending file and preserve the exact attempt outcome."""
    pending = Path(os.path.abspath(os.fspath(pending_path)))
    archive = Path(os.path.abspath(os.fspath(archive_path)))
    if pending.is_symlink() or not pending.is_file():
        raise ValueError("sealed pending 必须是实时普通文件")
    sealed_sha256 = sha256_file(pending)
    sealed_size_bytes = pending.stat().st_size
    link_succeeded = False
    link_errno: int | None = None
    link_error: str | None = None
    try:
        os.link(pending, archive)
    except OSError as error:
        link_errno = error.errno
        link_error = exact_link_error(error)
    else:
        link_succeeded = True
    snapshot = archive_file_snapshot(archive)
    archive_matches_sealed = bool(
        snapshot["archive_present"]
        and snapshot["archive_collection_error"] is None
        and snapshot["archive_sha256"] == sealed_sha256
        and snapshot["archive_size_bytes"] == sealed_size_bytes
    )
    stale_collision = bool(
        not link_succeeded
        and link_errno == errno.EEXIST
        and not archive_matches_sealed
    )
    if link_succeeded and archive_matches_sealed:
        archive_status = "LINK_CREATED"
        archive_success = True
    elif (
        not link_succeeded
        and link_errno == errno.EEXIST
        and archive_matches_sealed
    ):
        archive_status = "EXISTING_IDENTICAL"
        archive_success = True
    elif stale_collision:
        archive_status = "STALE_COLLISION"
        archive_success = False
    else:
        archive_status = "ARCHIVE_FAILED"
        archive_success = False
    return {
        "schema_version": 1,
        "sealed_pending_path": str(pending),
        "sealed_pending_sha256": sealed_sha256,
        "sealed_pending_size_bytes": sealed_size_bytes,
        "archive_path": str(archive),
        "link_attempted": True,
        "link_succeeded": link_succeeded,
        "link_errno": link_errno,
        "link_error": link_error,
        **snapshot,
        "archive_matches_sealed": archive_matches_sealed,
        "archive_status": archive_status,
        "archive_success": archive_success,
        "archive_failed": not archive_success,
        "stale_collision": stale_collision,
        "invalid_for_use": True,
    }


def validate_sealed_archive_provenance(
    provenance: dict[str, Any], root: Path
) -> None:
    expected_keys = {
        "schema_version",
        "sealed_pending_path",
        "sealed_pending_sha256",
        "sealed_pending_size_bytes",
        "archive_path",
        "link_attempted",
        "link_succeeded",
        "link_errno",
        "link_error",
        "archive_present",
        "archive_sha256",
        "archive_size_bytes",
        "archive_collection_error",
        "archive_matches_sealed",
        "archive_status",
        "archive_success",
        "archive_failed",
        "stale_collision",
        "invalid_for_use",
    }
    if not isinstance(provenance, dict) or set(provenance) != expected_keys:
        raise ValueError("sealed archive provenance schema 非法")
    if provenance["schema_version"] != 1:
        raise ValueError("sealed archive provenance 版本非法")
    root_resolved = root.resolve()
    archive_path = root_resolved / FAILED_SEALED_ARCHIVE_NAME
    if provenance["archive_path"] != str(archive_path):
        raise ValueError("sealed archive path 漂移")
    pending_value = provenance["sealed_pending_path"]
    if not isinstance(pending_value, str) or not pending_value:
        raise ValueError("sealed pending path 非法")
    pending_path = Path(pending_value)
    if pending_path.parent != root_resolved:
        raise ValueError("sealed pending path 越界")
    pending_name = pending_path.name
    prefix = ".cv_results.complete."
    suffix = ".json"
    process_part = pending_name[len(prefix) : -len(suffix)]
    if (
        not pending_name.startswith(prefix)
        or not pending_name.endswith(suffix)
        or not process_part.isdigit()
    ):
        raise ValueError("sealed pending 文件名不符合冻结合同")
    sealed_sha256 = provenance["sealed_pending_sha256"]
    sealed_size_bytes = provenance["sealed_pending_size_bytes"]
    if (
        not isinstance(sealed_sha256, str)
        or len(sealed_sha256) != 64
        or any(character not in "0123456789abcdef" for character in sealed_sha256)
    ):
        raise ValueError("sealed pending SHA 非法")
    if (
        isinstance(sealed_size_bytes, bool)
        or not isinstance(sealed_size_bytes, int)
        or sealed_size_bytes < 0
    ):
        raise ValueError("sealed pending size 非法")
    if pending_path.exists():
        if pending_path.is_symlink() or not pending_path.is_file():
            raise ValueError("实时 sealed pending 不是普通文件")
        if (
            sha256_file(pending_path) != sealed_sha256
            or pending_path.stat().st_size != sealed_size_bytes
        ):
            raise ValueError("实时 sealed pending SHA/size 与 provenance 不一致")
    if provenance["link_attempted"] is not True:
        raise ValueError("sealed archive 未记录 link attempt")
    for boolean_key in (
        "archive_present",
        "archive_matches_sealed",
        "archive_success",
        "archive_failed",
        "stale_collision",
        "invalid_for_use",
    ):
        if not isinstance(provenance[boolean_key], bool):
            raise ValueError(f"sealed archive 布尔字段非法：{boolean_key}")
    archive_sha256 = provenance["archive_sha256"]
    archive_size_bytes = provenance["archive_size_bytes"]
    archive_collection_error = provenance["archive_collection_error"]
    if archive_sha256 is not None and (
        not isinstance(archive_sha256, str)
        or len(archive_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in archive_sha256
        )
    ):
        raise ValueError("sealed archive SHA 非法")
    if archive_size_bytes is not None and (
        isinstance(archive_size_bytes, bool)
        or not isinstance(archive_size_bytes, int)
        or archive_size_bytes < 0
    ):
        raise ValueError("sealed archive size 非法")
    if archive_collection_error is not None and (
        not isinstance(archive_collection_error, str)
        or not archive_collection_error
    ):
        raise ValueError("sealed archive collection_error 非法")
    if provenance["archive_status"] not in {
        "LINK_CREATED",
        "EXISTING_IDENTICAL",
        "STALE_COLLISION",
        "ARCHIVE_FAILED",
    }:
        raise ValueError("sealed archive status 非法")
    link_succeeded = provenance["link_succeeded"]
    link_errno = provenance["link_errno"]
    link_error = provenance["link_error"]
    if not isinstance(link_succeeded, bool):
        raise ValueError("sealed archive link_succeeded 非法")
    if link_succeeded:
        if link_errno is not None or link_error is not None:
            raise ValueError("link 成功时不得伪造 error")
    else:
        if (
            isinstance(link_errno, bool)
            or not isinstance(link_errno, int)
            or not isinstance(link_error, str)
            or not link_error
        ):
            raise ValueError("link 失败缺少精确 error")
        try:
            error_payload = json.loads(link_error)
        except json.JSONDecodeError as error:
            raise ValueError("link_error 不是精确 JSON") from error
        if not isinstance(error_payload, dict) or set(error_payload) != {
            "type",
            "errno",
            "strerror",
            "filename",
            "filename2",
            "message",
        }:
            raise ValueError("link_error schema 非法")
        if link_error != canonical_json(error_payload):
            raise ValueError("link_error 非规范序列化")
        if (
            error_payload["errno"] != link_errno
            or error_payload["filename"] != str(pending_path)
            or error_payload["filename2"] != str(archive_path)
            or not isinstance(error_payload["type"], str)
            or not error_payload["type"]
            or not isinstance(error_payload["strerror"], str)
            or not error_payload["strerror"]
            or not isinstance(error_payload["message"], str)
            or not error_payload["message"]
        ):
            raise ValueError("link_error 与冻结路径/错误码不一致")
        if link_errno == errno.EEXIST:
            expected_message = (
                f"[Errno {errno.EEXIST}] {os.strerror(errno.EEXIST)}: "
                f"{str(pending_path)!r} -> {str(archive_path)!r}"
            )
            if error_payload != {
                "type": "FileExistsError",
                "errno": errno.EEXIST,
                "strerror": os.strerror(errno.EEXIST),
                "filename": str(pending_path),
                "filename2": str(archive_path),
                "message": expected_message,
            }:
                raise ValueError("EEXIST link_error 不是实际路径的精确证据")
    live_snapshot = archive_file_snapshot(archive_path)
    stored_snapshot = {
        key: provenance[key]
        for key in (
            "archive_present",
            "archive_sha256",
            "archive_size_bytes",
            "archive_collection_error",
        )
    }
    if stored_snapshot != live_snapshot:
        raise ValueError("sealed archive SHA/size 与实时重算不一致")
    archive_matches_sealed = bool(
        live_snapshot["archive_present"]
        and live_snapshot["archive_collection_error"] is None
        and live_snapshot["archive_sha256"] == sealed_sha256
        and live_snapshot["archive_size_bytes"] == sealed_size_bytes
    )
    stale_collision = bool(
        not link_succeeded
        and link_errno == errno.EEXIST
        and not archive_matches_sealed
    )
    if link_succeeded and archive_matches_sealed:
        expected_status = "LINK_CREATED"
        archive_success = True
    elif (
        not link_succeeded
        and link_errno == errno.EEXIST
        and archive_matches_sealed
    ):
        expected_status = "EXISTING_IDENTICAL"
        archive_success = True
    elif stale_collision:
        expected_status = "STALE_COLLISION"
        archive_success = False
    else:
        expected_status = "ARCHIVE_FAILED"
        archive_success = False
    expected_derived = {
        "archive_matches_sealed": archive_matches_sealed,
        "archive_status": expected_status,
        "archive_success": archive_success,
        "archive_failed": not archive_success,
        "stale_collision": stale_collision,
        "invalid_for_use": True,
    }
    for key, expected_value in expected_derived.items():
        if provenance[key] != expected_value:
            raise ValueError(f"sealed archive 派生状态伪造：{key}")


def build_failed_result(
    config: dict[str, Any],
    status: str,
    check: dict[str, Any],
    error_type: str,
    error: str,
    root: Path = OUT_DIR,
    input_evidence: dict[str, Any] | None = None,
    resource_checks: list[dict[str, Any]] | None = None,
    sealed_archive_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inventory = failure_inventory(root)
    evidence = input_evidence or collect_failure_input_evidence(config)
    validate_failure_input_evidence(evidence, config)
    checks = resource_checks or [check]
    validate_resource_sequence(config, checks, status, check)
    return {
        "schema_version": 1,
        "status": status,
        "decision": status,
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": True,
        "base": BASELINE_ID,
        "base_oof_auc": config["base_oof_auc"],
        "oof_delta_vs_base": None,
        "failure_attribution": failure_attribution_for(config, status, status),
        "error_type": error_type,
        "error": error,
        "resource_checks": checks,
        "resource_check": check,
        "elapsed_seconds": check["wall_elapsed_seconds"],
        "peak_rss_bytes": check["peak_rss_bytes"],
        "peak_rss_gib": check["peak_rss_gib"],
        "allowed_for_fusion": False,
        "eligible_for_separate_preregistration": False,
        "allowed_for_submission": False,
        "submission_budget": 0,
        **inventory,
        "sealed_pending_archive": {
            "artifact": FAILED_SEALED_ARCHIVE_NAME,
            "present": bool(
                sealed_archive_provenance
                and sealed_archive_provenance.get("archive_success") is True
            ),
            "physical_path_present": FAILED_SEALED_ARCHIVE_NAME
            in inventory["present_artifacts"],
            "archive_failed": bool(
                sealed_archive_provenance
                and sealed_archive_provenance.get("archive_failed") is True
            ),
            "stale_collision": bool(
                sealed_archive_provenance
                and sealed_archive_provenance.get("stale_collision") is True
            ),
            "invalid_for_use": True,
        },
        "sealed_archive_provenance": sealed_archive_provenance,
        "failure_input_evidence": evidence,
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
    checks = results.get("resource_checks")
    if not isinstance(checks, list):
        raise ValueError("失败状态缺少资源 phase 序列")
    validate_resource_sequence(config, checks, status, check)
    provenance = results.get("sealed_archive_provenance")
    if status == "FAILED_RESOURCE_BUDGET":
        if not check["breaches"]:
            raise ValueError("资源失败没有预算超限")
        error_type = "ResourceBudgetExceeded"
        error = ",".join(check["breaches"])
        if check["phase"] == "POST_SEAL_COMMIT_GUARD":
            if not isinstance(provenance, dict):
                raise ValueError("post-seal 资源失败缺少 archive provenance")
            validate_sealed_archive_provenance(provenance, root)
        elif provenance is not None:
            raise ValueError("非 post-seal 失败不得伪造 archive provenance")
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
        if provenance is not None:
            raise ValueError("普通异常失败不得伪造 archive provenance")
    evidence = results.get("failure_input_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("失败状态缺少输入 hash 证据")
    validate_failure_input_evidence(evidence, config)
    expected = build_failed_result(
        config,
        status,
        check,
        error_type,
        error,
        root,
        input_evidence=evidence,
        resource_checks=checks,
        sealed_archive_provenance=provenance,
    )
    assert_nested_close(results, expected, status)


def build_complete_result(
    config: dict[str, Any],
    meta: dict[str, Any],
    evaluation: dict[str, Any],
    final_resource_check: dict[str, Any],
    sources_sha256: str,
    resource_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    decision = evaluation["decision"]
    return {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "experiment_type": config["experiment_type"],
        "counts_toward_cycle": True,
        "model": config["model"],
        "hypothesis": config["hypothesis"],
        "n_folds": N_META_FOLDS,
        "fold_auc": [row["holdout_blend_auc"] for row in meta["fold_rows"]],
        "params": {
            "meta_cv": config["meta_cv"],
            "transform": config["transform"],
            "weight_search": config["weight_search"],
            "baseline_reconstruction": config["baseline_reconstruction"],
            "fixed_equal_weight_control": config["fixed_equal_weight_control"],
        },
        "elapsed_seconds": final_resource_check["wall_elapsed_seconds"],
        "oof_auc": evaluation["oof_auc"],
        "base": BASELINE_ID,
        "base_oof_auc": evaluation["base_oof_auc"],
        "oof_delta_vs_base": evaluation["oof_delta_vs_base"],
        "meta_fold_rows": meta["fold_rows"],
        "evaluation": evaluation,
        "decision": decision,
        "failure_attribution": failure_attribution_for(config, "COMPLETE", decision),
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
            "all_source_verifiers_and_hashes_passed": True,
            "source_row_identities_match_directly": True,
            "v90_rebuilt_oof_and_test_match_elementwise": True,
            "all_transforms_fit_on_meta_train_only": True,
            "equal_weight_control_not_used_for_selection": True,
            "no_parent_child_prediction_overlap": True,
        },
        "resource_checks": resource_checks,
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
    checks = results.get("resource_checks")
    if not isinstance(checks, list):
        raise ValueError("COMPLETE 缺少资源 phase 序列")
    phases = allowed_resource_phases or {"FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"}
    if check["phase"] not in phases:
        raise ValueError("COMPLETE 最终资源 phase 错误")
    if check["phase"] == "AFTER_ALL_OUTPUTS":
        expected_sequence = canonical_resource_sequence()[:8]
    elif check["phase"] == "AFTER_STAGED_VERIFY_PRE_COMPLETE":
        expected_sequence = canonical_resource_sequence()[:9]
    elif check["phase"] == "PRE_COMMIT_AFTER_FINAL_FILE_VERIFY":
        expected_sequence = canonical_resource_sequence()[:10]
    elif check["phase"] == "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY":
        expected_sequence = canonical_resource_sequence()
    else:
        raise ValueError("COMPLETE verifier 不接受该资源终点")
    observed_sequence = [(row.get("phase"), row.get("fold")) for row in checks]
    if observed_sequence != expected_sequence:
        raise ValueError("COMPLETE 资源 phase/fold 序列或覆盖漂移")
    validate_resource_sequence(
        config,
        checks,
        (
            "COMPLETE"
            if check["phase"] == "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"
            else "COMPLETE_PREFIX"
        ),
        check,
    )
    expected = build_complete_result(
        config, meta, evaluation, check, sources_sha256, checks
    )
    assert_nested_close(results, expected, "COMPLETE")


def verify_complete_payload(
    results: dict[str, Any] | None = None,
    allowed_resource_phases: set[str] | None = None,
) -> dict[str, Any]:
    config = load_frozen_config()
    is_override = results is not None
    if results is None:
        results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    if results.get("status") in {"FAILED_RESOURCE_BUDGET", "FAILED_EXCEPTION"}:
        validate_failed_result(results, config, OUT_DIR)
        return results
    if results.get("status") != "COMPLETE":
        raise ValueError("verify 只接受 COMPLETE 或两类 FAILED")
    (
        train,
        test,
        sample,
        y,
        member_oof,
        member_test,
        baseline_oof,
        baseline_test,
    ) = load_formal_inputs(config)
    expected_json = {
        "candidate_snapshot.json": candidate_snapshot(config),
        "lineage.json": lineage_payload(config),
        "meta_folds.json": meta_folds_payload(y),
    }
    for name, expected in expected_json.items():
        actual = json.loads((OUT_DIR / name).read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError(f"{name} 无法重建")
    meta = run_meta_cv(y, member_oof, member_test)
    assert_baseline_reconstruction(config, meta, baseline_oof, baseline_test)
    evaluation = evaluate(config, y, meta, member_oof, member_test)
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
    expected_sources["created_at_utc"] = stored_sources.get("created_at_utc")
    if stored_sources != expected_sources:
        raise ValueError("sources 无法重建")
    validate_complete_result_schema(
        results,
        config,
        meta,
        evaluation,
        sha256_file(OUT_DIR / "sources.json"),
        allowed_resource_phases
        or (
            {
                "AFTER_ALL_OUTPUTS",
                "AFTER_STAGED_VERIFY_PRE_COMPLETE",
                "PRE_COMMIT_AFTER_FINAL_FILE_VERIFY",
                "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY",
            }
            if is_override
            else {"FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"}
        ),
    )
    return results


def verify_staged_complete_file(
    path: Path, allowed_resource_phases: set[str]
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    before_sha256 = sha256_file(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    verified = verify_complete_payload(
        payload, allowed_resource_phases=allowed_resource_phases
    )
    after_sha256 = sha256_file(path)
    if before_sha256 != after_sha256:
        raise ValueError("staged COMPLETE 文件在完整 verifier 期间发生变化")
    assert_nested_close(verified, payload, "STAGED_COMPLETE_FILE")
    return payload


def commit_complete_file(pending_path: Path, results_path: Path) -> None:
    os.replace(pending_path, results_path)


def seal_final_guard_and_commit(
    config: dict[str, Any],
    started: float,
    pending_path: Path,
    results_path: Path,
    resource_checks: list[dict[str, Any]],
    third_verified_sha256: str,
    payload_builder: Callable[
        [dict[str, Any], list[dict[str, Any]]], dict[str, Any]
    ],
) -> dict[str, Any]:
    """Seal terminal resource evidence, verify that exact file, then commit.

    The fourth verifier is deliberately read-only and occurs after the evidence
    seal. A non-persisted post-seal guard immediately enforces the budget spent
    by that verifier. No payload rewrite follows the fourth verifier, which
    avoids recursive measure/rewrite/verify cycles.
    """
    if sha256_file(pending_path) != third_verified_sha256:
        raise ValueError("第三次 verifier 后 pending 文件发生变化")
    final_guard = resource_check(
        config,
        started,
        "FINAL_GUARD_AFTER_THIRD_FILE_VERIFY",
        N_META_FOLDS,
    )
    resource_checks.append(final_guard)
    require_resource_pass(config, final_guard)
    validate_resource_sequence(config, resource_checks, "COMPLETE", final_guard)
    sealed_payload = payload_builder(final_guard, list(resource_checks))
    _atomic_bytes(
        pending_path,
        (json.dumps(sealed_payload, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        ),
    )
    verify_staged_complete_file(
        pending_path, {"FINAL_GUARD_AFTER_THIRD_FILE_VERIFY"}
    )
    post_seal_guard = resource_check(
        config, started, "POST_SEAL_COMMIT_GUARD", N_META_FOLDS
    )
    validate_resource_check(config, post_seal_guard)
    if post_seal_guard["breaches"]:
        resource_checks.append(post_seal_guard)
        archive_path = results_path.parent / FAILED_SEALED_ARCHIVE_NAME
        archive_provenance = collect_sealed_archive_provenance(
            pending_path, archive_path
        )
        raise ResourceBudgetExceeded(post_seal_guard, archive_provenance)
    if results_path.exists():
        raise RuntimeError("终态提交前发现结果文件，拒绝覆盖")
    commit_complete_file(pending_path, results_path)
    return sealed_payload


def write_failed_result(
    config: dict[str, Any],
    status: str,
    check: dict[str, Any],
    error: Exception,
    resource_checks: list[dict[str, Any]],
    artifact_root: Path = OUT_DIR,
) -> dict[str, Any]:
    error_type = (
        "ResourceBudgetExceeded"
        if status == "FAILED_RESOURCE_BUDGET"
        else type(error).__name__
    )
    message = (
        ",".join(check["breaches"])
        if status == "FAILED_RESOURCE_BUDGET"
        else str(error)
    )
    payload = build_failed_result(
        config,
        status,
        check,
        error_type,
        message,
        root=artifact_root,
        resource_checks=resource_checks,
        sealed_archive_provenance=(
            error.sealed_archive_provenance
            if isinstance(error, ResourceBudgetExceeded)
            else None
        ),
    )
    validate_failed_result(payload, config, artifact_root)
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
            raise RuntimeError("v94 已有 formal run 持有 flock") from error
        if RESULTS_PATH.exists():
            verify_complete_payload()
            return
        started = time.monotonic()
        logger = RunLogger()
        resource_checks: list[dict[str, Any]] = []
        pending_results = OUT_DIR / f".cv_results.complete.{os.getpid()}.json"

        def checked_resource(phase: str, fold: int | None) -> dict[str, Any]:
            check = resource_check(config, started, phase, fold)
            resource_checks.append(check)
            require_resource_pass(config, check)
            return check

        try:
            logger.emit(
                "formal start; members=v80,v85,v87; v90 comparison-only; "
                "5-fold fit-only ECDF simplex"
            )
            checked_resource("BEFORE_INPUT_LOAD", None)
            (
                train,
                test,
                sample,
                y,
                member_oof,
                member_test,
                baseline_oof,
                baseline_test,
            ) = load_formal_inputs(config)
            checked_resource("AFTER_INPUT_LOAD", None)

            def guard(fold: int) -> None:
                checked_resource("AFTER_META_FOLD", fold)
                logger.emit(f"meta fold {fold}/{N_META_FOLDS} complete")

            meta = run_meta_cv(y, member_oof, member_test, fold_guard=guard)
            assert_baseline_reconstruction(
                config, meta, baseline_oof, baseline_test
            )
            evaluation = evaluate(config, y, meta, member_oof, member_test)
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
                f"delta_vs_v90={evaluation['oof_delta_vs_base']:+.9f} "
                f"wins={evaluation['meta_holdout_wins_vs_base']}/5 "
                f"decision={evaluation['decision']}"
            )
            after_outputs = checked_resource("AFTER_ALL_OUTPUTS", N_META_FOLDS)
            sources = build_sources(config, train, test)
            write_immutable_json(OUT_DIR / "sources.json", sources)
            sources_sha = sha256_file(OUT_DIR / "sources.json")
            provisional = build_complete_result(
                config,
                meta,
                evaluation,
                after_outputs,
                sources_sha,
                list(resource_checks),
            )
            _atomic_bytes(
                pending_results,
                (json.dumps(provisional, ensure_ascii=False, indent=2) + "\n").encode(
                    "utf-8"
                ),
            )
            verify_staged_complete_file(
                pending_results, {"AFTER_ALL_OUTPUTS"}
            )
            after_verify = checked_resource(
                "AFTER_STAGED_VERIFY_PRE_COMPLETE", N_META_FOLDS
            )
            post_verify_result = build_complete_result(
                config,
                meta,
                evaluation,
                after_verify,
                sources_sha,
                list(resource_checks),
            )
            _atomic_bytes(
                pending_results,
                (
                    json.dumps(post_verify_result, ensure_ascii=False, indent=2)
                    + "\n"
                ).encode("utf-8"),
            )
            verify_staged_complete_file(
                pending_results, {"AFTER_STAGED_VERIFY_PRE_COMPLETE"}
            )
            commit_guard = checked_resource(
                "PRE_COMMIT_AFTER_FINAL_FILE_VERIFY", N_META_FOLDS
            )
            final_result = build_complete_result(
                config,
                meta,
                evaluation,
                commit_guard,
                sources_sha,
                list(resource_checks),
            )
            _atomic_bytes(
                pending_results,
                (json.dumps(final_result, ensure_ascii=False, indent=2) + "\n").encode(
                    "utf-8"
                ),
            )
            verify_staged_complete_file(
                pending_results, {"PRE_COMMIT_AFTER_FINAL_FILE_VERIFY"}
            )
            third_verified_sha256 = sha256_file(pending_results)

            def build_sealed_payload(
                final_guard: dict[str, Any],
                sealed_checks: list[dict[str, Any]],
            ) -> dict[str, Any]:
                return build_complete_result(
                    config,
                    meta,
                    evaluation,
                    final_guard,
                    sources_sha,
                    sealed_checks,
                )

            seal_final_guard_and_commit(
                config,
                started,
                pending_results,
                RESULTS_PATH,
                resource_checks,
                third_verified_sha256,
                build_sealed_payload,
            )
            print(
                json.dumps(
                    {
                        "status": "COMPLETE_AND_VERIFIED",
                        "experiment_id": EXPERIMENT_ID,
                        "oof_auc": evaluation["oof_auc"],
                        "delta_vs_v90": evaluation["oof_delta_vs_base"],
                        "meta_holdout_wins": evaluation[
                            "meta_holdout_wins_vs_base"
                        ],
                        "decision": evaluation["decision"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        except ResourceBudgetExceeded as error:
            failure = write_failed_result(
                config,
                "FAILED_RESOURCE_BUDGET",
                error.check,
                error,
                resource_checks,
            )
            print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
        except Exception as error:
            completed_folds = sum(
                item["phase"] == "AFTER_META_FOLD" for item in resource_checks
            )
            check = resource_check(
                config, started, "FAILED_EXCEPTION", completed_folds
            )
            resource_checks.append(check)
            failure_status = (
                "FAILED_RESOURCE_BUDGET"
                if check["breaches"]
                else "FAILED_EXCEPTION"
            )
            failure = write_failed_result(
                config, failure_status, check, error, resource_checks
            )
            print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
            raise
        finally:
            if pending_results.exists():
                pending_results.unlink()


def smoke() -> dict[str, Any]:
    config = load_frozen_config()
    source_file_records(config)
    identities = source_row_identities(config)
    metadata = source_result_metadata(config)
    y = np.tile(np.array([0, 1], dtype=np.int8), 50)
    trend = np.linspace(0.01, 0.99, len(y))
    rng = np.random.default_rng(42)
    member_oof = {
        MEMBER_IDS[0]: np.clip(0.18 + 0.60 * y + 0.04 * trend, 0, 1),
        MEMBER_IDS[1]: np.clip(0.16 + 0.62 * y + 0.03 * trend[::-1], 0, 1),
        MEMBER_IDS[2]: np.clip(
            0.17 + 0.61 * y + 0.02 * rng.random(len(y)), 0, 1
        ),
    }
    member_test = {
        MEMBER_IDS[0]: np.linspace(0.05, 0.95, 31),
        MEMBER_IDS[1]: np.linspace(0.95, 0.05, 31),
        MEMBER_IDS[2]: np.linspace(0.10, 0.90, 31) ** 1.1,
    }
    meta = run_meta_cv(y, member_oof, member_test)
    synthetic_config = dict(config)
    synthetic_config["base_oof_auc"] = float(
        roc_auc_score(y, meta["baseline_oof"])
    )
    evaluation = evaluate(synthetic_config, y, meta, member_oof, member_test)
    assert_baseline_reconstruction(
        synthetic_config,
        meta,
        meta["baseline_oof"].copy(),
        meta["baseline_test"].copy(),
    )
    if not np.all(meta["coverage"] == 1):
        raise AssertionError("smoke coverage 失败")
    if any(
        not np.isclose(sum(row["selected_weights"].values()), 1.0)
        for row in meta["fold_rows"]
    ):
        raise AssertionError("smoke simplex 权重和错误")
    result = {
        "status": "SMOKE_OK_SYNTHETIC_ONLY_NO_REAL_PREDICTIONS_LOADED",
        "experiment_id": EXPERIMENT_ID,
        "member_ids": list(MEMBER_IDS),
        "strict_baseline": BASELINE_ID,
        "source_metadata_verified": sorted(metadata)
        == sorted([*MEMBER_IDS, BASELINE_ID]),
        "source_row_identity_direct_match": len(
            {canonical_json(value) for value in identities.values()}
        )
        == 1,
        "meta_fold_count": len(meta["fold_rows"]),
        "simplex_candidate_count": len(simplex_grid()),
        "fit_only_mid_ecdf": True,
        "baseline_reconstruction_exercised": True,
        "promotion_gate_exercised": evaluation["decision"] in {"PROMOTE", "REJECT"},
        "failure_contract_exercised": (
            failure_attribution_for(config, "COMPLETE", "PROMOTE") is None
            and isinstance(
                failure_attribution_for(config, "COMPLETE", "REJECT"), str
            )
            and isinstance(
                failure_attribution_for(
                    config, "FAILED_RESOURCE_BUDGET", "FAILED_RESOURCE_BUDGET"
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
