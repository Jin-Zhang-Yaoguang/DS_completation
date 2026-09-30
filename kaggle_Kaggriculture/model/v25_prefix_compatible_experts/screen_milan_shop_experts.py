#!/usr/bin/env python3
"""Targeted screen of seven prefix-compatible Milan production experts."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import statistics
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
V19 = MODEL / "v19_hierarchical_moe"
V21 = MODEL / "v21_top_meta_moe"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(V21), str(V19), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from top_route_panel import make_compatible_shop_router, make_lucaskna_hybrid


EXPERTS = {
    "milan_smoothie": ("SMOOTHIE_SHOP", "Milan Leonard", 99922362),
    "milan_pet": ("PET_CAFE", "Milan Leonard", 99972628),
    "milan_ice": ("ICE_CREAM_SHOP", "Milan Leonard", 100057294),
    "milan_bakery": ("BAKERY", "Milan Leonard", 99942858),
    "milan_farmers": ("FARMERS_MARKET", "Milan Leonard", 99931452),
    "milan_pizza": ("PIZZA_SHOP", "Milan Leonard", 99965778),
    "milan_brunch": ("BRUNCH_SPOT", "Milan Leonard", 100018415),
}
OPPONENTS = {
    "v13c_a2": MODEL / "v13c_a2_v8_no_wool_throttle" / "main.py",
    "v16_town_drain": MODEL / "v16_s2_town_drain_challenger" / "main.py",
    "v17_portfolio": MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "main.py",
    "v18_shop_moe": MODEL / "v18_shop_demand_moe" / "main.py",
    "v19_gold": MODEL / "v19_hierarchical_moe" / "main.py",
}
SEEDS = tuple(range(99000, 99032))
MODES = ("v21", *EXPERTS)


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def play(policy, opponent, seed: int, seat: int):
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    game = kagsim.Game(seed)
    first_shop = "NO_SHOP"
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        shops = list(observations[seat]["town"]["unlocked_shops"] or [])
        if shops and first_shop == "NO_SHOP":
            first_shop = str(shops[0])
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    return float(game.reward(seat)), float(game.reward(1 - seat)), first_shop


def run_job(payload: tuple[str, str, int, int, int]) -> dict:
    mode, family, seed, seat, switch_step = payload
    policy = make_lucaskna_hybrid(216) if mode == "v21" else make_compatible_shop_router(*EXPERTS[mode], switch_step=switch_step)
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v25_{mode}_{family}_{seed}_{seat}_{os.getpid()}", "kind": "python",
        "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    own, opp, first_shop = play(policy, opponent, seed, seat)
    return {"mode": mode, "family": family, "seed": seed, "seat": seat, "first_shop": first_shop, "own": own, "opp": opp, "margin": own - opp}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch-step", type=int, default=216)
    parser.add_argument("--seed-start", type=int, default=SEEDS[0])
    parser.add_argument("--seed-count", type=int, default=len(SEEDS))
    parser.add_argument("--output", type=Path, default=HERE / "milan_shop_expert_screen_results.json")
    args = parser.parse_args()
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    jobs = [(mode, family, seed, seat, args.switch_step) for mode in MODES for family in OPPONENTS for seed in seeds for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run_job, jobs, chunksize=4))
    baseline = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == "v21"}
    metrics = {}
    for mode, (target, team, episode) in EXPERTS.items():
        pairs = []
        for row in (r for r in rows if r["mode"] == mode):
            base = baseline[(row["family"], row["seed"], row["seat"])]
            pairs.append({
                "family": row["family"], "first_shop": row["first_shop"],
                "score": score(row["margin"]) - score(base["margin"]),
                "margin": row["margin"] - base["margin"], "own": row["own"] - base["own"],
            })
        impacted = [r for r in pairs if r["first_shop"] == target]
        by_family = {}
        for family in OPPONENTS:
            selected = [r for r in pairs if r["family"] == family]
            by_family[family] = 100 * statistics.mean(r["score"] for r in selected)
        metrics[mode] = {
            "source": f"{team}::{episode}", "target_shop": target,
            "cells": len(pairs), "impacted_cells": len(impacted),
            "score_uplift_pp": 100 * statistics.mean(r["score"] for r in pairs),
            "target_shop_uplift_pp": 100 * statistics.mean(r["score"] for r in impacted),
            "positive_zero_negative": [sum(r["score"] > 0 for r in pairs), sum(r["score"] == 0 for r in pairs), sum(r["score"] < 0 for r in pairs)],
            "margin_delta_mean_impacted": statistics.mean(r["margin"] for r in impacted),
            "own_delta_mean_impacted": statistics.mean(r["own"] for r in impacted),
            "guardrail_pass": all(value >= -2.0 for value in by_family.values()),
            "by_family_uplift_pp": by_family,
        }
    result = {
        "schema": "kaggriculture-v25-milan-compatible-expert-screen-v1",
        "status": "DEVELOPMENT_SCREEN_NOT_CONFIRMATION", "engine": str(kagsim.ENGINE_VERSION),
        "seed_range": [seeds[0], seeds[-1]], "switch_step": args.switch_step, "opponent_families": list(OPPONENTS), "double_seat": True,
        "baseline": "v21", "experts": {k: {"shop": v[0], "team": v[1], "episode": v[2]} for k, v in EXPERTS.items()},
        "metrics": metrics, "rows": rows,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({mode: {k: v for k, v in metric.items() if k != "by_family_uplift_pp"} for mode, metric in metrics.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
