"""Summarize a closed-loop V114 lineage foundation engineering screen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import tempfile


CATASTROPHE_REWARD = 3000.0


def percentile_10(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[int(0.10 * (len(ordered) - 1))])


def summarize(report: dict, candidate_id: str) -> dict:
    rows = list(report.get("rows") or [])
    valid = [
        row for row in rows
        if row.get("error") is None
        and row.get("statuses") == ["DONE", "DONE"]
        and int(row.get("steps", 0)) == 720
    ]
    rewards = [float(row["candidate_reward"]) for row in valid]
    wins = sum(float(row["score"]) == 1.0 for row in valid)
    draws = sum(float(row["score"]) == 0.5 for row in valid)
    losses = sum(float(row["score"]) == 0.0 for row in valid)
    score_rate = statistics.mean(float(row["score"]) for row in valid) if valid else 0.0
    p10 = percentile_10(rewards)
    catastrophes = sum(value < CATASTROPHE_REWARD for value in rewards)
    checks = {
        "all_games_valid": len(valid) == len(rows) and len(rows) > 0,
        "score_rate_at_least_75pct": score_rate >= 0.75,
        "p10_reward_at_least_3000": p10 >= CATASTROPHE_REWARD,
        "catastrophe_games_at_most_1": catastrophes <= 1,
    }
    return {
        "schema": "kaggriculture-v114-lineage-foundation-screen-v1",
        "candidate_id": candidate_id,
        "status": "PASS_ENGINEERING_SCREEN" if all(checks.values()) else "FAIL_ENGINEERING_SCREEN",
        "fresh_evidence": False,
        "checks": checks,
        "games": len(rows),
        "valid_games": len(valid),
        "wins_draws_losses": [wins, draws, losses],
        "score_rate": score_rate,
        "mean_candidate_reward": statistics.mean(rewards) if rewards else 0.0,
        "p10_candidate_reward": p10,
        "catastrophe_games": catastrophes,
        "mean_margin": statistics.mean(float(row["margin"]) for row in valid) if valid else 0.0,
        "qualification_status": "SCREEN_ONLY_NOT_FOUNDATION_NOT_GOLD",
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")), args.candidate_id)
    atomic_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
