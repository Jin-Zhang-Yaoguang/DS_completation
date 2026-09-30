#!/usr/bin/env python3
"""Frozen V71 mechanism smoke against all active gold gates."""

from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


POLICIES = {"candidate": HERE / "main.py", "parent": MODEL / "v70_duplicate_wheat_buy_lead/main.py"}
OPPONENTS = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v33": MODEL / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL / "v46_full_terminal_front_run/main.py",
    "v51": MODEL / "v51_post_action_terminal_sell/main.py",
    "v52": MODEL / "v52_terminal_route_acceleration/main.py",
    "v53": MODEL / "v53_terminal_access_flush/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v70": MODEL / "v70_duplicate_wheat_buy_lead/main.py",
}
SEEDS = range(71001, 71009)


def score(value):
    return 1.0 if value > 0 else 0.5 if value == 0 else 0.0


def play(task):
    mode, family, seed, seat = task
    registry = Registry(path=HERE / "smoke_registry.json", models={}, raw={})
    own = create_agent(registry, {"id": f"{mode}_{family}_{seed}_{seat}_{os.getpid()}", "kind": "python", "path": str(POLICIES[mode]), "entrypoint": "agent"})
    rival = create_agent(registry, {"id": f"opp_{mode}_{family}_{seed}_{seat}_{os.getpid()}", "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent"})
    agents = [None, None]
    agents[seat], agents[1 - seat] = own, rival
    game = kagsim.Game(seed)
    while not game.done:
        obs = [game.observe(0), game.observe(1)]
        game.step(agents[0](obs[0]), agents[1](obs[1]))
    return {
        "mode": mode, "family": family, "seed": seed, "seat": seat,
        "own": float(game.reward(seat)), "opponent": float(game.reward(1 - seat)),
        "margin": float(game.reward(seat)) - float(game.reward(1 - seat)),
    }


def main():
    tasks = [(mode, family, seed, seat) for mode in POLICIES for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    parent = {(row["family"], row["seed"], row["seat"]): row for row in rows if row["mode"] == "parent"}
    deltas = []
    for row in rows:
        if row["mode"] == "candidate":
            prior = parent[(row["family"], row["seed"], row["seat"])]
            deltas.append((score(row["margin"]) - score(prior["margin"]), row["margin"] - prior["margin"]))
    candidate = [row for row in rows if row["mode"] == "candidate"]
    result = {
        "schema": "kaggriculture-v71-mechanism-smoke-v1", "engine": str(kagsim.ENGINE_VERSION),
        "games": len(rows), "candidate_games": len(candidate),
        "changed_reward_games": sum(
            row["own"] != parent[(row["family"], row["seed"], row["seat"])]["own"]
            or row["opponent"] != parent[(row["family"], row["seed"], row["seat"])]["opponent"]
            for row in candidate
        ),
        "score_uplift_pp": 100 * statistics.mean(value[0] for value in deltas),
        "positive_zero_negative": [sum(value[0] > 0 for value in deltas), sum(value[0] == 0 for value in deltas), sum(value[0] < 0 for value in deltas)],
        "mean_margin_delta": statistics.mean(value[1] for value in deltas), "rows": rows,
    }
    result["gate"] = "PASS" if result["changed_reward_games"] > 0 and result["score_uplift_pp"] >= 0 and result["positive_zero_negative"][2] == 0 else "FAIL"
    (HERE / "mechanism_smoke_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
