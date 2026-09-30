"""Test a complete STRAWBERRY->TOMATO route substitution on current top tapes.

This is deliberately an open-loop mechanism screen.  It keeps movement,
watering, harvest cadence, labour, land and the opponent fixed, while changing
all strawberry seed purchases/plantings/sales to tomato.  A positive result in
a town regime identifies a missing complete expert; it is not a live-policy
win-rate estimate.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "production_gap"))

import causal_blocks as cb


ARENA = HERE / "top_route_arena.json"
OUT = HERE / "tomato_regime_counterfactual.json"


def replace_strawberry_with_tomato(actions):
    out = copy.deepcopy(actions)
    changed = 0
    for action in out:
        for actor in ("farmer", "hands"):
            orders = [action.get("farmer")] if actor == "farmer" else action.get("hands", [])
            for order in orders:
                if isinstance(order, list) and len(order) >= 2 and order[0] == "PLANT" and order[1] == "STRAWBERRY":
                    order[1] = "TOMATO"
                    changed += 1
        for order in action.get("market", []):
            if not isinstance(order, list) or len(order) < 2:
                continue
            if order[0] == "BUY_SEED" and order[1] == "STRAWBERRY":
                order[1] = "TOMATO"
                changed += 1
            elif order[0] == "SELL" and order[1] == "STRAWBERRY":
                order[1] = "TOMATO"
                changed += 1
    return out, changed


def summarize(values):
    return {
        "n": len(values),
        "mean": mean(values) if values else None,
        "median": median(values) if values else None,
        "positive_zero_negative": [
            sum(value > 0 for value in values),
            sum(value == 0 for value in values),
            sum(value < 0 for value in values),
        ],
    }


def main():
    arena = json.loads(ARENA.read_text())
    route_ids = sorted(arena["by_route"])
    rows = []
    for route_id in route_ids:
        team, episode_text = route_id.rsplit("::", 1)
        episode_id = int(episode_text)
        data = cb.load(episode_id)
        pid = data["info"]["TeamNames"].index(team)
        actions = cb.streams(data)

        baseline, baseline_pair = cb.run_once(data, actions, pid)
        expected = [float(value) for value in data["rewards"]]
        if baseline_pair != expected:
            raise AssertionError(f"identity mismatch for {episode_id}: {baseline_pair} != {expected}")

        treated_actions = copy.deepcopy(actions)
        treated_actions[pid], changed = replace_strawberry_with_tomato(treated_actions[pid])
        treated, treated_pair = cb.run_once(data, treated_actions, pid)
        baseline_margin = baseline_pair[pid] - baseline_pair[1 - pid]
        treated_margin = treated_pair[pid] - treated_pair[1 - pid]
        shops = data["steps"][-1][pid]["observation"]["town"]["unlocked_shops"]
        rows.append({
            "route_id": route_id,
            "team": team,
            "episode_id": episode_id,
            "shops": shops,
            "pizza_count": shops.count("PIZZA_SHOP"),
            "farmers_market_count": shops.count("FARMERS_MARKET"),
            "strawberry_shop_count": sum(
                shops.count(name)
                for name in ("SMOOTHIE_SHOP", "ICE_CREAM_SHOP", "BRUNCH_SPOT", "FARMERS_MARKET")
            ),
            "changed_orders": changed,
            "baseline_reward": baseline["reward"],
            "treated_reward": treated["reward"],
            "own_delta": treated["reward"] - baseline["reward"],
            "baseline_margin": baseline_margin,
            "treated_margin": treated_margin,
            "margin_delta": treated_margin - baseline_margin,
            "baseline_sell_cash": baseline["sell_cash"],
            "treated_sell_cash": treated["sell_cash"],
        })

    regimes = {}
    for tag, predicate in {
        "pizza_or_farmers_ge_2": lambda row: row["pizza_count"] + row["farmers_market_count"] >= 2,
        "pizza_or_farmers_lt_2": lambda row: row["pizza_count"] + row["farmers_market_count"] < 2,
        "pizza_ge_2": lambda row: row["pizza_count"] >= 2,
        "strawberry_shops_ge_3": lambda row: row["strawberry_shop_count"] >= 3,
    }.items():
        selected = [row for row in rows if predicate(row)]
        regimes[tag] = {
            "routes": len(selected),
            "own_delta": summarize([row["own_delta"] for row in selected]),
            "margin_delta": summarize([row["margin_delta"] for row in selected]),
        }

    result = {
        "status": "OPEN_LOOP_MECHANISM_SCREEN_NOT_LIVE_POLICY_EVIDENCE",
        "engine": cb.audit.engine_metadata(),
        "treatment": "complete STRAWBERRY->TOMATO substitution; all other own actions and opponent tape fixed",
        "source": str(ARENA),
        "identity_checks": len(rows),
        "overall": {
            "own_delta": summarize([row["own_delta"] for row in rows]),
            "margin_delta": summarize([row["margin_delta"] for row in rows]),
        },
        "regimes": regimes,
        "rows": rows,
        "boundary": "This can reveal a missing town-conditioned expert but cannot qualify a submission without closed-loop replanning and unseen-seed live evaluation.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "overall", "regimes")}, indent=2))


if __name__ == "__main__":
    main()
