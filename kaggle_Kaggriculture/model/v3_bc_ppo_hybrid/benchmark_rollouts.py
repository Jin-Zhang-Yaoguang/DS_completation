"""Benchmark local Kaggriculture rollout throughput at several worker counts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from train_ppo import collect_rollouts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=64)
    parser.add_argument("--workers", type=int, nargs="+", default=[8, 12, 16])
    parser.add_argument("--weights", type=Path, default=Path("policy_weights.npz"))
    args = parser.parse_args()

    for worker_count in args.workers:
        _, seconds = collect_rollouts(
            args.weights,
            args.episodes,
            worker_count,
            51,
            0.995,
            0.95,
            [],
        )
        print(
            json.dumps(
                {
                    "workers": worker_count,
                    "episodes": args.episodes,
                    "seconds": round(seconds, 3),
                    "episodes_per_second": round(args.episodes / seconds, 3),
                }
            )
        )


if __name__ == "__main__":
    main()
