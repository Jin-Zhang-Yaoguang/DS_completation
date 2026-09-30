#!/usr/bin/env python3
"""Exact official-1.32.7 versus cppsim QA for the searched block executor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import optimizer


PASS = {"farmer": ["PASS"], "hands": [], "market": []}


def full_observation(env, seat: int):
    shared = env.state[0].observation
    obs = dict(env.state[seat].observation)
    for key, value in shared.items():
        if obs.get(key) is None and key != "player":
            obs[key] = value
    return obs


def cpp_episode(genome, seed: int, seat: int):
    game = optimizer.KAGSIM.Game(seed)
    agent = optimizer.make_agent(genome)
    actions = []
    while not game.done:
        action = agent.act(game.observe(seat))
        actions.append(action)
        pair = [PASS, PASS]
        pair[seat] = action
        game.step(pair[0], pair[1])
    return [float(game.reward(0)), float(game.reward(1))], actions


def official_episode(genome, seed: int, seat: int):
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    env.reset(2)
    agent = optimizer.make_agent(genome)
    actions = []
    while not env.done:
        action = agent.act(full_observation(env, seat))
        actions.append(action)
        pair = [dict(PASS), dict(PASS)]
        pair[seat] = action
        env.step(pair)
    return [float(env.state[0].reward or 0), float(env.state[1].reward or 0)], actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--genome", type=Path, default=Path(__file__).with_name("best_genome.json"))
    parser.add_argument("--seeds", default="5000,5001")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("parity_report.json"))
    args = parser.parse_args()
    genome = json.loads(args.genome.read_text())
    rows = []
    for seed in [int(x) for x in args.seeds.split(",") if x]:
        for seat in (0, 1):
            cpp_reward, cpp_actions = cpp_episode(genome, seed, seat)
            off_reward, off_actions = official_episode(genome, seed, seat)
            first_diff = next((i for i, (a, b) in enumerate(zip(cpp_actions, off_actions)) if a != b), None)
            rows.append({"seed": seed, "seat": seat, "cpp_reward": cpp_reward,
                         "official_reward": off_reward, "reward_exact": cpp_reward == off_reward,
                         "actions_exact": first_diff is None and len(cpp_actions) == len(off_actions),
                         "first_action_diff": first_diff, "calls": len(cpp_actions)})
    result = {"engine": "1.32.7", "games": len(rows), "rows": rows,
              "all_reward_exact": all(r["reward_exact"] for r in rows),
              "all_actions_exact": all(r["actions_exact"] for r in rows)}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_reward_exact"] and result["all_actions_exact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
