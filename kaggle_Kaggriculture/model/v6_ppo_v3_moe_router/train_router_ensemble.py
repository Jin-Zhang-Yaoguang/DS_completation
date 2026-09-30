"""Bootstrap ensemble training for conservative D2 Router deployment.

Every member is trained from a bootstrap of D2's *training groups*.  The
served NumPy artifact contains all members; inference uses mean uplift and
member standard deviation as a simple epistemic uncertainty estimate.  The
validation/test rows are never bootstrapped or used for selection here.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np

from router_model import ROUTER_SCHEMA
from train_router import load_dataset, train


def _row_arrays(data: np.lib.npyio.NpzFile):
    n = len(data["features"])
    return {key: np.asarray(data[key]) for key in data.files if np.asarray(data[key]).ndim >= 1 and np.asarray(data[key]).shape[0] == n}


def _bootstrap_file(source: Path, output: Path, seed: int) -> None:
    raw = np.load(source, allow_pickle=False)
    try:
        arrays = {key: np.asarray(raw[key]) for key in raw.files}
        n = len(arrays["features"])
        split = np.asarray(arrays.get("split", np.asarray(["train"] * n))).astype(str)
        train_idx = np.flatnonzero(split == "train")
        if len(train_idx) < 2:
            raise ValueError("need at least two D2 training rows for bootstrap ensemble")
        rng = np.random.default_rng(int(seed))
        # Preserve at least one qualifying training observation for every
        # non-default expert.  A plain bootstrap can omit a rare but valid
        # intervention (for example an animal-sale state), turning a member
        # into a structurally untrainable no-op model.
        required = []
        for key in ("production_mask", "market_mask"):
            mask = np.asarray(arrays[key], dtype=bool)
            for column in range(1, mask.shape[1]):
                support = train_idx[mask[train_idx, column]]
                if not len(support):
                    raise ValueError(f"D2 train split lacks support for {key} column {column}")
                required.append(int(rng.choice(support)))
        required = np.asarray(required, dtype=np.int64)
        remainder = rng.choice(train_idx, size=len(train_idx) - len(required), replace=True)
        boot_idx = np.concatenate((required, remainder))
        other_idx = np.flatnonzero(split != "train")
        order = np.concatenate((boot_idx, other_idx))
        for key, value in list(arrays.items()):
            if value.ndim >= 1 and value.shape[0] == n:
                arrays[key] = value[order]
        arrays["split"] = np.asarray(["train"] * len(boot_idx) + split[other_idx].tolist())
        np.savez_compressed(output, **arrays)
    finally:
        raw.close()


def _combine(member_weights: list[Path], output: Path) -> dict:
    opened = [np.load(path, allow_pickle=False) for path in member_weights]
    try:
        base = opened[0]
        names = (tuple(base["production_names"].tolist()), tuple(base["market_names"].tolist()))
        arrays = {
            "schema": np.asarray(ROUTER_SCHEMA),
            "feature_schema": base["feature_schema"], "feature_dim": base["feature_dim"],
            "production_names": base["production_names"], "market_names": base["market_names"],
            "ensemble_members": np.asarray(len(opened), dtype=np.int32),
        }
        parameter_keys = [key for key in base.files if key.endswith("_w") or key.endswith("_b")]
        for data in opened[1:]:
            if (tuple(data["production_names"].tolist()), tuple(data["market_names"].tolist())) != names:
                raise ValueError("member expert schemas differ")
            if str(data["schema"].item()) != ROUTER_SCHEMA:
                raise ValueError("member schema differs")
        for key in parameter_keys:
            arrays[key] = np.stack([np.asarray(data[key], dtype=np.float32) for data in opened], axis=0)
        output.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(output, **arrays)
    finally:
        for data in opened:
            data.close()
    return {"weights": str(output), "members": len(member_weights), "production_names": list(names[0]), "market_names": list(names[1])}


def train_ensemble(data: Path, output: Path, members: int, epochs: int, batch_size: int, learning_rate: float, seed: int) -> dict:
    # Validate data once before expensive bootstrap work; load_dataset also
    # rejects unqualified no-op candidate columns.
    load_dataset(data)
    output.mkdir(parents=True, exist_ok=True)
    reports, weight_paths = [], []
    with tempfile.TemporaryDirectory(prefix="ppo_v3_d2_bootstrap_") as temp:
        temp = Path(temp)
        for index in range(int(members)):
            boot = temp / f"member_{index}.npz"
            member_dir = output / f"member_{index}"
            _bootstrap_file(data, boot, int(seed) + index * 104729)
            report = train(load_dataset(boot), member_dir, epochs, batch_size, int(seed) + index * 104729, learning_rate)
            reports.append(report)
            weight_paths.append(member_dir / "router_weights.npz")
    combined = _combine(weight_paths, output / "router_weights.npz")
    report = {"schema": "kaggriculture-ppo-v3-router-ensemble-1", "bootstrap_members": int(members), "members": reports, **combined}
    (output / "ensemble_training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--members", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    print(json.dumps(train_ensemble(args.data, args.output, args.members, args.epochs, args.batch_size, args.learning_rate, args.seed), ensure_ascii=False, indent=2))
