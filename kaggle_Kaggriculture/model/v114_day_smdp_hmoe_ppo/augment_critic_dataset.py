"""Add held-out simulator catastrophes to the V114 Replay critic dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np


def pooled_features(global_features, board, units, unit_mask) -> np.ndarray:
    global_features = np.asarray(global_features, dtype=np.float32)[:60]
    board = np.asarray(board, dtype=np.float32)
    units = np.asarray(units, dtype=np.float32)
    mask = np.asarray(unit_mask, dtype=np.float32)
    active = units[mask > 0.5]
    if len(active):
        unit_mean = active.mean(axis=0)
        unit_max = active.max(axis=0)
    else:
        unit_mean = np.zeros((units.shape[-1],), dtype=np.float32)
        unit_max = unit_mean.copy()
    return np.concatenate([
        global_features,
        board.mean(axis=(1, 2)).reshape(-1),
        board.max(axis=(1, 2)).reshape(-1),
        unit_mean,
        unit_max,
        np.asarray([mask.sum() / max(1, len(mask))], dtype=np.float32),
    ]).astype(np.float32)


def _split(seed: int) -> int:
    bucket = int.from_bytes(hashlib.sha256(f"sim|{seed}".encode()).digest()[:4], "big") % 10
    return 0 if bucket < 7 else 1 if bucket < 9 else 2


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def augment(replay_path: Path, simulator_path: Path, simulator_report: Path, output: Path, manifest: Path) -> dict:
    with np.load(replay_path, allow_pickle=False) as archive:
        replay = {key: np.asarray(archive[key]) for key in archive.files}
    simulator_keys = (
        "global", "board", "units", "unit_mask", "environment_step",
        "episode_seed", "seat", "reward",
    )
    # Load each compressed member once; indexing np.load archives in the loop
    # would repeatedly decompress multi-gigabyte arrays.
    with np.load(simulator_path, allow_pickle=False) as archive:
        simulator = {key: np.asarray(archive[key]) for key in simulator_keys}
    report = json.loads(simulator_report.read_text(encoding="utf-8"))
    outcomes = {
        (int(row["seed"]), int(row["seat"])): (
            float(row["candidate_reward"]), float(row["opponent_reward"])
        )
        for row in report["rows"]
    }
    rows = []
    keys = sorted(set(zip(simulator["episode_seed"].tolist(), simulator["seat"].tolist())))
    for seed_raw, seat_raw in keys:
        seed, seat = int(seed_raw), int(seat_raw)
        indexes = np.flatnonzero((simulator["episode_seed"] == seed) & (simulator["seat"] == seat))
        indexes = indexes[np.argsort(simulator["environment_step"][indexes])]
        own, opponent = outcomes[(seed, seat)]
        # V113 rollout rows label the first pre-action observation as step 1.
        for start in range(1, 697 + 1, 24):
            matches = indexes[simulator["environment_step"][indexes] == start]
            if len(matches) != 1:
                raise ValueError(f"seed={seed} seat={seat} step={start}: expected one state")
            index = int(matches[0])
            phase = indexes[
                (simulator["environment_step"][indexes] >= start)
                & (simulator["environment_step"][indexes] < min(719, start + 24))
            ]
            rows.append({
                "features": pooled_features(
                    simulator["global"][index], simulator["board"][index],
                    simulator["units"][index], simulator["unit_mask"][index],
                ),
                "manager_own": np.log1p(max(0.0, own)) / 12.0,
                "manager_margin": np.clip((own - opponent) / 200000.0, -2.0, 2.0),
                "catastrophe": float(own < 3000.0),
                "option_value": float(np.clip(simulator["reward"][phase].sum(), -2.0, 2.0)),
                "episode_id": seed,
                "seat": seat,
                "step": start - 1,
                "split": _split(seed),
            })
    sim_arrays = {
        "features": np.stack([row["features"] for row in rows]),
        "manager_own": np.asarray([row["manager_own"] for row in rows], dtype=np.float32),
        "manager_margin": np.asarray([row["manager_margin"] for row in rows], dtype=np.float32),
        "catastrophe": np.asarray([row["catastrophe"] for row in rows], dtype=np.float32),
        "option_value": np.asarray([row["option_value"] for row in rows], dtype=np.float32),
        "episode_id": np.asarray([row["episode_id"] for row in rows], dtype=np.int64),
        "seat": np.asarray([row["seat"] for row in rows], dtype=np.int8),
        "step": np.asarray([row["step"] for row in rows], dtype=np.int16),
        "split": np.asarray([row["split"] for row in rows], dtype=np.int8),
    }
    combined = {}
    for key in sim_arrays:
        combined[key] = np.concatenate([np.asarray(replay[key]), sim_arrays[key]], axis=0)
    combined["source"] = np.concatenate([
        np.zeros((len(replay["features"]),), dtype=np.int8),
        np.ones((len(sim_arrays["features"]),), dtype=np.int8),
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **combined)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    result = {
        "schema": "kaggriculture-v114-critic-dataset-v2",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "replay_dataset": str(replay_path),
        "simulator_dataset": str(simulator_path),
        "simulator_report": str(simulator_report),
        "simulator_policy_status": "FAILED_STAGE37_TRAJECTORIES_DATA_ONLY_NO_CHECKPOINT_INHERITANCE",
        "rows": int(len(combined["features"])),
        "replay_rows": int((combined["source"] == 0).sum()),
        "simulator_rows": int((combined["source"] == 1).sum()),
        "catastrophe_rate": float(combined["catastrophe"].mean()),
        "split_counts": {name: int((combined["split"] == value).sum()) for name, value in {"train": 0, "validation": 1, "test": 2}.items()},
        "dataset": str(output),
        "dataset_sha256": digest,
        "residual_target_status": "NOT_INCLUDED_REQUIRES_PAIRED_COUNTERFACTUAL",
    }
    _atomic_json(manifest, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--simulator", type=Path, required=True)
    parser.add_argument("--simulator-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = augment(args.replay, args.simulator, args.simulator_report, args.output, args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
