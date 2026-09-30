"""Relabel arbitrary Replay clusters into V113's stable day-level expert contract."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile

import numpy as np

import action_space as space


EXPERT_NAMES = {
    0: "crop_production",
    1: "animal_production",
    2: "logistics_maintenance",
    3: "market_realization",
    4: "capital_expansion_defense",
    5: "terminal_liquidation",
}


def row_votes(unit_tokens: np.ndarray, market_tokens: np.ndarray, market_mask: np.ndarray, step: int) -> Counter:
    """Count functional evidence without treating PASS/STOP as strategy."""
    votes: Counter = Counter()
    if int(step) >= 672:
        votes[5] += 100
    for token in unit_tokens:
        op = space.UNIT_TOKENS[int(token)].split(":", 1)[0]
        if op in {"PLANT", "WATER", "HARVEST", "FERTILIZE"}:
            votes[0] += 3.0
        elif op in {"FEED", "CARE", "COLLECT_FERTILIZER", "BUILD_COOP", "BUILD_PASTURE"}:
            votes[1] += 3.0
        elif op in {"PICKUP", "PLACE", "DROP", "DIG"}:
            votes[2] += 1.0
        elif op in space.MOVES:
            # Movement is present in almost every productive day.  It is weak
            # evidence for a logistics regime, not a vote equal to production.
            votes[2] += 0.05
    for token, active in zip(market_tokens, market_mask):
        if not active:
            continue
        name = space.MARKET_TOKENS[int(token)]
        op = name.split(":", 1)[0]
        if op == "SELL":
            votes[3] += 3.0
        elif op == "BUY_ANIMAL":
            votes[1] += 3.0
        elif op in {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT"}:
            votes[4] += 2.0
    return votes


def semantic_labels(data: dict[str, np.ndarray]) -> tuple[np.ndarray, dict]:
    required = {"episode", "seat", "step", "unit_tokens", "market_tokens", "market_mask"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"dataset missing relabel keys: {sorted(missing)}")
    grouped: dict[tuple[int, int, int], Counter] = defaultdict(Counter)
    row_keys = []
    for index in range(len(data["step"])):
        step = int(data["step"][index])
        key = (int(data["episode"][index]), int(data["seat"][index]), step // 24)
        grouped[key].update(row_votes(
            data["unit_tokens"][index], data["market_tokens"][index],
            data["market_mask"][index], step,
        ))
        row_keys.append(key)
    day_labels = {}
    day_votes = {}
    for key, votes in grouped.items():
        # Stable tie break follows the long-horizon production chain.  A day
        # with no functional action is capital preservation rather than an
        # invented production expert.
        label = max(range(6), key=lambda candidate: (votes[candidate], -candidate)) if votes else 4
        if not votes or votes[label] == 0:
            label = 4
        day_labels[key] = label
        day_votes[key] = {str(k): float(v) for k, v in sorted(votes.items())}
    labels = np.asarray([day_labels[key] for key in row_keys], dtype=np.int16)
    metadata = {
        "schema": "kaggriculture-v113-semantic-expert-relabel-v1",
        "expert_contract": {str(key): value for key, value in EXPERT_NAMES.items()},
        "rows": int(len(labels)),
        "days": int(len(day_labels)),
        "row_counts": {str(key): int(np.sum(labels == key)) for key in range(6)},
        "day_counts": {str(key): int(sum(label == key for label in day_labels.values())) for key in range(6)},
        "day_votes": {"/".join(map(str, key)): value for key, value in day_votes.items()},
    }
    return labels, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.dataset) as archive:
        data = {key: archive[key] for key in archive.files}
    old_counts = np.bincount(data["expert"], minlength=6).astype(int).tolist() if "expert" in data else None
    labels, metadata = semantic_labels(data)
    data["expert"] = labels
    metadata["source"] = str(args.dataset)
    metadata["source_expert_row_counts"] = old_counts
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **data)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    args.output.with_suffix(".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: metadata[key] for key in ("rows", "days", "row_counts", "day_counts")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
