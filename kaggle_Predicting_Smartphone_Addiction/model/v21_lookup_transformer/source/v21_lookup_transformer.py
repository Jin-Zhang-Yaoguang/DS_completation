#!/usr/bin/env python3
"""V21 candidate: fold-aligned Lookup-Transformer single model.

This is a local, single-model adaptation of Tamerlan Omralinov's public
``s6e8-lookup-transformer-insights-lb-0-97041`` notebook.  It deliberately
re-trains from the official competition CSV files and never consumes public
OOF, test predictions, or submission files.

Production contract:

* official ``train.csv`` row order is preserved;
* ``StratifiedKFold(5, shuffle=True, random_state=42)``;
* exact-value lookup ids and label-free transforms are fitted on train+test;
* one raw OOF score is produced per official training row;
* each completed fold is atomically checkpointed under a strict run signature;
* fold ids, raw/rank scores, probabilities, a ranked submission, and an audit
  JSON are finalized only after all five folds finish.

Use ``--smoke-test`` for a small one-fold integration test.  Smoke mode is not
an experiment and does not emit production OOF/submission artifacts.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import platform
import random
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd
import scipy
import sklearn
import torch
import torch.nn as nn
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import QuantileTransformer


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "artifacts"

TARGET = "addicted_label"
ID_COL = "id"
SEED = 42
N_FOLDS = 5
EXPECTED_FEATURES = [
    "age",
    "daily_screen_time_hours",
    "social_media_hours",
    "gaming_hours",
    "work_study_hours",
    "sleep_hours",
    "notifications_per_day",
    "app_opens_per_day",
    "weekend_screen_time",
    "gender",
    "stress_level",
    "academic_work_impact",
]
COMPONENTS = ["social_media_hours", "gaming_hours", "work_study_hours"]
SOURCE_NOTEBOOK = (
    "https://www.kaggle.com/code/tamerlanomralinov/"
    "s6e8-lookup-transformer-insights-lb-0-97041"
)
SOURCE_NOTEBOOK_SHA256 = (
    "a3b1d7468389bf9d53a7c49da1ba002636b48dcfcbb5deaa7af60c635b0b5806"
)


@dataclass(frozen=True)
class ModelConfig:
    d_model: int = 128
    plr_frequencies: int = 24
    layers: int = 4
    heads: int = 8
    dropout: float = 0.10
    epochs: int = 32
    batch_size: int = 2048
    predict_batch_size: int = 16384
    learning_rate: float = 2e-3
    augmentation_rate: float = 0.10
    ema_decay: float = 0.999
    eval_start_epoch: int = 5
    eval_every: int = 2
    early_stopping_checks: int = 5


@dataclass
class PreparedData:
    train: pd.DataFrame
    test: pd.DataFrame
    sample: pd.DataFrame
    features: list[str]
    y: np.ndarray
    ids: torch.Tensor
    raw_numeric: torch.Tensor
    raw_missing: torch.Tensor
    derived_numeric: torch.Tensor
    derived_missing: torch.Tensor
    offsets: np.ndarray
    vocab_sizes: list[int]
    derived_columns: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--device",
        choices=("auto", "cuda", "mps", "cpu"),
        default="auto",
        help="auto prefers CUDA, then Apple MPS, then CPU",
    )
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument(
        "--smoke-full-architecture",
        action="store_true",
        help="keep d=128/k=24/4 layers during smoke test",
    )
    parser.add_argument("--smoke-train-rows", type=int, default=4096)
    parser.add_argument("--smoke-test-rows", type=int, default=1024)
    parser.add_argument("--d-model", type=int, default=128)
    parser.add_argument("--plr-frequencies", type=int, default=24)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--heads", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.10)
    parser.add_argument("--epochs", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--predict-batch-size", type=int, default=16384)
    parser.add_argument("--learning-rate", type=float, default=2e-3)
    parser.add_argument("--augmentation-rate", type=float, default=0.10)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_values(values: np.ndarray) -> str:
    data = np.ascontiguousarray(values)
    return hashlib.sha256(data.view(np.uint8)).hexdigest()


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}"
    )
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_save_numpy(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}"
    )
    try:
        with temporary.open("wb") as handle:
            np.save(handle, values, allow_pickle=False)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def percentile_rank(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return rankdata(values, method="average") / len(values)


def seed_everything(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        if torch.cuda.is_available():
            requested = "cuda"
        elif torch.backends.mps.is_available():
            requested = "mps"
        else:
            requested = "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("指定了 CUDA，但 torch.cuda.is_available() 为 False")
    if requested == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("指定了 MPS，但 torch.backends.mps.is_available() 为 False")
    return torch.device(requested)


def autocast_context(device: torch.device):
    """Use AMP only on CUDA; MPS stays in float32 for reliability."""

    if device.type != "cuda":
        return contextlib.nullcontext()
    amp_dtype = (
        torch.bfloat16
        if torch.cuda.is_bf16_supported()
        else torch.float16
    )
    return torch.autocast(device_type="cuda", dtype=amp_dtype)


def make_grad_scaler(device: torch.device):
    enabled = (
        device.type == "cuda"
        and not torch.cuda.is_bf16_supported()
    )
    if not enabled:
        return None
    try:
        return torch.amp.GradScaler("cuda", enabled=True)
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler(enabled=True)


def empty_device_cache(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.empty_cache()
    elif device.type == "mps" and hasattr(torch, "mps"):
        torch.mps.empty_cache()


def device_memory_snapshot(device: torch.device) -> dict[str, int | None]:
    if device.type == "cuda":
        return {
            "allocated_bytes": int(torch.cuda.memory_allocated(device)),
            "reserved_bytes": int(torch.cuda.memory_reserved(device)),
            "max_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        }
    if device.type == "mps" and hasattr(torch, "mps"):
        current = getattr(torch.mps, "current_allocated_memory", lambda: 0)()
        driver = getattr(torch.mps, "driver_allocated_memory", lambda: 0)()
        return {
            "allocated_bytes": int(current),
            "reserved_bytes": int(driver),
            "max_allocated_bytes": None,
        }
    return {
        "allocated_bytes": None,
        "reserved_bytes": None,
        "max_allocated_bytes": None,
    }


def load_frames(
    data_dir: Path,
    smoke_test: bool,
    smoke_train_rows: int,
    smoke_test_rows: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_path = data_dir / "train.csv"
    test_path = data_dir / "test.csv"
    sample_path = data_dir / "sample_submission.csv"
    for path in (train_path, test_path, sample_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    # No sort, merge, index reset, or id-based reordering is allowed here.
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    sample = pd.read_csv(sample_path)
    if smoke_test:
        train = train.iloc[: min(smoke_train_rows, len(train))].copy()
        test = test.iloc[: min(smoke_test_rows, len(test))].copy()
        sample = sample.iloc[: len(test)].copy()

    expected_train = [ID_COL, *EXPECTED_FEATURES, TARGET]
    expected_test = [ID_COL, *EXPECTED_FEATURES]
    if train.columns.tolist() != expected_train:
        raise ValueError(f"train 字段/顺序不符合官方契约: {train.columns.tolist()}")
    if test.columns.tolist() != expected_test:
        raise ValueError(f"test 字段/顺序不符合官方契约: {test.columns.tolist()}")
    if sample.columns.tolist() != [ID_COL, TARGET]:
        raise ValueError("sample_submission.csv 字段不符合比赛要求")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission.csv 与 test.csv 的 id 顺序不一致")
    if not train[ID_COL].is_unique or not test[ID_COL].is_unique:
        raise ValueError("train/test id 必须唯一")
    return train, test, sample


def rank_gauss(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    values = np.zeros((len(frame), frame.shape[1]), dtype=np.float32)
    missing = np.zeros_like(values)
    for col_idx, column in enumerate(frame.columns):
        raw = frame[column].to_numpy(dtype=np.float64)
        observed = ~np.isnan(raw)
        count = int(observed.sum())
        if count > 10:
            transformer = QuantileTransformer(
                n_quantiles=min(1000, count),
                output_distribution="normal",
                subsample=min(400000, count),
                random_state=0,
            )
            values[observed, col_idx] = transformer.fit_transform(
                raw[observed].reshape(-1, 1)
            ).ravel().astype(np.float32)
        missing[~observed, col_idx] = 1.0
    return values, missing


def prepare_data(
    train: pd.DataFrame,
    test: pd.DataFrame,
    sample: pd.DataFrame,
) -> PreparedData:
    features = [c for c in test.columns if c != ID_COL]
    y = train[TARGET].to_numpy(dtype=np.float32)
    both = pd.concat([train[features], test[features]], ignore_index=True)

    exact_ids: list[np.ndarray] = []
    vocab_sizes: list[int] = []
    for column in features:
        levels = both[column].astype(str).where(both[column].notna(), "__NA__")
        categories = sorted(v for v in levels.unique() if v != "__NA__")
        mapping = {value: idx + 1 for idx, value in enumerate(categories)}
        mapping["__NA__"] = 0
        exact_ids.append(levels.map(mapping).to_numpy(dtype=np.int64))
        vocab_sizes.append(len(categories) + 1)
    ids = np.stack(exact_ids, axis=1)
    offsets = np.concatenate(
        [np.array([0], dtype=np.int64), np.cumsum(vocab_sizes)[:-1]]
    ).astype(np.int64)

    # Follow the public implementation exactly: pandas sum skips missing
    # components, so an unobserved component contributes zero to sgw.
    component_sum = both[COMPONENTS].sum(axis=1)
    daily = both["daily_screen_time_hours"]
    weekend = both["weekend_screen_time"]
    derived = pd.DataFrame(
        {
            "other_screen": daily - component_sum,
            "sgw": component_sum,
            "other_frac": (daily - component_sum) / daily.clip(lower=0.1),
            "wk_minus_sgw": weekend - component_sum,
            "wk_other": weekend - (daily - component_sum),
            "sgw_frac": component_sum / daily.clip(lower=0.1),
        }
    )

    raw_numeric = pd.DataFrame(
        {
            column: (
                both[column]
                if both[column].dtype != object
                else np.nan
            )
            for column in features
        }
    )
    raw_values, raw_missing = rank_gauss(raw_numeric)
    derived_values, derived_missing = rank_gauss(derived)

    return PreparedData(
        train=train,
        test=test,
        sample=sample,
        features=features,
        y=y,
        ids=torch.from_numpy(ids + offsets[None, :]),
        raw_numeric=torch.from_numpy(raw_values),
        raw_missing=torch.from_numpy(raw_missing),
        derived_numeric=torch.from_numpy(derived_values),
        derived_missing=torch.from_numpy(derived_missing),
        offsets=offsets,
        vocab_sizes=vocab_sizes,
        derived_columns=derived.columns.tolist(),
    )


class PLR(nn.Module):
    """Periodic-Linear numeric embedding with learned feature frequencies."""

    def __init__(self, n_features: int, frequencies: int, d_model: int, sigma: float = 0.5):
        super().__init__()
        self.frequencies = nn.Parameter(
            torch.randn(n_features, frequencies) * sigma
        )
        self.weight = nn.Parameter(
            torch.randn(n_features, 2 * frequencies, d_model)
            / math.sqrt(2 * frequencies)
        )
        self.bias = nn.Parameter(torch.zeros(n_features, d_model))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        periodic = (
            2
            * math.pi
            * values.unsqueeze(-1)
            * self.frequencies.unsqueeze(0)
        )
        periodic = torch.cat(
            [torch.sin(periodic), torch.cos(periodic)], dim=-1
        )
        return (
            torch.einsum("bfk,fkd->bfd", periodic, self.weight)
            + self.bias
        )


class LookupTransformer(nn.Module):
    def __init__(
        self,
        total_vocab: int,
        n_categorical: int,
        n_derived: int,
        config: ModelConfig,
    ) -> None:
        super().__init__()
        d_model = config.d_model
        self.embedding = nn.Embedding(total_vocab, d_model)
        nn.init.normal_(self.embedding.weight, std=0.02)
        self.raw_plr = PLR(
            n_categorical,
            config.plr_frequencies,
            d_model,
        )
        self.derived_plr = PLR(
            n_derived,
            config.plr_frequencies,
            d_model,
        )
        token_count = 1 + n_categorical + n_derived
        self.cls = nn.Parameter(torch.zeros(1, 1, d_model))
        self.position = nn.Parameter(
            torch.randn(1, token_count, d_model) * 0.02
        )
        self.embedding_dropout = nn.Dropout(config.dropout)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=config.heads,
            dim_feedforward=d_model * 2,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.layers,
            enable_nested_tensor=False,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(d_model, 1),
        )

    def forward(
        self,
        exact_ids: torch.Tensor,
        raw_numeric: torch.Tensor,
        raw_missing: torch.Tensor,
        derived_numeric: torch.Tensor,
        derived_missing: torch.Tensor,
    ) -> torch.Tensor:
        batch_size = exact_ids.shape[0]
        raw_tokens = self.embedding(exact_ids) + self.raw_plr(
            raw_numeric
        ) * (1 - raw_missing).unsqueeze(-1)
        derived_tokens = self.derived_plr(derived_numeric) * (
            1 - derived_missing
        ).unsqueeze(-1)
        tokens = torch.cat(
            [
                self.cls.expand(batch_size, -1, -1),
                raw_tokens,
                derived_tokens,
            ],
            dim=1,
        )
        tokens = self.embedding_dropout(tokens + self.position)
        encoded = self.transformer(tokens)
        return self.head(encoded[:, 0]).squeeze(-1)


def batched_predict(
    model: LookupTransformer,
    tensors: tuple[torch.Tensor, ...],
    device: torch.device,
    chunk_size: int,
) -> np.ndarray:
    model.eval()
    outputs: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, len(tensors[0]), chunk_size):
            batch = tuple(
                value[start : start + chunk_size].to(device)
                for value in tensors
            )
            with autocast_context(device):
                logits = model(*batch)
            outputs.append(logits.float().cpu())
    return torch.cat(outputs).numpy()


def index_tensors(data: PreparedData, indices: np.ndarray) -> tuple[torch.Tensor, ...]:
    return (
        data.ids[indices],
        data.raw_numeric[indices],
        data.raw_missing[indices],
        data.derived_numeric[indices],
        data.derived_missing[indices],
    )


def iter_batches(
    indices: torch.Tensor,
    batch_size: int,
) -> Iterator[torch.Tensor]:
    for start in range(0, len(indices), batch_size):
        yield indices[start : start + batch_size]


def train_fold(
    data: PreparedData,
    train_indices: np.ndarray,
    valid_indices: np.ndarray,
    fold: int,
    config: ModelConfig,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    fold_started = time.time()
    fold_seed = SEED + fold
    seed_everything(fold_seed)
    generator = torch.Generator(device="cpu").manual_seed(fold_seed)

    total_vocab = int(sum(data.vocab_sizes))
    model = LookupTransformer(
        total_vocab=total_vocab,
        n_categorical=len(data.features),
        n_derived=len(data.derived_columns),
        config=config,
    ).to(device)
    embedding_parameters = [
        parameter
        for name, parameter in model.named_parameters()
        if name.startswith("embedding")
    ]
    other_parameters = [
        parameter
        for name, parameter in model.named_parameters()
        if not name.startswith("embedding")
    ]
    optimizer = torch.optim.AdamW(
        [
            {"params": other_parameters, "weight_decay": 1e-5},
            {"params": embedding_parameters, "weight_decay": 3e-4},
        ],
        lr=config.learning_rate,
    )
    steps_per_epoch = math.ceil(len(train_indices) / config.batch_size)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=config.learning_rate,
        total_steps=steps_per_epoch * config.epochs + 10,
        pct_start=0.15,
    )
    scaler = make_grad_scaler(device)
    loss_function = nn.BCEWithLogitsLoss()
    parameters = list(model.parameters())
    ema = [parameter.detach().clone() for parameter in parameters]

    train_tensors = tuple(
        tensor[train_indices].to(device)
        for tensor in (
            data.ids,
            data.raw_numeric,
            data.raw_missing,
            data.derived_numeric,
            data.derived_missing,
        )
    )
    train_y = torch.from_numpy(data.y[train_indices]).to(device)
    valid_tensors = index_tensors(data, valid_indices)
    test_slice = np.arange(len(data.train), len(data.train) + len(data.test))
    test_tensors = index_tensors(data, test_slice)
    feature_offsets = torch.from_numpy(data.offsets).to(device)

    best_auc = -np.inf
    best_ema: list[torch.Tensor] | None = None
    bad_checks = 0
    epoch_history: list[dict[str, float | int]] = []

    for epoch in range(config.epochs):
        model.train()
        permutation = torch.randperm(
            len(train_indices), generator=generator
        ).to(device)
        # Keep the running loss on-device.  Calling ``loss.cpu()`` for every
        # batch serializes the MPS/CUDA stream and made logging unnecessarily
        # expensive; one scalar transfer per epoch is sufficient.
        loss_sum = torch.zeros((), dtype=torch.float32, device=device)
        seen = 0
        for selection in iter_batches(permutation, config.batch_size):
            exact_ids = train_tensors[0][selection].clone()
            raw_missing = train_tensors[2][selection].clone()
            if config.augmentation_rate > 0:
                extra_missing = (
                    torch.rand(exact_ids.shape, device=device)
                    < config.augmentation_rate
                )
                exact_ids = torch.where(
                    extra_missing,
                    feature_offsets.expand_as(exact_ids),
                    exact_ids,
                )
                raw_missing = torch.maximum(
                    raw_missing,
                    extra_missing.float(),
                )

            optimizer.zero_grad(set_to_none=True)
            with autocast_context(device):
                logits = model(
                    exact_ids,
                    train_tensors[1][selection],
                    raw_missing,
                    train_tensors[3][selection],
                    train_tensors[4][selection],
                )
                loss = loss_function(logits, train_y[selection])
            if scaler is None:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(parameters, 1.0)
                optimizer.step()
            else:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(parameters, 1.0)
                scaler.step(optimizer)
                scaler.update()
            scheduler.step()

            with torch.no_grad():
                for average, parameter in zip(ema, parameters):
                    average.mul_(config.ema_decay).add_(
                        parameter.detach(),
                        alpha=1.0 - config.ema_decay,
                    )
            batch_count = len(selection)
            loss_sum.add_(loss.detach().float(), alpha=batch_count)
            seen += batch_count

        epoch_loss = float(loss_sum.cpu()) / max(seen, 1)

        should_validate = (
            epoch >= config.eval_start_epoch
            and (
                (epoch + 1) % config.eval_every == 0
                or epoch == config.epochs - 1
            )
        )
        if should_validate:
            live_weights = [
                parameter.detach().clone() for parameter in parameters
            ]
            with torch.no_grad():
                for parameter, average in zip(parameters, ema):
                    parameter.copy_(average)
            valid_score = batched_predict(
                model,
                valid_tensors,
                device,
                config.predict_batch_size,
            )
            valid_auc = float(
                roc_auc_score(data.y[valid_indices], valid_score)
            )
            if valid_auc > best_auc:
                best_auc = valid_auc
                best_ema = [average.detach().clone() for average in ema]
                bad_checks = 0
            else:
                bad_checks += 1
            with torch.no_grad():
                for parameter, live in zip(parameters, live_weights):
                    parameter.copy_(live)
            epoch_history.append(
                {
                    "epoch": epoch + 1,
                    "train_loss": epoch_loss,
                    "valid_auc": valid_auc,
                }
            )
            print(
                f"[fold {fold}] epoch={epoch + 1:02d} "
                f"loss={epoch_loss:.6f} "
                f"valid_auc={valid_auc:.6f} best={best_auc:.6f}",
                flush=True,
            )
            if bad_checks >= config.early_stopping_checks:
                break

    if best_ema is None:
        best_ema = [average.detach().clone() for average in ema]
    with torch.no_grad():
        for parameter, average in zip(parameters, best_ema):
            parameter.copy_(average)

    valid_score = batched_predict(
        model,
        valid_tensors,
        device,
        config.predict_batch_size,
    )
    test_score = batched_predict(
        model,
        test_tensors,
        device,
        config.predict_batch_size,
    )
    final_auc = float(roc_auc_score(data.y[valid_indices], valid_score))
    report = {
        "fold": fold,
        "fold_seed": fold_seed,
        "train_rows": int(len(train_indices)),
        "valid_rows": int(len(valid_indices)),
        "best_auc": final_auc,
        "epochs_completed": int(epoch_history[-1]["epoch"] if epoch_history else config.epochs),
        "epoch_history": epoch_history,
        "runtime_seconds": float(time.time() - fold_started),
        "device_memory": device_memory_snapshot(device),
    }

    del model, optimizer, scheduler, train_tensors, train_y, valid_tensors
    empty_device_cache(device)
    return valid_score, test_score, report


def production_config(args: argparse.Namespace) -> ModelConfig:
    return ModelConfig(
        d_model=args.d_model,
        plr_frequencies=args.plr_frequencies,
        layers=args.layers,
        heads=args.heads,
        dropout=args.dropout,
        epochs=args.epochs,
        batch_size=args.batch_size,
        predict_batch_size=args.predict_batch_size,
        learning_rate=args.learning_rate,
        augmentation_rate=args.augmentation_rate,
    )


def smoke_config(args: argparse.Namespace) -> ModelConfig:
    if args.smoke_full_architecture:
        return ModelConfig(
            d_model=args.d_model,
            plr_frequencies=args.plr_frequencies,
            layers=args.layers,
            heads=args.heads,
            dropout=args.dropout,
            epochs=2,
            # Keep the production batch contract in the full-architecture
            # smoke test.  The default smoke subset is small, so this still
            # executes only two optimizer steps while verifying that MPS/CUDA
            # can hold the intended 2,048-row training batch.
            batch_size=args.batch_size,
            predict_batch_size=args.predict_batch_size,
            learning_rate=args.learning_rate,
            augmentation_rate=args.augmentation_rate,
            eval_start_epoch=0,
            eval_every=1,
            early_stopping_checks=2,
        )
    return ModelConfig(
        d_model=32,
        plr_frequencies=4,
        layers=1,
        heads=4,
        dropout=0.10,
        epochs=2,
        batch_size=256,
        predict_batch_size=1024,
        learning_rate=2e-3,
        augmentation_rate=0.10,
        eval_start_epoch=0,
        eval_every=1,
        early_stopping_checks=2,
    )


def validate_config(config: ModelConfig) -> None:
    if config.d_model % config.heads != 0:
        raise ValueError("d_model 必须可以被 heads 整除")
    if min(config.d_model, config.plr_frequencies, config.layers) <= 0:
        raise ValueError("模型维度/层数必须为正数")
    if config.epochs <= 0 or config.batch_size <= 0:
        raise ValueError("epochs/batch_size 必须为正数")
    if not 0 <= config.augmentation_rate < 1:
        raise ValueError("augmentation_rate 必须位于 [0, 1)")


def environment_report(device: torch.device) -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "torch": torch.__version__,
        "device": str(device),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": torch.version.cuda,
        "mps_built": bool(torch.backends.mps.is_built()),
        "mps_available": bool(torch.backends.mps.is_available()),
        "cuda_device": (
            torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else None
        ),
    }


def build_run_signature(
    data: PreparedData,
    config: ModelConfig,
    device: torch.device,
    data_dir: Path,
    mode: str,
    folds: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[str, dict[str, object]]:
    """Bind resumable fold files to code, data, folds, runtime, and config."""

    environment = environment_report(device)
    fold_digests = [
        {
            "fold": fold,
            "train_indices_sha256": sha256_values(
                np.asarray(train_indices, dtype=np.int64)
            ),
            "valid_indices_sha256": sha256_values(
                np.asarray(valid_indices, dtype=np.int64)
            ),
            "train_rows": int(len(train_indices)),
            "valid_rows": int(len(valid_indices)),
        }
        for fold, (train_indices, valid_indices) in enumerate(folds)
    ]
    payload: dict[str, object] = {
        "signature_version": 1,
        "mode": mode,
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "source_notebook_sha256": SOURCE_NOTEBOOK_SHA256,
        "input_sha256": {
            "train.csv": sha256_file(data_dir / "train.csv"),
            "test.csv": sha256_file(data_dir / "test.csv"),
            "sample_submission.csv": sha256_file(
                data_dir / "sample_submission.csv"
            ),
        },
        "loaded_data": {
            "train_rows": int(len(data.train)),
            "test_rows": int(len(data.test)),
            "train_id_sha256": sha256_values(
                data.train[ID_COL].to_numpy()
            ),
            "test_id_sha256": sha256_values(data.test[ID_COL].to_numpy()),
            "sample_id_sha256": sha256_values(
                data.sample[ID_COL].to_numpy()
            ),
            "target_sha256": sha256_values(data.y),
            "features": data.features,
            "derived_columns": data.derived_columns,
            "vocab_sizes": data.vocab_sizes,
        },
        "folds": fold_digests,
        "config": asdict(config),
        "seed": SEED,
        "runtime": {
            key: environment[key]
            for key in (
                "python",
                "platform",
                "numpy",
                "pandas",
                "scipy",
                "scikit_learn",
                "torch",
                "device",
                "cuda_version",
            )
        },
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hashlib.sha256(canonical).hexdigest()
    return signature, payload


def initialize_checkpoint_store(
    output_dir: Path,
    run_signature: str,
    signature_payload: dict[str, object],
) -> Path:
    """Create or strictly validate the run signature before any fold reuse."""

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_root = output_dir / "fold_checkpoints"
    signature_path = output_dir / "run_signature.json"
    expected = {
        "signature_version": 1,
        "run_signature": run_signature,
        "payload": signature_payload,
    }
    if signature_path.exists():
        existing = json.loads(signature_path.read_text(encoding="utf-8"))
        if existing != expected:
            existing_signature = (
                existing.get("run_signature", "missing")
                if isinstance(existing, dict)
                else "invalid"
            )
            raise RuntimeError(
                "output-dir 已存在不兼容的 run_signature；拒绝混用折预测。"
                f" existing={existing_signature} current={run_signature}"
            )
    else:
        if checkpoint_root.exists() and any(checkpoint_root.iterdir()):
            raise RuntimeError(
                "发现没有 run_signature.json 的旧折缓存；拒绝自动恢复"
            )
        atomic_write_json(signature_path, expected)
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    return checkpoint_root


def save_fold_checkpoint(
    checkpoint_root: Path,
    run_signature: str,
    fold: int,
    valid_indices: np.ndarray,
    valid_score: np.ndarray,
    test_score: np.ndarray,
    report: dict[str, object],
) -> None:
    """Atomically publish one completed fold; marker JSON is written last."""

    fold_dir = checkpoint_root / f"fold_{fold:02d}"
    valid_indices = np.asarray(valid_indices, dtype=np.int64)
    valid_score = np.asarray(valid_score)
    test_score = np.asarray(test_score)
    if valid_score.shape != (len(valid_indices),):
        raise ValueError("fold checkpoint valid score/indices shape 不一致")
    if not np.isfinite(valid_score).all() or not np.isfinite(test_score).all():
        raise ValueError("fold checkpoint prediction 含 NaN/inf")
    if int(report.get("fold", -1)) != fold:
        raise ValueError("fold checkpoint report.fold 不一致")

    valid_indices_path = fold_dir / "valid_indices.npy"
    valid_score_path = fold_dir / "valid_score.npy"
    test_score_path = fold_dir / "test_score.npy"
    report_path = fold_dir / "report.json"
    atomic_save_numpy(valid_indices_path, valid_indices)
    atomic_save_numpy(valid_score_path, valid_score)
    atomic_save_numpy(test_score_path, test_score)
    atomic_write_json(report_path, report)
    completion = {
        "checkpoint_version": 1,
        "run_signature": run_signature,
        "fold": fold,
        "valid_rows": int(len(valid_indices)),
        "test_rows": int(len(test_score)),
        "valid_indices_sha256": sha256_values(valid_indices),
        "valid_score_sha256": sha256_values(valid_score),
        "test_score_sha256": sha256_values(test_score),
        "report_sha256": sha256_file(report_path),
    }
    atomic_write_json(fold_dir / "complete.json", completion)


def load_fold_checkpoint(
    checkpoint_root: Path,
    run_signature: str,
    fold: int,
    expected_valid_indices: np.ndarray,
    expected_test_rows: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]] | None:
    """Load only a complete, hash-valid checkpoint for the exact current run."""

    fold_dir = checkpoint_root / f"fold_{fold:02d}"
    completion_path = fold_dir / "complete.json"
    if not completion_path.exists():
        if fold_dir.exists():
            print(
                f"[fold {fold}] incomplete checkpoint ignored; retraining",
                flush=True,
            )
        return None
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    if (
        completion.get("checkpoint_version") != 1
        or completion.get("run_signature") != run_signature
        or completion.get("fold") != fold
    ):
        raise RuntimeError(f"fold {fold} checkpoint signature/version 不一致")

    valid_indices_path = fold_dir / "valid_indices.npy"
    valid_score_path = fold_dir / "valid_score.npy"
    test_score_path = fold_dir / "test_score.npy"
    report_path = fold_dir / "report.json"
    for path in (
        valid_indices_path,
        valid_score_path,
        test_score_path,
        report_path,
    ):
        if not path.is_file():
            raise RuntimeError(f"fold {fold} complete marker 存在但缺文件: {path.name}")

    valid_indices = np.load(valid_indices_path, allow_pickle=False)
    valid_score = np.load(valid_score_path, allow_pickle=False)
    test_score = np.load(test_score_path, allow_pickle=False)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_valid_indices = np.asarray(expected_valid_indices, dtype=np.int64)
    checks = {
        "valid indices": np.array_equal(valid_indices, expected_valid_indices),
        "valid score shape": valid_score.shape == (len(expected_valid_indices),),
        "test score shape": test_score.shape == (expected_test_rows,),
        "valid indices hash": sha256_values(valid_indices)
        == completion.get("valid_indices_sha256"),
        "valid score hash": sha256_values(valid_score)
        == completion.get("valid_score_sha256"),
        "test score hash": sha256_values(test_score)
        == completion.get("test_score_sha256"),
        "report hash": sha256_file(report_path)
        == completion.get("report_sha256"),
        "report fold": isinstance(report, dict)
        and report.get("fold") == fold,
        "finite scores": np.isfinite(valid_score).all()
        and np.isfinite(test_score).all(),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"fold {fold} checkpoint 校验失败: {failed}")
    print(f"[fold {fold}] resumed from verified checkpoint", flush=True)
    return valid_score, test_score, report


def load_or_train_fold(
    data: PreparedData,
    train_indices: np.ndarray,
    valid_indices: np.ndarray,
    fold: int,
    config: ModelConfig,
    device: torch.device,
    checkpoint_root: Path,
    run_signature: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], bool]:
    cached = load_fold_checkpoint(
        checkpoint_root,
        run_signature,
        fold,
        valid_indices,
        len(data.test),
    )
    if cached is not None:
        valid_score, test_score, report = cached
        return valid_score, test_score, report, True
    valid_score, test_score, report = train_fold(
        data,
        train_indices,
        valid_indices,
        fold,
        config,
        device,
    )
    save_fold_checkpoint(
        checkpoint_root,
        run_signature,
        fold,
        valid_indices,
        valid_score,
        test_score,
        report,
    )
    print(f"[fold {fold}] checkpoint committed", flush=True)
    return valid_score, test_score, report, False


def run_smoke(
    data: PreparedData,
    config: ModelConfig,
    device: torch.device,
    data_dir: Path,
    output_dir: Path,
) -> None:
    folds = list(
        StratifiedKFold(
            n_splits=2,
            shuffle=True,
            random_state=SEED,
        ).split(np.zeros(len(data.y)), data.y)
    )
    train_indices, valid_indices = folds[0]
    run_signature, signature_payload = build_run_signature(
        data,
        config,
        device,
        data_dir,
        mode="smoke",
        folds=folds,
    )
    checkpoint_root = initialize_checkpoint_store(
        output_dir,
        run_signature,
        signature_payload,
    )
    valid_score, test_score, fold_report, checkpoint_resumed = load_or_train_fold(
        data,
        train_indices,
        valid_indices,
        fold=0,
        config=config,
        device=device,
        checkpoint_root=checkpoint_root,
        run_signature=run_signature,
    )
    if valid_score.shape != (len(valid_indices),):
        raise AssertionError("smoke valid prediction shape 错误")
    if test_score.shape != (len(data.test),):
        raise AssertionError("smoke test prediction shape 错误")
    if not np.isfinite(valid_score).all() or not np.isfinite(test_score).all():
        raise AssertionError("smoke prediction 存在 NaN/inf")
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "pass",
        "mode": "smoke_only_not_an_experiment",
        "run_signature": run_signature,
        "checkpoint_resumed": checkpoint_resumed,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": {
            "train_loaded": len(data.train),
            "test_loaded": len(data.test),
            "fold_train": len(train_indices),
            "fold_valid": len(valid_indices),
        },
        "config": asdict(config),
        "environment": environment_report(device),
        "fold_report": fold_report,
        "test_score": {
            "min": float(test_score.min()),
            "max": float(test_score.max()),
            "unique": int(np.unique(test_score).size),
        },
    }
    (output_dir / "smoke_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def run_production(
    data: PreparedData,
    config: ModelConfig,
    device: torch.device,
    data_dir: Path,
    output_dir: Path,
) -> None:
    started = time.time()
    folds = list(
        StratifiedKFold(
            n_splits=N_FOLDS,
            shuffle=True,
            random_state=SEED,
        ).split(np.zeros(len(data.y)), data.y)
    )
    run_signature, signature_payload = build_run_signature(
        data,
        config,
        device,
        data_dir,
        mode="production",
        folds=folds,
    )
    checkpoint_root = initialize_checkpoint_store(
        output_dir,
        run_signature,
        signature_payload,
    )
    oof_score = np.full(len(data.train), np.nan, dtype=np.float64)
    test_score = np.zeros(len(data.test), dtype=np.float64)
    fold_id = np.full(len(data.train), -1, dtype=np.int8)
    fold_reports: list[dict[str, object]] = []
    resumed_folds: list[int] = []

    for fold, (train_indices, valid_indices) in enumerate(folds):
        valid_score, fold_test_score, report, resumed = load_or_train_fold(
            data,
            train_indices,
            valid_indices,
            fold,
            config,
            device,
            checkpoint_root,
            run_signature,
        )
        if resumed:
            resumed_folds.append(fold)
        oof_score[valid_indices] = valid_score
        test_score += fold_test_score / N_FOLDS
        fold_id[valid_indices] = fold
        fold_reports.append(report)

    if np.isnan(oof_score).any() or (fold_id < 0).any():
        raise AssertionError("OOF 未覆盖全部官方训练行")
    if not np.isfinite(oof_score).all() or not np.isfinite(test_score).all():
        raise AssertionError("OOF/test score 存在 NaN/inf")

    # Raw logits remain the primary OOF contract.  This secondary view removes
    # cross-fold logit-scale drift by percentile-ranking inside each fold.
    oof_fold_rank = np.full(len(data.train), np.nan, dtype=np.float64)
    for _, valid_indices in folds:
        oof_fold_rank[valid_indices] = percentile_rank(
            oof_score[valid_indices]
        )
    if not np.isfinite(oof_fold_rank).all():
        raise AssertionError("per-fold percentile-rank OOF 存在 NaN/inf")

    oof_probability = torch.sigmoid(
        torch.from_numpy(oof_score)
    ).numpy()
    test_probability = torch.sigmoid(
        torch.from_numpy(test_score)
    ).numpy()
    overall_auc = float(roc_auc_score(data.y, oof_score))
    fold_rank_oof_auc = float(roc_auc_score(data.y, oof_fold_rank))
    fold_auc = [
        float(roc_auc_score(data.y[valid], oof_score[valid]))
        for _, valid in folds
    ]
    ranked_test = percentile_rank(test_score)
    submission = data.sample.copy()
    submission[TARGET] = ranked_test
    if not submission[ID_COL].equals(data.test[ID_COL]):
        raise AssertionError("submission id 顺序错误")
    if not submission[TARGET].between(0, 1).all():
        raise AssertionError("submission score 越界")

    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "oof_score.npy", oof_score)
    np.save(output_dir / "test_score.npy", test_score)
    np.save(output_dir / "oof_proba.npy", oof_probability)
    np.save(output_dir / "test_proba.npy", test_probability)
    np.save(output_dir / "fold_id.npy", fold_id)
    np.save(output_dir / "oof_fold_rank.npy", oof_fold_rank)
    submission.to_csv(output_dir / "submission.csv", index=False)

    train_path = data_dir / "train.csv"
    test_path = data_dir / "test.csv"
    sample_path = data_dir / "sample_submission.csv"
    manifest = {
        "experiment": "v21_lookup_transformer_candidate",
        "status": "trained_not_submitted",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_notebook": SOURCE_NOTEBOOK,
        "source_notebook_sha256_at_review": SOURCE_NOTEBOOK_SHA256,
        "public_predictions_used": False,
        "run_signature": run_signature,
        "resume": {
            "checkpoint_version": 1,
            "resumed_folds": resumed_folds,
            "checkpoint_directory": "fold_checkpoints",
        },
        "fold_contract": {
            "n_splits": N_FOLDS,
            "shuffle": True,
            "random_state": SEED,
            "splitter_random_state": SEED,
            "training_seed_policy": "SEED + fold_index",
            "training_fold_seeds": [SEED + fold for fold in range(N_FOLDS)],
            "row_order": "official train.csv physical row order; no sort/reindex",
            "train_id_sha256": sha256_values(data.train[ID_COL].to_numpy()),
            "test_id_sha256": sha256_values(data.test[ID_COL].to_numpy()),
        },
        "config": asdict(config),
        "features": {
            "raw": data.features,
            "derived": data.derived_columns,
            "vocab_sizes": dict(zip(data.features, data.vocab_sizes)),
            "total_vocab": int(sum(data.vocab_sizes)),
            "label_free_train_plus_test_preprocessing": [
                "exact-value vocabulary",
                "rank-gauss raw numerics",
                "rank-gauss budget features",
            ],
        },
        "validation": {
            "oof_auc": overall_auc,
            "oof_primary_metric_input": "raw cross-fold logits",
            "oof_fold_rank_auc": fold_rank_oof_auc,
            "oof_fold_rank_purpose": (
                "secondary diagnostic robust to cross-fold logit-scale drift"
            ),
            "fold_auc": fold_auc,
            "fold_reports": fold_reports,
        },
        "environment": environment_report(device),
        "runtime_seconds": float(time.time() - started),
        "input_sha256": {
            "train.csv": sha256_file(train_path),
            "test.csv": sha256_file(test_path),
            "sample_submission.csv": sha256_file(sample_path),
        },
        "outputs": [
            "oof_score.npy",
            "test_score.npy",
            "oof_proba.npy",
            "test_proba.npy",
            "fold_id.npy",
            "oof_fold_rank.npy",
            "submission.csv",
            "run_signature.json",
            "fold_checkpoints/",
            "cv_results.json",
        ],
    }
    (output_dir / "cv_results.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "oof_auc": overall_auc,
                "oof_fold_rank_auc": fold_rank_oof_auc,
                "fold_auc": fold_auc,
                "resumed_folds": resumed_folds,
                "runtime_seconds": manifest["runtime_seconds"],
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    config = smoke_config(args) if args.smoke_test else production_config(args)
    validate_config(config)
    seed_everything(SEED)
    print(
        f"[v21] device={device} smoke={args.smoke_test} "
        f"config={json.dumps(asdict(config), ensure_ascii=False)}",
        flush=True,
    )
    train, test, sample = load_frames(
        args.data_dir,
        smoke_test=args.smoke_test,
        smoke_train_rows=args.smoke_train_rows,
        smoke_test_rows=args.smoke_test_rows,
    )
    data = prepare_data(train, test, sample)
    print(
        f"[v21] train={train.shape} test={test.shape} "
        f"total_vocab={sum(data.vocab_sizes)} tokens="
        f"{1 + len(data.features) + len(data.derived_columns)}",
        flush=True,
    )
    if args.smoke_test:
        run_smoke(data, config, device, args.data_dir, args.output_dir)
    else:
        run_production(data, config, device, args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
