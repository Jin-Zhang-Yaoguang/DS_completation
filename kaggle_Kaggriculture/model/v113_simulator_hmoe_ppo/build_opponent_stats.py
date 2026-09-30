#!/usr/bin/env python3
"""Build reproducible PFSP/learning-progress statistics from league reports."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iteration", type=int, required=True)
    args = parser.parse_args()
    previous = (
        json.loads(args.previous.read_text(encoding="utf-8")).get("members", {})
        if args.previous else {}
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    source_schemas = []
    for path in args.report:
        report = json.loads(path.read_text(encoding="utf-8"))
        source_schemas.append(report.get("schema"))
        for row in report["rows"]:
            member = row.get("opponent_member_id")
            if member:
                grouped[member].append(row)
    members = {}
    for member, rows in sorted(grouped.items()):
        score = float(np.mean([row["score"] for row in rows]))
        prior_score = previous.get(member, {}).get("candidate_score_rate")
        members[member] = {
            "games": len(rows),
            "candidate_score_rate": score,
            "mean_candidate_reward": float(np.mean([row["candidate_reward"] for row in rows])),
            "mean_margin": float(np.mean([row["margin"] for row in rows])),
            "catastrophe_rate_reward_lt_3000": float(
                np.mean([row["candidate_reward"] < 3000 for row in rows])
            ),
            "absolute_learning_progress": (
                float(abs(score - float(prior_score))) if prior_score is not None else 0.0
            ),
        }
    result = {
        "schema": "kaggriculture-v113-opponent-stats-v1",
        "iteration": args.iteration,
        "sources": [str(path) for path in args.report],
        "source_schemas": source_schemas,
        "members": members,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
