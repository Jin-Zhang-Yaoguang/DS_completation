"""Collect fresh-seed on-policy trajectories for factorized V113 PPO."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
import numpy as np

import action_space as space
from collect_rollouts import (
    agent_observations, asset_value, call_opponent, finish_gae, potential,
    resolve_opponent,
)
from policy_factorized import FactorizedV113Policy
from policy_history_sequence import HistoryTimedSequenceActionV113Policy
from policy_market_memory_sequence import MarketMemoryTimedSequenceActionV113Policy
from policy_sequence_action import SequenceActionV113Policy, TimedSequenceActionV113Policy
from opponent_factory import checkpoint_opponent
from opponent_pool import build_opponent, build_schedule, load_registry, schedule_report


ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}


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
        raise argparse.ArgumentTypeError("expert schedule must look like 0:3,72:4") from None


def enterprise_value(obs) -> float:
    """Mark productive capacity to market while preserving potential shaping."""
    farm = space.own_farm(obs)
    step = int(space.get(obs, "step", 0) or 0)
    remaining_fraction = max(0.0, min(1.0, (720.0 - step) / 720.0))
    unlocked = len(space.get(farm, "unlocked_quadrants", []) or [])
    capacity = max(0, unlocked - 1) * 2000.0
    for row in space.get(farm, "tiles", []) or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            crop = str(space.get(tile, "crop", "") or "")
            animal = str(space.get(tile, "animal", "") or "")
            if crop in space.CROPS:
                capacity += 8.0 * space.BASE_PRICES[crop]
            if animal in ANIMAL_PRODUCT:
                capacity += 10.0 * space.BASE_PRICES[ANIMAL_PRODUCT[animal]]
    return float(asset_value(obs) + remaining_fraction * capacity)


def public_enterprise_value(obs, farm_index: int) -> float:
    """Value only public money, units, land and visible productive tiles."""
    farms = list(space.get(obs, "farms", []) or [])
    farm = farms[int(farm_index)]
    market = space.get(obs, "market", {}) or {}
    prices = space.get(market, "prices", {}) or {}
    value = float(space.get(farm, "money", 0.0) or 0.0)
    value += 250.0 * len(space.get(farm, "hands", []) or [])
    value += 500.0 * max(0, len(space.get(farm, "unlocked_quadrants", []) or []) - 1)
    for row in space.get(farm, "tiles", []) or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            crop = str(space.get(tile, "crop", "") or "")
            animal = str(space.get(tile, "animal", "") or "")
            if crop in space.CROPS:
                value += 0.5 * space.SEED_COST[crop]
                value += float(space.get(tile, "yield_units", 0) or 0) * float(
                    space.get(prices, crop, space.BASE_PRICES[crop]) or space.BASE_PRICES[crop]
                )
            if animal in ANIMAL_PRODUCT:
                product = ANIMAL_PRODUCT[animal]
                value += 0.7 * space.ANIMAL_COST[animal]
                value += float(space.get(tile, "yield_units", 0) or 0) * float(
                    space.get(prices, product, space.BASE_PRICES[product]) or space.BASE_PRICES[product]
                )
    return float(value)


def relative_public_enterprise_potential(obs, opponent_impact_weight: float) -> float:
    player = int(space.seat(obs))
    own = np.log1p(max(0.0, public_enterprise_value(obs, player)) / 3000.0)
    opponent = np.log1p(max(0.0, public_enterprise_value(obs, 1 - player)) / 3000.0)
    return float(own - opponent_impact_weight * opponent)


def cash_safety_relative_potential(
    obs, opponent_impact_weight: float, cash_floor: float,
    cash_reserve_weight: float, cash_shortfall_weight: float,
) -> float:
    """Relative public enterprise value with an explicit cash-solvency contract."""
    if cash_floor <= 0:
        raise ValueError("cash floor must be positive")
    player = int(space.seat(obs))
    farms = list(space.get(obs, "farms", []) or [])
    own_cash = max(0.0, float(space.get(farms[player], "money", 0.0) or 0.0))
    reserve = np.log1p(own_cash / cash_floor)
    shortfall = max(0.0, cash_floor - own_cash) / cash_floor
    return float(
        relative_public_enterprise_potential(obs, opponent_impact_weight)
        + cash_reserve_weight * reserve
        - cash_shortfall_weight * shortfall
    )


def shared_market_shock_potential(
    obs, opponent_impact_weight: float, inventory_reference: float,
    inventory_scale: float, liquidity_weight: float, cash_weight: float,
) -> float:
    """Reward liquid inventory and cash specifically when the shared market is scarce."""
    if inventory_reference <= 0 or inventory_scale <= 0:
        raise ValueError("market inventory reference and scale must be positive")
    market = space.get(obs, "market", {}) or {}
    market_inventory = space.get(market, "inventory", {}) or {}
    scarcity = np.asarray([
        np.clip(
            (inventory_reference - float(space.get(market_inventory, item, inventory_reference) or 0.0))
            / inventory_scale,
            0.0,
            10.0,
        )
        for item in space.PRODUCTS
    ], dtype=np.float64)
    own_private = space.private(obs)
    shed = space.get(own_private, "shed", {}) or {}
    liquid_stock = np.asarray([
        float(space.get(shed, item, 0.0) or 0.0)
        + sum(
            float(space.get(inventory, item, 0.0) or 0.0)
            for inventory in list(space.get(own_private, "inventories", []) or [])
        )
        for item in space.PRODUCTS
    ], dtype=np.float64)
    player = int(space.seat(obs))
    farms = list(space.get(obs, "farms", []) or [])
    own_cash = max(0.0, float(space.get(farms[player], "money", 0.0) or 0.0))
    scarcity_stock = float(np.mean(scarcity * np.log1p(liquid_stock)))
    cash_buffer = float(np.mean(scarcity) * np.log1p(own_cash / 3000.0))
    return float(
        relative_public_enterprise_potential(obs, opponent_impact_weight)
        + liquidity_weight * scarcity_stock
        + cash_weight * cash_buffer
    )


def shaped_potential(
    obs, mode: str, opponent_impact_weight: float = 1.0,
    cash_floor: float = 3000.0, cash_reserve_weight: float = 0.25,
    cash_shortfall_weight: float = 0.75,
    market_inventory_reference: float = 10000.0,
    market_inventory_scale: float = 1000.0,
    market_liquidity_weight: float = 0.35,
    market_cash_weight: float = 0.15,
) -> float:
    if mode == "bounded":
        return potential(obs)
    if mode == "relative-public-enterprise":
        return relative_public_enterprise_potential(obs, opponent_impact_weight)
    if mode == "cash-safety-relative":
        return cash_safety_relative_potential(
            obs, opponent_impact_weight, cash_floor,
            cash_reserve_weight, cash_shortfall_weight,
        )
    if mode == "shared-market-shock-relative":
        return shared_market_shock_potential(
            obs, opponent_impact_weight, market_inventory_reference,
            market_inventory_scale, market_liquidity_weight, market_cash_weight,
        )
    value = enterprise_value(obs) if mode == "enterprise" else asset_value(obs)
    return float(np.log1p(max(0.0, value) / 3000.0))


def terminal_objective(
    rewards: list[float], seat: int, margin_scale: float, terminal_mode: str,
    cash_floor: float, catastrophe_weight: float, own_log_weight: float,
) -> float:
    margin = float(rewards[seat] - rewards[1 - seat])
    terminal = float(np.tanh(margin / margin_scale))
    if terminal_mode == "sign":
        terminal = (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)) + 0.05 * terminal
    elif terminal_mode == "own-log":
        terminal = float(np.log1p(max(0.0, rewards[seat]) / 3000.0))
    terminal -= catastrophe_weight * max(0.0, cash_floor - rewards[seat]) / cash_floor
    terminal += own_log_weight * float(np.log1p(max(0.0, rewards[seat]) / 3000.0))
    return float(terminal)


def phase_indices(traces: list[dict], start: int, end: int) -> list[int]:
    """Select one-based decision rounds in the half-open interval [start, end)."""
    return [
        index for index, trace in enumerate(traces)
        if start <= int(trace["environment_step"]) < end
    ]


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
        "--pool-schedule-total-seeds", type=int,
        help="Build one global pool schedule of this size, then collect only this shard.",
    )
    parser.add_argument("--pool-schedule-offset", type=int, default=0)
    parser.add_argument(
        "--opponent-architecture",
        choices=("factorized", "sequence", "timed-sequence", "history-timed-sequence"),
        default="timed-sequence",
    )
    parser.add_argument("--opponent-forced-unit-expert", type=int)
    parser.add_argument("--opponent-forced-market-expert", type=int)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--seed-start", type=int, default=1138200)
    parser.add_argument("--worker-temperature", type=float, default=0.2)
    parser.add_argument("--margin-scale", type=float, default=500.0)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--lambda-gae", type=float, default=0.95)
    parser.add_argument(
        "--potential", choices=(
            "bounded", "log", "enterprise", "relative-public-enterprise",
            "cash-safety-relative",
            "shared-market-shock-relative",
        ), default="log"
    )
    parser.add_argument("--opponent-impact-weight", type=float, default=1.0)
    parser.add_argument("--cash-floor", type=float, default=3000.0)
    parser.add_argument("--cash-reserve-weight", type=float, default=0.25)
    parser.add_argument("--cash-shortfall-weight", type=float, default=0.75)
    parser.add_argument("--market-inventory-reference", type=float, default=10000.0)
    parser.add_argument("--market-inventory-scale", type=float, default=1000.0)
    parser.add_argument("--market-liquidity-weight", type=float, default=0.35)
    parser.add_argument("--market-cash-weight", type=float, default=0.15)
    parser.add_argument(
        "--terminal-catastrophe-weight", type=float, default=0.0,
        help="Subtract this scaled terminal penalty when final own reward is below cash-floor.",
    )
    parser.add_argument("--terminal-own-log-weight", type=float, default=0.0)
    parser.add_argument(
        "--terminal-mode", choices=("sign", "smooth", "own-log"), default="smooth"
    )
    parser.add_argument("--forced-expert", type=int, default=1)
    parser.add_argument("--forced-unit-expert", type=int)
    parser.add_argument("--forced-market-expert", type=int)
    parser.add_argument("--unit-expert-schedule", type=parse_expert_schedule)
    parser.add_argument("--market-expert-schedule", type=parse_expert_schedule)
    parser.add_argument("--training-step-start", type=int)
    parser.add_argument("--training-step-end", type=int)
    parser.add_argument(
        "--phase-include-terminal-objective", action="store_true",
        help="Add the final game objective to the last selected phase transition.",
    )
    parser.add_argument("--scale-worker-cap", type=int)
    parser.add_argument("--scale-seed-capacity", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sequence-action", action="store_true")
    parser.add_argument("--timed-sequence-action", action="store_true")
    parser.add_argument("--history-sequence-action", action="store_true")
    parser.add_argument("--market-memory-sequence-action", action="store_true")
    parser.add_argument("--no-normalize-advantage", action="store_true")
    parser.add_argument(
        "--ignore-value-baseline", action="store_true",
        help="Use zero as the rollout baseline; intended for the first PPO update after BC.",
    )
    args = parser.parse_args()
    selected_opponent_sources = sum(value is not None for value in (
        args.opponent, args.opponent_checkpoint, args.opponent_registry,
    ))
    if selected_opponent_sources == 0:
        args.opponent = "builtin:starter"
    elif selected_opponent_sources > 1:
        parser.error("choose only one opponent, opponent checkpoint, or opponent registry")
    if args.opponent_stats is not None and args.opponent_registry is None:
        parser.error("--opponent-stats requires --opponent-registry")
    if args.pool_schedule_total_seeds is not None and args.opponent_registry is None:
        parser.error("pool schedule sharding requires --opponent-registry")
    if args.pool_schedule_offset < 0:
        parser.error("--pool-schedule-offset must be non-negative")
    architecture_flags = sum((
        bool(args.sequence_action), bool(args.timed_sequence_action),
        bool(args.history_sequence_action),
        bool(args.market_memory_sequence_action),
    ))
    if architecture_flags > 1:
        parser.error("choose only one sequence architecture")
    if args.margin_scale <= 0:
        parser.error("--margin-scale must be positive")
    if not 0.0 < args.gamma <= 1.0 or not 0.0 <= args.lambda_gae <= 1.0:
        parser.error("invalid GAE gamma/lambda")
    if args.opponent_impact_weight < 0:
        parser.error("--opponent-impact-weight must be non-negative")
    if args.cash_floor <= 0:
        parser.error("--cash-floor must be positive")
    if min(
        args.cash_reserve_weight, args.cash_shortfall_weight,
        args.terminal_catastrophe_weight,
        args.terminal_own_log_weight,
    ) < 0:
        parser.error("cash reward weights must be non-negative")
    if args.market_inventory_reference <= 0 or args.market_inventory_scale <= 0:
        parser.error("market inventory reference and scale must be positive")
    if min(args.market_liquidity_weight, args.market_cash_weight) < 0:
        parser.error("market shock reward weights must be non-negative")
    phase_only = args.training_step_start is not None or args.training_step_end is not None
    if phase_only:
        if args.training_step_start is None or args.training_step_end is None:
            parser.error("phase training requires both --training-step-start and --training-step-end")
        if not 1 <= args.training_step_start < args.training_step_end <= 720:
            parser.error("invalid phase training step interval")
    elif args.phase_include_terminal_objective:
        parser.error("phase terminal objective requires a training step interval")
    started = time.time()
    forced_unit_expert = (
        args.forced_expert if args.forced_unit_expert is None
        else args.forced_unit_expert
    )
    forced_market_expert = (
        args.forced_expert if args.forced_market_expert is None
        else args.forced_market_expert
    )
    rng = np.random.default_rng(args.seed_start + args.pool_schedule_offset)
    registry = None
    pool_schedule = None
    pool_schedule_summary = None
    if args.opponent_registry is not None:
        registry = load_registry(args.opponent_registry)
        opponent_stats = (
            json.loads(args.opponent_stats.read_text(encoding="utf-8"))
            if args.opponent_stats is not None else None
        )
        schedule_total = args.pool_schedule_total_seeds or args.seeds
        if args.pool_schedule_offset + args.seeds > schedule_total:
            parser.error("pool schedule shard extends beyond total seeds")
        full_pool_schedule = build_schedule(
            registry, args.seed_start, schedule_total, args.opponent_pool_seed,
            iteration=args.iteration, stats=opponent_stats,
        )
        pool_schedule = full_pool_schedule[
            args.pool_schedule_offset:args.pool_schedule_offset + args.seeds
        ]
        pool_schedule_summary = schedule_report(
            registry, pool_schedule, args.iteration, args.opponent_pool_seed,
        )
        pool_schedule_summary["global_schedule_seed_groups"] = schedule_total
        pool_schedule_summary["shard_offset"] = args.pool_schedule_offset
    all_traces = []
    games = []
    episode_seeds = (
        [assignment.seed for assignment in pool_schedule]
        if pool_schedule is not None
        else list(range(args.seed_start, args.seed_start + args.seeds))
    )
    for episode_index, seed in enumerate(episode_seeds):
        pool_assignment = (
            pool_schedule[episode_index] if pool_schedule is not None else None
        )
        for seat in (0, 1):
            policy_class = (
                MarketMemoryTimedSequenceActionV113Policy
                if args.market_memory_sequence_action else (
                HistoryTimedSequenceActionV113Policy if args.history_sequence_action else (
                    TimedSequenceActionV113Policy if args.timed_sequence_action else (
                        SequenceActionV113Policy if args.sequence_action else FactorizedV113Policy
                    )
                ))
            )
            policy = policy_class(
                args.checkpoint, forced_unit_expert=forced_unit_expert,
                forced_market_expert=forced_market_expert,
                scale_worker_cap=args.scale_worker_cap,
                scale_seed_capacity=args.scale_seed_capacity,
                unit_expert_schedule=args.unit_expert_schedule,
                market_expert_schedule=args.market_expert_schedule,
            )
            opponent = build_opponent(
                pool_assignment, f"v113_mixed_pool_{seed}_{seat}_{pool_assignment.member_id}"
            ) if pool_assignment is not None else (
                checkpoint_opponent(
                    args.opponent_checkpoint,
                    args.opponent_architecture,
                    args.opponent_forced_unit_expert,
                    args.opponent_forced_market_expert,
                )
                if args.opponent_checkpoint is not None
                else resolve_opponent(
                    args.opponent, f"v113_factorized_ppo_opponent_{seed}_{seat}"
                )
            )
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            traces = []
            shaped_rewards = []
            while not env.done:
                observations = agent_observations(env)
                before = shaped_potential(
                    observations[seat], args.potential, args.opponent_impact_weight,
                    args.cash_floor, args.cash_reserve_weight,
                    args.cash_shortfall_weight,
                    args.market_inventory_reference, args.market_inventory_scale,
                    args.market_liquidity_weight, args.market_cash_weight,
                )
                action, trace = policy.sample(observations[seat], rng, worker_temperature=args.worker_temperature)
                # Kaggriculture has 719 decisions. Expose them as rounds 1..719,
                # matching the competition's human-facing round convention.
                trace["environment_step"] = np.int16(len(traces) + 1)
                actions = [None, None]
                actions[seat] = action
                actions[1 - seat] = call_opponent(opponent, observations[1 - seat], env.configuration)
                env.step(actions)
                if env.done:
                    after = 0.0
                else:
                    next_obs = agent_observations(env)[seat]
                    after = shaped_potential(
                        next_obs, args.potential, args.opponent_impact_weight,
                        args.cash_floor, args.cash_reserve_weight,
                        args.cash_shortfall_weight,
                        args.market_inventory_reference, args.market_inventory_scale,
                        args.market_liquidity_weight, args.market_cash_weight,
                    )
                shaped_rewards.append(args.gamma * after - before)
                traces.append(trace)
            rewards = [float(state.reward or 0.0) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            statuses = [str(state.status) for state in env.state]
            valid_trajectory = (
                statuses == ["DONE", "DONE"]
                and bool(traces)
                and bool(np.all(np.isfinite(rewards)))
                and bool(np.all(np.isfinite(shaped_rewards)))
            )
            terminal = terminal_objective(
                rewards, seat, args.margin_scale, args.terminal_mode,
                args.cash_floor, args.terminal_catastrophe_weight,
                args.terminal_own_log_weight,
            )
            if phase_only:
                selected_indices = phase_indices(
                    traces, args.training_step_start, args.training_step_end,
                )
                if not selected_indices:
                    raise RuntimeError("phase interval selected no transitions")
            else:
                shaped_rewards[-1] += terminal
                selected_indices = range(len(traces))
            selected_traces = [traces[index] for index in selected_indices]
            selected_rewards = [shaped_rewards[index] for index in selected_indices]
            if phase_only and args.phase_include_terminal_objective:
                selected_rewards[-1] += terminal
            if args.ignore_value_baseline:
                for trace in selected_traces:
                    trace["value_prediction"] = np.float32(0.0)
            advantages, returns = finish_gae(
                selected_traces, selected_rewards, args.gamma, args.lambda_gae
            )
            if valid_trajectory:
                for trace, reward, advantage, target in zip(
                    selected_traces, selected_rewards, advantages, returns
                ):
                    trace["reward"] = np.float32(reward)
                    trace["return_target"] = np.float32(target)
                    trace["advantage"] = np.float32(advantage)
                    trace["episode_seed"] = np.int32(seed)
                    trace["seat"] = np.int8(seat)
                    trace["opponent_layer_id"] = np.int8(
                        pool_assignment.layer_id if pool_assignment is not None else -1
                    )
                    trace["opponent_member_index"] = np.int16(
                        pool_assignment.member_index if pool_assignment is not None else -1
                    )
                    all_traces.append(trace)
            game = {
                "seed": seed, "seat": seat, "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat], "margin": margin,
                "score": 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0),
                "statuses": statuses, "accepted_for_training": valid_trajectory,
                "operation_counts": dict(policy.operation_counts),
                "opponent_layer": (
                    pool_assignment.layer if pool_assignment is not None else None
                ),
                "opponent_member_id": (
                    pool_assignment.member_id if pool_assignment is not None else None
                ),
            }
            games.append(game)
            print(json.dumps(game, ensure_ascii=False), flush=True)
    if not all_traces:
        raise RuntimeError("no valid DONE/DONE finite trajectories were collected")
    arrays = {key: np.asarray([trace[key] for trace in all_traces]) for key in sorted(all_traces[0])}
    advantage_normalization = {}
    if not args.no_normalize_advantage:
        if pool_schedule is None:
            mean = float(arrays["advantage"].mean())
            std = max(1e-6, float(arrays["advantage"].std()))
            arrays["advantage"] = (arrays["advantage"] - mean) / std
            advantage_normalization["all"] = {"rows": len(arrays["advantage"]), "mean": mean, "std": std}
        else:
            for layer, layer_id in sorted(
                ((assignment.layer, assignment.layer_id) for assignment in pool_schedule),
                key=lambda item: item[1],
            ):
                if layer in advantage_normalization:
                    continue
                selected = arrays["opponent_layer_id"] == layer_id
                mean = float(arrays["advantage"][selected].mean())
                std = max(1e-6, float(arrays["advantage"][selected].std()))
                arrays["advantage"][selected] = (arrays["advantage"][selected] - mean) / std
                advantage_normalization[layer] = {
                    "rows": int(selected.sum()), "mean": mean, "std": std,
                }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-factorized-rollout-v1", "games": len(games),
        "transitions": len(all_traces), "opponent": args.opponent,
        "opponent_checkpoint": (
            str(args.opponent_checkpoint) if args.opponent_checkpoint is not None else None
        ),
        "opponent_architecture": (
            args.opponent_architecture if args.opponent_checkpoint is not None else None
        ),
        "opponent_forced_unit_expert": args.opponent_forced_unit_expert,
        "opponent_forced_market_expert": args.opponent_forced_market_expert,
        "opponent_registry": (
            str(args.opponent_registry) if args.opponent_registry is not None else None
        ),
        "opponent_schedule": pool_schedule_summary,
        "worker_temperature": args.worker_temperature, "margin_scale": args.margin_scale,
        "gamma": args.gamma, "lambda_gae": args.lambda_gae,
        "potential": args.potential, "terminal_mode": args.terminal_mode,
        "opponent_impact_weight": args.opponent_impact_weight,
        "cash_floor": args.cash_floor,
        "cash_reserve_weight": args.cash_reserve_weight,
        "cash_shortfall_weight": args.cash_shortfall_weight,
        "terminal_own_log_weight": args.terminal_own_log_weight,
        "market_inventory_reference": args.market_inventory_reference,
        "market_inventory_scale": args.market_inventory_scale,
        "market_liquidity_weight": args.market_liquidity_weight,
        "market_cash_weight": args.market_cash_weight,
        "terminal_catastrophe_weight": args.terminal_catastrophe_weight,
        "forced_unit_expert": forced_unit_expert,
        "forced_market_expert": forced_market_expert,
        "unit_expert_schedule": args.unit_expert_schedule,
        "market_expert_schedule": args.market_expert_schedule,
        "phase_include_terminal_objective": args.phase_include_terminal_objective,
        "training_step_start": args.training_step_start,
        "training_step_end": args.training_step_end,
        "phase_only": phase_only,
        "ignore_value_baseline": args.ignore_value_baseline,
        "advantage_normalized": not args.no_normalize_advantage,
        "advantage_normalization": advantage_normalization,
        "score_rate": float(np.mean([game["score"] for game in games])),
        "mean_candidate_reward": float(np.mean([game["candidate_reward"] for game in games])),
        "mean_margin": float(np.mean([game["margin"] for game in games])),
        "done_done": sum(game["statuses"] == ["DONE", "DONE"] for game in games),
        "accepted_games": sum(game["accepted_for_training"] for game in games),
        "rejected_games": sum(not game["accepted_for_training"] for game in games),
        "elapsed_seconds": time.time() - started, "rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("games", "transitions", "score_rate", "mean_candidate_reward", "mean_margin", "done_done", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
