"""Search V1 low/high route mixtures for an independent opening template.

This deliberately does not read champion Replay routes. Each candidate is a
copy of the existing V1 low route with a subset of steps 72..87 replaced by
the existing high-route action. It is a small expert-search pilot used to
create candidate route labels for PPO, not an online submission.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np

import base_agent


def _copy_route(route):
    return copy.deepcopy(route)


def _candidate_route(mask):
    low = _copy_route(base_agent._LOW_ROUTE_ACTIONS)
    high = base_agent._HIGH_ROUTE_ACTIONS
    for offset, selected in enumerate(mask):
        if selected:
            low[72 + offset] = copy.deepcopy(high[72 + offset])
    return low


def _play(seed, seat, route):
    from kaggle_environments import make
    from train_ppo import _fixed_opponent

    opponent = _fixed_opponent("v3")
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        base_agent._ACTIONS = route
        own = base_agent._CORE_AGENT(env.state[seat].observation)
        other = opponent(env.state[1 - seat].observation)
        env.step([own, other] if seat == 0 else [other, own])
    rewards = [float(state.reward or 0.0) for state in env.state]
    own, other = (rewards[seat], rewards[1 - seat])
    return {"score": 1.0 if own > other else 0.0 if own < other else 0.5,
            "margin": own - other, "status": [str(state.status) for state in env.state]}


def evaluate(mask, seeds):
    rows = [_play(seed, seat, _candidate_route(mask)) for seed in seeds for seat in (0, 1)]
    return {
        "mask": [int(x) for x in mask], "games": len(rows),
        "score_rate": float(np.mean([row["score"] for row in rows])),
        "mean_margin": float(np.mean([row["margin"] for row in rows])),
        "errors": sum(row["status"] != ["DONE", "DONE"] for row in rows),
    }


def search(seed_start, seeds_count, population, output):
    seeds = [int(seed_start + i * 7919) for i in range(seeds_count)]
    rng = np.random.default_rng(20260819)
    masks = [np.zeros(16, dtype=np.int8), np.ones(16, dtype=np.int8)]
    while len(masks) < population:
        masks.append(rng.integers(0, 2, size=16, dtype=np.int8))
    results = []
    for index, mask in enumerate(masks):
        result = evaluate(mask, seeds)
        result["index"] = index
        results.append(result)
        print(json.dumps({"completed": index + 1, "population": len(masks), **result}), flush=True)
    results.sort(key=lambda row: (row["score_rate"], row["mean_margin"]), reverse=True)
    report = {
        "schema": "kaggriculture-ppo-v2-opening-mix-search-1",
        "seed_start": seed_start, "seeds": seeds_count, "games_per_candidate": seeds_count * 2,
        "segment": [72, 87], "source_routes": ["v1_low", "v1_high"],
        "results": results, "best": results[0],
        "holdout_policy": "synthetic route search only; no champion Replay",
    }
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=98900000)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--population", type=int, default=16)
    parser.add_argument("--output", type=Path, default=Path("opening_mix_search.json"))
    args = parser.parse_args()
    print(json.dumps(search(args.seed_start, args.seeds, args.population, args.output), ensure_ascii=False, indent=2))
