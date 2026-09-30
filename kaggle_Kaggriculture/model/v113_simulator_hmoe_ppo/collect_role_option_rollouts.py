"""Collect fresh-seed PPO trajectories for V113's role-target option policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
import numpy as np

from collect_rollouts import (
    agent_observations, asset_value, call_opponent, finish_gae, resolve_opponent,
)
from policy_role_option import RoleOptionV113Policy


def scale_potential(obs) -> float:
    """Unbounded-log economic potential that still distinguishes gold-scale economies."""
    return float(np.log1p(max(0.0, asset_value(obs)) / 3000.0))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent", default="builtin:pass")
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--seed-start", type=int, default=1165000)
    parser.add_argument("--worker-temperature", type=float, default=0.2)
    parser.add_argument("--manager-temperature", type=float, default=0.5)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--lambda-gae", type=float, default=0.95)
    parser.add_argument("--margin-scale", type=float, default=25000.0)
    parser.add_argument("--scale-worker-cap", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.margin_scale <= 0:
        parser.error("--margin-scale must be positive")
    started = time.time()
    rng = np.random.default_rng(args.seed_start)
    all_traces, games = [], []
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            policy = RoleOptionV113Policy(
                args.checkpoint, forced_unit_expert=5, forced_market_expert=5,
                coupled_product_router=True, router_period=720,
                scale_worker_cap=args.scale_worker_cap,
            )
            opponent = resolve_opponent(args.opponent, f"v113_role_option_ppo_opponent_{seed}_{seat}")
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            traces, shaping = [], []
            while not env.done:
                observations = agent_observations(env)
                before = scale_potential(observations[seat])
                action, trace = policy.sample(
                    observations[seat], rng,
                    worker_temperature=args.worker_temperature,
                    manager_temperature=args.manager_temperature,
                )
                actions = [None, None]
                actions[seat] = action
                actions[1 - seat] = call_opponent(opponent, observations[1 - seat], env.configuration)
                env.step(actions)
                if env.done:
                    after = 0.0
                else:
                    after = scale_potential(agent_observations(env)[seat])
                shaping.append(args.gamma * after - before)
                traces.append(trace)
            rewards = [float(state.reward or 0.0) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            # Replace the terminal disappearance of state by the observable final score.
            shaping[-1] += float(np.log1p(max(0.0, rewards[seat]) / 3000.0))
            shaping[-1] += 0.25 * float(np.tanh(margin / args.margin_scale))
            advantage, returns = finish_gae(traces, shaping, args.gamma, args.lambda_gae)
            for trace, reward, adv, target in zip(traces, shaping, advantage, returns):
                trace["reward"] = np.float32(reward)
                trace["advantage"] = np.float32(adv)
                trace["return_target"] = np.float32(target)
                trace["episode_seed"] = np.int32(seed)
                trace["seat"] = np.int8(seat)
                all_traces.append(trace)
            game = {
                "seed": seed, "seat": seat, "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat], "margin": margin,
                "score": 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0),
                "statuses": [str(state.status) for state in env.state],
                "operation_counts": dict(policy.operation_counts),
            }
            games.append(game)
            print(json.dumps(game, ensure_ascii=False), flush=True)
    arrays = {key: np.asarray([trace[key] for trace in all_traces]) for key in sorted(all_traces[0])}
    advantage_std = max(1e-6, float(arrays["advantage"].std()))
    arrays["advantage"] = (arrays["advantage"] - arrays["advantage"].mean()) / advantage_std
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-role-option-rollout-v1",
        "checkpoint": str(args.checkpoint), "opponent": args.opponent,
        "games": len(games), "transitions": len(all_traces),
        "score_rate": float(np.mean([game["score"] for game in games])),
        "mean_candidate_reward": float(np.mean([game["candidate_reward"] for game in games])),
        "mean_margin": float(np.mean([game["margin"] for game in games])),
        "done_done": sum(game["statuses"] == ["DONE", "DONE"] for game in games),
        "worker_temperature": args.worker_temperature,
        "manager_temperature": args.manager_temperature,
        "potential": "log1p(asset_value/3000)",
        "elapsed_seconds": time.time() - started, "rows": games,
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in (
        "games", "transitions", "score_rate", "mean_candidate_reward", "mean_margin",
        "done_done", "elapsed_seconds",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
