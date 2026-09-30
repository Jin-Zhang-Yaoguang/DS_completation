"""Profile production and capital growth for a Python agent or timed V113 policy."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
import statistics

from kaggle_environments import make

import action_space as space
from collect_rollouts import agent_observations, asset_value, call_opponent, resolve_opponent
from policy_sequence_action import TimedSequenceActionV113Policy


def state_summary(obs) -> dict:
    farm = space.own_farm(obs)
    private = space.private(obs)
    shed = space.get(private, "shed", {}) or {}
    seeds = space.get(private, "seeds", {}) or {}
    crop_tiles = Counter()
    animal_tiles = Counter()
    planted_yield = Counter()
    for row in space.get(farm, "tiles", []) or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            crop = str(space.get(tile, "crop", "") or "")
            animal = str(space.get(tile, "animal", "") or "")
            if crop in space.CROPS:
                crop_tiles[crop] += 1
                planted_yield[crop] += int(space.get(tile, "yield_units", 0) or 0)
            if animal in space.ANIMALS:
                animal_tiles[animal] += 1
    inventories = list(space.get(private, "inventories", []) or [])
    carried = Counter()
    for inventory in inventories:
        for item, quantity in inventory.items():
            carried[str(item)] += int(quantity or 0)
    return {
        "step": int(space.get(obs, "step", 0) or 0),
        "day": int(space.get(obs, "day", 0) or 0),
        "hour": int(space.get(obs, "hour", 0) or 0),
        "money": float(space.get(farm, "money", 0.0) or 0.0),
        "asset_value": float(asset_value(obs)),
        "units": int(space.unit_count(obs)),
        "unlocked_quadrants": len(space.get(farm, "unlocked_quadrants", []) or []),
        "shed": {item: int(space.get(shed, item, 0) or 0) for item in space.ITEMS},
        "seeds": {item: int(space.get(seeds, item, 0) or 0) for item in space.CROPS},
        "carried": dict(carried),
        "crop_tiles": dict(crop_tiles),
        "animal_tiles": dict(animal_tiles),
        "planted_yield": dict(planted_yield),
    }


def count_action(action, counts: Counter) -> None:
    if not isinstance(action, dict):
        return
    farmer_order = action.get("farmer", []) or []
    if farmer_order:
        counts[f"unit:{farmer_order[0]}"] += 1
    for order in action.get("hands", []) or []:
        if order:
            counts[f"unit:{order[0]}"] += 1
    for order in action.get("market", []) or []:
        if order:
            counts[f"market:{order[0]}"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--candidate-agent")
    source.add_argument("--checkpoint", type=Path)
    parser.add_argument("--opponent", default="builtin:pass")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--seat", type=int, choices=(0, 1), required=True)
    parser.add_argument("--interval", type=int, default=72)
    parser.add_argument("--forced-expert", type=int, default=5)
    parser.add_argument("--scale-worker-cap", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.interval < 1:
        parser.error("--interval must be positive")

    if args.candidate_agent:
        candidate = resolve_opponent(args.candidate_agent, "v113_profile_candidate")
        candidate_name = args.candidate_agent
    else:
        candidate = TimedSequenceActionV113Policy(
            args.checkpoint,
            args.forced_expert,
            args.forced_expert,
            scale_worker_cap=args.scale_worker_cap,
        )
        candidate_name = str(args.checkpoint)
    opponent = resolve_opponent(args.opponent, "v113_profile_opponent")
    env = make("kaggriculture", configuration={"seed": args.seed}, debug=False)
    env.reset(2)
    counts = Counter()
    snapshots = []
    window_units = []
    observations = agent_observations(env)
    snapshots.append({**state_summary(observations[args.seat]), "operation_counts": {}})
    while not env.done:
        observations = agent_observations(env)
        window_units.append(space.unit_count(observations[args.seat]))
        candidate_action = call_opponent(candidate, observations[args.seat], env.configuration)
        count_action(candidate_action, counts)
        actions = [None, None]
        actions[args.seat] = candidate_action
        actions[1 - args.seat] = call_opponent(
            opponent, observations[1 - args.seat], env.configuration
        )
        env.step(actions)
        if not env.done:
            obs = agent_observations(env)[args.seat]
            step = int(space.get(obs, "step", 0) or 0)
            if step % args.interval == 0:
                snapshots.append({
                    **state_summary(obs),
                    "window_max_units": max(window_units),
                    "window_mean_units": statistics.mean(window_units),
                    "operation_counts": dict(counts),
                })
                window_units.clear()
    rewards = [float(state.reward or 0.0) for state in env.state]
    terminal_obs = agent_observations(env)[args.seat]
    snapshots.append({
        **state_summary(terminal_obs),
        "window_max_units": max(window_units) if window_units else space.unit_count(terminal_obs),
        "window_mean_units": (
            statistics.mean(window_units) if window_units else space.unit_count(terminal_obs)
        ),
        "operation_counts": dict(counts),
    })
    report = {
        "schema": "kaggriculture-v113-trajectory-profile-v1",
        "candidate": candidate_name,
        "opponent": args.opponent,
        "seed": args.seed,
        "seat": args.seat,
        "candidate_reward": rewards[args.seat],
        "opponent_reward": rewards[1 - args.seat],
        "margin": rewards[args.seat] - rewards[1 - args.seat],
        "statuses": [str(state.status) for state in env.state],
        "operation_counts": dict(counts),
        "snapshots": snapshots,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as sink:
        json.dump(report, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps({
        "candidate_reward": report["candidate_reward"],
        "margin": report["margin"],
        "snapshots": len(snapshots),
        "operation_counts": report["operation_counts"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
