#!/usr/bin/env python3
"""Collect step-144 public/private-own features for early-vs-safe route labels."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(HERE), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from hierarchical_policy import make_agent


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
}
SEEDS = tuple(range(87000, 87256))
DECISION_STEP = 144
ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def tile_counts(farm: dict, prefix: str) -> dict:
    counts = Counter()
    for row in farm.get("tiles") or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("crop"):
                counts[f"{prefix}_crop_{tile['crop']}"] += 1
            if tile.get("animal"):
                counts[f"{prefix}_animal_{tile['animal']}"] += 1
            if tile.get("kind"):
                counts[f"{prefix}_kind_{tile['kind']}"] += 1
    return dict(counts)


def features(obs: dict, seat: int) -> dict:
    own = obs["farms"][seat]
    opp = obs["farms"][1 - seat]
    shops = [str(value) for value in ((obs.get("town") or {}).get("unlocked_shops") or [])]
    result = {
        "seat": seat,
        "shop_1": shops[0] if len(shops) > 0 else "NONE",
        "shop_2": shops[1] if len(shops) > 1 else "NONE",
        "shop_pair": "|".join(shops[:2]),
        "own_money": int(own.get("money", 0) or 0),
        "opp_money": int(opp.get("money", 0) or 0),
        "money_lead": int(own.get("money", 0) or 0) - int(opp.get("money", 0) or 0),
        "own_hands": len(own.get("hands") or []),
        "opp_hands": len(opp.get("hands") or []),
        "hand_lead": len(own.get("hands") or []) - len(opp.get("hands") or []),
        "own_land": len(own.get("unlocked_quadrants") or []),
        "opp_land": len(opp.get("unlocked_quadrants") or []),
    }
    result.update(tile_counts(own, "own"))
    result.update(tile_counts(opp, "opp"))
    private = obs.get("private") or {}
    shed = private.get("shed") or {}
    seeds = private.get("seeds") or {}
    result["shed_total"] = sum(int(value or 0) for value in shed.values())
    result["seed_total"] = sum(int(value or 0) for value in seeds.values())
    market = obs.get("market") or {}
    prices = market.get("prices") or {}
    inventory = market.get("inventory") or {}
    for item in ITEMS:
        result[f"shed_{item}"] = int(shed.get(item, 0) or 0)
        result[f"seed_{item}"] = int(seeds.get(item, 0) or 0)
        result[f"price_{item}"] = float(prices.get(item, 0) or 0)
        result[f"market_inventory_{item}"] = int(inventory.get(item, 0) or 0)
    return result


def play(family: str, seed: int, seat: int, mode: str) -> dict:
    policy = make_agent(mode)
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v20_early_{family}_{seed}_{seat}_{mode}", "kind": "python",
        "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    game = kagsim.Game(seed)
    snapshot = None
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        if game.step_count == DECISION_STEP:
            snapshot = features(observations[seat], seat)
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    assert snapshot is not None
    own, opp = float(game.reward(seat)), float(game.reward(1 - seat))
    return {"features": snapshot, "own": own, "opp": opp, "margin": own - opp}


def run_job(payload: tuple[str, int, int]) -> dict:
    family, seed, seat = payload
    early = play(family, seed, seat, "switch_144")
    safe = play(family, seed, seat, "switch_360")
    if early["features"] != safe["features"]:
        raise RuntimeError(f"decision-state mismatch: {family}/{seed}/{seat}")
    return {
        "opponent_family": family,
        "seed": seed,
        "seat": seat,
        "features": early["features"],
        "early": {key: early[key] for key in ("own", "opp", "margin")},
        "safe": {key: safe[key] for key in ("own", "opp", "margin")},
        "score_delta": score(early["margin"]) - score(safe["margin"]),
        "margin_delta": early["margin"] - safe["margin"],
        "own_delta": early["own"] - safe["own"],
    }


def main() -> int:
    jobs = [(family, seed, seat) for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run_job, jobs, chunksize=1))
    split_seed = 87192
    result = {
        "schema": "kaggriculture-v20-step144-router-dataset-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "decision_step": DECISION_STEP,
        "seed_range": [SEEDS[0], SEEDS[-1]],
        "train_seed_range": [SEEDS[0], split_seed - 1],
        "test_seed_range": [split_seed, SEEDS[-1]],
        "opponent_families": list(OPPONENTS),
        "double_seat": True,
        "cells": len(rows),
        "positive_zero_negative": [
            sum(row["score_delta"] > 0 for row in rows),
            sum(row["score_delta"] == 0 for row in rows),
            sum(row["score_delta"] < 0 for row in rows),
        ],
        "rows": rows,
    }
    (HERE / "early_switch_dataset.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("engine", "seed_range", "train_seed_range", "test_seed_range", "cells", "positive_zero_negative")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
