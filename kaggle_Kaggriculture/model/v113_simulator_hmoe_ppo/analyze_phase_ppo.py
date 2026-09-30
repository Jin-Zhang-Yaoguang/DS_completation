"""Block-bootstrap paired phase PPO candidates by seed, preserving both seats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import numpy as np


def block_ci(seed_values: np.ndarray, seed: int, samples: int = 100_000):
    rng = np.random.default_rng(seed)
    means = seed_values[rng.integers(0, len(seed_values), (samples, len(seed_values)))].mean(axis=1)
    return [float(value) for value in np.quantile(means, (0.025, 0.975))]


def wtl(values: np.ndarray):
    return [int((values > 0).sum()), int((values == 0).sum()), int((values < 0).sum())]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, nargs="+", required=True)
    parser.add_argument("--label", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11325)
    args = parser.parse_args()
    if len(args.candidate) != len(args.label):
        parser.error("--candidate and --label must have equal length")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    base = {(int(row["seed"]), int(row["seat"])): row for row in baseline["rows"]}
    seeds = sorted({key[0] for key in base})
    if any((seed, seat) not in base for seed in seeds for seat in (0, 1)):
        raise ValueError("baseline is not a complete dual-seat seed panel")
    candidates = []
    for candidate_index, (label, path) in enumerate(zip(args.label, args.candidate)):
        report = json.loads(path.read_text(encoding="utf-8"))
        rows = {(int(row["seed"]), int(row["seat"])): row for row in report["rows"]}
        if set(rows) != set(base):
            raise ValueError(f"candidate {label} does not match baseline panel")
        metrics = {}
        for metric_index, metric in enumerate(("candidate_reward", "margin")):
            differences = np.asarray([
                float(rows[key][metric]) - float(base[key][metric]) for key in sorted(base)
            ])
            seed_differences = np.asarray([
                np.mean([float(rows[(seed, seat)][metric]) - float(base[(seed, seat)][metric]) for seat in (0, 1)])
                for seed in seeds
            ])
            metrics[metric] = {
                "candidate_mean": float(np.mean([rows[key][metric] for key in sorted(rows)])),
                "baseline_mean": float(np.mean([base[key][metric] for key in sorted(base)])),
                "paired_gain_mean": float(differences.mean()),
                "seed_block_bootstrap_ci95": block_ci(
                    seed_differences, args.seed + candidate_index * 7 + metric_index
                ),
                "seed_wins_ties_losses": wtl(seed_differences),
                "seat_row_wins_ties_losses": wtl(differences),
                "seed_paired_gains": dict(zip(map(str, seeds), map(float, seed_differences))),
            }
        candidates.append({
            "label": label, "report": str(path),
            "done_done": int(report["done_done"]), "score_rate": float(report["score_rate"]),
            "metrics": metrics,
        })
    result = {
        "schema": "kaggriculture-v113-phase-ppo-paired-seed-block-v1",
        "baseline": str(args.baseline), "seeds": len(seeds), "games": len(base),
        "candidates": candidates,
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
