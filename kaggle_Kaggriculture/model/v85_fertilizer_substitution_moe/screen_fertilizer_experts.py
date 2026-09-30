#!/usr/bin/env python3
"""Synthetic ablation screen for V85 fertilizer-substitution experts."""

from __future__ import annotations

import concurrent.futures
from collections import defaultdict
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


PARENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
MODES = (
    "parent", "collect", "collect_before_672", "collect_capacity95",
    "collect_cash_lt_3000", "collect_cash_lt_10000", "collect_when_buying",
    "collect_reduce_one_buy",
)
SEEDS = range(82501, 82517)


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def _eligible(obs, action, mode: str) -> bool:
    step = int(obs.get("step", 0) or 0)
    seat = int(obs.get("player", 0) or 0)
    money = int(obs["farms"][seat].get("money", 0) or 0)
    private = obs.get("private", {}) or {}
    total = sum(int(v or 0) for v in dict(private.get("shed", {}) or {}).values())
    total += sum(sum(int(v or 0) for v in dict(inv or {}).values())
                 for inv in (private.get("inventories", []) or []))
    buys = any(order and order[0] == "BUY_PRODUCT" and len(order) > 1
               and order[1] == "FERTILIZER" and int(order[2] or 0) > 0
               for order in (action.get("market") or []))
    if mode == "collect_before_672":
        return step < 672
    if mode == "collect_capacity95":
        return total < 95
    if mode == "collect_cash_lt_3000":
        return money < 3000
    if mode == "collect_cash_lt_10000":
        return money < 10000
    if mode in {"collect_when_buying", "collect_reduce_one_buy"}:
        return buys
    return True


def apply_mode(obs, action, mode: str):
    if mode == "parent" or not _eligible(obs, action, mode):
        return action
    action = {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or [])],
    }
    seat = int(obs.get("player", 0) or 0)
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *(farm.get("hands") or [])]
    orders = [action["farmer"], *action["hands"]]
    collected = 0
    for actor, (order, position) in enumerate(zip(orders, positions)):
        if not order or order[0] != "PASS":
            continue
        x, y = map(int, position)
        tile = farm["tiles"][y][x]
        if isinstance(tile, dict) and bool(tile.get("fertilizer_available")):
            orders[actor] = ["COLLECT_FERTILIZER"]
            collected += 1
    if mode == "collect_reduce_one_buy" and collected:
        remain = collected
        for order in action["market"]:
            if order and order[0] == "BUY_PRODUCT" and len(order) > 2 and order[1] == "FERTILIZER":
                cut = min(remain, max(0, int(order[2] or 0)))
                order[2] = max(0, int(order[2] or 0)) - cut
                remain -= cut
                if remain <= 0:
                    break
    action["farmer"], action["hands"] = orders[0], orders[1:]
    return action


def play(task):
    mode, family, seed, seat = task
    registry = Registry(path=HERE / "screen_registry.json", models={}, raw={})
    parent = create_agent(registry, {"id": f"p_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
                                    "kind": "python", "path": str(PARENT), "entrypoint": "agent"})
    rival = create_agent(registry, {"id": f"r_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
                                   "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent"})
    agents = [None, None]
    agents[seat], agents[1 - seat] = parent, rival
    game = kagsim.Game(seed)
    changed_calls = 0
    collect_calls = 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions = [None, None]
        base = agents[seat](observations[seat])
        candidate = apply_mode(observations[seat], base, mode)
        changed_calls += int(candidate != base)
        collect_calls += sum(int(order and order[0] == "COLLECT_FERTILIZER")
                             for order in [candidate.get("farmer"), *(candidate.get("hands") or [])])
        actions[seat] = candidate
        actions[1 - seat] = agents[1 - seat](observations[1 - seat])
        game.step(actions[0], actions[1])
    own, opponent = float(game.reward(seat)), float(game.reward(1 - seat))
    return {"mode": mode, "family": family, "seed": seed, "seat": seat,
            "own": own, "opponent": opponent, "margin": own - opponent,
            "changed_calls": changed_calls, "collect_calls": collect_calls}


def main() -> None:
    tasks = [(mode, family, seed, seat) for mode in MODES for family in OPPONENTS
             for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    parent = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == "parent"}
    summaries = {}
    for mode in MODES[1:]:
        current = [r for r in rows if r["mode"] == mode]
        deltas, by_family = [], defaultdict(list)
        reward_changes = 0
        for row in current:
            prior = parent[row["family"], row["seed"], row["seat"]]
            delta = score(row["margin"]) - score(prior["margin"])
            deltas.append(delta)
            by_family[row["family"]].append(delta)
            reward_changes += int(row["own"] != prior["own"] or row["opponent"] != prior["opponent"])
        summaries[mode] = {
            "games": len(current), "score_uplift_pp": 100 * statistics.mean(deltas),
            "positive_zero_negative": [sum(x > 0 for x in deltas), sum(x == 0 for x in deltas), sum(x < 0 for x in deltas)],
            "by_opponent_pp": {k: 100 * statistics.mean(v) for k, v in by_family.items()},
            "changed_reward_games": reward_changes,
            "changed_action_calls": sum(r["changed_calls"] for r in current),
            "collect_calls": sum(r["collect_calls"] for r in current),
        }
    payload = {"schema": "kaggriculture-v85-synthetic-expert-screen-v1",
               "engine": str(kagsim.ENGINE_VERSION), "seeds": [min(SEEDS), max(SEEDS)],
               "official_replay_sources": 0, "summaries": summaries}
    (HERE / "synthetic_expert_screen_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
