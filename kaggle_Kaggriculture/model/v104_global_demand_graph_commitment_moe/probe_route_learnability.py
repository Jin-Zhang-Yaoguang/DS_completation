#!/usr/bin/env python3
"""Test whether public state at step 216 predicts a useful coherent continuation."""
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
REPLAYS = PROJECT / "model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore

BASE = 100439801
EXPERTS = (100439801, 100501596, 100398798, 100414724, 100410172, 100458412, 100446711, 100465032)
SWITCH_STEP = 216
SEEDS = tuple(range(104101, 104133))
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


def route(episode: int):
    replay = json.loads((REPLAYS / f"episode-{episode}-replay.json").read_text())
    seat = replay["info"]["TeamNames"].index("lucaskna")
    return [step[seat].get("action") or {} for step in replay["steps"][1:720]]


def signature(obs):
    shops = tuple(obs.get("town", {}).get("unlocked_shops", []) or [])
    farms = obs.get("farms", []) or []
    seat = int(obs.get("player", 0) or 0)
    own, rival = farms[seat], farms[1 - seat]

    def farm_features(farm):
        fields = farm.get("fields", []) or []
        crops = sorted(str((tile or {}).get("crop", "")) for row in fields for tile in (row or []) if isinstance(tile, dict) and (tile or {}).get("crop"))
        animals = sorted(str((animal or {}).get("type", "")) for animal in (farm.get("animals", []) or []))
        return [int(farm.get("money", 0) or 0), len(farm.get("hands", []) or []), crops, animals]

    return {"shops": shops, "seat": seat, "own": farm_features(own), "rival": farm_features(rival)}


def play(task):
    episode, family, seed, seat = task
    base_actions = route(BASE)
    expert_actions = route(episode)
    rival = load(OPPONENTS[family], f"v104_probe_{episode}_{family}_{seed}_{seat}_{os.getpid()}")
    game = kagsim.Game(seed)
    sig = None
    while not game.done:
        obs = game.observe(seat)
        if game.step_count == SWITCH_STEP:
            sig = signature(obs)
        own_action = base_actions[game.step_count] if game.step_count < SWITCH_STEP else expert_actions[game.step_count]
        actions = [None, None]
        actions[seat] = own_action
        actions[1 - seat] = rival.agent(game.observe(1 - seat))
        game.step(actions[0], actions[1])
    own, opponent = float(game.reward(seat)), float(game.reward(1 - seat))
    margin = own - opponent
    return {
        "episode": episode, "family": family, "seed": seed, "seat": seat,
        "signature": sig, "own": own, "opponent": opponent, "margin": margin,
        "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
        "catastrophic": margin < -10000,
    }


def distance(a, b):
    # Shop graph dominates; public state only breaks ties among equal demand graphs.
    shop = sum(x != y for x, y in zip(a["shops"], b["shops"])) + abs(len(a["shops"]) - len(b["shops"]))
    seat = int(a["seat"] != b["seat"])
    cash = abs(a["own"][0] - b["own"][0]) + abs(a["rival"][0] - b["rival"][0])
    topology = abs(a["own"][1] - b["own"][1]) + abs(a["rival"][1] - b["rival"][1])
    return (shop, seat, topology, cash)


def cross_validated_router(rows):
    index = {(r["episode"], r["family"], r["seed"], r["seat"]): r for r in rows}
    contexts = [(family, seed, seat) for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    selected = []
    for family, seed, seat in contexts:
        test = index[(BASE, family, seed, seat)]
        train_seeds = [s for s in SEEDS if s % 4 != seed % 4]
        neighbours = []
        for train_seed in train_seeds:
            ref = index[(BASE, family, train_seed, seat)]
            neighbours.append((distance(test["signature"], ref["signature"]), train_seed))
        nearest = [s for _, s in sorted(neighbours)[:8]]
        utility = {}
        for expert in EXPERTS:
            sample = [index[(expert, family, s, seat)] for s in nearest]
            utility[expert] = (statistics.mean(r["score"] for r in sample), statistics.mean(r["margin"] for r in sample))
        chosen = max(EXPERTS, key=lambda expert: utility[expert])
        selected.append((index[(chosen, family, seed, seat)], test, chosen))
    deltas = [a["score"] - b["score"] for a, b, _ in selected]
    margin_deltas = [a["margin"] - b["margin"] for a, b, _ in selected]
    counts = {str(expert): sum(chosen == expert for _, _, chosen in selected) for expert in EXPERTS}
    return {
        "contexts": len(selected),
        "router_score": statistics.mean(a["score"] for a, _, _ in selected),
        "fixed_base_score": statistics.mean(b["score"] for _, b, _ in selected),
        "uplift_pp": 100 * statistics.mean(deltas),
        "positive_zero_negative": [sum(x > 0 for x in deltas), sum(x == 0 for x in deltas), sum(x < 0 for x in deltas)],
        "mean_margin_delta": statistics.mean(margin_deltas),
        "selected_expert_counts": counts,
        "selected_catastrophic_rate": statistics.mean(a["catastrophic"] for a, _, _ in selected),
        "base_catastrophic_rate": statistics.mean(b["catastrophic"] for _, b, _ in selected),
    }


def main():
    tasks = [(expert, family, seed, seat) for expert in EXPERTS for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    routed = cross_validated_router(rows)
    expert_scores = {
        str(expert): {
            "score": statistics.mean(r["score"] for r in rows if r["episode"] == expert),
            "catastrophic_rate": statistics.mean(r["catastrophic"] for r in rows if r["episode"] == expert),
        }
        for expert in EXPERTS
    }
    active = sum(count > 0 for count in routed["selected_expert_counts"].values())
    gate = routed["uplift_pp"] > 0 and routed["positive_zero_negative"][0] > routed["positive_zero_negative"][2] and active >= 3
    payload = {
        "schema": "kaggriculture-v104-route-learnability-probe-v1",
        "status": "PASS_SOURCE_QUALIFICATION" if gate else "REJECT_SOURCE_QUALIFICATION",
        "strategy_proof": False,
        "official_evaluation_sources_consumed": 0,
        "synthetic_seed_range": [min(SEEDS), max(SEEDS)],
        "games": len(rows),
        "switch_step": SWITCH_STEP,
        "expert_scores": expert_scores,
        "cross_validated_router": routed,
        "rows": rows,
    }
    (HERE / "route_learnability_probe.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
