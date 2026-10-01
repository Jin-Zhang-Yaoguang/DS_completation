#!/usr/bin/env python3
"""一次性五折配对诊断：strict-v96 vs 严格交叉拟合收入局部曲面。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
EVIDENCE_PATH = OUT_DIR / "evidence.json"
START_MARKER = OUT_DIR / "RUN_STARTED.json"
V96_PATH = (
    PROJECT_DIR
    / "model/v96_strict_v80_outer42_matched_control_40f"
    / "v96_strict_v80_outer42_matched_control_40f.py"
)
V96_CONFIG_PATH = V96_PATH.with_name("frozen_config.json")

OUTER_FOLDS = 5
OUTER_SEED = 42
Q_BINS = 16_384
SMOOTH = 10.0
WALL_BUDGET_SECONDS = 1800.0
MEMORY_BUDGET_BYTES = 8 * 1024**3
GATE_DELTA = 0.0001
GATE_WINS = 4
FEATURE_COLUMNS = [
    "income_surface_position",
    "income_surface_central",
    "income_surface_symmetric",
    "income_surface_left",
    "income_surface_right",
    "income_surface_slope",
    "income_surface_curvature",
    "income_surface_log_count",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("v96_surface_probe_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return native if sys.platform == "darwin" else native * 1024


def resource_guard(started: float, phase: str) -> dict[str, Any]:
    row = {
        "phase": phase,
        "elapsed_seconds": float(time.monotonic() - started),
        "peak_rss_bytes": peak_rss_bytes(),
    }
    row["wall_ok"] = row["elapsed_seconds"] <= WALL_BUDGET_SECONDS
    row["memory_ok"] = row["peak_rss_bytes"] <= MEMORY_BUDGET_BYTES
    if not row["wall_ok"] or not row["memory_ok"]:
        raise RuntimeError(f"resource budget exceeded at {phase}: {row}")
    return row


def bin_statistics(
    codes: np.ndarray,
    labels: np.ndarray,
    n_bins: int,
    prior: float,
    smooth: float,
) -> np.ndarray:
    sums = np.bincount(codes, weights=labels, minlength=n_bins).astype(np.float64)
    counts = np.bincount(codes, minlength=n_bins).astype(np.float64)
    central = (sums + smooth * prior) / (counts + smooth)
    left_sums = np.r_[0.0, sums[:-1]]
    left_counts = np.r_[0.0, counts[:-1]]
    right_sums = np.r_[sums[1:], 0.0]
    right_counts = np.r_[counts[1:], 0.0]
    left = (left_sums + smooth * prior) / (left_counts + smooth)
    right = (right_sums + smooth * prior) / (right_counts + smooth)
    kernel = np.exp(-0.5 * (np.arange(-1, 2) / 0.8) ** 2)
    neighbor_sums = np.convolve(sums, kernel, mode="same")
    neighbor_counts = np.convolve(counts, kernel, mode="same")
    symmetric = (neighbor_sums + smooth * kernel.sum() * prior) / (
        neighbor_counts + smooth * kernel.sum()
    )
    slope = right - left
    curvature = central - 0.5 * (left + right)
    return np.column_stack(
        [central, symmetric, left, right, slope, curvature, np.log1p(counts)]
    ).astype(np.float32)


def build_income_local_surface(
    fit_income: np.ndarray,
    fit_y: np.ndarray,
    valid_income: np.ndarray,
    inner_splits: list[tuple[np.ndarray, np.ndarray]],
    *,
    q: int = Q_BINS,
    smooth: float = SMOOTH,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """严格生成 inner-OOF fit 特征和 outer-fit→valid 特征。"""
    fit_income = np.asarray(fit_income, dtype=np.float64)
    valid_income = np.asarray(valid_income, dtype=np.float64)
    fit_y = np.asarray(fit_y, dtype=np.int8)
    if not np.isfinite(fit_income).all() or not np.isfinite(valid_income).all():
        raise ValueError("income contains NaN/Inf")
    if q < 2 or smooth <= 0.0:
        raise ValueError("invalid q/smooth")
    edges = np.linspace(float(fit_income.min()), float(fit_income.max()), q + 1)
    fit_codes = np.searchsorted(edges[1:-1], fit_income)
    valid_codes = np.searchsorted(edges[1:-1], valid_income)
    n_bins = len(edges)
    position_scale = max(n_bins - 2, 1)
    fit_features = np.full((len(fit_income), len(FEATURE_COLUMNS)), np.nan, np.float32)
    coverage = np.zeros(len(fit_income), dtype=np.int8)

    for inner_fit, inner_valid in inner_splits:
        # 关键修复：prior 只来自 inner-train，不能用完整 outer-fit 均值。
        inner_prior = float(fit_y[inner_fit].mean())
        stats = bin_statistics(
            fit_codes[inner_fit], fit_y[inner_fit], n_bins, inner_prior, smooth
        )
        fit_features[inner_valid, 0] = fit_codes[inner_valid] / position_scale
        fit_features[inner_valid, 1:] = stats[fit_codes[inner_valid]]
        coverage[inner_valid] += 1
    if not np.all(coverage == 1):
        raise ValueError("inner split does not cover each fit row exactly once")

    outer_prior = float(fit_y.mean())
    outer_stats = bin_statistics(fit_codes, fit_y, n_bins, outer_prior, smooth)
    valid_features = np.column_stack(
        [valid_codes / position_scale, outer_stats[valid_codes]]
    ).astype(np.float32)
    if not np.isfinite(fit_features).all() or not np.isfinite(valid_features).all():
        raise ValueError("income local surface contains NaN/Inf")
    profile = {
        "columns": FEATURE_COLUMNS,
        "q": q,
        "n_bins_allocated": n_bins,
        "smooth": smooth,
        "inner_prior_contract": "each inner-train labels only",
        "outer_valid_contract": "complete outer-fit labels only",
        "uses_outer_valid_labels": False,
    }
    return fit_features, valid_features, profile


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temp, path)


def run() -> dict[str, Any]:
    started = time.monotonic()
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump(
                {
                    "status": "RUN_STARTED_ONE_SHOT",
                    "pid": os.getpid(),
                    "outer_folds": OUTER_FOLDS,
                    "outer_seed": OUTER_SEED,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
    except FileExistsError as error:
        raise RuntimeError("one-shot run marker already exists; refusing rerun") from error

    script_sha = sha256_file(Path(__file__))
    config = json.loads(V96_CONFIG_PATH.read_text(encoding="utf-8"))
    source = load_module(V96_PATH)
    recipe = source.load_recipe()
    train, test, _sample = recipe.base.load_data()
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    x_train, _x_test, keys_train, keys_test = recipe.base.build_static_features(
        train, test
    )
    if x_train.shape[1] != int(config["expected_static_features"]):
        raise ValueError("strict-v96 static feature count drift")

    oof_a = np.full(len(train), np.nan, dtype=np.float64)
    oof_b = np.full(len(train), np.nan, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    surface_profiles: list[dict[str, Any]] = []
    checks = [resource_guard(started, "AFTER_DATA_PREP")]
    folds = list(
        StratifiedKFold(
            n_splits=OUTER_FOLDS, shuffle=True, random_state=OUTER_SEED
        ).split(np.zeros(len(train)), y)
    )
    params = dict(config["lightgbm_params"])
    income = train["Annual_Income_USD"].to_numpy(np.float64)

    for fold, (fit_idx, valid_idx) in enumerate(folds, start=1):
        fold_started = time.monotonic()
        checks.append(resource_guard(started, f"FOLD_{fold}_START"))
        inner = list(
            StratifiedKFold(
                n_splits=int(config["n_inner_folds"]),
                shuffle=True,
                random_state=int(config["inner_te_seed_base"]) + fold,
            ).split(np.zeros(len(fit_idx)), y[fit_idx])
        )
        fit_te: list[np.ndarray] = []
        valid_te: list[np.ndarray] = []
        for key in recipe.base.TE_KEYS:
            fit_block, valid_block, _unused_test = source.strict_encode_key(
                keys_train[key],
                keys_test[key],
                y,
                fit_idx,
                valid_idx,
                inner,
                tuple(config["smooths"]),
            )
            fit_te.append(fit_block)
            valid_te.append(valid_block)
        surface_fit, surface_valid, surface_profile = build_income_local_surface(
            income[fit_idx], y[fit_idx], income[valid_idx], inner
        )
        surface_profiles.append(surface_profile)
        x_fit_a = np.column_stack(
            [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
        )
        x_valid_a = np.column_stack(
            [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
        )
        x_fit_b = np.column_stack([x_fit_a, surface_fit])
        x_valid_b = np.column_stack([x_valid_a, surface_valid])
        del fit_te, valid_te, _unused_test

        arm_rows: dict[str, Any] = {"fold": fold, "valid_rows": len(valid_idx)}
        for arm, x_fit, x_valid, target in (
            ("a", x_fit_a, x_valid_a, oof_a),
            ("b", x_fit_b, x_valid_b, oof_b),
        ):
            model = lgb.LGBMClassifier(**params)
            model.fit(
                x_fit,
                y[fit_idx],
                eval_set=[(x_valid, y[valid_idx])],
                eval_metric="auc",
                callbacks=[
                    lgb.early_stopping(
                        int(config["early_stopping_rounds"]), verbose=False
                    )
                ],
            )
            prediction = model.predict_proba(x_valid)[:, 1]
            target[valid_idx] = prediction
            arm_rows[f"{arm}_auc"] = float(roc_auc_score(y[valid_idx], prediction))
            arm_rows[f"{arm}_best_iteration"] = int(model.best_iteration_)
            del model, prediction
        arm_rows["delta_b_minus_a"] = arm_rows["b_auc"] - arm_rows["a_auc"]
        arm_rows["elapsed_seconds"] = float(time.monotonic() - fold_started)
        rows.append(arm_rows)
        checks.append(resource_guard(started, f"FOLD_{fold}_END"))
        print(json.dumps(arm_rows, ensure_ascii=False, sort_keys=True), flush=True)

    if not np.isfinite(oof_a).all() or not np.isfinite(oof_b).all():
        raise RuntimeError("incomplete pooled OOF")
    pooled_a = float(roc_auc_score(y, oof_a))
    pooled_b = float(roc_auc_score(y, oof_b))
    delta = pooled_b - pooled_a
    wins = sum(row["delta_b_minus_a"] > 0.0 for row in rows)
    passed = delta >= GATE_DELTA and wins >= GATE_WINS
    checks.append(resource_guard(started, "COMPLETE"))
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": "TEMP_STRICT_INCOME_LOCAL_SURFACE_AB_SEED42",
        "counts_toward_c01": False,
        "public_source": {
            "notebook_ref": "jazivxt/single-model-zoom-zoom",
            "notebook_sha256": "36eed7ecb78956c562dca5f6a728c2c3d34f591f8d762871560c78fcdaba51c8",
            "public_oof_used": False,
            "leaderboard_used": False,
            "reimplementation_note": "inner prior repaired to each inner-train mean",
        },
        "historical_distinction": {
            "v73": "fixed-width income category TE variants; no left/right/slope/curvature continuous local surface",
            "public_protocol_defect": "public fit_y.mean prior includes inner-hold labels",
        },
        "source_sha256": {
            "probe.py": script_sha,
            "v96_runner": sha256_file(V96_PATH),
            "v96_config": sha256_file(V96_CONFIG_PATH),
        },
        "protocol": {
            "baseline": "strict-v96",
            "outer_folds": OUTER_FOLDS,
            "outer_seed": OUTER_SEED,
            "inner_te_and_surface_seed_formula": "104395303 + one_based_outer_fold",
            "arm_a": "62 static + 51 strict nested TE",
            "arm_b": "arm A + eight strict inner-OOF income surface columns",
            "test_predictions_generated": False,
            "oof_arrays_saved": False,
            "submission_generated": False,
            "gate": {"minimum_delta": GATE_DELTA, "minimum_positive_folds": GATE_WINS},
        },
        "surface_profile": surface_profiles[0],
        "folds": rows,
        "aggregate": {
            "pooled_a_auc": pooled_a,
            "pooled_b_auc": pooled_b,
            "pooled_delta_b_minus_a": delta,
            "positive_folds": wins,
            "decision": "FORMAL_CANDIDATE_GO" if passed else "NO_GO",
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "sklearn": sklearn.__version__,
            "lightgbm": lgb.__version__,
        },
        "resource_checks": checks,
        "elapsed_seconds": checks[-1]["elapsed_seconds"],
        "peak_rss_bytes": checks[-1]["peak_rss_bytes"],
    }
    write_json(EVIDENCE_PATH, payload)
    print(json.dumps(payload["aggregate"], ensure_ascii=False, sort_keys=True))
    return payload


def audit() -> dict[str, Any]:
    fit_income = np.arange(12, dtype=np.float64) * 10.0
    fit_y = np.asarray([0, 1] * 6, dtype=np.int8)
    splits = list(
        StratifiedKFold(3, shuffle=True, random_state=42).split(fit_income, fit_y)
    )
    fit, valid, profile = build_income_local_surface(
        fit_income, fit_y, np.asarray([15.0, 75.0]), splits, q=8, smooth=2.0
    )
    return {
        "status": "AUDIT_OK_NO_TRAINING",
        "fit_shape": list(fit.shape),
        "valid_shape": list(valid.shape),
        "all_finite": bool(np.isfinite(fit).all() and np.isfinite(valid).all()),
        "profile": profile,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["audit", "run"], default="audit")
    args = parser.parse_args()
    result = run() if args.mode == "run" else audit()
    if args.mode == "audit":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
