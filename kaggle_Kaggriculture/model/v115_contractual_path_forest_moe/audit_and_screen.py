#!/usr/bin/env python3
"""V115 static originality audit and synthetic paired preconstruction screen."""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
from collections import defaultdict
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore


POLICIES = {
    "full": HERE / "main.py",
    "ablation": HERE / "ablation_main.py",
    "expert_default": HERE / "expert_default_main.py",
    "expert_yarn": HERE / "expert_yarn_main.py",
    "expert_dairy": HERE / "expert_dairy_main.py",
    "expert_smoothie": HERE / "expert_smoothie_main.py",
    "comparator": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
EXPERT_MODES = ("expert_default", "expert_yarn", "expert_dairy", "expert_smoothie")


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def game_score(margin):
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def validate(action, obs):
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    return int(
        not isinstance(action, dict)
        or set(action) - {"farmer", "hands", "market"}
        or not isinstance(action.get("farmer"), list)
        or not isinstance(action.get("hands"), list)
        or not isinstance(action.get("market"), list)
        or len(action.get("market", []) or []) > 10
        or len(action.get("hands", []) or []) != expected
    )


def play(task):
    mode, family, seed, seat = task
    own = load(POLICIES[mode], f"v115_{mode}_{family}_{seed}_{seat}_{os.getpid()}")
    rival = load(OPPONENTS[family], f"opp_{mode}_{family}_{seed}_{seat}_{os.getpid()}")
    game = kagsim.Game(seed)
    calls = violations = 0
    latencies = []
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions = [None, None]
        started = time.perf_counter()
        actions[seat] = own.agent(observations[seat])
        latencies.append((time.perf_counter() - started) * 1000.0)
        actions[1 - seat] = rival.agent(observations[1 - seat])
        violations += validate(actions[seat], observations[seat])
        game.step(actions[0], actions[1])
        calls += 1
    own_reward = float(game.reward(seat))
    opponent_reward = float(game.reward(1 - seat))
    margin = own_reward - opponent_reward
    status = own.model_status() if mode != "comparator" else {}
    state = (status.get("stats") or {}).get(seat, {}) if isinstance(status, dict) else {}
    stats = state.get("stats", {}) if isinstance(state, dict) else {}
    latencies.sort()
    p99_index = min(len(latencies) - 1, int(0.99 * len(latencies)))
    return {
        "mode": mode,
        "family": family,
        "seed": seed,
        "seat": seat,
        "own": own_reward,
        "opponent": opponent_reward,
        "margin": margin,
        "score": game_score(margin),
        "calls": calls,
        "violations": violations,
        "latency_p99_ms": latencies[p99_index] if latencies else 0.0,
        "latency_max_ms": max(latencies) if latencies else 0.0,
        "stats": stats,
    }


def paired(rows, left, right, opponents):
    indexed = {(row["mode"], row["family"], row["seed"], row["seat"]): row for row in rows}
    deltas = []
    margin_deltas = []
    for family in opponents:
        keys = sorted((row["seed"], row["seat"]) for row in rows if row["mode"] == left and row["family"] == family)
        for seed, seat in keys:
            a = indexed[left, family, seed, seat]
            b = indexed[right, family, seed, seat]
            deltas.append(float(a["score"]) - float(b["score"]))
            margin_deltas.append(float(a["margin"]) - float(b["margin"]))
    return {
        "uplift_pp": 100.0 * statistics.mean(deltas),
        "positive_zero_negative": [
            sum(value > 0 for value in deltas),
            sum(value == 0 for value in deltas),
            sum(value < 0 for value in deltas),
        ],
        "mean_margin_delta": statistics.mean(margin_deltas),
    }


def static_audit():
    source = (HERE / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = sorted({node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)})
    from_imports = sorted({node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)})
    agent_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "agent"]
    forbidden = [
        token for token in ("importlib", "spec_from_file", "load_parent", "parent_agent", "_PARENT_AGENT", "v76.agent")
        if token in source
    ]
    allowed = {"base64", "copy", "json", "zlib"}
    external = [name for name in imports + from_imports if name not in allowed]
    return {
        "agent_definition_count": len(agent_defs),
        "imports": imports + from_imports,
        "external_imports": external,
        "forbidden_tokens": forbidden,
        "complete_agent_call_detected": bool(forbidden or external or len(agent_defs) != 1),
    }


def summarize(rows, seeds):
    mode_scores = {
        mode: statistics.mean(row["score"] for row in rows if row["mode"] == mode)
        for mode in POLICIES
    }
    by_family = {
        mode: {
            family: statistics.mean(row["score"] for row in rows if row["mode"] == mode and row["family"] == family)
            for family in OPPONENTS
        }
        for mode in POLICIES
    }
    best_expert = max(EXPERT_MODES, key=lambda mode: mode_scores[mode])
    beu = paired(rows, "full", best_expert, OPPONENTS)
    mcu = paired(rows, "full", "ablation", OPPONENTS)
    pou = paired(rows, "full", "comparator", OPPONENTS)
    full_rows = [row for row in rows if row["mode"] == "full"]
    comparator_rows = [row for row in rows if row["mode"] == "comparator"]
    commitment_games = defaultdict(int)
    route_games = defaultdict(int)
    for row in full_rows:
        for route, count in (row.get("stats", {}).get("commitments", {}) or {}).items():
            commitment_games[route] += int(int(count) > 0)
        for route, count in (row.get("stats", {}).get("route_calls", {}) or {}).items():
            route_games[route] += int(int(count) > 0)
    full_catastrophic = statistics.mean(row["margin"] < -10000 for row in full_rows)
    comparator_catastrophic = statistics.mean(row["margin"] < -10000 for row in comparator_rows)
    architecture = static_audit()
    all_719 = all(row["calls"] == 719 for row in rows)
    safety_violations = sum(row["violations"] for row in rows)
    expert_coverage = all(commitment_games.get(route, 0) >= 8 for route in ("yarn", "dairy", "smoothie"))
    latency_p99 = max(row["latency_p99_ms"] for row in full_rows)
    latency_max = max(row["latency_max_ms"] for row in full_rows)
    changed_calls = sum(int(row.get("stats", {}).get("changed_calls", 0)) for row in full_rows)
    fallback_calls = sum(int(row.get("stats", {}).get("fallback", 0)) for row in full_rows)
    preconstruction_pass = (
        not architecture["complete_agent_call_detected"]
        and all_719
        and safety_violations == 0
        and fallback_calls == 0
        and expert_coverage
        and changed_calls > 0
        and beu["uplift_pp"] > 0
        and beu["positive_zero_negative"][0] > beu["positive_zero_negative"][2]
        and mcu["uplift_pp"] > 0
        and mcu["positive_zero_negative"][0] > mcu["positive_zero_negative"][2]
        and mode_scores["full"] >= 0.60
        and by_family["full"]["v76"] >= 0.50
        and full_catastrophic <= comparator_catastrophic + 0.01
        and latency_p99 < 250.0
        and latency_max < 1000.0
    )
    return {
        "schema": "kaggriculture-v115-preconstruction-audit-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "official_replay_sources_consumed": 0,
        "synthetic_seed_range": [min(seeds), max(seeds)],
        "games": len(rows),
        "static_architecture_audit": architecture,
        "score_rate": mode_scores,
        "score_rate_by_opponent": by_family,
        "best_fixed_expert": best_expert,
        "best_expert_uplift": beu,
        "mechanism_contribution_uplift": mcu,
        "paired_originality_uplift_vs_v76": pou,
        "direct_v76_score_rate": by_family["full"]["v76"],
        "candidate_catastrophic_rate": full_catastrophic,
        "comparator_catastrophic_rate": comparator_catastrophic,
        "catastrophic_rate_delta_pp": 100.0 * (full_catastrophic - comparator_catastrophic),
        "route_game_coverage": dict(route_games),
        "commitment_game_coverage": dict(commitment_games),
        "expert_coverage_gate": expert_coverage,
        "changed_sell_controller_calls": changed_calls,
        "fallback_calls_full": fallback_calls,
        "all_719_calls": all_719,
        "safety_violations": safety_violations,
        "latency_p99_upper_ms": latency_p99,
        "latency_max_ms": latency_max,
        "decision": "PASS_PRECONSTRUCTION" if preconstruction_pass else "REJECT_PRECONSTRUCTION",
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=115101)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    seeds = tuple(range(args.seed_start, args.seed_start + args.seeds))
    tasks = [
        (mode, family, seed, seat)
        for mode in POLICIES
        for family in OPPONENTS
        for seed in seeds
        for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    payload = summarize(rows, seeds)
    (HERE / "preconstruction_audit_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

