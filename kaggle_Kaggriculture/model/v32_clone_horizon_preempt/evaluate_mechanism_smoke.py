#!/usr/bin/env python3
"""Frozen V32 mechanism smoke against the three active gold lineages."""

from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


POLICIES = {
    "candidate": HERE / "main.py",
    "parent": MODEL / "v21_top_meta_moe/main.py",
}
OPPONENTS = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
}
SEEDS = list(range(32001, 32009))


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def play(task: tuple[str, str, int, int]) -> dict[str, object]:
    mode, family, seed, seat = task
    registry = Registry(path=HERE / "smoke_registry.json", models={}, raw={})
    own = create_agent(registry, {
        "id": f"{mode}_{family}_{seed}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(POLICIES[mode]), "entrypoint": "agent",
    })
    rival = create_agent(registry, {
        "id": f"opp_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    agents = [None, None]
    agents[seat], agents[1 - seat] = own, rival
    game = kagsim.Game(seed)
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    diagnostics = own.diagnostics()
    stats = diagnostics.get("model_status", {}).get("stats", {}).get(str(seat), {})
    if not stats:
        stats = diagnostics.get("model_status", {}).get("stats", {}).get(seat, {})
    return {
        "mode": mode, "family": family, "seed": seed, "seat": seat,
        "own": rewards[seat], "opponent": rewards[1 - seat],
        "margin": rewards[seat] - rewards[1 - seat],
        "preempt_events": int(stats.get("events", 0) or 0),
        "preempt_units": int(stats.get("units", 0) or 0),
    }


def main() -> None:
    tasks = [
        (mode, family, seed, seat)
        for mode in POLICIES for family in OPPONENTS for seed in SEEDS for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    parent = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == "parent"}
    pairs = []
    for row in rows:
        if row["mode"] != "candidate":
            continue
        prior = parent[(row["family"], row["seed"], row["seat"])]
        pairs.append({
            "family": row["family"], "seed": row["seed"], "seat": row["seat"],
            "score_delta": score(float(row["margin"])) - score(float(prior["margin"])),
            "margin_delta": float(row["margin"]) - float(prior["margin"]),
        })
    result = {
        "schema": "kaggriculture-v32-mechanism-smoke-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "seeds": SEEDS,
        "opponents": list(OPPONENTS),
        "games": len(rows),
        "candidate_games": sum(r["mode"] == "candidate" for r in rows),
        "preempt_events": sum(int(r["preempt_events"]) for r in rows if r["mode"] == "candidate"),
        "preempt_units": sum(int(r["preempt_units"]) for r in rows if r["mode"] == "candidate"),
        "score_uplift_pp": 100 * statistics.mean(float(r["score_delta"]) for r in pairs),
        "positive_zero_negative": [
            sum(float(r["score_delta"]) > 0 for r in pairs),
            sum(float(r["score_delta"]) == 0 for r in pairs),
            sum(float(r["score_delta"]) < 0 for r in pairs),
        ],
        "mean_margin_delta": statistics.mean(float(r["margin_delta"]) for r in pairs),
        "rows": rows,
    }
    result["gate"] = "PASS" if (
        result["preempt_events"] > 0
        and result["score_uplift_pp"] >= 0
        and result["positive_zero_negative"][2] == 0
    ) else "FAIL"
    (HERE / "mechanism_smoke_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
