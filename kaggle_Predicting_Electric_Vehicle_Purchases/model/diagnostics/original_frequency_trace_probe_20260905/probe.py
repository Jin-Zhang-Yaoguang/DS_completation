#!/usr/bin/env python3
"""一次性五折配对诊断：strict-v96 vs 收入 original-frequency trace 特征。

本诊断不生成 test 预测、submission 或可复用 OOF 文件。只有完整五折的聚合证据
会写入 evidence.json；重复运行会被 RUN_STARTED.json 拒绝。
"""

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
EVIDENCE_PATH = OUT_DIR / "evidence_r1.json"
START_MARKER = OUT_DIR / "RUN_STARTED_R1.json"
V96_PATH = (
    PROJECT_DIR
    / "model/v96_strict_v80_outer42_matched_control_40f"
    / "v96_strict_v80_outer42_matched_control_40f.py"
)
V96_CONFIG_PATH = V96_PATH.with_name("frozen_config.json")
ORIGINAL_PATH = (
    PROJECT_DIR
    / "data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv"
)

OUTER_FOLDS = 5
OUTER_SEED = 42
WALL_BUDGET_SECONDS = 1800.0
MEMORY_BUDGET_BYTES = 8 * 1024**3
GATE_DELTA = 0.0001
GATE_WINS = 4
FEATURE_COLUMNS = [
    "income_original_frequency",
    "income_comp_over_original_lift",
    "income_original_novel",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("v96_frequency_probe_source", path)
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


def build_income_frequency_trace(
    train: pd.DataFrame,
    test: pd.DataFrame,
    original: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """从竞赛 train+test 与 original 的无标签边际频率构造三列。"""
    column = "Annual_Income_USD"
    for label, frame in (("train", train), ("test", test), ("original", original)):
        if column not in frame:
            raise ValueError(f"{label} missing {column}")
        values = frame[column].to_numpy(np.float64)
        if label == "original":
            if np.isinf(values).any():
                raise ValueError(f"{label} {column} contains Inf")
        elif not np.isfinite(values).all():
            raise ValueError(f"{label} {column} contains NaN/Inf")

    competition_values = pd.concat(
        [train[column], test[column]], ignore_index=True
    )
    competition_frequency = competition_values.value_counts(normalize=True)
    original_frequency = original[column].value_counts(normalize=True)

    def transform(frame: pd.DataFrame) -> pd.DataFrame:
        comp = frame[column].map(competition_frequency).to_numpy(np.float64)
        orig = (
            frame[column]
            .map(original_frequency)
            .fillna(0.0)
            .to_numpy(np.float64)
        )
        lift = np.divide(comp, orig, out=np.zeros_like(comp), where=orig > 0.0)
        block = pd.DataFrame(
            {
                FEATURE_COLUMNS[0]: orig.astype(np.float32),
                FEATURE_COLUMNS[1]: lift.astype(np.float32),
                FEATURE_COLUMNS[2]: (orig == 0.0).astype(np.float32),
            }
        )
        if not np.isfinite(block.to_numpy(np.float64)).all():
            raise ValueError("frequency trace block contains NaN/Inf")
        return block

    train_block = transform(train)
    test_block = transform(test)
    profile = {
        "columns": FEATURE_COLUMNS,
        "competition_rows": int(len(competition_values)),
        "original_rows": int(len(original)),
        "original_nonmissing_income_rows": int(original[column].notna().sum()),
        "original_missing_income_rows": int(original[column].isna().sum()),
        "competition_unique_income": int(competition_values.nunique()),
        "original_unique_income": int(original[column].nunique()),
        "train_novel_rows": int(train_block[FEATURE_COLUMNS[2]].sum()),
        "test_novel_rows": int(test_block[FEATURE_COLUMNS[2]].sum()),
        "uses_target": False,
        "uses_test_labels": False,
        "competition_frequency_scope": "train_plus_test_features_only",
    }
    return train_block, test_block, profile


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temp, path)


def run() -> dict[str, Any]:
    started = time.monotonic()
    marker = {
        "status": "RUN_STARTED_ONE_SHOT",
        "pid": os.getpid(),
        "outer_folds": OUTER_FOLDS,
        "outer_seed": OUTER_SEED,
    }
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump(marker, handle, ensure_ascii=False, indent=2)
    except FileExistsError as error:
        raise RuntimeError("one-shot run marker already exists; refusing rerun") from error

    script_sha = sha256_file(Path(__file__))
    config = json.loads(V96_CONFIG_PATH.read_text(encoding="utf-8"))
    source = load_module(V96_PATH)
    recipe = source.load_recipe()
    train, test, _sample = recipe.base.load_data()
    original = pd.read_csv(ORIGINAL_PATH)
    y = train[config["target"]].eq(config["positive_label"]).to_numpy(np.int8)
    x_train, _x_test, keys_train, keys_test = recipe.base.build_static_features(
        train, test
    )
    block_train, _block_test, block_profile = build_income_frequency_trace(
        train, test, original
    )
    if x_train.shape[1] != int(config["expected_static_features"]):
        raise ValueError("strict-v96 static feature count drift")
    if set(x_train.columns).intersection(block_train.columns):
        raise ValueError("candidate block duplicates a strict-v96 column name")
    if train[config["target"]].sample(frac=1.0, random_state=17).reset_index(drop=True).equals(
        train[config["target"]]
    ):
        raise AssertionError("target permutation guard unexpectedly unchanged")
    target_flipped = train.copy()
    target_flipped[config["target"]] = target_flipped[config["target"]].iloc[::-1].to_numpy()
    flipped_block, _, _ = build_income_frequency_trace(target_flipped, test, original)
    pd.testing.assert_frame_equal(block_train, flipped_block)

    oof_a = np.full(len(train), np.nan, dtype=np.float64)
    oof_b = np.full(len(train), np.nan, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    checks = [resource_guard(started, "AFTER_DATA_PREP")]
    folds = list(
        StratifiedKFold(
            n_splits=OUTER_FOLDS, shuffle=True, random_state=OUTER_SEED
        ).split(np.zeros(len(train)), y)
    )
    params = dict(config["lightgbm_params"])

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
        x_fit_a = np.column_stack(
            [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
        )
        x_valid_a = np.column_stack(
            [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
        )
        x_fit_b = np.column_stack(
            [x_fit_a, block_train.iloc[fit_idx].to_numpy(np.float32)]
        )
        x_valid_b = np.column_stack(
            [x_valid_a, block_train.iloc[valid_idx].to_numpy(np.float32)]
        )
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
    final_check = resource_guard(started, "COMPLETE")
    checks.append(final_check)
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": "TEMP_INCOME_ORIGINAL_FREQUENCY_TRACE_AB_SEED42_R1",
        "counts_toward_c01": False,
        "public_source": {
            "discussion_id": 739354,
            "topic_message_id": 3520621,
            "topic_raw_markdown_sha256": "e2ac52098bc226c33241dbea3597650a562d2582d42e1b0f7e57372415bb41fc",
            "public_predictions_used": False,
            "leaderboard_used": False,
        },
        "source_sha256": {
            "probe.py": script_sha,
            "v96_runner": sha256_file(V96_PATH),
            "v96_config": sha256_file(V96_CONFIG_PATH),
            "original_csv": sha256_file(ORIGINAL_PATH),
        },
        "protocol": {
            "baseline": "strict-v96",
            "outer_folds": OUTER_FOLDS,
            "outer_seed": OUTER_SEED,
            "inner_te_seed_formula": "104395303 + one_based_outer_fold",
            "arm_a": "62 static + 51 strict nested TE",
            "arm_b": "arm A + three income original-frequency trace columns",
            "test_predictions_generated": False,
            "oof_arrays_saved": False,
            "submission_generated": False,
            "gate": {"minimum_delta": GATE_DELTA, "minimum_positive_folds": GATE_WINS},
        },
        "feature_profile": block_profile,
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
        "elapsed_seconds": final_check["elapsed_seconds"],
        "peak_rss_bytes": final_check["peak_rss_bytes"],
    }
    write_json(EVIDENCE_PATH, payload)
    print(json.dumps(payload["aggregate"], ensure_ascii=False, sort_keys=True))
    return payload


def audit() -> dict[str, Any]:
    original = pd.DataFrame({"Annual_Income_USD": [10.0, 10.0, 20.0]})
    train = pd.DataFrame({"Annual_Income_USD": [10.0, 20.0], "y": [0, 1]})
    test = pd.DataFrame({"Annual_Income_USD": [10.0, 30.0]})
    block, test_block, profile = build_income_frequency_trace(train, test, original)
    return {
        "status": "AUDIT_OK_NO_TRAINING",
        "columns": list(block.columns),
        "train": block.to_dict("list"),
        "test": test_block.to_dict("list"),
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
