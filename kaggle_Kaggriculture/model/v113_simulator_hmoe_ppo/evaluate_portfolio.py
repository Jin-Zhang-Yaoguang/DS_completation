"""Evaluate V113's multi-checkpoint Product MoE with paired seats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import tempfile
import time

from kaggle_environments import make

from evaluate_bc_closed_loop import resolve_opponent, score
from policy_portfolio import FactorizedPortfolioPolicy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--router-checkpoint", type=Path, required=True)
    parser.add_argument("--specialist", action="append", required=True, help="EXPERT=CHECKPOINT")
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1146000)
    parser.add_argument("--router-period", type=int, default=720)
    parser.add_argument("--forced-expert", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    specialists = {}
    for value in args.specialist:
        expert, path = value.split("=", 1)
        specialists[int(expert)] = Path(path)
    started = time.time()
    rows = []
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            candidate = FactorizedPortfolioPolicy(
                args.router_checkpoint, specialists, router_period=args.router_period,
                forced_expert=args.forced_expert,
            )
            opponent = resolve_opponent(args.opponent, f"v113_portfolio_opponent_{seed}_{seat}")
            agents = [None, None]
            agents[seat] = candidate
            agents[1 - seat] = opponent
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            error = None
            try:
                env.run(agents)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            rewards = [float(state.reward or 0.0) for state in env.state]
            statuses = [str(state.status) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            row = {
                "seed": seed, "seat": seat, "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat], "margin": margin,
                "score": score(margin), "statuses": statuses, "error": error,
                "expert_usage": dict(candidate.expert_usage),
                "operation_counts": dict(candidate.operation_counts),
            }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    valid = [row for row in rows if row["error"] is None and row["statuses"] == ["DONE", "DONE"]]
    report = {
        "schema": "kaggriculture-v113-specialist-portfolio-v1", "games": len(rows),
        "done_done": len(valid),
        "score_rate": statistics.mean(row["score"] for row in valid) if valid else 0.0,
        "mean_candidate_reward": statistics.mean(row["candidate_reward"] for row in valid) if valid else 0.0,
        "mean_margin": statistics.mean(row["margin"] for row in valid) if valid else 0.0,
        "elapsed_seconds": time.time() - started, "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as sink:
        json.dump(report, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps({key: report[key] for key in (
        "games", "done_done", "score_rate", "mean_candidate_reward", "mean_margin", "elapsed_seconds"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
