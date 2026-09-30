"""Measure whether a fixed-expert grid contains learnable Router support."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

import numpy as np


def bootstrap_ci(values: np.ndarray, seed: int, samples: int = 100_000) -> list[float]:
    rng = np.random.default_rng(seed)
    means = values[rng.integers(0, len(values), (samples, len(values)))].mean(axis=1)
    return [float(value) for value in np.quantile(means, (0.025, 0.975))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--label", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=113)
    args = parser.parse_args()
    if len(args.input) != len(args.label):
        parser.error("--input and --label must have equal length")

    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.input]
    indexed = []
    for report in reports:
        rows = {(int(row["seed"]), int(row["seat"])): row for row in report["rows"]}
        indexed.append(rows)
    keys = set(indexed[0])
    if any(set(rows) != keys for rows in indexed[1:]):
        raise ValueError("expert grid reports do not share an identical seed/seat panel")
    ordered_keys = sorted(keys)

    metrics = {}
    for metric_index, metric in enumerate(("candidate_reward", "margin")):
        matrix = np.asarray([
            [float(rows[key][metric]) for key in ordered_keys] for rows in indexed
        ])
        fixed_means = matrix.mean(axis=1)
        best_fixed_index = int(np.argmax(fixed_means))
        oracle_indices = np.argmax(matrix, axis=0)
        oracle = matrix[oracle_indices, np.arange(matrix.shape[1])]
        gain = oracle - matrix[best_fixed_index]
        metrics[metric] = {
            "fixed_mean": {
                label: float(value) for label, value in zip(args.label, fixed_means)
            },
            "best_fixed": args.label[best_fixed_index],
            "best_fixed_mean": float(fixed_means[best_fixed_index]),
            "oracle_mean": float(oracle.mean()),
            "oracle_gain_mean": float(gain.mean()),
            "oracle_gain_ci95": bootstrap_ci(gain, args.seed + metric_index),
            "oracle_gain_wins_ties_losses": [
                int(np.sum(gain > 0)), int(np.sum(gain == 0)), int(np.sum(gain < 0))
            ],
            "oracle_winner_count": dict(Counter(args.label[index] for index in oracle_indices)),
            "distinct_row_outcomes": int(sum(len(set(matrix[:, column])) > 1 for column in range(matrix.shape[1]))),
        }

    result = {
        "schema": "kaggriculture-v113-expert-grid-support-v1",
        "inputs": [str(path) for path in args.input],
        "labels": args.label,
        "rows": len(ordered_keys),
        "metrics": metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as sink:
        json.dump(result, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
