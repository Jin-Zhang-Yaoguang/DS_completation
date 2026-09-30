#!/usr/bin/env python3
"""Fresh-seed full V22-through-V29 rematch against V17-V21."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
MODEL = PROJECT / "model"
FACTORY = MODEL / "v10_replay_lolo_router"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
sys.path[:0] = [str(PROJECT.parent), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


CANDIDATES = {
    "v22": MODEL / "v22_lucaskna_no_delay_ablation" / "main.py",
    "v23": MODEL / "v23_demand_fraction_search" / "main.py",
    "v24": MODEL / "v24_shop_expert_router" / "main.py",
    "v25": MODEL / "v25_prefix_compatible_experts" / "main.py",
    "v26": MODEL / "v26_step72_milan_router" / "main.py",
    "v27": MODEL / "v27_lucaskna_shop_router" / "main.py",
    "v28": MODEL / "v28_broad_smoothie_router" / "main.py",
    "v29": MODEL / "v29_champion_selection" / "main.py",
}
OPPONENTS = {
    "v17": MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "main.py",
    "v18": MODEL / "v18_shop_demand_moe" / "main.py",
    "v19": MODEL / "v19_hierarchical_moe" / "main.py",
    "v20": MODEL / "v20_demand_timing_moe" / "main.py",
    "v21": MODEL / "v21_top_meta_moe" / "main.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    x = (len(values) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] if lo == hi else values[lo] * (hi - x) + values[hi] * (x - lo)


def create(path: Path, identity: str):
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    return create_agent(registry, {"id": identity, "kind": "python", "path": str(path), "entrypoint": "agent"})


def run_job(payload: tuple[str, str, int, int]) -> dict:
    candidate_name, opponent_name, seed, seat = payload
    suffix = f"{seed}_{seat}_{os.getpid()}"
    candidate = create(CANDIDATES[candidate_name], f"rematch_candidate_{candidate_name}_{suffix}")
    opponent = create(OPPONENTS[opponent_name], f"rematch_opponent_{opponent_name}_{candidate_name}_{suffix}")
    agents = [None, None]
    agents[seat], agents[1 - seat] = candidate, opponent
    game = kagsim.Game(seed)
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    own = float(game.reward(seat))
    rival = float(game.reward(1 - seat))
    return {"candidate": candidate_name, "opponent": opponent_name, "seed": seed, "seat": seat,
            "own": own, "opponent_reward": rival, "margin": own - rival}


def bootstrap_score_ci(rows: list[dict], random_seed: int) -> list[float]:
    by_seed: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        by_seed[row["seed"]].append(score(row["margin"]))
    seed_scores = {seed: statistics.mean(values) for seed, values in by_seed.items()}
    seeds = list(seed_scores)
    rng = random.Random(random_seed)
    values = [statistics.mean(seed_scores[s] for s in rng.choices(seeds, k=len(seeds))) for _ in range(10000)]
    return [quantile(values, 0.025), quantile(values, 0.975)]


def summarize(rows: list[dict], random_seed: int) -> dict:
    wins = sum(row["margin"] > 0 for row in rows)
    ties = sum(row["margin"] == 0 for row in rows)
    losses = sum(row["margin"] < 0 for row in rows)
    return {
        "games": len(rows), "wins_ties_losses": [wins, ties, losses],
        "win_rate": wins / len(rows), "score_rate": (wins + 0.5 * ties) / len(rows),
        "score_rate_ci95": bootstrap_score_ci(rows, random_seed),
        "mean_bank": statistics.mean(row["own"] for row in rows),
        "mean_margin": statistics.mean(row["margin"] for row in rows),
    }


def compare(rows: list[dict], candidate: str, baseline: str) -> dict:
    baseline_rows = {(row["opponent"], row["seed"], row["seat"]): row for row in rows if row["candidate"] == baseline}
    pairs = []
    for row in rows:
        if row["candidate"] != candidate:
            continue
        prior = baseline_rows[(row["opponent"], row["seed"], row["seat"])]
        pairs.append({
            "opponent": row["opponent"], "seed": row["seed"], "seat": row["seat"],
            "score_delta": score(row["margin"]) - score(prior["margin"]),
            "margin_delta": row["margin"] - prior["margin"], "own_delta": row["own"] - prior["own"],
        })
    by_seed: dict[int, list[float]] = defaultdict(list)
    for row in pairs:
        by_seed[row["seed"]].append(row["score_delta"])
    seed_delta = {seed: statistics.mean(values) for seed, values in by_seed.items()}
    seeds = list(seed_delta)
    rng = random.Random(106991 + sum(map(ord, candidate + baseline)))
    bootstrap = [statistics.mean(seed_delta[s] for s in rng.choices(seeds, k=len(seeds))) for _ in range(10000)]
    by_opponent = {}
    for opponent in OPPONENTS:
        selected = [row for row in pairs if row["opponent"] == opponent]
        by_opponent[opponent] = {
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in selected),
            "positive_zero_negative": [sum(row["score_delta"] > 0 for row in selected), sum(row["score_delta"] == 0 for row in selected), sum(row["score_delta"] < 0 for row in selected)],
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in selected),
            "own_delta_mean": statistics.mean(row["own_delta"] for row in selected),
        }
    return {
        "candidate": candidate, "baseline": baseline, "cells": len(pairs),
        "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in pairs),
        "score_uplift_ci95_pp": [100 * quantile(bootstrap, 0.025), 100 * quantile(bootstrap, 0.975)],
        "positive_zero_negative": [sum(row["score_delta"] > 0 for row in pairs), sum(row["score_delta"] == 0 for row in pairs), sum(row["score_delta"] < 0 for row in pairs)],
        "margin_delta_mean": statistics.mean(row["margin_delta"] for row in pairs),
        "own_delta_mean": statistics.mean(row["own_delta"] for row in pairs),
        "by_opponent": by_opponent,
    }


def main() -> int:
    manifest = json.loads((HERE / "rematch_manifest.json").read_text())
    seeds = range(manifest["seed_range"][0], manifest["seed_range"][1] + 1)
    jobs = [(candidate, opponent, seed, seat) for candidate in manifest["candidates"] for opponent in manifest["opponents"] for seed in seeds for seat in (0, 1)]
    print(f"V22-V29 full rematch: {len(jobs)} games, workers={max(1, os.cpu_count() or 1)}", flush=True)
    rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        for index, row in enumerate(pool.map(run_job, jobs, chunksize=4), 1):
            rows.append(row)
            if index % 512 == 0:
                print(f"progress {index}/{len(jobs)}", flush=True)
    absolute = {}
    by_opponent = {}
    for index, candidate in enumerate(manifest["candidates"]):
        selected = [row for row in rows if row["candidate"] == candidate]
        absolute[candidate] = summarize(selected, 105700 + index)
        by_opponent[candidate] = {
            opponent: summarize([row for row in selected if row["opponent"] == opponent], 105800 + index * 10 + i)
            for i, opponent in enumerate(manifest["opponents"])
        }
    paired_vs_v29 = {candidate: compare(rows, candidate, "v29") for candidate in manifest["candidates"] if candidate != "v29"}
    v29_prefix = CANDIDATES["v29"].read_bytes().startswith(OPPONENTS["v21"].read_bytes())
    gates = {}
    for candidate in manifest["candidates"]:
        gates[candidate] = {
            "upper_panel_score_rate_pass": absolute[candidate]["score_rate"] > 0.55,
            "upper_panel_ci_lower_pass": absolute[candidate]["score_rate_ci95"][0] > 0.55,
            "per_opponent_floor_pass": all(value["score_rate"] >= 0.48 for value in by_opponent[candidate].values()),
        }
        if candidate != "v29":
            gates[candidate]["uplift_vs_v29_ci_lower_pass"] = paired_vs_v29[candidate]["score_uplift_ci95_pp"][0] > 0
            gates[candidate]["genuine_new_gold_pass"] = all(gates[candidate].values())
    gates["v29"]["distinct_from_v21"] = not v29_prefix
    gates["v29"]["genuine_new_gold_pass"] = all(gates["v29"].values())
    result = {
        "schema": "kaggriculture-v22-through-v29-full-rematch-v1", "status": "PASS", "engine": str(kagsim.ENGINE_VERSION),
        "manifest": manifest,
        "source_sha256": {**{key: sha256(path) for key, path in CANDIDATES.items()}, **{key: sha256(path) for key, path in OPPONENTS.items()}},
        "v29_is_v21_source_plus_version_only": v29_prefix,
        "absolute": absolute, "by_opponent": by_opponent, "paired_vs_v29": paired_vs_v29, "gold_gates": gates,
        "rows": rows,
    }
    (HERE / "rematch_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    compact = {"absolute": absolute, "by_opponent": by_opponent, "paired_vs_v29": {candidate: {key: value for key, value in comparison.items() if key != "by_opponent"} for candidate, comparison in paired_vs_v29.items()}, "gold_gates": gates, "v29_is_v21_source_plus_version_only": v29_prefix}
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
