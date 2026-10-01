#!/usr/bin/env python3
"""一次性五折三臂诊断：严格 MLP、收入频率痕迹、训练期输入遮蔽。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = OUT_DIR.parents[2]
DATA_DIR = PROJECT_DIR / "data"
EVIDENCE_PATH = OUT_DIR / "evidence.json"
START_MARKER = OUT_DIR / "RUN_STARTED.json"
V90_OOF = (
    PROJECT_DIR / "model/v90_v89_member_verify_budget_retry/oof_proba.npy"
)
ORIGINAL_PATH = (
    DATA_DIR / "original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv"
)

SEED = 42
N_FOLDS = 5
N_INNER = 5
MODEL_SEEDS = [0, 1, 2]
EPOCHS = 30
BATCH = 4096
LR = 2e-3
WD = 1e-5
WIDTH = 512
DROP = 0.2
EMB_DROP = 0.2
PATIENCE = 4
MASK_PROB = 0.2
TE_SMOOTH = 10.0
WALL_BUDGET_SECONDS = 1800.0
MEMORY_BUDGET_BYTES = 16 * 1024**3
GATE_DELTA = 0.0001
GATE_WINS = 4
MIN_DIVERSITY_AUC = 0.9452

TARGET = "Will_Buy_EV"
POS_LABEL = "Yes"
INCOME = "Annual_Income_USD"
CAT_SPEC = [
    (INCOME, 2, 12),
    ("Daily_Commute_km", 2, 6),
    ("Age", 1, 4),
    ("Charging_Stations_Near_Home", 1, 4),
    ("Charging_Stations_Near_Work", 1, 4),
    ("Number_of_Cars_Owned", 1, 2),
    ("Environmental_Concern_Level", 1, 3),
    ("Subsidy_Available", 1, 2),
    ("Range_Anxiety_Level", 1, 2),
    ("Home_Charging_Possible", 1, 2),
    ("City_Type", 1, 2),
    ("Current_Car_Type", 1, 2),
    ("Gender", 1, 2),
]
NUM_COLS = [
    INCOME,
    "Daily_Commute_km",
    "Age",
    "Environmental_Concern_Level",
    "Charging_Stations_Near_Home",
    "Charging_Stations_Near_Work",
    "Number_of_Cars_Owned",
]
TE_KEYS = {
    "te_inc": [INCOME],
    "te_inc_bin100": ["_inc_bin100"],
    "te_inc_subsidy": [INCOME, "Subsidy_Available"],
    "te_inc_env": [INCOME, "Environmental_Concern_Level"],
    "te_commute": ["Daily_Commute_km"],
    "te_age": ["Age"],
}
TRACE_COLS = [
    "income_original_frequency",
    "income_comp_over_original_lift",
    "income_original_novel",
]


class Net(nn.Module):
    def __init__(self, vocab_dims: list[tuple[int, int]], n_num: int):
        super().__init__()
        self.embs = nn.ModuleList([nn.Embedding(v, d) for v, d in vocab_dims])
        self.emb_drop = nn.Dropout(EMB_DROP)
        in_dim = sum(d for _, d in vocab_dims) + n_num
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, WIDTH),
            nn.SiLU(),
            nn.Dropout(DROP),
            nn.Linear(WIDTH, WIDTH // 2),
            nn.SiLU(),
            nn.Dropout(DROP),
            nn.Linear(WIDTH // 2, WIDTH // 4),
            nn.SiLU(),
            nn.Dropout(DROP / 2),
            nn.Linear(WIDTH // 4, 1),
        )

    def forward(self, categorical: torch.Tensor, numeric: torch.Tensor) -> torch.Tensor:
        embedded = torch.cat(
            [embedding(categorical[:, i]) for i, embedding in enumerate(self.embs)],
            dim=1,
        )
        return self.mlp(torch.cat([self.emb_drop(embedded), numeric], dim=1)).squeeze(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def key_series(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    parts: list[pd.Series] = []
    for column in columns:
        if column == "_inc_bin100":
            parts.append((frame[INCOME] // 100).astype(np.int64).astype(str))
        else:
            parts.append(frame[column].astype(str))
    return pd.Series(["|".join(values) for values in zip(*parts)], index=frame.index)


def smoothed_te(
    key_fit: pd.Series,
    y_fit: np.ndarray,
    key_apply: pd.Series,
    prior: float,
) -> np.ndarray:
    stats = pd.DataFrame(
        {"key": key_fit.to_numpy(), "target": y_fit}
    ).groupby("key")["target"].agg(["sum", "count"])
    sums = key_apply.map(stats["sum"]).fillna(0.0).to_numpy(np.float64)
    counts = key_apply.map(stats["count"]).fillna(0.0).to_numpy(np.float64)
    return (sums + prior * TE_SMOOTH) / (counts + TE_SMOOTH)


def strict_fold_target_encoding(
    key_fit: pd.Series,
    y_fit: np.ndarray,
    key_valid: pd.Series,
    inner_splits: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray]:
    """inner-hold prior/count/sum 只来自对应 inner-train。"""
    key_fit = key_fit.reset_index(drop=True)
    y_fit = np.asarray(y_fit, dtype=np.int8)
    encoded_fit = np.full(len(key_fit), np.nan, dtype=np.float64)
    coverage = np.zeros(len(key_fit), dtype=np.int8)
    for inner_fit, inner_hold in inner_splits:
        inner_prior = float(y_fit[inner_fit].mean())
        encoded_fit[inner_hold] = smoothed_te(
            key_fit.iloc[inner_fit],
            y_fit[inner_fit],
            key_fit.iloc[inner_hold],
            inner_prior,
        )
        coverage[inner_hold] += 1
    if not np.all(coverage == 1) or not np.isfinite(encoded_fit).all():
        raise ValueError("strict inner OOF coverage invalid")
    outer_prior = float(y_fit.mean())
    encoded_valid = smoothed_te(key_fit, y_fit, key_valid, outer_prior)
    return encoded_fit, encoded_valid


def logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 1e-4, 1.0 - 1e-4)
    return np.log(clipped / (1.0 - clipped))


def build_income_trace(
    train: pd.DataFrame, test: pd.DataFrame, original: pd.DataFrame
) -> pd.DataFrame:
    competition = pd.concat([train[INCOME], test[INCOME]], ignore_index=True)
    comp_frequency = competition.value_counts(normalize=True)
    original_frequency = original[INCOME].value_counts(normalize=True)
    comp = train[INCOME].map(comp_frequency).to_numpy(np.float64)
    orig = train[INCOME].map(original_frequency).fillna(0.0).to_numpy(np.float64)
    lift = np.divide(comp, orig, out=np.zeros_like(comp), where=orig > 0.0)
    block = pd.DataFrame(
        {
            TRACE_COLS[0]: orig,
            TRACE_COLS[1]: lift,
            TRACE_COLS[2]: (orig == 0.0).astype(np.float64),
        }
    )
    if not np.isfinite(block.to_numpy()).all():
        raise ValueError("income trace contains NaN/Inf")
    return block


@torch.inference_mode()
def predict(
    model: Net,
    categorical: torch.Tensor,
    numeric: torch.Tensor,
) -> np.ndarray:
    model.eval()
    outputs: list[np.ndarray] = []
    for start in range(0, len(categorical), 65_536):
        logits = model(
            categorical[start : start + 65_536],
            numeric[start : start + 65_536],
        )
        outputs.append(torch.sigmoid(logits).float().cpu().numpy())
    return np.concatenate(outputs)


def fit_arm(
    *,
    arm: str,
    fold: int,
    vocab: list[tuple[int, int]],
    categorical_fit: torch.Tensor,
    numeric_fit: torch.Tensor,
    target_fit: torch.Tensor,
    categorical_valid: torch.Tensor,
    numeric_valid: torch.Tensor,
    y_valid: np.ndarray,
    mask_probability: float,
) -> tuple[np.ndarray, list[int]]:
    fold_prediction = np.zeros(len(y_valid), dtype=np.float64)
    best_epochs: list[int] = []
    loss_function = nn.BCEWithLogitsLoss()
    n_raw = len(NUM_COLS)
    flag_start = numeric_fit.shape[1] - n_raw

    for model_seed in MODEL_SEEDS:
        frozen_seed = SEED + fold + 1000 * model_seed
        torch.manual_seed(frozen_seed)
        order_rng = np.random.default_rng(frozen_seed + 10_000)
        mask_rng = np.random.default_rng(frozen_seed + 20_000)
        model = Net(vocab, numeric_fit.shape[1]).to(numeric_fit.device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="max", factor=0.5, patience=1
        )
        best_auc = -np.inf
        best_epoch = 0
        bad_epochs = 0
        best_state: dict[str, torch.Tensor] | None = None
        best_prediction: np.ndarray | None = None
        for epoch in range(1, EPOCHS + 1):
            model.train()
            # 排序和 corruption 使用彼此独立的 CPU RNG；三臂共享相同 batch
            # 顺序，且 corruption 不消耗控制 dropout 的 torch RNG。
            order = torch.tensor(
                order_rng.permutation(len(categorical_fit)),
                device=numeric_fit.device,
            )
            for batch_indices in order.split(BATCH):
                batch_numeric = numeric_fit[batch_indices]
                if mask_probability > 0.0:
                    batch_numeric = batch_numeric.clone()
                    mask = torch.tensor(
                        mask_rng.random((len(batch_indices), n_raw))
                        < mask_probability,
                        device=numeric_fit.device,
                    )
                    batch_numeric[:, :n_raw] *= (~mask).to(batch_numeric.dtype)
                    batch_numeric[:, flag_start:] = mask.to(batch_numeric.dtype)
                optimizer.zero_grad(set_to_none=True)
                loss = loss_function(
                    model(categorical_fit[batch_indices], batch_numeric),
                    target_fit[batch_indices],
                )
                loss.backward()
                optimizer.step()
            valid_prediction = predict(model, categorical_valid, numeric_valid)
            auc = float(roc_auc_score(y_valid, valid_prediction))
            scheduler.step(auc)
            if auc > best_auc:
                best_auc = auc
                best_epoch = epoch
                bad_epochs = 0
                best_state = copy.deepcopy(model.state_dict())
                best_prediction = valid_prediction
            else:
                bad_epochs += 1
                if bad_epochs >= PATIENCE:
                    break
        if best_state is None or best_prediction is None:
            raise RuntimeError(f"{arm} fold {fold} produced no checkpoint")
        fold_prediction += best_prediction / len(MODEL_SEEDS)
        best_epochs.append(best_epoch)
        del model, optimizer, scheduler, best_state, best_prediction
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    return fold_prediction, best_epochs


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temp, path)


def run() -> dict[str, Any]:
    if not torch.backends.mps.is_available():
        raise RuntimeError("this frozen diagnostic requires Apple MPS")
    try:
        with START_MARKER.open("x", encoding="utf-8") as handle:
            json.dump(
                {"status": "RUN_STARTED_ONE_SHOT", "pid": os.getpid()},
                handle,
                ensure_ascii=False,
                indent=2,
            )
    except FileExistsError as error:
        raise RuntimeError("one-shot run marker already exists; refusing rerun") from error

    started = time.monotonic()
    script_sha = sha256_file(Path(__file__))
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    original = pd.read_csv(ORIGINAL_PATH)
    y = train[TARGET].eq(POS_LABEL).to_numpy(np.int8)
    trace = build_income_trace(train, test, original)
    device = torch.device("mps")

    categorical_arrays: list[np.ndarray] = []
    vocab: list[tuple[int, int]] = []
    for column, min_count, embedding_dim in CAT_SPEC:
        all_values = pd.concat([train[column], test[column]]).astype(str)
        counts = all_values.value_counts()
        mapping = {
            value: index + 1
            for index, value in enumerate(counts[counts >= min_count].index)
        }
        categorical_arrays.append(
            train[column].astype(str).map(mapping).fillna(0).to_numpy(np.int64)
        )
        vocab.append((len(mapping) + 1, embedding_dim))
    categorical = np.stack(categorical_arrays, axis=1)
    raw_numeric = train[NUM_COLS].to_numpy(np.float64)
    raw_numeric[:, 0] = np.log(raw_numeric[:, 0])
    keys = {name: key_series(train, columns) for name, columns in TE_KEYS.items()}

    arm_oof = {
        "strict_baseline": np.full(len(train), np.nan, dtype=np.float64),
        "strict_plus_trace": np.full(len(train), np.nan, dtype=np.float64),
        "strict_plus_trace_mask02": np.full(len(train), np.nan, dtype=np.float64),
    }
    fold_rows: list[dict[str, Any]] = []
    checks = [resource_guard(started, "AFTER_DATA_PREP")]
    folds = list(
        StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(
            categorical, y
        )
    )

    for fold, (fit_idx, valid_idx) in enumerate(folds, start=1):
        fold_started = time.monotonic()
        inner = list(
            StratifiedKFold(N_INNER, shuffle=True, random_state=SEED + fold).split(
                np.zeros(len(fit_idx)), y[fit_idx]
            )
        )
        raw_mean = raw_numeric[fit_idx].mean(axis=0)
        raw_std = raw_numeric[fit_idx].std(axis=0) + 1e-6
        fit_raw = ((raw_numeric[fit_idx] - raw_mean) / raw_std).astype(np.float32)
        valid_raw = ((raw_numeric[valid_idx] - raw_mean) / raw_std).astype(np.float32)

        fit_te = np.zeros((len(fit_idx), len(TE_KEYS)), dtype=np.float32)
        valid_te = np.zeros((len(valid_idx), len(TE_KEYS)), dtype=np.float32)
        for column_index, name in enumerate(TE_KEYS):
            encoded_fit, encoded_valid = strict_fold_target_encoding(
                keys[name].iloc[fit_idx],
                y[fit_idx],
                keys[name].iloc[valid_idx],
                inner,
            )
            fit_logit = logit(encoded_fit)
            valid_logit = logit(encoded_valid)
            center = fit_logit.mean()
            scale = fit_logit.std() + 1e-6
            fit_te[:, column_index] = (fit_logit - center) / scale
            valid_te[:, column_index] = (valid_logit - center) / scale

        trace_mean = trace.iloc[fit_idx].to_numpy(np.float64).mean(axis=0)
        trace_std = trace.iloc[fit_idx].to_numpy(np.float64).std(axis=0) + 1e-6
        fit_trace = (
            (trace.iloc[fit_idx].to_numpy(np.float64) - trace_mean) / trace_std
        ).astype(np.float32)
        valid_trace = (
            (trace.iloc[valid_idx].to_numpy(np.float64) - trace_mean) / trace_std
        ).astype(np.float32)
        zero_trace_fit = np.zeros_like(fit_trace)
        zero_trace_valid = np.zeros_like(valid_trace)
        zero_flags_fit = np.zeros((len(fit_idx), len(NUM_COLS)), dtype=np.float32)
        zero_flags_valid = np.zeros((len(valid_idx), len(NUM_COLS)), dtype=np.float32)

        numeric_fit = {
            "strict_baseline": np.column_stack(
                [fit_raw, fit_te, zero_trace_fit, zero_flags_fit]
            ).astype(np.float32),
            "strict_plus_trace": np.column_stack(
                [fit_raw, fit_te, fit_trace, zero_flags_fit]
            ).astype(np.float32),
            "strict_plus_trace_mask02": np.column_stack(
                [fit_raw, fit_te, fit_trace, zero_flags_fit]
            ).astype(np.float32),
        }
        numeric_valid = {
            "strict_baseline": np.column_stack(
                [valid_raw, valid_te, zero_trace_valid, zero_flags_valid]
            ).astype(np.float32),
            "strict_plus_trace": np.column_stack(
                [valid_raw, valid_te, valid_trace, zero_flags_valid]
            ).astype(np.float32),
            "strict_plus_trace_mask02": np.column_stack(
                [valid_raw, valid_te, valid_trace, zero_flags_valid]
            ).astype(np.float32),
        }
        categorical_fit = torch.tensor(categorical[fit_idx], device=device)
        categorical_valid = torch.tensor(categorical[valid_idx], device=device)
        target_fit = torch.tensor(y[fit_idx].astype(np.float32), device=device)
        row: dict[str, Any] = {"fold": fold, "valid_rows": len(valid_idx)}

        for arm in arm_oof:
            arm_prediction, best_epochs = fit_arm(
                arm=arm,
                fold=fold,
                vocab=vocab,
                categorical_fit=categorical_fit,
                numeric_fit=torch.tensor(numeric_fit[arm], device=device),
                target_fit=target_fit,
                categorical_valid=categorical_valid,
                numeric_valid=torch.tensor(numeric_valid[arm], device=device),
                y_valid=y[valid_idx],
                mask_probability=MASK_PROB if arm.endswith("mask02") else 0.0,
            )
            arm_oof[arm][valid_idx] = arm_prediction
            row[f"{arm}_auc"] = float(roc_auc_score(y[valid_idx], arm_prediction))
            row[f"{arm}_best_epochs"] = best_epochs
            checks.append(resource_guard(started, f"FOLD_{fold}_{arm}_END"))
        row["trace_delta"] = row["strict_plus_trace_auc"] - row["strict_baseline_auc"]
        row["mask_delta"] = (
            row["strict_plus_trace_mask02_auc"] - row["strict_plus_trace_auc"]
        )
        row["elapsed_seconds"] = float(time.monotonic() - fold_started)
        fold_rows.append(row)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
        del categorical_fit, categorical_valid, target_fit, numeric_fit, numeric_valid
        torch.mps.empty_cache()

    if any(not np.isfinite(values).all() for values in arm_oof.values()):
        raise RuntimeError("incomplete OOF")
    auc = {name: float(roc_auc_score(y, values)) for name, values in arm_oof.items()}
    trace_delta = auc["strict_plus_trace"] - auc["strict_baseline"]
    mask_delta = auc["strict_plus_trace_mask02"] - auc["strict_plus_trace"]
    trace_wins = sum(row["trace_delta"] > 0.0 for row in fold_rows)
    mask_wins = sum(row["mask_delta"] > 0.0 for row in fold_rows)
    v90 = np.load(V90_OOF, allow_pickle=False)
    correlations = {
        name: float(spearmanr(values, v90).statistic)
        for name, values in arm_oof.items()
    }
    trace_go = (
        trace_delta >= GATE_DELTA
        and trace_wins >= GATE_WINS
        and auc["strict_plus_trace"] >= MIN_DIVERSITY_AUC
    )
    mask_go = mask_delta >= GATE_DELTA and mask_wins >= GATE_WINS
    checks.append(resource_guard(started, "COMPLETE"))
    payload = {
        "schema_version": 1,
        "status": "COMPLETE",
        "experiment_id": "TEMP_STRICT_MLP_TRACE_AND_MASK_AB_SEED42",
        "counts_toward_c01": False,
        "public_sources": {
            "trace_discussion_id": 739354,
            "trace_message_sha256": "e2ac52098bc226c33241dbea3597650a562d2582d42e1b0f7e57372415bb41fc",
            "mask_notebook_ref": "talhatursun/s6e9-feature-corruption-augmentation-tabular-nn",
            "mask_notebook_sha256": "aa901509597ca45e061c7cc40e6f6f2610d52933c1e392f41161adec8227d0e5",
            "public_predictions_used": False,
            "leaderboard_used": False,
        },
        "historical_reason_to_reopen_mlp": "community reports about +0.006 MLP gain after spike/value features; v78 lacked original-frequency trace and its inner-hold smoothing prior used full outer-fit mean",
        "protocol": {
            "outer_folds": N_FOLDS,
            "outer_seed": SEED,
            "inner_folds": N_INNER,
            "model_seeds": MODEL_SEEDS,
            "same_input_width_all_arms": True,
            "strict_baseline": "raw numeric + six repaired nested TE + three zero placeholders + seven zero flags",
            "trace_arm": "baseline with the three placeholders replaced by income frequency trace",
            "mask_arm": "trace arm with training-only mask_prob=0.2 on seven raw numeric values and companion flags",
            "test_predictions_generated": False,
            "oof_arrays_saved": False,
            "submission_generated": False,
            "go_gate": {"minimum_delta": GATE_DELTA, "minimum_positive_folds": GATE_WINS, "minimum_candidate_auc": MIN_DIVERSITY_AUC},
        },
        "source_sha256": {
            "probe.py": script_sha,
            "original_csv": sha256_file(ORIGINAL_PATH),
            "v90_oof": sha256_file(V90_OOF),
        },
        "folds": fold_rows,
        "aggregate": {
            "auc": auc,
            "trace_delta": trace_delta,
            "trace_positive_folds": trace_wins,
            "trace_decision": "FORMAL_CANDIDATE_GO" if trace_go else "NO_GO",
            "mask_delta": mask_delta,
            "mask_positive_folds": mask_wins,
            "mask_decision": "FORMAL_CANDIDATE_GO" if mask_go else "NO_GO",
            "spearman_vs_v90": correlations,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "torch": torch.__version__,
            "device": str(device),
        },
        "resource_checks": checks,
        "elapsed_seconds": checks[-1]["elapsed_seconds"],
        "peak_rss_bytes": checks[-1]["peak_rss_bytes"],
    }
    write_json(EVIDENCE_PATH, payload)
    print(json.dumps(payload["aggregate"], ensure_ascii=False, sort_keys=True))
    return payload


def audit() -> dict[str, Any]:
    key = pd.Series(["a", "a", "b", "b", "c", "c"])
    y = np.asarray([0, 1, 0, 1, 0, 1], dtype=np.int8)
    splits = list(StratifiedKFold(3, shuffle=True, random_state=42).split(key, y))
    fit, valid = strict_fold_target_encoding(key, y, pd.Series(["a", "z"]), splits)
    return {
        "status": "AUDIT_OK_NO_TRAINING",
        "strict_te_finite": bool(np.isfinite(fit).all() and np.isfinite(valid).all()),
        "same_input_width_formula": len(NUM_COLS) + len(TE_KEYS) + len(TRACE_COLS) + len(NUM_COLS),
        "mask_probability": MASK_PROB,
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
