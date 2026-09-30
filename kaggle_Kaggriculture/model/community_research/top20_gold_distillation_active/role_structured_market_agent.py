"""Research agent using Top20-distilled causal market event/quantity trees."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

os.environ["ROLE_CAUSAL_COMPILER"] = "0"
os.environ["ROLE_PREEMPT_ITEMS"] = "none"
os.environ["ROLE_PREBUY_HORIZON"] = "0"
os.environ["ROLE_QUEUE_EXPERT"] = "0"

import contract_features as FEATURES
import role_option_agent as ROLE


HERE = Path(__file__).resolve().parent
MODEL = json.loads(Path(os.environ.get("STRUCTURED_MARKET_MODEL", HERE / "structured_market_hmoe.json")).read_text(encoding="utf-8"))
STATE = {0: {}, 1: {}}
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
PRIORITY = {"SELL": 0, "HIRE": 1, "BUY_LAND": 2, "BUY_SEED": 3, "BUY_ANIMAL": 4, "BUY_PRODUCT": 5}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _seat(obs: Mapping[str, Any]) -> int:
    return 1 if _int(obs.get("player")) == 1 else 0


def _tree(root: dict, features: Mapping[str, float], field: str) -> float:
    node = root
    while "feature" in node:
        node = node["left"] if float(features.get(node["feature"], 0.0)) <= float(node["threshold"]) else node["right"]
    return float(node[field])


def _raw_predictions(obs: dict, previous: dict | None) -> list[tuple[float, float, list]]:
    features = FEATURES.state_features(obs, previous)
    result = []
    for key, model in MODEL["models"].items():
        probability = _tree(model["event"]["root"], features, "probability")
        if probability < float(model["threshold"]):
            continue
        quantity = max(1, int(round(_tree(model["quantity"]["root"], features, "value"))))
        if ":" in key:
            op, item = key.split(":", 1)
            order = [op, item, quantity]
        else:
            op, order = key, [key, quantity]
        # Confidence margin is only a tie-breaker inside a semantic priority.
        position = _tree(model["position"]["root"], features, "value") if "position" in model else float(PRIORITY.get(op, 9))
        result.append((position, probability-float(model["threshold"]), order))
    return result


def _fib(index: int) -> int:
    a, b = 0, 1
    for _ in range(max(0, index)):
        a, b = b, a+b
    return a


def _safe_queue(obs: dict, unit_action: dict, predictions: list[tuple[float, float, list]]) -> list[list]:
    seat = _seat(obs)
    farm = list(obs.get("farms") or [{}, {}])[seat]
    private = obs.get("private") or {}
    available = ROLE._projected_shed(obs, unit_action)
    used = sum(available.values())
    money = max(0, _int(farm.get("money")))
    hires = max(0, _int(farm.get("hires_today")))
    lands = len(farm.get("unlocked_quadrants") or [])
    market_inventory = {str(k): _int(v) for k, v in dict(((obs.get("market") or {}).get("inventory") or {})).items()}
    queued = sorted(predictions, key=lambda row: (row[0], -row[1]))
    result: list[list] = []
    for _, _, raw in queued:
        if len(result) >= 10:
            break
        order = list(raw)
        op = str(order[0])
        if op == "SELL" and len(order) >= 3:
            item = str(order[1]); quantity = min(max(0, _int(order[2])), available.get(item, 0))
            if quantity <= 0:
                continue
            order[2] = quantity; available[item] -= quantity; used -= quantity
            inv = market_inventory.get(item, 10000)
            for _ in range(quantity):
                price = ROLE._market_price(item, inv); money += price
                if price > 1: inv += 1
            market_inventory[item] = inv
        elif op == "HIRE":
            quantity = min(max(1, _int(raw[1]) if len(raw) >= 2 else 1), 10-len(result))
            for _ in range(quantity):
                cost = _fib(hires)
                if money < cost or len(result) >= 10: break
                result.append(["HIRE"]); money -= cost; hires += 1
            continue
        elif op == "BUY_LAND":
            if lands >= 4: continue
            cost = (1000, 2000, 4000)[lands-1]
            if money < cost: continue
            money -= cost; lands += 1
        elif op == "BUY_SEED" and len(order) >= 3 and str(order[1]) in SEED_COST:
            item = str(order[1]); quantity = min(max(0, _int(order[2])), money//SEED_COST[item])
            if quantity <= 0: continue
            order[2] = quantity; money -= quantity*SEED_COST[item]
        elif op == "BUY_ANIMAL" and len(order) >= 3 and str(order[1]) in ANIMAL_COST:
            item = str(order[1]); quantity = min(max(0, _int(order[2])), money//ANIMAL_COST[item], max(0, 100-used))
            if quantity <= 0: continue
            order[2] = quantity; money -= quantity*ANIMAL_COST[item]; used += quantity
        elif op == "BUY_PRODUCT" and len(order) >= 3 and str(order[1]) in ROLE.MARKET_PARAMS:
            item = str(order[1]); wanted = min(max(0, _int(order[2])), max(0, 100-used)); inv = market_inventory.get(item, 10000); quantity = 0
            while quantity < wanted:
                price = ROLE._market_price(item, inv-1)
                if money < price: break
                money -= price; inv -= 1; quantity += 1; used += 1
            if quantity <= 0: continue
            order[2] = quantity; market_inventory[item] = inv
        else:
            continue
        result.append(order)
    return result[:10]


def agent(obs, configuration=None):
    seat = _seat(obs)
    day, hour = _int(obs.get("day")), _int(obs.get("hour"))
    step = day*24 + hour
    state = STATE[seat]
    if step == 0 or step <= _int(state.get("last_step", -1)):
        state.clear()
    previous = state.get("previous")
    unit = ROLE.agent(obs, configuration)
    unit["market"] = _safe_queue(obs, unit, _raw_predictions(obs, previous))
    unit = ROLE._room_guard(obs, unit, step)
    unit = ROLE._terminal_liquidate(obs, unit, step)
    unit = ROLE._rank_sales(obs, unit)
    unit = ROLE._sell_bubble(unit)
    state["previous"] = obs
    state["last_step"] = step
    return unit


def model_status() -> dict:
    return {"kind": "research_top20_structured_market_hmoe", "strategy_parent": None,
            "unit_tape": False, "market_tape": False, "step_lookup": False,
            "future_features": False, "teacher_count": MODEL["teacher_count"],
            "promotable": False, "router": "current_state_event_tree",
            "experts": sorted(MODEL["models"])}
