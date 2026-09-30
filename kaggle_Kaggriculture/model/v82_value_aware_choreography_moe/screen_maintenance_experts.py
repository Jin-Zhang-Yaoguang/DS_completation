#!/usr/bin/env python3
"""Screen V82 maintenance experts on non-Replay synthetic QA seeds."""

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
SHOP_PRODUCTS = {
    "BAKERY": {"EGG", "WHEAT"},
    "BRUNCH_SPOT": {"EGG", "WHEAT", "STRAWBERRY"},
    "FARMERS_MARKET": {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY"},
    "ICE_CREAM_SHOP": {"STRAWBERRY", "MILK", "WHEAT"},
    "PET_CAFE": {"CARROT"},
    "PIZZA_SHOP": {"MILK", "TOMATO", "WHEAT"},
    "SMOOTHIE_SHOP": {"STRAWBERRY", "MILK"},
    "YARN_STORE": {"WOOL"},
}
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
MODES = (
    "parent", "all_no_collect", "water", "care", "water_care",
    "demand_water", "demand_care", "demand_water_care", "demand_all",
    "demand_all_before_672",
)
SEEDS = range(82201, 82217)


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def demanded_products(obs) -> set[str]:
    products: set[str] = set()
    for shop in obs.get("town", {}).get("unlocked_shops", []) or []:
        products.update(SHOP_PRODUCTS.get(str(shop), set()))
    return products


def apply_mode(obs, action, mode: str):
    if mode == "parent":
        return action
    action = {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order) for order in (action.get("hands") or [])],
        "market": [list(order) for order in (action.get("market") or [])],
    }
    if mode == "demand_all_before_672" and int(obs.get("step", 0) or 0) >= 672:
        return action
    demand_only = mode.startswith("demand_")
    allowed = set()
    if mode in {"all_no_collect", "demand_all", "demand_all_before_672"}:
        allowed = {"WATER", "FEED", "CARE"}
    elif "water_care" in mode:
        allowed = {"WATER", "CARE"}
    elif "water" in mode:
        allowed = {"WATER"}
    elif "care" in mode:
        allowed = {"CARE"}
    demand = demanded_products(obs)
    seat = int(obs.get("player", 0) or 0)
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *(farm.get("hands") or [])]
    inventories = list(obs["private"].get("inventories", []) or [])
    orders = [action["farmer"], *action["hands"]]
    for actor, (order, position) in enumerate(zip(orders, positions)):
        if not order or str(order[0]) != "PASS":
            continue
        x, y = map(int, position)
        tile = farm["tiles"][y][x]
        if not isinstance(tile, dict):
            continue
        inventory = inventories[actor] if actor < len(inventories) else {}
        replacement = None
        product = None
        if "WATER" in allowed and tile.get("kind") == "PLANT" and not tile.get("watered_today"):
            replacement, product = ["WATER"], str(tile.get("crop"))
        elif "FEED" in allowed and tile.get("animal") and not tile.get("fed_today") and int(inventory.get("WHEAT", 0) or 0) > 0:
            replacement, product = ["FEED"], ANIMAL_PRODUCT.get(str(tile.get("animal")))
        elif "CARE" in allowed and tile.get("animal") and not tile.get("cared_today"):
            replacement, product = ["CARE"], ANIMAL_PRODUCT.get(str(tile.get("animal")))
        if replacement is not None and (not demand_only or product in demand):
            orders[actor] = replacement
    action["farmer"], action["hands"] = orders[0], orders[1:]
    return action


def play(task):
    mode, family, seed, seat = task
    registry = Registry(path=HERE / "screen_registry.json", models={}, raw={})
    parent = create_agent(registry, {
        "id": f"parent_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(PARENT), "entrypoint": "agent",
    })
    rival = create_agent(registry, {
        "id": f"rival_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    agents = [None, None]
    agents[seat], agents[1 - seat] = parent, rival
    game = kagsim.Game(seed)
    changed_calls = 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions = [None, None]
        base = agents[seat](observations[seat])
        candidate = apply_mode(observations[seat], base, mode)
        changed_calls += int(candidate != base)
        actions[seat] = candidate
        actions[1 - seat] = agents[1 - seat](observations[1 - seat])
        game.step(actions[0], actions[1])
    own = float(game.reward(seat))
    opponent = float(game.reward(1 - seat))
    return {"mode": mode, "family": family, "seed": seed, "seat": seat,
            "margin": own - opponent, "own": own, "opponent": opponent,
            "changed_calls": changed_calls}


def main() -> None:
    tasks = [(mode, family, seed, seat) for mode in MODES for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    parent = {(row["family"], row["seed"], row["seat"]): row for row in rows if row["mode"] == "parent"}
    summaries = {}
    for mode in MODES[1:]:
        current = [row for row in rows if row["mode"] == mode]
        deltas = []
        family_deltas = defaultdict(list)
        changed_games = 0
        for row in current:
            prior = parent[(row["family"], row["seed"], row["seat"])]
            delta = score(row["margin"]) - score(prior["margin"])
            deltas.append(delta)
            family_deltas[row["family"]].append(delta)
            changed_games += int(row["own"] != prior["own"] or row["opponent"] != prior["opponent"])
        summaries[mode] = {
            "games": len(current),
            "score_uplift_pp": 100 * statistics.mean(deltas),
            "positive_zero_negative": [sum(x > 0 for x in deltas), sum(x == 0 for x in deltas), sum(x < 0 for x in deltas)],
            "by_opponent_pp": {key: 100 * statistics.mean(values) for key, values in family_deltas.items()},
            "changed_reward_games": changed_games,
            "changed_action_calls": sum(row["changed_calls"] for row in current),
        }
    result = {"schema": "kaggriculture-v82-synthetic-expert-screen-v1", "engine": str(kagsim.ENGINE_VERSION),
              "seeds": [min(SEEDS), max(SEEDS)], "official_replay_sources": 0, "summaries": summaries}
    (HERE / "synthetic_expert_screen_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
