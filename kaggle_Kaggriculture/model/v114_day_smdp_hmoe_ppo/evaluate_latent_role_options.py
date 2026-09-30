"""Fresh-seed, dual-seat closed-loop evaluation for V114 latent-role options."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Iterable


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

from evaluate_bc_closed_loop import resolve_opponent, score  # noqa: E402
from policy_latent_role_hmoe import (  # noqa: E402
    NUM_OPTIONS,
    LatentRoleOptionPolicy,
)
from seed_ledger import SeedLedger  # noqa: E402


CATASTROPHE_REWARD = 3000.0


def percentile_10(values: Iterable[float]) -> float:
    """Empirical lower P10, stable for small screening samples."""

    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int(0.1 * (len(ordered) - 1))))
    return ordered[index]


def evaluate_seed(
    checkpoint: str,
    option_id: int,
    seed: int,
    opponent_id: str,
    worker_cap: int,
    cash_reserve: float,
    terminal_buy_cutoff: int,
):
    """Evaluate both seats of one seed block against the same opponent."""

    from kaggle_environments import make

    rows = []
    for seat in (0, 1):
        candidate = LatentRoleOptionPolicy(
            Path(checkpoint),
            option_id,
            worker_cap=None if worker_cap < 0 else worker_cap,
            cash_reserve=cash_reserve,
            terminal_buy_cutoff=(
                None if terminal_buy_cutoff < 0 else terminal_buy_cutoff
            ),
        )
        opponent = resolve_opponent(
            opponent_id, f"v114_latent_role_{option_id}_{seed}_{seat}"
        )
        agents = [None, None]
        agents[seat], agents[1 - seat] = candidate, opponent
        env = make(
            "kaggriculture", configuration={"seed": seed}, debug=False
        )
        error = None
        try:
            env.run(agents)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        margin = rewards[seat] - rewards[1 - seat]
        rows.append({
            "option_id": int(option_id),
            "seed": int(seed),
            "seat": int(seat),
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "statuses": statuses,
            "steps": len(env.steps),
            "error": error,
            "catastrophe": rewards[seat] < CATASTROPHE_REWARD,
            "option_usage": dict(candidate.option_usage),
            "unit_role_usage": dict(candidate.unit_role_usage),
            "market_role_usage": dict(candidate.market_role_usage),
            "operation_counts": dict(candidate.operation_counts),
            "nonpass_unit_orders": int(candidate.nonpass_unit_orders),
            "market_turns": int(candidate.market_turns),
            "ten_slot_market_turns": int(candidate.ten_slot_market_turns),
            "ten_slot_rate": float(candidate.ten_slot_rate),
            "market_sequence_lengths": dict(candidate.market_sequence_lengths),
        })
    return rows


def summarize_option(rows: list[dict], option_id: int) -> dict:
    selected = [row for row in rows if row["option_id"] == option_id]
    valid = [
        row for row in selected
        if row["error"] is None and row["statuses"] == ["DONE", "DONE"]
    ]
    wins = sum(row["score"] == 1.0 for row in valid)
    draws = sum(row["score"] == 0.5 for row in valid)
    losses = sum(row["score"] == 0.0 for row in valid)
    market_turns = sum(row["market_turns"] for row in valid)
    ten_slot_turns = sum(row["ten_slot_market_turns"] for row in valid)
    catastrophes = sum(bool(row["catastrophe"]) for row in valid)
    return {
        "option_id": int(option_id),
        "games": len(selected),
        "valid_games": len(valid),
        "wdl": {"wins": wins, "draws": draws, "losses": losses},
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "score_rate": (
            statistics.mean(row["score"] for row in valid) if valid else 0.0
        ),
        "mean_candidate_reward": (
            statistics.mean(row["candidate_reward"] for row in valid)
            if valid else 0.0
        ),
        "p10_candidate_reward": percentile_10(
            row["candidate_reward"] for row in valid
        ),
        "mean_opponent_reward": (
            statistics.mean(row["opponent_reward"] for row in valid)
            if valid else 0.0
        ),
        "mean_margin": (
            statistics.mean(row["margin"] for row in valid) if valid else 0.0
        ),
        "catastrophe_games": catastrophes,
        "catastrophe_rate": catastrophes / len(valid) if valid else 0.0,
        "market_turns": market_turns,
        "ten_slot_market_turns": ten_slot_turns,
        "ten_slot_rate": ten_slot_turns / market_turns if market_turns else 0.0,
        "errors": len(selected) - len(valid),
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def _default_registry_sha256(opponent: str) -> str:
    identity = json.dumps(
        {"opponent": opponent, "seat_contract": [0, 1]},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--options", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--worker-cap", type=int, default=-1)
    parser.add_argument("--cash-reserve", type=float, default=0.0)
    parser.add_argument("--terminal-buy-cutoff", type=int, default=-1)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--split", choices=("train", "dev", "blind"), default="train")
    parser.add_argument("--registry-sha256")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    options = [int(option) for option in args.options]
    if len(options) != len(set(options)):
        parser.error("--options may not contain duplicates")
    if any(option < 0 or option >= NUM_OPTIONS for option in options):
        parser.error(f"--options must be in [0, {NUM_OPTIONS})")
    if args.seeds <= 0:
        parser.error("--seeds must be positive")
    if args.workers <= 0:
        parser.error("--workers must be positive")
    if not args.checkpoint.is_file():
        parser.error("--checkpoint does not exist")

    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    registry_sha256 = (
        args.registry_sha256 or _default_registry_sha256(args.opponent)
    )
    ledger = SeedLedger(args.ledger)
    ledger.reserve_schedule(
        [
            {"seed": seed, "opponent_id": args.opponent}
            for seed in seeds
        ],
        split=args.split,
        campaign_id=args.campaign,
        registry_sha256=registry_sha256,
    )
    ledger_sha_before_exposure = ledger.sha256()

    started = time.time()
    jobs = [(option_id, seed) for option_id in options for seed in seeds]
    rows = []
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs))) as pool:
        futures = {
            pool.submit(
                evaluate_seed,
                str(args.checkpoint),
                option_id,
                seed,
                args.opponent,
                args.worker_cap,
                args.cash_reserve,
                args.terminal_buy_cutoff,
            ): (option_id, seed)
            for option_id, seed in jobs
        }
        for future in as_completed(futures):
            option_id, seed = futures[future]
            result = future.result()
            rows.extend(result)
            print(json.dumps({
                "completed": [option_id, seed], "games": len(result)
            }, ensure_ascii=False), flush=True)

    # Every scheduled seed was now disclosed to the candidate, including runs
    # ending in an engine or agent error, so all blocks become exposed.
    ledger.mark_schedule_exposed([{"seed": seed} for seed in seeds])
    ledger_sha_after_exposure = ledger.sha256()

    summaries = [summarize_option(rows, option_id) for option_id in options]
    summaries.sort(key=lambda row: (
        row["errors"],
        row["catastrophe_games"],
        -row["score_rate"],
        -row["p10_candidate_reward"],
        row["ten_slot_rate"],
        -row["mean_candidate_reward"],
    ))
    report = {
        "schema": "kaggriculture-v114-latent-role-option-screen-v1",
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": hashlib.sha256(
            args.checkpoint.read_bytes()
        ).hexdigest(),
        "campaign": args.campaign,
        "split": args.split,
        "seed_start": args.seed_start,
        "seed_blocks": args.seeds,
        "seats_per_seed": [0, 1],
        "fresh_seed_dual_seat": True,
        "opponent": args.opponent,
        "registry_sha256": registry_sha256,
        "seed_ledger": {
            "path": str(args.ledger),
            "sha256_after_reservation": ledger_sha_before_exposure,
            "sha256_after_exposure": ledger_sha_after_exposure,
            "reserved_seed_blocks": seeds,
        },
        "candidate_safety": {
            "worker_cap": None if args.worker_cap < 0 else args.worker_cap,
            "cash_reserve": args.cash_reserve,
            "terminal_buy_cutoff": (
                None if args.terminal_buy_cutoff < 0
                else args.terminal_buy_cutoff
            ),
        },
        "metric_contract": {
            "win": "candidate_reward > opponent_reward",
            "draw": "candidate_reward == opponent_reward",
            "loss": "candidate_reward < opponent_reward",
            "catastrophe": f"candidate_reward < {CATASTROPHE_REWARD:g}",
            "p10": "empirical lower P10 of valid candidate rewards",
            "ten_slot_rate": (
                "market decision turns with 10 successfully applied non-STOP "
                "orders / all candidate market decision turns"
            ),
        },
        "elapsed_seconds": time.time() - started,
        "summaries": summaries,
        "best": summaries[0],
        "rows": sorted(
            rows, key=lambda row: (row["option_id"], row["seed"], row["seat"])
        ),
    }
    atomic_json(args.output, report)
    print(json.dumps(
        {"best": report["best"], "summaries": summaries},
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
