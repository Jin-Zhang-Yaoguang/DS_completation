"""Collect fresh-seed full-action V113 trajectories in the official engine."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
import numpy as np

import action_space as space
from policy import V113Policy
from evaluate_bc_closed_loop import load_agent


def resolve_opponent(value: str, name: str):
    if value.startswith("builtin:"):
        from kaggle_environments.envs.kaggriculture import kaggriculture
        agents = {"pass": kaggriculture.pass_agent, "random": kaggriculture.random_agent, "starter": kaggriculture.starter_agent}
        return agents[value.split(":", 1)[1]]
    return load_agent(Path(value), name)


def call_opponent(agent, obs, configuration):
    parameters = inspect.signature(agent).parameters
    return agent(obs, configuration) if len(parameters) >= 2 else agent(obs)


def agent_observations(env):
    """Hydrate Kaggle's seat1 private delta with seat0's shared observation."""
    shared = env.state[0].observation
    base = {key: space.get(shared, key) for key in shared.keys()}
    observations = []
    for seat in (0, 1):
        private_delta = env.state[seat].observation
        obs = dict(base)
        obs["player"] = seat
        obs["private"] = space.get(private_delta, "private", {}) or {}
        obs["remainingOverageTime"] = space.get(private_delta, "remainingOverageTime", 60)
        observations.append(obs)
    return observations


def asset_value(obs) -> float:
    farm = space.own_farm(obs)
    own_private = space.private(obs)
    market = space.get(obs, "market", {}) or {}
    prices = space.get(market, "prices", {}) or {}
    value = float(space.get(farm, "money", 0.0) or 0.0)
    shed = space.get(own_private, "shed", {}) or {}
    for item in space.PRODUCTS:
        value += float(space.get(shed, item, 0) or 0) * float(space.get(prices, item, space.BASE_PRICES[item]) or space.BASE_PRICES[item])
    for crop in space.CROPS:
        value += 0.5 * float(space.get(space.get(own_private, "seeds", {}) or {}, crop, 0) or 0) * space.SEED_COST[crop]
    for animal in space.ANIMALS:
        value += 0.7 * float(space.get(shed, animal, 0) or 0) * space.ANIMAL_COST[animal]
    # Harvest first lands in unit inventory.  Omitting it would make every
    # successful HARVEST look like value destruction until the later deposit.
    for unit_inventory in list(space.get(own_private, "inventories", []) or []):
        for item in space.PRODUCTS:
            value += float(space.get(unit_inventory, item, 0) or 0) * float(space.get(prices, item, space.BASE_PRICES[item]) or space.BASE_PRICES[item])
        for animal in space.ANIMALS:
            value += 0.7 * float(space.get(unit_inventory, animal, 0) or 0) * space.ANIMAL_COST[animal]
    for row in space.get(farm, "tiles", []) or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            crop = str(space.get(tile, "crop", ""))
            animal = str(space.get(tile, "animal", ""))
            if crop in space.CROPS:
                value += 0.5 * space.SEED_COST[crop] + float(space.get(tile, "yield_units", 0) or 0) * float(space.get(prices, crop, space.BASE_PRICES[crop]) or space.BASE_PRICES[crop])
            if animal in space.ANIMALS:
                value += 0.7 * space.ANIMAL_COST[animal]
    return value


def potential(obs) -> float:
    # Bounded legacy curriculum potential retained for reproducibility.
    return float(np.tanh(asset_value(obs) / 3000.0))


def finish_gae(traces, rewards, gamma: float, lam: float):
    advantage = np.zeros((len(traces),), dtype=np.float32)
    last = 0.0
    for index in range(len(traces) - 1, -1, -1):
        value = float(traces[index]["value_prediction"])
        next_value = 0.0 if index == len(traces) - 1 else float(traces[index + 1]["value_prediction"])
        delta = float(rewards[index]) + gamma * next_value - value
        last = delta + gamma * lam * last
        advantage[index] = last
    returns = advantage + np.asarray([trace["value_prediction"] for trace in traces], dtype=np.float32)
    return advantage, returns


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--seed-start", type=int, default=1132000)
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--lambda-gae", type=float, default=0.95)
    parser.add_argument("--forced-expert", type=int)
    parser.add_argument("--worker-temperature", type=float, default=1.0)
    parser.add_argument("--router-temperature", type=float, default=1.0)
    parser.add_argument("--router-deterministic", action="store_true")
    parser.add_argument("--terminal-mode", choices=("sign", "smooth"), default="sign")
    parser.add_argument("--margin-scale", type=float, default=25000.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    all_traces = []
    rows = []
    rng = np.random.default_rng(args.seed_start)
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            policy = V113Policy(args.checkpoint, forced_expert=args.forced_expert)
            rival = resolve_opponent(args.opponent, f"v113_rollout_opponent_{seed}_{seat}")
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            traces = []
            shaping = []
            while not env.done:
                observations = agent_observations(env)
                action, trace = policy.act(
                    observations[seat], rng, deterministic=False,
                    router_deterministic=args.router_deterministic,
                    router_temperature=args.router_temperature,
                    worker_temperature=args.worker_temperature,
                )
                actions = [None, None]
                actions[seat] = action
                actions[1 - seat] = call_opponent(rival, observations[1 - seat], env.configuration)
                before = potential(observations[seat])
                env.step(actions)
                after = 0.0 if env.done else potential(agent_observations(env)[seat])
                shaping.append(args.gamma * after - before)
                traces.append(trace)
            rewards = [float(state.reward or 0.0) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            if args.margin_scale <= 0:
                parser.error("--margin-scale must be positive")
            if args.terminal_mode == "smooth":
                terminal_objective = np.tanh(margin / args.margin_scale)
            else:
                terminal_objective = (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)) + 0.05 * np.tanh(margin / args.margin_scale)
            shaping[-1] += terminal_objective
            advantage, returns = finish_gae(traces, shaping, args.gamma, args.lambda_gae)
            for trace, reward, adv, target in zip(traces, shaping, advantage, returns):
                trace["reward"] = np.float32(reward)
                trace["advantage"] = np.float32(adv)
                trace["return_target"] = np.float32(target)
                trace["episode_seed"] = np.int32(seed)
                trace["seat"] = np.int8(seat)
                all_traces.append(trace)
            row = {
                "seed": seed,
                "seat": seat,
                "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat],
                "margin": margin,
                "score": 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0),
                "steps": len(traces),
                "statuses": [str(state.status) for state in env.state],
            }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    keys = sorted(all_traces[0])
    arrays = {key: np.asarray([trace[key] for trace in all_traces]) for key in keys}
    advantage_std = max(1e-6, float(arrays["advantage"].std()))
    arrays["advantage"] = (arrays["advantage"] - arrays["advantage"].mean()) / advantage_std
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-rollout-v1",
        "checkpoint": str(args.checkpoint),
        "opponent": str(args.opponent),
        "games": len(rows),
        "transitions": len(all_traces),
        "score_rate": float(np.mean([row["score"] for row in rows])),
        "mean_margin": float(np.mean([row["margin"] for row in rows])),
        "done_done": sum(row["statuses"] == ["DONE", "DONE"] for row in rows),
        "forced_expert": args.forced_expert,
        "worker_temperature": args.worker_temperature,
        "router_temperature": args.router_temperature,
        "router_deterministic": args.router_deterministic,
        "terminal_mode": args.terminal_mode,
        "margin_scale": args.margin_scale,
        "elapsed_seconds": time.time() - started,
        "rows": rows,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("games", "transitions", "score_rate", "mean_margin", "done_done", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
