#!/usr/bin/env python3
"""Exact 1.32.7 mechanism probes for the next gold strategy.

The slot experiment is intentionally split into two estimands:

* ``sell_front`` is causal and deployable: SELL orders are moved before this
  player's non-SELL orders, preserving SELL relative order and quantities.
* ``rival_slot_oracle`` uses the opponent's simultaneous action to order our
  SELL products.  It is not deployable; it is an upper bound on the value of
  predicting the opponent's same-turn market flow from public history.

Both are evaluated on a broad fixed-route arena with unseen simulator seeds,
both seats, and exact 1.32.7 market resolution.  Fixed routes are a mechanism
test, not closed-loop policy qualification.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]
RESEARCH = ROOT / "kaggle_Kaggriculture" / "model" / "v16_gold_strategy_research"
DATA = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
CPPSIM = ROOT / "kaggle_Kaggriculture" / "model" / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
TEAMS = ("Crop Dusta", "Ryo Hasegawa", "Subramanya N", "tetsuya", "Kronki", "tyz123456")
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SHOP_COEFF = {
    "BAKERY": {"WHEAT": 1, "EGG": 1},
    "BRUNCH_SPOT": {"WHEAT": 1, "EGG": 1, "STRAWBERRY": 1},
    "FARMERS_MARKET": {"WHEAT": 1, "CARROT": 1, "TOMATO": 1, "STRAWBERRY": 1},
    "ICE_CREAM_SHOP": {"WHEAT": 1, "STRAWBERRY": 1, "MILK": 1},
    "PET_CAFE": {"CARROT": 2},
    "PIZZA_SHOP": {"WHEAT": 1, "TOMATO": 1, "MILK": 1},
    "SMOOTHIE_SHOP": {"STRAWBERRY": 1, "MILK": 1},
    "YARN_STORE": {"WOOL": 2},
}
UNLOCK_STEPS = tuple(range(72, 72 * 9, 72))
SHOP_TICKS_REMAINING = tuple(len(range(step, 720, 4)) for step in UNLOCK_STEPS)


def load_cppsim():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim build missing")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = load_cppsim()


def newest_routes(per_team: int) -> list[dict]:
    selected: dict[str, list[Path]] = {team: [] for team in TEAMS}
    for path in DATA.glob("*.json"):
        text = path.open(errors="ignore").read(5000)
        for team in TEAMS:
            if json.dumps(team) in text:
                selected[team].append(path)
    rows = []
    for team in TEAMS:
        for path in sorted(selected[team], key=lambda p: int(p.stem), reverse=True)[:per_team]:
            replay = json.loads(path.read_text())
            seat = replay["info"]["TeamNames"].index(team)
            actions = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
            rows.append({
                "id": f"{team}::{path.stem}", "team": team,
                "episode": int(path.stem), "actions": actions,
            })
    return rows


def is_sell(order: list) -> bool:
    return bool(order) and order[0] == "SELL" and len(order) >= 3


def sell_front(actions: list[dict]) -> list[dict]:
    out = copy.deepcopy(actions)
    for action in out:
        market = list(action.get("market") or [])[:10]
        action["market"] = [o for o in market if is_sell(o)] + [o for o in market if not is_sell(o)]
    return out


def nonbuyable_sell_front(actions: list[dict]) -> list[dict]:
    """Provably safe slot move for products the rival cannot BUY from market.

    For CARROT/TOMATO/STRAWBERRY/MELON/EGG/MILK/WOOL, market inventory can only
    stay flat or rise during market processing (town demand happens later).
    Crossing an earlier slot therefore weakly raises our quote and weakly
    lowers any intervening rival same-product quote.  WHEAT/FERTILIZER are
    excluded because a rival BUY_PRODUCT can reverse that monotonicity.
    """
    out = copy.deepcopy(actions)
    safe = set(PRODUCTS) - {"WHEAT", "FERTILIZER"}
    for action in out:
        market = list(action.get("market") or [])[:10]
        # Bubble only across non-SELL orders.  Crossing a WHEAT/FERTILIZER SELL
        # would delay that sale and void the dominance argument.
        for i in range(1, len(market)):
            if not (is_sell(market[i]) and str(market[i][1]) in safe):
                continue
            j = i
            while j > 0 and not is_sell(market[j - 1]):
                market[j - 1], market[j] = market[j], market[j - 1]
                j -= 1
        action["market"] = market
    return out


def rival_slot_oracle(actions: list[dict], rival: list[dict]) -> list[dict]:
    """Hindsight upper bound: prioritize products rival sells earliest/most."""
    out = copy.deepcopy(actions)
    for step, action in enumerate(out):
        market = list(action.get("market") or [])[:10]
        sells = [(i, o) for i, o in enumerate(market) if is_sell(o)]
        if not sells:
            continue
        rival_market = list((rival[step].get("market") if step < len(rival) else []) or [])[:10]
        rival_flow: dict[str, tuple[int, int]] = {}
        for slot, order in enumerate(rival_market):
            if not is_sell(order):
                continue
            item, qty = str(order[1]), max(0, int(order[2] or 0))
            first, total = rival_flow.get(item, (99, 0))
            rival_flow[item] = (min(first, slot), total + qty)

        # Collision products first.  More rival volume and earlier rival slot
        # mean more common-pool price capacity at risk.  Stable original order
        # breaks ties.  Non-SELLs follow, because any intervening rival SELL can
        # only weakly lower our quote under the exact independent-product curves.
        ranked = sorted(
            sells,
            key=lambda row: (
                0 if str(row[1][1]) in rival_flow else 1,
                -rival_flow.get(str(row[1][1]), (99, 0))[1],
                rival_flow.get(str(row[1][1]), (99, 0))[0],
                row[0],
            ),
        )
        action["market"] = [o for _, o in ranked] + [o for o in market if not is_sell(o)]
    return out


def game_score(own: float, opp: float) -> float:
    return 1.0 if own > opp else 0.5 if own == opp else 0.0


def paired_summary(rows: list[dict]) -> dict:
    score_delta = [row["treated_score"] - row["base_score"] for row in rows]
    margin_delta = [row["treated_margin"] - row["base_margin"] for row in rows]
    own_delta = [row["treated_own"] - row["base_own"] for row in rows]
    return {
        "games": len(rows),
        "base_score_rate": statistics.mean(row["base_score"] for row in rows),
        "treated_score_rate": statistics.mean(row["treated_score"] for row in rows),
        "score_uplift_pp": 100 * statistics.mean(score_delta),
        "l_to_w": sum(row["base_score"] == 0 and row["treated_score"] == 1 for row in rows),
        "w_to_l": sum(row["base_score"] == 1 and row["treated_score"] == 0 for row in rows),
        "own_delta_mean": statistics.mean(own_delta),
        "margin_delta_mean": statistics.mean(margin_delta),
        "margin_delta_p10": sorted(margin_delta)[max(0, math.ceil(0.1 * len(margin_delta)) - 1)],
        "margin_positive_zero_negative": [
            sum(v > 0 for v in margin_delta), sum(v == 0 for v in margin_delta), sum(v < 0 for v in margin_delta)
        ],
    }


def town_information() -> dict:
    weights = SHOP_TICKS_REMAINING
    total_weight = sum(weights)
    sum_sq = sum(w * w for w in weights)
    rows = {}
    shops = tuple(SHOP_COEFF)
    for item in PRODUCTS:
        coeffs = [SHOP_COEFF[shop].get(item, 0) for shop in shops]
        mean_c = statistics.mean(coeffs)
        var_c = statistics.pvariance(coeffs)
        center = 0 if item == "FERTILIZER" else 30
        expected = center + total_weight * mean_c
        sd = math.sqrt(sum_sq * var_c)
        rows[item] = {
            "expected_total_town_drain": expected,
            "sd_from_random_shops": sd,
            "coefficient_of_variation": sd / expected if expected else None,
            "minimum": center + total_weight * min(coeffs),
            "maximum": center + total_weight * max(coeffs),
        }
    cumulative = []
    used = 0
    for day, weight in zip(range(3, 25, 3), weights, strict=True):
        used += weight
        cumulative.append({
            "day": day, "new_shop_weight": weight,
            "fraction_of_all_shop_demand_revealed": used / total_weight,
        })
    return {
        "unlock_days": list(range(3, 25, 3)),
        "remaining_shop_consumption_ticks": list(weights),
        "total_weight": total_weight,
        "first_shop_fraction_of_shop_demand": weights[0] / total_weight,
        "future_unknown_fraction_after_first_shop": 1 - weights[0] / total_weight,
        "cumulative_information": cumulative,
        "by_product": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes-per-team", type=int, default=3)
    parser.add_argument("--seeds", type=int, default=80)
    parser.add_argument("--seed-start", type=int, default=60000)
    parser.add_argument("--output", default=str(HERE / "mechanism_results.json"))
    args = parser.parse_args()

    routes = newest_routes(args.routes_per_team)
    rivals = []
    for team in TEAMS:
        rivals.append(max((row for row in routes if row["team"] == team), key=lambda r: r["episode"]))

    estimands: dict[str, list[dict]] = {
        "sell_front": [],
        "nonbuyable_sell_front": [],
        "rival_slot_oracle": [],
    }
    for name in estimands:
        jobs, labels = [], []
        streams: list[object] = []  # retain references consumed by C++ jobs
        for route in routes:
            for rival in rivals:
                base_stream = KAGSIM.Stream(route["actions"])
                rival_stream = KAGSIM.Stream(rival["actions"])
                if name == "sell_front":
                    treated_actions = sell_front(route["actions"])
                elif name == "nonbuyable_sell_front":
                    treated_actions = nonbuyable_sell_front(route["actions"])
                else:
                    treated_actions = rival_slot_oracle(route["actions"], rival["actions"])
                treated_stream = KAGSIM.Stream(treated_actions)
                streams.extend((base_stream, rival_stream, treated_stream))
                for seed in range(args.seed_start, args.seed_start + args.seeds):
                    for seat in (0, 1):
                        if seat == 0:
                            jobs.extend(((base_stream, rival_stream, seed), (treated_stream, rival_stream, seed)))
                        else:
                            jobs.extend(((rival_stream, base_stream, seed), (rival_stream, treated_stream, seed)))
                        labels.append((route, rival, seed, seat))
        rewards = KAGSIM.run_many(jobs)
        for index, (route, rival, seed, seat) in enumerate(labels):
            base = rewards[2 * index]
            treated = rewards[2 * index + 1]
            b_own, b_opp = float(base[seat]), float(base[1 - seat])
            t_own, t_opp = float(treated[seat]), float(treated[1 - seat])
            estimands[name].append({
                "route": route["id"], "route_team": route["team"],
                "rival": rival["id"], "rival_team": rival["team"],
                "seed": seed, "seat": seat,
                "base_own": b_own, "base_margin": b_own - b_opp, "base_score": game_score(b_own, b_opp),
                "treated_own": t_own, "treated_margin": t_own - t_opp, "treated_score": game_score(t_own, t_opp),
            })

    result = {
        "status": "EXACT_MECHANISM_SCREEN_NOT_CLOSED_LOOP_QUALIFICATION",
        "engine": KAGSIM.ENGINE_VERSION,
        "source_date": "2026-08-25",
        "unseen_seed_range": [args.seed_start, args.seed_start + args.seeds - 1],
        "both_seats": True,
        "routes": [{k: r[k] for k in ("id", "team", "episode")} for r in routes],
        "opponent_routes": [{k: r[k] for k in ("id", "team", "episode")} for r in rivals],
        "town_information": town_information(),
        "slot_estimands": {
            name: {
                "deployable": name != "rival_slot_oracle",
                "overall": paired_summary(rows),
                "by_rival_family": {
                    team: paired_summary([r for r in rows if r["rival_team"] == team]) for team in TEAMS
                },
            }
            for name, rows in estimands.items()
        },
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "engine": result["engine"],
        "town_information": result["town_information"],
        "slot_estimands": result["slot_estimands"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
