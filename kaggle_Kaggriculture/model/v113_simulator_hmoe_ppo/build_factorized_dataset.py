"""Add independent production-day and market-turn expert labels to a V113 shard."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile

import numpy as np

import action_space as space


UNIT_EXPERTS = {
    0: "wheat_production",
    1: "carrot_production",
    2: "tomato_production",
    3: "strawberry_production",
    4: "melon_production",
    5: "animal_production",
}
MARKET_EXPERTS = {
    0: "wheat_controller",
    1: "carrot_controller",
    2: "tomato_controller",
    3: "strawberry_controller",
    4: "melon_controller",
    5: "animal_byproduct_controller",
}

PRODUCT_EXPERT = {crop: index for index, crop in enumerate(space.CROPS)}
PRODUCT_EXPERT.update({item: 5 for item in (*space.ANIMALS, "FERTILIZER", "MILK", "WOOL", "EGG")})


def unit_votes(tokens: np.ndarray, step: int) -> Counter:
    votes: Counter = Counter()
    for token in tokens:
        name = space.UNIT_TOKENS[int(token)]
        op, _, item = name.partition(":")
        if op == "PLANT" and item in space.CROPS:
            votes[PRODUCT_EXPERT[item]] += 3.0
        elif op in {"BUILD_COOP", "BUILD_PASTURE"}:
            votes[5] += 3.0
    return votes


def market_votes(tokens: np.ndarray, mask: np.ndarray) -> Counter:
    votes: Counter = Counter()
    for token, active in zip(tokens, mask):
        if not active:
            continue
        _, _, item = space.MARKET_TOKENS[int(token)].partition(":")
        if item in PRODUCT_EXPERT:
            votes[PRODUCT_EXPERT[item]] += 1
    return votes


def production_market_votes(tokens: np.ndarray, mask: np.ndarray) -> Counter:
    votes: Counter = Counter()
    for token, active in zip(tokens, mask):
        if not active:
            continue
        name = space.MARKET_TOKENS[int(token)]
        op, _, item = name.partition(":")
        if op == "BUY_SEED" and item in space.CROPS:
            votes[PRODUCT_EXPERT[item]] += 3.0
        elif op == "BUY_ANIMAL":
            votes[5] += 3.0
    return votes


def factorized_labels(data: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, dict]:
    required = {"episode", "seat", "step", "unit_tokens", "market_tokens", "market_mask"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"dataset missing factorization keys: {sorted(missing)}")
    grouped: dict[tuple[int, int, int], Counter] = defaultdict(Counter)
    row_keys = []
    for index, step_value in enumerate(data["step"]):
        step = int(step_value)
        key = (int(data["episode"][index]), int(data["seat"][index]), step // 24)
        grouped[key].update(unit_votes(data["unit_tokens"][index], step))
        grouped[key].update(production_market_votes(data["market_tokens"][index], data["market_mask"][index]))
        row_keys.append(key)
    day_labels = {}
    series = defaultdict(list)
    for key in grouped:
        series[key[:2]].append(key)
    for identity, keys in series.items():
        previous = 0
        for key in sorted(keys, key=lambda value: value[2]):
            votes = grouped[key]
            if votes:
                previous = max(range(6), key=lambda candidate: (votes[candidate], -candidate))
            day_labels[key] = previous
    unit_expert = np.asarray([day_labels[key] for key in row_keys], dtype=np.int16)
    market_labels = []
    for index, fallback in enumerate(unit_expert):
        votes = market_votes(data["market_tokens"][index], data["market_mask"][index])
        market_labels.append(max(range(6), key=lambda candidate: (votes[candidate], -candidate)) if votes else int(fallback))
    market_expert = np.asarray(market_labels, dtype=np.int16)
    metadata = {
        "schema": "kaggriculture-v113-factorized-dataset-v1",
        "unit_expert_contract": {str(key): value for key, value in UNIT_EXPERTS.items()},
        "market_expert_contract": {str(key): value for key, value in MARKET_EXPERTS.items()},
        "rows": int(len(unit_expert)),
        "days": int(len(day_labels)),
        "unit_expert_rows": {str(key): int(np.sum(unit_expert == key)) for key in range(6)},
        "market_expert_rows": {str(key): int(np.sum(market_expert == key)) for key in range(6)},
    }
    return unit_expert, market_expert, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force-expert", type=int, choices=range(6))
    args = parser.parse_args()
    with np.load(args.dataset) as archive:
        data = {key: archive[key] for key in archive.files}
    unit_expert, market_expert, metadata = factorized_labels(data)
    if args.force_expert is not None:
        unit_expert[:] = args.force_expert
        market_expert[:] = args.force_expert
        metadata["forced_expert"] = args.force_expert
        metadata["unit_expert_rows"] = {
            str(key): int(np.sum(unit_expert == key)) for key in range(6)
        }
        metadata["market_expert_rows"] = {
            str(key): int(np.sum(market_expert == key)) for key in range(6)
        }
    data["unit_expert"] = unit_expert
    data["market_expert"] = market_expert
    metadata["source"] = str(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **data)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    args.output.with_suffix(".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
