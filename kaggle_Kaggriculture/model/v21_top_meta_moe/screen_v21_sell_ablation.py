#!/usr/bin/env python3
"""Direct V19/V20/V21 sell-controller ablation on a broad local panel."""

from __future__ import annotations

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
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(HERE), str(V19), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from hierarchical_policy import make_agent
from top_route_panel import make_lucaskna_hybrid


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
SEEDS = tuple(range(98400, 98432))
MODES = ("v19", "v20", "v21_delay", "v21_none")


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def make_policy(mode: str):
    if mode == "v19":
        return make_agent("switch_360", seller_mode="none")
    if mode == "v20":
        return make_agent("switch_360", seller_mode="demand_delay_25")
    if mode == "v21_delay":
        return make_lucaskna_hybrid(216, "non_yarn", "demand_delay_25")
    if mode == "v21_none":
        return make_lucaskna_hybrid(216, "non_yarn", "none")
    raise ValueError(mode)


def play(policy, opponent, seed: int, seat: int) -> tuple[float, float]:
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    game = kagsim.Game(seed)
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    return float(game.reward(seat)), float(game.reward(1 - seat))


def run_job(payload: tuple[str, str, int, int]) -> dict:
    mode, family, seed, seat = payload
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v21_sell_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    own, opp = play(make_policy(mode), opponent, seed, seat)
    return {"mode": mode, "family": family, "seed": seed, "seat": seat, "own": own, "opp": opp, "margin": own - opp}


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(r["margin"] > 0 for r in rows), sum(r["margin"] == 0 for r in rows), sum(r["margin"] < 0 for r in rows)],
        "score_rate": statistics.mean(score(r["margin"]) for r in rows),
        "mean_bank": statistics.mean(r["own"] for r in rows),
        "mean_margin": statistics.mean(r["margin"] for r in rows),
    }


def paired(rows: list[dict], candidate: str, baseline: str) -> dict:
    base = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == baseline}
    pairs = []
    for row in rows:
        if row["mode"] != candidate:
            continue
        parent = base[(row["family"], row["seed"], row["seat"])]
        pairs.append({"family": row["family"], "score": score(row["margin"]) - score(parent["margin"]), "margin": row["margin"] - parent["margin"], "own": row["own"] - parent["own"]})
    by_family = {}
    for family in OPPONENTS:
        selected = [r for r in pairs if r["family"] == family]
        by_family[family] = {
            "score_uplift_pp": 100 * statistics.mean(r["score"] for r in selected),
            "positive_zero_negative": [sum(r["score"] > 0 for r in selected), sum(r["score"] == 0 for r in selected), sum(r["score"] < 0 for r in selected)],
            "margin_delta_mean": statistics.mean(r["margin"] for r in selected),
            "own_delta_mean": statistics.mean(r["own"] for r in selected),
        }
    return {
        "candidate": candidate, "baseline": baseline, "cells": len(pairs),
        "score_uplift_pp": 100 * statistics.mean(r["score"] for r in pairs),
        "positive_zero_negative": [sum(r["score"] > 0 for r in pairs), sum(r["score"] == 0 for r in pairs), sum(r["score"] < 0 for r in pairs)],
        "margin_delta_mean": statistics.mean(r["margin"] for r in pairs),
        "own_delta_mean": statistics.mean(r["own"] for r in pairs),
        "guardrail_pass": all(value["score_uplift_pp"] >= -2.0 for value in by_family.values()),
        "by_family": by_family,
    }


def main() -> int:
    jobs = [(mode, family, seed, seat) for mode in MODES for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run_job, jobs, chunksize=4))
    result = {
        "schema": "kaggriculture-v21-sell-ablation-v1",
        "status": "DEVELOPMENT_SCREEN_NOT_CONFIRMATION",
        "engine": str(kagsim.ENGINE_VERSION), "seed_range": [SEEDS[0], SEEDS[-1]],
        "opponent_families": list(OPPONENTS), "double_seat": True,
        "absolute": {mode: summarize([r for r in rows if r["mode"] == mode]) for mode in MODES},
        "paired": {
            "v20_vs_v19": paired(rows, "v20", "v19"),
            "v21_delay_vs_v19": paired(rows, "v21_delay", "v19"),
            "v21_none_vs_v19": paired(rows, "v21_none", "v19"),
            "v21_none_vs_v21_delay": paired(rows, "v21_none", "v21_delay"),
        },
        "rows": rows,
    }
    (HERE / "v21_sell_ablation_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"absolute": result["absolute"], "paired": {k: {kk: vv for kk, vv in v.items() if kk != "by_family"} for k, v in result["paired"].items()}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
