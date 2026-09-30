"""Build group-split Replay shards for V113 BC/value initialization."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import time

import numpy as np

import action_space as space
import engine_parity
import features


def split_id(episode_id: int) -> int:
    bucket = int(hashlib.sha256(f"v113-split:{episode_id}".encode()).hexdigest()[:8], 16) % 100
    return 0 if bucket < 80 else (1 if bucket < 90 else 2)


def day_signatures(replay: dict, seat: int) -> dict[int, np.ndarray]:
    """Describe a whole day without assigning hand-written expert identity."""
    signatures: dict[int, np.ndarray] = {}
    counts: Counter = Counter()
    steps = replay.get("steps") or []
    for action_index in range(1, len(steps)):
        obs = dict(steps[action_index - 1][seat].get("observation") or {})
        obs["step"] = action_index - 1
        source = space.normalise_action(steps[action_index][seat].get("action") or {}, space.unit_count(obs) - 1)
        clean = space.decode_action(obs, space.encode_action(obs, source))
        day = (action_index - 1) // 24
        vector = signatures.setdefault(day, np.zeros((33,), dtype=np.float32))
        functional = space.functional_expert_label(clean, action_index - 1)
        vector[functional] += 1.0
        for order in [clean["farmer"], *clean["hands"]]:
            op = str(order[0]) if order else "PASS"
            if op == "PASS":
                vector[6] += 1.0
            elif op in space.MOVES:
                vector[7] += 1.0
            elif op in {"PICKUP", "PLACE", "DROP"}:
                vector[8] += 1.0
            elif op in {"PLANT", "WATER", "FERTILIZE", "HARVEST"}:
                vector[9] += 1.0
            elif op in {"FEED", "CARE", "COLLECT_FERTILIZER"}:
                vector[10] += 1.0
            elif op in {"BUILD_COOP", "BUILD_PASTURE", "DIG"}:
                vector[11] += 1.0
        for order in clean["market"]:
            op = str(order[0])
            vector[12 + {"HIRE": 0, "BUY_LAND": 1, "BUY_SEED": 2, "BUY_PRODUCT": 3, "BUY_ANIMAL": 4, "SELL": 5}.get(op, 5)] += 1.0
            if len(order) >= 2 and str(order[1]) in space.PRODUCTS:
                vector[18 + space.PRODUCTS.index(str(order[1]))] += 1.0
        vector[27] += len(clean["hands"]) + 1
        vector[28] += len(clean["market"])
        vector[29] += float(space.get(space.own_farm(obs), "money", 0.0) or 0.0) / 10000.0
        vector[30] += sum(float(v or 0) for v in (space.get(space.private(obs), "shed", {}) or {}).values()) / 100.0
        vector[31] += day / 30.0
        vector[32] += 1.0
        counts[day] += 1
    for day, vector in signatures.items():
        vector /= max(1, counts[day])
    return signatures


def fit_day_clusters(files: list[Path], clusters: int = 6, seed: int = 113004) -> tuple[dict[tuple[int, int, int], int], dict]:
    keys: list[tuple[int, int, int]] = []
    vectors: list[np.ndarray] = []
    for path in files:
        replay = json.loads(path.read_text(encoding="utf-8"))
        episode = int(path.stem)
        for seat in (0, 1):
            for day, signature in day_signatures(replay, seat).items():
                keys.append((episode, seat, day))
                vectors.append(signature)
    matrix = np.asarray(vectors, dtype=np.float32)
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale < 1e-5] = 1.0
    standardized = (matrix - mean) / scale
    rng = np.random.default_rng(seed)
    best_labels = None
    best_centers = None
    best_inertia = float("inf")
    for _ in range(8):
        centers = [standardized[rng.integers(len(standardized))]]
        while len(centers) < clusters:
            distance = np.min(np.stack([np.sum((standardized - center) ** 2, axis=1) for center in centers]), axis=0)
            probability = distance / max(1e-12, distance.sum())
            centers.append(standardized[rng.choice(len(standardized), p=probability)])
        centers = np.asarray(centers)
        for _ in range(50):
            distance = np.stack([np.sum((standardized - center) ** 2, axis=1) for center in centers], axis=1)
            labels = np.argmin(distance, axis=1)
            updated = np.stack([standardized[labels == index].mean(axis=0) if np.any(labels == index) else centers[index] for index in range(clusters)])
            if np.max(np.abs(updated - centers)) < 1e-5:
                centers = updated
                break
            centers = updated
        inertia = float(np.sum((standardized - centers[labels]) ** 2))
        if inertia < best_inertia:
            best_inertia, best_labels, best_centers = inertia, labels.copy(), centers.copy()
    label_map = {key: int(label) for key, label in zip(keys, best_labels)}
    metadata = {
        "method": "standardized_kmeans_day_action_signature",
        "seed": seed,
        "clusters": clusters,
        "days": len(keys),
        "cluster_counts": {str(index): int(np.sum(best_labels == index)) for index in range(clusters)},
        "inertia": best_inertia,
        "centers_standardized": best_centers.tolist(),
    }
    return label_map, metadata


def build(files: list[Path], stride: int) -> tuple[dict[str, np.ndarray], dict]:
    started = time.time()
    label_map, cluster_metadata = fit_day_clusters(files)
    rows: dict[str, list] = {key: [] for key in (
        "global", "board", "units", "unit_mask", "unit_tokens", "unit_quantities",
        "market_tokens", "market_quantities", "market_mask", "expert", "value", "split",
        "episode", "step", "seat",
    )}
    cleaned = 0
    total = 0
    for path in files:
        replay = json.loads(path.read_text(encoding="utf-8"))
        episode_id = int(path.stem)
        steps = replay.get("steps") or []
        terminal_rewards = [float((steps[-1][seat].get("reward") or 0.0)) for seat in (0, 1)]
        for seat in (0, 1):
            margin = terminal_rewards[seat] - terminal_rewards[1 - seat]
            value = (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)) + 0.05 * np.tanh(margin / 25000.0)
            for action_index in range(1, len(steps), stride):
                obs = dict(steps[action_index - 1][seat].get("observation") or {})
                obs["step"] = action_index - 1
                source = space.normalise_action(steps[action_index][seat].get("action") or {}, space.unit_count(obs) - 1)
                clean = space.decode_action(obs, space.encode_action(obs, source))
                cleaned += int(clean != source)
                total += 1
                encoded = space.encode_action(obs, clean)
                state = features.encode_observation(obs)
                unit_tokens = np.full((features.MAX_UNITS,), space.UNIT_INDEX["PASS"], dtype=np.int16)
                unit_quantities = np.zeros((features.MAX_UNITS,), dtype=np.int16)
                count = min(features.MAX_UNITS, len(encoded["unit_tokens"]))
                unit_tokens[:count] = encoded["unit_tokens"][:count]
                unit_quantities[:count] = encoded["unit_quantities"][:count]
                market_tokens = np.asarray(encoded["market_tokens"], dtype=np.int16)
                market_quantities = np.asarray(encoded["market_quantities"], dtype=np.int16)
                market_count = min(space.MAX_MARKET_SLOTS, len(clean["market"]) + 1)
                market_mask = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.float32)
                market_mask[:market_count] = 1.0
                for key in ("global", "board", "units", "unit_mask"):
                    rows[key].append(state[key])
                rows["unit_tokens"].append(unit_tokens)
                rows["unit_quantities"].append(unit_quantities)
                rows["market_tokens"].append(market_tokens)
                rows["market_quantities"].append(market_quantities)
                rows["market_mask"].append(market_mask)
                rows["expert"].append(label_map[(episode_id, seat, (action_index - 1) // 24)])
                rows["value"].append(value)
                rows["split"].append(split_id(episode_id))
                rows["episode"].append(episode_id)
                rows["step"].append(action_index - 1)
                rows["seat"].append(seat)
    arrays = {key: np.asarray(value) for key, value in rows.items()}
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)
    for key in ("unit_mask", "market_mask"):
        arrays[key] = arrays[key].astype(np.uint8)
    metadata = {
        "schema": "kaggriculture-v113-offline-dataset-v1",
        "episodes": len(files),
        "rows": total,
        "stride": stride,
        "cleaned_source_actions": cleaned,
        "source_action_cleaning_rate": cleaned / max(1, total),
        "split_rows": {name: int(np.sum(arrays["split"] == index)) for index, name in enumerate(("train", "validation", "test"))},
        "expert_rows": {str(index): int(np.sum(arrays["expert"] == index)) for index in range(6)},
        "expert_initialization": cluster_metadata,
        "feature_shapes": {key: list(value.shape[1:]) for key, value in arrays.items()},
        "elapsed_seconds": time.time() - started,
    }
    return arrays, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--module-version", default="1.32.7")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--stride", type=int, default=6)
    parser.add_argument("--selection-seed", type=int, default=113003)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = engine_parity.select_samples(engine_parity.discover(args.episodes_root, args.module_version), args.samples, args.selection_seed)
    arrays, metadata = build([Path(row["path"]) for row in selected], args.stride)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    meta_path = args.output.with_suffix(".json")
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
