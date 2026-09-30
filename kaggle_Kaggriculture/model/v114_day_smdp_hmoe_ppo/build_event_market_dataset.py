"""Compress Replay market queues into V12 event-level transaction supervision."""

from __future__ import annotations

import argparse
from collections import Counter
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


EVENT_TYPES = ("DAY_START", "INVENTORY_THRESHOLD", "TERMINAL_WINDOW")
PROCUREMENT_HEADS = (
    "HIRE", "BUY_LAND",
    *(f"BUY_SEED:{item}" for item in space.CROPS),
    "BUY_PRODUCT:WHEAT", "BUY_PRODUCT:FERTILIZER",
    *(f"BUY_ANIMAL:{item}" for item in space.ANIMALS),
)
SELL_HEADS = tuple(f"SELL:{item}" for item in space.PRODUCTS)
TRANSACTION_HEADS = PROCUREMENT_HEADS + SELL_HEADS
HEAD_INDEX = {name: index for index, name in enumerate(TRANSACTION_HEADS)}
QUANTITY_TIERS = (0, 1, 2, 3, 5, 10, 25, 50, 100)


def quantity_index(value: int) -> int:
    clipped = max(0, min(100, int(value)))
    return min(range(len(QUANTITY_TIERS)), key=lambda index: (abs(QUANTITY_TIERS[index] - clipped), index))


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


def aggregate(tokens: np.ndarray, quantities: np.ndarray, *, allow: set[str]) -> np.ndarray:
    result = np.zeros(len(TRANSACTION_HEADS), np.int16)
    for token, quantity in zip(tokens.reshape(-1), quantities.reshape(-1)):
        name = space.MARKET_TOKENS[int(token)]
        if name == "STOP" or name not in allow or name not in HEAD_INDEX:
            continue
        amount = 1 if name in {"HIRE", "BUY_LAND"} else max(1, int(quantity))
        index = HEAD_INDEX[name]
        result[index] = min(100, int(result[index]) + amount)
    return result


def build(sources: list[Path], output: Path, manifest_path: Path) -> dict:
    started = time.time()
    rows = {key: [] for key in (
        "global", "board", "event_type", "presence", "quantity_tier",
        "quantity_raw", "split", "episode", "step", "seat", "source",
    )}
    event_counts = Counter()
    positive_counts = Counter()
    for source_index, path in enumerate(sources):
        with np.load(path, allow_pickle=False) as archive:
            data = {
                key: np.asarray(archive[key])
                for key in (
                    "global", "board", "market_tokens", "market_quantities",
                    "episode", "step", "split", "seat",
                )
            }
            episodes = np.asarray(data["episode"])
            for identity in np.unique(episodes):
                selected = np.flatnonzero(episodes == identity)
                selected = selected[np.argsort(data["step"][selected], kind="stable")]
                step_to_index = {int(data["step"][index]): int(index) for index in selected}
                split = int(data["split"][selected[0]])
                seat = int(data["seat"][selected[0]])

                def append(index: int, event_type: int, quantity: np.ndarray) -> None:
                    rows["global"].append(np.asarray(data["global"][index, :60], np.float16))
                    rows["board"].append(np.asarray(data["board"][index], np.float16))
                    rows["event_type"].append(event_type)
                    rows["presence"].append(quantity > 0)
                    rows["quantity_tier"].append(np.asarray([quantity_index(value) for value in quantity], np.int8))
                    rows["quantity_raw"].append(quantity)
                    rows["split"].append(split)
                    rows["episode"].append(identity)
                    rows["step"].append(int(data["step"][index]))
                    rows["seat"].append(seat)
                    rows["source"].append(source_index)
                    event_counts[EVENT_TYPES[event_type]] += 1
                    for head_index in np.flatnonzero(quantity > 0):
                        positive_counts[TRANSACTION_HEADS[int(head_index)]] += 1

                for day in range(30):
                    start = day * 24
                    if start not in step_to_index:
                        continue
                    day_indices = [step_to_index[step] for step in range(start, min(start + 24, 719)) if step in step_to_index]
                    quantity = aggregate(
                        np.asarray(data["market_tokens"])[day_indices],
                        np.asarray(data["market_quantities"])[day_indices],
                        allow=set(PROCUREMENT_HEADS),
                    )
                    append(step_to_index[start], 0, quantity)

                previous_sell_signature = None
                for index in selected:
                    quantity = aggregate(
                        np.asarray(data["market_tokens"])[index:index + 1],
                        np.asarray(data["market_quantities"])[index:index + 1],
                        allow=set(SELL_HEADS),
                    )
                    signature = tuple(int(value > 0) for value in quantity[len(PROCUREMENT_HEADS):])
                    if not any(signature):
                        previous_sell_signature = None
                        continue
                    # One event per contiguous product-signature run; the ledger owns repetition.
                    if signature != previous_sell_signature:
                        append(int(index), 1, quantity)
                    previous_sell_signature = signature

                terminal_step = 671
                if terminal_step in step_to_index:
                    terminal_indices = [step_to_index[step] for step in range(terminal_step, 719) if step in step_to_index]
                    quantity = aggregate(
                        np.asarray(data["market_tokens"])[terminal_indices],
                        np.asarray(data["market_quantities"])[terminal_indices],
                        allow=set(SELL_HEADS),
                    )
                    append(step_to_index[terminal_step], 2, quantity)

    arrays = {key: np.asarray(value) for key, value in rows.items()}
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
    _atomic_npz(output, arrays)
    manifest = {
        "schema": "kaggriculture-v114-v12-event-market-dataset-v1",
        "status": "OFFLINE_EVENT_DATA_ONLY_NOT_G2_NOT_FOUNDATION_NOT_GOLD",
        "sources": [str(path.resolve()) for path in sources],
        "source_sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in sources],
        "output": str(output.resolve()),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "rows": len(arrays["split"]),
        "event_types": EVENT_TYPES,
        "transaction_heads": TRANSACTION_HEADS,
        "quantity_tiers": QUANTITY_TIERS,
        "event_counts": dict(event_counts),
        "positive_counts": dict(positive_counts),
        "split_rows": {
            name: int(np.sum(arrays["split"] == value))
            for name, value in (("train", 0), ("development", 1), ("blind", 2))
        },
        "teacher_identity_model_input": False,
        "history_features_model_input": False,
        "historical_agent_online_action_source": False,
        "strategy_parent": None,
        "blind_split_accessed_for_metrics_or_selection": False,
        "elapsed_seconds": time.time() - started,
    }
    _atomic_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.source, args.output, args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
