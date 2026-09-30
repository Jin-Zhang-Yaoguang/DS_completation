#!/usr/bin/env python3
"""Frozen paired discovery for the V19 three-route production Router."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(HERE), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from hierarchical_policy import FIRST_SHOP_ROUTE, make_agent


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "bc_ppo": MODEL / "v3_bc_ppo_hybrid" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "ppo_topdays": MODEL / "v5_ppo_v2_league" / "v5_ppo_v2_topdays" / "main.py",
    "rule_hybrid": MODEL / "v5_rule_hybrid" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
    "v13c_a2": MODEL / "v13c_a2_v8_no_wool_throttle" / "main.py",
    "v16_town_drain": MODEL / "v16_s2_town_drain_challenger" / "main.py",
    "v17_portfolio": MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "main.py",
    "v18_shop_moe": MODEL / "v18_shop_demand_moe" / "main.py",
    "v19_gold": MODEL / "v19_hierarchical_moe" / "main.py",
}


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] if lo == hi else values[lo] * (hi - pos) + values[hi] * (pos - lo)


def play(policy, opponent, seed: int, seat: int):
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    shops = []
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        if game.step_count in (72, 144, 216):
            shops = list(observations[seat]["town"]["unlocked_shops"][:3])
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat], shops


def evaluate_seed_job(payload: tuple[str, int, str, str, str, str]) -> list[dict]:
    """Evaluate one opponent/seed block in an isolated process.

    Keeping both seats and both policies in one job amortizes process overhead while
    ensuring that mutable agent state is never shared across games.
    """
    family, seed, comparison, candidate_seller, candidate_mode, baseline_mode = payload
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    block = []
    for seat in (0, 1):
        for mode in ("parent", "candidate"):
            if comparison == "seller_ablation":
                policy = make_agent(baseline_mode, seller_mode="none") if mode == "parent" else make_agent(candidate_mode, seller_mode=candidate_seller)
            else:
                policy = make_agent("parent" if mode == "parent" else candidate_mode)
            opponent = create_agent(registry, {
                "id": f"v19_router_{family}_{seed}_{seat}_{mode}", "kind": "python",
                "path": str(OPPONENTS[family]), "entrypoint": "agent",
            })
            own, opp, shops = play(policy, opponent, int(seed), seat)
            block.append({
                "mode": mode, "opponent_family": family, "seed": seed, "seat": seat,
                "shops": shops, "first_shop": shops[0] if shops else "NO_SHOP",
                "selected_route": FIRST_SHOP_ROUTE.get(shops[0] if shops else "", "default") if mode == "candidate" else "V17_PARENT",
                "own": own, "opp": opp, "margin": own - opp,
            })
    return block


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(row["margin"] > 0 for row in rows), sum(row["margin"] == 0 for row in rows), sum(row["margin"] < 0 for row in rows)],
        "score_rate": statistics.mean(score(row["margin"]) for row in rows),
        "mean_bank": statistics.mean(row["own"] for row in rows),
        "mean_margin": statistics.mean(row["margin"] for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=HERE / "router_discovery_seeds.json")
    parser.add_argument("--output", type=Path, default=HERE / "router_discovery_results.json")
    parser.add_argument("--comparison", choices=("router_vs_parent", "seller_ablation"), default="router_vs_parent")
    parser.add_argument("--candidate-seller", default="boost_fertilizer")
    parser.add_argument("--candidate-mode", default="router")
    parser.add_argument("--baseline-mode", default="router")
    parser.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 1))
    args = parser.parse_args()
    frozen = json.loads(args.manifest.read_text(encoding="utf-8"))
    seeds = list(frozen.get("seeds") or range(int(frozen["seed_range"][0]), int(frozen["seed_range"][1]) + 1))
    phase = str(frozen.get("phase") or "discovery")
    rows = []
    progress = HERE / f"router_{phase}_progress.json"
    jobs = [
        (family, int(seed), args.comparison, args.candidate_seller, args.candidate_mode, args.baseline_mode)
        for family in frozen["opponent_families"] for seed in seeds
    ]
    if args.jobs == 1:
        blocks = map(evaluate_seed_job, jobs)
    else:
        pool = concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs)
        blocks = pool.map(evaluate_seed_job, jobs, chunksize=1)
    try:
        for index, block in enumerate(blocks, start=1):
            rows.extend(block)
            if index % max(1, len(seeds)) == 0 or index == len(jobs):
                completed_family = jobs[index - 1][0]
                progress.write_text(json.dumps({"completed_family": completed_family, "rows": rows}, ensure_ascii=False) + "\n", encoding="utf-8")
                print(f"completed {completed_family}: {len(rows)} rows", flush=True)
    finally:
        if args.jobs != 1:
            pool.shutdown(wait=True)

    parent = {(row["opponent_family"], row["seed"], row["seat"]): row for row in rows if row["mode"] == "parent"}
    paired = []
    for row in rows:
        if row["mode"] != "candidate":
            continue
        base = parent[(row["opponent_family"], row["seed"], row["seat"])]
        paired.append({
            **{key: row[key] for key in ("opponent_family", "seed", "seat", "first_shop", "shops", "selected_route")},
            "score_delta": score(row["margin"]) - score(base["margin"]),
            "margin_delta": row["margin"] - base["margin"],
            "own_delta": row["own"] - base["own"],
        })
    by_seed = defaultdict(list)
    for row in paired:
        by_seed[row["seed"]].append(row["score_delta"])
    seed_delta = {seed: statistics.mean(values) for seed, values in by_seed.items()}
    rng = random.Random(1901)
    bootstrap = [statistics.mean(seed_delta[seed] for seed in rng.choices(list(seed_delta), k=len(seed_delta))) for _ in range(10000)]
    by_family = {}
    for family in frozen["opponent_families"]:
        selected = [row for row in paired if row["opponent_family"] == family]
        by_family[family] = {
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in selected),
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in selected),
            "own_delta_mean": statistics.mean(row["own_delta"] for row in selected),
        }
    by_shop = {}
    for shop in sorted({row["first_shop"] for row in paired}):
        selected = [row for row in paired if row["first_shop"] == shop]
        by_shop[shop] = {
            "cells": len(selected), "route": selected[0]["selected_route"],
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in selected),
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in selected),
            "positive_zero_negative": [sum(row["score_delta"] > 0 for row in selected), sum(row["score_delta"] == 0 for row in selected), sum(row["score_delta"] < 0 for row in selected)],
        }
    candidate_rows = [row for row in rows if row["mode"] == "candidate"]
    parent_rows = [row for row in rows if row["mode"] == "parent"]
    result = {
        "schema": "kaggriculture-v19-router-frozen-paired-evaluation-v2",
        "phase": phase,
        "comparison": args.comparison,
        "candidate_seller": args.candidate_seller if args.comparison == "seller_ablation" else None,
        "candidate_mode": args.candidate_mode,
        "status": "FROZEN_PAIRED_EVALUATION",
        "engine": str(kagsim.ENGINE_VERSION),
        "candidate": summarize(candidate_rows),
        "parent": summarize(parent_rows),
        "paired": {
            "cells": len(paired),
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in paired),
            "score_uplift_ci95_pp": [100 * quantile(bootstrap, 0.025), 100 * quantile(bootstrap, 0.975)],
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in paired),
            "own_delta_mean": statistics.mean(row["own_delta"] for row in paired),
            "positive_zero_negative": [sum(row["score_delta"] > 0 for row in paired), sum(row["score_delta"] == 0 for row in paired), sum(row["score_delta"] < 0 for row in paired)],
            "by_family": by_family, "by_first_shop": by_shop,
        },
        "rows": rows,
    }
    result["paired"]["primary_pass"] = result["paired"]["score_uplift_ci95_pp"][0] > 0
    result["paired"]["guardrail_pass"] = all(value["score_uplift_pp"] >= -2.0 for value in by_family.values())
    result["decision"] = (
        "QUALIFY_ROUTER_FOR_NEXT_LAYER"
        if result["paired"]["primary_pass"] and result["paired"]["guardrail_pass"]
        else "DO_NOT_QUALIFY_ROUTER"
    )
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "engine", "candidate", "parent", "paired")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
