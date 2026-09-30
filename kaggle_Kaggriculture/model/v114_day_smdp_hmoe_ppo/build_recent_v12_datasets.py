#!/usr/bin/env python3
"""Build recent-rule V114 unit, market and opponent datasets from one registry.

Only rows marked Train or Dev are opened.  Blind paths are filtered before any
worker receives them.  Official games contribute both public seats; own-online
games contribute only the uniquely registered submitted-agent seat.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
for module_path in (HERE, V113):
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))

import action_space as space  # noqa: E402
import features  # noqa: E402
from build_event_market_dataset import (  # noqa: E402
    EVENT_TYPES, PROCUREMENT_HEADS, SELL_HEADS, TRANSACTION_HEADS,
    aggregate, quantity_index,
)
from build_unit_task_dataset import (  # noqa: E402
    ITEMS, ROLE_NAMES, TASK_INDEX, TASK_OPERATIONS,
    infer_task, own_positions, role_for,
)


SPLIT_ID = {"train": 0, "dev": 1}
MOVES = set(space.MOVES)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def empty_rows(keys: tuple[str, ...]) -> dict[str, list[Any]]:
    return {key: [] for key in keys}


def seats_for(entry: dict[str, Any]) -> list[int]:
    if entry["registry_source"] == "official_daily_index":
        return [0, 1]
    seat = entry.get("seat")
    if seat not in (0, 1):
        raise ValueError(f"own-online row lacks unique seat: {entry['episode_id']}")
    return [int(seat)]


def encoded_state(observations: list[dict[str, Any]], cache: dict[int, dict[str, np.ndarray]], step: int):
    if step not in cache:
        cache[step] = features.encode_observation(observations[step])
    return cache[step]


def process_shard(
    shard_index: int,
    entries: list[dict[str, Any]],
    output_root: str,
    stride: int,
    horizon: int,
) -> dict[str, Any]:
    root = Path(output_root)
    unit_rows = empty_rows((
        "global", "board", "unit", "unit_index", "target_x", "target_y",
        "operation", "item", "quantity_tier", "duration", "role", "split",
        "episode", "step", "seat", "source",
    ))
    market_rows = empty_rows((
        "global", "board", "event_type", "presence", "quantity_tier",
        "quantity_raw", "split", "episode", "step", "seat", "source",
    ))
    opponent_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    operation_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    positive_counts: Counter[str] = Counter()

    for entry in entries:
        identity = int(entry["episode_id"])
        try:
            replay = json.loads(Path(entry["replay_path"]).read_text(encoding="utf-8"))
            steps = replay.get("steps") or []
            if len(steps) != 720:
                raise ValueError(f"expected 720 Replay indices, got {len(steps)}")
            team_names = list((replay.get("info") or {}).get("TeamNames") or entry.get("team_names") or ["", ""])
            seed = (replay.get("configuration") or {}).get("seed")
            if seed is None:
                seed = (replay.get("configuration") or {}).get("Seed", entry.get("seed"))
            source_id = 0 if entry["registry_source"] == "official_daily_index" else 1
            split = SPLIT_ID[entry["split"]]
            for seat in seats_for(entry):
                observations: list[dict[str, Any]] = []
                positions: list[list[tuple[int, int]]] = []
                orders: list[list[list[Any]]] = []
                market_tokens: list[np.ndarray] = []
                market_quantities: list[np.ndarray] = []
                unit_action_counts: Counter[str] = Counter()
                market_quantity_totals: Counter[str] = Counter()

                for action_index in range(1, len(steps)):
                    step = action_index - 1
                    observation = dict(steps[action_index - 1][seat].get("observation") or {})
                    observation["step"] = step
                    source_action = space.normalise_action(
                        steps[action_index][seat].get("action") or {},
                        space.unit_count(observation) - 1,
                    )
                    clean_action = space.decode_action(
                        observation, space.encode_action(observation, source_action)
                    )
                    encoded = space.encode_action(observation, clean_action)
                    clean_orders = [
                        list(clean_action["farmer"]),
                        *[list(order) for order in clean_action["hands"]],
                    ]
                    observations.append(observation)
                    positions.append(own_positions(observation))
                    orders.append(clean_orders)
                    market_tokens.append(np.asarray(encoded["market_tokens"], dtype=np.int16))
                    market_quantities.append(np.asarray(encoded["market_quantities"], dtype=np.int16))
                    for order in clean_orders:
                        operation = str((order or ["PASS"])[0])
                        unit_action_counts[operation] += 1
                    for token, quantity in zip(
                        market_tokens[-1].reshape(-1), market_quantities[-1].reshape(-1)
                    ):
                        name = space.MARKET_TOKENS[int(token)]
                        if name != "STOP":
                            market_quantity_totals[name] += 1 if name in {"HIRE", "BUY_LAND"} else max(1, int(quantity))

                cache: dict[int, dict[str, np.ndarray]] = {}
                # Persistent tasks are decisions with duration, not repeated primitives.
                # Fixed-interval states plus a lookahead target avoid overweighting a
                # teacher that emits the same operation on every engine step.
                sample_steps = list(range(0, len(observations), stride))
                for step in sample_steps:
                    state = encoded_state(observations, cache, step)
                    for unit_index in range(len(positions[step])):
                        x, y, operation, item, quantity, duration = infer_task(
                            step, unit_index, positions, orders, horizon
                        )
                        role = role_for(operation)
                        unit_rows["global"].append(state["global"])
                        unit_rows["board"].append(state["board"])
                        unit_rows["unit"].append(state["units"][unit_index])
                        unit_rows["unit_index"].append(unit_index)
                        unit_rows["target_x"].append(x)
                        unit_rows["target_y"].append(y)
                        unit_rows["operation"].append(TASK_INDEX[operation])
                        unit_rows["item"].append(ITEMS.index(item))
                        unit_rows["quantity_tier"].append(quantity)
                        unit_rows["duration"].append(duration)
                        unit_rows["role"].append(role)
                        unit_rows["split"].append(split)
                        unit_rows["episode"].append(identity)
                        unit_rows["step"].append(step)
                        unit_rows["seat"].append(seat)
                        unit_rows["source"].append(source_id)
                        operation_counts[operation] += 1
                        role_counts[ROLE_NAMES[role]] += 1

                token_array = np.asarray(market_tokens)
                quantity_array = np.asarray(market_quantities)

                def append_market(step: int, event_type: int, quantity: np.ndarray) -> None:
                    state = encoded_state(observations, cache, step)
                    market_rows["global"].append(np.asarray(state["global"], np.float16))
                    market_rows["board"].append(np.asarray(state["board"], np.float16))
                    market_rows["event_type"].append(event_type)
                    market_rows["presence"].append(quantity > 0)
                    market_rows["quantity_tier"].append(
                        np.asarray([quantity_index(value) for value in quantity], np.int8)
                    )
                    market_rows["quantity_raw"].append(quantity)
                    market_rows["split"].append(split)
                    market_rows["episode"].append(identity)
                    market_rows["step"].append(step)
                    market_rows["seat"].append(seat)
                    market_rows["source"].append(source_id)
                    event_counts[EVENT_TYPES[event_type]] += 1
                    for head_index in np.flatnonzero(quantity > 0):
                        positive_counts[TRANSACTION_HEADS[int(head_index)]] += 1

                for day in range(30):
                    start = day * 24
                    if start >= len(observations):
                        continue
                    stop = min(start + 24, len(observations))
                    quantity = aggregate(
                        token_array[start:stop], quantity_array[start:stop],
                        allow=set(PROCUREMENT_HEADS),
                    )
                    append_market(start, 0, quantity)

                previous_sell_signature = None
                for step in range(len(observations)):
                    quantity = aggregate(
                        token_array[step:step + 1], quantity_array[step:step + 1],
                        allow=set(SELL_HEADS),
                    )
                    signature = tuple(int(value > 0) for value in quantity[len(PROCUREMENT_HEADS):])
                    if not any(signature):
                        previous_sell_signature = None
                    elif signature != previous_sell_signature:
                        append_market(step, 1, quantity)
                        previous_sell_signature = signature

                terminal_step = 671
                quantity = aggregate(
                    token_array[terminal_step:], quantity_array[terminal_step:],
                    allow=set(SELL_HEADS),
                )
                append_market(terminal_step, 2, quantity)

                rewards = [float(steps[-1][index].get("reward") or 0.0) for index in (0, 1)]
                opponent_rows.append({
                    "episode_id": identity,
                    "game_date": entry["game_date"],
                    "split": entry["split"],
                    "registry_source": entry["registry_source"],
                    "submission_id": entry.get("submission_id"),
                    "model_version": entry.get("model_version"),
                    "replay_sha256": entry["replay_sha256"],
                    "seed": seed,
                    "seat": seat,
                    "team_name": team_names[seat] if len(team_names) > seat else None,
                    "opponent_name": team_names[1 - seat] if len(team_names) > 1 - seat else None,
                    "reward": rewards[seat],
                    "opponent_reward": rewards[1 - seat],
                    "margin": rewards[seat] - rewards[1 - seat],
                    "unit_action_counts": dict(sorted(unit_action_counts.items())),
                    "market_quantity_totals": dict(sorted(market_quantity_totals.items())),
                })
        except Exception as exc:
            failures.append({
                "episode_id": identity,
                "replay_path": entry["replay_path"],
                "error": f"{type(exc).__name__}: {exc}",
            })

    def unit_arrays() -> dict[str, np.ndarray]:
        arrays = {key: np.asarray(value) for key, value in unit_rows.items()}
        for key in ("global", "board", "unit"):
            arrays[key] = arrays[key].astype(np.float16)
        for key in (
            "unit_index", "target_x", "target_y", "operation", "item",
            "quantity_tier", "duration", "role", "split", "step", "seat", "source",
        ):
            arrays[key] = arrays[key].astype(np.int16)
        arrays["episode"] = arrays["episode"].astype(np.int64)
        return arrays

    def market_arrays() -> dict[str, np.ndarray]:
        arrays = {key: np.asarray(value) for key, value in market_rows.items()}
        arrays["global"] = arrays["global"].astype(np.float16)
        arrays["board"] = arrays["board"].astype(np.float16)
        arrays["event_type"] = arrays["event_type"].astype(np.int8)
        arrays["presence"] = arrays["presence"].astype(np.bool_)
        arrays["quantity_tier"] = arrays["quantity_tier"].astype(np.int8)
        arrays["quantity_raw"] = arrays["quantity_raw"].astype(np.int16)
        arrays["split"] = arrays["split"].astype(np.int8)
        arrays["episode"] = arrays["episode"].astype(np.int64)
        arrays["step"] = arrays["step"].astype(np.int16)
        arrays["seat"] = arrays["seat"].astype(np.int8)
        arrays["source"] = arrays["source"].astype(np.int8)
        return arrays

    unit_path = root / "unit_tasks" / f"unit_tasks_{shard_index:04d}.npz"
    market_path = root / "event_market" / f"event_market_{shard_index:04d}.npz"
    opponent_path = root / "opponent_features" / f"opponent_features_{shard_index:04d}.json"
    units = unit_arrays()
    markets = market_arrays()
    atomic_npz(unit_path, units)
    atomic_npz(market_path, markets)
    atomic_json(opponent_path, opponent_rows)
    report = {
        "shard": shard_index,
        "episodes": [int(entry["episode_id"]) for entry in entries],
        "games": len(opponent_rows),
        "failures": failures,
        "unit": {"path": str(unit_path.resolve()), "sha256": sha256_file(unit_path), "rows": len(units["episode"])},
        "market": {"path": str(market_path.resolve()), "sha256": sha256_file(market_path), "rows": len(markets["episode"])},
        "opponent": {"path": str(opponent_path.resolve()), "sha256": sha256_file(opponent_path), "rows": len(opponent_rows)},
        "operation_counts": dict(operation_counts),
        "role_counts": dict(role_counts),
        "event_counts": dict(event_counts),
        "positive_counts": dict(positive_counts),
    }
    atomic_json(root / "shard_reports" / f"shard_{shard_index:04d}.json", report)
    return report


def recover_completed_shard(
    shard_index: int, entries: list[dict[str, Any]], output_root: Path
) -> dict[str, Any] | None:
    report_path = output_root / "shard_reports" / f"shard_{shard_index:04d}.json"
    if report_path.exists():
        return json.loads(report_path.read_text(encoding="utf-8"))
    unit_path = output_root / "unit_tasks" / f"unit_tasks_{shard_index:04d}.npz"
    market_path = output_root / "event_market" / f"event_market_{shard_index:04d}.npz"
    opponent_path = output_root / "opponent_features" / f"opponent_features_{shard_index:04d}.json"
    if not all(path.exists() for path in (unit_path, market_path, opponent_path)):
        return None
    try:
        with np.load(unit_path, allow_pickle=False) as archive:
            operation = np.asarray(archive["operation"])
            role = np.asarray(archive["role"])
            unit_rows = len(archive["episode"])
        with np.load(market_path, allow_pickle=False) as archive:
            event_type = np.asarray(archive["event_type"])
            presence = np.asarray(archive["presence"])
            market_rows = len(archive["episode"])
        opponent_rows = json.loads(opponent_path.read_text(encoding="utf-8"))
        report = {
            "shard": shard_index,
            "episodes": [int(entry["episode_id"]) for entry in entries],
            "games": len(opponent_rows),
            "failures": [],
            "unit": {"path": str(unit_path.resolve()), "sha256": sha256_file(unit_path), "rows": unit_rows},
            "market": {"path": str(market_path.resolve()), "sha256": sha256_file(market_path), "rows": market_rows},
            "opponent": {"path": str(opponent_path.resolve()), "sha256": sha256_file(opponent_path), "rows": len(opponent_rows)},
            "operation_counts": {
                name: int(np.sum(operation == index))
                for index, name in enumerate(TASK_OPERATIONS)
            },
            "role_counts": {
                name: int(np.sum(role == index)) for index, name in enumerate(ROLE_NAMES)
            },
            "event_counts": {
                name: int(np.sum(event_type == index)) for index, name in enumerate(EVENT_TYPES)
            },
            "positive_counts": {
                name: int(np.sum(presence[:, index]))
                for index, name in enumerate(TRANSACTION_HEADS)
            },
            "resumed_from_atomic_outputs": True,
        }
        atomic_json(report_path, report)
        return report
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--episodes-per-shard", type=int, default=8)
    parser.add_argument("--stride", type=int, default=12)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--max-entries", type=int, default=0)
    args = parser.parse_args()
    started = time.time()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    if not str(registry.get("status", "")).startswith("QUALIFIED"):
        raise SystemExit("Recent replay registry is not qualified")
    selected = [entry for entry in registry["entries"] if entry["split"] in SPLIT_ID]
    if args.max_entries > 0:
        selected = selected[:args.max_entries]
    if any(entry["split"] == "blind" for entry in selected):
        raise SystemExit("Blind entry reached worker selection")
    chunks = [
        selected[offset:offset + args.episodes_per_shard]
        for offset in range(0, len(selected), args.episodes_per_shard)
    ]
    reports = []
    pending: list[tuple[int, list[dict[str, Any]]]] = []
    for index, chunk in enumerate(chunks):
        recovered = recover_completed_shard(index, chunk, args.output_root)
        if recovered is None:
            pending.append((index, chunk))
        else:
            reports.append(recovered)
    if reports:
        print(json.dumps({
            "resumed_completed_shards": len(reports),
            "pending_shards": len(pending),
            "total_shards": len(chunks),
        }), flush=True)
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                process_shard, index, chunk, str(args.output_root.resolve()),
                args.stride, args.horizon,
            ): index
            for index, chunk in pending
        }
        for completed, future in enumerate(as_completed(futures), start=len(reports) + 1):
            report = future.result()
            reports.append(report)
            print(json.dumps({
                "completed_shards": completed,
                "total_shards": len(chunks),
                "shard": report["shard"],
                "unit_rows": report["unit"]["rows"],
                "market_rows": report["market"]["rows"],
                "failures": len(report["failures"]),
            }), flush=True)
    reports.sort(key=lambda row: row["shard"])
    failures = [failure for report in reports for failure in report["failures"]]
    aggregate_counts: dict[str, Counter[str]] = {
        name: Counter() for name in ("operation_counts", "role_counts", "event_counts", "positive_counts")
    }
    for report in reports:
        for name, counter in aggregate_counts.items():
            counter.update(report[name])
    manifest = {
        "schema": "kaggriculture-v114-recent-v12-datasets-v1",
        "status": "QUALIFIED_OFFLINE_DATASET_NOT_CHECKPOINT_NOT_GOLD" if not failures else "PARTIAL_FAIL_CLOSED",
        "registry": str(args.registry.resolve()),
        "registry_sha256": sha256_file(args.registry),
        "source_registry_status": registry["status"],
        "blind_policy": {
            "selected_rows": 0,
            "content_accessed": False,
            "allowed_splits": ["train", "dev"],
        },
        "input_entries": len(selected),
        "max_entries_for_run": args.max_entries,
        "input_split_entries": dict(Counter(entry["split"] for entry in selected)),
        "games": sum(report["games"] for report in reports),
        "unit_rows": sum(report["unit"]["rows"] for report in reports),
        "market_rows": sum(report["market"]["rows"] for report in reports),
        "opponent_rows": sum(report["opponent"]["rows"] for report in reports),
        "failures": failures,
        "stride": args.stride,
        "unit_sampling_contract": "fixed interval state; next objective within lookahead; repeated primitives are not extra rows",
        "lookahead_horizon": args.horizon,
        "unit_task_operations": TASK_OPERATIONS,
        "unit_roles": ROLE_NAMES,
        "market_event_types": EVENT_TYPES,
        "market_transaction_heads": TRANSACTION_HEADS,
        "counts": {name: dict(counter) for name, counter in aggregate_counts.items()},
        "shards": reports,
        "strategy_parent": None,
        "historical_checkpoint_inherited": False,
        "qualification_status": "OFFLINE_RECENT_RULE_DATA_ONLY_NOT_G1_NOT_G2_NOT_PPO_NOT_GOLD",
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output_root / "manifest.json", manifest)
    print(json.dumps({
        "status": manifest["status"],
        "input_entries": manifest["input_entries"],
        "games": manifest["games"],
        "unit_rows": manifest["unit_rows"],
        "market_rows": manifest["market_rows"],
        "opponent_rows": manifest["opponent_rows"],
        "failures": len(failures),
        "manifest": str((args.output_root / 'manifest.json').resolve()),
        "manifest_sha256": sha256_file(args.output_root / "manifest.json"),
        "elapsed_seconds": manifest["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
