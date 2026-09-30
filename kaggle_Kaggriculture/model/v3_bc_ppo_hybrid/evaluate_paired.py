"""Run a paired, both-seats evaluation of v3 against one named opponent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from evaluate import _bootstrap, _partition_seeds, _run_tasks


HERE = Path(__file__).resolve().parent


def evaluate_paired(weights: Path, opponent: str, seeds: int, workers: int) -> dict:
    seed_values = _partition_seeds(61000000, seeds)
    tasks = []
    for seed_index, seed in enumerate(seed_values):
        for seat in (0, 1):
            tasks.append((seed_index * 2 + seat, seed, seat, "v3", opponent))

    rows = _run_tasks(tasks, weights, workers)
    per_seed_scores = np.asarray(
        [
            np.mean([row["score"] for row in rows if row["seed"] == seed])
            for seed in seed_values
        ],
        dtype=np.float64,
    )

    def summarize(subset: list[dict]) -> dict:
        scores = np.asarray([row["score"] for row in subset], dtype=np.float64)
        margins = np.asarray([row["margin"] for row in subset], dtype=np.float64)
        return {
            "games": len(subset),
            "wins": int(np.sum(scores == 1.0)),
            "losses": int(np.sum(scores == 0.0)),
            "ties": int(np.sum(scores == 0.5)),
            "score_rate": float(np.mean(scores)),
            "mean_margin": float(np.mean(margins)),
            "median_margin": float(np.median(margins)),
            "mean_own_reward": float(np.mean([row["own"] for row in subset])),
            "mean_opponent_reward": float(np.mean([row["other"] for row in subset])),
        }

    return {
        "schema": "kaggriculture-v3-paired-evaluation-1",
        "candidate": "v3",
        "opponent": opponent,
        "weights": str(weights),
        "seeds": seeds,
        "seed_partition": "sha256(seed) mod 100 in [90, 100)",
        "both_seats": True,
        "overall": {
            **summarize(rows),
            "paired_bootstrap_95_ci": _bootstrap(per_seed_scores),
        },
        "by_seat": {
            str(seat): summarize([row for row in rows if row["seat"] == seat])
            for seat in (0, 1)
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, default=HERE / "policy_weights.npz")
    parser.add_argument("--opponent", choices=("v0", "v1", "v2", "starter", "random", "forced_low", "forced_high"), default="v1")
    parser.add_argument("--seeds", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = evaluate_paired(args.weights, args.opponent, args.seeds, args.workers)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
