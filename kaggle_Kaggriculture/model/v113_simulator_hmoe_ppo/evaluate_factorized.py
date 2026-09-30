"""Evaluate factorized V113 BC in the official engine with paired seats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import tempfile
import time

import numpy as np

from kaggle_environments import make

from evaluate_bc_closed_loop import resolve_opponent, score
import features
from opponent_factory import checkpoint_opponent
from opponent_pool import build_opponent, build_schedule, load_registry, schedule_report
from policy_factorized import FactorizedV113Policy
from policy_delayed_tree_router import DelayedTreeRouterPolicy
from policy_history_sequence import HistoryTimedSequenceActionV113Policy
from policy_market_memory_sequence import MarketMemoryTimedSequenceActionV113Policy
from policy_role_option import RoleOptionV113Policy
from policy_sequence_action import SequenceActionV113Policy, TimedSequenceActionV113Policy
from policy_staged_option import StagedOptionV113Policy


def parse_expert_schedule(value: str | None):
    if value is None:
        return None
    try:
        return tuple(
            (int(start), int(expert))
            for item in value.split(",")
            for start, expert in (item.split(":", 1),)
        )
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            "expert schedule must look like 0:3,72:4"
        ) from None


class RouterSnapshotPolicy:
    """Capture the exact encoded state seen before a delayed Router decision."""

    def __init__(self, policy, capture_step: int):
        self.policy = policy
        self.capture_step = int(capture_step)
        self.snapshot = None

    def __call__(self, obs, configuration=None):
        if int(obs.get("step", 0) or 0) == self.capture_step:
            self.snapshot = {
                key: np.asarray(value).tolist()
                for key, value in features.encode_observation(obs).items()
            }
        return self.policy(obs, configuration)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent")
    parser.add_argument("--opponent-checkpoint", type=Path)
    parser.add_argument("--opponent-registry", type=Path)
    parser.add_argument("--opponent-stats", type=Path)
    parser.add_argument("--opponent-pool-seed", type=int, default=113027)
    parser.add_argument("--iteration", type=int, default=0)
    parser.add_argument(
        "--opponent-architecture",
        choices=("factorized", "sequence", "timed-sequence", "history-timed-sequence"),
        default="timed-sequence",
    )
    parser.add_argument("--opponent-forced-unit-expert", type=int)
    parser.add_argument("--opponent-forced-market-expert", type=int)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1136500)
    parser.add_argument("--forced-unit-expert", type=int)
    parser.add_argument("--forced-market-expert", type=int)
    parser.add_argument("--unit-expert-schedule", type=parse_expert_schedule)
    parser.add_argument("--market-expert-schedule", type=parse_expert_schedule)
    parser.add_argument("--capture-router-step", type=int)
    parser.add_argument("--market-stop-bias", type=float, default=0.0)
    parser.add_argument("--coupled-product-router", action="store_true")
    parser.add_argument(
        "--router-period", type=int,
        help=(
            "Expert route hold period. Defaults to 1 for sequence-action policies "
            "and 24 for legacy factorized/option policies."
        ),
    )
    parser.add_argument("--scale-worker-cap", type=int)
    parser.add_argument("--scale-seed-capacity", type=int)
    parser.add_argument("--role-option", action="store_true")
    parser.add_argument("--staged-option", action="store_true")
    parser.add_argument("--sequence-action", action="store_true")
    parser.add_argument("--timed-sequence-action", action="store_true")
    parser.add_argument("--delayed-tree-router", action="store_true")
    parser.add_argument("--history-sequence-action", action="store_true")
    parser.add_argument("--market-memory-sequence-action", action="store_true")
    parser.add_argument("--router-model", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sum(value is not None for value in (
        args.opponent, args.opponent_checkpoint, args.opponent_registry,
    )) != 1:
        parser.error("choose exactly one opponent, opponent checkpoint, or opponent registry")
    if args.opponent_stats is not None and args.opponent_registry is None:
        parser.error("--opponent-stats requires --opponent-registry")
    started = time.time()
    rows = []
    registry = None
    pool_schedule = None
    pool_schedule_summary = None
    if args.opponent_registry is not None:
        registry = load_registry(args.opponent_registry)
        opponent_stats = (
            json.loads(args.opponent_stats.read_text(encoding="utf-8"))
            if args.opponent_stats is not None else None
        )
        pool_schedule = build_schedule(
            registry, args.seed_start, args.seeds, args.opponent_pool_seed,
            iteration=args.iteration, stats=opponent_stats,
        )
        pool_schedule_summary = schedule_report(
            registry, pool_schedule, args.iteration, args.opponent_pool_seed,
        )
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        pool_assignment = (
            pool_schedule[seed - args.seed_start] if pool_schedule is not None else None
        )
        for seat in (0, 1):
            if sum((
                args.role_option, args.staged_option, args.sequence_action,
                args.timed_sequence_action, args.delayed_tree_router,
                args.history_sequence_action,
                args.market_memory_sequence_action,
            )) > 1:
                parser.error("choose only one hierarchical policy architecture")
            if args.delayed_tree_router and args.router_model is None:
                parser.error("--delayed-tree-router requires --router-model")
            policy_class = (
                DelayedTreeRouterPolicy if args.delayed_tree_router else (
                    MarketMemoryTimedSequenceActionV113Policy
                    if args.market_memory_sequence_action else (
                    HistoryTimedSequenceActionV113Policy if args.history_sequence_action else (
                    TimedSequenceActionV113Policy if args.timed_sequence_action else (
                    SequenceActionV113Policy if args.sequence_action else (
                    StagedOptionV113Policy if args.staged_option
                    else (RoleOptionV113Policy if args.role_option else FactorizedV113Policy)
                    )
                    )
                    ))
                )
            )
            sequence_policy = any((
                args.sequence_action, args.timed_sequence_action,
                args.history_sequence_action, args.market_memory_sequence_action,
            ))
            router_period = args.router_period
            if router_period is None:
                router_period = 1 if sequence_policy else 24
            policy_kwargs = dict(
                market_stop_bias=args.market_stop_bias,
                coupled_product_router=args.coupled_product_router,
                router_period=router_period,
                scale_worker_cap=args.scale_worker_cap,
                scale_seed_capacity=args.scale_seed_capacity,
            )
            candidate = (
                policy_class(args.checkpoint, args.router_model, **policy_kwargs)
                if args.delayed_tree_router else policy_class(
                    args.checkpoint, args.forced_unit_expert, args.forced_market_expert,
                    unit_expert_schedule=args.unit_expert_schedule,
                    market_expert_schedule=args.market_expert_schedule,
                    **policy_kwargs,
                )
            )
            candidate_agent = (
                RouterSnapshotPolicy(candidate, args.capture_router_step)
                if args.capture_router_step is not None else candidate
            )
            opponent = build_opponent(
                pool_assignment, f"v113_eval_pool_{seed}_{seat}_{pool_assignment.member_id}"
            ) if pool_assignment is not None else (
                checkpoint_opponent(
                    args.opponent_checkpoint,
                    args.opponent_architecture,
                    args.opponent_forced_unit_expert,
                    args.opponent_forced_market_expert,
                )
                if args.opponent_checkpoint is not None
                else resolve_opponent(
                    args.opponent, f"v113_factorized_opponent_{seed}_{seat}"
                )
            )
            agents = [None, None]
            agents[seat] = candidate_agent
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
                "opponent_reward": rewards[1 - seat], "margin": margin, "score": score(margin),
                "statuses": statuses, "steps": len(env.steps), "error": error,
                "unit_expert_usage": dict(candidate.unit_expert_usage),
                "market_expert_usage": dict(candidate.market_expert_usage),
                "operation_counts": dict(candidate.operation_counts),
                "nonpass_unit_orders": candidate.nonpass_unit_orders,
                "router_snapshot": (
                    candidate_agent.snapshot
                    if args.capture_router_step is not None else None
                ),
                "selected_combo": list(candidate.selected_combo)
                if hasattr(candidate, "selected_combo") else None,
                "opponent_layer": (
                    pool_assignment.layer if pool_assignment is not None else None
                ),
                "opponent_member_id": (
                    pool_assignment.member_id if pool_assignment is not None else None
                ),
            }
            rows.append(row)
            printed_row = dict(row)
            if printed_row["router_snapshot"] is not None:
                printed_row["router_snapshot"] = "captured"
            print(json.dumps(printed_row, ensure_ascii=False), flush=True)
    valid = [row for row in rows if row["error"] is None and row["statuses"] == ["DONE", "DONE"]]
    report = {
        "schema": "kaggriculture-v113-factorized-closed-loop-v1",
        "games": len(rows), "done_done": len(valid),
        "score_rate": statistics.mean(row["score"] for row in valid) if valid else 0.0,
        "mean_candidate_reward": statistics.mean(row["candidate_reward"] for row in valid) if valid else 0.0,
        "mean_margin": statistics.mean(row["margin"] for row in valid) if valid else 0.0,
        "elapsed_seconds": time.time() - started, "rows": rows,
        "unit_expert_schedule": args.unit_expert_schedule,
        "market_expert_schedule": args.market_expert_schedule,
        "capture_router_step": args.capture_router_step,
        "policy_class": policy_class.__name__,
        "router_period": router_period,
        "sequence_action": args.sequence_action,
        "timed_sequence_action": args.timed_sequence_action,
        "history_sequence_action": args.history_sequence_action,
        "market_memory_sequence_action": args.market_memory_sequence_action,
        "opponent_registry": (
            str(args.opponent_registry) if args.opponent_registry is not None else None
        ),
        "opponent_schedule": pool_schedule_summary,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as sink:
        json.dump(report, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps({key: report[key] for key in ("games", "done_done", "score_rate", "mean_candidate_reward", "mean_margin", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
