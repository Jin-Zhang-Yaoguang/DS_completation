#!/usr/bin/env python3
"""Official-engine open-loop screen for a missing TOMATO production expert.

The treatment preserves the recorded movement/watering/harvest schedule and
substitutes a deterministic share of STRAWBERRY production orders with TOMATO.
It is a mechanism screen, not live-policy evidence.
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
OUT = HERE / "open_loop_screen.json"
VARIANTS = (0.25, 0.50, 1.00)


def quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lo, hi = math.floor(position), math.ceil(position)
    if lo == hi:
        return ordered[lo]
    w = position - lo
    return ordered[lo] * (1.0 - w) + ordered[hi] * w


def summary(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "p10": quantile(values, 0.10) if values else None,
        "positive_zero_negative": [
            sum(x > 0 for x in values),
            sum(x == 0 for x in values),
            sum(x < 0 for x in values),
        ],
    }


def replace_fraction(actions: list[dict[str, Any]], fraction: float) -> tuple[list[dict[str, Any]], Counter]:
    """Replace the same deterministic fraction in each relevant order class.

    Evenly spaced ordinal selection avoids concentrating a partial treatment at
    the beginning or end of the season. BUY_SEED, PLANT and SELL are selected
    separately because the replay queues can contain unsuccessful orders.
    """
    out = copy.deepcopy(actions)
    refs: dict[str, list[list[Any]]] = {"BUY_SEED": [], "PLANT": [], "SELL": []}
    for action in out:
        unit_orders = [action.get("farmer"), *action.get("hands", [])]
        for order in unit_orders:
            if isinstance(order, list) and len(order) >= 2 and order[:2] == ["PLANT", "STRAWBERRY"]:
                refs["PLANT"].append(order)
        for order in action.get("market", []):
            if not isinstance(order, list) or len(order) < 2 or order[1] != "STRAWBERRY":
                continue
            if order[0] in ("BUY_SEED", "SELL"):
                refs[order[0]].append(order)

    changed = Counter()
    for op, orders in refs.items():
        n = len(orders)
        target = int(round(n * fraction))
        if target <= 0:
            continue
        # The midpoint of each of `target` equal ordinal bins.
        selected = {min(n - 1, int((k + 0.5) * n / target)) for k in range(target)}
        for index in sorted(selected):
            orders[index][1] = "TOMATO"
            changed[op] += 1
    return out, changed


def route_shop_features(data: dict[str, Any]) -> dict[str, int]:
    shops = data["steps"][-1][0]["observation"]["town"]["unlocked_shops"]
    counts = Counter(shops)
    tomato = counts["PIZZA_SHOP"] + counts["FARMERS_MARKET"]
    strawberry = sum(counts[x] for x in ("SMOOTHIE_SHOP", "ICE_CREAM_SHOP", "BRUNCH_SPOT", "FARMERS_MARKET"))
    return {
        "tomato_shop_instances": tomato,
        "strawberry_shop_instances": strawberry,
        "relative_tomato_minus_strawberry": tomato - strawberry,
        "pizza_count": counts["PIZZA_SHOP"],
        "farmers_market_count": counts["FARMERS_MARKET"],
    }


def group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "routes": len(rows),
        "own_delta": summary([float(r["own_delta"]) for r in rows]),
        "margin_delta": summary([float(r["margin_delta"]) for r in rows]),
        "score_delta": summary([float(r["score_delta"]) for r in rows]),
        "w_to_l": sum(r["baseline_score"] == 1.0 and r["treated_score"] == 0.0 for r in rows),
        "l_to_w": sum(r["baseline_score"] == 0.0 and r["treated_score"] == 1.0 for r in rows),
    }


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def main() -> None:
    arena = json.loads(ARENA.read_text())
    rows: list[dict[str, Any]] = []
    identity_checks = 0
    for route_id in sorted(arena["by_route"]):
        team, episode_text = route_id.rsplit("::", 1)
        episode_id = int(episode_text)
        data = cb.load(episode_id)
        pid = data["info"]["TeamNames"].index(team)
        actions = cb.streams(data)
        baseline, baseline_pair = cb.run_once(data, actions, pid)
        expected = [float(x) for x in data["rewards"]]
        if baseline_pair != expected:
            raise AssertionError(f"identity mismatch {route_id}: {baseline_pair} != {expected}")
        identity_checks += 1
        baseline_margin = baseline_pair[pid] - baseline_pair[1 - pid]
        features = route_shop_features(data)
        for fraction in VARIANTS:
            treated_actions = copy.deepcopy(actions)
            treated_actions[pid], changed = replace_fraction(treated_actions[pid], fraction)
            treated, treated_pair = cb.run_once(data, treated_actions, pid)
            treated_margin = treated_pair[pid] - treated_pair[1 - pid]
            rows.append({
                "route_id": route_id,
                "team": team,
                "episode_id": episode_id,
                "player_id": pid,
                "fraction": fraction,
                **features,
                "changed_orders": dict(changed),
                "baseline_reward": baseline["reward"],
                "treated_reward": treated["reward"],
                "own_delta": treated["reward"] - baseline["reward"],
                "baseline_margin": baseline_margin,
                "treated_margin": treated_margin,
                "margin_delta": treated_margin - baseline_margin,
                "baseline_score": score(baseline_margin),
                "treated_score": score(treated_margin),
                "score_delta": score(treated_margin) - score(baseline_margin),
                "baseline_sell_cash": baseline["sell_cash"],
                "treated_sell_cash": treated["sell_cash"],
                "baseline_harvest": baseline["harvest"],
                "treated_harvest": treated["harvest"],
            })

    regimes: dict[str, Any] = {}
    predicates = {
        "tomato_shops_0": lambda r: r["tomato_shop_instances"] == 0,
        "tomato_shops_1": lambda r: r["tomato_shop_instances"] == 1,
        "tomato_shops_ge2": lambda r: r["tomato_shop_instances"] >= 2,
        "tomato_shops_ge3": lambda r: r["tomato_shop_instances"] >= 3,
        "relative_gap_ge_minus2": lambda r: r["relative_tomato_minus_strawberry"] >= -2,
        "relative_gap_lt_minus2": lambda r: r["relative_tomato_minus_strawberry"] < -2,
    }
    for fraction in VARIANTS:
        frows = [r for r in rows if r["fraction"] == fraction]
        regimes[str(fraction)] = {"overall": group(frows)}
        for name, predicate in predicates.items():
            regimes[str(fraction)][name] = group([r for r in frows if predicate(r)])

    result = {
        "status": "OPEN_LOOP_MECHANISM_SCREEN_NOT_LIVE_POLICY_EVIDENCE",
        "engine": cb.audit.engine_metadata(),
        "source": str(ARENA),
        "identity_checks": identity_checks,
        "treatment": "evenly-spaced 25/50/100% STRAWBERRY BUY_SEED+PLANT+SELL order substitution to TOMATO; movement, watering, harvest cadence, other own actions and opponent tape fixed",
        "regimes": regimes,
        "rows": rows,
        "boundary": "A positive regime only motivates a complete closed-loop expert; this screen cannot qualify a submission.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(regimes, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
