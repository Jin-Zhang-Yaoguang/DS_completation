"""Deterministic nested meta-fold generation with confirmation-seed gating."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.model_selection import StratifiedKFold

from .registry import RegistryError, sha256_file, sha256_int_array, sha256_json, write_json_exclusive


DEFAULT_OUTER_SEEDS = (42, 2026, 3407, 8119, 104743)
DEFAULT_CONFIRMATION_SEED = 104743


def _validate_target(target: np.ndarray, n_splits: int) -> np.ndarray:
    labels = np.asarray(target)
    if labels.ndim != 1:
        raise ValueError("target must be one-dimensional")
    unique, counts = np.unique(labels, return_counts=True)
    if set(unique.tolist()) != {0, 1}:
        raise ValueError("target must contain exactly binary labels 0 and 1")
    if counts.min() < n_splits:
        raise ValueError("each class must contain at least n_splits rows")
    return labels.astype(np.int8, copy=False)


def generate_meta_folds(
    target: np.ndarray,
    *,
    outer_seeds: Sequence[int] = DEFAULT_OUTER_SEEDS,
    confirmation_seed: int = DEFAULT_CONFIRMATION_SEED,
    outer_splits: int = 5,
    inner_splits: int = 5,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Generate all shared indices without fitting, scoring or exposing results."""

    labels = _validate_target(target, max(outer_splits, inner_splits))
    seeds = tuple(int(seed) for seed in outer_seeds)
    if len(set(seeds)) != len(seeds):
        raise ValueError("outer seeds must be unique")
    if confirmation_seed not in seeds:
        raise ValueError("confirmation_seed must be included in outer_seeds")
    arrays: dict[str, np.ndarray] = {}
    outer_records: list[dict[str, Any]] = []

    for seed in seeds:
        splitter = StratifiedKFold(n_splits=outer_splits, shuffle=True, random_state=seed)
        for outer_fold, (train_index, valid_index) in enumerate(
            splitter.split(np.zeros(len(labels)), labels), start=1
        ):
            train_index = np.asarray(train_index, dtype=np.int64)
            valid_index = np.asarray(valid_index, dtype=np.int64)
            train_key = f"outer_s{seed}_f{outer_fold}_train"
            valid_key = f"outer_s{seed}_f{outer_fold}_valid"
            arrays[train_key] = train_index
            arrays[valid_key] = valid_index
            inner_seed = int((seed * 1_000_003 + outer_fold * 1_009 + 17) % (2**32 - 1))
            inner = StratifiedKFold(
                n_splits=inner_splits,
                shuffle=True,
                random_state=inner_seed,
            )
            inner_records: list[dict[str, Any]] = []
            outer_train_labels = labels[train_index]
            for inner_fold, (inner_train_rel, inner_valid_rel) in enumerate(
                inner.split(np.zeros(len(train_index)), outer_train_labels), start=1
            ):
                inner_train = train_index[np.asarray(inner_train_rel, dtype=np.int64)]
                inner_valid = train_index[np.asarray(inner_valid_rel, dtype=np.int64)]
                inner_train_key = f"{train_key}_inner{inner_fold}_train"
                inner_valid_key = f"{train_key}_inner{inner_fold}_valid"
                arrays[inner_train_key] = inner_train
                arrays[inner_valid_key] = inner_valid
                inner_records.append(
                    {
                        "fold": inner_fold,
                        "train_key": inner_train_key,
                        "valid_key": inner_valid_key,
                        "train_sha256": sha256_int_array(inner_train),
                        "valid_sha256": sha256_int_array(inner_valid),
                        "train_rows": len(inner_train),
                        "valid_rows": len(inner_valid),
                    }
                )
            outer_records.append(
                {
                    "seed": seed,
                    "role": "confirmation" if seed == confirmation_seed else "development",
                    "fold": outer_fold,
                    "train_key": train_key,
                    "valid_key": valid_key,
                    "train_sha256": sha256_int_array(train_index),
                    "valid_sha256": sha256_int_array(valid_index),
                    "train_rows": len(train_index),
                    "valid_rows": len(valid_index),
                    "inner_seed": inner_seed,
                    "inner_folds": inner_records,
                }
            )

    manifest = {
        "schema_version": 1,
        "n_rows": len(labels),
        "target_sha256": sha256_int_array(labels),
        "outer_splits": outer_splits,
        "inner_splits": inner_splits,
        "outer_seeds": list(seeds),
        "development_seeds": [seed for seed in seeds if seed != confirmation_seed],
        "confirmation_seed": confirmation_seed,
        "confirmation_locked_by_default": True,
        "outer_folds": outer_records,
    }
    manifest["fold_definition_sha256"] = sha256_json(manifest)
    return manifest, arrays


def save_meta_folds(
    output_dir: Path,
    manifest: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
) -> tuple[Path, Path]:
    """Persist indices once as compressed NPZ plus the required JSON manifest."""

    output_dir.mkdir(parents=True, exist_ok=True)
    npz_path = output_dir / "meta_fold_indices.npz"
    manifest_path = output_dir / "meta_folds.json"
    with npz_path.open("xb") as handle:
        np.savez_compressed(handle, **arrays)
    enriched = dict(manifest)
    enriched["indices_file"] = npz_path.name
    enriched["indices_file_sha256"] = sha256_file(npz_path)
    envelope = {"meta_folds": enriched, "meta_folds_sha256": sha256_json(enriched)}
    write_json_exclusive(manifest_path, envelope)
    return manifest_path, npz_path


def load_meta_folds(
    manifest_path: Path,
    *,
    include_confirmation: bool = False,
    confirmation_unlocked: bool = False,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Load development folds by default; confirmation requires two explicit flags."""

    with manifest_path.open(encoding="utf-8") as handle:
        envelope = json.load(handle)
    manifest = envelope.get("meta_folds")
    if not isinstance(manifest, Mapping) or sha256_json(manifest) != envelope.get("meta_folds_sha256"):
        raise RegistryError("meta-fold manifest hash mismatch")
    if include_confirmation and not confirmation_unlocked:
        raise RegistryError("confirmation folds remain locked until the method is frozen")
    npz_path = manifest_path.parent / manifest["indices_file"]
    if sha256_file(npz_path) != manifest["indices_file_sha256"]:
        raise RegistryError("meta-fold index file hash mismatch")
    allowed_records = [
        record
        for record in manifest["outer_folds"]
        if include_confirmation or record["role"] == "development"
    ]
    allowed_keys: set[str] = set()
    for record in allowed_records:
        allowed_keys.update((record["train_key"], record["valid_key"]))
        for inner in record["inner_folds"]:
            allowed_keys.update((inner["train_key"], inner["valid_key"]))
    with np.load(npz_path, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in sorted(allowed_keys)}
    filtered = dict(manifest)
    filtered["outer_folds"] = allowed_records
    filtered["confirmation_included"] = include_confirmation
    return filtered, arrays
