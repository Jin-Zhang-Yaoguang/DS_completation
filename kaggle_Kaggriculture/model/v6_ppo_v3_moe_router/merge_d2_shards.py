"""Validate and merge independently generated D2 counterfactual shards.

Shards are intentionally accepted only when their expert ordering and tensor
schema agree.  State IDs must be globally unique: silently keeping the first
copy would give duplicated situations extra weight during router training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


REQUIRED = {
    "features", "production_mask", "market_mask", "production_uplift",
    "market_uplift", "state_ids", "production_names", "market_names",
}

# These arrays describe the tensor schema rather than individual state rows.
# They must never be concatenated, even when a tiny shard happens to contain
# exactly P or M states.  The old shape-only heuristic merged e.g.
# ``production_names`` for two-row/two-expert smoke shards, producing four
# names for a [N, 2] production tensor.
SCHEMA_KEYS = {"production_ids", "market_ids", "production_names", "market_names"}


def _text(value: np.ndarray) -> tuple[str, ...]:
    return tuple(str(item) for item in np.asarray(value).tolist())


def merge(inputs: list[Path], output: Path) -> dict[str, object]:
    if not inputs:
        raise ValueError("at least one input shard is required")
    opened = [np.load(path, allow_pickle=False) for path in inputs]
    try:
        for path, data in zip(inputs, opened):
            missing = REQUIRED.difference(data.files)
            if missing:
                raise ValueError(f"{path}: missing fields {sorted(missing)}")
        production = _text(opened[0]["production_names"])
        market = _text(opened[0]["market_names"])
        feature_shape = tuple(opened[0]["features"].shape[1:])
        seen: set[str] = set()
        for path, data in zip(inputs, opened):
            if _text(data["production_names"]) != production or _text(data["market_names"]) != market:
                raise ValueError(f"{path}: expert ordering differs")
            if tuple(data["features"].shape[1:]) != feature_shape:
                raise ValueError(f"{path}: feature shape differs")
            ids = _text(data["state_ids"])
            overlap = seen.intersection(ids)
            if overlap:
                raise ValueError(f"{path}: duplicate state_id {sorted(overlap)[0]}")
            seen.update(ids)
        common = [key for key in opened[0].files if all(key in data.files for data in opened)]
        merged: dict[str, np.ndarray] = {}
        for key in common:
            arrays = [np.asarray(data[key]) for data in opened]
            if key in SCHEMA_KEYS:
                if not all(np.array_equal(arrays[0], value) for value in arrays[1:]):
                    raise ValueError(f"{key}: non-row schema value differs")
                merged[key] = arrays[0]
            elif all(array.ndim >= 1 and array.shape[0] == len(data["features"]) for array, data in zip(arrays, opened)):
                merged[key] = np.concatenate(arrays, axis=0)
            else:
                # Expert names are schema values, not per-row data.
                if not all(np.array_equal(arrays[0], value) for value in arrays[1:]):
                    raise ValueError(f"{key}: non-row schema value differs")
                merged[key] = arrays[0]
        output.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(output, **merged)
    finally:
        for data in opened:
            data.close()
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    report = {
        "schema": "kaggriculture-ppo-v3-d2-merge-1",
        "inputs": [str(path) for path in inputs],
        "rows": int(len(merged["features"])),
        "feature_shape": list(feature_shape),
        "production_names": list(production),
        "market_names": list(market),
        "sha256": digest,
        "output": str(output),
    }
    output.with_suffix(".merge_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(merge(args.inputs, args.output), ensure_ascii=False, indent=2))
