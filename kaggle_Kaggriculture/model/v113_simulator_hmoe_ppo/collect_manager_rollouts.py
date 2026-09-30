"""Collect 30-decision Manager trajectories with frozen deterministic Workers."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
import numpy as np

import action_space as space
from collect_rollouts import agent_observations, call_opponent, potential, resolve_opponent
from policy import V113Policy


MODEL_KEYS = ("global", "board", "units", "unit_mask")


def manager_gae(traces, rewards, gamma, lam):
    advantage = np.zeros((len(traces),), dtype=np.float32)
    last = 0.0
    for index in range(len(traces) - 1, -1, -1):
        value = float(traces[index]["value_prediction"])
        next_value = 0.0 if index == len(traces) - 1 else float(traces[index + 1]["value_prediction"])
        delta = rewards[index] + gamma * next_value - value
        last = delta + gamma * lam * last
        advantage[index] = last
    return advantage, advantage + np.asarray([trace["value_prediction"] for trace in traces], dtype=np.float32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent", default="builtin:pass")
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--seed-start", type=int, default=1138000)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--lambda-gae", type=float, default=0.95)
    parser.add_argument("--router-temperature", type=float, default=3.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    rng = np.random.default_rng(args.seed_start)
    all_rows = []
    games = []
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            policy = V113Policy(args.checkpoint)
            rival = resolve_opponent(args.opponent, f"v113_manager_opponent_{seed}_{seat}")
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            day_traces = []
            day_rewards = []
            current_day = -1
            day_start_potential = None
            while not env.done:
                observations = agent_observations(env)
                day = int(space.get(observations[seat], "step", len(env.steps) - 1) or 0) // 24
                new_day = day != current_day
                action, trace = policy.act(
                    observations[seat], rng, deterministic=False,
                    router_deterministic=False, worker_deterministic=True,
                    router_temperature=args.router_temperature,
                )
                if new_day:
                    if day_rewards:
                        day_rewards[-1] += args.gamma * potential(observations[seat]) - day_start_potential
                    current_day = day
                    day_traces.append(trace)
                    day_rewards.append(0.0)
                    day_start_potential = potential(observations[seat])
                actions = [None, None]
                actions[seat] = action
                actions[1 - seat] = call_opponent(rival, observations[1 - seat], env.configuration)
                env.step(actions)
            terminal = [float(state.reward or 0.0) for state in env.state]
            margin = terminal[seat] - terminal[1 - seat]
            day_rewards[-1] -= day_start_potential
            day_rewards[-1] += (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)) + 0.05 * np.tanh(margin / 25000.0)
            advantage, returns = manager_gae(day_traces, day_rewards, args.gamma, args.lambda_gae)
            for trace, reward, adv, target in zip(day_traces, day_rewards, advantage, returns):
                all_rows.append({
                    **{key: trace[key] for key in MODEL_KEYS},
                    "expert": trace["expert"],
                    "old_logprob": trace["router_logprob"],
                    "old_value": trace["value_prediction"],
                    "reward": np.float32(reward),
                    "advantage": np.float32(adv),
                    "return_target": np.float32(target),
                    "seed": np.int32(seed),
                    "seat": np.int8(seat),
                })
            game = {
                "seed": seed, "seat": seat, "candidate_reward": terminal[seat],
                "opponent_reward": terminal[1 - seat], "margin": margin,
                "score": 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0),
                "expert_days": dict(Counter(int(trace["expert"]) for trace in day_traces)),
            }
            games.append(game)
            print(json.dumps(game, ensure_ascii=False), flush=True)
    arrays = {key: np.asarray([row[key] for row in all_rows]) for key in all_rows[0]}
    arrays["advantage"] = (arrays["advantage"] - arrays["advantage"].mean()) / max(1e-6, float(arrays["advantage"].std()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-manager-rollout-v1",
        "games": len(games), "manager_transitions": len(all_rows),
        "score_rate": float(np.mean([row["score"] for row in games])),
        "mean_candidate_reward": float(np.mean([row["candidate_reward"] for row in games])),
        "mean_margin": float(np.mean([row["margin"] for row in games])),
        "router_temperature": args.router_temperature,
        "elapsed_seconds": time.time() - started, "rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("games", "manager_transitions", "score_rate", "mean_candidate_reward", "mean_margin", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
