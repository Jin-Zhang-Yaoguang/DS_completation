"""Fresh-seed paired-seat grid for V114 fixed production/market experts."""

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
from policy_v114 import V114StableExpertPolicy  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


def _evaluate_combo(
    checkpoint: str, unit_expert: int, market_expert: int, worker_cap: int,
    cash_reserve: float, terminal_buy_cutoff: int, seeds: list[int], opponent_id: str,
):
    from kaggle_environments import make

    rows = []
    for seed in seeds:
        for seat in (0, 1):
            candidate = V114StableExpertPolicy(
                Path(checkpoint), unit_expert, market_expert,
                worker_cap=None if worker_cap < 0 else worker_cap,
                cash_reserve=cash_reserve,
                terminal_buy_cutoff=None if terminal_buy_cutoff < 0 else terminal_buy_cutoff,
            )
            opponent = resolve_opponent(opponent_id, f"v114_grid_{unit_expert}_{market_expert}_{seed}_{seat}")
            agents = [None, None]
            agents[seat], agents[1 - seat] = candidate, opponent
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            error = None
            try:
                env.run(agents)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            rewards = [float(state.reward or 0) for state in env.state]
            statuses = [str(state.status) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            rows.append({
                "unit_expert": unit_expert,
                "market_expert": market_expert,
                "worker_cap": worker_cap,
                "cash_reserve": cash_reserve,
                "terminal_buy_cutoff": terminal_buy_cutoff,
                "seed": seed,
                "seat": seat,
                "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat],
                "margin": margin,
                "score": score(margin),
                "statuses": statuses,
                "error": error,
            })
    return rows


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--unit-experts", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--market-experts", type=int, nargs="+", default=[3, 4])
    parser.add_argument(
        "--expert-pairs", nargs="+",
        help="Explicit unit:market pairs; when set, disables the Cartesian expert grid.",
    )
    parser.add_argument("--worker-caps", type=int, nargs="+", default=[-1])
    parser.add_argument("--cash-reserves", type=float, nargs="+", default=[0.0])
    parser.add_argument("--terminal-buy-cutoffs", type=int, nargs="+", default=[-1])
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    ledger = SeedLedger(args.ledger)
    registry_sha = "v114-fixed-opponent-" + args.opponent
    for seed in seeds:
        ledger.reserve(
            seed, split="train", campaign_id=args.campaign,
            opponent_id=args.opponent, registry_sha256=registry_sha,
        )
    if args.expert_pairs:
        expert_pairs = []
        for raw in args.expert_pairs:
            try:
                unit, market = (int(value) for value in raw.split(":", 1))
            except (TypeError, ValueError) as exc:
                parser.error(f"invalid --expert-pairs value {raw!r}; expected UNIT:MARKET")
            expert_pairs.append((unit, market))
    else:
        expert_pairs = [
            (unit, market) for unit in args.unit_experts for market in args.market_experts
        ]
    combinations = [
        (unit, market, worker_cap, cash_reserve, cutoff)
        for unit, market in expert_pairs
        for worker_cap in args.worker_caps
        for cash_reserve in args.cash_reserves
        for cutoff in args.terminal_buy_cutoffs
    ]
    rows = []
    # One task owns both seats of one seed block.  This preserves the paired-seat
    # contract while allowing a single expert composition to use all CPU workers.
    jobs = [(*combination, seed) for combination in combinations for seed in seeds]
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs))) as pool:
        futures = {
            pool.submit(
                _evaluate_combo, str(args.checkpoint), unit, market, worker_cap,
                cash_reserve, cutoff, [seed], args.opponent
            ): (unit, market, worker_cap, cash_reserve, cutoff, seed)
            for unit, market, worker_cap, cash_reserve, cutoff, seed in jobs
        }
        for future in as_completed(futures):
            result = future.result()
            rows.extend(result)
            unit, market, worker_cap, cash_reserve, cutoff, seed = futures[future]
            print(json.dumps({
                "completed": [unit, market, worker_cap, cash_reserve, cutoff, seed],
                "games": len(result)
            }, ensure_ascii=False), flush=True)
    ledger.mark_schedule_exposed([{"seed": seed} for seed in seeds])
    summaries = []
    for unit, market, worker_cap, cash_reserve, cutoff in combinations:
        selected = [
            row for row in rows
            if row["unit_expert"] == unit
            and row["market_expert"] == market
            and row["worker_cap"] == worker_cap
            and row["cash_reserve"] == cash_reserve
            and row["terminal_buy_cutoff"] == cutoff
        ]
        valid = [row for row in selected if row["error"] is None and row["statuses"] == ["DONE", "DONE"]]
        rewards = sorted(row["candidate_reward"] for row in valid)
        p10_index = max(0, min(len(rewards) - 1, int(0.1 * max(0, len(rewards) - 1)))) if rewards else 0
        summaries.append({
            "unit_expert": unit,
            "market_expert": market,
            "worker_cap": worker_cap,
            "cash_reserve": cash_reserve,
            "terminal_buy_cutoff": cutoff,
            "games": len(selected),
            "valid_games": len(valid),
            "score_rate": statistics.mean(row["score"] for row in valid) if valid else 0.0,
            "mean_candidate_reward": statistics.mean(row["candidate_reward"] for row in valid) if valid else 0.0,
            "p10_candidate_reward": rewards[p10_index] if rewards else 0.0,
            "mean_margin": statistics.mean(row["margin"] for row in valid) if valid else 0.0,
            "catastrophe_games": sum(row["candidate_reward"] < 3000 for row in valid),
        })
    summaries.sort(key=lambda row: (
        row["catastrophe_games"], -row["score_rate"],
        -row["p10_candidate_reward"], -row["mean_candidate_reward"], -row["mean_margin"]
    ))
    report = {
        "schema": "kaggriculture-v114-expert-grid-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "checkpoint": str(args.checkpoint),
        "campaign": args.campaign,
        "seed_start": args.seed_start,
        "seed_blocks": args.seeds,
        "games_per_combo": args.seeds * 2,
        "opponent": args.opponent,
        "summaries": summaries,
        "best": summaries[0],
        "rows": sorted(rows, key=lambda row: (
            row["unit_expert"], row["market_expert"], row["worker_cap"],
            row["cash_reserve"], row["terminal_buy_cutoff"], row["seed"], row["seat"]
        )),
    }
    _atomic_json(args.output, report)
    print(json.dumps({"best": report["best"], "summaries": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
