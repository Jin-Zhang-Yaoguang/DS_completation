#!/usr/bin/env python3
"""Calibrate product price thresholds from closed-loop parent observations."""

from __future__ import annotations

import json
import math
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
from hierarchical_policy import make_agent


PERCENTILES = {
    "WHEAT": 0.6426804833449733,
    "CARROT": 0.9394900324524804,
    "TOMATO": 0.9290076797484429,
    "STRAWBERRY": 0.5681297553792033,
    "MELON": 0.539664383294555,
    "EGG": 0.7664009089306357,
    "MILK": 0.48672925359295327,
    "WOOL": 0.546685210941122,
    "FERTILIZER": 0.4770015334688491,
}
OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
}
SEEDS = tuple(range(70000, 70016))


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * p
    low, high = math.floor(pos), math.ceil(pos)
    return values[low] if low == high else values[low] * (high - pos) + values[high] * (pos - low)


def main() -> int:
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    observed_prices = defaultdict(list)
    planned_prices = defaultdict(list)
    planned_quantities = defaultdict(list)
    planned_events = defaultdict(int)
    games = 0
    for family, path in OPPONENTS.items():
        for seed in SEEDS:
            for seat in (0, 1):
                policy = make_agent("parent")
                opponent = create_agent(registry, {
                    "id": f"sell_cal_{family}_{seed}_{seat}", "kind": "python",
                    "path": str(path), "entrypoint": "agent",
                })
                game = kagsim.Game(seed)
                agents = [None, None]
                agents[seat], agents[1 - seat] = policy, opponent
                while not game.done:
                    observations = [game.observe(0), game.observe(1)]
                    own_obs = observations[seat]
                    prices = dict((own_obs.get("market") or {}).get("prices") or {})
                    for item in PERCENTILES:
                        observed_prices[item].append(float(prices.get(item, 0) or 0))
                    actions = [agents[0](observations[0]), agents[1](observations[1])]
                    for order in actions[seat].get("market") or []:
                        if len(order) >= 3 and order[0] == "SELL" and order[1] in PERCENTILES:
                            item = str(order[1])
                            planned_prices[item].append(float(prices.get(item, 0) or 0))
                            planned_quantities[item].append(max(0, int(order[2] or 0)))
                            planned_events[item] += 1
                    game.step(*actions)
                games += 1
        print(f"completed {family}: {games} games", flush=True)

    products = {}
    for item, percentile in PERCENTILES.items():
        observed = observed_prices[item]
        planned = planned_prices[item]
        threshold = int(round(quantile(observed, percentile)))
        products[item] = {
            "initializer_percentile": percentile,
            "observed_steps": len(observed),
            "observed_price_min_median_max": [min(observed), statistics.median(observed), max(observed)],
            "price_threshold": threshold,
            "planned_sell_events": planned_events[item],
            "planned_sell_price_median": statistics.median(planned) if planned else None,
            "planned_sell_price_ge_threshold_share": sum(value >= threshold for value in planned) / len(planned) if planned else None,
            "planned_sell_quantity_median": statistics.median(planned_quantities[item]) if planned_quantities[item] else None,
        }
    result = {
        "schema": "kaggriculture-v19-product-sell-threshold-calibration-v1",
        "status": "DEVELOPMENT_CALIBRATION_NOT_EVALUATION",
        "engine": str(kagsim.ENGINE_VERSION),
        "seeds": list(SEEDS),
        "opponent_families": list(OPPONENTS),
        "double_seat": True,
        "games": games,
        "products": products,
    }
    (HERE / "sell_threshold_calibration.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
