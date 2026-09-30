#!/usr/bin/env python3
"""Official-engine screen of 1/2/4/8-tile TOMATO capacity substitutions.

Unlike the broad fraction screen, this treatment preserves every STRAWBERRY
sale order and adds TOMATO liquidation in unused market slots.  Seed quantities
are split exactly where queue capacity permits.  This isolates the value of a
small TOMATO production block without stranding the remaining strawberries.
"""

from __future__ import annotations

import copy
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
sys.path.insert(0, str(RESEARCH / "production_gap"))
import causal_blocks as cb  # type: ignore


ARENA = RESEARCH / "top_route_arena.json"
OUT = HERE / "isolated_capacity_screen.json"
CAPACITIES = (1, 2, 4, 8)


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] if lo == hi else values[lo] * (hi - pos) + values[hi] * (pos - lo)


def summary(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "p10": quantile(values, 0.1) if values else None,
        "positive_zero_negative": [sum(x > 0 for x in values), sum(x == 0 for x in values), sum(x < 0 for x in values)],
    }


def select_evenly(n: int, target: int) -> set[int]:
    target = min(n, target)
    return {min(n - 1, int((k + 0.5) * n / target)) for k in range(target)} if target else set()


def substitute_capacity(actions: list[dict[str, Any]], capacity: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    out = copy.deepcopy(actions)
    plants: list[list[Any]] = []
    for action in out:
        for order in [action.get("farmer"), *action.get("hands", [])]:
            if isinstance(order, list) and len(order) >= 2 and order[:2] == ["PLANT", "STRAWBERRY"]:
                plants.append(order)
    target = min(capacity, len(plants))
    for index in select_evenly(len(plants), target):
        plants[index][1] = "TOMATO"

    # Convert exactly `target` seed units, preferring earlier orders so every
    # selected plant has inventory available. A split adds one queue slot.
    remaining = target
    converted = 0
    for action in out:
        if remaining <= 0:
            break
        market = action.get("market", [])
        for index, order in list(enumerate(market)):
            if remaining <= 0:
                break
            if not isinstance(order, list) or len(order) < 3 or order[:2] != ["BUY_SEED", "STRAWBERRY"]:
                continue
            quantity = max(0, int(order[2]))
            take = min(quantity, remaining)
            if take == quantity:
                order[1] = "TOMATO"
            elif len(market) < 10:
                order[2] = quantity - take
                market.insert(index + 1, ["BUY_SEED", "TOMATO", take])
            else:
                continue
            remaining -= take
            converted += take

    # Keep all parent strawberry sales. At each such cadence, use a free slot
    # to liquidate any tomato currently in the shed; over-sized sells are safely
    # capped by the official engine to current inventory.
    liquidation_orders = 0
    for action in out:
        market = action.get("market", [])
        has_strawberry_sell = any(
            isinstance(order, list) and len(order) >= 2 and order[:2] == ["SELL", "STRAWBERRY"]
            for order in market
        )
        if has_strawberry_sell and len(market) < 10:
            market.append(["SELL", "TOMATO", 100])
            liquidation_orders += 1
    return out, {
        "target_plants": target,
        "converted_seed_units": converted,
        "unfilled_seed_units": remaining,
        "tomato_liquidation_orders": liquidation_orders,
    }


def shops(data: dict[str, Any]) -> dict[str, int]:
    obs = [step[0]["observation"] for step in data["steps"] if step and "market" in step[0]["observation"]]
    counts = Counter(obs[-1]["town"]["unlocked_shops"])
    inv = [int(x["market"]["inventory"]["TOMATO"]) for x in obs]
    prices = [int(x["market"]["prices"]["TOMATO"]) for x in obs]
    return {
        "tomato_shop_instances": counts["PIZZA_SHOP"] + counts["FARMERS_MARKET"],
        "strawberry_shop_instances": sum(counts[x] for x in ("SMOOTHIE_SHOP", "ICE_CREAM_SHOP", "BRUNCH_SPOT", "FARMERS_MARKET")),
        "pizza_count": counts["PIZZA_SHOP"],
        "farmers_market_count": counts["FARMERS_MARKET"],
        "baseline_tomato_min_inventory": min(inv),
        "baseline_tomato_max_price": max(prices),
        "baseline_tomato_crossed_knee": int(min(inv) < 9800),
    }


def group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "routes": len(rows),
        "own_delta": summary([r["own_delta"] for r in rows]),
        "opponent_delta": summary([r["opponent_delta"] for r in rows]),
        "margin_delta": summary([r["margin_delta"] for r in rows]),
        "score_delta": summary([r["score_delta"] for r in rows]),
        "w_to_l": sum(r["baseline_score"] == 1.0 and r["treated_score"] == 0.0 for r in rows),
        "l_to_w": sum(r["baseline_score"] == 0.0 and r["treated_score"] == 1.0 for r in rows),
    }


def main() -> None:
    arena = json.loads(ARENA.read_text())
    rows: list[dict[str, Any]] = []
    identity_checks = 0
    for route_id in sorted(arena["by_route"]):
        team, episode_text = route_id.rsplit("::", 1)
        data = cb.load(int(episode_text))
        pid = data["info"]["TeamNames"].index(team)
        actions = cb.streams(data)
        baseline, pair0 = cb.run_once(data, actions, pid)
        expected = [float(x) for x in data["rewards"]]
        if pair0 != expected:
            raise AssertionError(f"identity mismatch {route_id}")
        identity_checks += 1
        margin0 = pair0[pid] - pair0[1 - pid]
        features = shops(data)
        for capacity in CAPACITIES:
            treated_actions = copy.deepcopy(actions)
            treated_actions[pid], changes = substitute_capacity(treated_actions[pid], capacity)
            treated, pair1 = cb.run_once(data, treated_actions, pid)
            margin1 = pair1[pid] - pair1[1 - pid]
            rows.append({
                "route_id": route_id,
                "team": team,
                "episode_id": int(episode_text),
                "capacity": capacity,
                **features,
                **changes,
                "baseline_reward": baseline["reward"],
                "treated_reward": treated["reward"],
                "own_delta": pair1[pid] - pair0[pid],
                "opponent_delta": pair1[1 - pid] - pair0[1 - pid],
                "margin_delta": margin1 - margin0,
                "baseline_score": score(margin0),
                "treated_score": score(margin1),
                "score_delta": score(margin1) - score(margin0),
            })
    regimes: dict[str, Any] = {}
    for capacity in CAPACITIES:
        selected = [r for r in rows if r["capacity"] == capacity]
        regimes[str(capacity)] = {
            "overall": group(selected),
            "tomato_shops_0": group([r for r in selected if r["tomato_shop_instances"] == 0]),
            "tomato_shops_1": group([r for r in selected if r["tomato_shop_instances"] == 1]),
            "tomato_shops_ge2": group([r for r in selected if r["tomato_shop_instances"] >= 2]),
            "crossed_hinge_knee": group([r for r in selected if r["baseline_tomato_crossed_knee"]]),
            "not_crossed_hinge_knee": group([r for r in selected if not r["baseline_tomato_crossed_knee"]]),
        }
    result = {
        "status": "OPEN_LOOP_ISOLATED_CAPACITY_SCREEN_NOT_LIVE_POLICY_EVIDENCE",
        "engine": cb.audit.engine_metadata(),
        "identity_checks": identity_checks,
        "treatment": "replace 1/2/4/8 evenly spaced strawberry plant slots plus exact seed units with tomato; preserve strawberry sells and add tomato liquidation in free market slots",
        "regimes": regimes,
        "rows": rows,
        "boundary": "Only a positive, shop-observable regime can justify building and live-testing a full TOMATO expert.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(regimes, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
