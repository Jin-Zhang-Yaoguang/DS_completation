"""Fresh-seed dual-seat screen for V114's fixed high-level nested options."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import statistics
import sys
import tempfile


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

from evaluate_bc_closed_loop import resolve_opponent, score  # noqa: E402
from policy_nested_hmoe import NestedOptionRolePolicy  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


def evaluate_seed(
    checkpoint: str, option_id: int, seed: int, opponent_id: str,
    worker_cap: int, cash_reserve: float, terminal_buy_cutoff: int,
):
    from kaggle_environments import make

    rows = []
    for seat in (0, 1):
        candidate = NestedOptionRolePolicy(
            Path(checkpoint), option_id,
            worker_cap=None if worker_cap < 0 else worker_cap,
            cash_reserve=cash_reserve,
            terminal_buy_cutoff=None if terminal_buy_cutoff < 0 else terminal_buy_cutoff,
        )
        opponent = resolve_opponent(opponent_id, f"v114_nested_{option_id}_{seed}_{seat}")
        agents = [None, None]
        agents[seat], agents[1 - seat] = candidate, opponent
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        error = None
        try:
            env.run(agents)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        margin = rewards[seat] - rewards[1 - seat]
        rows.append({
            "option_id": option_id,
            "seed": seed,
            "seat": seat,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "statuses": statuses,
            "error": error,
            "unit_role_usage": dict(candidate.unit_expert_usage),
            "market_role_usage": dict(candidate.market_expert_usage),
            "operation_counts": dict(candidate.operation_counts),
        })
    return rows


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
    parser.add_argument("--options", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--worker-cap", type=int, default=4)
    parser.add_argument("--cash-reserve", type=float, default=0.0)
    parser.add_argument("--terminal-buy-cutoff", type=int, default=672)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    ledger = SeedLedger(args.ledger)
    for seed in seeds:
        ledger.reserve(
            seed, split="train", campaign_id=args.campaign,
            opponent_id=args.opponent,
            registry_sha256="v114-fixed-opponent-" + args.opponent,
        )
    jobs = [(option_id, seed) for option_id in args.options for seed in seeds]
    rows = []
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs))) as pool:
        futures = {
            pool.submit(
                evaluate_seed, str(args.checkpoint), option_id, seed, args.opponent,
                args.worker_cap, args.cash_reserve, args.terminal_buy_cutoff,
            ): (option_id, seed)
            for option_id, seed in jobs
        }
        for future in as_completed(futures):
            result = future.result()
            rows.extend(result)
            option_id, seed = futures[future]
            print(json.dumps({
                "completed": [option_id, seed], "games": len(result)
            }, ensure_ascii=False), flush=True)
    ledger.mark_schedule_exposed([{"seed": seed} for seed in seeds])

    summaries = []
    for option_id in args.options:
        selected = [row for row in rows if row["option_id"] == option_id]
        valid = [row for row in selected if row["error"] is None and row["statuses"] == ["DONE", "DONE"]]
        rewards = sorted(row["candidate_reward"] for row in valid)
        p10 = rewards[max(0, min(len(rewards) - 1, int(0.1 * max(0, len(rewards) - 1))))] if rewards else 0.0
        summaries.append({
            "option_id": option_id,
            "games": len(selected),
            "valid_games": len(valid),
            "wins": sum(row["score"] == 1.0 for row in valid),
            "draws": sum(row["score"] == 0.5 for row in valid),
            "losses": sum(row["score"] == 0.0 for row in valid),
            "score_rate": statistics.mean(row["score"] for row in valid) if valid else 0.0,
            "mean_candidate_reward": statistics.mean(row["candidate_reward"] for row in valid) if valid else 0.0,
            "p10_candidate_reward": p10,
            "mean_margin": statistics.mean(row["margin"] for row in valid) if valid else 0.0,
            "catastrophe_games": sum(row["candidate_reward"] < 3000 for row in valid),
            "errors": len(selected) - len(valid),
        })
    summaries.sort(key=lambda row: (
        row["catastrophe_games"], -row["score_rate"],
        -row["p10_candidate_reward"], -row["mean_candidate_reward"]
    ))
    report = {
        "schema": "kaggriculture-v114-nested-option-screen-v1",
        "checkpoint": str(args.checkpoint),
        "campaign": args.campaign,
        "seed_start": args.seed_start,
        "seed_blocks": args.seeds,
        "opponent": args.opponent,
        "candidate_safety": {
            "worker_cap": args.worker_cap,
            "cash_reserve": args.cash_reserve,
            "terminal_buy_cutoff": args.terminal_buy_cutoff,
        },
        "summaries": summaries,
        "best": summaries[0],
        "rows": sorted(rows, key=lambda row: (row["option_id"], row["seed"], row["seat"])),
    }
    atomic_json(args.output, report)
    print(json.dumps({"best": report["best"], "summaries": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
