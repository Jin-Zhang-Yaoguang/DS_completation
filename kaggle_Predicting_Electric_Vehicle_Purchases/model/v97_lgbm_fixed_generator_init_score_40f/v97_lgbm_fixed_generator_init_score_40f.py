# -*- coding: utf-8 -*-
"""C01-14：strict v96 配方 + 冻结公开生成公式 LightGBM init_score。

默认仅执行 audit。正式训练必须显式传入 ``--mode train``。相对已独立完成的
v96，唯一科学变量是固定生成公式 margin 的 init/eval-init 注入与 raw residual
重建；特征、切分、TE、LightGBM 参数和资源合同均不变。
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import fcntl
import gc
import hashlib
import importlib.util
import io
import json
import os
import platform
import resource
import stat
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
from scipy.special import expit
from scipy.stats import norm, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


EXPERIMENT_ID = "v97_lgbm_fixed_generator_init_score_40f"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
DATA_DIR = PROJECT_DIR / "data"
CONFIG_PATH = OUT_DIR / "frozen_config.json"
HISTORY_FORMULA_MANIFEST_PATH = OUT_DIR / "history_formula_manifest.json"
PREFLIGHT_PROBE_PATH = OUT_DIR / "preflight_probe_evidence.json"
PUBLIC_SOURCE_EVIDENCE_PATH = OUT_DIR / "public_source_evidence.json"
PREFLIGHT_REPORT_PATH = OUT_DIR / "preflight_report.json"
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
V96_DIR = MODEL_DIR / "v96_strict_v80_outer42_matched_control_40f"
V96_SCRIPT_PATH = V96_DIR / "v96_strict_v80_outer42_matched_control_40f.py"
V96_SOURCES_PATH = V96_DIR / "sources.json"
COMPARISON_DIRS = {
    "v80_strict_v61_outer104395303_40f": V80_DIR,
    "v90_v89_member_verify_budget_retry": MODEL_DIR
    / "v90_v89_member_verify_budget_retry",
    "v95_v94_source_verifier_adapter_retry": MODEL_DIR
    / "v95_v94_source_verifier_adapter_retry",
}
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
MODEL_DESCRIPTION = "strict-v96 LightGBM plus frozen generator init_score, 40 folds"
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
HISTORY_MAX_VERSION = 96
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


def capture_regular_file_seal(path: Path) -> dict[str, Any]:
    """稳定读取常规文件并封印对象身份与完整字节。"""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink():
        raise ValueError(f"封印目标不是常规文件：{path.name}")
    content = path.read_bytes()
    after = path.lstat()
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    if before_identity != after_identity or len(content) != after.st_size:
        raise ValueError(f"封印读取期间文件发生变化：{path.name}")
    return {
        "device": int(after.st_dev),
        "inode": int(after.st_ino),
        "mode": int(after.st_mode),
        "size_bytes": int(after.st_size),
        "mtime_ns": int(after.st_mtime_ns),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content": content,
    }


def require_same_file_seal(
    expected: dict[str, Any], actual: dict[str, Any], *, phase: str
) -> None:
    if actual != expected:
        raise RuntimeError(f"{phase}: 已验证 COMPLETE 文件封印发生漂移")


def load_npy_from_sha_verified_bytes(
    path: Path, *, expected_sha256: str, label: str
) -> np.ndarray:
    """只读取一份封印字节，并从同一份字节解析 NPY。"""
    seal = capture_regular_file_seal(path)
    if seal["sha256"] != expected_sha256:
        raise ValueError(f"{label} 封印字节 SHA-256 与冻结合同不一致")
    with io.BytesIO(seal["content"]) as stream:
        values = np.load(stream, allow_pickle=False)
    if not isinstance(values, np.ndarray):
        raise ValueError(f"{label} NPY 未解析为 ndarray")
    return values


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
            # v48 属用户明确禁止复用/查看的旧 seed lineage，不进入本快照。
            if version == 48:
                continue
            files.extend(path for path in directory.rglob("*.py") if path.is_file())
    return sorted(files, key=lambda path: str(path.relative_to(PROJECT_DIR)))


def build_history_formula_manifest_payload(
    max_version: int = HISTORY_MAX_VERSION,
) -> dict[str, Any]:
    files = discover_history_python_files(max_version)
    records: list[dict[str, Any]] = []
    markers = (
        "init_score",
        "eval_init_score",
        "raw_score",
        "base_margin",
        "Annual_Income_USD",
        "Environmental_Concern_Level",
        "Subsidy_Available",
        "Range_Anxiety_Level",
        "norm.cdf",
    )
    equivalent_matches: list[str] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(PROJECT_DIR))
        present = [marker for marker in markers if marker in source]
        equivalent = bool(
            "init_score" in present
            and "eval_init_score" in present
            and "raw_score" in present
            and "norm.cdf" in present
            and all(field in present for field in markers[4:8])
        )
        if equivalent:
            equivalent_matches.append(relative)
        records.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "markers": present,
                "equivalent_fixed_generator_init_score": equivalent,
            }
        )
    directories = sorted({record["path"].split("/")[1] for record in records})
    return {
        "schema_version": 1,
        "snapshot_rule": (
            "all recursive Python files in numeric model/vN_* directories with 1<=N<=96, excluding the explicitly prohibited v48 seed lineage"
        ),
        "excluded_versions": [48],
        "maximum_version_inclusive": max_version,
        "mechanism_markers": list(markers),
        "directories": directories,
        "file_count": len(records),
        "files": records,
        "equivalent_matches": equivalent_matches,
        "no_equivalent_fixed_generator_init_score": not equivalent_matches,
        "related_xgb_base_margin_is_distinct": True,
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
        raise ValueError("历史公式 manifest 与当前允许审计的 v1-v96 Python 快照不一致")
    required_versions = {
        f"v{version}"
        for version in (80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 92, 93, 94, 95, 96)
    }
    covered_versions = {
        directory.split("_", 1)[0] for directory in stored["directories"]
    }
    if not required_versions.issubset(covered_versions):
        raise ValueError("历史公式 manifest 未完整覆盖 v80-v96")
    if (
        stored.get("no_equivalent_fixed_generator_init_score") is not True
        or stored.get("equivalent_matches") != []
    ):
        raise ValueError("历史 v1-v96 已存在等价 fixed-generator init_score 机制")
    return {
        "path": expected_relative,
        "sha256": config["history_formula_manifest_sha256"],
        "maximum_version_inclusive": HISTORY_MAX_VERSION,
        "directory_count": len(stored["directories"]),
        "file_count": stored["file_count"],
        "required_v80_v96_covered": True,
        "equivalent_matches": [],
        "mechanism_scan_recomputed_equal": True,
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
    if config.get("research_cycle") != "C01" or config.get("cycle_position") != 14:
        raise ValueError("冻结研究周期必须为 C01 第14个普通版本")
    if (
        float(config.get("time_budget_minutes", -1)) != 60.0
        or float(config.get("wall_clock_budget_seconds", -1)) != 3600.0
        or float(config.get("memory_budget_gb", -1)) != 16.0
        or int(config.get("peak_rss_budget_bytes", -1)) != 16 * 1024**3
        or int(config.get("cpu_threads", -1)) != 8
        or int(config.get("submission_budget", -1)) != 0
    ):
        raise ValueError("冻结资源预算必须为3600s/16GiB/8线程/提交0")
    if (
        config.get("base") != "v96_strict_v80_outer42_matched_control_40f"
        or float(config.get("base_oof_auc", -1)) != 0.9462430073165773
        or int(config.get("base_outer_split_seed", -1)) != 42
    ):
        raise ValueError("v97 matched baseline 必须是已完成 v96 seed42")
    if (
        config.get("strict_project_baseline")
        != "v80_strict_v61_outer104395303_40f"
        or float(config.get("strict_project_baseline_oof_auc", -1))
        != 0.946240610976364
        or float(config.get("current_best_strict_reference_oof_auc", -1))
        != 0.9463720745765888
        or float(config.get("current_best_completed_reference_oof_auc", -1))
        != 0.9463838901455106
        or float(config.get("absolute_target_auc", -1)) != 0.947
    ):
        raise ValueError("冻结 v80/v90/v95/0.947 比较基准漂移")
    if (
        config.get("non_formal_prediction_access")
        != "HASH_ONLY_BYTES_NOT_PARSED"
        or config.get("formal_source_prediction_identity_required") is not True
        or config.get("complete_commit_protocol")
        != "STAGED_VERIFY_THEN_ATOMIC_COMPLETE"
        or config.get("complete_preverify_resource_phase")
        != "BEFORE_STAGED_VERIFY"
        or config.get("complete_postverify_resource_phase")
        != "AFTER_STAGED_VERIFY_PRE_COMPLETE"
        or config.get("complete_commit_guard_phase")
        != "POST_COMPLETE_FILE_VERIFY_GUARD"
        or config.get("complete_post_seal_commit_guard_phase")
        != "POST_SEAL_COMMIT_GUARD"
        or config.get("formal_exception_close_protocol")
        != "ATOMIC_FAILED_EXCEPTION_INSIDE_FLOCK_WITH_INVALID_ARTIFACTS"
        or config.get("failed_artifacts_invalid_for_use") is not True
    ):
        raise ValueError("formal source-first/TOCTOU/staged/FAILED 合同漂移")
    source_schema = {
        "experiment_id",
        "runner_sha256",
        "config_sha256",
        "cv_results_sha256",
        "sources_sha256",
        "oof_sha256",
        "test_sha256",
        "verifier",
    }
    v96_source = config.get("v96_source")
    if not isinstance(v96_source, dict) or set(v96_source) != source_schema:
        raise ValueError("v96 冻结来源 schema 漂移")
    if (
        v96_source["experiment_id"]
        != "v96_strict_v80_outer42_matched_control_40f"
        or v96_source["verifier"] != "verify_complete"
    ):
        raise ValueError("v96 verifier 入口或身份漂移")
    for key in source_schema.difference({"experiment_id", "verifier"}):
        if not isinstance(v96_source[key], str) or len(v96_source[key]) != 64:
            raise ValueError(f"v96 {key} 非冻结 SHA-256")
    expected_variable = (
        "inject the frozen public generator margin through LightGBM fit init_score "
        "and validation eval_init_score, then reconstruct validation/test "
        "probabilities as expit(margin + raw residual)"
    )
    if config.get("unique_primary_variable") != expected_variable:
        raise ValueError("唯一科学变量必须只有 init/eval-init 与 raw residual 重建")
    margin = config.get("fixed_margin", {})
    if (
        margin.get("formula_sha256")
        != "5ac4a67799d7afc00688b77123e853e0d298bf3e2ec4a15579dc368b70e7d82d"
        or margin.get("clip_lower") != 1e-6
        or margin.get("clip_upper") != 1 - 1e-6
    ):
        raise ValueError("固定生成公式哈希或 clip 边界漂移")
    formula_sha = hashlib.sha256(
        str(margin.get("formula_literal", "")).encode("utf-8")
    ).hexdigest()
    if formula_sha != margin.get("formula_sha256"):
        raise ValueError("固定生成公式或其 SHA 漂移")
    required_margin_contract = {
        "fit_contract": "train margin subset is passed as init_score",
        "valid_contract": "validation margin subset is passed as eval_init_score[0]",
        "predict_contract": "predict_proba(raw_score=True) returns residual raw score; final probability is expit(frozen margin + residual raw score)",
        "test_contract": "test residual raw score is combined with the frozen test margin before expit",
    }
    for key, expected in required_margin_contract.items():
        if margin.get(key) != expected:
            raise ValueError(f"固定 margin {key} 合同漂移")
    if (
        config.get("feature_block_name")
        != "NONE_PURE_V96_STATIC_AND_STRICT_NESTED_TE"
        or config.get("feature_block_columns") != []
        or config.get("feature_block_formulas") != {}
        or config.get("feature_block_column_order_sha256") != hashlib.sha256(b"").hexdigest()
        or config.get("candidate_selection_used_labels") is not False
    ):
        raise ValueError("v97 不得改变 v96 feature block")
    if (
        config.get("feature_block_uses_labels") is not False
        or config.get("feature_block_is_row_wise_only") is not True
        or config.get("feature_block_changes_te_keys") is not False
    ):
        raise ValueError("feature block 边界必须是逐行、无标签且不改变 TE")
    expected_widths = {
        "expected_base_static_features": 62,
        "expected_added_static_features": 0,
        "expected_static_features": 62,
        "expected_te_features": 51,
        "expected_total_features": 113,
    }
    for key, expected in expected_widths.items():
        if int(config.get(key, -1)) != expected:
            raise ValueError(f"冻结特征宽度 {key} 必须为 {expected}")
    if (int(config.get("checkpoint_every_folds", -1)) != 1
        or int(config.get("observable_summary_every_folds", -1)) != 5
        or config.get("training_authorized_in_creation_task") is not False):
        raise ValueError("checkpoint/汇报/提交/本次训练授权合同漂移")
    if config.get("formal_requires_complete_40_folds") is not True:
        raise ValueError("v97 正式机制门槛必须完成全部40折")
    if (
        float(config.get("formal_minimum_oof_delta_vs_v96", -1)) != 0.0001
        or int(config.get("formal_minimum_positive_folds_vs_v96", -1)) != 24
        or config.get("below_v90_after_mechanism_pass_policy")
        != "ELIGIBLE_FOR_SEPARATE_SMALL_FUSION_PREREGISTRATION_ONLY"
    ):
        raise ValueError("v97 主门槛或低于v90权限合同漂移")
    evidence = config.get("preflight_evidence", {})
    evidence_paths = {
        "temporary_probe_sha256": PREFLIGHT_PROBE_PATH,
        "public_source_sha256": PUBLIC_SOURCE_EVIDENCE_PATH,
    }
    for key, path in evidence_paths.items():
        if not path.is_file() or sha256_file(path) != evidence.get(key):
            raise ValueError(f"preflight evidence {key} 漂移")
    if (
        evidence.get("temporary_probe_role")
        != "DESIGN_EVIDENCE_ONLY_NOT_FORMAL_CV_NOT_REUSABLE_PREDICTIONS"
        or evidence.get("public_predictions_used") is not False
        or evidence.get("leaderboard_used") is not False
    ):
        raise ValueError("临时 probe/public evidence 边界漂移")
    comparison_sources = config.get("comparison_sources")
    if not isinstance(comparison_sources, dict) or set(comparison_sources) != set(
        COMPARISON_DIRS
    ):
        raise ValueError("冻结比较来源必须精确为 v80/v90/v95")
    for experiment_id, source in comparison_sources.items():
        if source.get("role") not in {"strict_project_baseline_whole_oof", "current_best_strict_whole_oof", "current_best_completed_whole_oof"}:
            raise ValueError(f"{experiment_id} 比较角色漂移")
        for key in (
            "runner_sha256",
            "config_sha256",
            "cv_results_sha256",
            "sources_sha256",
            "oof_sha256",
            "test_sha256",
        ):
            if not isinstance(source.get(key), str) or len(source[key]) != 64:
                raise ValueError(f"{experiment_id} {key} 非冻结 SHA-256")
        expected_verifier = "verify_complete_payload" if experiment_id in {
            "v90_v89_member_verify_budget_retry",
            "v95_v94_source_verifier_adapter_retry",
        } else "verify_complete"
        if source.get("verifier") != expected_verifier:
            raise ValueError(f"{experiment_id} verifier 入口漂移")
    return config


def build_pure_v80_zero_column_adapter(frame: pd.DataFrame) -> pd.DataFrame:
    """兼容继承 runner 的零列哨兵；不得改变 v80 static features。"""
    return pd.DataFrame(index=np.arange(len(frame)))


def assert_pure_v80_static_identity(
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
    train_block = build_pure_v80_zero_column_adapter(train)
    test_block = build_pure_v80_zero_column_adapter(test)
    expected_columns = config["feature_block_columns"]
    if list(train_block.columns) != expected_columns or list(test_block.columns) != expected_columns:
        raise ValueError("pure control 的零列 feature block 漂移")
    block_sha = hashlib.sha256(b"").hexdigest()
    if block_sha != config["feature_block_column_order_sha256"]:
        raise ValueError("pure control 零列哨兵哈希漂移")
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
        raise ValueError("pure control static schema 与 v80 不完全一致")
    profile = {
        "name": config["feature_block_name"],
        "columns": expected_columns,
        "column_order_sha256": block_sha,
        "train_rows": len(train_block),
        "test_rows": len(test_block),
        "all_finite": True,
        "uses_labels": False,
        "row_wise_only": True,
        "identical_to_v80_static_values": bool(
            np.array_equal(expanded_train.to_numpy(), x_train.to_numpy())
            and np.array_equal(expanded_test.to_numpy(), x_test.to_numpy())
            and list(expanded_train.columns) == list(x_train.columns)
            and list(expanded_test.columns) == list(x_test.columns)
        ),
    }
    if profile["identical_to_v80_static_values"] is not True:
        raise ValueError("pure strict-v80 static 特征未逐元素保持")
    return expanded_train, expanded_test, profile


def build_fixed_generator_margin(frame: pd.DataFrame) -> np.ndarray:
    """逐行重建冻结公开生成公式；不读取标签或任何预测产物。"""
    required = {
        "Annual_Income_USD",
        "Environmental_Concern_Level",
        "Subsidy_Available",
        "Range_Anxiety_Level",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"固定 generator margin 缺列：{missing}")
    income = pd.to_numeric(frame["Annual_Income_USD"], errors="raise").to_numpy(
        np.float64
    )
    concern = pd.to_numeric(
        frame["Environmental_Concern_Level"], errors="raise"
    ).to_numpy(np.float64)
    score = (
        1.2 * income / 100_000.0
        + 0.6 * concern
        + 2.0 * frame["Subsidy_Available"].eq("Yes").to_numpy(np.float64)
        - 1.0 * frame["Range_Anxiety_Level"].eq("Medium").to_numpy(np.float64)
        - 3.0 * frame["Range_Anxiety_Level"].eq("High").to_numpy(np.float64)
    )
    p0 = np.clip(norm.cdf(score - 5.5), 1e-6, 1.0 - 1e-6)
    margin = np.log(p0 / (1.0 - p0)).astype(np.float64, copy=False)
    if margin.shape != (len(frame),) or not np.isfinite(margin).all():
        raise ValueError("固定 generator margin shape/有限值异常")
    return margin


def fit_lgbm_residual_with_fixed_margin(
    model: Any,
    x_fit: np.ndarray,
    y_fit: np.ndarray,
    x_valid: np.ndarray,
    y_valid: np.ndarray,
    train_margin: np.ndarray,
    valid_margin: np.ndarray,
    *,
    feature_name: list[str],
    early_stopping_rounds: int,
) -> Any:
    """唯一正式 fit 入口，强制同时传 train/valid 初始分数。"""
    if train_margin.shape != (len(y_fit),) or valid_margin.shape != (len(y_valid),):
        raise ValueError("fit/eval init_score 长度异常")
    if not np.isfinite(train_margin).all() or not np.isfinite(valid_margin).all():
        raise ValueError("fit/eval init_score 含 NaN/Inf")
    return model.fit(
        x_fit,
        y_fit,
        init_score=train_margin,
        eval_set=[(x_valid, y_valid)],
        eval_init_score=[valid_margin],
        eval_metric="auc",
        feature_name=feature_name,
        callbacks=[
            lgb.early_stopping(int(early_stopping_rounds), verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )


def predict_probability_from_margin_and_raw_residual(
    model: Any,
    features: np.ndarray,
    margin: np.ndarray,
    *,
    best_iteration: int,
) -> tuple[np.ndarray, np.ndarray]:
    """唯一正式 predict 入口；禁止把 raw residual 当概率或遗漏 margin。"""
    raw = np.asarray(
        model.predict_proba(
            features, num_iteration=best_iteration, raw_score=True
        ),
        dtype=np.float64,
    )
    if raw.shape != (len(features),) or margin.shape != (len(features),):
        raise ValueError("raw residual/margin shape 异常")
    if not np.isfinite(raw).all() or not np.isfinite(margin).all():
        raise ValueError("raw residual/margin 含 NaN/Inf")
    probability = expit(margin + raw)
    validate_probability_array("margin_plus_raw_probability", probability, len(features))
    return probability, raw


def derive_candidate_decision(
    config: dict[str, Any], oof_auc: float, delta_vs_v96: float, wins_vs_v96: int
) -> dict[str, Any]:
    mechanism_gate = bool(
        delta_vs_v96 >= float(config["formal_minimum_oof_delta_vs_v96"])
        and wins_vs_v96 >= int(config["formal_minimum_positive_folds_vs_v96"])
    )
    at_least_v90 = bool(
        oof_auc >= float(config["current_best_strict_reference_oof_auc"])
    )
    if mechanism_gate and at_least_v90:
        decision = "PROMOTE_SINGLE_MODEL"
    elif mechanism_gate:
        decision = config["below_v90_after_mechanism_pass_policy"]
    else:
        decision = "STOP"
    return {
        "mechanism_gate": mechanism_gate,
        "at_least_v90": at_least_v90,
        "decision": decision,
        "allowed_for_fusion": bool(mechanism_gate and at_least_v90),
        "eligible_for_separate_small_fusion_preregistration": bool(
            mechanism_gate and not at_least_v90
        ),
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


def canonical_resource_sequence() -> list[tuple[str, int | None]]:
    return [
        *[
            item
            for fold in range(1, N_FOLDS + 1)
            for item in (("BEFORE_FOLD", fold), ("AFTER_FOLD", fold))
        ],
        ("AFTER_ALL_FOLDS", N_FOLDS),
        ("BEFORE_STAGED_VERIFY", N_FOLDS),
        ("AFTER_STAGED_VERIFY_PRE_COMPLETE", N_FOLDS),
        ("POST_COMPLETE_FILE_VERIFY_GUARD", N_FOLDS),
        ("POST_SEAL_COMMIT_GUARD", N_FOLDS),
    ]


def validate_commit_guard_sequence(
    config: dict[str, Any], resource_checks: list[dict[str, Any]]
) -> None:
    """验证不回写 COMPLETE payload 的最终两段 guard 序列。"""
    expected = [
        (config["complete_commit_guard_phase"], N_FOLDS),
        (config["complete_post_seal_commit_guard_phase"], N_FOLDS),
    ]
    if len(resource_checks) < 2:
        raise ValueError("最终 commit guard 资源序列缺失")
    tail = resource_checks[-2:]
    if [(check.get("phase"), check.get("fold")) for check in tail] != expected:
        raise ValueError("最终 commit guard phase/fold 序列不一致")
    for check, (phase, fold) in zip(tail, expected):
        validate_recorded_resource_check(
            config,
            check,
            expected_phase=phase,
            expected_fold=fold,
            must_pass=False,
        )
    if (
        float(tail[1]["wall_elapsed_seconds"])
        < float(tail[0]["wall_elapsed_seconds"])
        or int(tail[1]["peak_rss_bytes"]) < int(tail[0]["peak_rss_bytes"])
    ):
        raise ValueError("最终 commit guard 资源序列回退")


def validate_failed_resource_sequence(
    config: dict[str, Any], payload: dict[str, Any]
) -> None:
    checks = payload.get("resource_checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("FAILED 资源序列为空")
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("FAILED 资源序列元素非法")
        phase = check.get("phase")
        fold = check.get("fold")
        if phase in {"FAILED", "FAILED_EXCEPTION"}:
            if isinstance(fold, bool) or not isinstance(fold, int) or not 0 <= fold <= N_FOLDS:
                raise ValueError("FAILED 终态 phase/fold 非法")
        elif (phase, fold) not in canonical_resource_sequence():
            raise ValueError("FAILED 资源 phase/fold 不在冻结域")
        validate_recorded_resource_check(
            config,
            check,
            expected_phase=str(phase),
            expected_fold=fold,
            must_pass=False,
        )
    for previous, current in zip(checks, checks[1:]):
        if float(current["wall_elapsed_seconds"]) < float(
            previous["wall_elapsed_seconds"]
        ):
            raise ValueError("FAILED 资源 elapsed 序列回退")
        if int(current["peak_rss_bytes"]) < int(previous["peak_rss_bytes"]):
            raise ValueError("FAILED 资源 peak RSS 序列回退")
        if float(current["peak_rss_gib"]) < float(previous["peak_rss_gib"]):
            raise ValueError("FAILED 资源 peak RSS GiB 序列回退")
    if checks[-1] != payload.get("final_resource_check"):
        raise ValueError("FAILED final_resource_check 不是资源序列末项")
    attribution = payload.get("failure_attribution")
    canonical = canonical_resource_sequence()
    observed = [(check["phase"], check["fold"]) for check in checks]
    completed = int(payload.get("completed_folds", -1))
    terminal_phase = "FAILED_EXCEPTION" if attribution == "FAILED_EXCEPTION" else "FAILED"
    if observed[-1][0] != terminal_phase:
        raise ValueError("FAILED 终态资源 phase 与归因不一致")
    prefix = observed[:-1]
    if prefix != canonical[: len(prefix)]:
        raise ValueError("FAILED 资源 phase/fold 不是合法前缀")
    completed_from_prefix = sum(
        phase == "AFTER_FOLD" for phase, _ in prefix
    )
    if completed_from_prefix != completed:
        raise ValueError("FAILED completed_folds 与资源前缀不一致")
    if terminal_phase == "FAILED_EXCEPTION":
        if observed[-1][1] != completed or any(
            check["breaches"] for check in checks[:-1]
        ):
            raise ValueError("FAILED_EXCEPTION 资源前缀或 fold 非法")
        return
    if not prefix or not checks[-2]["breaches"] or not checks[-1]["breaches"]:
        raise ValueError("资源 FAILED 缺少触发与终态 breach")
    if any(check["breaches"] for check in checks[:-2]):
        raise ValueError("资源 FAILED 在更早 phase 已超限却未停止")
    if payload.get("failure_phase") != prefix[-1][0] or payload.get(
        "failure_fold"
    ) != prefix[-1][1]:
        raise ValueError("资源 FAILED 触发 phase/fold 与前缀不一致")
    if attribution.split("+") != checks[-1]["breaches"]:
        raise ValueError("资源 FAILED attribution 与最终 breach 不一致")


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
        raise ValueError("冻结 LightGBM 版本与 v96 cv_results 不一致")
    if runtime_version != baseline_version:
        raise RuntimeError(
            "当前 LightGBM 版本与 v96 cv_results 不一致："
            f"runtime={runtime_version}, v96={baseline_version}"
        )


def validate_v96_contract(config: dict[str, Any], recipe: Any) -> dict[str, Any]:
    """确认 v97 除 margin 机制外逐项保持已完成 v96。"""
    validate_v96_source_hashes(config)
    baseline = json.loads((V96_DIR / "cv_results.json").read_text(encoding="utf-8"))
    baseline_config = json.loads((V96_DIR / "frozen_config.json").read_text())
    if baseline.get("status") != "COMPLETE":
        raise RuntimeError("formal trigger 未满足：v96 必须 COMPLETE")
    if baseline.get("experiment_id") != config["base"]:
        raise ValueError("v96 experiment_id 与冻结 base 不一致")
    if baseline["params"] != config["lightgbm_params"]:
        raise ValueError("冻结 LightGBM 参数与 v96 不一致")
    if baseline["te_keys"] != config["te_keys"]:
        raise ValueError("冻结 TE keys 与 v96 不一致")
    if baseline["smooths"] != config["smooths"]:
        raise ValueError("冻结 smoothing 与 v96 不一致")
    scalar_match = {
        "n_folds": N_FOLDS,
        "outer_split_seed": OUTER_SEED,
        "n_inner_folds": N_INNER_FOLDS,
        "inner_te_seed_base": INNER_TE_SEED_BASE,
        "model_seed": MODEL_SEED,
    }
    for key, expected in scalar_match.items():
        if int(baseline[key]) != expected:
            raise ValueError(f"v96 {key} 历史合同漂移")
    if baseline["strict_prior_contract"] != config["strict_prior_contract"]:
        raise ValueError("strict prior 合同未保持 v96")
    inherited_config_keys = (
        "n_folds",
        "outer_split_seed",
        "n_inner_folds",
        "inner_te_seed_base",
        "inner_te_seed_formula",
        "model_seed",
        "required_lightgbm_version",
        "strict_prior_contract",
        "smooths",
        "te_keys",
        "lightgbm_params",
        "early_stopping_rounds",
        "expected_train_rows",
        "expected_test_rows",
        "expected_base_static_features",
        "expected_added_static_features",
        "expected_static_features",
        "expected_te_features",
        "expected_total_features",
        "checkpoint_every_folds",
        "observable_summary_every_folds",
        "time_budget_minutes",
        "wall_clock_budget_seconds",
        "cpu_threads",
        "memory_budget_gb",
        "memory_budget_unit",
        "peak_rss_budget_bytes",
        "peak_rss_measurement",
        "submission_budget",
    )
    for key in inherited_config_keys:
        if config.get(key) != baseline_config.get(key):
            raise ValueError(f"{key} 未逐项保持冻结 v96")
    if not np.isclose(
        baseline["oof_auc"], config["base_oof_auc"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("v96 OOF 与冻结 base_oof_auc 不一致")
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


def candidate_output_record(path: Path) -> dict[str, Any]:
    """候选输出的严格记录：path/size/SHA 三者必须同时绑定。"""
    return {
        "path": str(path.relative_to(PROJECT_DIR)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def validate_candidate_output_records(
    sources: dict[str, Any],
    results: dict[str, Any],
    output_paths: dict[str, Path],
) -> None:
    outputs = sources.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != set(output_paths):
        raise ValueError("sources 输出清单不完整")
    artifact_hashes = results.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("cv_results artifact_sha256 非法")
    for name, path in output_paths.items():
        actual = candidate_output_record(path)
        if outputs.get(name) != actual:
            raise ValueError(f"sources 中 {name} path/size_bytes/sha256 合同不一致")
        if artifact_hashes.get(name) != actual["sha256"]:
            raise ValueError(f"cv_results 中 {name} 哈希不一致")


def validate_v96_source_hashes(config: dict[str, Any]) -> dict[str, Any]:
    """在导入 verifier 或解析预测前核对 v96 六个冻结文件。"""
    frozen = config["v96_source"]
    paths = {
        "runner_sha256": V96_SCRIPT_PATH,
        "config_sha256": V96_DIR / "frozen_config.json",
        "cv_results_sha256": V96_DIR / "cv_results.json",
        "sources_sha256": V96_DIR / "sources.json",
        "oof_sha256": V96_DIR / "oof_proba.npy",
        "test_sha256": V96_DIR / "test_proba.npy",
    }
    for key, path in paths.items():
        if not path.is_file() or sha256_file(path) != frozen[key]:
            raise ValueError(f"v96 {key} 冻结来源漂移")
    return {
        "experiment_id": frozen["experiment_id"],
        "verifier": frozen["verifier"],
        "hashes_verified": sorted(paths),
        "prediction_arrays_parsed": False,
    }


def validate_v80_source_hashes(config: dict[str, Any]) -> dict[str, Any]:
    """保留给继承的防护测试；正式来源编排仍统一走 comparison validator。"""
    experiment_id = "v80_strict_v61_outer104395303_40f"
    frozen = config["comparison_sources"][experiment_id]
    paths = {
        "runner_sha256": V80_SCRIPT_PATH,
        "config_sha256": V80_DIR / "frozen_config.json",
        "cv_results_sha256": V80_DIR / "cv_results.json",
        "sources_sha256": V80_DIR / "sources.json",
        "oof_sha256": V80_DIR / "oof_proba.npy",
        "test_sha256": V80_DIR / "test_proba.npy",
    }
    for key, path in paths.items():
        if not path.is_file() or sha256_file(path) != frozen[key]:
            raise ValueError(f"strict v80 {key} 冻结来源漂移")
    return {
        "experiment_id": experiment_id,
        "verifier": frozen["verifier"],
        "hashes_verified": sorted(paths),
        "prediction_arrays_parsed": False,
    }


def build_run_contract() -> dict[str, Any]:
    source_paths = {
        "candidate_runner": Path(__file__).resolve(),
        "frozen_config": CONFIG_PATH,
        "v61_wrapper": V61_SCRIPT_PATH,
        "v29_recipe": RECIPE_PATH,
        "v6_recipe": V6_SCRIPT_PATH,
        "v96_runner": V96_SCRIPT_PATH,
        "v96_config": V96_DIR / "frozen_config.json",
        "train_csv": DATA_DIR / "train.csv",
        "test_csv": DATA_DIR / "test.csv",
        "sample_submission_csv": DATA_DIR / "sample_submission.csv",
        "v96_cv_results": V96_DIR / "cv_results.json",
        "v96_sources": V96_SOURCES_PATH,
        "v96_oof": V96_DIR / "oof_proba.npy",
        "v96_test": V96_DIR / "test_proba.npy",
        "preflight_probe_evidence": PREFLIGHT_PROBE_PATH,
        "public_source_evidence": PUBLIC_SOURCE_EVIDENCE_PATH,
        "preflight_report": PREFLIGHT_REPORT_PATH,
        "history_formula_manifest": HISTORY_FORMULA_MANIFEST_PATH,
    }
    for experiment_id, directory in COMPARISON_DIRS.items():
        runner = directory / f"{experiment_id}.py"
        source_paths.update(
            {
                f"{experiment_id}:runner": runner,
                f"{experiment_id}:config": directory / "frozen_config.json",
                f"{experiment_id}:cv_results": directory / "cv_results.json",
                f"{experiment_id}:sources": directory / "sources.json",
                f"{experiment_id}:oof": directory / "oof_proba.npy",
                f"{experiment_id}:test": directory / "test_proba.npy",
            }
        )
    missing = [str(path) for path in source_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"运行合同来源文件缺失：{missing}")
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "frozen_config_sha256": sha256_file(CONFIG_PATH),
        "sources": {name: file_record(path) for name, path in source_paths.items()},
        "prediction_artifact_access": expected_prediction_artifact_access(),
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


def expected_prediction_artifact_access() -> dict[str, Any]:
    return {
        "v96_oof": "HASH_ONLY_BYTES_NOT_PARSED",
        "v96_test": "HASH_ONLY_BYTES_NOT_PARSED",
        "comparison_oof_test": "HASH_ONLY_BYTES_NOT_PARSED",
        "non_formal_modes": ["audit", "smoke"],
    }


def validate_comparison_source_hashes(config: dict[str, Any]) -> dict[str, Any]:
    """只读文件字节并核冻结 SHA；audit/smoke 不解析预测数组。"""
    validated: dict[str, Any] = {}
    for experiment_id, directory in COMPARISON_DIRS.items():
        frozen = config["comparison_sources"][experiment_id]
        paths = {
            "runner_sha256": directory / f"{experiment_id}.py",
            "config_sha256": directory / "frozen_config.json",
            "cv_results_sha256": directory / "cv_results.json",
            "sources_sha256": directory / "sources.json",
            "oof_sha256": directory / "oof_proba.npy",
            "test_sha256": directory / "test_proba.npy",
        }
        for key, path in paths.items():
            if not path.is_file() or sha256_file(path) != frozen[key]:
                raise ValueError(f"{experiment_id} {key} 冻结来源漂移")
        validated[experiment_id] = {
            "role": frozen["role"],
            "verifier": frozen["verifier"],
            "hashes_verified": sorted(paths),
            "prediction_arrays_parsed": False,
        }
    return validated


def validate_probability_array(name: str, values: np.ndarray, expected: int) -> None:
    if values.shape != (expected,):
        raise ValueError(f"{name} shape={values.shape}，预期 {(expected,)}")
    if not np.issubdtype(values.dtype, np.number):
        raise ValueError(f"{name} dtype 非数值：{values.dtype}")
    if not np.isfinite(values).all():
        raise ValueError(f"{name} 含 NaN/Inf")
    if ((values < 0.0) | (values > 1.0)).any():
        raise ValueError(f"{name} 含 [0,1] 外概率")


def validate_prediction_identity(
    train: pd.DataFrame,
    test: pd.DataFrame,
    results: dict[str, Any],
    *,
    experiment_id: str,
    directory: Path,
    frozen: dict[str, Any],
) -> dict[str, Any]:
    """仅供 formal/verify：绑定来源预测、当前行身份与冻结哈希。"""
    sources_path = directory / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    if sha256_file(sources_path) != frozen["sources_sha256"]:
        raise ValueError(f"{experiment_id} sources.json 冻结哈希不一致")
    expected_ids = {
        "train_rows": len(train),
        "test_rows": len(test),
        "train_id_sha256": sha256_ids(train["id"]),
        "test_id_sha256": sha256_ids(test["id"]),
    }
    if sources.get("row_identity") != expected_ids:
        raise ValueError(f"{experiment_id} sources 行身份与当前 train/test 不一致")
    required_outputs = {
        "oof_proba": directory / "oof_proba.npy",
        "test_proba": directory / "test_proba.npy",
    }
    evidence: dict[str, Any] = {
        "sources_sha256": sha256_file(sources_path),
        "row_identity": expected_ids,
        "artifacts": {},
    }
    for name, path in required_outputs.items():
        actual = file_record(path)
        frozen_key = "oof_sha256" if name == "oof_proba" else "test_sha256"
        if frozen[frozen_key] != actual["sha256"]:
            raise ValueError(f"{experiment_id} {name} 冻结哈希不一致")
        artifact_hashes = results.get("artifact_sha256", {})
        result_hash = artifact_hashes.get(name, artifact_hashes.get(f"{name}.npy"))
        if result_hash != actual["sha256"]:
            raise ValueError(f"{experiment_id} {name} cv_results 哈希不一致")
        outputs = sources.get("outputs")
        if isinstance(outputs, dict):
            record = outputs.get(name, outputs.get(f"{name}.npy"))
            size = record.get("bytes", record.get("size_bytes", -1)) if isinstance(record, dict) else -1
            if (
                not isinstance(record, dict)
                or record.get("path") != actual["path"]
                or record.get("sha256") != actual["sha256"]
                or int(size) != actual["bytes"]
            ):
                raise ValueError(f"{experiment_id} {name} sources 输出合同不一致")
        evidence["artifacts"][name] = actual
    return evidence


def validate_v80_prediction_identity(
    train: pd.DataFrame,
    test: pd.DataFrame,
    baseline: dict[str, Any],
    *,
    baseline_dir: Path = V80_DIR,
) -> dict[str, Any]:
    """兼容继承的 synthetic 防护测试，内部统一使用通用身份校验。"""
    return validate_prediction_identity(
        train,
        test,
        baseline,
        experiment_id=str(baseline.get("experiment_id", "synthetic_v80")),
        directory=baseline_dir,
        frozen={
            "sources_sha256": baseline["sources_sha256"],
            "oof_sha256": baseline["artifact_sha256"]["oof_proba"],
            "test_sha256": baseline["artifact_sha256"]["test_proba"],
        },
    )


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
    baseline = json.loads((V96_DIR / "cv_results.json").read_text(encoding="utf-8"))
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
        raise ValueError("v96 冻结 JSON 基准合同不一致")
    if not load_predictions:
        return train, test, sample, None, None, baseline
    verified = verify_all_prediction_sources_before_load(
        config, recipe, train, test
    )
    loaded = load_all_prediction_arrays_after_verification(
        config, train, test, verified
    )
    return train, test, sample, loaded[0], loaded[1], loaded[2]


def load_verified_comparison_predictions(
    config: dict[str, Any], train: pd.DataFrame, test: pd.DataFrame
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, dict[str, Any]]]:
    """兼容入口：四来源统一验收后才解析任一比较预测。"""
    recipe = load_recipe()
    verified = verify_all_prediction_sources_before_load(
        config, recipe, train, test
    )
    loaded = load_all_prediction_arrays_after_verification(
        config, train, test, verified
    )
    return loaded[3], loaded[4], loaded[5]


def verify_all_prediction_sources_before_load(
    config: dict[str, Any],
    recipe: Any,
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> dict[str, Any]:
    """在本 runner 解析任一预测前完成四个来源的完整验收。"""
    validate_v96_source_hashes(config)
    validate_comparison_source_hashes(config)
    v96_spec = importlib.util.spec_from_file_location(
        "v97_frozen_v96_verifier", V96_SCRIPT_PATH
    )
    if v96_spec is None or v96_spec.loader is None:
        raise RuntimeError("无法加载冻结 v96 verifier")
    v96_module = importlib.util.module_from_spec(v96_spec)
    v96_spec.loader.exec_module(v96_module)
    v96_verifier = getattr(v96_module, config["v96_source"]["verifier"], None)
    if not callable(v96_verifier):
        raise RuntimeError("冻结 v96 缺少 verify_complete")
    returned = v96_verifier()
    validate_v96_source_hashes(config)
    validate_comparison_source_hashes(config)
    baseline = json.loads(
        (V96_DIR / "cv_results.json").read_text(encoding="utf-8")
    )
    validate_v96_contract(config, recipe)
    if (
        not isinstance(returned, dict)
        or returned.get("status")
        != "COMPLETE_REBUILT_FROM_40_CHECKPOINTS_AND_VERIFIED"
        or returned.get("experiment_id") != config["base"]
        or not np.isclose(
            returned.get("oof_auc", np.nan), baseline["oof_auc"], atol=1e-12, rtol=0.0
        )
    ):
        raise ValueError("v96 full verifier 返回摘要不精确")
    validate_prediction_identity(
        train,
        test,
        baseline,
        experiment_id=config["base"],
        directory=V96_DIR,
        frozen=config["v96_source"],
    )

    results_by_id: dict[str, dict[str, Any]] = {}
    for experiment_id, directory in COMPARISON_DIRS.items():
        frozen = config["comparison_sources"][experiment_id]
        runner_path = directory / f"{experiment_id}.py"
        spec = importlib.util.spec_from_file_location(
            f"v97_source_{experiment_id}", runner_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"无法加载 {experiment_id} 冻结 verifier")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verifier = getattr(module, frozen["verifier"], None)
        if not callable(verifier):
            raise RuntimeError(f"{experiment_id} 缺少 {frozen['verifier']}")
        returned = verifier()
        validate_v96_source_hashes(config)
        validate_comparison_source_hashes(config)
        results = json.loads(
            (directory / "cv_results.json").read_text(encoding="utf-8")
        )
        if (
            results.get("status") != "COMPLETE"
            or results.get("experiment_id") != experiment_id
        ):
            raise ValueError(f"{experiment_id} 不是冻结 COMPLETE")
        if experiment_id in {
            "v90_v89_member_verify_budget_retry",
            "v95_v94_source_verifier_adapter_retry",
        }:
            if returned != results:
                raise ValueError(f"{experiment_id} verifier 返回值与重读 cv 不一致")
        else:
            if returned is not None:
                raise ValueError("v80 verify_complete 历史入口必须返回 None")
        validate_prediction_identity(
            train,
            test,
            results,
            experiment_id=experiment_id,
            directory=directory,
            frozen=frozen,
        )
        results_by_id[experiment_id] = results

    validate_v96_source_hashes(config)
    validate_comparison_source_hashes(config)
    return {
        "all_four_sources_fully_verified_before_candidate_np_load": True,
        "baseline_results": baseline,
        "comparison_results": results_by_id,
    }


def load_all_prediction_arrays_after_verification(
    config: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    verified: dict[str, Any],
) -> tuple[
    np.ndarray,
    np.ndarray,
    dict[str, Any],
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    dict[str, dict[str, Any]],
]:
    """统一预检后，每个预测源仅从自身 SHA 验证过的封印字节解析。"""
    if verified.get("all_four_sources_fully_verified_before_candidate_np_load") is not True:
        raise ValueError("缺少四来源统一完整验收令牌")
    validate_v96_source_hashes(config)
    validate_comparison_source_hashes(config)
    baseline = json.loads(
        (V96_DIR / "cv_results.json").read_text(encoding="utf-8")
    )
    if baseline != verified.get("baseline_results"):
        raise ValueError("v96 metadata 在统一验收后漂移")
    validate_prediction_identity(
        train,
        test,
        baseline,
        experiment_id=config["base"],
        directory=V96_DIR,
        frozen=config["v96_source"],
    )
    for experiment_id, directory in COMPARISON_DIRS.items():
        current = json.loads(
            (directory / "cv_results.json").read_text(encoding="utf-8")
        )
        if current != verified.get("comparison_results", {}).get(experiment_id):
            raise ValueError(f"{experiment_id} metadata 在统一验收后漂移")

    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    baseline_oof = load_npy_from_sha_verified_bytes(
        V96_DIR / "oof_proba.npy",
        expected_sha256=config["v96_source"]["oof_sha256"],
        label="v96_oof",
    )
    baseline_test = load_npy_from_sha_verified_bytes(
        V96_DIR / "test_proba.npy",
        expected_sha256=config["v96_source"]["test_sha256"],
        label="v96_test",
    )
    validate_probability_array("v96_oof", baseline_oof, len(train))
    validate_probability_array("v96_test", baseline_test, len(test))
    baseline_auc = float(roc_auc_score(y, baseline_oof))
    if (
        not np.isclose(baseline_auc, baseline["oof_auc"], atol=1e-12, rtol=0.0)
        or not np.isclose(
            baseline_auc, config["base_oof_auc"], atol=1e-12, rtol=0.0
        )
    ):
        raise ValueError("v96 OOF 无法按冻结 metadata 复算")

    oof_predictions: dict[str, np.ndarray] = {}
    test_predictions: dict[str, np.ndarray] = {}
    results_by_id = verified["comparison_results"]
    for experiment_id, directory in COMPARISON_DIRS.items():
        results = results_by_id[experiment_id]
        frozen = config["comparison_sources"][experiment_id]
        oof = load_npy_from_sha_verified_bytes(
            directory / "oof_proba.npy",
            expected_sha256=frozen["oof_sha256"],
            label=f"{experiment_id}.oof",
        )
        test_prediction = load_npy_from_sha_verified_bytes(
            directory / "test_proba.npy",
            expected_sha256=frozen["test_sha256"],
            label=f"{experiment_id}.test",
        )
        validate_probability_array(f"{experiment_id}.oof", oof, len(train))
        validate_probability_array(
            f"{experiment_id}.test", test_prediction, len(test)
        )
        recomputed_auc = float(roc_auc_score(y, oof))
        if not np.isclose(
            recomputed_auc, results["oof_auc"], atol=1e-12, rtol=0.0
        ):
            raise ValueError(f"{experiment_id} OOF 与 cv_results 不一致")
        oof_predictions[experiment_id] = np.asarray(oof)
        test_predictions[experiment_id] = np.asarray(test_prediction)
    return (
        np.asarray(baseline_oof),
        np.asarray(baseline_test),
        baseline,
        oof_predictions,
        test_predictions,
        results_by_id,
    )


def prepare_formal_prediction_sources(
    config: dict[str, Any], recipe: Any
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    np.ndarray,
    np.ndarray,
    dict[str, Any],
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    dict[str, dict[str, Any]],
]:
    """train/verify 共用的唯一来源编排入口。"""
    train, test, sample, _, _, _ = validate_data_contract(
        config, recipe, load_predictions=False
    )
    verified = verify_all_prediction_sources_before_load(
        config, recipe, train, test
    )
    loaded = load_all_prediction_arrays_after_verification(
        config, train, test, verified
    )
    return train, test, sample, *loaded


def compute_frozen_comparisons(
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    candidate_oof: np.ndarray,
    candidate_test: np.ndarray,
    comparison_oof: dict[str, np.ndarray],
    comparison_test: dict[str, np.ndarray],
    comparison_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    candidate_auc = float(roc_auc_score(y, candidate_oof))
    for experiment_id in COMPARISON_DIRS:
        source = comparison_oof[experiment_id]
        source_auc = float(roc_auc_score(y, source))
        if not np.isclose(
            source_auc,
            comparison_results[experiment_id]["oof_auc"],
            atol=1e-12,
            rtol=0.0,
        ):
            raise ValueError(f"{experiment_id} 整体 OOF 无法重建")
        rows[experiment_id] = {
            "source_oof_auc": source_auc,
            "candidate_oof_delta": candidate_auc - source_auc,
            "oof_spearman": float(spearmanr(candidate_oof, source).statistic),
            "test_spearman": float(
                spearmanr(candidate_test, comparison_test[experiment_id]).statistic
            ),
            "comparison_boundary": "whole OOF on identical row order; fold wins are reserved exclusively for matched v96",
        }
    rows["absolute_0_947"] = {
        "target_oof_auc": 0.947,
        "candidate_oof_minus_target": candidate_auc - 0.947,
        "distance_to_target": 0.947 - candidate_auc,
        "comparison_boundary": "absolute local OOF reference only",
    }
    return rows


def validate_historical_overlap_audit(config: dict[str, Any]) -> dict[str, Any]:
    """对 v1-v96 源码快照做机制级去重，而不是按版本名判断。"""
    frozen = config.get("historical_mechanism_audit", {})
    if (
        frozen.get("maximum_version_inclusive") != HISTORY_MAX_VERSION
        or frozen.get("required_absence")
        != "no v1-v96 Python implementation combines this fixed generator formula with LightGBM init_score/eval_init_score and raw-score-plus-margin reconstruction"
        or frozen.get("base_margin_boundary")
        != "XGBoost base_margin is a related but model-family/API-distinct mechanism and is not historical equivalence"
    ):
        raise ValueError("历史机制去重边界漂移")
    manifest = validate_history_formula_manifest(config)
    return {
        "decision": "GO_NO_EQUIVALENT_FIXED_GENERATOR_LGBM_INIT_SCORE_IN_V1_V96",
        "maximum_version_inclusive": HISTORY_MAX_VERSION,
        "equivalent_existing_versions": [],
        "manifest": manifest,
        "candidate_selection_used_labels": False,
        "related_but_distinct": "XGBoost base_margin uses a different learner/API",
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
            raise RuntimeError(f"已有 v96 实例持有 flock：{owner}") from error
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
    valid_raw_residual: np.ndarray,
    test_raw_residual: np.ndarray,
    eval_auc: float,
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
            valid_raw_residual=valid_raw_residual.astype(np.float64, copy=False),
            test_raw_residual=test_raw_residual.astype(np.float64, copy=False),
            eval_auc=np.asarray(eval_auc, dtype=np.float64),
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
    valid_margin: np.ndarray,
    test_margin: np.ndarray,
) -> dict[str, Any]:
    required = {
        "fold",
        "valid_idx",
        "valid_idx_sha256",
        "valid_pred",
        "test_pred",
        "valid_raw_residual",
        "test_raw_residual",
        "eval_auc",
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
            "valid_raw_residual": saved["valid_raw_residual"].astype(
                np.float64, copy=True
            ),
            "test_raw_residual": saved["test_raw_residual"].astype(
                np.float64, copy=True
            ),
            "eval_auc": float(saved["eval_auc"].item()),
            "best_iteration": int(saved["best_iteration"].item()),
            "gain": saved["gain"].astype(np.float64, copy=True),
            "split": saved["split"].astype(np.float64, copy=True),
            "fold_auc": float(saved["fold_auc"].item()),
            "elapsed_seconds": float(saved["elapsed_seconds"].item()),
        }
    validate_probability_array("checkpoint.valid_pred", payload["valid_pred"], len(valid_idx))
    validate_probability_array("checkpoint.test_pred", payload["test_pred"], test_rows)
    if payload["valid_raw_residual"].shape != (len(valid_idx),):
        raise ValueError(f"{path.name} valid raw residual shape 不一致")
    if payload["test_raw_residual"].shape != (test_rows,):
        raise ValueError(f"{path.name} test raw residual shape 不一致")
    if not np.isfinite(payload["valid_raw_residual"]).all() or not np.isfinite(
        payload["test_raw_residual"]
    ).all():
        raise ValueError(f"{path.name} raw residual 含 NaN/Inf")
    if valid_margin.shape != (len(valid_idx),) or test_margin.shape != (test_rows,):
        raise ValueError(f"{path.name} 重建 margin shape 不一致")
    rebuilt_valid = expit(valid_margin + payload["valid_raw_residual"])
    rebuilt_test = expit(test_margin + payload["test_raw_residual"])
    if not np.array_equal(rebuilt_valid, payload["valid_pred"]):
        raise ValueError(f"{path.name} valid 不是 expit(margin + raw residual)")
    if not np.array_equal(rebuilt_test, payload["test_pred"]):
        raise ValueError(f"{path.name} test 不是 expit(margin + raw residual)")
    if payload["gain"].shape != (feature_count,) or payload["split"].shape != (
        feature_count,
    ):
        raise ValueError(f"{path.name} feature importance shape 不一致")
    if not np.isfinite(payload["gain"]).all() or not np.isfinite(payload["split"]).all():
        raise ValueError(f"{path.name} feature importance 含 NaN/Inf")
    if (
        payload["best_iteration"] <= 0
        or not np.isfinite(payload["fold_auc"])
        or not np.isfinite(payload["eval_auc"])
        or not np.isclose(
            payload["fold_auc"], payload["eval_auc"], atol=1e-12, rtol=0.0
        )
    ):
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
        "outputs": {
            name: candidate_output_record(path) for name, path in output_paths.items()
        },
    }


def audit() -> None:
    audit_started = time.monotonic()
    config = load_frozen_config()
    recipe = load_recipe()
    baseline = validate_v96_contract(config, recipe)
    strict_prior_self_check()
    overlap_audit = validate_historical_overlap_audit(config)
    v96_hash_audit = validate_v96_source_hashes(config)
    comparison_hash_audit = validate_comparison_source_hashes(config)
    run_contract = build_run_contract()
    train, test, _, baseline_oof, baseline_test, _ = validate_data_contract(
        config, recipe, load_predictions=False
    )
    if baseline_oof is not None or baseline_test is not None:
        raise AssertionError("audit 禁止解析 v96/比较来源预测数组")
    x_train, x_test, _, _ = recipe.base.build_static_features(train, test)
    x_train, x_test, block_profile = assert_pure_v80_static_identity(
        x_train, x_test, train, test, config
    )
    audit_resource_check = make_resource_check(
        config, started_monotonic=audit_started, phase="AUDIT", fold=None
    )
    validate_recorded_resource_check(
        config, audit_resource_check, expected_phase="AUDIT", expected_fold=None,
        must_pass=True,
    )
    print(json.dumps({
        "status": "AUDIT_OK_NO_TRAINING_OR_PREDICTION_ARRAYS_READ",
        "experiment_id": EXPERIMENT_ID,
        "formal_outputs_created": False,
        "base": config["base"],
        "base_oof_auc": float(baseline["oof_auc"]),
        "outer_split_seed": OUTER_SEED,
        "inner_te_seed_base": INNER_TE_SEED_BASE,
        "model_seed": MODEL_SEED,
        "strict_prior_self_check": True,
        "history_mechanism_dedup": overlap_audit,
        "v96_source_hash_audit": v96_hash_audit,
        "comparison_source_hash_audit": comparison_hash_audit,
        "preflight_probe_sha256": sha256_file(PREFLIGHT_PROBE_PATH),
        "public_source_evidence_sha256": sha256_file(PUBLIC_SOURCE_EVIDENCE_PATH),
        "prediction_artifact_access": run_contract["prediction_artifact_access"],
        "static_features": x_train.shape[1],
        "test_static_features": x_test.shape[1],
        "te_features": config["expected_te_features"],
        "total_features": config["expected_total_features"],
        "matched_control_profile": block_profile,
        "mechanism_gate": {
            "minimum_delta_vs_v96": config["formal_minimum_oof_delta_vs_v96"],
            "minimum_positive_folds_vs_v96": config["formal_minimum_positive_folds_vs_v96"],
        },
        "resource_budget": {
            "wall_clock_seconds": config["wall_clock_budget_seconds"],
            "peak_rss_bytes": config["peak_rss_budget_bytes"],
            "threads": config["cpu_threads"],
            "submissions": config["submission_budget"],
        },
        "frozen_config_sha256": run_contract["frozen_config_sha256"],
        "run_contract_sha256": run_contract["run_contract_sha256"],
    }, ensure_ascii=False, indent=2))


def smoke() -> None:
    config = load_frozen_config()
    recipe = load_recipe()
    baseline = validate_v96_contract(config, recipe)
    strict_prior_self_check()
    validate_historical_overlap_audit(config)
    validate_v96_source_hashes(config)
    validate_comparison_source_hashes(config)
    try:
        validate_lightgbm_version_contract(config, baseline, "0.0.0-smoke-mismatch")
    except RuntimeError as error:
        if "v96" not in str(error):
            raise
    else:
        raise AssertionError("不匹配的 LightGBM 版本未被拒绝")
    run_contract = build_run_contract()

    synthetic = pd.DataFrame({
        "Annual_Income_USD": [0.0, 50_000.0, 100_000.0, 200_000.0],
        "Environmental_Concern_Level": [1.0, 2.0, 4.0, 5.0],
        "Subsidy_Available": ["No", "Yes", "No", "Yes"],
        "Range_Anxiety_Level": ["Low", "Medium", "High", "Low"],
    })
    margin = build_fixed_generator_margin(synthetic)
    expected_score = np.asarray([0.6, 2.8, 0.6, 7.4])
    expected_p0 = np.clip(norm.cdf(expected_score - 5.5), 1e-6, 1 - 1e-6)
    expected_margin = np.log(expected_p0 / (1 - expected_p0))
    if not np.allclose(margin, expected_margin, atol=1e-15, rtol=0.0):
        raise AssertionError("冻结 generator margin 公式 smoke 失败")

    class FakeResidualModel:
        def __init__(self) -> None:
            self.fit_kwargs: dict[str, Any] = {}

        def fit(self, *args: Any, **kwargs: Any) -> "FakeResidualModel":
            self.fit_kwargs = kwargs
            return self

        def predict_proba(self, features: np.ndarray, **kwargs: Any) -> np.ndarray:
            if kwargs != {"num_iteration": 7, "raw_score": True}:
                raise AssertionError("predict 必须固定 raw_score=True")
            return np.linspace(-0.3, 0.3, len(features))

    fake = FakeResidualModel()
    x_fit = np.zeros((2, 3), dtype=np.float32)
    x_valid = np.zeros((2, 3), dtype=np.float32)
    y_fit = np.asarray([0, 1], dtype=np.int8)
    y_valid = np.asarray([1, 0], dtype=np.int8)
    fit_lgbm_residual_with_fixed_margin(
        fake, x_fit, y_fit, x_valid, y_valid, margin[:2], margin[2:],
        feature_name=["a", "b", "c"], early_stopping_rounds=500,
    )
    if (
        not np.array_equal(fake.fit_kwargs.get("init_score"), margin[:2])
        or len(fake.fit_kwargs.get("eval_init_score", [])) != 1
        or not np.array_equal(fake.fit_kwargs["eval_init_score"][0], margin[2:])
    ):
        raise AssertionError("fit/valid init_score 注入 smoke 失败")
    probability, raw = predict_probability_from_margin_and_raw_residual(
        fake, x_valid, margin[2:], best_iteration=7
    )
    if not np.allclose(probability, expit(margin[2:] + raw), atol=0.0, rtol=0.0):
        raise AssertionError("margin + raw residual -> expit smoke 失败")

    promote = derive_candidate_decision(config, 0.9465, 0.0001, 24)
    small_fusion_only = derive_candidate_decision(config, 0.9463, 0.0001, 24)
    stop = derive_candidate_decision(config, 0.9471, 0.000099, 40)
    if (
        promote["decision"] != "PROMOTE_SINGLE_MODEL"
        or not promote["allowed_for_fusion"]
        or small_fusion_only["decision"]
        != "ELIGIBLE_FOR_SEPARATE_SMALL_FUSION_PREREGISTRATION_ONLY"
        or small_fusion_only["allowed_for_fusion"]
        or not small_fusion_only["eligible_for_separate_small_fusion_preregistration"]
        or stop["decision"] != "STOP"
    ):
        raise AssertionError("v97 门槛/权限 smoke 失败")
    if classify_resource_breach(config, 3600.0, 0) != ["WALL_CLOCK_BUDGET"]:
        raise AssertionError("3600s 资源门槛 smoke 失败")
    if classify_resource_breach(config, 0.0, 16 * 1024**3 + 1) != ["PEAK_RSS_BUDGET"]:
        raise AssertionError("16GiB 资源门槛 smoke 失败")
    with tempfile.TemporaryDirectory(prefix="v97_smoke_", dir=OUT_DIR) as tmp:
        lock = Path(tmp) / "run.lock"
        with exclusive_run_lock(lock, run_contract["run_contract_sha256"]):
            try:
                with exclusive_run_lock(lock, run_contract["run_contract_sha256"]):
                    raise AssertionError("第二实例不应取得 flock")
            except RuntimeError:
                pass
    print(json.dumps({
        "status": "SMOKE_OK_SYNTHETIC_ONLY_NO_PREDICTION_ARRAYS_READ",
        "experiment_id": EXPERIMENT_ID,
        "formal_outputs_created": False,
        "fixed_margin_formula_verified": True,
        "fit_init_score_verified": True,
        "valid_eval_init_score_verified": True,
        "predict_raw_score_plus_margin_verified": True,
        "source_first_hashes_verified": True,
        "history_dedup_verified": True,
        "decision_permissions_verified": True,
        "resource_limits_verified": True,
        "flock_rejection_verified": True,
        "run_contract_sha256": run_contract["run_contract_sha256"],
    }, ensure_ascii=False, indent=2))


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
    wins = int(sum(row["delta_vs_v96_same_fold"] > 0 for row in fold_rows))
    payload = {
        "timestamp_utc": utc_now(),
        "evidence_level": "INTERIM_DIAGNOSTIC_NOT_FINAL",
        "completed_folds": completed,
        "total_folds": N_FOLDS,
        "trained_this_run": trained_this_run,
        "resumed_this_run": resumed_this_run,
        "covered_rows": int(covered.sum()),
        "partial_v97_oof_auc": partial_auc,
        "v96_auc_same_rows": baseline_auc,
        "partial_delta_vs_v96": partial_auc - baseline_auc,
        "winning_folds_vs_v96": wins,
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
        f"folds={completed}/{N_FOLDS} v97_partial_oof={partial_auc:.9f} "
        f"v96_same_rows={baseline_auc:.9f} "
        f"delta={partial_auc-baseline_auc:+.9f} wins={wins}/{completed} "
        f"trained={trained_this_run} resumed={resumed_this_run} "
        f"eta={payload['rough_eta_seconds']:.0f}s"
    )


def failure_artifact_inventory(
    *, artifact_root: Path, checkpoint_dir: Path
) -> dict[str, Any]:
    present: list[str] = []
    present_records: dict[str, dict[str, Any]] = {}
    for name in FINAL_ARTIFACT_NAMES:
        path = (
            checkpoint_dir / Path(name).name
            if name.startswith("checkpoints/")
            else artifact_root / name
        )
        if path.is_file():
            present.append(name)
            present_records[name] = {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
    return {
        "expected_artifacts": FINAL_ARTIFACT_NAMES,
        "present_artifacts": present,
        "present_artifact_records": present_records,
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
        "completed_folds",
        "fold_auc",
        "best_iterations",
        "fold_diagnostics",
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
        "present_artifact_records",
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
    completed = int(payload["completed_folds"])
    if any(
        len(payload.get(key, [])) != completed
        for key in ("fold_auc", "best_iterations", "fold_diagnostics")
    ):
        raise ValueError("FAILED 折诊断与 completed_folds 不一致")
    validate_failed_resource_sequence(config, payload)
    final_check = payload["final_resource_check"]
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
    if attribution == "FAILED_EXCEPTION":
        interrupted = payload.get("interrupted_state")
        if (
            final_check.get("phase") != "FAILED_EXCEPTION"
            or final_check.get("fold") != completed
            or not isinstance(payload.get("error_type"), str)
            or not payload["error_type"]
            or not isinstance(payload.get("error"), str)
            or payload.get("failure_phase") != "FAILED_EXCEPTION"
            or not isinstance(interrupted, dict)
            or interrupted.get("protocol")
            != "COMMON_COMMITTED_FOLD_AND_RESOURCE_PREFIX"
            or interrupted.get("committed_common_prefix_folds") != completed
            or interrupted.get("retained_resource_checks") != len(
                payload["resource_checks"]
            )
            - 1
            or int(interrupted.get("dropped_resource_checks", -1)) < 0
            or any(
                int(interrupted.get(key, -1)) < completed
                for key in (
                    "original_fold_diagnostics",
                    "original_fold_auc",
                    "original_best_iterations",
                )
            )
            or int(interrupted.get("original_resource_checks", -1))
            != int(interrupted.get("retained_resource_checks", -1))
            + int(interrupted.get("dropped_resource_checks", -1))
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
    breaches = list(failure_check["breaches"])
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


def committed_exception_prefix(
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[float],
    list[int],
    list[dict[str, Any]],
    dict[str, Any],
]:
    """以折诊断与完整 BEFORE/AFTER 资源对的共同前缀关闭异常。"""
    canonical = canonical_resource_sequence()
    matched_nonbreaching = 0
    for check, expected in zip(resource_checks, canonical):
        if (check.get("phase"), check.get("fold")) != expected or check.get(
            "breaches"
        ):
            break
        matched_nonbreaching += 1
    complete_resource_folds = sum(
        phase == "AFTER_FOLD"
        for phase, _ in canonical[:matched_nonbreaching]
    )
    committed = min(
        len(fold_rows),
        len(fold_scores),
        len(best_iterations),
        complete_resource_folds,
    )
    retained_resource_count = 2 * committed
    if committed == N_FOLDS:
        retained_resource_count = matched_nonbreaching
    committed_rows = [dict(row) for row in fold_rows[:committed]]
    committed_scores = [
        float(row["strict_candidate_auc"]) for row in committed_rows
    ]
    committed_best_iterations = [
        int(row["best_iteration"]) for row in committed_rows
    ]
    closed_checks = [dict(check) for check in resource_checks[:retained_resource_count]]
    interrupted_state = {
        "protocol": "COMMON_COMMITTED_FOLD_AND_RESOURCE_PREFIX",
        "committed_common_prefix_folds": committed,
        "original_fold_diagnostics": len(fold_rows),
        "original_fold_auc": len(fold_scores),
        "original_best_iterations": len(best_iterations),
        "original_resource_checks": len(resource_checks),
        "retained_resource_checks": retained_resource_count,
        "dropped_resource_checks": len(resource_checks) - retained_resource_count,
        "dropped_resource_tail": [
            {
                "phase": check.get("phase"),
                "fold": check.get("fold"),
                "breaches": check.get("breaches"),
            }
            for check in resource_checks[retained_resource_count:]
        ],
    }
    return (
        committed_rows,
        committed_scores,
        committed_best_iterations,
        closed_checks,
        interrupted_state,
    )




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
    (
        committed_rows,
        committed_scores,
        committed_best_iterations,
        closed_checks,
        interrupted_state,
    ) = committed_exception_prefix(
        fold_rows, fold_scores, best_iterations, resource_checks
    )
    completed = len(committed_rows)
    failure_check = make_resource_check(
        config,
        started_monotonic=started_monotonic,
        phase="FAILED_EXCEPTION",
        fold=completed,
    )
    closed_checks.append(failure_check)
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
        "fold_auc": committed_scores,
        "best_iterations": committed_best_iterations,
        "fold_diagnostics": committed_rows,
        "interrupted_state": interrupted_state,
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
        "resource_checks": closed_checks,
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
    validate_v96_contract(config, recipe)
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
            comparison_oof,
            comparison_test,
            comparison_results,
        ) = prepare_formal_prediction_sources(config, recipe)
        y = train_frame[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
        x_train, x_test, keys_train, keys_test = recipe.base.build_static_features(
            train_frame, test_frame
        )
        x_train, x_test, matched_control_profile = assert_pure_v80_static_identity(
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
            raise ValueError("完整特征 schema 不是冻结的 62 static + 51 TE")
        logger.emit(
            f"data train={train_frame.shape} test={test_frame.shape} "
            f"static={x_train.shape[1]} te={len(te_names)} total={len(all_features)}"
        )
        train_margin_all = build_fixed_generator_margin(train_frame)
        test_margin = build_fixed_generator_margin(test_frame)

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
                    valid_margin=train_margin_all[valid_idx],
                    test_margin=test_margin,
                )
                valid_pred = saved["valid_pred"]
                fold_test = saved["test_pred"]
                valid_raw_residual = saved["valid_raw_residual"]
                test_raw_residual = saved["test_raw_residual"]
                eval_auc = saved["eval_auc"]
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
                fit_lgbm_residual_with_fixed_margin(
                    model,
                    x_fit,
                    y[fit_idx],
                    x_valid,
                    y[valid_idx],
                    train_margin_all[fit_idx],
                    train_margin_all[valid_idx],
                    feature_name=all_features,
                    early_stopping_rounds=int(config["early_stopping_rounds"]),
                )
                best_iteration = int(
                    model.best_iteration_ or config["lightgbm_params"]["n_estimators"]
                )
                valid_pred, valid_raw_residual = (
                    predict_probability_from_margin_and_raw_residual(
                        model,
                        x_valid,
                        train_margin_all[valid_idx],
                        best_iteration=best_iteration,
                    )
                )
                fold_test, test_raw_residual = (
                    predict_probability_from_margin_and_raw_residual(
                        model, x_tst, test_margin, best_iteration=best_iteration
                    )
                )
                fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
                eval_auc = float(model.best_score_["valid_0"]["auc"])
                if not np.isclose(fold_auc, eval_auc, atol=1e-12, rtol=0.0):
                    raise ValueError(f"fold={fold} eval_init_score AUC 与手工重建不一致")
                gain = model.booster_.feature_importance(importance_type="gain")
                split = model.booster_.feature_importance(importance_type="split")
                fold_elapsed = time.monotonic() - fold_started
                save_checkpoint(
                    checkpoint,
                    fold=fold,
                    valid_idx=valid_idx,
                    valid_pred=valid_pred,
                    test_pred=fold_test,
                    valid_raw_residual=valid_raw_residual,
                    test_raw_residual=test_raw_residual,
                    eval_auc=eval_auc,
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
                    "v96_auc_same_seed42_fold": baseline_fold_auc,
                    "delta_vs_v96_same_fold": fold_auc - baseline_fold_auc,
                    "eval_auc": eval_auc,
                    "manual_vs_eval_auc_abs_diff": abs(fold_auc - eval_auc),
                    "valid_margin_sha256": hashlib.sha256(
                        train_margin_all[valid_idx].tobytes()
                    ).hexdigest(),
                    "test_margin_sha256": hashlib.sha256(test_margin.tobytes()).hexdigest(),
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
        baseline_auc = float(baseline_results["oof_auc"])
        delta_vs_v96 = oof_auc - baseline_auc
        oof_spearman = float(spearmanr(oof, baseline_oof).statistic)
        test_spearman = float(spearmanr(test_prediction, baseline_test).statistic)
        if not np.isfinite(oof_spearman) or not np.isfinite(test_spearman):
            raise ValueError("与 v96 的 Spearman 非有限值")
        wins_vs_v96 = int(
            sum(row["delta_vs_v96_same_fold"] > 0 for row in fold_rows)
        )
        decision = derive_candidate_decision(
            config, oof_auc, delta_vs_v96, wins_vs_v96
        )
        frozen_comparisons = compute_frozen_comparisons(
            y,
            folds,
            oof,
            test_prediction,
            comparison_oof,
            comparison_test,
            comparison_results,
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
                "the frozen public generator margin gives LightGBM a useful prior "
                "while v96 features, folds, TE and parameters remain unchanged"
            ),
            "unique_primary_variable": config["unique_primary_variable"],
            "feature_block_name": config["feature_block_name"],
            "feature_block_columns": config["feature_block_columns"],
            "matched_control_profile": matched_control_profile,
            "historical_overlap_audit": historical_overlap_audit,
            "comparison_source_hashes_verified": True,
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
            "winning_folds_vs_v96": wins_vs_v96,
            "oof_auc": oof_auc,
            "base": config["base"],
            "base_oof_auc": baseline_auc,
            "oof_delta_vs_base": delta_vs_v96,
            "strict_project_baseline": config["strict_project_baseline"],
            "strict_project_baseline_oof_auc": frozen_comparisons[
                "v80_strict_v61_outer104395303_40f"
            ]["source_oof_auc"],
            "oof_delta_vs_strict_project_baseline": frozen_comparisons[
                "v80_strict_v61_outer104395303_40f"
            ]["candidate_oof_delta"],
            "oof_spearman_vs_base": oof_spearman,
            "test_spearman_vs_base": test_spearman,
            "comparison_boundary": (
                "v97 and v96 use identical seed42 validation rows for the 40 paired "
                "fold deltas; v80/v90/v95 are whole-OOF row-aligned references only"
            ),
            "frozen_comparisons": frozen_comparisons,
            "oof_delta_vs_v80": frozen_comparisons[
                "v80_strict_v61_outer104395303_40f"
            ]["candidate_oof_delta"],
            "oof_delta_vs_v90": frozen_comparisons[
                "v90_v89_member_verify_budget_retry"
            ]["candidate_oof_delta"],
            "oof_delta_vs_v95": frozen_comparisons[
                "v95_v94_source_verifier_adapter_retry"
            ]["candidate_oof_delta"],
            "distance_to_0_947": frozen_comparisons["absolute_0_947"][
                "distance_to_target"
            ],
            "fixed_margin_contract": config["fixed_margin"],
            "preflight_evidence": config["preflight_evidence"],
            "mechanism_gate": {
                "minimum_oof_delta_vs_v96": config[
                    "formal_minimum_oof_delta_vs_v96"
                ],
                "minimum_positive_folds_vs_v96": config[
                    "formal_minimum_positive_folds_vs_v96"
                ],
                "passes": decision["mechanism_gate"],
            },
            "decision": decision["decision"],
            "allowed_for_fusion": decision["allowed_for_fusion"],
            "eligible_for_separate_small_fusion_preregistration": decision[
                "eligible_for_separate_small_fusion_preregistration"
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
                "checkpoint_raw_residual_reconstruction_required": True,
                "fit_init_score_required": True,
                "valid_eval_init_score_required": True,
                "test_margin_plus_raw_required": True,
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
            f"staged_verified v97_oof={oof_auc:.9f} "
            f"delta_vs_v96={delta_vs_v96:+.9f} wins={wins_vs_v96}/40 "
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
        committed = finalize_verified_complete(
            config,
            pending_results_path=pending_results_path,
            results_path=results_path,
            started_monotonic=started_monotonic,
            config_sha256=config_hash,
            run_contract_sha256=contract_hash,
            fold_rows=fold_rows,
            fold_scores=fold_scores,
            best_iterations=best_iterations,
            resource_checks=resource_checks,
            logger=logger,
        )
        state["closed"] = True
        if not committed:
            return


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
    if sources.get("prediction_artifact_access") != expected_prediction_artifact_access():
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


def finalize_verified_complete(
    config: dict[str, Any],
    *,
    pending_results_path: Path,
    results_path: Path,
    started_monotonic: float,
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
    logger: RunLogger,
    checkpoint_dir: Path = CHECKPOINT_DIR,
) -> bool:
    """完整验证 pending，封印字节，封印后立即做最终资源 guard 再提交。"""
    if results_path.exists():
        raise FileExistsError("最终 cv_results 已存在，拒绝覆盖")
    before_verify = capture_regular_file_seal(pending_results_path)
    verify_complete(results_path=pending_results_path, allow_staged=False)
    verified_seal = capture_regular_file_seal(pending_results_path)
    require_same_file_seal(
        before_verify, verified_seal, phase="FULL_COMPLETE_VERIFIER"
    )

    guard = make_resource_check(
        config,
        started_monotonic=started_monotonic,
        phase=config["complete_commit_guard_phase"],
        fold=N_FOLDS,
    )
    validate_recorded_resource_check(
        config,
        guard,
        expected_phase=config["complete_commit_guard_phase"],
        expected_fold=N_FOLDS,
        must_pass=False,
    )
    record_resource_check(resource_checks, guard)
    if guard["breaches"]:
        pending_results_path.unlink(missing_ok=True)
        failure_check = make_resource_check(
            config,
            started_monotonic=started_monotonic,
            phase="FAILED",
            fold=N_FOLDS,
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
            guard,
            failure_check,
            results_path=results_path,
            checkpoint_dir=checkpoint_dir,
        )
        logger.emit(
            "stopped reason="
            f"{'+'.join(failure_check['breaches'])} "
            f"phase={guard['phase']} fold={guard['fold']} "
            f"wall={failure_check['wall_elapsed_seconds']:.1f}s "
            f"peak_rss={failure_check['peak_rss_gib']:.3f}GiB"
        )
        return False

    try:
        post_guard_seal = capture_regular_file_seal(pending_results_path)
        require_same_file_seal(
            verified_seal,
            post_guard_seal,
            phase="FINAL_PENDING_SEAL_DRIFT",
        )
    except Exception as error:
        return close_finalization_integrity_failure(
            config,
            error=error,
            pending_results_path=pending_results_path,
            results_path=results_path,
            started_monotonic=started_monotonic,
            config_sha256=config_sha256,
            run_contract_sha256=run_contract_sha256,
            fold_rows=fold_rows,
            fold_scores=fold_scores,
            best_iterations=best_iterations,
            resource_checks=resource_checks,
            checkpoint_dir=checkpoint_dir,
        )

    post_seal_guard = make_resource_check(
        config,
        started_monotonic=started_monotonic,
        phase=config["complete_post_seal_commit_guard_phase"],
        fold=N_FOLDS,
    )
    validate_recorded_resource_check(
        config,
        post_seal_guard,
        expected_phase=config["complete_post_seal_commit_guard_phase"],
        expected_fold=N_FOLDS,
        must_pass=False,
    )
    record_resource_check(resource_checks, post_seal_guard)
    validate_commit_guard_sequence(config, resource_checks)
    if post_seal_guard["breaches"]:
        pending_results_path.unlink(missing_ok=True)
        failure_check = make_resource_check(
            config,
            started_monotonic=started_monotonic,
            phase="FAILED",
            fold=N_FOLDS,
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
            post_seal_guard,
            failure_check,
            results_path=results_path,
            checkpoint_dir=checkpoint_dir,
        )
        logger.emit(
            "stopped reason="
            f"{'+'.join(failure_check['breaches'])} "
            f"phase={post_seal_guard['phase']} fold={post_seal_guard['fold']} "
            f"wall={failure_check['wall_elapsed_seconds']:.1f}s "
            f"peak_rss={failure_check['peak_rss_gib']:.3f}GiB"
        )
        return False

    try:
        commit_complete_pending(pending_results_path, results_path)
        committed_seal = capture_regular_file_seal(results_path)
        require_same_file_seal(
            verified_seal,
            committed_seal,
            phase="POST_COMMIT_SEAL_DRIFT",
        )
    except Exception as error:
        return close_finalization_integrity_failure(
            config,
            error=error,
            pending_results_path=pending_results_path,
            results_path=results_path,
            started_monotonic=started_monotonic,
            config_sha256=config_sha256,
            run_contract_sha256=run_contract_sha256,
            fold_rows=fold_rows,
            fold_scores=fold_scores,
            best_iterations=best_iterations,
            resource_checks=resource_checks,
            checkpoint_dir=checkpoint_dir,
        )
    return True


def commit_complete_pending(pending_results_path: Path, results_path: Path) -> None:
    """最终 COMPLETE 唯一允许的目标替换入口。"""
    os.replace(pending_results_path, results_path)


def close_finalization_integrity_failure(
    config: dict[str, Any],
    *,
    error: Exception,
    pending_results_path: Path,
    results_path: Path,
    started_monotonic: float,
    config_sha256: str,
    run_contract_sha256: str,
    fold_rows: list[dict[str, Any]],
    fold_scores: list[float],
    best_iterations: list[int],
    resource_checks: list[dict[str, Any]],
    checkpoint_dir: Path,
) -> bool:
    """移除未可信 COMPLETE，并用统一失败 schema 原子关闭。"""
    pending_results_path.unlink(missing_ok=True)
    results_path.unlink(missing_ok=True)
    write_exception_failure(
        config,
        error=error,
        started_monotonic=started_monotonic,
        config_sha256=config_sha256,
        run_contract_sha256=run_contract_sha256,
        fold_rows=fold_rows,
        fold_scores=fold_scores,
        best_iterations=best_iterations,
        resource_checks=resource_checks,
        results_path=results_path,
        checkpoint_dir=checkpoint_dir,
    )
    return False


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
    validate_v96_contract(config, recipe)
    strict_prior_self_check()
    historical_overlap_audit = validate_historical_overlap_audit(config)
    (
        train,
        test,
        sample,
        baseline_oof,
        baseline_test,
        baseline_results,
        comparison_oof,
        comparison_test,
        comparison_results,
    ) = prepare_formal_prediction_sources(config, recipe)
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
        or results.get("comparison_source_hashes_verified") is not True
        or results.get("fixed_margin_contract") != config["fixed_margin"]
        or results.get("preflight_evidence") != config["preflight_evidence"]
    ):
        raise ValueError("cv_results v96/v80 基准或历史审计合同不一致")

    x_train, x_test, _, _ = recipe.base.build_static_features(train, test)
    x_train, x_test, matched_control_profile = assert_pure_v80_static_identity(
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
        or results.get("matched_control_profile") != matched_control_profile
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
    train_margin = build_fixed_generator_margin(train)
    test_margin = build_fixed_generator_margin(test)

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
            valid_margin=train_margin[valid_idx],
            test_margin=test_margin,
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
                diagnostic["v96_auc_same_seed42_fold"],
                baseline_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
            or not np.isclose(
                diagnostic["delta_vs_v96_same_fold"],
                fold_auc - baseline_fold_auc,
                atol=1e-12,
                rtol=0.0,
            )
        ):
            raise ValueError(f"fold={fold} cv_results fold diagnostic 复算不一致")
        if (
            not np.isclose(
                diagnostic["eval_auc"], checkpoint["eval_auc"], atol=1e-12, rtol=0.0
            )
            or diagnostic["manual_vs_eval_auc_abs_diff"] > 1e-12
            or diagnostic["valid_margin_sha256"]
            != hashlib.sha256(train_margin[valid_idx].tobytes()).hexdigest()
            or diagnostic["test_margin_sha256"]
            != hashlib.sha256(test_margin.tobytes()).hexdigest()
        ):
            raise ValueError(f"fold={fold} init/eval/raw margin diagnostic 不一致")
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
    delta_vs_v96 = recomputed_oof_auc - float(baseline_results["oof_auc"])
    if not np.isclose(
        delta_vs_v96, results["oof_delta_vs_base"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("oof_delta_vs_base 复算不一致")
    rebuilt_oof_spearman = float(spearmanr(rebuilt_oof, baseline_oof).statistic)
    rebuilt_test_spearman = float(spearmanr(rebuilt_test, baseline_test).statistic)
    if not np.isclose(
        rebuilt_oof_spearman, results["oof_spearman_vs_base"], atol=1e-12, rtol=0.0
    ) or not np.isclose(
        rebuilt_test_spearman, results["test_spearman_vs_base"], atol=1e-12, rtol=0.0
    ):
        raise ValueError("与 v96 的 Spearman 复算不一致")

    expected_comparisons = compute_frozen_comparisons(
        y,
        folds,
        rebuilt_oof,
        rebuilt_test,
        comparison_oof,
        comparison_test,
        comparison_results,
    )
    if results.get("frozen_comparisons") != expected_comparisons:
        raise ValueError("v80/v90/v95/0.947 比较复算不一致")
    comparison_keys = {
        "oof_delta_vs_v80": "v80_strict_v61_outer104395303_40f",
        "oof_delta_vs_v90": "v90_v89_member_verify_budget_retry",
        "oof_delta_vs_v95": "v95_v94_source_verifier_adapter_retry",
    }
    for result_key, source_id in comparison_keys.items():
        if not np.isclose(
            results.get(result_key, np.nan),
            expected_comparisons[source_id]["candidate_oof_delta"],
            atol=1e-12,
            rtol=0.0,
        ):
            raise ValueError(f"{result_key} 复算不一致")
    if not np.isclose(
        results.get("distance_to_0_947", np.nan),
        expected_comparisons["absolute_0_947"]["distance_to_target"],
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("distance_to_0_947 复算不一致")
    if not np.isclose(
        results["oof_delta_vs_strict_project_baseline"],
        expected_comparisons["v80_strict_v61_outer104395303_40f"][
            "candidate_oof_delta"
        ], atol=1e-12, rtol=0.0
    ):
        raise ValueError("oof_delta_vs_strict_project_baseline 复算不一致")

    wins_vs_v96 = int(sum(
        row["delta_vs_v96_same_fold"] > 0 for row in results["fold_diagnostics"]
    ))
    if int(results["winning_folds_vs_v96"]) != wins_vs_v96:
        raise ValueError("winning_folds_vs_v96 复算不一致")
    expected = derive_candidate_decision(
        config, recomputed_oof_auc, delta_vs_v96, wins_vs_v96
    )
    expected_gate = {
        "minimum_oof_delta_vs_v96": config["formal_minimum_oof_delta_vs_v96"],
        "minimum_positive_folds_vs_v96": config[
            "formal_minimum_positive_folds_vs_v96"
        ],
        "passes": expected["mechanism_gate"],
    }
    if results.get("mechanism_gate") != expected_gate:
        raise ValueError("mechanism_gate 复算不一致")
    for key in (
        "decision",
        "allowed_for_fusion",
        "eligible_for_separate_small_fusion_preregistration",
    ):
        if results.get(key) != expected[key]:
            raise ValueError(f"{key} 未由重建结果正确推导")
    if not expected["mechanism_gate"] and results["allowed_for_fusion"] is not False:
        raise ValueError("机制门槛未过不得进入融合")
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

    validate_candidate_output_records(
        sources,
        results,
        {
            "oof_proba": paths["oof_proba"],
            "test_proba": paths["test_proba"],
            "submission": paths["submission"],
            "feature_importance": paths["feature_importance"],
        },
    )
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
