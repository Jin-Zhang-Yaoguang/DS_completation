#!/usr/bin/env python3
"""Build standalone V20 from the qualified V19 package plus demand-timed sells."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
BASE = MODEL / "v19_hierarchical_moe" / "main.py"


APPENDIX = r'''

# --- V20 product-level sell controller: shift 25% past same-step town demand ---
_V20_PARENT_AGENT = agent
_V20_DELAY_FRACTION = 0.25
_V20_DELAY_START = 360
_V20_DELAY_STOP = 672
_V20_SHED_GUARD = 80
_V20_STATE = {
    0: {"last": -1, "due_step": -1, "due": {}},
    1: {"last": -1, "due_step": -1, "due": {}},
}
__version__ = "v20-demand-timing-hierarchical-moe-rc1"


def _v20_town_demand(obs, item, step):
    demand = 1 if item != "FERTILIZER" and step % 24 == 0 else 0
    if step % 4 != 0:
        return demand
    town = _get(obs, "town", {}) or {}
    for shop in list(_get(town, "unlocked_shops", []) or []):
        products = _SHOP_PRODUCTS.get(shop, ())
        if item in products:
            demand += 2 if len(products) == 1 else 1
    return demand


def _v20_delay_sales(obs, action, step):
    seat = _seat(obs)
    state = _V20_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, due_step=-1, due={})
    state["last"] = step
    action = _copy_action(action)
    market = [list(order) for order in (action.get("market") or [])]
    due_step = int(state.get("due_step", -1))
    due = {str(item): max(0, int(quantity or 0)) for item, quantity in dict(state.get("due") or {}).items()}
    if due and due_step <= step:
        for item, quantity in due.items():
            if quantity <= 0:
                continue
            existing = next((order for order in market if _is_sell(order) and str(order[1]) == item), None)
            if existing is not None:
                existing[2] = max(0, int(existing[2] or 0)) + quantity
            elif len(market) < 10:
                market.append(["SELL", item, quantity])
            else:
                state["due_step"] = step + 1
                action["market"] = market[:10]
                return action
        state["due_step"] = -1
        state["due"] = {}

    can_delay = (
        _V20_DELAY_START <= step < _V20_DELAY_STOP
        and not due
        and market
        and all(_is_sell(order) for order in market)
    )
    if can_delay:
        private = _get(obs, "private", {}) or {}
        shed = dict(_get(private, "shed", {}) or {})
        shed_total = sum(max(0, int(value or 0)) for value in shed.values())
        next_market = list((_ACTIONS[step + 1] or {}).get("market") or []) if step + 1 < len(_ACTIONS) else []
        delayed = {}
        if shed_total < _V20_SHED_GUARD:
            for order in market:
                item = str(order[1])
                quantity = max(0, int(order[2] or 0))
                next_has_room = len(next_market) < 10 or any(_is_sell(future) and str(future[1]) == item for future in next_market)
                if quantity <= 0 or _v20_town_demand(obs, item, step) <= 0 or not next_has_room:
                    continue
                shift = min(quantity, max(1, int(round(quantity * _V20_DELAY_FRACTION))))
                order[2] = quantity - shift
                delayed[item] = delayed.get(item, 0) + shift
        if delayed:
            market = [order for order in market if max(0, int(order[2] or 0)) > 0]
            state["due_step"] = step + 1
            state["due"] = delayed
    action["market"] = market[:10]
    return _rank_sell_slots(obs, action, None)


del agent
def agent(obs, configuration=None):
    action = _V20_PARENT_AGENT(obs, configuration)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    return _v20_delay_sales(obs, action, step)
'''


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + APPENDIX, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V20 demand-timing hierarchical MoE RC1",
        "status": "OFFLINE_GOLD_CANDIDATE_QA_PASS",
        "parent": "V19 hierarchical MoE step-360 RC1",
        "controller": "delay 25% of eligible all-SELL queues by one turn when same-step town demand follows market execution",
        "active_steps": [360, 671],
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "confirmation": {
            "games_each": 1792,
            "opponent_families": 7,
            "score_uplift_pp": 6.529017857142858,
            "score_uplift_ci95_pp": [5.189732142857142, 7.924107142857142],
            "positive_zero_negative": [220, 1556, 16],
            "mean_margin_delta": 91.4375,
            "mean_own_delta": 34.81919642857143
        },
        "qa": {
            "research_package_exact_games": [8, 8],
            "official_cpp_exact_games": [4, 4],
            "action_safety_games": 224,
            "unit_orders": 1495967,
            "unit_precondition_invalid": 0,
            "market_overflow": 0,
            "hand_mismatch": 0
        }
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
