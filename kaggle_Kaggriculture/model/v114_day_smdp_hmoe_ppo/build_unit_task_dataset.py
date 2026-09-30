"""Compress V2/V8 Replay into persistent unit-task supervision for V12 G1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
import features  # noqa: E402
from build_replay_lineage_dataset import episode_id, replay_inventory, split_id  # noqa: E402


TASK_OPERATIONS = (
    "REST", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG",
    "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
    "PICKUP", "PLACE", "DROP",
)
TASK_INDEX = {name: index for index, name in enumerate(TASK_OPERATIONS)}
ITEMS = ("NONE", *space.ITEMS)
ITEM_INDEX = {name: index for index, name in enumerate(ITEMS)}
QUANTITY_TIERS = (0, 1, 2, 3, 5, 10, 25, 50, 100)
ROLE_NAMES = ("CROP_PRODUCTION", "ANIMAL_MAINTENANCE", "LOGISTICS", "RECOVERY_IDLE")
MOVES = set(space.MOVES)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantity_tier(quantity: int) -> int:
    value = max(0, int(quantity))
    return min(range(len(QUANTITY_TIERS)), key=lambda index: (abs(QUANTITY_TIERS[index] - value), index))


def role_for(operation: str) -> int:
    if operation in {"PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG"}:
        return 0
    if operation in {
        "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
    }:
        return 1
    if operation in {"PICKUP", "PLACE", "DROP"}:
        return 2
    return 3


def own_positions(observation: dict) -> list[tuple[int, int]]:
    player = int(observation.get("player", 0) or 0)
    farm = list(observation.get("farms", []) or [])[player]
    raw = [farm.get("farmer", [0, 0]), *list(farm.get("hands", []) or [])]
    return [(int(position[0]), int(position[1])) for position in raw]


def canonical_orders(observation: dict, action: dict) -> list[list]:
    source = space.normalise_action(action or {}, space.unit_count(observation) - 1)
    clean = space.decode_action(observation, space.encode_action(observation, source))
    return [list(clean["farmer"]), *[list(order) for order in clean["hands"]]]


def infer_task(
    start: int,
    unit_index: int,
    positions: list[list[tuple[int, int]]],
    orders: list[list[list]],
    horizon: int,
) -> tuple[int, int, str, str, int, int]:
    """Infer the next non-movement objective from an executed trajectory."""
    origin = positions[start][unit_index]
    stop = min(len(orders), start + horizon + 1)
    for future in range(start, stop):
        if unit_index >= len(orders[future]) or unit_index >= len(positions[future]):
            break
        order = orders[future][unit_index] or ["PASS"]
        operation = str(order[0])
        if operation == "PASS" or operation in MOVES:
            continue
        if operation not in TASK_INDEX:
            continue
        target = positions[future][unit_index]
        item = str(order[1]) if len(order) >= 2 and str(order[1]) in ITEM_INDEX else "NONE"
        quantity = int(order[2]) if len(order) >= 3 else 0
        return target[0], target[1], operation, item, quantity_tier(quantity), future - start
    return origin[0], origin[1], "REST", "NONE", 0, horizon


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def build_source(
    replay_root: Path,
    sync_manifest: Path,
    output_dir: Path,
    family: str,
    *,
    stride: int = 6,
    horizon: int = 24,
    episodes_per_shard: int = 16,
) -> dict:
    started = time.time()
    files, seats, replay_bundle_sha = replay_inventory(replay_root, sync_manifest)
    shard_reports = []
    operation_counts = {name: 0 for name in TASK_OPERATIONS}
    role_counts = {name: 0 for name in ROLE_NAMES}
    total_rows = 0
    for shard_index, offset in enumerate(range(0, len(files), episodes_per_shard)):
        rows: dict[str, list] = {key: [] for key in (
            "global", "board", "unit", "unit_index", "target_x", "target_y",
            "operation", "item", "quantity_tier", "duration", "role", "split",
            "episode", "step", "seat", "teacher_family",
        )}
        selected = files[offset:offset + episodes_per_shard]
        for path in selected:
            identity = episode_id(path)
            seat = seats[identity]
            replay = json.loads(path.read_text(encoding="utf-8"))
            steps = replay.get("steps") or []
            if len(steps) != 720:
                raise ValueError(f"episode {identity} has {len(steps)} Replay indices")
            observations: list[dict] = []
            positions: list[list[tuple[int, int]]] = []
            orders: list[list[list]] = []
            states: list[dict[str, np.ndarray]] = []
            for action_index in range(1, len(steps)):
                observation = dict(steps[action_index - 1][seat].get("observation") or {})
                observation["step"] = action_index - 1
                observations.append(observation)
                positions.append(own_positions(observation))
                orders.append(canonical_orders(
                    observation, steps[action_index][seat].get("action") or {}
                ))
                states.append(features.encode_observation(observation))

            for step in range(len(observations)):
                current_ops = [str((order or ["PASS"])[0]) for order in orders[step]]
                sample_step = step % stride == 0 or any(
                    operation not in MOVES | {"PASS"} for operation in current_ops
                )
                if not sample_step:
                    continue
                state = states[step]
                for unit_index in range(len(positions[step])):
                    x, y, operation, item, quantity, duration = infer_task(
                        step, unit_index, positions, orders, horizon
                    )
                    role = role_for(operation)
                    rows["global"].append(state["global"])
                    rows["board"].append(state["board"])
                    rows["unit"].append(state["units"][unit_index])
                    rows["unit_index"].append(unit_index)
                    rows["target_x"].append(x)
                    rows["target_y"].append(y)
                    rows["operation"].append(TASK_INDEX[operation])
                    rows["item"].append(ITEM_INDEX[item])
                    rows["quantity_tier"].append(quantity)
                    rows["duration"].append(duration)
                    rows["role"].append(role)
                    rows["split"].append(split_id(identity))
                    rows["episode"].append(identity)
                    rows["step"].append(step)
                    rows["seat"].append(seat)
                    rows["teacher_family"].append(family)
                    operation_counts[operation] += 1
                    role_counts[ROLE_NAMES[role]] += 1

        arrays = {key: np.asarray(value) for key, value in rows.items()}
        for key in ("global", "board", "unit"):
            arrays[key] = arrays[key].astype(np.float16)
        for key in (
            "unit_index", "target_x", "target_y", "operation", "item", "quantity_tier",
            "duration", "role", "split", "step", "seat",
        ):
            arrays[key] = arrays[key].astype(np.int16)
        arrays["episode"] = arrays["episode"].astype(np.int64)
        shard_path = output_dir / f"unit_tasks_{shard_index:03d}.npz"
        _atomic_npz(shard_path, arrays)
        report = {
            "path": str(shard_path.resolve()),
            "sha256": sha256_file(shard_path),
            "rows": int(len(arrays["step"])),
            "episodes": [episode_id(path) for path in selected],
        }
        shard_reports.append(report)
        total_rows += report["rows"]

    manifest = {
        "schema": "kaggriculture-v114-v12-unit-task-dataset-v1",
        "teacher_family": family,
        "sync_manifest": str(sync_manifest.resolve()),
        "sync_manifest_sha256": sha256_file(sync_manifest),
        "replay_bundle_sha256": replay_bundle_sha,
        "episodes": len(files),
        "rows": total_rows,
        "stride": stride,
        "lookahead_horizon": horizon,
        "task_operations": TASK_OPERATIONS,
        "items": ITEMS,
        "quantity_tiers": QUANTITY_TIERS,
        "roles": ROLE_NAMES,
        "operation_rows": operation_counts,
        "role_rows": role_counts,
        "shards": shard_reports,
        "input_contract": "current public observation and one current unit only",
        "target_contract": "next non-movement objective target, operation, item, quantity tier and duration",
        "teacher_identity_model_input": False,
        "historical_agent_online_action_source": False,
        "strategy_parent": None,
        "qualification_status": "OFFLINE_UNIT_TASK_DATA_ONLY_NOT_G1_NOT_GOLD",
        "elapsed_seconds": time.time() - started,
    }
    _atomic_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--sync-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--stride", type=int, default=6)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--episodes-per-shard", type=int, default=16)
    args = parser.parse_args()
    report = build_source(
        args.replay_root, args.sync_manifest, args.output_dir, args.family,
        stride=args.stride, horizon=args.horizon, episodes_per_shard=args.episodes_per_shard,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
