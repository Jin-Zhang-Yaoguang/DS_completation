#!/usr/bin/env python3
"""Closed-state test of a sufficient-condition market slot dominance gate.

The gate moves non-buyable product SELLs left across HIRE/BUY_LAND/BUY_SEED
only when current cash covers every such fixed-cost request in the turn and no
BUY_PRODUCT/BUY_ANIMAL is present.  Under 1.32.7 this preserves our executed
purchases and end-of-turn resources; before town consumption the relevant
market inventories can only rise, so the move weakly improves match margin.
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
from pathlib import Path

from mechanism_probe import KAGSIM, PRODUCTS, TEAMS, game_score, newest_routes


HERE = Path(__file__).resolve().parent
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
LAND_COST = (1000, 2000, 4000)
SAFE = set(PRODUCTS) - {"WHEAT", "FERTILIZER"}


def fib(n: int) -> int:
    if n <= 1:
        return 1
    a, b = 1, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def gated_action(obs: dict, raw: dict) -> tuple[dict, bool]:
    action = copy.deepcopy(raw)
    market = list(action.get("market") or [])[:10]
    if any(o and o[0] in ("BUY_PRODUCT", "BUY_ANIMAL") for o in market):
        return action, False
    farm = (obs.get("farms") or [{}, {}])[int(obs.get("player", 0))]
    hires = int(farm.get("hires_today", 0) or 0)
    quadrants = len(farm.get("unlocked_quadrants", []) or [])
    spend = 0
    for order in market:
        if not order:
            continue
        if order[0] == "HIRE":
            spend += fib(hires)
            hires += 1
        elif order[0] == "BUY_LAND":
            extra = quadrants - 1
            if 0 <= extra < len(LAND_COST):
                spend += LAND_COST[extra]
                quadrants += 1
        elif order[0] == "BUY_SEED" and len(order) >= 3:
            spend += SEED_COST.get(str(order[1]), 10**9) * max(0, int(order[2] or 0))
    if float(farm.get("money", 0) or 0) < spend:
        return action, False

    changed = False
    for i in range(1, len(market)):
        if not (market[i] and market[i][0] == "SELL" and len(market[i]) >= 3 and str(market[i][1]) in SAFE):
            continue
        j = i
        while j > 0 and market[j - 1] and market[j - 1][0] in ("HIRE", "BUY_LAND", "BUY_SEED"):
            market[j - 1], market[j] = market[j], market[j - 1]
            j -= 1
            changed = True
    action["market"] = market
    return action, changed


def run_pair(route: dict, rival: dict, seed: int, seat: int, treated: bool) -> tuple[float, float, int]:
    game = KAGSIM.Game(seed)
    changed = 0
    while not game.done:
        step = game.step_count
        own = route["actions"][step] if step < len(route["actions"]) else {}
        opp = rival["actions"][step] if step < len(rival["actions"]) else {}
        if treated:
            own, did = gated_action(game.observe(seat), own)
            changed += int(did)
        if seat == 0:
            game.step(own, opp)
        else:
            game.step(opp, own)
    return float(game.reward(seat)), float(game.reward(1 - seat)), changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes-per-team", type=int, default=3)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=70000)
    parser.add_argument("--output", default=str(HERE / "safe_slot_results.json"))
    args = parser.parse_args()
    routes = newest_routes(args.routes_per_team)
    rivals = [max((r for r in routes if r["team"] == team), key=lambda r: r["episode"]) for team in TEAMS]
    rows = []
    for route in routes:
        for rival in rivals:
            for seed in range(args.seed_start, args.seed_start + args.seeds):
                for seat in (0, 1):
                    base_own, base_opp, _ = run_pair(route, rival, seed, seat, False)
                    own, opp, changed = run_pair(route, rival, seed, seat, True)
                    rows.append({
                        "route": route["id"], "rival_team": rival["team"], "seed": seed, "seat": seat,
                        "changed_turns": changed, "base_own": base_own, "own": own,
                        "base_margin": base_own - base_opp, "margin": own - opp,
                        "base_score": game_score(base_own, base_opp), "score": game_score(own, opp),
                    })
    margin_delta = [r["margin"] - r["base_margin"] for r in rows]
    score_delta = [r["score"] - r["base_score"] for r in rows]
    result = {
        "status": "SUFFICIENT_CONDITION_MECHANISM_TEST_NOT_POLICY_QUALIFICATION",
        "engine": KAGSIM.ENGINE_VERSION,
        "unseen_seed_range": [args.seed_start, args.seed_start + args.seeds - 1],
        "games": len(rows), "both_seats": True,
        "changed_games": sum(r["changed_turns"] > 0 for r in rows),
        "changed_turns": sum(r["changed_turns"] for r in rows),
        "score_uplift_pp": 100 * statistics.mean(score_delta),
        "l_to_w": sum(r["base_score"] == 0 and r["score"] == 1 for r in rows),
        "w_to_l": sum(r["base_score"] == 1 and r["score"] == 0 for r in rows),
        "own_delta_mean": statistics.mean(r["own"] - r["base_own"] for r in rows),
        "margin_delta_mean": statistics.mean(margin_delta),
        "margin_positive_zero_negative": [sum(x > 0 for x in margin_delta), sum(x == 0 for x in margin_delta), sum(x < 0 for x in margin_delta)],
        "by_rival": {
            team: {
                "games": len(group := [r for r in rows if r["rival_team"] == team]),
                "score_uplift_pp": 100 * statistics.mean(r["score"] - r["base_score"] for r in group),
                "margin_delta_mean": statistics.mean(r["margin"] - r["base_margin"] for r in group),
            }
            for team in TEAMS
        },
        "gate": {
            "moved_products": sorted(SAFE),
            "crossed_order_types": ["HIRE", "BUY_LAND", "BUY_SEED"],
            "forbidden_turn_types": ["BUY_PRODUCT", "BUY_ANIMAL"],
            "cash_condition": "current money >= total fixed cost of all HIRE/BUY_LAND/BUY_SEED requests",
        },
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
