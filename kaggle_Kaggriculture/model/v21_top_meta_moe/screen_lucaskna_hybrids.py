#!/usr/bin/env python3
"""Paired timing/gate screen for the replay-derived lucaskna expert."""

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
    "v13c_a2": MODEL / "v13c_a2_v8_no_wool_throttle" / "main.py",
    "v16_town_drain": MODEL / "v16_s2_town_drain_challenger" / "main.py",
    "v17_portfolio": MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "main.py",
    "v18_shop_moe": MODEL / "v18_shop_demand_moe" / "main.py",
    "v19_gold": MODEL / "v19_hierarchical_moe" / "main.py",
}
SEEDS = tuple(range(97200, 97216))
MODES = (
    "v20",
    "non_yarn_216", "non_yarn_288", "non_yarn_360", "non_yarn_432", "non_yarn_504",
    "first_pizza_216", "first_pizza_360",
)


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


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
    if mode == "v20":
        policy = make_agent("switch_360", seller_mode="demand_delay_25")
    else:
        gate, step = mode.rsplit("_", 1)
        policy = make_lucaskna_hybrid(int(step), gate)
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v21_hybrid_{mode}_{family}_{seed}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    own, opp = play(policy, opponent, seed, seat)
    return {"mode": mode, "family": family, "seed": seed, "seat": seat, "own": own, "opp": opp, "margin": own - opp}


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(r["margin"] > 0 for r in rows), sum(r["margin"] == 0 for r in rows), sum(r["margin"] < 0 for r in rows)],
        "score_rate": statistics.mean(score(r["margin"]) for r in rows),
        "mean_bank": statistics.mean(r["own"] for r in rows),
        "mean_margin": statistics.mean(r["margin"] for r in rows),
    }


def main() -> int:
    jobs = [(mode, family, seed, seat) for mode in MODES for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run_job, jobs, chunksize=4))
    baseline = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == "v20"}
    metrics = {}
    for mode in MODES:
        selected = [r for r in rows if r["mode"] == mode]
        by_family = {family: summarize([r for r in selected if r["family"] == family]) for family in OPPONENTS}
        metric = {**summarize(selected), "worst_family_score_rate": min(v["score_rate"] for v in by_family.values()), "by_family": by_family}
        if mode != "v20":
            paired = []
            for row in selected:
                base = baseline[(row["family"], row["seed"], row["seat"])]
                paired.append({"score": score(row["margin"]) - score(base["margin"]), "margin": row["margin"] - base["margin"], "own": row["own"] - base["own"]})
            metric["paired_vs_v20"] = {
                "score_uplift_pp": 100 * statistics.mean(r["score"] for r in paired),
                "positive_zero_negative": [sum(r["score"] > 0 for r in paired), sum(r["score"] == 0 for r in paired), sum(r["score"] < 0 for r in paired)],
                "margin_delta_mean": statistics.mean(r["margin"] for r in paired),
                "own_delta_mean": statistics.mean(r["own"] for r in paired),
            }
        metrics[mode] = metric
    result = {
        "schema": "kaggriculture-v21-lucaskna-hybrid-screen-v1",
        "status": "DEVELOPMENT_SCREEN_NOT_CONFIRMATION",
        "engine": str(kagsim.ENGINE_VERSION), "seed_range": [SEEDS[0], SEEDS[-1]],
        "opponent_families": list(OPPONENTS), "double_seat": True,
        "metrics": metrics, "rows": rows,
    }
    (HERE / "lucaskna_hybrid_screen_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({mode: {key: value for key, value in metric.items() if key != "by_family"} for mode, metric in metrics.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
