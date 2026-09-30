#!/usr/bin/env python3
"""Closed-loop step-360 screen for all 90 exact-prefix P1 Replay routes."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import os
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
from hierarchical_policy import PARENT, ROUTER_STEP, _ROUTES, make_agent


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
}
SEEDS = tuple(range(90000, 90012))
SWITCH_STEP = 360
_CACHE: dict[tuple[str, str], list[dict]] = {}


def profile_key(row: dict) -> tuple:
    purchases = row["purchases"]
    return (
        tuple(sorted(purchases["seed"].items())),
        tuple(sorted(purchases["animal"].items())),
        int(purchases["hires"]), int(purchases["land"]),
    )


def candidate_routes(catalog_path: Path, all_compatible: bool = False) -> list[dict]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    rows = [row for row in catalog["rows"] if row["exact_parent_prefix"]]
    if all_compatible:
        # Production signatures collapse identical geometry, labour and fixed
        # purchase plans while ignoring market sells.  Keep the strongest source
        # result per signature so the screen is not dominated by replay aliases.
        by_production = defaultdict(list)
        for row in rows:
            by_production[row["production_hash"]].append(row)
        return sorted(
            [max(group, key=lambda row: (row["source_result"] == "W", row["source_margin"], row["source_reward"])) for group in by_production.values()],
            key=lambda row: (row["team"], int(row["episode"])),
        )
    groups = defaultdict(list)
    for row in rows:
        groups[profile_key(row)].append(row)
    p1 = max(groups.values(), key=len)
    return sorted(p1, key=lambda row: (row["team"], int(row["episode"])))


def route_actions(team: str, path: str) -> list[dict]:
    key = (team, path)
    if key not in _CACHE:
        replay = json.loads(Path(path).read_text(encoding="utf-8"))
        seat = replay["info"]["TeamNames"].index(team)
        _CACHE[key] = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
    return _CACHE[key]


def route_agent(team: str, path: str):
    candidate = _ROUTES["default"][:SWITCH_STEP] + route_actions(team, path)[SWITCH_STEP:]
    base = PARENT._fresh_base()
    base._V17_FEED_GUARD = False
    state = {0: {"last": -1, "route": None}, 1: {"last": -1, "route": None}}

    def policy(obs, configuration=None):
        del configuration
        seat = PARENT._seat(obs)
        step = PARENT._step(obs)
        local = state[seat]
        if step == 0 or step < int(local.get("last", -1)):
            local.update(last=step, route=None)
        local["last"] = step
        if local.get("route") is None and step >= ROUTER_STEP:
            shops = [str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])]
            local["route"] = "yarn" if shops and shops[0] == "YARN_STORE" else "default"
        actions = _ROUTES["yarn"] if local.get("route") == "yarn" else candidate if step >= SWITCH_STEP else _ROUTES["default"]
        base._ACTIONS = actions
        action = base._CORE_AGENT(obs)
        action = PARENT._cap_fixed_purchases(obs, action, base)
        return PARENT._fail_closed_units(obs, action)

    return policy


def play(policy, family: str, seed: int, seat: int) -> tuple[float, float]:
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"p1_all_{family}_{seed}_{seat}_{os.getpid()}", "kind": "python",
        "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    game = kagsim.Game(seed)
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    return float(game.reward(seat)), float(game.reward(1 - seat))


def run_job(payload: tuple[str, str, int, str, str, int, int]) -> dict:
    route_hash, team, episode, path, family, seed, seat = payload
    own, opp = play(route_agent(team, path), family, seed, seat)
    return {
        "route_hash": route_hash, "route_id": f"{team}::{episode}",
        "opponent_family": family, "seed": seed, "seat": seat,
        "own": own, "opp": opp, "margin": own - opp,
    }


def run_baseline(payload: tuple[str, int, int]) -> dict:
    family, seed, seat = payload
    own, opp = play(make_agent("switch_360"), family, seed, seat)
    return {"opponent_family": family, "seed": seed, "seat": seat, "own": own, "opp": opp, "margin": own - opp}


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=HERE / "production_route_catalog.json")
    parser.add_argument("--all-compatible", action="store_true")
    parser.add_argument("--seed-start", type=int, default=SEEDS[0])
    parser.add_argument("--seed-count", type=int, default=len(SEEDS))
    parser.add_argument("--output", type=Path, default=HERE / "all_p1_route360_screen.json")
    args = parser.parse_args()
    routes = candidate_routes(args.catalog, args.all_compatible)
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    base_jobs = [(family, seed, seat) for family in OPPONENTS for seed in seeds for seat in (0, 1)]
    jobs = [
        (row["full_action_hash"], row["team"], int(row["episode"]), row["path"], family, seed, seat)
        for row in routes for family, seed, seat in base_jobs
    ]
    workers = max(1, os.cpu_count() or 1)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        baseline_rows = list(pool.map(run_baseline, base_jobs, chunksize=1))
        candidate_rows = []
        for index, row in enumerate(pool.map(run_job, jobs, chunksize=12), start=1):
            candidate_rows.append(row)
            if index % (len(base_jobs) * 10) == 0:
                print(f"completed_routes={index // len(base_jobs)}/{len(routes)}", flush=True)
    baseline = {(row["opponent_family"], row["seed"], row["seat"]): row for row in baseline_rows}
    metrics = []
    for route in routes:
        selected = [row for row in candidate_rows if row["route_hash"] == route["full_action_hash"]]
        paired = []
        for row in selected:
            base = baseline[(row["opponent_family"], row["seed"], row["seat"])]
            paired.append({
                **row,
                "score_delta": score(row["margin"]) - score(base["margin"]),
                "margin_delta": row["margin"] - base["margin"],
                "own_delta": row["own"] - base["own"],
            })
        by_family = {}
        for family in OPPONENTS:
            family_rows = [row for row in paired if row["opponent_family"] == family]
            by_family[family] = 100 * statistics.mean(row["score_delta"] for row in family_rows)
        metrics.append({
            "route": route,
            "cells": len(paired),
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in paired),
            "positive_zero_negative": [sum(row["score_delta"] > 0 for row in paired), sum(row["score_delta"] == 0 for row in paired), sum(row["score_delta"] < 0 for row in paired)],
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in paired),
            "own_delta_mean": statistics.mean(row["own_delta"] for row in paired),
            "by_family_uplift_pp": by_family,
            "guardrail_pass": all(value >= -2.0 for value in by_family.values()),
        })
    metrics.sort(key=lambda row: (row["score_uplift_pp"], -row["positive_zero_negative"][2], row["margin_delta_mean"]), reverse=True)
    result = {
        "schema": "kaggriculture-v20-all-p1-route360-screen-v1",
        "status": "DEVELOPMENT_SCREEN_NOT_CONFIRMATION",
        "engine": str(kagsim.ENGINE_VERSION),
        "catalog": str(args.catalog.resolve()),
        "candidate_selection": "all_unique_production_signatures" if args.all_compatible else "largest_purchase_profile",
        "seed_range": [seeds[0], seeds[-1]],
        "opponent_families": list(OPPONENTS),
        "double_seat": True,
        "route_count": len(routes),
        "cells_per_route": len(base_jobs),
        "baseline": "V19 switch_360 Kronki::99108392",
        "metrics": metrics,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"route_count": len(routes), "cells_per_route": len(base_jobs), "top10": [{
        "route_id": row["route"]["team"] + "::" + str(row["route"]["episode"]),
        **{key: row[key] for key in ("score_uplift_pp", "positive_zero_negative", "margin_delta_mean", "own_delta_mean", "guardrail_pass")},
    } for row in metrics[:10]]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
