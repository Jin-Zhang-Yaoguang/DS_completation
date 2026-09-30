#!/usr/bin/env python3
"""Attribute V19 gains using closed-loop actions rather than raw Replay plans."""

from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
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
SEEDS = tuple(range(83000, 83032))
WINDOWS = ((360, 431), (432, 503), (504, 575), (576, 647), (648, 718))


def window_name(step: int) -> str:
    for start, end in WINDOWS:
        if start <= step <= end:
            return f"{start}-{end}"
    return "outside"


def run_job(payload: tuple[str, int, int, str]) -> dict:
    family, seed, seat, mode = payload
    policy = make_agent("parent" if mode == "parent" else "switch_360")
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v19_trace_{family}_{seed}_{seat}_{mode}", "kind": "python",
        "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    game = kagsim.Game(seed)
    market = Counter()
    price_quantity = Counter()
    sell_events = Counter()
    unit_ops = Counter()
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        pair = [agents[0](observations[0]), agents[1](observations[1])]
        obs = observations[seat]
        action = pair[seat]
        step = int(obs["step"])
        if step >= 360:
            window = window_name(step)
            prices = (obs.get("market") or {}).get("prices") or {}
            for order in action.get("market") or []:
                if len(order) >= 3 and order[0] in {"SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"}:
                    op, item, quantity = str(order[0]), str(order[1]), max(0, int(order[2] or 0))
                    market[(window, op, item)] += quantity
                    if op == "SELL" and quantity > 0:
                        price_quantity[(window, item)] += quantity * float(prices.get(item, 0) or 0)
                        sell_events[(window, item)] += 1
            for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]:
                unit_ops[(window, str(order[0]) if order else "PASS")] += 1
        game.step(*pair)
    return {
        "family": family, "seed": seed, "seat": seat, "mode": mode,
        "own": float(game.reward(seat)), "opp": float(game.reward(1 - seat)),
        "market": {"|".join(key): value for key, value in market.items()},
        "price_quantity": {"|".join(key): value for key, value in price_quantity.items()},
        "sell_events": {"|".join(key): value for key, value in sell_events.items()},
        "unit_ops": {"|".join(key): value for key, value in unit_ops.items()},
    }


def aggregate(rows: list[dict], mode: str, field: str) -> Counter:
    total = Counter()
    for row in rows:
        if row["mode"] == mode:
            total.update(row[field])
    return total


def main() -> int:
    jobs = [(family, seed, seat, mode) for family in OPPONENTS for seed in SEEDS for seat in (0, 1) for mode in ("parent", "candidate")]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run_job, jobs, chunksize=1))
    games_per_mode = len(rows) // 2
    summary = {}
    for field in ("market", "price_quantity", "sell_events", "unit_ops"):
        parent = aggregate(rows, "parent", field)
        candidate = aggregate(rows, "candidate", field)
        keys = sorted(set(parent) | set(candidate))
        summary[field] = {
            key: {
                "parent_per_game": parent[key] / games_per_mode,
                "candidate_per_game": candidate[key] / games_per_mode,
                "delta_per_game": (candidate[key] - parent[key]) / games_per_mode,
            }
            for key in keys if candidate[key] != parent[key]
        }
    terminal = {}
    for mode in ("parent", "candidate"):
        selected = [row for row in rows if row["mode"] == mode]
        terminal[mode] = {
            "games": len(selected),
            "mean_own": statistics.mean(row["own"] for row in selected),
            "mean_margin": statistics.mean(row["own"] - row["opp"] for row in selected),
        }
    result = {
        "schema": "kaggriculture-v19-closed-loop-action-attribution-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_range": [SEEDS[0], SEEDS[-1]],
        "opponent_families": list(OPPONENTS),
        "double_seat": True,
        "games_per_mode": games_per_mode,
        "windows": [list(value) for value in WINDOWS],
        "terminal": terminal,
        "summary": summary,
    }
    (HERE / "live_action_attribution.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"games_per_mode": games_per_mode, "terminal": terminal, "market_deltas": summary["market"], "unit_deltas": summary["unit_ops"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
