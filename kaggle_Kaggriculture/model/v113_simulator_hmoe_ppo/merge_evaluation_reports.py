#!/usr/bin/env python3
"""Merge disjoint fixed-opponent evaluation report shards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.input]
    rows = sorted(
        [row for report in reports for row in report["rows"]],
        key=lambda row: (int(row["seed"]), int(row["seat"])),
    )
    keys = [(int(row["seed"]), int(row["seat"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("evaluation shards overlap")
    if any(row["error"] is not None or row["statuses"] != ["DONE", "DONE"] for row in rows):
        raise ValueError("evaluation shard contains an abnormal game")
    result = {
        "schema": "kaggriculture-v113-factorized-closed-loop-merged-v1",
        "inputs": [str(path) for path in args.input],
        "games": len(rows),
        "done_done": len(rows),
        "score_rate": float(np.mean([row["score"] for row in rows])),
        "mean_candidate_reward": float(np.mean([row["candidate_reward"] for row in rows])),
        "mean_margin": float(np.mean([row["margin"] for row in rows])),
        "elapsed_seconds_sum": float(sum(report["elapsed_seconds"] for report in reports)),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
