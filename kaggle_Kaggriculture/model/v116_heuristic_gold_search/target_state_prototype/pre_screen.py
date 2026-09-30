#!/usr/bin/env python3
"""Run the 8-seed x 6-anchor x dual-seat V116 prototype screen."""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore


OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(action, obs):
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    return int(
        not isinstance(action, dict)
        or set(action) - {"farmer", "hands", "market"}
        or not isinstance(action.get("farmer"), list)
        or not isinstance(action.get("hands"), list)
        or not isinstance(action.get("market"), list)
        or len(action.get("hands", [])) != expected
        or len(action.get("market", [])) > 10
    )


def play(task):
    family, seed, seat = task
    own = load(HERE / "main.py", f"v116_{family}_{seed}_{seat}_{os.getpid()}")
    rival = load(OPPONENTS[family], f"opponent_{family}_{seed}_{seat}_{os.getpid()}")
    game = kagsim.Game(seed)
    calls = violations = 0
    latency = []
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions = [None, None]
        started = time.perf_counter()
        actions[seat] = own.agent(observations[seat])
        latency.append((time.perf_counter() - started) * 1000.0)
        actions[1 - seat] = rival.agent(observations[1 - seat])
        violations += validate(actions[seat], observations[seat])
        game.step(actions[0], actions[1])
        calls += 1
    own_reward = float(game.reward(seat))
    rival_reward = float(game.reward(1 - seat))
    margin = own_reward - rival_reward
    status = own.model_status()
    stats = (status.get("stats") or {}).get(seat, {})
    latency.sort()
    return {
        "opponent": family,
        "seed": seed,
        "seat": seat,
        "own_reward": own_reward,
        "opponent_reward": rival_reward,
        "margin": margin,
        "win": int(margin > 0),
        "tie": int(margin == 0),
        "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
        "calls": calls,
        "violations": violations,
        "latency_p99_ms": latency[min(len(latency) - 1, int(0.99 * len(latency)))] if latency else 0.0,
        "stats": stats,
    }


def static_audit():
    source = (HERE / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    agent_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "agent"]
    forbidden = [
        token for token in (
            "_ACTIONS", "reference_actions", "copy_action", "importlib", "spec_from_file",
            "parent_agent", "load_parent", "v76.agent",
        ) if token in source
    ]
    return {
        "agent_definition_count": len(agent_defs),
        "forbidden_tokens": forbidden,
        "embedded_action_stream_detected": any(
            isinstance(node, (ast.List, ast.Tuple)) and len(node.elts) >= 700 for node in ast.walk(tree)
        ),
        "pass": len(agent_defs) == 1 and not forbidden,
    }


def summarize(rows, seeds):
    by_opponent = {}
    for family in OPPONENTS:
        subset = [row for row in rows if row["opponent"] == family]
        by_opponent[family] = {
            "games": len(subset),
            "pure_win_rate": statistics.mean(row["win"] for row in subset),
            "score_rate": statistics.mean(row["score"] for row in subset),
            "mean_margin": statistics.mean(row["margin"] for row in subset),
        }
    routes = {}
    unit_experts = {}
    fallback = safety_rewrites = 0
    for row in rows:
        stats = row.get("stats") or {}
        for key, value in (stats.get("routes") or {}).items():
            routes[key] = routes.get(key, 0) + int(value)
        for key, value in (stats.get("unit_experts") or {}).items():
            unit_experts[key] = unit_experts.get(key, 0) + int(value)
        fallback += int(stats.get("fallback", 0) or 0)
        safety_rewrites += int(stats.get("safety_rewrites", 0) or 0)
    pure_win = statistics.mean(row["win"] for row in rows)
    score = statistics.mean(row["score"] for row in rows)
    audit = static_audit()
    return {
        "schema": "kaggriculture-v116-target-state-prototype-screen-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_range": [min(seeds), max(seeds)],
        "opponents": list(OPPONENTS),
        "games": len(rows),
        "pure_win_rate": pure_win,
        "score_rate": score,
        "mean_margin": statistics.mean(row["margin"] for row in rows),
        "by_opponent": by_opponent,
        "all_719_calls": all(row["calls"] == 719 for row in rows),
        "schema_violations": sum(row["violations"] for row in rows),
        "fallback_calls": fallback,
        "safety_rewrites": safety_rewrites,
        "latency_p99_upper_ms": max(row["latency_p99_ms"] for row in rows),
        "route_calls": routes,
        "unit_expert_calls": unit_experts,
        "static_audit": audit,
        "gold_75pct_screen": pure_win >= 0.75 and audit["pass"] and not sum(row["violations"] for row in rows),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=116301)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    seeds = tuple(range(args.seed_start, args.seed_start + args.seeds))
    tasks = [(family, seed, seat) for family in OPPONENTS for seed in seeds for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    payload = summarize(rows, seeds)
    (HERE / "pre_screen_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
