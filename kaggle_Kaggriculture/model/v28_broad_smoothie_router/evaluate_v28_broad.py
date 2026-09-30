#!/usr/bin/env python3
"""Frozen 12-family broad evaluation of the V27 Smoothie expert."""

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
from top_route_panel import make_compatible_shop_router, make_lucaskna_hybrid


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
    ordered = sorted(values); pos = (len(ordered) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] if lo == hi else ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def play(policy, opponent, seed: int, seat: int):
    game = kagsim.Game(seed); agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    first_shop = "NO_SHOP"
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        shops = list(observations[seat]["town"]["unlocked_shops"] or [])
        if shops and first_shop == "NO_SHOP": first_shop = str(shops[0])
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    return float(game.reward(seat)), float(game.reward(1 - seat)), first_shop


def run_block(payload: tuple[str, int]) -> list[dict]:
    family, seed = payload
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    block = []
    for seat in (0, 1):
        for mode in ("baseline", "candidate"):
            policy = make_lucaskna_hybrid(216) if mode == "baseline" else make_compatible_shop_router("SMOOTHIE_SHOP", "lucaskna", 100501596)
            opponent = create_agent(registry, {
                "id": f"v28_{family}_{seed}_{seat}_{mode}_{os.getpid()}", "kind": "python",
                "path": str(OPPONENTS[family]), "entrypoint": "agent",
            })
            own, opp, first_shop = play(policy, opponent, seed, seat)
            block.append({"mode": mode, "family": family, "seed": seed, "seat": seat, "first_shop": first_shop, "own": own, "opp": opp, "margin": own - opp})
    return block


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(r["margin"] > 0 for r in rows), sum(r["margin"] == 0 for r in rows), sum(r["margin"] < 0 for r in rows)],
        "score_rate": statistics.mean(score(r["margin"]) for r in rows),
        "mean_bank": statistics.mean(r["own"] for r in rows), "mean_margin": statistics.mean(r["margin"] for r in rows),
    }


def main() -> int:
    manifest = json.loads((HERE / "v28_broad_seeds.json").read_text(encoding="utf-8"))
    seeds = range(manifest["seed_range"][0], manifest["seed_range"][1] + 1)
    jobs = [(family, seed) for family in manifest["opponent_families"] for seed in seeds]
    rows = []; progress = HERE / "v28_broad_progress.json"
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        for index, block in enumerate(pool.map(run_block, jobs, chunksize=1), start=1):
            rows.extend(block)
            if index % len(seeds) == 0:
                print(f"completed {jobs[index - 1][0]}: {len(rows)} rows", flush=True)
                progress.write_text(json.dumps({"completed_family": jobs[index - 1][0], "rows": rows}, ensure_ascii=False) + "\n", encoding="utf-8")
    base = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == "baseline"}
    paired = []
    for row in rows:
        if row["mode"] != "candidate": continue
        parent = base[(row["family"], row["seed"], row["seat"])]
        paired.append({"family": row["family"], "seed": row["seed"], "seat": row["seat"], "first_shop": row["first_shop"], "score_delta": score(row["margin"]) - score(parent["margin"]), "margin_delta": row["margin"] - parent["margin"], "own_delta": row["own"] - parent["own"]})
    by_seed = defaultdict(list)
    for row in paired: by_seed[row["seed"]].append(row["score_delta"])
    seed_delta = {seed: statistics.mean(values) for seed, values in by_seed.items()}
    rng = random.Random(28001)
    bootstrap = [statistics.mean(seed_delta[seed] for seed in rng.choices(list(seed_delta), k=len(seed_delta))) for _ in range(10000)]
    by_family = {}
    for family in manifest["opponent_families"]:
        selected = [r for r in paired if r["family"] == family]
        by_family[family] = {
            "score_uplift_pp": 100 * statistics.mean(r["score_delta"] for r in selected),
            "positive_zero_negative": [sum(r["score_delta"] > 0 for r in selected), sum(r["score_delta"] == 0 for r in selected), sum(r["score_delta"] < 0 for r in selected)],
            "margin_delta_mean": statistics.mean(r["margin_delta"] for r in selected), "own_delta_mean": statistics.mean(r["own_delta"] for r in selected),
        }
    impacted = [r for r in paired if r["first_shop"] == "SMOOTHIE_SHOP"]
    candidate_rows = [r for r in rows if r["mode"] == "candidate"]; baseline_rows = [r for r in rows if r["mode"] == "baseline"]
    result = {
        "schema": "kaggriculture-v28-broad-smoothie-router-v1", "status": "FROZEN_BROAD_DEVELOPMENT",
        "engine": str(kagsim.ENGINE_VERSION), "manifest": manifest,
        "baseline": summarize(baseline_rows), "candidate": summarize(candidate_rows),
        "paired": {
            "cells": len(paired), "impacted_cells": len(impacted),
            "score_uplift_pp": 100 * statistics.mean(r["score_delta"] for r in paired),
            "score_uplift_ci95_pp": [100 * quantile(bootstrap, .025), 100 * quantile(bootstrap, .975)],
            "target_shop_uplift_pp": 100 * statistics.mean(r["score_delta"] for r in impacted),
            "positive_zero_negative": [sum(r["score_delta"] > 0 for r in paired), sum(r["score_delta"] == 0 for r in paired), sum(r["score_delta"] < 0 for r in paired)],
            "margin_delta_mean": statistics.mean(r["margin_delta"] for r in paired), "own_delta_mean": statistics.mean(r["own_delta"] for r in paired),
            "by_family": by_family,
        }, "rows": rows,
    }
    result["paired"]["primary_pass"] = result["paired"]["score_uplift_ci95_pp"][0] > 0
    result["paired"]["guardrail_pass"] = all(v["score_uplift_pp"] >= -2.0 for v in by_family.values())
    result["paired"]["target_pass"] = result["paired"]["target_shop_uplift_pp"] > 0
    result["decision"] = "QUALIFY_FOR_V29" if all(result["paired"][k] for k in ("primary_pass", "guardrail_pass", "target_pass")) else "DO_NOT_QUALIFY"
    (HERE / "v28_broad_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "baseline", "candidate", "paired", "decision")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
