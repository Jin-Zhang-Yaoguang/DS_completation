#!/usr/bin/env python3
"""strict-v96 LightGBM control vs extra_trees 的 seed42 五折配对诊断。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
V96_DIR = PROJECT_DIR / "model/v96_strict_v80_outer42_matched_control_40f"
V96_RUNNER = V96_DIR / "v96_strict_v80_outer42_matched_control_40f.py"
V96_CONFIG = V96_DIR / "frozen_config.json"
V100_OOF = PROJECT_DIR / "model/v100_v90_ctboost_nested_cv_blend/oof_proba.npy"
START_MARKER = OUT_DIR / "RUN_STARTED.json"
EVIDENCE_PATH = OUT_DIR / "evidence.json"
EXPERIMENT_ID = "TEMP_STRICT_LGBM_EXTRA_TREES_AB_SEED42"
WEIGHT_GRID = np.arange(0.0, 0.5000001, 0.025)
GATE_DELTA = 0.0001
GATE_WINS = 4
MIN_DIVERSITY_AUC = 0.9452
WALL_BUDGET_SECONDS = 900.0
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


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("extra_trees_v96", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def peak_rss_bytes() -> int:
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return native if sys.platform == "darwin" else native * 1024


def guard(started: float, phase: str) -> dict[str, Any]:
    row = {
        "phase": phase,
        "elapsed_seconds": float(time.monotonic() - started),
        "peak_rss_bytes": peak_rss_bytes(),
    }
    row["wall_ok"] = row["elapsed_seconds"] <= WALL_BUDGET_SECONDS
    row["memory_ok"] = row["peak_rss_bytes"] <= MEMORY_BUDGET_BYTES
    if not row["wall_ok"] or not row["memory_ok"]:
        raise RuntimeError(f"resource budget exceeded: {row}")
    return row


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
        scores = [
            float(roc_auc_score(y[fit_idx], (1 - weight) * core_fit + weight * candidate_fit))
            for weight in WEIGHT_GRID
        ]
        index = max(range(len(WEIGHT_GRID)), key=lambda i: (scores[i], -WEIGHT_GRID[i]))
        weight = float(WEIGHT_GRID[index])
        baseline[hold_idx] = core_hold
        blend[hold_idx] = (1 - weight) * core_hold + weight * candidate_hold
        base_auc = float(roc_auc_score(y[hold_idx], baseline[hold_idx]))
        blend_auc = float(roc_auc_score(y[hold_idx], blend[hold_idx]))
        rows.append(
            {
                "fold": fold,
                "selected_candidate_weight": weight,
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


def frozen_design() -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "outer_folds": 5,
        "outer_seed": 42,
        "arm_a": "strict-v96 params unchanged",
        "arm_b_override": {"extra_trees": True, "extra_seed": 104395303},
        "only_variable": "random threshold split selection",
        "strength_gate": {"delta": GATE_DELTA, "wins": GATE_WINS},
        "diversity_gate": {
            "minimum_candidate_auc": MIN_DIVERSITY_AUC,
            "delta": GATE_DELTA,
            "wins": 5,
        },
        "submission_budget": 0,
        "oof_saved": False,
        "test_generated": False,
        "no_grid_or_retry": True,
    }


def audit() -> dict[str, Any]:
    config = json.loads(V96_CONFIG.read_text(encoding="utf-8"))
    params_a = dict(config["lightgbm_params"])
    params_b = dict(params_a) | {"extra_trees": True, "extra_seed": 104395303}
    added = {key: value for key, value in params_b.items() if params_a.get(key) != value}
    if added != {"extra_trees": True, "extra_seed": 104395303}:
        raise AssertionError("B 参数差异漂移")
    return {
        "status": "AUDIT_OK_NO_TRAINING",
        "frozen_design": frozen_design(),
        "source_sha256": {
            "v96_runner": sha256_file(V96_RUNNER),
            "v96_config": sha256_file(V96_CONFIG),
            "v100_oof": sha256_file(V100_OOF),
        },
    }


def run() -> dict[str, Any]:
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump({"status": "RUN_STARTED_ONE_SHOT", "pid": os.getpid()}, handle)
    except FileExistsError as error:
        raise RuntimeError("one-shot marker 已存在") from error
    started = time.monotonic()
    runner_sha = sha256_file(Path(__file__))
    checks = [guard(started, "START")]
    audit_payload = audit()
    config = json.loads(V96_CONFIG.read_text(encoding="utf-8"))
    source = load_module(V96_RUNNER)
    recipe = source.load_recipe()
    train, test, _sample = recipe.base.load_data()
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    x_train, _x_test, keys_train, keys_test = recipe.base.build_static_features(train, test)
    current_best = np.load(V100_OOF, allow_pickle=False).astype(np.float64, copy=False)
    if current_best.shape != y.shape or not np.isfinite(current_best).all():
        raise ValueError("v100 OOF 非法")
    oof_a = np.full(len(y), np.nan)
    oof_b = np.full(len(y), np.nan)
    rows = []
    splits = StratifiedKFold(5, shuffle=True, random_state=42).split(x_train, y)
    for fold, (fit_idx, valid_idx) in enumerate(splits, start=1):
        inner = list(
            StratifiedKFold(
                config["n_inner_folds"],
                shuffle=True,
                random_state=config["inner_te_seed_base"] + fold,
            ).split(np.zeros(len(fit_idx)), y[fit_idx])
        )
        fit_te, valid_te = [], []
        for key in recipe.base.TE_KEYS:
            fit_block, valid_block, _ = source.strict_encode_key(
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
        x_fit = np.column_stack([x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te])
        x_valid = np.column_stack([x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te])
        del fit_te, valid_te
        row = {"fold": fold}
        for arm, override, target in (
            ("a", {}, oof_a),
            ("b", {"extra_trees": True, "extra_seed": 104395303}, oof_b),
        ):
            params = dict(config["lightgbm_params"]) | override
            model = lgb.LGBMClassifier(**params)
            model.fit(
                x_fit,
                y[fit_idx],
                eval_set=[(x_valid, y[valid_idx])],
                eval_metric="auc",
                callbacks=[
                    lgb.early_stopping(config["early_stopping_rounds"], verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            prediction = model.predict_proba(x_valid, num_iteration=model.best_iteration_)[:, 1]
            target[valid_idx] = prediction
            row[f"auc_{arm}"] = float(roc_auc_score(y[valid_idx], prediction))
            row[f"best_iteration_{arm}"] = int(model.best_iteration_)
        row["delta_b_minus_a"] = row["auc_b"] - row["auc_a"]
        rows.append(row)
        checks.append(guard(started, f"FOLD_{fold}"))
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
        del x_fit, x_valid
    if not np.isfinite(oof_a).all() or not np.isfinite(oof_b).all():
        raise RuntimeError("OOF coverage 不完整")
    auc_a = float(roc_auc_score(y, oof_a))
    auc_b = float(roc_auc_score(y, oof_b))
    delta = auc_b - auc_a
    wins = sum(row["delta_b_minus_a"] > 0 for row in rows)
    meta = nested_meta(y, current_best, oof_b)
    strength = delta >= GATE_DELTA and wins >= GATE_WINS
    diversity = (
        auc_b >= MIN_DIVERSITY_AUC
        and meta["delta"] >= GATE_DELTA
        and meta["positive_folds"] == 5
    )
    checks.append(guard(started, "COMPLETE"))
    if sha256_file(Path(__file__)) != runner_sha:
        raise RuntimeError("runner 在运行中漂移")
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "counts_toward_c01": False,
        "frozen_design": frozen_design(),
        "folds": rows,
        "aggregate": {
            "auc_a": auc_a,
            "auc_b": auc_b,
            "delta_b_minus_a": delta,
            "winning_folds": wins,
            "spearman_b_vs_v100": float(spearmanr(oof_b, current_best).statistic),
            "nested_v100_blend": meta,
            "strength_gate_passed": strength,
            "diversity_gate_passed": diversity,
            "decision": "FORMAL_40F_GO" if strength or diversity else "NO_GO",
        },
        "source_sha256": audit_payload["source_sha256"] | {"probe.py": runner_sha},
        "resource_checks": checks,
        "elapsed_seconds": checks[-1]["elapsed_seconds"],
        "peak_rss_bytes": checks[-1]["peak_rss_bytes"],
    }
    atomic_json(EVIDENCE_PATH, payload)
    return payload


def preserve_failure(error: Exception) -> None:
    if EVIDENCE_PATH.exists():
        return
    atomic_json(
        EVIDENCE_PATH,
        {
            "schema_version": 1,
            "status": "FAILED_IMPLEMENTATION",
            "experiment_id": EXPERIMENT_ID,
            "error_type": type(error).__name__,
            "error": str(error),
            "decision": "CLOSE_NO_RERUN",
            "source_sha256": {"probe.py": sha256_file(Path(__file__))},
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "run"), default="audit")
    args = parser.parse_args()
    try:
        payload = run() if args.mode == "run" else audit()
    except Exception as error:
        if args.mode == "run":
            preserve_failure(error)
        raise
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
