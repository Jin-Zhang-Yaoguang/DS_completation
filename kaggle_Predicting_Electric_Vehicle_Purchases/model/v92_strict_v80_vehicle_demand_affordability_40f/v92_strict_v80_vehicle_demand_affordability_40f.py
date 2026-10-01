# -*- coding: utf-8 -*-
"""C01：strict v80 加入冻结的车辆需求/可负担性逐行比值块。

默认仅执行 audit。正式训练必须显式传入 ``--mode train``。唯一模型变量是追加
三个逐行无标签静态特征；LightGBM、fold 数量和严格 nested-TE 协议不变。
"""

from __future__ import annotations

import argparse
import ast
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


EXPERIMENT_ID = "v92_strict_v80_vehicle_demand_affordability_40f"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
HISTORY_FORMULA_MANIFEST_PATH = OUT_DIR / "history_formula_manifest.json"
RECIPE_PATH = MODEL_DIR / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
V61_SCRIPT_PATH = (
    MODEL_DIR
    / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
    / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303.py"
)
V6_SCRIPT_PATH = MODEL_DIR / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
V80_DIR = MODEL_DIR / "v80_strict_v61_outer104395303_40f"
V80_SCRIPT_PATH = V80_DIR / "v80_strict_v61_outer104395303_40f.py"
V80_SOURCES_PATH = V80_DIR / "sources.json"
HISTORY_PATHS = {
    "v2_runner": MODEL_DIR
    / "v2_income_artifact_lgbm"
    / "v2_income_artifact_lgbm.py",
    "v6_runner": MODEL_DIR
    / "v6_multiscale_te_lgbm"
    / "v6_multiscale_te_lgbm.py",
    "v23_results": MODEL_DIR / "v23_income_env_subsidy_te" / "cv_results.json",
    "v40_results": MODEL_DIR / "v40_commute_bin1_te_lgbm" / "cv_results.json",
    "v45_log": MODEL_DIR / "v45_income_env_radius50_te_lgbm" / "train_log.txt",
    "v46_log": MODEL_DIR / "v46_replace_income_env_radius50" / "train_log.txt",
    "v53_results": MODEL_DIR / "v53_income_bin2_range_probe" / "probe_results.json",
    "v54_runner": MODEL_DIR / "v54_sparse_additive_probe" / "v54_sparse_additive_probe.py",
    "v65_results": MODEL_DIR
    / "v65_targeted_feature_duplication_probe"
    / "probe_results.json",
    "v65_runner": MODEL_DIR
    / "v65_targeted_feature_duplication_probe"
    / "v65_targeted_feature_duplication_probe.py",
    "v68_runner": MODEL_DIR
    / "v68_naji_accelerated_probe"
    / "v68_naji_accelerated_probe.py",
    "v69_runner": MODEL_DIR / "v69_naji_lgbm_20f" / "v69_naji_lgbm_20f.py",
    "v70_results": MODEL_DIR / "v70_naji_income_bin10_probe" / "probe_results.json",
    "v71_results": MODEL_DIR / "v71_naji_income_bin10_lgbm_20f" / "cv_results.json",
    "v72_runner": MODEL_DIR
    / "v72_naji_income_bin10_robust_ensemble"
    / "v72_naji_income_bin10_robust_ensemble.py",
    "v73_results": MODEL_DIR / "v73_naji_income_neighborhood_probe" / "probe_results.json",
    "v74_results": MODEL_DIR
    / "v74_naji_income_bin10_100_lgbm_20f"
    / "cv_results.json",
    "v74_runner": MODEL_DIR
    / "v74_naji_income_bin10_100_lgbm_20f"
    / "v74_naji_income_bin10_100_lgbm_20f.py",
    "v75_results": MODEL_DIR / "v75_naji_joint_te_probe" / "probe_results.json",
    "v76_results": MODEL_DIR / "v76_naji_income_env_lgbm_20f" / "cv_results.json",
    "v87_runner": MODEL_DIR
    / "v87_strict_v80_commute_charging_burden_40f"
    / "v87_strict_v80_commute_charging_burden_40f.py",
}
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
PROGRESS_PATH = OUT_DIR / "progress.jsonl"
LOG_PATH = OUT_DIR / "train_log.txt"
LOCK_PATH = OUT_DIR / "run.lock"

OUTER_SEED = 42
INNER_TE_SEED_BASE = 104_395_303
MODEL_SEED = 104_395_303
N_FOLDS = 40
N_INNER_FOLDS = 5
MODEL_DESCRIPTION = (
    "strict-v80 LightGBM plus vehicle_demand_affordability_v1, 40 folds"
)
FINAL_ARTIFACT_NAMES = [
    "oof_proba.npy",
    "test_proba.npy",
    "submission.csv",
    "feature_importance.csv",
    "sources.json",
    "train_log.txt",
    "progress.jsonl",
    *(f"checkpoints/fold_{fold:02d}.npz" for fold in range(1, N_FOLDS + 1)),
]
HISTORY_MAX_VERSION = 90
RATIO_FIELDS = frozenset(
    {
        "Annual_Income_USD",
        "Daily_Commute_km",
        "Number_of_Cars_Owned",
        "Household_Size",
        "Cost_Sensitivity",
    }
)
TARGET_RATIO_SIGNATURES = [
    "Daily_Commute_km__OVER__Number_of_Cars_Owned",
    "Annual_Income_USD__OVER__Number_of_Cars_Owned",
    "Annual_Income_USD__OVER__Daily_Commute_km+Number_of_Cars_Owned",
]


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


def _field_dependencies(node: ast.AST, aliases: dict[str, set[str]]) -> set[str]:
    """Conservatively propagate raw-field dependencies through one expression."""
    if isinstance(node, ast.Name):
        return set(aliases.get(node.id, set()))
    if isinstance(node, ast.Attribute) and node.attr in RATIO_FIELDS:
        return {node.attr}
    if isinstance(node, ast.Subscript):
        direct = {
            child.value
            for child in ast.walk(node.slice)
            if isinstance(child, ast.Constant)
            and isinstance(child.value, str)
            and child.value in RATIO_FIELDS
        }
        dependencies = set(direct)
        dependencies.update(_field_dependencies(node.value, aliases))
        return dependencies
    dependencies: set[str] = set()
    for child in ast.iter_child_nodes(node):
        dependencies.update(_field_dependencies(child, aliases))
    return dependencies


def _assigned_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for item in target.elts for name in _assigned_names(item)]
    return []


class _ScopeCollector(ast.NodeVisitor):
    """Collect a scope without descending into nested function/class definitions."""

    def __init__(self) -> None:
        self.assignments: list[tuple[list[str], ast.AST]] = []
        self.divisions: list[tuple[ast.AST, ast.AST, int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        return

    def visit_AsyncFunctionDef(  # noqa: N802
        self, node: ast.AsyncFunctionDef
    ) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        return

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        names = [name for target in node.targets for name in _assigned_names(target)]
        if names:
            self.assignments.append((names, node.value))
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if node.value is not None:
            names = _assigned_names(node.target)
            if names:
                self.assignments.append((names, node.value))
            self.visit(node.value)

    def visit_BinOp(self, node: ast.BinOp) -> None:  # noqa: N802
        if isinstance(node.op, ast.Div):
            self.divisions.append((node.left, node.right, node.lineno, "DIV"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        function_name = ""
        if isinstance(node.func, ast.Name):
            function_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            function_name = node.func.attr
        if function_name == "divide" and len(node.args) >= 2:
            self.divisions.append((node.args[0], node.args[1], node.lineno, "DIVIDE_CALL"))
        self.generic_visit(node)


def _ratio_signature(numerator: set[str], denominator: set[str]) -> str:
    return f"{'+'.join(sorted(numerator))}__OVER__{'+'.join(sorted(denominator))}"


def extract_cross_field_ratios(source: str) -> list[dict[str, Any]]:
    """Find aliased cross-field divisions from source without executing it."""
    tree = ast.parse(source)
    scopes: list[tuple[str, list[ast.stmt]]] = [("<module>", tree.body)]
    scopes.extend(
        (node.name, node.body)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    rows: list[dict[str, Any]] = []
    for scope_name, statements in scopes:
        collector = _ScopeCollector()
        synthetic_scope = ast.Module(body=statements, type_ignores=[])
        collector.visit(synthetic_scope)
        aliases: dict[str, set[str]] = {}
        for _ in range(len(collector.assignments) + 1):
            changed = False
            for names, value in collector.assignments:
                dependencies = _field_dependencies(value, aliases)
                for name in names:
                    combined = aliases.get(name, set()).union(dependencies)
                    if combined != aliases.get(name, set()):
                        aliases[name] = combined
                        changed = True
            if not changed:
                break
        for numerator_node, denominator_node, lineno, operator in collector.divisions:
            numerator = _field_dependencies(numerator_node, aliases)
            denominator = _field_dependencies(denominator_node, aliases)
            if not numerator or not denominator or len(numerator | denominator) < 2:
                continue
            rows.append(
                {
                    "scope": scope_name,
                    "line": int(lineno),
                    "operator": operator,
                    "numerator_fields": sorted(numerator),
                    "denominator_fields": sorted(denominator),
                    "signature": _ratio_signature(numerator, denominator),
                }
            )
    return sorted(
        rows,
        key=lambda row: (row["line"], row["scope"], row["signature"]),
    )


def discover_history_python_files(max_version: int = HISTORY_MAX_VERSION) -> list[Path]:
    files: list[Path] = []
    for directory in MODEL_DIR.iterdir():
        if not directory.is_dir():
            continue
        prefix = directory.name.split("_", 1)[0]
        if not prefix.startswith("v") or not prefix[1:].isdigit():
            continue
        version = int(prefix[1:])
        if 1 <= version <= max_version:
            files.extend(path for path in directory.rglob("*.py") if path.is_file())
    return sorted(files, key=lambda path: str(path.relative_to(PROJECT_DIR)))


def build_history_formula_manifest_payload(
    max_version: int = HISTORY_MAX_VERSION,
) -> dict[str, Any]:
    files = discover_history_python_files(max_version)
    records: list[dict[str, Any]] = []
    matches = {signature: [] for signature in TARGET_RATIO_SIGNATURES}
    for path in files:
        source = path.read_text(encoding="utf-8")
        ratios = extract_cross_field_ratios(source)
        relative = str(path.relative_to(PROJECT_DIR))
        for row in ratios:
            if row["signature"] in matches:
                matches[row["signature"]].append(
                    {"path": relative, "scope": row["scope"], "line": row["line"]}
                )
        records.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "cross_field_ratios": ratios,
            }
        )
    directories = sorted({record["path"].split("/")[1] for record in records})
    return {
        "schema_version": 1,
        "snapshot_rule": (
            "all recursive Python files in numeric model/vN_* directories with 1<=N<=90"
        ),
        "maximum_version_inclusive": max_version,
        "ratio_fields": sorted(RATIO_FIELDS),
        "target_ratio_signatures": TARGET_RATIO_SIGNATURES,
        "directories": directories,
        "file_count": len(records),
        "files": records,
        "target_ratio_matches": matches,
        "no_target_ratio_match": all(not value for value in matches.values()),
    }


def validate_history_formula_manifest(config: dict[str, Any]) -> dict[str, Any]:
    expected_relative = str(HISTORY_FORMULA_MANIFEST_PATH.relative_to(PROJECT_DIR))
    if config.get("history_formula_manifest_path") != expected_relative:
        raise ValueError("历史公式 manifest 路径漂移")
    if not HISTORY_FORMULA_MANIFEST_PATH.is_file():
        raise FileNotFoundError("历史公式 manifest 缺失")
    if sha256_file(HISTORY_FORMULA_MANIFEST_PATH) != config.get(
        "history_formula_manifest_sha256"
    ):
        raise ValueError("历史公式 manifest 哈希漂移")
    stored = json.loads(HISTORY_FORMULA_MANIFEST_PATH.read_text(encoding="utf-8"))
    recomputed = build_history_formula_manifest_payload(HISTORY_MAX_VERSION)
    if stored != recomputed:
        raise ValueError("历史公式 manifest 与当前 v1-v90 Python 快照不一致")
    required_versions = {f"v{version}" for version in range(84, 91)}
    covered_versions = {
        directory.split("_", 1)[0] for directory in stored["directories"]
    }
    if not required_versions.issubset(covered_versions):
        raise ValueError("历史公式 manifest 未完整覆盖 v84-v90")
    if stored.get("target_ratio_signatures") != TARGET_RATIO_SIGNATURES:
        raise ValueError("历史公式 manifest 的目标比值签名漂移")
    if stored.get("no_target_ratio_match") is not True or any(
        stored.get("target_ratio_matches", {}).get(signature)
        for signature in TARGET_RATIO_SIGNATURES
    ):
        raise ValueError("历史代码已命中 v92 三种跨字段比值，GO 失效")
    return {
        "path": expected_relative,
        "sha256": config["history_formula_manifest_sha256"],
        "maximum_version_inclusive": HISTORY_MAX_VERSION,
        "directory_count": len(stored["directories"]),
        "file_count": stored["file_count"],
        "required_v84_v90_covered": True,
        "target_ratio_matches": stored["target_ratio_matches"],
        "ast_recomputed_equal": True,
    }


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
    if config.get("base") != "v80_strict_v61_outer104395303_40f":
        raise ValueError("v92 base 必须是 strict v80")
    if float(config.get("base_oof_auc", -1)) != 0.946240610976364:
        raise ValueError("v80 基准 OOF 冻结值不一致")
    if int(config.get("base_outer_split_seed", -1)) != 104_395_303:
        raise ValueError("v80 基准 outer seed 冻结值不一致")
    if config.get("non_formal_prediction_access") != "HASH_ONLY_BYTES_NOT_PARSED":
        raise ValueError("audit/smoke 预测产物访问边界漂移")
    if (
        config.get("formal_v80_prediction_identity_required") is not True
        or config.get("complete_commit_protocol")
        != "STAGED_VERIFY_THEN_ATOMIC_COMPLETE"
        or config.get("complete_preverify_resource_phase")
        != "BEFORE_STAGED_VERIFY"
        or config.get("complete_postverify_resource_phase")
        != "AFTER_STAGED_VERIFY_PRE_COMPLETE"
        or config.get("formal_exception_close_protocol")
        != "ATOMIC_FAILED_EXCEPTION_INSIDE_FLOCK_WITH_INVALID_ARTIFACTS"
        or config.get("failed_artifacts_invalid_for_use") is not True
    ):
        raise ValueError("formal 身份/ staged COMPLETE / FAILED 产物合同漂移")
    if config.get("feature_block_name") != "vehicle_demand_affordability_v1":
        raise ValueError("唯一 feature block 名称漂移")
    if config.get("feature_block_columns") != [
        "mobility_commute_per_owned_car",
        "afford_income_per_postpurchase_car",
        "afford_income_per_postpurchase_car_km",
    ]:
        raise ValueError("冻结 feature block 列序漂移")
    expected_formulas = {
        "mobility_commute_per_owned_car": (
            "Daily_Commute_km / Number_of_Cars_Owned"
        ),
        "afford_income_per_postpurchase_car": (
            "Annual_Income_USD / (Number_of_Cars_Owned + 1)"
        ),
        "afford_income_per_postpurchase_car_km": (
            "Annual_Income_USD / ((Number_of_Cars_Owned + 1) * Daily_Commute_km)"
        ),
    }
    if config.get("feature_block_formulas") != expected_formulas:
        raise ValueError("冻结 feature block 公式漂移")
    if (
        config.get("unavailable_observed_fields")
        != ["Household_Size", "Cost_Sensitivity"]
        or config.get("candidate_selection_used_labels") is not False
        or "not observed household size" not in config.get("semantic_boundary", "")
    ):
        raise ValueError("字段可用性、无标签筛选或语义边界合同漂移")
    if (
        config.get("history_formula_manifest_path")
        != "model/v92_strict_v80_vehicle_demand_affordability_40f/history_formula_manifest.json"
        or not isinstance(config.get("history_formula_manifest_sha256"), str)
        or len(config["history_formula_manifest_sha256"]) != 64
        or int(config.get("history_formula_manifest_max_version", -1))
        != HISTORY_MAX_VERSION
    ):
        raise ValueError("历史公式 manifest 冻结合同漂移")
    if (
        config.get("feature_block_uses_labels") is not False
        or config.get("feature_block_is_row_wise_only") is not True
        or config.get("feature_block_changes_te_keys") is not False
    ):
        raise ValueError("feature block 边界必须是逐行、无标签且不改变 TE")
    expected_widths = {
        "expected_base_static_features": 62,
        "expected_added_static_features": 3,
        "expected_static_features": 65,
        "expected_te_features": 51,
        "expected_total_features": 116,
    }
    for key, expected in expected_widths.items():
        if int(config.get(key, -1)) != expected:
            raise ValueError(f"冻结特征宽度 {key} 必须为 {expected}")
    if (
        int(config.get("checkpoint_every_folds", -1)) != 1
        or int(config.get("observable_summary_every_folds", -1)) != 5
        or int(config.get("submission_budget", -1)) != 0
        or config.get("training_authorized_in_creation_task") is not False
    ):
        raise ValueError("checkpoint/汇报/提交/本次训练授权合同漂移")
    if (
        int(config.get("futility_check_after_folds", -1)) != 10
        or float(config.get("futility_delta_below", 0)) != -0.00005
        or int(config.get("futility_max_winning_buckets", -1)) != 4
    ):
        raise ValueError("10折 futility 必须冻结为 delta<-0.00005 且胜桶<=4")
    if (
        float(config.get("project_strength_minimum_oof_delta_vs_v80", -1))
        != 0.0001
        or int(
            config.get("project_strength_minimum_seed42_bucket_wins_vs_v80", -1)
        )
        != 24
    ):
        raise ValueError("项目强度门槛必须相对 v80 为+0.0001且24/40")
    if (
        float(config.get("minimum_oof_for_diversity_path", -1)) != 0.9452
        or config.get("diversity_only_allowed_for_fusion") is not False
        or config.get("diversity_only_eligible_for_separate_preregistration") is not True
    ):
        raise ValueError("多样性路径权限合同漂移")
    return config


def build_vehicle_demand_affordability_block(frame: pd.DataFrame) -> pd.DataFrame:
    """逐行、无标签地构造唯一冻结的车辆需求/可负担性比值块。"""
    numeric_inputs = [
        "Annual_Income_USD",
        "Daily_Commute_km",
        "Number_of_Cars_Owned",
    ]
    missing = [column for column in numeric_inputs if column not in frame]
    if missing:
        raise ValueError(f"vehicle_demand_affordability 原始列缺失：{missing}")
    numeric_values = frame[numeric_inputs].to_numpy(np.float64)
    if not np.isfinite(numeric_values).all() or (numeric_values <= 0.0).any():
        raise ValueError("vehicle_demand_affordability 三个原始分母必须有限且严格为正")
    income = frame["Annual_Income_USD"].to_numpy(np.float64)
    commute = frame["Daily_Commute_km"].to_numpy(np.float64)
    owned_cars = frame["Number_of_Cars_Owned"].to_numpy(np.float64)
    prospective_cars = owned_cars + 1.0
    block = pd.DataFrame(
        {
            "mobility_commute_per_owned_car": (commute / owned_cars).astype(
                np.float32
            ),
            "afford_income_per_postpurchase_car": (income / prospective_cars).astype(
                np.float32
            ),
            "afford_income_per_postpurchase_car_km": (
                income / (prospective_cars * commute)
            ).astype(np.float32),
        }
    )
    if not np.isfinite(block.to_numpy(np.float64)).all():
        raise ValueError("vehicle_demand_affordability 特征块含 NaN/Inf")
    return block


def append_feature_block(
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    train: pd.DataFrame,
    test: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if x_train.shape[1] != int(config["expected_base_static_features"]):
        raise ValueError("v80 基础 static feature 数量漂移")
    if x_test.shape[1] != int(config["expected_base_static_features"]):
        raise ValueError("v80 测试 static feature 数量漂移")
    train_block = build_vehicle_demand_affordability_block(train)
    test_block = build_vehicle_demand_affordability_block(test)
    expected_columns = config["feature_block_columns"]
    if list(train_block.columns) != expected_columns or list(test_block.columns) != expected_columns:
        raise ValueError("vehicle_demand_affordability 列序漂移")
    block_sha = hashlib.sha256("\n".join(expected_columns).encode("utf-8")).hexdigest()
    if block_sha != config["feature_block_column_order_sha256"]:
        raise ValueError("vehicle_demand_affordability 列序哈希漂移")
    overlap = set(x_train.columns).intersection(expected_columns)
    if overlap:
        raise ValueError(f"feature block 与 v80 static 列重名：{sorted(overlap)}")
    expanded_train = pd.concat(
        [x_train.reset_index(drop=True), train_block.reset_index(drop=True)], axis=1
    )
    expanded_test = pd.concat(
        [x_test.reset_index(drop=True), test_block.reset_index(drop=True)], axis=1
    )
    if (
        expanded_train.shape[1] != int(config["expected_static_features"])
        or expanded_test.shape[1] != int(config["expected_static_features"])
        or list(expanded_train.columns) != list(expanded_test.columns)
    ):
        raise ValueError("追加 feature block 后 static schema 异常")
    profile = {
        "name": config["feature_block_name"],
        "columns": expected_columns,
        "column_order_sha256": block_sha,
        "train_rows": len(train_block),
        "test_rows": len(test_block),
        "all_finite": True,
        "uses_labels": False,
        "row_wise_only": True,
        "train_min": {
            column: float(train_block[column].min()) for column in expected_columns
        },
        "train_max": {
            column: float(train_block[column].max()) for column in expected_columns
        },
        "test_min": {
            column: float(test_block[column].min()) for column in expected_columns
        },
        "test_max": {
            column: float(test_block[column].max()) for column in expected_columns
        },
    }
    return expanded_train, expanded_test, profile


def preregistered_futility_stop(
    config: dict[str, Any], completed: int, partial_delta: float, winning_buckets: int
) -> bool:
    return bool(
        completed == int(config["futility_check_after_folds"])
        and partial_delta < float(config["futility_delta_below"])
        and winning_buckets <= int(config["futility_max_winning_buckets"])
    )


def derive_candidate_decision(
    config: dict[str, Any], oof_auc: float, delta_vs_v80: float, wins_vs_v80: int
) -> dict[str, Any]:
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
        decision = "PROMOTE_SINGLE_MODEL"
    elif diversity_screen:
        decision = "ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_ONLY"
    else:
        decision = "STOP"
    return {
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
    config: dict[str, Any], baseline: dict[str, Any], runtime_version: str
) -> None:
    baseline_version = str(baseline.get("runtime", {}).get("lightgbm", ""))
    if config.get("required_lightgbm_version") != baseline_version:
        raise ValueError("冻结 LightGBM 版本与 strict v80 cv_results 不一致")
    if runtime_version != baseline_version:
        raise RuntimeError(
            "当前 LightGBM 版本与 strict v80 cv_results 不一致："
            f"runtime={runtime_version}, v80={baseline_version}"
        )


def validate_v80_contract(config: dict[str, Any], recipe: Any) -> dict[str, Any]:
    baseline = json.loads((V80_DIR / "cv_results.json").read_text(encoding="utf-8"))
    if baseline.get("status") != "COMPLETE":
        raise RuntimeError("formal trigger 未满足：strict v80 必须 COMPLETE")
    if baseline.get("experiment_id") != config["base"]:
        raise ValueError("strict v80 experiment_id 与冻结 base 不一致")
    if baseline["params"] != config["lightgbm_params"]:
        raise ValueError("冻结 LightGBM 参数与 strict v80 不一致")
    if baseline["te_keys"] != config["te_keys"]:
        raise ValueError("冻结 TE keys 与 strict v80 不一致")
    if baseline["smooths"] != config["smooths"]:
        raise ValueError("冻结 smoothing 与 strict v80 不一致")
    if int(baseline["n_folds"]) != N_FOLDS:
        raise ValueError("冻结 outer folds 与 strict v80 不一致")
    if int(baseline["outer_split_seed"]) != 104_395_303:
        raise ValueError("strict v80 基准 outer seed 历史合同漂移")
    if int(baseline["n_inner_folds"]) != N_INNER_FOLDS:
        raise ValueError("冻结 inner folds 与 strict v80 不一致")
    if int(baseline["inner_te_seed_base"]) != INNER_TE_SEED_BASE:
        raise ValueError("inner TE seed base 未保持 strict v80")
    if int(baseline["model_seed"]) != MODEL_SEED:
        raise ValueError("model seed 未保持 strict v80")
    if baseline["strict_prior_contract"] != config["strict_prior_contract"]:
        raise ValueError("strict prior 合同未保持 v80")
    if not np.isclose(
        baseline["oof_auc"], config["base_oof_auc"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("strict v80 OOF 与冻结 base_oof_auc 不一致")
    validate_lightgbm_version_contract(config, baseline, lgb.__version__)
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
            raise ValueError(f"{key} 未保持 strict v80 model seed")
    return baseline


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
        "history_formula_manifest": HISTORY_FORMULA_MANIFEST_PATH,
        "v61_wrapper": V61_SCRIPT_PATH,
        "v29_recipe": RECIPE_PATH,
        "v6_recipe": V6_SCRIPT_PATH,
        "strict_v80_runner": V80_SCRIPT_PATH,
        "strict_v80_config": V80_DIR / "frozen_config.json",
        "train_csv": DATA_DIR / "train.csv",
        "test_csv": DATA_DIR / "test.csv",
        "sample_submission_csv": DATA_DIR / "sample_submission.csv",
        "strict_v80_cv_results": V80_DIR / "cv_results.json",
        "strict_v80_sources": V80_SOURCES_PATH,
        "strict_v80_oof": V80_DIR / "oof_proba.npy",
        "strict_v80_test": V80_DIR / "test_proba.npy",
        **HISTORY_PATHS,
    }
    missing = [str(path) for path in source_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"运行合同来源文件缺失：{missing}")
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "frozen_config_sha256": sha256_file(CONFIG_PATH),
        "sources": {name: file_record(path) for name, path in source_paths.items()},
        "prediction_artifact_access": {
            "strict_v80_oof": "HASH_ONLY_BYTES_NOT_PARSED",
            "strict_v80_test": "HASH_ONLY_BYTES_NOT_PARSED",
            "non_formal_modes": ["audit", "smoke"],
        },
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


def validate_v80_prediction_identity(
    train: pd.DataFrame,
    test: pd.DataFrame,
    baseline: dict[str, Any],
    *,
    baseline_dir: Path = V80_DIR,
) -> dict[str, Any]:
    """仅供 formal/verify：绑定 v80 预测文件、来源清单与当前行身份。"""
    sources_path = baseline_dir / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    if sha256_file(sources_path) != baseline.get("sources_sha256"):
        raise ValueError("strict v80 sources.json 哈希与 cv_results 不一致")
    expected_ids = {
        "train_rows": len(train),
        "test_rows": len(test),
        "train_id_sha256": sha256_ids(train["id"]),
        "test_id_sha256": sha256_ids(test["id"]),
    }
    if sources.get("row_identity") != expected_ids:
        raise ValueError("strict v80 sources 行身份与当前 train/test 不一致")
    required_outputs = {
        "oof_proba": baseline_dir / "oof_proba.npy",
        "test_proba": baseline_dir / "test_proba.npy",
    }
    evidence: dict[str, Any] = {
        "sources_sha256": sha256_file(sources_path),
        "row_identity": expected_ids,
        "artifacts": {},
    }
    for name, path in required_outputs.items():
        record = sources.get("outputs", {}).get(name)
        if not isinstance(record, dict):
            raise ValueError(f"strict v80 sources 缺少 {name}")
        actual = file_record(path)
        if (
            record.get("path") != actual["path"]
            or record.get("sha256") != actual["sha256"]
            or int(record.get("bytes", -1)) != actual["bytes"]
            or baseline.get("artifact_sha256", {}).get(name) != actual["sha256"]
        ):
            raise ValueError(f"strict v80 {name} artifact/source 哈希合同不一致")
        evidence["artifacts"][name] = actual
    return evidence


def validate_data_contract(
    config: dict[str, Any], recipe: Any, *, load_predictions: bool = False
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    np.ndarray | None,
    np.ndarray | None,
    dict[str, Any],
]:
    train, test, sample = recipe.base.load_data()
    if len(train) != int(config["expected_train_rows"]):
        raise ValueError("train 行数与冻结配置不一致")
    if len(test) != int(config["expected_test_rows"]):
        raise ValueError("test 行数与冻结配置不一致")
    if not train[config["id_column"]].is_unique or not test[config["id_column"]].is_unique:
        raise ValueError("train/test id 必须唯一")
    if not sample[config["id_column"]].equals(test[config["id_column"]]):
        raise ValueError("sample_submission 与 test id 行序不一致")
    baseline = json.loads((V80_DIR / "cv_results.json").read_text(encoding="utf-8"))
    if (
        baseline.get("status") != "COMPLETE"
        or baseline.get("experiment_id") != config["base"]
        or not np.isclose(
            baseline.get("oof_auc", np.nan),
            config["base_oof_auc"],
            atol=1e-12,
            rtol=0.0,
        )
    ):
        raise ValueError("strict v80 冻结 JSON 基准合同不一致")
    if not load_predictions:
        return train, test, sample, None, None, baseline
    baseline_oof = np.load(V80_DIR / "oof_proba.npy", mmap_mode="r")
    baseline_test = np.load(V80_DIR / "test_proba.npy", mmap_mode="r")
    validate_v80_prediction_identity(train, test, baseline)
    validate_probability_array("strict_v80_oof", baseline_oof, len(train))
    validate_probability_array("strict_v80_test", baseline_test, len(test))
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    recomputed = float(roc_auc_score(y, baseline_oof))
    if not np.isclose(recomputed, baseline["oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("strict v80 OOF 复算与 cv_results 不一致")
    if not np.isclose(
        recomputed,
        config["base_oof_auc"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("strict v80 OOF 与冻结 base_oof_auc 不一致")
    return train, test, sample, baseline_oof, baseline_test, baseline


def validate_historical_overlap_audit(config: dict[str, Any]) -> dict[str, Any]:
    """把 GO 决策绑定到既有实验事实，避免把旧机制换名重跑。"""
    formula_manifest = validate_history_formula_manifest(config)
    v23 = json.loads(HISTORY_PATHS["v23_results"].read_text(encoding="utf-8"))
    v40 = json.loads(HISTORY_PATHS["v40_results"].read_text(encoding="utf-8"))
    v53 = json.loads(HISTORY_PATHS["v53_results"].read_text(encoding="utf-8"))
    v65 = json.loads(HISTORY_PATHS["v65_results"].read_text(encoding="utf-8"))
    v74 = json.loads(HISTORY_PATHS["v74_results"].read_text(encoding="utf-8"))
    v76 = json.loads(HISTORY_PATHS["v76_results"].read_text(encoding="utf-8"))
    if not np.isclose(v23["oof_auc"], 0.9458685953610309, atol=1e-12, rtol=0.0):
        raise ValueError("v23 历史结果漂移")
    if not np.isclose(v40["oof_auc"], 0.9459491015370579, atol=1e-12, rtol=0.0):
        raise ValueError("v40 历史结果漂移")
    if (
        not np.isclose(v53["mean_delta"], 0.0000014652427373640364, atol=1e-15, rtol=0.0)
        or int(v53["folds_won"]) != 2
    ):
        raise ValueError("v53 历史结果漂移")
    if "duplicating subsidy and environmental concern" not in v65["hypothesis"]:
        raise ValueError("v65 历史机制记录漂移")
    if not np.isclose(v74["oof_auc"], 0.9462245318765949, atol=1e-12, rtol=0.0):
        raise ValueError("v74 历史结果漂移")
    if not np.isclose(v76["oof_auc"], 0.9461686554466816, atol=1e-12, rtol=0.0):
        raise ValueError("v76 历史结果漂移")
    v45_folds = HISTORY_PATHS["v45_log"].read_text(encoding="utf-8").count("fold=")
    v46_folds = HISTORY_PATHS["v46_log"].read_text(encoding="utf-8").count("fold=")
    if (v45_folds, v46_folds) != (3, 3):
        raise ValueError("v45/v46 incomplete 历史边界漂移")
    train_columns = set(pd.read_csv(DATA_DIR / "train.csv", nrows=0).columns)
    test_columns = set(pd.read_csv(DATA_DIR / "test.csv", nrows=0).columns)
    original_columns = set(
        pd.read_csv(
            DATA_DIR
            / "original_dataset"
            / "EV_Adoption_and_Range_Anxiety_Dataset.csv",
            nrows=0,
        ).columns
    )
    unavailable_fields = {"Household_Size", "Cost_Sensitivity"}
    if any(unavailable_fields.intersection(columns) for columns in (train_columns, test_columns, original_columns)):
        raise ValueError("字段 schema 漂移：Household_Size/Cost_Sensitivity 意外出现")
    frozen_columns = set(config["feature_block_columns"])
    for name, path in HISTORY_PATHS.items():
        history_text = path.read_text(encoding="utf-8")
        repeated = frozen_columns.intersection(history_text)
        if repeated:
            raise ValueError(f"{name} 已出现 v92 冻结列，GO 判定失效：{sorted(repeated)}")
    return {
        "decision": "GO_DISTINCT_MECHANISM",
        "audited_versions": [
            "v2",
            "v6",
            "v23",
            "v40",
            "v45",
            "v46",
            "v53",
            "v54",
            "v65",
            "v68",
            "v69-v76",
            "v87",
        ],
        "nearest_precedent": "v80 raw fields plus v87 commute-to-charging ratios",
        "nearest_precedent_oof_auc": None,
        "nearest_precedent_boundary": (
            "v80 exposes income, commute and car count separately; v87 normalizes "
            "commute by charging access, not by owned vehicles or income"
        ),
        "household_size_available": False,
        "cost_sensitivity_available": False,
        "proxy_claim_forbidden": (
            "the frozen block represents vehicle capacity and income burden only; "
            "it must not be described as observed household size or cost preference"
        ),
        "candidate_selection_used_labels": False,
        "formula_manifest": formula_manifest,
        "v45_completed_folds": v45_folds,
        "v46_completed_folds": v46_folds,
        "exact_frozen_columns_absent_from_history": True,
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
def exclusive_run_lock(
    lock_path: Path,
    run_contract_sha256: str,
    *,
    failure_state: dict[str, Any] | None = None,
) -> Iterator[None]:
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
            raise RuntimeError(f"已有 v92 实例持有 flock：{owner}") from error
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
        try:
            yield
        except Exception as error:
            if acquired and failure_state is not None:
                close_formal_exception_state(failure_state, error)
            raise
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
        "prediction_artifact_access": run_contract["prediction_artifact_access"],
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
    baseline = validate_v80_contract(config, recipe)
    strict_prior_self_check()
    overlap_audit = validate_historical_overlap_audit(config)
    run_contract = build_run_contract()
    train, test, _, baseline_oof, baseline_test, _ = validate_data_contract(
        config, recipe, load_predictions=False
    )
    if baseline_oof is not None or baseline_test is not None:
        raise AssertionError("audit 禁止解析 strict v80 预测数组")
    x_train, x_test, _, _ = recipe.base.build_static_features(train, test)
    x_train, x_test, block_profile = append_feature_block(
        x_train, x_test, train, test, config
    )
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
                "status": "AUDIT_OK_NO_TRAINING_OR_PREDICTION_ARRAYS_READ",
                "experiment_id": EXPERIMENT_ID,
                "train_rows": len(train),
                "test_rows": len(test),
                "outer_split_seed": OUTER_SEED,
                "inner_te_seed_base": INNER_TE_SEED_BASE,
                "model_seed": MODEL_SEED,
                "runtime_lightgbm_version": lgb.__version__,
                "strict_v80_lightgbm_version": config["required_lightgbm_version"],
                "base": config["base"],
                "base_oof_auc": float(baseline["oof_auc"]),
                "strict_prior_self_check": True,
                "strict_v80_is_honest_baseline": True,
                "prediction_artifact_access": run_contract[
                    "prediction_artifact_access"
                ],
                "historical_overlap_audit": overlap_audit,
                "feature_block_profile": block_profile,
                "static_features": x_train.shape[1],
                "test_static_features": x_test.shape[1],
                "te_features": config["expected_te_features"],
                "total_features": config["expected_total_features"],
                "futility_rule": {
                    "after_folds": config["futility_check_after_folds"],
                    "delta_below": config["futility_delta_below"],
                    "winning_buckets_at_most": config[
                        "futility_max_winning_buckets"
                    ],
                },
                "project_strength_gate": {
                    "minimum_delta_vs_v80": config[
                        "project_strength_minimum_oof_delta_vs_v80"
                    ],
                    "minimum_seed42_bucket_wins": config[
                        "project_strength_minimum_seed42_bucket_wins_vs_v80"
                    ],
                },
                "diversity_only_allowed_for_fusion": False,
                "diversity_only_eligible_for_separate_preregistration": True,
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
    baseline = validate_v80_contract(config, recipe)
    strict_prior_self_check()
    validate_historical_overlap_audit(config)
    try:
        validate_lightgbm_version_contract(config, baseline, "0.0.0-smoke-mismatch")
    except RuntimeError as error:
        if "strict v80" not in str(error):
            raise
    else:
        raise AssertionError("不匹配的 LightGBM 版本未被拒绝")
    run_contract = build_run_contract()
    train, test, _, baseline_oof, baseline_test, _ = validate_data_contract(
        config, recipe, load_predictions=False
    )
    if baseline_oof is not None or baseline_test is not None:
        raise AssertionError("smoke 禁止解析 strict v80 预测数组")

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
    x_train, x_test, block_profile = append_feature_block(
        x_train, x_test, smoke_train, smoke_test, config
    )
    flipped_target = smoke_train.copy()
    flipped_target[config["target"]] = np.where(
        flipped_target[config["target"]].eq(config["positive_label"]), "No", "Yes"
    )
    if not build_vehicle_demand_affordability_block(smoke_train).equals(
        build_vehicle_demand_affordability_block(flipped_target)
    ):
        raise AssertionError("feature block 响应标签变化，不满足无标签合同")
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
        raise ValueError("smoke 特征宽度不是冻结的117")
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
    project_pass = derive_candidate_decision(
        config,
        float(config["base_oof_auc"]) + 0.0001,
        0.0001,
        24,
    )
    diversity_only = derive_candidate_decision(config, 0.9452, -0.001, 0)
    stop_decision = derive_candidate_decision(config, 0.945199, -0.001, 0)
    if (
        project_pass["decision"] != "PROMOTE_SINGLE_MODEL"
        or project_pass["allowed_for_fusion"] is not True
        or diversity_only["decision"]
        != "ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_ONLY"
        or diversity_only["allowed_for_fusion"] is not False
        or diversity_only["eligible_for_separate_preregistration"] is not True
        or stop_decision["decision"] != "STOP"
    ):
        raise AssertionError("项目强度/多样性权限推导 smoke 失败")
    if not preregistered_futility_stop(config, 10, -0.000051, 4):
        raise AssertionError("10折 futility 触发边界未生效")
    if (
        preregistered_futility_stop(config, 10, -0.00005, 4)
        or preregistered_futility_stop(config, 10, -0.000051, 5)
        or preregistered_futility_stop(config, 9, -0.000051, 4)
    ):
        raise AssertionError("10折 futility 非触发边界错误")
    with tempfile.TemporaryDirectory(prefix="v92_smoke_", dir=OUT_DIR) as temporary_dir:
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
        for fold in range(1, N_FOLDS + 1):
            (failure_checkpoint_dir / f"fold_{fold:02d}.npz").write_bytes(
                b"smoke-checkpoint-preservation"
            )
        fold_40_checkpoint = failure_checkpoint_dir / "fold_40.npz"
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
            [{} for _ in range(N_FOLDS)],
            [0.5 for _ in range(N_FOLDS)],
            [1 for _ in range(N_FOLDS)],
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
            or len(failed_evidence.get("preserved_checkpoints", [])) != N_FOLDS
            or failed_evidence.get("present_artifacts_are_invalid_for_use") is not True
            or len(failed_evidence.get("expected_artifacts", []))
            != len(FINAL_ARTIFACT_NAMES)
            or "checkpoints/fold_40.npz"
            not in failed_evidence.get("present_artifacts", [])
            or failed_evidence.get("missing_artifacts")
            != [
                name
                for name in FINAL_ARTIFACT_NAMES
                if not name.startswith("checkpoints/")
            ]
            or not fold_40_checkpoint.is_file()
            or (temporary_root / "cv_results.json.tmp").exists()
        ):
            raise AssertionError("资源超限 FAILED 原子证据 smoke 未通过")
        resource_failure_verification = verify_failed_closed(
            results_path=failure_path,
            checkpoint_dir=failure_checkpoint_dir,
        )
        if (
            resource_failure_verification["status"]
            != "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ"
        ):
            raise AssertionError("资源 FAILED 独立 verify smoke 未通过")

        futility_root = temporary_root / "futility"
        futility_root.mkdir()
        futility_checkpoints = futility_root / "checkpoints"
        futility_checkpoints.mkdir()
        for fold in range(1, 11):
            (futility_checkpoints / f"fold_{fold:02d}.npz").write_bytes(
                b"synthetic-futility-checkpoint"
            )
        futility_resource = make_resource_check(
            config,
            started_monotonic=time.monotonic(),
            phase="AFTER_FOLD",
            fold=10,
        )
        futility_path = futility_root / "cv_results.json"
        write_futility_failure(
            config,
            config_sha256=run_contract["frozen_config_sha256"],
            run_contract_sha256=run_contract["run_contract_sha256"],
            fold_rows=[{} for _ in range(10)],
            fold_scores=[0.5 for _ in range(10)],
            best_iterations=[1 for _ in range(10)],
            resource_checks=[futility_resource],
            partial_oof_auc=0.499,
            partial_v80_auc=0.5,
            winning_buckets=4,
            results_path=futility_path,
            checkpoint_dir=futility_checkpoints,
        )
        futility_failure = json.loads(futility_path.read_text(encoding="utf-8"))
        if (
            futility_failure.get("failure_attribution")
            != "PREREGISTERED_10_FOLD_FUTILITY"
            or futility_failure.get("completed_folds") != 10
            or futility_failure.get("present_artifacts_are_invalid_for_use") is not True
            or len(futility_failure.get("present_artifacts", [])) != 10
            or futility_failure.get("oof_auc") is not None
            or futility_failure.get("oof_delta_vs_base") is not None
        ):
            raise AssertionError("futility FAILED 统一 schema smoke 未通过")
        futility_failure_verification = verify_failed_closed(
            results_path=futility_path,
            checkpoint_dir=futility_checkpoints,
        )
        if (
            futility_failure_verification["status"]
            != "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ"
        ):
            raise AssertionError("futility FAILED 独立 verify smoke 未通过")

        exception_root = temporary_root / "exception"
        exception_root.mkdir()
        exception_checkpoints = exception_root / "checkpoints"
        exception_checkpoints.mkdir()
        for fold in range(1, 4):
            (exception_checkpoints / f"fold_{fold:02d}.npz").write_bytes(
                b"synthetic-exception-checkpoint"
            )
        exception_path = exception_root / "cv_results.json"
        exception_failure = write_exception_failure(
            config,
            error=RuntimeError("synthetic staged verify failure"),
            started_monotonic=time.monotonic(),
            config_sha256=run_contract["frozen_config_sha256"],
            run_contract_sha256=run_contract["run_contract_sha256"],
            fold_rows=[{} for _ in range(3)],
            fold_scores=[0.5 for _ in range(3)],
            best_iterations=[1 for _ in range(3)],
            resource_checks=[],
            results_path=exception_path,
            checkpoint_dir=exception_checkpoints,
        )
        if (
            exception_failure.get("failure_attribution") != "FAILED_EXCEPTION"
            or exception_failure.get("error_type") != "RuntimeError"
            or exception_failure.get("completed_folds") != 3
            or exception_failure.get("present_artifacts_are_invalid_for_use")
            is not True
            or exception_failure.get("oof_auc") is not None
        ):
            raise AssertionError("FAILED_EXCEPTION 统一 schema smoke 未通过")
        exception_verification = verify_failed_closed(
            results_path=exception_path,
            checkpoint_dir=exception_checkpoints,
        )
        if (
            exception_verification["status"]
            != "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ"
        ):
            raise AssertionError("FAILED_EXCEPTION 独立 verify smoke 未通过")

        synthetic_v80 = temporary_root / "synthetic_v80"
        synthetic_v80.mkdir()
        synthetic_train = pd.DataFrame({"id": [11, 12, 13]})
        synthetic_test = pd.DataFrame({"id": [21, 22]})
        synthetic_oof_path = synthetic_v80 / "oof_proba.npy"
        synthetic_test_path = synthetic_v80 / "test_proba.npy"
        np.save(synthetic_oof_path, np.asarray([0.1, 0.2, 0.3]))
        np.save(synthetic_test_path, np.asarray([0.4, 0.5]))
        synthetic_sources = {
            "row_identity": {
                "train_rows": 3,
                "test_rows": 2,
                "train_id_sha256": sha256_ids(synthetic_train["id"]),
                "test_id_sha256": sha256_ids(synthetic_test["id"]),
            },
            "outputs": {
                "oof_proba": file_record(synthetic_oof_path),
                "test_proba": file_record(synthetic_test_path),
            },
        }
        synthetic_sources_path = synthetic_v80 / "sources.json"
        atomic_write_json(synthetic_sources_path, synthetic_sources)
        synthetic_baseline = {
            "sources_sha256": sha256_file(synthetic_sources_path),
            "artifact_sha256": {
                "oof_proba": sha256_file(synthetic_oof_path),
                "test_proba": sha256_file(synthetic_test_path),
            },
        }
        validate_v80_prediction_identity(
            synthetic_train,
            synthetic_test,
            synthetic_baseline,
            baseline_dir=synthetic_v80,
        )
        altered_test = synthetic_test.copy()
        altered_test.loc[1, "id"] = 23
        try:
            validate_v80_prediction_identity(
                synthetic_train,
                altered_test,
                synthetic_baseline,
                baseline_dir=synthetic_v80,
            )
        except ValueError as error:
            if "行身份" not in str(error):
                raise
        else:
            raise AssertionError("strict v80 test ID 行序漂移未被拒绝")

        staged = {
            "status": "STAGED_COMPLETE_PENDING_VERIFY",
            "elapsed_seconds": futility_resource["wall_elapsed_seconds"],
            "wall_clock_elapsed_seconds": futility_resource["wall_elapsed_seconds"],
            "peak_rss_bytes": futility_resource["peak_rss_bytes"],
            "peak_rss_gib": futility_resource["peak_rss_gib"],
            "resource_checks": [futility_resource],
            "final_resource_check": futility_resource,
            "immutable_payload": "synthetic",
        }
        postverify = make_resource_check(
            config,
            started_monotonic=time.monotonic(),
            phase=config["complete_postverify_resource_phase"],
            fold=N_FOLDS,
        )
        final = json.loads(json.dumps(staged))
        final.update(
            {
                "status": "COMPLETE",
                "elapsed_seconds": postverify["wall_elapsed_seconds"],
                "wall_clock_elapsed_seconds": postverify["wall_elapsed_seconds"],
                "peak_rss_bytes": postverify["peak_rss_bytes"],
                "peak_rss_gib": postverify["peak_rss_gib"],
                "resource_checks": [futility_resource, postverify],
                "final_resource_check": postverify,
            }
        )
        validate_staged_complete_transition(staged, final, config)

    print(
        json.dumps(
            {
                "status": "SMOKE_OK_SYNTHETIC_ONLY_NO_PREDICTION_ARRAYS_READ",
                "prediction_artifact_access": run_contract[
                    "prediction_artifact_access"
                ],
                "strict_prior_self_check": True,
                "subset_train_rows": len(smoke_train),
                "subset_test_rows": len(smoke_test),
                "feature_block_profile": block_profile,
                "feature_block_label_invariance": True,
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
                "futility_failed_minimum_schema_verified": True,
                "failed_artifacts_explicitly_invalid": True,
                "failed_independent_verify_without_prediction_arrays": True,
                "formal_exception_failed_close_verified": True,
                "strict_v80_identity_and_artifact_hash_verified_synthetic": True,
                "staged_complete_transition_verified": True,
                "futility_boundaries_verified": True,
                "decision_permissions_verified": True,
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
    baseline_oof: np.ndarray,
    fold_rows: list[dict[str, Any]],
    latest_resource_check: dict[str, Any],
    trained_this_run: int,
    resumed_this_run: int,
) -> None:
    covered = coverage == 1
    partial_auc = float(roc_auc_score(y[covered], oof[covered]))
    baseline_auc = float(roc_auc_score(y[covered], baseline_oof[covered]))
    wins = int(sum(row["delta_vs_v80_same_seed42_bucket"] > 0 for row in fold_rows))
    payload = {
        "timestamp_utc": utc_now(),
        "evidence_level": "INTERIM_DIAGNOSTIC_NOT_FINAL",
        "completed_folds": completed,
        "total_folds": N_FOLDS,
        "trained_this_run": trained_this_run,
        "resumed_this_run": resumed_this_run,
        "covered_rows": int(covered.sum()),
        "partial_strict_oof_auc": partial_auc,
        "strict_v80_auc_same_rows": baseline_auc,
        "partial_delta_vs_v80": partial_auc - baseline_auc,
        "winning_seed42_buckets_vs_v80": wins,
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
        f"v80_same_rows={baseline_auc:.9f} "
        f"delta={partial_auc-baseline_auc:+.9f} wins={wins}/{completed} "
        f"trained={trained_this_run} resumed={resumed_this_run} "
        f"eta={payload['rough_eta_seconds']:.0f}s"
    )


def failure_artifact_inventory(
    *, artifact_root: Path, checkpoint_dir: Path
) -> dict[str, Any]:
    present: list[str] = []
    for name in FINAL_ARTIFACT_NAMES:
        path = (
            checkpoint_dir / Path(name).name
            if name.startswith("checkpoints/")
            else artifact_root / name
        )
        if path.is_file():
            present.append(name)
    return {
        "expected_artifacts": FINAL_ARTIFACT_NAMES,
        "present_artifacts": present,
        "missing_artifacts": [
            name for name in FINAL_ARTIFACT_NAMES if name not in present
        ],
        "present_artifacts_are_invalid_for_use": True,
    }


def validate_failed_result_schema(
    payload: dict[str, Any],
    config: dict[str, Any],
    *,
    artifact_root: Path,
    checkpoint_dir: Path,
) -> None:
    required = {
        "model",
        "n_folds",
        "fold_auc",
        "oof_auc",
        "base",
        "base_oof_auc",
        "oof_delta_vs_base",
        "params",
        "elapsed_seconds",
        "wall_elapsed_seconds",
        "peak_rss_bytes",
        "peak_rss_gib",
        "resource_budget",
        "resource_checks",
        "final_resource_check",
        "expected_artifacts",
        "present_artifacts",
        "missing_artifacts",
        "present_artifacts_are_invalid_for_use",
    }
    if payload.get("status") != "FAILED" or not required.issubset(payload):
        raise ValueError("FAILED 统一 schema 不完整")
    if (
        payload["model"] != MODEL_DESCRIPTION
        or payload["n_folds"] != N_FOLDS
        or payload["params"] != config["lightgbm_params"]
        or payload["oof_auc"] is not None
        or payload["base"] != config["base"]
        or payload["base_oof_auc"] != config["base_oof_auc"]
        or payload["oof_delta_vs_base"] is not None
        or payload["allowed_for_fusion"] is not False
        or payload["eligible_for_separate_preregistration"] is not False
        or payload["allowed_for_submission"] is not False
    ):
        raise ValueError("FAILED 统一模型/指标/权限合同错误")
    if len(payload["fold_auc"]) != int(payload["completed_folds"]):
        raise ValueError("FAILED fold_auc 与 completed_folds 不一致")
    final_check = payload["final_resource_check"]
    if not payload["resource_checks"] or payload["resource_checks"][-1] != final_check:
        raise ValueError("FAILED final_resource_check 不是资源序列末项")
    validate_recorded_resource_check(
        config,
        final_check,
        expected_phase=final_check["phase"],
        expected_fold=final_check["fold"],
        must_pass=False,
    )
    if not np.isclose(
        payload["elapsed_seconds"],
        final_check["wall_elapsed_seconds"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("FAILED elapsed_seconds 与最终资源记录不一致")
    if (
        not np.isclose(
            payload["wall_elapsed_seconds"],
            final_check["wall_elapsed_seconds"],
            atol=1e-12,
            rtol=0.0,
        )
        or int(payload["peak_rss_bytes"]) != int(final_check["peak_rss_bytes"])
        or not np.isclose(
            payload["peak_rss_gib"],
            final_check["peak_rss_gib"],
            atol=1e-12,
            rtol=0.0,
        )
        or payload["resource_budget"]
        != {
            "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
            "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
            "peak_rss_budget_gib": config["memory_budget_gb"],
        }
    ):
        raise ValueError("FAILED 墙钟/peak RSS/预算摘要不一致")
    attribution = payload.get("failure_attribution")
    if attribution == "PREREGISTERED_10_FOLD_FUTILITY":
        partial_delta = float(payload["partial_oof_auc"]) - float(
            payload["partial_v80_auc_same_rows"]
        )
        if (
            int(payload["completed_folds"]) != 10
            or not np.isclose(
                payload["partial_delta_vs_v80"],
                partial_delta,
                atol=1e-12,
                rtol=0.0,
            )
            or not preregistered_futility_stop(
                config,
                10,
                partial_delta,
                int(payload["winning_seed42_buckets_vs_v80"]),
            )
            or final_check["breaches"]
        ):
            raise ValueError("futility FAILED 无法从记录指标复算")
    elif attribution == "FAILED_EXCEPTION":
        if (
            final_check.get("phase") != "FAILED_EXCEPTION"
            or final_check.get("fold") != int(payload["completed_folds"])
            or not isinstance(payload.get("error_type"), str)
            or not payload["error_type"]
            or not isinstance(payload.get("error"), str)
            or payload.get("failure_phase") != "FAILED_EXCEPTION"
        ):
            raise ValueError("FAILED_EXCEPTION 缺少可复算的异常/资源证据")
    else:
        if (
            not isinstance(attribution, str)
            or not attribution
            or attribution.split("+") != final_check["breaches"]
            or final_check.get("phase") != "FAILED"
            or not final_check["breaches"]
            or payload.get("resource_at_failure") != final_check
        ):
            raise ValueError("资源 FAILED 缺少可复算的超限证据")
    inventory = failure_artifact_inventory(
        artifact_root=artifact_root, checkpoint_dir=checkpoint_dir
    )
    for key, expected in inventory.items():
        if payload.get(key) != expected:
            raise ValueError(f"FAILED 产物清单错误：{key}")


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
    preserved_checkpoints = sorted(
        path.name for path in target_checkpoint_dir.glob("fold_[0-9][0-9].npz")
    )
    artifact_root = target_results_path.parent
    payload = {
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
            "model": MODEL_DESCRIPTION,
            "n_folds": N_FOLDS,
            "fold_auc": fold_scores,
            "best_iterations": best_iterations,
            "fold_diagnostics": fold_rows,
            "resource_checks": resource_checks,
            "resource_at_failure": failure_check,
            "final_resource_check": failure_check,
            "elapsed_seconds": failure_check["wall_elapsed_seconds"],
            "wall_elapsed_seconds": failure_check["wall_elapsed_seconds"],
            "peak_rss_bytes": failure_check["peak_rss_bytes"],
            "peak_rss_gib": failure_check["peak_rss_gib"],
            "resource_budget": {
                "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
                "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
                "peak_rss_budget_gib": config["memory_budget_gb"],
            },
            "params": config["lightgbm_params"],
            "oof_auc": None,
            "base": config["base"],
            "base_oof_auc": config["base_oof_auc"],
            "oof_delta_vs_base": None,
            "strict_project_baseline": config["strict_project_baseline"],
            "strict_project_baseline_oof_auc": config[
                "strict_project_baseline_oof_auc"
            ],
            "oof_delta_vs_strict_project_baseline": None,
            "feature_block_name": config["feature_block_name"],
            "feature_block_columns": config["feature_block_columns"],
            "frozen_config_sha256": config_sha256,
            "run_contract_sha256": run_contract_sha256,
            "allowed_for_fusion": False,
            "eligible_for_separate_preregistration": False,
            "allowed_for_submission": False,
            "decision": "STOP",
            "preserved_checkpoints": preserved_checkpoints,
            **failure_artifact_inventory(
                artifact_root=artifact_root, checkpoint_dir=target_checkpoint_dir
            ),
        }
    validate_failed_result_schema(
        payload,
        config,
        artifact_root=artifact_root,
        checkpoint_dir=target_checkpoint_dir,
    )
    atomic_write_json(target_results_path, payload)


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


def write_futility_failure(
    config: dict[str, Any],
    *,
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
    partial_oof_auc: float,
    partial_v80_auc: float,
    winning_buckets: int,
    results_path: Path | None = None,
    checkpoint_dir: Path | None = None,
) -> None:
    completed = len(fold_rows)
    partial_delta = partial_oof_auc - partial_v80_auc
    if not preregistered_futility_stop(
        config, completed, partial_delta, winning_buckets
    ):
        raise ValueError("拒绝写入未满足预注册条件的 futility FAILED")
    target_results_path = results_path or (OUT_DIR / "cv_results.json")
    target_checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
    artifact_root = target_results_path.parent
    if not resource_checks:
        raise ValueError("futility FAILED 缺少资源记录")
    final_resource_check = resource_checks[-1]
    validate_recorded_resource_check(
        config,
        final_resource_check,
        expected_phase=final_resource_check["phase"],
        expected_fold=final_resource_check["fold"],
        must_pass=True,
    )
    preserved_checkpoints = sorted(
        path.name for path in target_checkpoint_dir.glob("fold_[0-9][0-9].npz")
    )
    payload = {
            "schema_version": 1,
            "status": "FAILED",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": True,
            "failed_at_utc": utc_now(),
            "failure_attribution": "PREREGISTERED_10_FOLD_FUTILITY",
            "failure_reason": "partial delta<-0.00005 and winning buckets<=4/10",
            "failure_phase": "AFTER_FOLD_FUTILITY_CHECK",
            "failure_fold": completed,
            "completed_folds": completed,
            "model": MODEL_DESCRIPTION,
            "n_folds": N_FOLDS,
            "fold_auc": fold_scores,
            "best_iterations": best_iterations,
            "fold_diagnostics": fold_rows,
            "partial_oof_auc": partial_oof_auc,
            "partial_v80_auc_same_rows": partial_v80_auc,
            "partial_delta_vs_v80": partial_delta,
            "oof_auc": None,
            "winning_seed42_buckets_vs_v80": winning_buckets,
            "futility_rule": {
                "check_after_folds": config["futility_check_after_folds"],
                "delta_below": config["futility_delta_below"],
                "maximum_winning_buckets": config[
                    "futility_max_winning_buckets"
                ],
                "passes_stop_rule": True,
            },
            "base": config["base"],
            "base_oof_auc": config["base_oof_auc"],
            "oof_delta_vs_base": None,
            "strict_project_baseline": config["strict_project_baseline"],
            "strict_project_baseline_oof_auc": config[
                "strict_project_baseline_oof_auc"
            ],
            "oof_delta_vs_strict_project_baseline": None,
            "feature_block_name": config["feature_block_name"],
            "feature_block_columns": config["feature_block_columns"],
            "resource_checks": resource_checks,
            "final_resource_check": final_resource_check,
            "elapsed_seconds": final_resource_check["wall_elapsed_seconds"],
            "wall_elapsed_seconds": final_resource_check[
                "wall_elapsed_seconds"
            ],
            "peak_rss_bytes": final_resource_check["peak_rss_bytes"],
            "peak_rss_gib": final_resource_check["peak_rss_gib"],
            "resource_budget": {
                "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
                "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
                "peak_rss_budget_gib": config["memory_budget_gb"],
            },
            "params": config["lightgbm_params"],
            "frozen_config_sha256": config_sha256,
            "run_contract_sha256": run_contract_sha256,
            "allowed_for_fusion": False,
            "eligible_for_separate_preregistration": False,
            "allowed_for_submission": False,
            "decision": "STOP",
            "preserved_checkpoints": preserved_checkpoints,
            **failure_artifact_inventory(
                artifact_root=artifact_root, checkpoint_dir=target_checkpoint_dir
            ),
        }
    validate_failed_result_schema(
        payload,
        config,
        artifact_root=artifact_root,
        checkpoint_dir=target_checkpoint_dir,
    )
    atomic_write_json(target_results_path, payload)


def write_exception_failure(
    config: dict[str, Any],
    *,
    error: Exception,
    started_monotonic: float,
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
    results_path: Path | None = None,
    checkpoint_dir: Path | None = None,
) -> dict[str, Any]:
    """将 formal 主体的普通异常原子关闭为不可用 FAILED_EXCEPTION。"""
    target_results_path = results_path or (OUT_DIR / "cv_results.json")
    target_checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
    artifact_root = target_results_path.parent
    completed = len(fold_rows)
    failure_check = make_resource_check(
        config,
        started_monotonic=started_monotonic,
        phase="FAILED_EXCEPTION",
        fold=completed,
    )
    resource_checks.append(failure_check)
    preserved_checkpoints = sorted(
        path.name for path in target_checkpoint_dir.glob("fold_[0-9][0-9].npz")
    )
    payload = {
        "schema_version": 1,
        "status": "FAILED",
        "experiment_id": EXPERIMENT_ID,
        "research_cycle": config["research_cycle"],
        "cycle_position": config["cycle_position"],
        "counts_toward_cycle": True,
        "failed_at_utc": failure_check["timestamp_utc"],
        "failure_attribution": "FAILED_EXCEPTION",
        "failure_reason": f"{type(error).__name__}: {error}",
        "failure_phase": "FAILED_EXCEPTION",
        "failure_fold": completed,
        "completed_folds": completed,
        "error_type": type(error).__name__,
        "error": str(error),
        "model": MODEL_DESCRIPTION,
        "n_folds": N_FOLDS,
        "fold_auc": fold_scores,
        "best_iterations": best_iterations,
        "fold_diagnostics": fold_rows,
        "params": config["lightgbm_params"],
        "oof_auc": None,
        "base": config["base"],
        "base_oof_auc": config["base_oof_auc"],
        "oof_delta_vs_base": None,
        "strict_project_baseline": config["strict_project_baseline"],
        "strict_project_baseline_oof_auc": config[
            "strict_project_baseline_oof_auc"
        ],
        "oof_delta_vs_strict_project_baseline": None,
        "feature_block_name": config["feature_block_name"],
        "feature_block_columns": config["feature_block_columns"],
        "resource_checks": resource_checks,
        "final_resource_check": failure_check,
        "elapsed_seconds": failure_check["wall_elapsed_seconds"],
        "wall_elapsed_seconds": failure_check["wall_elapsed_seconds"],
        "peak_rss_bytes": failure_check["peak_rss_bytes"],
        "peak_rss_gib": failure_check["peak_rss_gib"],
        "resource_budget": {
            "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
            "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
            "peak_rss_budget_gib": config["memory_budget_gb"],
        },
        "frozen_config_sha256": config_sha256,
        "run_contract_sha256": run_contract_sha256,
        "allowed_for_fusion": False,
        "eligible_for_separate_preregistration": False,
        "allowed_for_submission": False,
        "decision": "STOP",
        "preserved_checkpoints": preserved_checkpoints,
        **failure_artifact_inventory(
            artifact_root=artifact_root,
            checkpoint_dir=target_checkpoint_dir,
        ),
    }
    validate_failed_result_schema(
        payload,
        config,
        artifact_root=artifact_root,
        checkpoint_dir=target_checkpoint_dir,
    )
    atomic_write_json(target_results_path, payload)
    return payload


def close_formal_exception_state(
    state: dict[str, Any], error: Exception
) -> dict[str, Any] | None:
    """在原 formal flock 尚未释放时关闭异常，避免第二实例竞态。"""
    pending = state.get("pending_results_path")
    if isinstance(pending, Path):
        pending.unlink(missing_ok=True)
    if not state.get("formal_scope_started") or state.get("closed"):
        return None
    results_path = state["results_path"]
    if results_path.exists():
        state["closed"] = True
        return json.loads(results_path.read_text(encoding="utf-8"))
    payload = write_exception_failure(
        state["config"],
        error=error,
        started_monotonic=state["started_monotonic"],
        config_sha256=state["config_hash"],
        run_contract_sha256=state["run_contract_hash"],
        fold_rows=state["fold_rows"],
        fold_scores=state["fold_scores"],
        best_iterations=state["best_iterations"],
        resource_checks=state["resource_checks"],
        results_path=results_path,
        checkpoint_dir=CHECKPOINT_DIR,
    )
    state["exception_closed_inside_flock"] = True
    state["closed"] = True
    return payload


def _train_impl(state: dict[str, Any]) -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v80_contract(config, recipe)
    strict_prior_self_check()
    historical_overlap_audit = validate_historical_overlap_audit(config)
    run_contract = build_run_contract()
    config_hash = run_contract["frozen_config_sha256"]
    contract_hash = run_contract["run_contract_sha256"]
    logger = RunLogger(LOG_PATH)
    state.update(
        {
            "config": config,
            "config_hash": config_hash,
            "run_contract_hash": contract_hash,
            "logger": logger,
            "results_path": OUT_DIR / "cv_results.json",
        }
    )

    results_path = state["results_path"]
    if results_path.exists():
        existing = json.loads(results_path.read_text(encoding="utf-8"))
        if existing.get("status") == "COMPLETE":
            verify_complete()
            return
        raise RuntimeError("cv_results.json 已存在且非 COMPLETE，必须先人工审计")

    with exclusive_run_lock(
        LOCK_PATH, contract_hash, failure_state=state
    ):
        if results_path.exists():
            locked_existing = json.loads(results_path.read_text(encoding="utf-8"))
            if locked_existing.get("status") == "COMPLETE":
                verify_complete()
                return
            raise RuntimeError(
                "获得 flock 后发现非 COMPLETE cv_results，必须先人工审计"
            )
        started_monotonic = time.monotonic()
        state.update(
            {
                "formal_scope_started": True,
                "started_monotonic": started_monotonic,
                "fold_rows": [],
                "fold_scores": [],
                "best_iterations": [],
                "resource_checks": [],
            }
        )
        logger.emit(
            f"start mode=train config_sha256={config_hash} "
            f"run_contract_sha256={contract_hash}"
        )
        (
            train_frame,
            test_frame,
            sample,
            baseline_oof,
            baseline_test,
            baseline_results,
        ) = validate_data_contract(config, recipe, load_predictions=True)
        if baseline_oof is None or baseline_test is None:
            raise AssertionError("formal train 未加载 strict v80 基准预测")
        y = train_frame[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
        x_train, x_test, keys_train, keys_test = recipe.base.build_static_features(
            train_frame, test_frame
        )
        x_train, x_test, feature_block_profile = append_feature_block(
            x_train, x_test, train_frame, test_frame, config
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
            raise ValueError("完整特征 schema 不是冻结的 66 static + 51 TE")
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
        state.update(
            {
                "fold_rows": fold_rows,
                "fold_scores": fold_scores,
                "best_iterations": best_iterations,
                "resource_checks": resource_checks,
            }
        )
        futility_evidence: dict[str, Any] | None = None
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
            baseline_fold_auc = float(
                roc_auc_score(y[valid_idx], baseline_oof[valid_idx])
            )
            fold_scores.append(fold_auc)
            best_iterations.append(best_iteration)
            fold_rows.append(
                {
                    "fold": fold,
                    "inner_te_seed": INNER_TE_SEED_BASE + fold,
                    "valid_idx_sha256": hashlib.sha256(valid_idx.tobytes()).hexdigest(),
                    "strict_candidate_auc": fold_auc,
                    "strict_v80_auc_same_seed42_bucket": baseline_fold_auc,
                    "delta_vs_v80_same_seed42_bucket": fold_auc - baseline_fold_auc,
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
                    baseline_oof=baseline_oof,
                    fold_rows=fold_rows,
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
                partial_oof_auc = float(roc_auc_score(y[covered], oof[covered]))
                partial_v80_auc = float(
                    roc_auc_score(y[covered], baseline_oof[covered])
                )
                winning_buckets = int(
                    sum(
                        row["delta_vs_v80_same_seed42_bucket"] > 0
                        for row in fold_rows
                    )
                )
                futility_evidence = {
                    "check_after_folds": fold,
                    "partial_oof_auc": partial_oof_auc,
                    "partial_v80_auc_same_rows": partial_v80_auc,
                    "partial_delta_vs_v80": partial_oof_auc - partial_v80_auc,
                    "winning_seed42_buckets_vs_v80": winning_buckets,
                    "delta_below": config["futility_delta_below"],
                    "maximum_winning_buckets": config[
                        "futility_max_winning_buckets"
                    ],
                    "passes_stop_rule": preregistered_futility_stop(
                        config,
                        fold,
                        partial_oof_auc - partial_v80_auc,
                        winning_buckets,
                    ),
                }
                if preregistered_futility_stop(
                    config,
                    fold,
                    partial_oof_auc - partial_v80_auc,
                    winning_buckets,
                ):
                    write_futility_failure(
                        config,
                        config_sha256=config_hash,
                        run_contract_sha256=contract_hash,
                        fold_rows=fold_rows,
                        fold_scores=fold_scores,
                        best_iterations=best_iterations,
                        resource_checks=resource_checks,
                        partial_oof_auc=partial_oof_auc,
                        partial_v80_auc=partial_v80_auc,
                        winning_buckets=winning_buckets,
                    )
                    logger.emit(
                        "stopped reason=PREREGISTERED_10_FOLD_FUTILITY "
                        f"partial_delta={partial_oof_auc-partial_v80_auc:+.9f} "
                        f"wins={winning_buckets}/10"
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
        if futility_evidence is None or futility_evidence["passes_stop_rule"] is not False:
            raise ValueError("COMPLETE 前 10折 futility 证据缺失或本应停止")
        validate_probability_array("oof_proba", oof, len(train_frame))
        validate_probability_array("test_proba", test_prediction, len(test_frame))
        oof_auc = float(roc_auc_score(y, oof))
        baseline_auc = float(baseline_results["oof_auc"])
        delta_vs_v80 = oof_auc - baseline_auc
        oof_spearman = float(spearmanr(oof, baseline_oof).statistic)
        test_spearman = float(spearmanr(test_prediction, baseline_test).statistic)
        if not np.isfinite(oof_spearman) or not np.isfinite(test_spearman):
            raise ValueError("与 strict v80 的 Spearman 非有限值")
        wins_vs_v80 = int(
            sum(row["delta_vs_v80_same_seed42_bucket"] > 0 for row in fold_rows)
        )
        decision = derive_candidate_decision(
            config, oof_auc, delta_vs_v80, wins_vs_v80
        )

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
        preverify_resource_check = make_resource_check(
            config,
            started_monotonic=started_monotonic,
            phase=config["complete_preverify_resource_phase"],
            fold=N_FOLDS,
        )
        record_resource_check(resource_checks, preverify_resource_check)
        if stop_for_resource_breach(
            config,
            config_hash,
            contract_hash,
            fold_rows,
            fold_scores,
            best_iterations,
            resource_checks,
            preverify_resource_check,
            started_monotonic=started_monotonic,
            logger=logger,
        ):
            return
        results = {
            "schema_version": 1,
            "status": "STAGED_COMPLETE_PENDING_VERIFY",
            "experiment_id": EXPERIMENT_ID,
            "research_cycle": config["research_cycle"],
            "cycle_position": config["cycle_position"],
            "counts_toward_cycle": True,
            "competition": config["competition"],
            "model": MODEL_DESCRIPTION,
            "hypothesis": (
                "row-wise commute demand per owned vehicle and income capacity after "
                "adding one vehicle expose a low-depth mobility-affordability boundary "
                "that separate raw fields require extra LightGBM splits to approximate"
            ),
            "unique_primary_variable": config["unique_primary_variable"],
            "feature_block_name": config["feature_block_name"],
            "feature_block_columns": config["feature_block_columns"],
            "feature_block_profile": feature_block_profile,
            "historical_overlap_audit": historical_overlap_audit,
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
            "futility_check": futility_evidence,
            "winning_seed42_buckets_vs_v80": wins_vs_v80,
            "oof_auc": oof_auc,
            "base": config["base"],
            "base_oof_auc": baseline_auc,
            "oof_delta_vs_base": delta_vs_v80,
            "strict_project_baseline": config["strict_project_baseline"],
            "strict_project_baseline_oof_auc": baseline_auc,
            "oof_delta_vs_strict_project_baseline": delta_vs_v80,
            "oof_spearman_vs_base": oof_spearman,
            "oof_spearman_vs_strict_project_baseline": oof_spearman,
            "test_spearman_vs_base": test_spearman,
            "test_spearman_vs_strict_project_baseline": test_spearman,
            "comparison_boundary": (
                "overall OOF compares the same rows against strict v80; fold wins are "
                "fixed seed-42 row buckets applied to both complete OOF vectors"
            ),
            "project_strength_gate": {
                "minimum_oof_delta_vs_v80": config[
                    "project_strength_minimum_oof_delta_vs_v80"
                ],
                "minimum_seed42_bucket_wins_vs_v80": config[
                    "project_strength_minimum_seed42_bucket_wins_vs_v80"
                ],
                "passes": decision["project_strength"],
            },
            "diversity_screen": {
                "minimum_oof_auc": config["minimum_oof_for_diversity_path"],
                "passes": decision["diversity_screen"],
                "meaning": "only permits a later separately preregistered blend test",
            },
            "decision": decision["decision"],
            "allowed_for_fusion": decision["allowed_for_fusion"],
            "eligible_for_separate_preregistration": decision[
                "eligible_for_separate_preregistration"
            ],
            "allowed_for_submission": False,
            "cycle_count_update_required": True,
            "elapsed_seconds": preverify_resource_check["wall_elapsed_seconds"],
            "wall_clock_elapsed_seconds": preverify_resource_check[
                "wall_elapsed_seconds"
            ],
            "peak_rss_bytes": preverify_resource_check["peak_rss_bytes"],
            "peak_rss_gib": preverify_resource_check["peak_rss_gib"],
            "resource_budget": {
                "wall_clock_budget_seconds": config["wall_clock_budget_seconds"],
                "peak_rss_budget_bytes": config["peak_rss_budget_bytes"],
                "peak_rss_budget_gib": config["memory_budget_gb"],
            },
            "resource_checks": resource_checks,
            "final_resource_check": preverify_resource_check,
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
        pending_results_path = OUT_DIR / f".cv_results.staged.{os.getpid()}.json"
        state["pending_results_path"] = pending_results_path
        atomic_write_json(pending_results_path, results)
        try:
            verify_complete(results_path=pending_results_path, allow_staged=True)
        except Exception:
            pending_results_path.unlink(missing_ok=True)
            raise
        logger.emit(
            f"staged_verified strict_oof={oof_auc:.9f} "
            f"delta_vs_v80={delta_vs_v80:+.9f} wins={wins_vs_v80}/40 "
            f"decision={decision['decision']}"
        )
        postverify_resource_check = make_resource_check(
            config,
            started_monotonic=started_monotonic,
            phase=config["complete_postverify_resource_phase"],
            fold=N_FOLDS,
        )
        record_resource_check(resource_checks, postverify_resource_check)
        if stop_for_resource_breach(
            config,
            config_hash,
            contract_hash,
            fold_rows,
            fold_scores,
            best_iterations,
            resource_checks,
            postverify_resource_check,
            started_monotonic=started_monotonic,
            logger=logger,
        ):
            pending_results_path.unlink(missing_ok=True)
            return
        staged_results = json.loads(
            pending_results_path.read_text(encoding="utf-8")
        )
        results["status"] = "COMPLETE"
        results["final_resource_check"] = postverify_resource_check
        results["elapsed_seconds"] = postverify_resource_check[
            "wall_elapsed_seconds"
        ]
        results["wall_clock_elapsed_seconds"] = postverify_resource_check[
            "wall_elapsed_seconds"
        ]
        results["peak_rss_bytes"] = postverify_resource_check["peak_rss_bytes"]
        results["peak_rss_gib"] = postverify_resource_check["peak_rss_gib"]
        validate_staged_complete_transition(staged_results, results, config)
        atomic_write_json(pending_results_path, results)
        os.replace(pending_results_path, results_path)
        state["closed"] = True


def train() -> None:
    state: dict[str, Any] = {}
    _train_impl(state)


def verify_source_contract(
    sources: dict[str, Any], results: dict[str, Any]
) -> None:
    stored_payload = {
        "experiment_id": sources["experiment_id"],
        "frozen_config_sha256": sources["frozen_config_sha256"],
        "sources": sources["code_and_inputs"],
        "prediction_artifact_access": sources["prediction_artifact_access"],
        "runtime": sources["runtime"],
    }
    if sha256_json(stored_payload) != sources["run_contract_sha256"]:
        raise ValueError("sources.json 运行合同哈希无法复算")
    if results["run_contract_sha256"] != sources["run_contract_sha256"]:
        raise ValueError("cv_results 与 sources 的运行合同哈希不一致")
    if sources.get("prediction_artifact_access") != {
        "strict_v80_oof": "HASH_ONLY_BYTES_NOT_PARSED",
        "strict_v80_test": "HASH_ONLY_BYTES_NOT_PARSED",
        "non_formal_modes": ["audit", "smoke"],
    }:
        raise ValueError("sources 预测产物访问边界不一致")
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


def validate_staged_complete_transition(
    staged: dict[str, Any], final: dict[str, Any], config: dict[str, Any]
) -> None:
    """只允许在 staged 完整验证后追加一次资源检查并改为 COMPLETE。"""
    if staged.get("status") != "STAGED_COMPLETE_PENDING_VERIFY":
        raise ValueError("staged 结果状态错误")
    if final.get("status") != "COMPLETE":
        raise ValueError("最终结果状态错误")
    mutable = {
        "status",
        "elapsed_seconds",
        "wall_clock_elapsed_seconds",
        "peak_rss_bytes",
        "peak_rss_gib",
        "resource_checks",
        "final_resource_check",
    }
    if set(staged) != set(final):
        raise ValueError("staged→COMPLETE 字段 schema 发生变化")
    for key in set(staged).difference(mutable):
        if final[key] != staged[key]:
            raise ValueError(f"staged→COMPLETE 非授权字段改变：{key}")
    staged_checks = staged.get("resource_checks", [])
    final_checks = final.get("resource_checks", [])
    if (
        len(final_checks) != len(staged_checks) + 1
        or final_checks[:-1] != staged_checks
    ):
        raise ValueError("staged→COMPLETE 必须仅追加一次资源检查")
    postverify_check = final_checks[-1]
    validate_recorded_resource_check(
        config,
        postverify_check,
        expected_phase=config["complete_postverify_resource_phase"],
        expected_fold=N_FOLDS,
        must_pass=True,
    )
    if final.get("final_resource_check") != postverify_check:
        raise ValueError("COMPLETE final_resource_check 不是验证后资源检查")
    expected_summary = {
        "elapsed_seconds": postverify_check["wall_elapsed_seconds"],
        "wall_clock_elapsed_seconds": postverify_check["wall_elapsed_seconds"],
        "peak_rss_bytes": postverify_check["peak_rss_bytes"],
        "peak_rss_gib": postverify_check["peak_rss_gib"],
    }
    for key, expected in expected_summary.items():
        if final.get(key) != expected:
            raise ValueError(f"COMPLETE {key} 未纳入 staged verify 资源")


def verify_failed_closed(
    *, results_path: Path | None = None, checkpoint_dir: Path | None = None
) -> dict[str, Any]:
    """独立验证已关闭 FAILED；不解析任何预测或 checkpoint 数组。"""
    config = load_frozen_config()
    run_contract = build_run_contract()
    target_results_path = results_path or (OUT_DIR / "cv_results.json")
    target_checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
    results = json.loads(target_results_path.read_text(encoding="utf-8"))
    if results.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("FAILED experiment_id 不一致")
    if results.get("frozen_config_sha256") != run_contract["frozen_config_sha256"]:
        raise ValueError("FAILED 冻结配置哈希漂移")
    if results.get("run_contract_sha256") != run_contract["run_contract_sha256"]:
        raise ValueError("FAILED runner/配置/输入合同哈希漂移")
    validate_failed_result_schema(
        results,
        config,
        artifact_root=target_results_path.parent,
        checkpoint_dir=target_checkpoint_dir,
    )
    return {
        "status": "FAILED_CLOSED_AND_VERIFIED_WITHOUT_PREDICTION_ARRAY_READ",
        "experiment_id": EXPERIMENT_ID,
        "failure_attribution": results["failure_attribution"],
        "completed_folds": results["completed_folds"],
        "present_artifacts_are_invalid_for_use": True,
    }


def verify_complete(
    *, results_path: Path | None = None, allow_staged: bool = False
) -> dict[str, Any]:
    config = load_frozen_config()
    recipe = load_recipe()
    validate_v80_contract(config, recipe)
    strict_prior_self_check()
    historical_overlap_audit = validate_historical_overlap_audit(config)
    (
        train,
        test,
        sample,
        baseline_oof,
        baseline_test,
        baseline_results,
    ) = validate_data_contract(config, recipe, load_predictions=True)
    if baseline_oof is None or baseline_test is None:
        raise AssertionError("verify 未加载 strict v80 基准预测")
    target_results_path = results_path or (OUT_DIR / "cv_results.json")
    paths = {
        "cv_results": target_results_path,
        "sources": OUT_DIR / "sources.json",
        "oof_proba": OUT_DIR / "oof_proba.npy",
        "test_proba": OUT_DIR / "test_proba.npy",
        "submission": OUT_DIR / "submission.csv",
        "feature_importance": OUT_DIR / "feature_importance.csv",
        "train_log": LOG_PATH,
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"待验证产物缺失：{missing}")
    results = json.loads(paths["cv_results"].read_text(encoding="utf-8"))
    sources = json.loads(paths["sources"].read_text(encoding="utf-8"))
    expected_status = (
        "STAGED_COMPLETE_PENDING_VERIFY" if allow_staged else "COMPLETE"
    )
    if (
        results.get("status") != expected_status
        or results.get("experiment_id") != EXPERIMENT_ID
    ):
        raise ValueError("cv_results staged/COMPLETE/experiment_id 合同不一致")
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
        or results["inner_te_seeds"]
        != [INNER_TE_SEED_BASE + fold for fold in range(1, N_FOLDS + 1)]
        or results["params"] != config["lightgbm_params"]
        or results["smooths"] != config["smooths"]
        or results["te_keys"] != config["te_keys"]
    ):
        raise ValueError("cv_results 随机源或 strict prior 合同不一致")
    if (
        results.get("base") != config["base"]
        or results.get("strict_project_baseline")
        != config["strict_project_baseline"]
        or not np.isclose(
            results["base_oof_auc"], config["base_oof_auc"], atol=1e-12, rtol=0.0
        )
        or not np.isclose(
            results["strict_project_baseline_oof_auc"],
            config["strict_project_baseline_oof_auc"],
            atol=1e-12,
            rtol=0.0,
        )
        or results.get("historical_overlap_audit") != historical_overlap_audit
    ):
        raise ValueError("cv_results strict v80 基准或历史审计合同不一致")

    x_train, x_test, _, _ = recipe.base.build_static_features(train, test)
    x_train, x_test, feature_block_profile = append_feature_block(
        x_train, x_test, train, test, config
    )
    expected_te_names = [
        f"te_{key}_m{smooth:g}"
        for key in config["te_keys"]
        for smooth in config["smooths"]
    ]
    if (
        int(results["static_feature_count"]) != x_train.shape[1]
        or x_train.shape[1] != int(config["expected_static_features"])
        or x_test.shape[1] != int(config["expected_static_features"])
        or results.get("feature_block_profile") != feature_block_profile
        or results.get("feature_block_columns") != config["feature_block_columns"]
        or int(results["te_feature_count"]) != len(expected_te_names)
        or int(results["feature_count"])
        != x_train.shape[1] + len(expected_te_names)
    ):
        raise ValueError("COMPLETE feature block schema/profile 复算不一致")

    resource_checks = results.get("resource_checks", [])
    expected_resource_checks = N_FOLDS * 2 + (2 if allow_staged else 3)
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
    after_folds_check = resource_checks[N_FOLDS * 2]
    before_staged_verify_check = resource_checks[N_FOLDS * 2 + 1]
    validate_recorded_resource_check(
        config,
        after_folds_check,
        expected_phase="AFTER_ALL_FOLDS",
        expected_fold=N_FOLDS,
        must_pass=True,
    )
    validate_recorded_resource_check(
        config,
        before_staged_verify_check,
        expected_phase=config["complete_preverify_resource_phase"],
        expected_fold=N_FOLDS,
        must_pass=True,
    )
    tail_checks = [after_folds_check, before_staged_verify_check]
    if allow_staged:
        final_resource_check = before_staged_verify_check
    else:
        after_staged_verify_check = resource_checks[N_FOLDS * 2 + 2]
        validate_recorded_resource_check(
            config,
            after_staged_verify_check,
            expected_phase=config["complete_postverify_resource_phase"],
            expected_fold=N_FOLDS,
            must_pass=True,
        )
        tail_checks.append(after_staged_verify_check)
        final_resource_check = after_staged_verify_check
    for check in tail_checks:
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
        raise ValueError("待验证结果的最终资源摘要与资源检查不一致")
    if results.get("final_resource_check") != final_resource_check:
        raise ValueError("顶层 final_resource_check 与资源序列不一致")
    if not np.isclose(
        results["elapsed_seconds"],
        final_resource_check["wall_elapsed_seconds"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("待验证结果 elapsed_seconds 与最终墙钟检查不一致")
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
        baseline_fold_auc = float(
            roc_auc_score(y[valid_idx], baseline_oof[valid_idx])
        )
        if (
            int(diagnostic["fold"]) != fold
            or int(diagnostic["inner_te_seed"]) != INNER_TE_SEED_BASE + fold
            or int(diagnostic["best_iteration"]) != checkpoint["best_iteration"]
            or not np.isclose(
                diagnostic["strict_candidate_auc"], fold_auc, atol=1e-12, rtol=0.0
            )
            or not np.isclose(
                diagnostic["strict_v80_auc_same_seed42_bucket"],
                baseline_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
            or not np.isclose(
                diagnostic["delta_vs_v80_same_seed42_bucket"],
                fold_auc - baseline_fold_auc,
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

    first_ten_idx = np.concatenate([valid_idx for _, valid_idx in folds[:10]])
    partial_oof_auc = float(roc_auc_score(y[first_ten_idx], rebuilt_oof[first_ten_idx]))
    partial_v80_auc = float(
        roc_auc_score(y[first_ten_idx], baseline_oof[first_ten_idx])
    )
    first_ten_wins = int(
        sum(
            row["delta_vs_v80_same_seed42_bucket"] > 0
            for row in results["fold_diagnostics"][:10]
        )
    )
    expected_futility_stop = preregistered_futility_stop(
        config,
        10,
        partial_oof_auc - partial_v80_auc,
        first_ten_wins,
    )
    futility_check = results.get("futility_check", {})
    if (
        int(futility_check.get("check_after_folds", -1)) != 10
        or not np.isclose(
            futility_check.get("partial_oof_auc", np.nan),
            partial_oof_auc,
            atol=1e-12,
            rtol=0.0,
        )
        or not np.isclose(
            futility_check.get("partial_v80_auc_same_rows", np.nan),
            partial_v80_auc,
            atol=1e-12,
            rtol=0.0,
        )
        or not np.isclose(
            futility_check.get("partial_delta_vs_v80", np.nan),
            partial_oof_auc - partial_v80_auc,
            atol=1e-12,
            rtol=0.0,
        )
        or int(futility_check.get("winning_seed42_buckets_vs_v80", -1))
        != first_ten_wins
        or bool(futility_check.get("passes_stop_rule")) != expected_futility_stop
        or expected_futility_stop
    ):
        raise ValueError("10折 futility 证据复算不一致或 COMPLETE 本应停止")

    recomputed_oof_auc = float(roc_auc_score(y, rebuilt_oof))
    if not np.isclose(recomputed_oof_auc, results["oof_auc"], atol=1e-12, rtol=0.0):
        raise ValueError("整体 OOF AUC 复算不一致")
    delta_vs_v80 = recomputed_oof_auc - float(baseline_results["oof_auc"])
    for key in ("oof_delta_vs_base", "oof_delta_vs_strict_project_baseline"):
        if not np.isclose(delta_vs_v80, results[key], atol=1e-12, rtol=0.0):
            raise ValueError(f"{key} 复算不一致")
    rebuilt_oof_spearman = float(spearmanr(rebuilt_oof, baseline_oof).statistic)
    rebuilt_test_spearman = float(spearmanr(rebuilt_test, baseline_test).statistic)
    for key in (
        "oof_spearman_vs_base",
        "oof_spearman_vs_strict_project_baseline",
    ):
        if not np.isclose(
            rebuilt_oof_spearman, results[key], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{key} 复算不一致")
    for key in (
        "test_spearman_vs_base",
        "test_spearman_vs_strict_project_baseline",
    ):
        if not np.isclose(
            rebuilt_test_spearman, results[key], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{key} 复算不一致")

    wins_vs_v80 = int(
        sum(
            row["delta_vs_v80_same_seed42_bucket"] > 0
            for row in results["fold_diagnostics"]
        )
    )
    if int(results["winning_seed42_buckets_vs_v80"]) != wins_vs_v80:
        raise ValueError("winning_seed42_buckets_vs_v80 复算不一致")
    expected = derive_candidate_decision(
        config, recomputed_oof_auc, delta_vs_v80, wins_vs_v80
    )
    expected_project_gate = {
        "minimum_oof_delta_vs_v80": config[
            "project_strength_minimum_oof_delta_vs_v80"
        ],
        "minimum_seed42_bucket_wins_vs_v80": config[
            "project_strength_minimum_seed42_bucket_wins_vs_v80"
        ],
        "passes": expected["project_strength"],
    }
    expected_diversity_screen = {
        "minimum_oof_auc": config["minimum_oof_for_diversity_path"],
        "passes": expected["diversity_screen"],
        "meaning": "only permits a later separately preregistered blend test",
    }
    if results.get("project_strength_gate") != expected_project_gate:
        raise ValueError("project_strength_gate 复算不一致")
    if results.get("diversity_screen") != expected_diversity_screen:
        raise ValueError("diversity_screen 复算不一致")
    for key in (
        "decision",
        "allowed_for_fusion",
        "eligible_for_separate_preregistration",
    ):
        if results.get(key) != expected[key]:
            raise ValueError(f"{key} 未由重建结果正确推导")
    if (
        not expected["project_strength"]
        and expected["diversity_screen"]
        and results["allowed_for_fusion"] is not False
    ):
        raise ValueError("diversity-only 不得直接进入融合")
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
    if set(importance["feature"]) != set(x_train.columns).union(expected_te_names):
        raise ValueError("feature_importance 特征集合与冻结 schema 不一致")
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

    verification = {
        "status": (
            "STAGED_COMPLETE_REBUILT_FROM_40_CHECKPOINTS_AND_VERIFIED"
            if allow_staged
            else "COMPLETE_REBUILT_FROM_40_CHECKPOINTS_AND_VERIFIED"
        ),
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
    }
    if not allow_staged:
        print(json.dumps(verification, ensure_ascii=False, indent=2))
    return verification


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
        results_path = OUT_DIR / "cv_results.json"
        stored = json.loads(results_path.read_text(encoding="utf-8"))
        if stored.get("status") == "FAILED":
            print(
                json.dumps(
                    verify_failed_closed(), ensure_ascii=False, indent=2
                )
            )
        else:
            verify_complete()
    else:
        train()


if __name__ == "__main__":
    main()
