#!/usr/bin/env python3
"""Minimal cppsim 1.32.7 versus official-engine parity QA for Kaito v48/A2."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from paired_live_pool import Kaito_SHA256, load_runtime, model_paths, fresh_agent


SEEDS = (41009357, 1551885668)


class Counter:
    def __init__(self, agent: Any):
        self.agent = agent
        self.calls = 0

    def __call__(self, observation: Any, configuration: Any = None) -> Any:
        self.calls += 1
        return self.agent(observation, configuration)


def agents(paths: dict[str, Path], registry: Any, create_agent: Any, kaito_seat: int) -> list[Counter]:
    kaito = Counter(fresh_agent("kaito_v48", paths, registry, create_agent))
    a2 = Counter(fresh_agent("a2", paths, registry, create_agent))
    return [kaito, a2] if kaito_seat == 0 else [a2, kaito]


def play_cpp(seed: int, kaito_seat: int, paths: dict[str, Path], kagsim: Any, registry: Any, create_agent: Any) -> tuple[list[float], list[int]]:
    live = agents(paths, registry, create_agent, kaito_seat)
    game = kagsim.Game(int(seed))
    while not game.done:
        game.step(live[0](game.observe(0)), live[1](game.observe(1)))
    return [float(game.reward(0)), float(game.reward(1))], [agent.calls for agent in live]


def play_official(seed: int, kaito_seat: int, paths: dict[str, Path], registry: Any, create_agent: Any) -> tuple[list[float], list[int], list[str]]:
    import numpy as np
    from kaggle_environments import make

    random.seed(seed * 104729 + kaito_seat * 1009)
    np.random.seed((seed + kaito_seat * 65537) % (2**32 - 1))
    live = agents(paths, registry, create_agent, kaito_seat)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    env.run(live)
    return (
        [float(state.reward or 0.0) for state in env.state],
        [agent.calls for agent in live],
        [str(state.status) for state in env.state],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kaito-main", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results") / "kaito_a2_cpp_official_qa.json")
    parser.add_argument("--seed-limit", type=int)
    parser.add_argument("--seat", type=int, choices=(0, 1), action="append")
    args = parser.parse_args()
    kagsim, registry, create_agent = load_runtime()
    paths = model_paths(args.kaito_main)
    selected_seeds = SEEDS[: args.seed_limit] if args.seed_limit else SEEDS
    selected_seats = args.seat or [0, 1]
    rows = []
    for seed in selected_seeds:
        for seat in selected_seats:
            cpp_rewards, cpp_calls = play_cpp(seed, seat, paths, kagsim, registry, create_agent)
            official_rewards, official_calls, statuses = play_official(seed, seat, paths, registry, create_agent)
            rows.append(
                {
                    "seed": seed,
                    "kaito_seat": seat,
                    "cpp_rewards": cpp_rewards,
                    "official_rewards": official_rewards,
                    "exact": cpp_rewards == official_rewards,
                    "cpp_calls": cpp_calls,
                    "official_calls": official_calls,
                    "statuses": statuses,
                }
            )
    result = {
        "status": "CPP_L1_OFFICIAL_QA_NOT_FORMAL",
        "cppsim_engine": "1.32.7",
        "kaito_main_sha256": Kaito_SHA256,
        "kaito_license_verified": False,
        "games": len(rows),
        "exact_games": sum(row["exact"] for row in rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["exact_games"] != result["games"]:
        return 1
    if any(row["cpp_calls"] != [719, 719] or row["official_calls"] != [719, 719] for row in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
