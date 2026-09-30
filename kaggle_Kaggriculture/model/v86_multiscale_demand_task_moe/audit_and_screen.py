#!/usr/bin/env python3
"""Static architecture audit plus synthetic full/ablation/comparator screen."""

from __future__ import annotations

import ast
import concurrent.futures
from collections import defaultdict
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore


POLICIES = {
    "full": HERE / "main.py",
    "ablation": HERE / "ablation_main.py",
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
SEEDS = tuple(range(86101, 86117))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score(margin):
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def validate(action, obs):
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    return int(not isinstance(action, dict) or len(action.get("market", []) or []) > 10
               or len(action.get("hands", []) or []) != expected)


def play(task):
    mode, family, seed, seat = task
    own_module = load(POLICIES[mode], f"own_{mode}_{family}_{seed}_{seat}_{os.getpid()}")
    rival_module = load(OPPONENTS[family], f"opp_{mode}_{family}_{seed}_{seat}_{os.getpid()}")
    game = kagsim.Game(seed)
    violations = calls = 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions = [None, None]
        actions[seat] = own_module.agent(observations[seat])
        actions[1 - seat] = rival_module.agent(observations[1 - seat])
        violations += validate(actions[seat], observations[seat])
        game.step(actions[0], actions[1])
        calls += 1
    own, opponent = float(game.reward(seat)), float(game.reward(1 - seat))
    status = own_module.model_status() if mode in {"full", "ablation"} else {}
    stats = (status.get("stats") or {}).get(seat, {}) if isinstance(status, dict) else {}
    return {
        "mode": mode, "family": family, "seed": seed, "seat": seat,
        "own": own, "opponent": opponent, "margin": own - opponent,
        "score": score(own - opponent), "calls": calls, "violations": violations,
        "stats": stats,
    }


def paired(rows, left, right):
    indexed = {(row["mode"], row["family"], row["seed"], row["seat"]): row for row in rows}
    deltas = []
    for family in OPPONENTS:
        for seed in SEEDS:
            for seat in (0, 1):
                a = indexed[left, family, seed, seat]
                b = indexed[right, family, seed, seat]
                deltas.append(a["score"] - b["score"])
    return {
        "uplift_pp": 100 * statistics.mean(deltas),
        "positive_zero_negative": [sum(x > 0 for x in deltas), sum(x == 0 for x in deltas), sum(x < 0 for x in deltas)],
    }


def static_audit():
    source = (HERE / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = sorted({node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)})
    from_imports = sorted({node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)})
    agent_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "agent"]
    forbidden_tokens = [
        token for token in ("importlib", "spec_from_file", "load_parent", "parent_agent", "_PARENT_AGENT", "v76.agent")
        if token in source
    ]
    external_imports = [name for name in imports + from_imports if name not in {"base64", "copy", "json", "math", "zlib"}]
    return {
        "agent_definition_count": len(agent_defs),
        "imports": imports + from_imports,
        "external_imports": external_imports,
        "forbidden_tokens": forbidden_tokens,
        "complete_agent_call_detected": bool(forbidden_tokens or external_imports or len(agent_defs) != 1),
    }


def main():
    tasks = [(mode, family, seed, seat) for mode in POLICIES for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
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
    full_rows = [row for row in rows if row["mode"] == "full"]
    route_games = defaultdict(int)
    for row in full_rows:
        for route, count in (row.get("stats", {}).get("routes", {}) or {}).items():
            route_games[route] += int(int(count) > 0)
    architecture = static_audit()
    full_vs_ablation = paired(rows, "full", "ablation")
    full_vs_comparator = paired(rows, "full", "comparator")
    direct_v76 = by_family["full"]["v76"]
    safety_violations = sum(row["violations"] for row in rows)
    all_719 = all(row["calls"] == 719 for row in rows)
    expert_coverage = all(route_games.get(route, 0) >= 8 for route in ("yarn", "dairy", "smoothie"))
    gate = (
        not architecture["complete_agent_call_detected"]
        and all_719 and safety_violations == 0 and expert_coverage
        and full_vs_ablation["uplift_pp"] > 0
        and full_vs_ablation["positive_zero_negative"][0] > full_vs_ablation["positive_zero_negative"][2]
        and direct_v76 >= 0.25
    )
    payload = {
        "schema": "kaggriculture-v86-preconstruction-audit-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "official_replay_sources_consumed": 0,
        "synthetic_seeds": [min(SEEDS), max(SEEDS)],
        "games": len(rows),
        "static_architecture_audit": architecture,
        "score_rate": mode_scores,
        "score_rate_by_opponent": by_family,
        "full_vs_ablation": full_vs_ablation,
        "full_vs_comparator": full_vs_comparator,
        "direct_v76_score_rate": direct_v76,
        "expert_game_coverage": dict(route_games),
        "expert_coverage_gate": expert_coverage,
        "all_719_calls": all_719,
        "safety_violations": safety_violations,
        "fallback_calls_full": sum(int(row.get("stats", {}).get("fallback", 0)) for row in full_rows),
        "decision": "PASS_PRECONSTRUCTION" if gate else "REJECT_PRECONSTRUCTION",
        "rows": rows,
    }
    (HERE / "preconstruction_audit_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
