#!/usr/bin/env python3
"""Independent frozen V30 confirmation against three local model generations."""

from __future__ import annotations

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
V19 = MODEL / "v19_hierarchical_moe"
V21 = MODEL / "v21_top_meta_moe"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(V21), str(V19), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from hierarchical_policy import make_agent
from top_route_panel import make_lucaskna_hybrid


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "bc_ppo": MODEL / "v3_bc_ppo_hybrid" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "v13c_a2": MODEL / "v13c_a2_v8_no_wool_throttle" / "main.py",
    "v16_town_drain": MODEL / "v16_s2_town_drain_challenger" / "main.py",
    "v17_portfolio": MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "main.py",
    "v18_shop_moe": MODEL / "v18_shop_demand_moe" / "main.py",
    "v19_gold": MODEL / "v19_hierarchical_moe" / "main.py",
}


def score(margin):
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values, p):
    values = sorted(values)
    x = (len(values) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] if lo == hi else values[lo] * (hi - x) + values[hi] * (x - lo)


def policy(mode):
    if mode == "v19":
        return make_agent("switch_360", seller_mode="none")
    if mode == "v20":
        return make_agent("switch_360", seller_mode="demand_delay_25")
    if mode == "v21":
        return make_lucaskna_hybrid(216)
    raise ValueError(mode)


def play(candidate, opponent, seed, seat):
    agents = [None, None]
    agents[seat], agents[1 - seat] = candidate, opponent
    game = kagsim.Game(seed)
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    return float(game.reward(seat)), float(game.reward(1 - seat))


def run_job(payload):
    mode, family, seed, seat = payload
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v30_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    own, rival = play(policy(mode), opponent, seed, seat)
    return {"mode": mode, "family": family, "seed": seed, "seat": seat,
            "own": own, "opp": rival, "margin": own - rival}


def summarize(rows):
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(r["margin"] > 0 for r in rows), sum(r["margin"] == 0 for r in rows), sum(r["margin"] < 0 for r in rows)],
        "score_rate": statistics.mean(score(r["margin"]) for r in rows),
        "mean_bank": statistics.mean(r["own"] for r in rows),
        "mean_margin": statistics.mean(r["margin"] for r in rows),
    }


def compare(rows, candidate, baseline):
    base = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == baseline}
    pairs = []
    for row in rows:
        if row["mode"] != candidate:
            continue
        prior = base[(row["family"], row["seed"], row["seat"])]
        pairs.append({
            "family": row["family"], "seed": row["seed"],
            "score": score(row["margin"]) - score(prior["margin"]),
            "margin": row["margin"] - prior["margin"], "own": row["own"] - prior["own"],
        })
    by_seed = defaultdict(list)
    for row in pairs:
        by_seed[row["seed"]].append(row["score"])
    seed_delta = {seed: statistics.mean(values) for seed, values in by_seed.items()}
    rng = random.Random(30001 + sum(map(ord, candidate + baseline)))
    bootstrap = [statistics.mean(seed_delta[s] for s in rng.choices(list(seed_delta), k=len(seed_delta))) for _ in range(10000)]
    by_family = {}
    for family in OPPONENTS:
        family_rows = [r for r in pairs if r["family"] == family]
        by_family[family] = {
            "score_uplift_pp": 100 * statistics.mean(r["score"] for r in family_rows),
            "positive_zero_negative": [sum(r["score"] > 0 for r in family_rows), sum(r["score"] == 0 for r in family_rows), sum(r["score"] < 0 for r in family_rows)],
        }
    return {
        "candidate": candidate, "baseline": baseline, "cells": len(pairs),
        "score_uplift_pp": 100 * statistics.mean(r["score"] for r in pairs),
        "score_uplift_ci95_pp": [100 * quantile(bootstrap, 0.025), 100 * quantile(bootstrap, 0.975)],
        "positive_zero_negative": [sum(r["score"] > 0 for r in pairs), sum(r["score"] == 0 for r in pairs), sum(r["score"] < 0 for r in pairs)],
        "margin_delta_mean": statistics.mean(r["margin"] for r in pairs),
        "own_delta_mean": statistics.mean(r["own"] for r in pairs),
        "guardrail_pass": all(value["score_uplift_pp"] >= -2 for value in by_family.values()),
        "by_family": by_family,
    }


def main():
    manifest = json.loads((HERE / "v30_confirmation_seeds.json").read_text())
    seeds = range(manifest["seed_range"][0], manifest["seed_range"][1] + 1)
    jobs = [(mode, family, seed, seat) for mode in manifest["modes"] for family in manifest["opponent_families"] for seed in seeds for seat in (0, 1)]
    print(f"V30 confirmation: {len(jobs)} games, workers={max(1, os.cpu_count() or 1)}", flush=True)
    rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        for index, row in enumerate(pool.map(run_job, jobs, chunksize=4), 1):
            rows.append(row)
            if index % 512 == 0:
                print(f"progress {index}/{len(jobs)}", flush=True)
    absolute = {mode: summarize([r for r in rows if r["mode"] == mode]) for mode in manifest["modes"]}
    comparisons = {
        "v21_vs_v19": compare(rows, "v21", "v19"),
        "v21_vs_v20": compare(rows, "v21", "v20"),
    }
    passed = all(value["score_uplift_ci95_pp"][0] > 0 and value["guardrail_pass"] for value in comparisons.values())
    result = {
        "schema": "kaggriculture-v30-independent-confirmation-v1",
        "status": "PASS" if passed else "FAIL", "engine": str(kagsim.ENGINE_VERSION),
        "manifest": manifest, "absolute": absolute, "comparisons": comparisons,
        "decision": "OFFLINE_GOLD_LEVEL_CONFIRMED" if passed else "GOLD_GATE_REJECTED", "rows": rows,
    }
    (HERE / "v30_confirmation_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    compact = {"status": result["status"], "absolute": absolute,
               "comparisons": {key: {k: v for k, v in value.items() if k != "by_family"} for key, value in comparisons.items()},
               "decision": result["decision"]}
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
