#!/usr/bin/env python3
"""校验私有 CTBoost kernel 的 OOF，并做 fit-only 嵌套元融合。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
TRAIN_PATH = PROJECT_DIR / "data/train.csv"
V90_PATH = PROJECT_DIR / "model/v90_v89_member_verify_budget_retry/oof_proba.npy"
DEFAULT_OOF_PATH = OUT_DIR / "remote_output/oof.npz"
EVIDENCE_PATH = OUT_DIR / "evidence.json"
MIN_MODEL_AUC = 0.9452
MIN_BLEND_DELTA = 0.0001
WEIGHT_GRID = np.arange(0.0, 0.5000001, 0.025)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def fit_mid_ecdf(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all() or not len(values):
        raise ValueError("ECDF fit 输入非法")
    return np.sort(values)


def transform_mid_ecdf(state: np.ndarray, values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("ECDF transform 输入非法")
    return (
        np.searchsorted(state, values, side="left")
        + np.searchsorted(state, values, side="right")
    ) / (2.0 * len(state))


def expected_fold_ids(y: np.ndarray) -> np.ndarray:
    fold_ids = np.full(len(y), -1, dtype=np.int8)
    splitter = StratifiedKFold(5, shuffle=True, random_state=42)
    for fold, (_, valid_idx) in enumerate(splitter.split(np.zeros(len(y)), y)):
        fold_ids[valid_idx] = fold
    if np.any(fold_ids < 0):
        raise AssertionError("seed42 fold 未完整覆盖")
    return fold_ids


def nested_meta_blend(
    y: np.ndarray,
    core_oof: np.ndarray,
    candidate_oof: np.ndarray,
    fold_ids: np.ndarray,
) -> dict[str, Any]:
    baseline = np.full(len(y), np.nan, dtype=np.float64)
    blend = np.full(len(y), np.nan, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    for fold in range(5):
        hold_idx = np.flatnonzero(fold_ids == fold)
        fit_idx = np.flatnonzero(fold_ids != fold)
        core_state = fit_mid_ecdf(core_oof[fit_idx])
        candidate_state = fit_mid_ecdf(candidate_oof[fit_idx])
        core_fit = transform_mid_ecdf(core_state, core_oof[fit_idx])
        candidate_fit = transform_mid_ecdf(candidate_state, candidate_oof[fit_idx])
        core_hold = transform_mid_ecdf(core_state, core_oof[hold_idx])
        candidate_hold = transform_mid_ecdf(candidate_state, candidate_oof[hold_idx])
        fit_scores = [
            float(
                roc_auc_score(
                    y[fit_idx], (1.0 - weight) * core_fit + weight * candidate_fit
                )
            )
            for weight in WEIGHT_GRID
        ]
        best_index = max(
            range(len(WEIGHT_GRID)),
            key=lambda index: (fit_scores[index], -WEIGHT_GRID[index]),
        )
        weight = float(WEIGHT_GRID[best_index])
        baseline[hold_idx] = core_hold
        blend[hold_idx] = (1.0 - weight) * core_hold + weight * candidate_hold
        baseline_auc = float(roc_auc_score(y[hold_idx], baseline[hold_idx]))
        blend_auc = float(roc_auc_score(y[hold_idx], blend[hold_idx]))
        rows.append(
            {
                "fold": fold + 1,
                "selected_candidate_weight": weight,
                "meta_train_auc": fit_scores[best_index],
                "holdout_baseline_auc": baseline_auc,
                "holdout_blend_auc": blend_auc,
                "holdout_delta": blend_auc - baseline_auc,
            }
        )
    if not np.isfinite(baseline).all() or not np.isfinite(blend).all():
        raise AssertionError("meta OOF 覆盖不完整")
    baseline_auc = float(roc_auc_score(y, baseline))
    blend_auc = float(roc_auc_score(y, blend))
    return {
        "baseline_auc": baseline_auc,
        "blend_auc": blend_auc,
        "delta": blend_auc - baseline_auc,
        "positive_folds": sum(row["holdout_delta"] > 0.0 for row in rows),
        "rows": rows,
    }


def load_and_validate_oof(
    oof_path: Path, train: pd.DataFrame, y: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    with np.load(oof_path, allow_pickle=False) as archive:
        expected_keys = {"id", "target", "prediction", "fold"}
        if set(archive.files) != expected_keys:
            raise ValueError(f"OOF schema 漂移：{archive.files}")
        ids = np.asarray(archive["id"])
        target = np.asarray(archive["target"])
        prediction = np.asarray(archive["prediction"], dtype=np.float64)
        fold_ids = np.asarray(archive["fold"], dtype=np.int8)
    expected_shape = (len(train),)
    if any(values.shape != expected_shape for values in (ids, target, prediction, fold_ids)):
        raise ValueError("OOF shape 不匹配")
    if not np.array_equal(ids, train["id"].to_numpy()):
        raise ValueError("OOF ID 顺序不匹配")
    if not np.array_equal(target, y):
        raise ValueError("OOF target 不匹配")
    if not np.array_equal(fold_ids, expected_fold_ids(y)):
        raise ValueError("OOF fold 与预注册 seed42 五折不匹配")
    if not np.isfinite(prediction).all() or np.any((prediction < 0) | (prediction > 1)):
        raise ValueError("OOF prediction 非有限或越界")
    return prediction, fold_ids


def evaluate(oof_path: Path) -> dict[str, Any]:
    train = pd.read_csv(TRAIN_PATH)
    y = train["Will_Buy_EV"].eq("Yes").to_numpy(np.int8)
    candidate, fold_ids = load_and_validate_oof(oof_path, train, y)
    core = np.load(V90_PATH, allow_pickle=False).astype(np.float64, copy=False)
    if core.shape != y.shape or not np.isfinite(core).all():
        raise ValueError("v90 OOF 非法")
    fold_rows = []
    for fold in range(5):
        valid = fold_ids == fold
        fold_rows.append(
            {
                "fold": fold + 1,
                "rows": int(valid.sum()),
                "ctboost_auc": float(roc_auc_score(y[valid], candidate[valid])),
                "v90_auc": float(roc_auc_score(y[valid], core[valid])),
            }
        )
    candidate_auc = float(roc_auc_score(y, candidate))
    meta = nested_meta_blend(y, core, candidate, fold_ids)
    strength_passed = candidate_auc >= MIN_MODEL_AUC
    diversity_passed = (
        meta["delta"] >= MIN_BLEND_DELTA and meta["positive_folds"] == 5
    )
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": "TEMP_CTBOOST_REMOTE_5FOLD_SEED42",
        "counts_toward_c01": False,
        "remote_kernel": {
            "ref": "yaoguang516/s6e9-ctboost-oof-audit",
            "version": 1,
            "private": True,
            "competition_submitted": False,
        },
        "protocol": {
            "folds": 5,
            "seed": 42,
            "minimum_model_auc": MIN_MODEL_AUC,
            "minimum_nested_meta_delta": MIN_BLEND_DELTA,
            "required_positive_meta_folds": 5,
            "meta_weight_grid": WEIGHT_GRID.tolist(),
            "leaderboard_used_for_selection": False,
            "test_prediction_ignored": True,
        },
        "folds": fold_rows,
        "aggregate": {
            "ctboost_auc": candidate_auc,
            "spearman_vs_v90": float(spearmanr(candidate, core).statistic),
            "nested_v90_blend": meta,
            "strength_gate_passed": strength_passed,
            "diversity_gate_passed": diversity_passed,
            "decision": (
                "FORMAL_40F_GO"
                if strength_passed and diversity_passed
                else "NO_GO"
            ),
        },
        "source_sha256": {
            "evaluate_oof.py": sha256_file(Path(__file__)),
            "remote_oof.npz": sha256_file(oof_path),
            "train.csv": sha256_file(TRAIN_PATH),
            "v90_oof": sha256_file(V90_PATH),
        },
    }
    atomic_json(EVIDENCE_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oof", type=Path, default=DEFAULT_OOF_PATH)
    args = parser.parse_args()
    payload = evaluate(args.oof.resolve())
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
