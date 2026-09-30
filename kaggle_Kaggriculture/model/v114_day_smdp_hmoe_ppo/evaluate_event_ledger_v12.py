"""Closed-loop engineering screen for V12 Event-Ledger compositions."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import statistics
import tempfile
import time

from evaluate_event_program import score
from policy_event_ledger_v12 import EventLedgerV12EngineeringPolicy


def run_game(
    checkpoint: str,
    market_checkpoint: str | None,
    contract: str | None,
    seed: int,
    seat: int,
) -> dict:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture.kaggriculture import starter_agent

    candidate = EventLedgerV12EngineeringPolicy(
        Path(checkpoint), Path(market_checkpoint) if market_checkpoint else None,
        contract=contract,
    )
    agents = [None, None]
    agents[seat], agents[1 - seat] = candidate, starter_agent
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    error = None
    try:
        env.run(agents)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    rewards = [float(state.reward or 0.0) for state in env.state]
    statuses = [str(state.status) for state in env.state]
    margin = rewards[seat] - rewards[1 - seat]
    return {
        "seed": seed, "seat": seat,
        "candidate_reward": rewards[seat], "opponent_reward": rewards[1 - seat],
        "margin": margin, "score": score(margin), "statuses": statuses,
        "steps": len(env.steps), "error": error, "audit": candidate.audit(),
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
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--market-checkpoint", type=Path)
    parser.add_argument("--contract", choices=("WHEAT_CASH", "MELON_CASH", "COW_DAIRY"))
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seed-blocks", type=int, default=4)
    parser.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    assignments = [
        (args.seed_start + offset, seat)
        for offset in range(args.seed_blocks) for seat in (0, 1)
    ]
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                run_game,
                str(args.checkpoint),
                str(args.market_checkpoint) if args.market_checkpoint else None,
                args.contract,
                seed,
                seat,
            ): (seed, seat)
            for seed, seat in assignments
        }
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    rows.sort(key=lambda row: (row["seed"], row["seat"]))
    valid = [
        row for row in rows
        if row["error"] is None and row["statuses"] == ["DONE", "DONE"] and row["steps"] == 720
    ]
    rewards = [row["candidate_reward"] for row in valid]
    report = {
        "schema": "kaggriculture-v114-v12-event-ledger-engineering-v1",
        "status": "ENGINEERING_DIAGNOSTIC_ONLY_NOT_G1_NOT_G2_NOT_FOUNDATION_NOT_GOLD",
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "market_checkpoint": str(args.market_checkpoint.resolve()) if args.market_checkpoint else None,
        "market_checkpoint_sha256": (
            hashlib.sha256(args.market_checkpoint.read_bytes()).hexdigest()
            if args.market_checkpoint else None
        ),
        "enterprise_contract": args.contract,
        "seed_start": args.seed_start,
        "seed_blocks": args.seed_blocks,
        "fresh_evidence": False,
        "games": len(rows), "valid_games": len(valid),
        "wins": sum(row["score"] == 1 for row in valid),
        "draws": sum(row["score"] == 0.5 for row in valid),
        "losses": sum(row["score"] == 0 for row in valid),
        "mean_reward": statistics.mean(rewards) if rewards else 0.0,
        "p10_reward": sorted(rewards)[int(0.1 * (len(rewards) - 1))] if rewards else 0.0,
        "catastrophe_games": sum(reward < 3000 for reward in rewards),
        "errors": len(rows) - len(valid),
        "mean_planner_calls": statistics.mean(
            row["audit"]["unit"]["planner_calls"] for row in valid
        ) if valid else 0.0,
        "mean_completed_tasks": statistics.mean(
            row["audit"]["unit"]["completed_tasks"] for row in valid
        ) if valid else 0.0,
        "mean_failed_tasks": statistics.mean(
            row["audit"]["unit"]["failed_tasks"] for row in valid
        ) if valid else 0.0,
        "unauthorized_market_turns": sum(
            row["audit"]["events"]["unauthorized_market_turns"] for row in valid
        ),
        "duplicate_commit_blocks": sum(
            row["audit"]["events"]["ledger"]["blocked_duplicate_emits"] for row in valid
        ),
        "rows": rows,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.output, report)
    print(json.dumps({key: report[key] for key in (
        "status", "wins", "draws", "losses", "mean_reward", "p10_reward",
        "catastrophe_games", "errors", "mean_planner_calls", "mean_completed_tasks",
        "mean_failed_tasks", "unauthorized_market_turns", "duplicate_commit_blocks",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
