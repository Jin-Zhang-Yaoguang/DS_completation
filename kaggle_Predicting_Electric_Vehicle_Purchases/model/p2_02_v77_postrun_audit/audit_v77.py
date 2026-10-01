# -*- coding: utf-8 -*-
"""P2-02 v77 训练后独立验收。

本脚本只读取 v77、v61、v10 与原始数据，在当前审计目录写出结果。
训练尚未完成时正常返回 ARTIFACT_INCOMPLETE，不修改或重启 v77。
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import catboost
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


AUDIT_DIR = Path(__file__).resolve().parent
MODEL_DIR = AUDIT_DIR.parent
PROJECT_DIR = MODEL_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

CANDIDATE_NAME = "v77_catboost_dual_40f"
BASE_NAME = "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
RECIPE_NAME = "v10_catboost_bag_10f"

CANDIDATE_DIR = MODEL_DIR / CANDIDATE_NAME
BASE_DIR = MODEL_DIR / BASE_NAME
RECIPE_DIR = MODEL_DIR / RECIPE_NAME
CHECKPOINT_DIR = CANDIDATE_DIR / "checkpoints"

TRAIN_PATH = DATA_DIR / "train.csv"
TEST_PATH = DATA_DIR / "test.csv"
SAMPLE_PATH = DATA_DIR / "sample_submission.csv"
CANDIDATE_SCRIPT = CANDIDATE_DIR / f"{CANDIDATE_NAME}.py"
RECIPE_SCRIPT = RECIPE_DIR / f"{RECIPE_NAME}.py"
BASE_SCRIPT = BASE_DIR / f"{BASE_NAME}.py"

TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"
N_FOLDS = 40
OUTER_SEED = 42
BAG_SEEDS = [42, 2026]
EXPECTED_FEATURE_COUNT = 20
EXPECTED_CATEGORICAL_COUNT = 13
META_N_FOLDS = 5
META_SEED = 42
META_GRID = np.linspace(0.0, 1.0, 101, dtype=np.float64)
SINGLE_MIN_OOF = 0.9458
BLEND_MIN_DELTA = 0.0001
FLOAT_ATOL = 1e-15
CHECKPOINT_PATTERN = re.compile(r"^fold_(\d{2})\.npz$")

# 2026-09-03 21:56 +08:00：训练仍连续运行时冻结的输入证据。
# 这些哈希既防止完成前输入漂移，也补偿旧 checkpoint 未内嵌配置哈希的缺口。
EXPECTED_FROZEN_SHA256 = {
    "data/train.csv": "eae9eaa4e6378df405e755f853771d7e26d212bd93258349fc797b771021946a",
    "data/test.csv": "539263f6caabc40afd5e2f0bc0ab16b10a2d1177c565fc71b866f0181d836b34",
    "data/sample_submission.csv": "a9747a8b947e4e35505e3da4535a5a494978b012a7adb50973f13e598849dda5",
    f"model/{CANDIDATE_NAME}/{CANDIDATE_NAME}.py": "9aa3924a3f73f36ace5dfa280dd1ce0a8028d2782eee9f4fe7674291045b778c",
    f"model/{RECIPE_NAME}/{RECIPE_NAME}.py": "b9a9b30a51e39acc9cab543b3f911a2929d498e9fe44ad237f45e13d85f40b60",
    f"model/{RECIPE_NAME}/cv_results.json": "241e9c99b8944715bd25b0160a4f6ad7059eb94b267eeae5b52edb8857a964e7",
    f"model/{BASE_NAME}/{BASE_NAME}.py": "78746e874e8a4715b29244ffb948cfe545fa6ce06c48a4379acea8c50924ab1c",
    f"model/{BASE_NAME}/cv_results.json": "d0ea0a78fb1327c579e0e9e4e49e553fadd62198597fd256d33597337d95a2ee",
    f"model/{BASE_NAME}/oof_proba.npy": "0b027d782c53b0f6fbef6cef930a3beef14d94effe18ff4957ca714382e111aa",
    f"model/{BASE_NAME}/test_proba.npy": "c3606720fc429b4bfc4998ab8c72e48c76bae4162dbe729643b2d62c84bf914f",
    f"model/{BASE_NAME}/submission.csv": "2f54c9b50f2aa19497827031d46d0f5018eac929a1e105823b4da1b3551209aa",
}

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


class AuditLogger:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
        self.lines.append(line)
        print(line, flush=True)

    def save(self) -> None:
        atomic_write_text(AUDIT_DIR / "audit_log.txt", "\n".join(self.lines) + "\n")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def atomic_write_npy(path: Path, values: np.ndarray) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, values)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_indices(indices: np.ndarray) -> str:
    normalized = np.asarray(indices, dtype="<i8")
    return hashlib.sha256(normalized.tobytes(order="C")).hexdigest()


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()


def source_entry(role: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"role": role, "path": relative_path(path), "exists": False}
    stat = path.stat()
    return {
        "role": role,
        "path": relative_path(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def validate_probability_array(
    name: str, values: np.ndarray, expected_shape: tuple[int, ...]
) -> list[str]:
    problems: list[str] = []
    if values.shape != expected_shape:
        problems.append(f"{name}: shape={values.shape}, expected={expected_shape}")
        return problems
    if not np.issubdtype(values.dtype, np.number):
        problems.append(f"{name}: dtype={values.dtype} 不是数值")
        return problems
    if not np.isfinite(values).all():
        problems.append(f"{name}: 存在 NaN/Inf")
    if ((values < 0.0) | (values > 1.0)).any():
        problems.append(f"{name}: 概率超出 [0,1]")
    return problems


def max_abs_difference(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape:
        return float("inf")
    return float(np.max(np.abs(left.astype(np.float64) - right.astype(np.float64))))


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray]:
    train = pd.read_csv(TRAIN_PATH, usecols=[ID_COL, TARGET])
    test = pd.read_csv(TEST_PATH, usecols=[ID_COL])
    sample = pd.read_csv(SAMPLE_PATH)
    if train[ID_COL].duplicated().any() or test[ID_COL].duplicated().any():
        raise ValueError("train/test 出现重复 id")
    if set(train[TARGET].unique()) != {"No", "Yes"}:
        raise ValueError("训练目标取值不为 No/Yes")
    if list(sample.columns) != [ID_COL, TARGET]:
        raise ValueError(f"sample_submission 列异常：{sample.columns.tolist()}")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission 与 test id 顺序不一致")
    y = train[TARGET].eq(POS_LABEL).to_numpy(np.int8)
    return train, test, sample, y


def make_outer_splits(y: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    splitter = StratifiedKFold(
        n_splits=N_FOLDS, shuffle=True, random_state=OUTER_SEED
    )
    return list(splitter.split(np.zeros(len(y), dtype=np.uint8), y))


def build_meta_fold_manifest(y: np.ndarray) -> tuple[dict[str, Any], list[tuple[np.ndarray, np.ndarray]]]:
    splitter = StratifiedKFold(
        n_splits=META_N_FOLDS, shuffle=True, random_state=META_SEED
    )
    splits = list(splitter.split(np.zeros(len(y), dtype=np.uint8), y))
    rows = []
    for fold, (fit_idx, valid_idx) in enumerate(splits, 1):
        rows.append(
            {
                "fold": fold,
                "fit_size": int(len(fit_idx)),
                "valid_size": int(len(valid_idx)),
                "fit_index_sha256_int64_le": sha256_indices(fit_idx),
                "valid_index_sha256_int64_le": sha256_indices(valid_idx),
                "fit_positive_count": int(y[fit_idx].sum()),
                "valid_positive_count": int(y[valid_idx].sum()),
            }
        )
    manifest = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "splitter": {
            "class": "sklearn.model_selection.StratifiedKFold",
            "n_splits": META_N_FOLDS,
            "shuffle": True,
            "random_state": META_SEED,
        },
        "index_encoding": "numpy int64 little-endian C-order bytes",
        "rows": rows,
    }
    return manifest, splits


def freeze_checkpoint_paths() -> tuple[dict[int, Path], list[str]]:
    checkpoints: dict[int, Path] = {}
    unexpected: list[str] = []
    if not CHECKPOINT_DIR.exists():
        return checkpoints, unexpected
    for path in sorted(CHECKPOINT_DIR.glob("fold_*.npz")):
        match = CHECKPOINT_PATTERN.fullmatch(path.name)
        if match is None:
            unexpected.append(path.name)
            continue
        fold = int(match.group(1))
        if fold in checkpoints:
            unexpected.append(path.name)
        else:
            checkpoints[fold] = path
    return checkpoints, unexpected


def audit_checkpoints(
    checkpoint_paths: dict[int, Path],
    unexpected_names: list[str],
    y: np.ndarray,
    test_size: int,
    logger: AuditLogger,
) -> tuple[dict[str, Any], np.ndarray | None, np.ndarray | None, list[float]]:
    expected_splits = make_outer_splits(y)
    missing_folds = [fold for fold in range(1, N_FOLDS + 1) if fold not in checkpoint_paths]
    invalid_folds = sorted(fold for fold in checkpoint_paths if fold < 1 or fold > N_FOLDS)
    errors: list[str] = []
    if unexpected_names:
        errors.append(f"非标准 checkpoint 文件：{unexpected_names}")
    if invalid_folds:
        errors.append(f"checkpoint 折号超范围：{invalid_folds}")

    seen = np.zeros(len(y), dtype=np.uint8)
    reconstructed_oof = np.zeros(len(y), dtype=np.float64)
    reconstructed_test = np.zeros(test_size, dtype=np.float64)
    fold_scores: list[float] = []
    rows: list[dict[str, Any]] = []
    required_keys = {
        "valid_idx",
        "valid_pred",
        "test_pred",
        "best_iterations",
        "importance",
    }

    for fold in sorted(checkpoint_paths):
        path = checkpoint_paths[fold]
        row_problems: list[str] = []
        row: dict[str, Any] = {"fold": fold, "path": relative_path(path)}
        if not 1 <= fold <= N_FOLDS:
            rows.append({**row, "problems": ["折号超范围"]})
            continue
        try:
            with np.load(path, allow_pickle=False) as saved:
                keys = set(saved.files)
                missing_keys = sorted(required_keys - keys)
                extra_keys = sorted(keys - required_keys)
                if missing_keys:
                    row_problems.append(f"缺少 keys={missing_keys}")
                    rows.append({**row, "keys": sorted(keys), "problems": row_problems})
                    errors.extend(f"fold {fold}: {p}" for p in row_problems)
                    continue
                valid_idx = np.asarray(saved["valid_idx"])
                valid_pred = np.asarray(saved["valid_pred"])
                fold_test = np.asarray(saved["test_pred"])
                iterations = np.asarray(saved["best_iterations"])
                importance = np.asarray(saved["importance"])
        except Exception as exc:  # noqa: BLE001
            row_problems.append(f"读取失败：{type(exc).__name__}: {exc}")
            rows.append({**row, "problems": row_problems})
            errors.extend(f"fold {fold}: {p}" for p in row_problems)
            continue

        expected_idx = expected_splits[fold - 1][1]
        if not np.issubdtype(valid_idx.dtype, np.integer):
            row_problems.append(f"valid_idx dtype={valid_idx.dtype}")
        if valid_idx.shape != expected_idx.shape or not np.array_equal(valid_idx, expected_idx):
            row_problems.append("valid_idx 与预注册 seed42 划分不一致")
        row_problems.extend(
            validate_probability_array(
                "valid_pred", valid_pred, (len(expected_idx),)
            )
        )
        row_problems.extend(
            validate_probability_array("test_pred", fold_test, (test_size,))
        )
        if iterations.shape != (len(BAG_SEEDS),):
            row_problems.append(
                f"best_iterations shape={iterations.shape}, expected={(len(BAG_SEEDS),)}"
            )
        elif not np.issubdtype(iterations.dtype, np.integer) or (iterations <= 0).any():
            row_problems.append("best_iterations 必须是两个正整数")
        if importance.shape != (EXPECTED_FEATURE_COUNT,):
            row_problems.append(
                f"importance shape={importance.shape}, expected={(EXPECTED_FEATURE_COUNT,)}"
            )
        elif not np.isfinite(importance).all():
            row_problems.append("importance 存在 NaN/Inf")
        if valid_idx.shape == expected_idx.shape and np.issubdtype(valid_idx.dtype, np.integer):
            if ((valid_idx < 0) | (valid_idx >= len(y))).any():
                row_problems.append("valid_idx 越界")
            elif seen[valid_idx].any():
                row_problems.append("valid_idx 与此前 checkpoint 重叠")

        usable = not row_problems
        fold_auc: float | None = None
        if usable:
            seen[valid_idx] = 1
            reconstructed_oof[valid_idx] = valid_pred
            reconstructed_test += fold_test / N_FOLDS
            fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
            fold_scores.append(fold_auc)
        else:
            errors.extend(f"fold {fold}: {p}" for p in row_problems)

        rows.append(
            {
                **row,
                "keys": sorted(keys),
                "extra_keys": extra_keys,
                "valid_size": int(len(valid_idx)),
                "valid_index_sha256_int64_le": sha256_indices(valid_idx)
                if np.issubdtype(valid_idx.dtype, np.integer)
                else None,
                "fold_auc": fold_auc,
                "best_iterations": [int(v) for v in iterations]
                if iterations.ndim == 1
                else None,
                "problems": row_problems,
            }
        )

    complete = not missing_folds and not errors and int(seen.sum()) == len(y)
    logger.write(
        f"checkpoint={len(checkpoint_paths)}/{N_FOLDS}, "
        f"覆盖={int(seen.sum())}/{len(y)}, errors={len(errors)}"
    )
    summary = {
        "expected_count": N_FOLDS,
        "present_count": len(checkpoint_paths),
        "missing_folds": missing_folds,
        "unexpected_names": unexpected_names,
        "covered_rows": int(seen.sum()),
        "expected_rows": int(len(y)),
        "coverage_complete": bool(int(seen.sum()) == len(y)),
        "errors": errors,
        "rows": rows,
        "complete": complete,
        "config_hash_embedded_in_checkpoint": False,
    }
    return (
        summary,
        reconstructed_oof if complete else None,
        reconstructed_test if complete else None,
        fold_scores,
    )


def fit_only_mid_ecdf(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    """用 reference 拟合 mid-ECDF，再变换 values；不读取 values 的分布。"""
    reference = np.asarray(reference, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if reference.ndim != 1 or values.ndim != 1 or len(reference) == 0:
        raise ValueError("ECDF 输入必须是一维，且 reference 非空")
    if not np.isfinite(reference).all() or not np.isfinite(values).all():
        raise ValueError("ECDF 输入存在 NaN/Inf")
    ordered = np.sort(reference, kind="mergesort")
    left = np.searchsorted(ordered, values, side="left")
    right = np.searchsorted(ordered, values, side="right")
    return (left.astype(np.float64) + right.astype(np.float64)) / (2.0 * len(ordered))


def crossfit_fit_only_ecdf(
    y: np.ndarray,
    base: np.ndarray,
    candidate: np.ndarray,
    meta_splits: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, dict[str, Any]]:
    blend_oof = np.zeros(len(y), dtype=np.float64)
    base_meta_oof = np.zeros(len(y), dtype=np.float64)
    candidate_meta_oof = np.zeros(len(y), dtype=np.float64)
    rows: list[dict[str, Any]] = []

    for fold, (fit_idx, valid_idx) in enumerate(meta_splits, 1):
        base_fit = fit_only_mid_ecdf(base[fit_idx], base[fit_idx])
        candidate_fit = fit_only_mid_ecdf(candidate[fit_idx], candidate[fit_idx])
        base_valid = fit_only_mid_ecdf(base[fit_idx], base[valid_idx])
        candidate_valid = fit_only_mid_ecdf(candidate[fit_idx], candidate[valid_idx])

        fit_scores = np.asarray(
            [
                roc_auc_score(
                    y[fit_idx],
                    (1.0 - weight) * base_fit + weight * candidate_fit,
                )
                for weight in META_GRID
            ],
            dtype=np.float64,
        )
        best_score = float(fit_scores.max())
        tied = np.flatnonzero(
            np.isclose(fit_scores, best_score, rtol=0.0, atol=FLOAT_ATOL)
        )
        best_index = int(tied[0])
        weight = float(META_GRID[best_index])

        base_meta_oof[valid_idx] = base_valid
        candidate_meta_oof[valid_idx] = candidate_valid
        blend_oof[valid_idx] = (
            (1.0 - weight) * base_valid + weight * candidate_valid
        )
        base_auc = float(roc_auc_score(y[valid_idx], base_valid))
        candidate_auc = float(roc_auc_score(y[valid_idx], candidate_valid))
        blend_auc = float(roc_auc_score(y[valid_idx], blend_oof[valid_idx]))
        rows.append(
            {
                "fold": fold,
                "fit_size": int(len(fit_idx)),
                "valid_size": int(len(valid_idx)),
                "candidate_weight": weight,
                "fit_auc": best_score,
                "valid_base_auc": base_auc,
                "valid_candidate_auc": candidate_auc,
                "valid_blend_auc": blend_auc,
                "delta_vs_base": blend_auc - base_auc,
            }
        )

    base_meta_auc = float(roc_auc_score(y, base_meta_oof))
    candidate_meta_auc = float(roc_auc_score(y, candidate_meta_oof))
    blend_auc = float(roc_auc_score(y, blend_oof))
    delta = blend_auc - base_meta_auc
    folds_won = int(sum(row["delta_vs_base"] > 0.0 for row in rows))
    passes = bool(delta >= BLEND_MIN_DELTA and folds_won == META_N_FOLDS)

    # 仅为通过后拟合 test 权重准备，不能替代上面的交叉拟合验收。
    base_full = fit_only_mid_ecdf(base, base)
    candidate_full = fit_only_mid_ecdf(candidate, candidate)
    full_scores = np.asarray(
        [
            roc_auc_score(
                y, (1.0 - weight) * base_full + weight * candidate_full
            )
            for weight in META_GRID
        ],
        dtype=np.float64,
    )
    full_best_score = float(full_scores.max())
    full_tied = np.flatnonzero(
        np.isclose(full_scores, full_best_score, rtol=0.0, atol=FLOAT_ATOL)
    )
    full_weight = float(META_GRID[int(full_tied[0])])

    result = {
        "method": "5-fold seed42 cross-fit with fit-only mid-ECDF",
        "transform_formula": (
            "(searchsorted(sorted_fit,x,left)+searchsorted(sorted_fit,x,right))"
            "/(2*n_fit)"
        ),
        "weight_grid": {
            "minimum": 0.0,
            "maximum": 1.0,
            "step": 0.01,
            "tie_break": "smallest candidate weight within absolute AUC tolerance 1e-15",
        },
        "fold_rows": rows,
        "mean_candidate_weight": float(
            np.mean([row["candidate_weight"] for row in rows])
        ),
        "base_meta_oof_auc": base_meta_auc,
        "candidate_meta_oof_auc": candidate_meta_auc,
        "crossfit_oof_auc": blend_auc,
        "oof_delta_vs_base_meta": delta,
        "folds_won_vs_base": folds_won,
        "minimum_delta": BLEND_MIN_DELTA,
        "passes_gate": passes,
        "full_fit_weight_for_future_test_generation": full_weight,
        "full_fit_auc_in_sample_not_for_acceptance": full_best_score,
    }
    return blend_oof, result


def compare_reported_number(
    checks: dict[str, Any],
    name: str,
    actual: float,
    reported: Any,
    tolerance: float = 1e-12,
) -> None:
    try:
        reported_float = float(reported)
        difference = abs(actual - reported_float)
        checks[name] = {
            "actual": actual,
            "reported": reported_float,
            "absolute_difference": difference,
            "passes": bool(difference <= tolerance),
        }
    except (TypeError, ValueError):
        checks[name] = {
            "actual": actual,
            "reported": reported,
            "absolute_difference": None,
            "passes": False,
        }


def audit_complete_outputs(
    y: np.ndarray,
    test: pd.DataFrame,
    sample: pd.DataFrame,
    reconstructed_oof: np.ndarray,
    reconstructed_test: np.ndarray,
    checkpoint_fold_scores: list[float],
    checkpoint_summary: dict[str, Any],
    meta_splits: list[tuple[np.ndarray, np.ndarray]],
    logger: AuditLogger,
) -> tuple[dict[str, Any], np.ndarray, list[str]]:
    errors: list[str] = []
    checks: dict[str, Any] = {}

    candidate_oof = np.load(CANDIDATE_DIR / "oof_proba.npy", allow_pickle=False)
    candidate_test = np.load(CANDIDATE_DIR / "test_proba.npy", allow_pickle=False)
    base_oof = np.load(BASE_DIR / "oof_proba.npy", allow_pickle=False)
    base_test = np.load(BASE_DIR / "test_proba.npy", allow_pickle=False)
    candidate_results = json.loads(
        (CANDIDATE_DIR / "cv_results.json").read_text(encoding="utf-8")
    )
    base_results = json.loads(
        (BASE_DIR / "cv_results.json").read_text(encoding="utf-8")
    )
    submission = pd.read_csv(CANDIDATE_DIR / "submission.csv")

    errors.extend(validate_probability_array("candidate_oof", candidate_oof, (len(y),)))
    errors.extend(
        validate_probability_array("candidate_test", candidate_test, (len(test),))
    )
    errors.extend(validate_probability_array("base_oof", base_oof, (len(y),)))
    errors.extend(validate_probability_array("base_test", base_test, (len(test),)))

    oof_max_diff = max_abs_difference(candidate_oof, reconstructed_oof)
    test_max_diff = max_abs_difference(candidate_test, reconstructed_test)
    checks["oof_equals_checkpoint_reconstruction"] = {
        "max_abs_difference": oof_max_diff,
        "tolerance": FLOAT_ATOL,
        "passes": bool(oof_max_diff <= FLOAT_ATOL),
    }
    checks["test_equals_checkpoint_mean"] = {
        "max_abs_difference": test_max_diff,
        "tolerance": FLOAT_ATOL,
        "passes": bool(test_max_diff <= FLOAT_ATOL),
    }

    expected_columns = [ID_COL, TARGET]
    submission_ok = bool(
        list(submission.columns) == expected_columns
        and submission.shape == sample.shape
        and submission[ID_COL].equals(test[ID_COL])
    )
    submission_pred = (
        submission[TARGET].to_numpy()
        if TARGET in submission
        else np.asarray([], dtype=np.float64)
    )
    submission_max_diff = max_abs_difference(submission_pred, candidate_test)
    checks["submission"] = {
        "columns": list(submission.columns),
        "shape": list(submission.shape),
        "id_order_matches_test": bool(
            ID_COL in submission and submission[ID_COL].equals(test[ID_COL])
        ),
        "prediction_max_abs_difference_vs_test_npy": submission_max_diff,
        "passes": bool(submission_ok and submission_max_diff <= FLOAT_ATOL),
    }

    candidate_auc = float(roc_auc_score(y, candidate_oof))
    base_auc = float(roc_auc_score(y, base_oof))
    reconstructed_fold_scores = [
        float(roc_auc_score(y[valid_idx], candidate_oof[valid_idx]))
        for _, valid_idx in make_outer_splits(y)
    ]
    fold_score_max_diff = max_abs_difference(
        np.asarray(reconstructed_fold_scores),
        np.asarray(candidate_results.get("fold_auc", [])),
    )
    checkpoint_fold_score_max_diff = max_abs_difference(
        np.asarray(reconstructed_fold_scores), np.asarray(checkpoint_fold_scores)
    )
    checks["fold_auc"] = {
        "reported_count": len(candidate_results.get("fold_auc", [])),
        "recomputed_count": len(reconstructed_fold_scores),
        "max_abs_difference_vs_results": fold_score_max_diff,
        "max_abs_difference_vs_checkpoints": checkpoint_fold_score_max_diff,
        "passes": bool(
            fold_score_max_diff <= 1e-12 and checkpoint_fold_score_max_diff <= 1e-12
        ),
    }
    compare_reported_number(
        checks, "candidate_oof_auc", candidate_auc, candidate_results.get("oof_auc")
    )
    compare_reported_number(
        checks, "base_oof_auc", base_auc, base_results.get("oof_auc")
    )
    compare_reported_number(
        checks,
        "candidate_fold_auc_mean",
        float(np.mean(reconstructed_fold_scores)),
        candidate_results.get("fold_auc_mean"),
    )
    compare_reported_number(
        checks,
        "candidate_fold_auc_std_ddof0",
        float(np.std(reconstructed_fold_scores)),
        candidate_results.get("fold_auc_std"),
    )
    compare_reported_number(
        checks,
        "candidate_delta_vs_base",
        candidate_auc - base_auc,
        candidate_results.get("oof_delta_vs_base"),
    )
    for statistic, actual in (
        ("prediction_min", float(candidate_test.min())),
        ("prediction_max", float(candidate_test.max())),
        ("prediction_mean", float(candidate_test.mean())),
    ):
        compare_reported_number(
            checks,
            f"candidate_{statistic}",
            actual,
            candidate_results.get(statistic),
        )

    core_result_keys = {
        "model",
        "n_folds",
        "fold_auc",
        "oof_auc",
        "base",
        "base_oof_auc",
        "oof_delta_vs_base",
        "params",
        "elapsed_seconds",
    }
    missing_core_result_keys = sorted(core_result_keys - set(candidate_results))
    checkpoint_iterations = [row.get("best_iterations") for row in checkpoint_summary["rows"]]
    reported_iterations = candidate_results.get("best_iterations")
    checks["result_schema_and_iterations"] = {
        "missing_core_keys": missing_core_result_keys,
        "best_iterations_match_checkpoints": reported_iterations == checkpoint_iterations,
        "passes": bool(
            not missing_core_result_keys and reported_iterations == checkpoint_iterations
        ),
    }

    train_log_text = (CANDIDATE_DIR / "train_log.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    train_header_count = sum(
        line.startswith("train=") for line in train_log_text.splitlines()
    )
    resumed_count = train_log_text.count("resumed from")
    checks["continuous_run_log"] = {
        "train_header_count": train_header_count,
        "resumed_checkpoint_count": resumed_count,
        "passes": bool(train_header_count == 1 and resumed_count == 0),
        "note": "旧脚本用 tee 覆盖日志，现场连续运行证据仍需与冻结哈希合并解释",
    }

    config_checks = {
        "n_folds": candidate_results.get("n_folds") == N_FOLDS,
        "outer_split_seed": candidate_results.get("outer_split_seed") == OUTER_SEED,
        "bag_seeds": candidate_results.get("bag_seeds") == BAG_SEEDS,
        "params": candidate_results.get("params") == EXPECTED_CAT_PARAMS,
        "feature_count": candidate_results.get("feature_count")
        == EXPECTED_FEATURE_COUNT,
        "categorical_feature_count": candidate_results.get(
            "categorical_feature_count"
        )
        == EXPECTED_CATEGORICAL_COUNT,
        "base": candidate_results.get("base") == BASE_NAME,
    }
    checks["frozen_config"] = {
        **config_checks,
        "passes": bool(all(config_checks.values())),
    }

    diagnostic_rows = []
    for fold, (_, valid_idx) in enumerate(make_outer_splits(y), 1):
        base_fold_auc = float(roc_auc_score(y[valid_idx], base_oof[valid_idx]))
        candidate_fold_auc = float(
            roc_auc_score(y[valid_idx], candidate_oof[valid_idx])
        )
        diagnostic_rows.append(
            {
                "fold": fold,
                "base_auc": base_fold_auc,
                "candidate_auc": candidate_fold_auc,
                "delta_vs_base": candidate_fold_auc - base_fold_auc,
            }
        )
    diagnostic_wins = int(
        sum(row["delta_vs_base"] > 0.0 for row in diagnostic_rows)
    )

    blend_oof, blend = crossfit_fit_only_ecdf(y, base_oof, candidate_oof, meta_splits)
    single_gate = bool(candidate_auc >= SINGLE_MIN_OOF)
    accepted = bool(single_gate and blend["passes_gate"])
    correlations = {
        "oof_spearman_v77_v61": float(spearmanr(candidate_oof, base_oof).statistic),
        "test_spearman_v77_v61": float(
            spearmanr(candidate_test, base_test).statistic
        ),
    }

    required_check_passes = []
    for value in checks.values():
        if isinstance(value, dict) and "passes" in value:
            required_check_passes.append(bool(value["passes"]))
    if not all(required_check_passes):
        errors.append("至少一项最终产物复算不一致")

    logger.write(
        f"candidate OOF={candidate_auc:.9f}, base OOF={base_auc:.9f}, "
        f"fit-only blend delta={blend['oof_delta_vs_base_meta']:+.9f}, "
        f"wins={blend['folds_won_vs_base']}/5"
    )
    result = {
        "checks": checks,
        "candidate": {
            "name": CANDIDATE_NAME,
            "raw_oof_auc": candidate_auc,
            "minimum_oof_auc": SINGLE_MIN_OOF,
            "passes_specific_p2_02_single_gate": single_gate,
            "prediction_summary": {
                "oof_min": float(candidate_oof.min()),
                "oof_max": float(candidate_oof.max()),
                "oof_mean": float(candidate_oof.mean()),
                "test_min": float(candidate_test.min()),
                "test_max": float(candidate_test.max()),
                "test_mean": float(candidate_test.mean()),
            },
        },
        "base": {"name": BASE_NAME, "raw_oof_auc": base_auc},
        "seed42_common_row_bucket_diagnostic_only": {
            "reason": "v61 的训练外层种子为 104395303，不能称相同训练折配对",
            "folds_won": diagnostic_wins,
            "minimum_60_percent_count": 24,
            "rows": diagnostic_rows,
        },
        "blend_with_v61": blend,
        "correlations": correlations,
        "acceptance": {
            "single_gate": single_gate,
            "blend_gate": bool(blend["passes_gate"]),
            "artifact_reconstruction_gate": not errors,
            "accepted_for_candidate_pool": bool(accepted and not errors),
            "embedded_v77_blend_result_used": False,
        },
    }
    return result, blend_oof, errors


def build_source_manifest(
    checkpoint_paths: dict[int, Path], generated_at: str
) -> tuple[dict[str, Any], list[str]]:
    static_sources = [
        ("audit_script", Path(__file__).resolve()),
        ("audit_readme", AUDIT_DIR / "README.md"),
        ("train_csv", TRAIN_PATH),
        ("test_csv", TEST_PATH),
        ("sample_submission_csv", SAMPLE_PATH),
        ("candidate_script", CANDIDATE_SCRIPT),
        ("candidate_train_log", CANDIDATE_DIR / "train_log.txt"),
        ("candidate_cv_results", CANDIDATE_DIR / "cv_results.json"),
        ("candidate_oof", CANDIDATE_DIR / "oof_proba.npy"),
        ("candidate_test", CANDIDATE_DIR / "test_proba.npy"),
        ("candidate_submission", CANDIDATE_DIR / "submission.csv"),
        ("candidate_feature_importance", CANDIDATE_DIR / "feature_importance.csv"),
        ("candidate_recipe_script", RECIPE_SCRIPT),
        ("candidate_recipe_results", RECIPE_DIR / "cv_results.json"),
        ("base_script", BASE_SCRIPT),
        ("base_cv_results", BASE_DIR / "cv_results.json"),
        ("base_oof", BASE_DIR / "oof_proba.npy"),
        ("base_test", BASE_DIR / "test_proba.npy"),
        ("base_submission", BASE_DIR / "submission.csv"),
    ]
    entries = [source_entry(role, path) for role, path in static_sources]
    entries.extend(
        source_entry(f"candidate_checkpoint_{fold:02d}", path)
        for fold, path in sorted(checkpoint_paths.items())
    )

    by_path = {entry["path"]: entry for entry in entries}
    frozen_hash_mismatches: list[str] = []
    for path, expected in EXPECTED_FROZEN_SHA256.items():
        entry = by_path.get(path)
        if entry is None or not entry.get("exists"):
            frozen_hash_mismatches.append(f"冻结输入缺失：{path}")
        elif entry.get("sha256") != expected:
            frozen_hash_mismatches.append(
                f"冻结输入哈希漂移：{path}, actual={entry.get('sha256')}, expected={expected}"
            )

    manifest = {
        "schema_version": 1,
        "audit_id": "P2-02-v77-postrun-audit",
        "generated_at_utc": generated_at,
        "project_root": ".",
        "frozen_sha256": EXPECTED_FROZEN_SHA256,
        "frozen_hash_mismatches": frozen_hash_mismatches,
        "files": entries,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "catboost": catboost.__version__,
        },
    }
    return manifest, frozen_hash_mismatches


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    logger = AuditLogger()
    generated_at = utc_now()
    logger.write("开始 P2-02 v77 独立只读验收")

    train, test, sample, y = load_data()
    meta_manifest, meta_splits = build_meta_fold_manifest(y)
    atomic_write_json(AUDIT_DIR / "meta_folds.json", meta_manifest)
    logger.write(f"数据行数 train={len(train)}, test={len(test)}；meta folds 已冻结")

    checkpoint_paths, unexpected_names = freeze_checkpoint_paths()
    checkpoint_summary, reconstructed_oof, reconstructed_test, fold_scores = (
        audit_checkpoints(
            checkpoint_paths,
            unexpected_names,
            y,
            len(test),
            logger,
        )
    )
    source_manifest, frozen_hash_mismatches = build_source_manifest(
        checkpoint_paths, generated_at
    )
    atomic_write_json(AUDIT_DIR / "sources.json", source_manifest)
    source_manifest_sha256 = sha256_file(AUDIT_DIR / "sources.json")
    meta_manifest_sha256 = sha256_file(AUDIT_DIR / "meta_folds.json")

    final_required = [
        CANDIDATE_DIR / "cv_results.json",
        CANDIDATE_DIR / "oof_proba.npy",
        CANDIDATE_DIR / "test_proba.npy",
        CANDIDATE_DIR / "submission.csv",
        CANDIDATE_DIR / "feature_importance.csv",
        CANDIDATE_DIR / "train_log.txt",
    ]
    missing_final = [relative_path(path) for path in final_required if not path.exists()]
    incomplete_reasons: list[str] = []
    if checkpoint_summary["missing_folds"]:
        incomplete_reasons.append(
            f"缺少 checkpoint folds={checkpoint_summary['missing_folds']}"
        )
    if missing_final:
        incomplete_reasons.append(f"缺少最终产物={missing_final}")

    protocol_deviations = [
        {
            "code": "CHECKPOINT_CONFIG_HASH_ABSENT",
            "impact": "checkpoint 本身不能拒绝不同配置续跑；本审计以连续运行现场冻结哈希补偿",
        },
        {
            "code": "EMBEDDED_BLEND_GLOBAL_RANK",
            "impact": "v77 内置 blend 在元CV前使用全量 rank；该结果和 accepted_for_p2_06 永久忽略",
        },
        {
            "code": "CANDIDATE_SOURCES_JSON_ABSENT",
            "impact": "由独立审计目录 sources.json 补充来源和哈希，不回写历史目录",
        },
        {
            "code": "PER_SEED_PREDICTIONS_NOT_SAVED",
            "impact": "无法事后逐元素复核两个模型种子的均值，只能核验代码、日志、两个迭代数和折级预测",
        },
        {
            "code": "FINAL_OUTPUTS_NOT_ATOMIC_IN_CANDIDATE",
            "impact": "必须以 checkpoint 重建与逐元素比较确认最终 npy/csv/json 完整",
        },
    ]

    critical_errors = list(checkpoint_summary["errors"]) + frozen_hash_mismatches
    result: dict[str, Any] = {
        "schema_version": 1,
        "audit_id": "P2-02-v77-postrun-audit",
        "generated_at_utc": generated_at,
        "status": None,
        "decision": None,
        "protocol": {
            "candidate_outer_cv": {
                "class": "StratifiedKFold",
                "n_splits": N_FOLDS,
                "shuffle": True,
                "random_state": OUTER_SEED,
                "bag_seeds": BAG_SEEDS,
            },
            "meta_cv": {
                "class": "StratifiedKFold",
                "n_splits": META_N_FOLDS,
                "shuffle": True,
                "random_state": META_SEED,
                "transform": "fit-only mid-ECDF",
                "candidate_weight_grid": "0.00..1.00 step 0.01",
            },
            "specific_p2_02_gates": {
                "candidate_oof_at_least": SINGLE_MIN_OOF,
                "blend_delta_at_least": BLEND_MIN_DELTA,
                "meta_folds_won": "5/5",
            },
        },
        "checkpoint_audit": checkpoint_summary,
        "missing_final_artifacts": missing_final,
        "incomplete_reasons": incomplete_reasons,
        "frozen_hash_mismatches": frozen_hash_mismatches,
        "source_manifest_sha256": source_manifest_sha256,
        "meta_folds_manifest_sha256": meta_manifest_sha256,
        "protocol_deviations": protocol_deviations,
        "complete_output_audit": None,
    }

    if critical_errors:
        result["status"] = "AUDIT_FAILED"
        result["decision"] = "REJECTED_PROTOCOL_OR_ARTIFACT_ERROR"
        result["errors"] = critical_errors
        logger.write(f"AUDIT_FAILED: {critical_errors}")
    elif incomplete_reasons:
        result["status"] = "ARTIFACT_INCOMPLETE"
        result["decision"] = "WAIT_FOR_SAME_TRAINING_INSTANCE"
        result["errors"] = []
        logger.write(
            f"ARTIFACT_INCOMPLETE: checkpoint={len(checkpoint_paths)}/{N_FOLDS}"
        )
    else:
        if reconstructed_oof is None or reconstructed_test is None:
            raise RuntimeError("checkpoint 标记完整但未返回重建预测")
        complete_audit, blend_oof, complete_errors = audit_complete_outputs(
            y,
            test,
            sample,
            reconstructed_oof,
            reconstructed_test,
            fold_scores,
            checkpoint_summary,
            meta_splits,
            logger,
        )
        result["complete_output_audit"] = complete_audit
        result["errors"] = complete_errors
        accepted = complete_audit["acceptance"]["accepted_for_candidate_pool"]
        if complete_errors:
            result["status"] = "AUDIT_FAILED"
            result["decision"] = "REJECTED_ARTIFACT_MISMATCH"
            logger.write(f"AUDIT_FAILED: {complete_errors}")
        elif accepted:
            result["status"] = "PASS"
            result["decision"] = "ACCEPTED_FOR_CANDIDATE_POOL"
            atomic_write_npy(AUDIT_DIR / "blend_oof_fit_ecdf.npy", blend_oof)
            logger.write("PASS: v77 通过 P2-02 单模与 fit-only ECDF 融合门槛")
        else:
            result["status"] = "PASS"
            result["decision"] = "REJECTED_BY_PREREGISTERED_GATE"
            atomic_write_npy(AUDIT_DIR / "blend_oof_fit_ecdf.npy", blend_oof)
            logger.write("PASS: 产物可信，但 v77 未通过预注册晋级门槛")

    atomic_write_json(AUDIT_DIR / "audit_results.json", result)
    logger.save()
    print(result["status"], flush=True)
    return 0 if result["status"] in {"PASS", "ARTIFACT_INCOMPLETE"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        failure = {
            "schema_version": 1,
            "audit_id": "P2-02-v77-postrun-audit",
            "generated_at_utc": utc_now(),
            "status": "AUDIT_FAILED",
            "decision": "REJECTED_AUDIT_EXCEPTION",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        atomic_write_json(AUDIT_DIR / "audit_results.json", failure)
        atomic_write_text(
            AUDIT_DIR / "audit_log.txt",
            f"[{utc_now()}] AUDIT_FAILED {type(exc).__name__}: {exc}\n",
        )
        print("AUDIT_FAILED", file=sys.stderr, flush=True)
        raise SystemExit(1)
