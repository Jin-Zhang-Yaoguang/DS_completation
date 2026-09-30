#!/usr/bin/env python3
"""Engineering, safety, action-change and relative-latency smoke for V85."""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


POLICIES = {"candidate": HERE / "main.py", "parent": MODEL / "v76_adjacent_safe_buy_lead/main.py"}
OPPONENTS = {"v21": MODEL / "v21_top_meta_moe/main.py", "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py"}
SEEDS = (85001, 85002, 85003, 85004)


def validate(action, obs):
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    return int(not isinstance(action, dict) or len(action.get("market", []) or []) > 10
               or len(action.get("hands", []) or []) != expected)


def play(task):
    mode, family, seed, seat = task
    registry = Registry(path=HERE / "engineering_registry.json", models={}, raw={})
    own = create_agent(registry, {"id": f"{mode}_{family}_{seed}_{seat}_{os.getpid()}",
                                  "kind": "python", "path": str(POLICIES[mode]), "entrypoint": "agent"})
    rival = create_agent(registry, {"id": f"opp_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
                                    "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent"})
    agents = [None, None]
    agents[seat], agents[1 - seat] = own, rival
    game = kagsim.Game(seed)
    latency, violations, calls = [], 0, 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        t0 = time.perf_counter_ns()
        own_action = agents[seat](observations[seat])
        latency.append((time.perf_counter_ns() - t0) / 1e6)
        rival_action = agents[1 - seat](observations[1 - seat])
        actions = [None, None]
        actions[seat], actions[1 - seat] = own_action, rival_action
        violations += validate(own_action, observations[seat])
        game.step(actions[0], actions[1])
        calls += 1
    return {"mode": mode, "family": family, "seed": seed, "seat": seat,
            "calls": calls, "violations": violations,
            "own": float(game.reward(seat)), "opponent": float(game.reward(1 - seat)),
            "latency_ms": latency}


def percentile(values, p):
    values = sorted(values)
    i = (len(values) - 1) * p
    lo, hi = math.floor(i), math.ceil(i)
    return values[lo] if lo == hi else values[lo] * (hi - i) + values[hi] * (i - lo)


def main():
    tasks = [(mode, family, seed, seat) for mode in POLICIES for family in OPPONENTS
             for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    by_key = {(r["mode"], r["family"], r["seed"], r["seat"]): r for r in rows}
    changed = sum(
        (r["own"], r["opponent"]) !=
        (by_key["parent", r["family"], r["seed"], r["seat"]]["own"],
         by_key["parent", r["family"], r["seed"], r["seat"]]["opponent"])
        for r in rows if r["mode"] == "candidate")
    latencies = {mode: [x for r in rows if r["mode"] == mode for x in r["latency_ms"]]
                 for mode in POLICIES}
    p99 = {mode: percentile(values, 0.99) for mode, values in latencies.items()}
    result = {
        "schema": "kaggriculture-v85-engineering-qa-v1", "engine": str(kagsim.ENGINE_VERSION),
        "games": len(rows), "candidate_games": sum(r["mode"] == "candidate" for r in rows),
        "changed_reward_games": changed,
        "all_719_calls": all(r["calls"] == 719 for r in rows),
        "safety_violations": sum(r["violations"] for r in rows),
        "p99_latency_ms": p99,
        "relative_p99": p99["candidate"] / max(p99["parent"], 1e-9),
        "absolute_latency_gate_ms": 250.0, "relative_latency_gate": 1.25,
    }
    result["gate"] = "PASS" if (result["all_719_calls"] and result["safety_violations"] == 0
        and result["changed_reward_games"] > 0 and p99["candidate"] < 250
        and result["relative_p99"] <= 1.25) else "FAIL"
    result["rows"] = rows
    (HERE / "engineering_qa_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
