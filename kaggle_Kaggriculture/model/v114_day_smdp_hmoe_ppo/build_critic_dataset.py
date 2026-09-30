"""Build leakage-safe day-boundary critic data from official 1.32.7 Replay files."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as shared_space  # noqa: E402
import engine_parity as shared_engine  # noqa: E402
import features as shared_features  # noqa: E402


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def critic_features(obs: Mapping[str, Any]) -> np.ndarray:
    encoded = shared_features.encode_observation(obs)
    board = np.asarray(encoded["board"], dtype=np.float32)
    units = np.asarray(encoded["units"], dtype=np.float32)
    mask = np.asarray(encoded["unit_mask"], dtype=np.float32)
    active = units[mask > 0.5]
    if len(active):
        unit_mean = active.mean(axis=0)
        unit_max = active.max(axis=0)
    else:
        unit_mean = np.zeros((units.shape[-1],), dtype=np.float32)
        unit_max = unit_mean.copy()
    return np.concatenate([
        np.asarray(encoded["global"], dtype=np.float32),
        board.mean(axis=(1, 2)).reshape(-1),
        board.max(axis=(1, 2)).reshape(-1),
        unit_mean,
        unit_max,
        np.asarray([mask.sum() / max(1, len(mask))], dtype=np.float32),
    ]).astype(np.float32)


def enterprise_value(obs: Mapping[str, Any]) -> float:
    player = shared_space.seat(obs)
    farms = list(_get(obs, "farms", []) or [])
    own = farms[player] if player < len(farms) else {}
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    seeds = _get(private, "seeds", {}) or {}
    inventories = list(_get(private, "inventories", []) or [])
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    value = float(_get(own, "money", 0) or 0)
    for crop in shared_space.CROPS:
        value += float(_get(seeds, crop, 0) or 0) * shared_space.SEED_COST[crop]
    for inventory in [shed, *inventories]:
        for item in shared_space.PRODUCTS:
            value += float(_get(inventory, item, 0) or 0) * float(
                _get(prices, item, shared_space.BASE_PRICES[item]) or shared_space.BASE_PRICES[item]
            )
        for animal in shared_space.ANIMALS:
            value += float(_get(inventory, animal, 0) or 0) * shared_space.ANIMAL_COST[animal]
    return value


def _split(team_names: list[str], episode_id: int) -> str:
    identity = "|".join(sorted(map(str, team_names))) or str(episode_id)
    bucket = int.from_bytes(hashlib.sha256(identity.encode("utf-8")).digest()[:4], "big") % 10
    return "train" if bucket < 7 else "validation" if bucket < 9 else "test"


def extract_episode(row: dict[str, Any]) -> dict[str, Any]:
    path = Path(row["path"])
    replay = json.loads(path.read_text(encoding="utf-8"))
    steps = replay.get("steps") or []
    if len(steps) != 720:
        raise ValueError(f"{path}: expected 720 steps, got {len(steps)}")
    rewards = [float(value or 0) for value in replay.get("rewards") or [0, 0]]
    info = replay.get("info") or {}
    teams = list(info.get("TeamNames") or [])
    episode_id = int(info.get("EpisodeId") or row["episode_id"])
    split = _split(teams, episode_id)
    features: list[np.ndarray] = []
    manager_own: list[float] = []
    manager_margin: list[float] = []
    catastrophe: list[float] = []
    option_value: list[float] = []
    metadata: list[tuple[int, int, int, str]] = []
    boundaries = list(range(0, 720, 24))
    for seat in (0, 1):
        own_reward = rewards[seat]
        opponent_reward = rewards[1 - seat]
        values = []
        observations = []
        for step in boundaries:
            obs = dict(steps[step][seat].get("observation") or {})
            obs["step"] = step
            observations.append(obs)
            values.append(enterprise_value(obs))
        for index, (step, obs) in enumerate(zip(boundaries, observations)):
            next_value = values[min(index + 1, len(values) - 1)]
            features.append(critic_features(obs))
            manager_own.append(np.log1p(max(0.0, own_reward)) / 12.0)
            manager_margin.append(np.clip((own_reward - opponent_reward) / 200000.0, -2.0, 2.0))
            catastrophe.append(float(own_reward < 3000.0))
            option_value.append(np.clip((next_value - values[index]) / 100000.0, -2.0, 2.0))
            metadata.append((episode_id, seat, step, split))
    return {
        "features": np.stack(features),
        "manager_own": np.asarray(manager_own, dtype=np.float32),
        "manager_margin": np.asarray(manager_margin, dtype=np.float32),
        "catastrophe": np.asarray(catastrophe, dtype=np.float32),
        "option_value": np.asarray(option_value, dtype=np.float32),
        "metadata": metadata,
        "teams": teams,
        "path": str(path),
    }


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def build(episodes_root: Path, episodes: int, workers: int, output: Path, manifest: Path) -> dict[str, Any]:
    discovered = shared_engine.discover(episodes_root, "1.32.7")
    selected = shared_engine.select_samples(discovered, episodes, 114101)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    with ProcessPoolExecutor(max_workers=max(1, workers)) as pool:
        future_rows = {pool.submit(extract_episode, row): row for row in selected}
        for index, future in enumerate(as_completed(future_rows), 1):
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({"path": future_rows[future]["path"], "error": repr(exc)})
            if index % 16 == 0 or index == len(selected):
                print(json.dumps({"phase": "V4_1_DATA", "completed": index, "total": len(selected), "failed": len(failures)}), flush=True)
    if failures:
        raise RuntimeError(f"critic dataset extraction failed: {failures[:3]}")
    results.sort(key=lambda item: item["path"])
    arrays = {key: np.concatenate([item[key] for item in results], axis=0) for key in (
        "features", "manager_own", "manager_margin", "catastrophe", "option_value"
    )}
    metadata = [row for item in results for row in item["metadata"]]
    arrays["episode_id"] = np.asarray([row[0] for row in metadata], dtype=np.int64)
    arrays["seat"] = np.asarray([row[1] for row in metadata], dtype=np.int8)
    arrays["step"] = np.asarray([row[2] for row in metadata], dtype=np.int16)
    split_map = {"train": 0, "validation": 1, "test": 2}
    arrays["split"] = np.asarray([split_map[row[3]] for row in metadata], dtype=np.int8)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **arrays)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    split_counts = {name: int((arrays["split"] == value).sum()) for name, value in split_map.items()}
    report = {
        "schema": "kaggriculture-v114-critic-dataset-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "module_version": "1.32.7",
        "selection_seed": 114101,
        "episodes": len(results),
        "rows": int(len(arrays["features"])),
        "feature_dim": int(arrays["features"].shape[1]),
        "split_counts": split_counts,
        "split_contract": "deterministic_team_pair_hash_70_20_10",
        "dataset": str(output),
        "dataset_sha256": digest,
        "residual_target_status": "NOT_INCLUDED_REQUIRES_PAIRED_SIMULATOR_COUNTERFACTUAL",
        "source_files": [item["path"] for item in results],
        "source_teams": [item["teams"] for item in results],
    }
    _atomic_json(manifest, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=128)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.episodes_root, args.episodes, args.workers, args.output, args.manifest)
    print(json.dumps({key: report[key] for key in ("episodes", "rows", "feature_dim", "split_counts", "dataset_sha256")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

