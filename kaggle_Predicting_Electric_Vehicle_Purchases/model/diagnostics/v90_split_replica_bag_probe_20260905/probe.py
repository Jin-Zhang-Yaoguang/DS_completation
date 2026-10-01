#!/usr/bin/env python3
"""v90 加 strict split-replica family bag 的嵌套元验证诊断。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import time
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
V100_PATH = PROJECT_DIR / "model/v100_v90_ctboost_nested_cv_blend/oof_proba.npy"
MEMBERS = {
    "v81_split7": PROJECT_DIR / "model/v81_strict_v61_split7_40f/oof_proba.npy",
    "v82_split2026": PROJECT_DIR / "model/v82_strict_v61_split2026_40f/oof_proba.npy",
    "v96_split42": PROJECT_DIR / "model/v96_strict_v80_outer42_matched_control_40f/oof_proba.npy",
}
START_MARKER = OUT_DIR / "RUN_STARTED.json"
EVIDENCE_PATH = OUT_DIR / "evidence.json"
EXPERIMENT_ID = "TEMP_V90_SPLIT_REPLICA_BAG_NESTED_META_SEED42"
WEIGHT_GRID = np.arange(0.0, 0.5000001, 0.025)
MIN_FAMILY_AUC = 0.9462
MIN_DELTA = 0.0001
WALL_BUDGET_SECONDS = 120.0
MEMORY_BUDGET_BYTES = 8 * 1024**3


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
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("ECDF fit 输入非法")
    return np.sort(values)


def transform_mid_ecdf(state: np.ndarray, values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return (
        np.searchsorted(state, values, side="left")
        + np.searchsorted(state, values, side="right")
    ) / (2.0 * len(state))


def choose_weight(y: np.ndarray, core: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    scores = [
        float(roc_auc_score(y, (1.0 - weight) * core + weight * candidate))
        for weight in WEIGHT_GRID
    ]
    index = max(range(len(WEIGHT_GRID)), key=lambda i: (scores[i], -WEIGHT_GRID[i]))
    return float(WEIGHT_GRID[index]), scores[index]


def nested_meta(y: np.ndarray, core: np.ndarray, candidate: np.ndarray) -> dict[str, Any]:
    baseline = np.full(len(y), np.nan)
    blend = np.full(len(y), np.nan)
    rows = []
    splits = StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(y)), y)
    for fold, (fit_idx, hold_idx) in enumerate(splits, start=1):
        core_state = fit_mid_ecdf(core[fit_idx])
        candidate_state = fit_mid_ecdf(candidate[fit_idx])
        core_fit = transform_mid_ecdf(core_state, core[fit_idx])
        candidate_fit = transform_mid_ecdf(candidate_state, candidate[fit_idx])
        core_hold = transform_mid_ecdf(core_state, core[hold_idx])
        candidate_hold = transform_mid_ecdf(candidate_state, candidate[hold_idx])
        weight, fit_auc = choose_weight(y[fit_idx], core_fit, candidate_fit)
        baseline[hold_idx] = core_hold
        blend[hold_idx] = (1.0 - weight) * core_hold + weight * candidate_hold
        base_auc = float(roc_auc_score(y[hold_idx], baseline[hold_idx]))
        blend_auc = float(roc_auc_score(y[hold_idx], blend[hold_idx]))
        rows.append(
            {
                "fold": fold,
                "selected_family_weight": weight,
                "meta_train_auc": fit_auc,
                "holdout_baseline_auc": base_auc,
                "holdout_blend_auc": blend_auc,
                "holdout_delta": blend_auc - base_auc,
            }
        )
    base_auc = float(roc_auc_score(y, baseline))
    blend_auc = float(roc_auc_score(y, blend))
    return {
        "baseline_auc": base_auc,
        "blend_auc": blend_auc,
        "delta": blend_auc - base_auc,
        "positive_folds": sum(row["holdout_delta"] > 0 for row in rows),
        "rows": rows,
    }


def audit() -> dict[str, Any]:
    sources = {"train.csv": TRAIN_PATH, "v90": V90_PATH, "v100": V100_PATH} | MEMBERS
    return {
        "status": "AUDIT_OK_HASH_ONLY",
        "experiment_id": EXPERIMENT_ID,
        "sources": {name: sha256_file(path) for name, path in sources.items()},
        "member_weights": {name: 1 / 3 for name in MEMBERS},
        "weight_grid": WEIGHT_GRID.tolist(),
    }


def run() -> dict[str, Any]:
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump({"status": "RUN_STARTED_ONE_SHOT", "pid": os.getpid()}, handle)
    except FileExistsError as error:
        raise RuntimeError("one-shot marker 已存在") from error
    started = time.monotonic()
    sources = audit()["sources"]
    train = pd.read_csv(TRAIN_PATH)
    y = train["Will_Buy_EV"].eq("Yes").to_numpy(np.int8)
    core = np.load(V90_PATH, allow_pickle=False).astype(np.float64, copy=False)
    current_best = np.load(V100_PATH, allow_pickle=False).astype(np.float64, copy=False)
    member_values = {
        name: np.load(path, allow_pickle=False).astype(np.float64, copy=False)
        for name, path in MEMBERS.items()
    }
    for name, values in ({"v90": core, "v100": current_best} | member_values).items():
        if values.shape != y.shape or not np.isfinite(values).all():
            raise ValueError(f"{name} OOF 非法")
    family = np.mean(np.stack(list(member_values.values())), axis=0)
    family_auc = float(roc_auc_score(y, family))
    meta = nested_meta(y, core, family)
    current_best_auc = float(roc_auc_score(y, current_best))
    gate = (
        family_auc >= MIN_FAMILY_AUC
        and meta["delta"] >= MIN_DELTA
        and meta["positive_folds"] == 5
    )
    elapsed = float(time.monotonic() - started)
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    peak = peak if sys.platform == "darwin" else peak * 1024
    if elapsed > WALL_BUDGET_SECONDS or peak > MEMORY_BUDGET_BYTES:
        raise RuntimeError("resource budget exceeded")
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "counts_toward_c01": False,
        "protocol": {
            "family_member_weights": {name: 1 / 3 for name in MEMBERS},
            "meta_folds": 5,
            "meta_seed": 42,
            "transform": "fit-only mid-ECDF",
            "weight_grid": WEIGHT_GRID.tolist(),
            "minimum_family_auc": MIN_FAMILY_AUC,
            "minimum_nested_delta": MIN_DELTA,
            "required_positive_meta_folds": 5,
            "submission_generated": False,
            "oof_saved": False,
        },
        "aggregate": {
            "member_auc": {
                name: float(roc_auc_score(y, values)) for name, values in member_values.items()
            },
            "family_auc": family_auc,
            "family_spearman_vs_v90": float(spearmanr(family, core).statistic),
            "nested_v90_family_blend": meta,
            "current_numeric_best_v100_auc": current_best_auc,
            "delta_nested_blend_vs_v100": meta["blend_auc"] - current_best_auc,
            "formal_gate_passed": gate,
            "decision": "FORMAL_GO" if gate else "NO_GO",
        },
        "source_sha256": sources | {"probe.py": sha256_file(Path(__file__))},
        "elapsed_seconds": elapsed,
        "peak_rss_bytes": peak,
    }
    atomic_json(EVIDENCE_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "run"), default="audit")
    args = parser.parse_args()
    payload = run() if args.mode == "run" else audit()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
