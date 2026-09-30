#!/usr/bin/env python3
"""Collect public checkpoint states and terminal outcomes for tail-risk qualification."""
from __future__ import annotations

import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
REPLAY = PROJECT / "model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100439801-replay.json"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore

SEEDS = tuple(range(106001, 106097))
CHECKPOINTS = (432, 504, 576, 624, 672)
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SHOPS = ("YARN_STORE", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "PET_CAFE", "PIZZA_SHOP", "FARMERS_MARKET", "DINER", "JUICE_BAR")
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
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def actions():
    replay = json.loads(REPLAY.read_text())
    seat = replay["info"]["TeamNames"].index("lucaskna")
    return [step[seat].get("action") or {} for step in replay["steps"][1:720]]


def features(obs):
    seat = int(obs.get("player", 0) or 0)
    farms = obs.get("farms", []) or []
    own, rival = farms[seat], farms[1 - seat]
    private = obs.get("private", {}) or {}
    shed = private.get("shed", {}) or {}
    carried = private.get("inventories", []) or []
    market = obs.get("market", {}) or {}
    prices = market.get("prices", {}) or {}
    supply = market.get("inventory", {}) or {}
    shops = list((obs.get("town", {}) or {}).get("unlocked_shops", []) or [])
    values = {
        "seat": seat,
        "money_gap": int(own.get("money", 0) or 0) - int(rival.get("money", 0) or 0),
        "own_money": int(own.get("money", 0) or 0),
        "rival_money": int(rival.get("money", 0) or 0),
        "own_hands": len(own.get("hands", []) or []),
        "rival_hands": len(rival.get("hands", []) or []),
        "own_quadrants": len(own.get("unlocked_quadrants", []) or []),
        "rival_quadrants": len(rival.get("unlocked_quadrants", []) or []),
        "shed_units": sum(max(0, int(v or 0)) for v in shed.values()),
        "shed_value": sum(max(0, int(shed.get(p, 0) or 0)) * max(1, int(prices.get(p, 1) or 1)) for p in PRODUCTS),
        "carried_units": sum(max(0, int(v or 0)) for inventory in carried for v in (inventory or {}).values()),
        "carried_value": sum(max(0, int((inventory or {}).get(p, 0) or 0)) * max(1, int(prices.get(p, 1) or 1)) for inventory in carried for p in PRODUCTS),
        "market_supply_sum": sum(max(0, int(supply.get(p, 10000) or 0)) for p in PRODUCTS),
        "market_price_sum": sum(max(1, int(prices.get(p, 1) or 1)) for p in PRODUCTS),
    }
    for shop in SHOPS:
        values[f"shop_{shop}"] = shops.count(shop)
    return values


def play(task):
    family, seed, seat = task
    own_actions = actions()
    rival = load(OPPONENTS[family], f"v106_probe_{family}_{seed}_{seat}_{os.getpid()}")
    game = kagsim.Game(seed)
    snapshots = {}
    while not game.done:
        if game.step_count in CHECKPOINTS:
            snapshots[str(game.step_count)] = features(game.observe(seat))
        pair = [None, None]
        pair[seat] = own_actions[game.step_count]
        pair[1 - seat] = rival.agent(game.observe(1 - seat))
        game.step(pair[0], pair[1])
    own, opponent = float(game.reward(seat)), float(game.reward(1 - seat))
    margin = own - opponent
    return {"family": family, "seed": seed, "seat": seat, "margin": margin, "score": 1 if margin > 0 else 0.5 if margin == 0 else 0, "catastrophic": margin < -10000, "snapshots": snapshots}


def main():
    tasks = [(family, seed, seat) for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    payload = {"schema": "kaggriculture-v106-risk-probe-data-v1", "strategy_proof": False, "official_evaluation_sources_consumed": 0, "synthetic_seed_range": [min(SEEDS), max(SEEDS)], "games": len(rows), "checkpoints": list(CHECKPOINTS), "catastrophic_rate": statistics.mean(r["catastrophic"] for r in rows), "rows": rows}
    (HERE / "risk_probe_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
