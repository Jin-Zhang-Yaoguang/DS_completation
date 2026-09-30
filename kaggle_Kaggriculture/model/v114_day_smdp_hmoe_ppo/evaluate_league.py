"""Evaluate the frozen V114 responsibility policy on a registered mixed league."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import inspect
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
from opponent_factory import checkpoint_opponent  # noqa: E402
from opponent_registry import (  # noqa: E402
    SeedAssignment, build_schedule, load_registry, schedule_report,
)
from policy_v114 import V114StableExpertPolicy, with_observation_step  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


class StepEnrichedCheckpointOpponent:
    """Repair the official day/hour -> step adapter for frozen PPO-history policies."""

    def __init__(self, policy):
        self.policy = policy

    def __call__(self, obs, configuration=None):
        return self.policy(with_observation_step(obs), configuration)


def build_registered_opponent(registry: dict, opponent_id: str, unique_name: str):
    member = next(row for row in registry["members"] if row["id"] == opponent_id)
    if member["kind"] == "builtin":
        return resolve_opponent(member["spec"], unique_name)
    if member["kind"] == "agent":
        return resolve_opponent(member["resolved_path"], unique_name)
    if member["kind"] == "checkpoint":
        policy = checkpoint_opponent(
            Path(member["resolved_path"]), member["architecture"],
            member.get("forced_unit_expert"), member.get("forced_market_expert"),
            unit_expert_schedule=member.get("unit_expert_schedule"),
            market_expert_schedule=member.get("market_expert_schedule"),
        )
        return StepEnrichedCheckpointOpponent(policy)
    raise ValueError(f"unsupported opponent kind: {member['kind']}")


def call_agent(agent, obs, configuration):
    try:
        return agent(obs, configuration) if len(inspect.signature(agent).parameters) >= 2 else agent(obs)
    except (TypeError, ValueError):
        return agent(obs, configuration)


def evaluate_seed(
    checkpoint: str, registry_path: str, assignment: dict,
    unit_expert: int, market_expert: int, worker_cap: int,
    cash_reserve: float, terminal_buy_cutoff: int,
) -> list[dict]:
    from kaggle_environments import make

    registry = load_registry(Path(registry_path), verify_artifacts=True)
    rows = []
    seed = int(assignment["seed"])
    for seat in (0, 1):
        candidate = V114StableExpertPolicy(
            Path(checkpoint), unit_expert, market_expert,
            worker_cap=None if worker_cap < 0 else worker_cap,
            cash_reserve=cash_reserve,
            terminal_buy_cutoff=None if terminal_buy_cutoff < 0 else terminal_buy_cutoff,
        )
        opponent = build_registered_opponent(
            registry, assignment["opponent_id"], f"v114_league_{seed}_{seat}"
        )
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
            **assignment,
            "seat": seat,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "statuses": statuses,
            "error": error,
        })
    return rows


def summarise(rows: list[dict], key: str | None = None) -> dict | list[dict]:
    groups = {"pooled": rows} if key is None else defaultdict(list)
    if key is not None:
        for row in rows:
            groups[row[key]].append(row)
    result = []
    for name, selected in groups.items():
        valid = [row for row in selected if row["error"] is None and row["statuses"] == ["DONE", "DONE"]]
        rewards = sorted(row["candidate_reward"] for row in valid)
        p10 = rewards[max(0, min(len(rewards) - 1, int(0.1 * max(0, len(rewards) - 1))))] if rewards else 0.0
        result.append({
            "group": name,
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
    return result[0] if key is None else sorted(result, key=lambda row: row["group"])


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
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--stage", choices=("survival", "improvement", "final"), required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--pool-seed", type=int, required=True)
    parser.add_argument("--iteration", type=int, default=0)
    parser.add_argument("--unit-expert", type=int, default=0)
    parser.add_argument("--market-expert", type=int, default=1)
    parser.add_argument("--worker-cap", type=int, default=4)
    parser.add_argument("--cash-reserve", type=float, default=1250.0)
    parser.add_argument("--terminal-buy-cutoff", type=int, default=672)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    registry = load_registry(args.registry, verify_artifacts=True)
    schedule = build_schedule(
        registry, args.stage, args.seed_start, args.seeds,
        args.pool_seed, iteration=args.iteration,
    )
    schedule_meta = schedule_report(registry, args.stage, schedule)
    ledger = SeedLedger(args.ledger)
    for assignment in schedule:
        ledger.reserve(
            assignment.seed, split="train", campaign_id=args.campaign,
            opponent_id=assignment.opponent_id,
            registry_sha256=registry["registry_sha256"],
        )

    assignments = [assignment.__dict__ for assignment in schedule]
    rows = []
    with ProcessPoolExecutor(max_workers=min(args.workers, len(assignments))) as pool:
        futures = {
            pool.submit(
                evaluate_seed, str(args.checkpoint), str(args.registry), assignment,
                args.unit_expert, args.market_expert, args.worker_cap,
                args.cash_reserve, args.terminal_buy_cutoff,
            ): assignment
            for assignment in assignments
        }
        for future in as_completed(futures):
            result = future.result()
            rows.extend(result)
            assignment = futures[future]
            print(json.dumps({
                "completed": assignment["seed"],
                "layer": assignment["layer"],
                "opponent": assignment["opponent_id"],
                "games": len(result),
            }, ensure_ascii=False), flush=True)
    ledger.mark_schedule_exposed(assignments)

    report = {
        "schema": "kaggriculture-v114-league-evaluation-v1",
        "model_id": "v114_day_smdp_hmoe_ppo_responsibility_bc_v1",
        "checkpoint": str(args.checkpoint),
        "candidate_contract": {
            "unit_expert": args.unit_expert,
            "market_expert": args.market_expert,
            "worker_cap": args.worker_cap,
            "cash_reserve": args.cash_reserve,
            "terminal_buy_cutoff": args.terminal_buy_cutoff,
        },
        "campaign": args.campaign,
        "schedule": schedule_meta,
        "pooled": summarise(rows),
        "by_layer": summarise(rows, "layer"),
        "by_opponent": summarise(rows, "opponent_id"),
        "rows": sorted(rows, key=lambda row: (row["seed"], row["seat"])),
    }
    atomic_json(args.output, report)
    print(json.dumps({
        "pooled": report["pooled"],
        "by_layer": report["by_layer"],
        "by_opponent": report["by_opponent"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
