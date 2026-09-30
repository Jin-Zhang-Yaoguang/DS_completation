"""Research agent: role-option unit policy plus a causal resource-rule market HMoE.

The market path uses only current observations and daily semantic task demand.  It
does not read the replay market queue, a future action, or V120 code.
"""

from __future__ import annotations

from collections import Counter
import os
from typing import Any, Mapping

# Keep the unit executor, but discard its diagnostic market result below.
os.environ["ROLE_CAUSAL_COMPILER"] = "0"
os.environ["ROLE_PREEMPT_ITEMS"] = "none"
os.environ["ROLE_PREBUY_HORIZON"] = "0"
os.environ["ROLE_QUEUE_EXPERT"] = "0"

import role_option_agent as ROLE


STATE = {0: {}, 1: {}}
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
SELLABLE = ("WOOL", "MILK", "STRAWBERRY", "MELON", "EGG", "TOMATO", "CARROT", "FERTILIZER", "WHEAT")


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _seat(obs: Mapping[str, Any]) -> int:
    return 1 if _int(obs.get("player")) == 1 else 0


def _fib(index: int) -> int:
    a, b = 0, 1
    for _ in range(max(0, index)):
        a, b = b, a + b
    return a


def _daily_needs(day: int) -> tuple[Counter, Counter, Counter, int]:
    """Compress semantic option leaves into resource targets, not action timing."""
    row = ROLE.CONTRACT["days"].get(str(day), {})
    seeds: Counter = Counter()
    animals: Counter = Counter()
    inputs: Counter = Counter()
    for queue in (row.get("actors") or {}).values():
        for task in queue:
            order = list(task.get("order") or [])
            if not order:
                continue
            if order[0] == "PLANT" and len(order) >= 2:
                seeds[str(order[1])] += 1
            elif order[0] == "PICKUP" and len(order) >= 3 and str(order[1]) in ANIMAL_COST:
                animals[str(order[1])] += 1
            elif order[0] == "PICKUP" and len(order) >= 3 and str(order[1]) in {"WHEAT", "FERTILIZER"}:
                inputs[str(order[1])] += max(0, _int(order[2]))
    workers = max(0, len((row.get("actors") or {})) - 1)
    return seeds, animals, inputs, workers


def _simulate_sell(obs: Mapping[str, Any], item: str, quantity: int) -> int:
    inventory = _int(((obs.get("market") or {}).get("inventory") or {}).get(item))
    total = 0
    for _ in range(max(0, quantity)):
        price = ROLE._market_price(item, inventory)
        total += price
        if price > 1:
            inventory += 1
    return total


def _market(obs: Mapping[str, Any], unit_action: Mapping[str, Any], state: dict) -> list[list]:
    seat = _seat(obs)
    day, hour = _int(obs.get("day")), _int(obs.get("hour"))
    step = day * 24 + hour
    farm = list(obs.get("farms") or [{}, {}])[seat]
    private = obs.get("private") or {}
    shed = {str(k): max(0, _int(v)) for k, v in dict(private.get("shed") or {}).items()}
    seeds = {str(k): max(0, _int(v)) for k, v in dict(private.get("seeds") or {}).items()}
    carried = Counter()
    for inventory in private.get("inventories") or []:
        carried.update({str(k): max(0, _int(v)) for k, v in dict(inventory or {}).items()})
    money = max(0, _int(farm.get("money")))
    hires = max(0, _int(farm.get("hires_today")))
    lands = len(farm.get("unlocked_quadrants") or [])
    daily_seed, daily_animal, daily_input, target_hands = _daily_needs(day)
    initial = state.setdefault("initial", {"seed": dict(seeds), "stock": dict(shed), "carried": dict(carried)})
    bought = state.setdefault("bought", {"seed": {}, "animal": {}, "input": {}})
    orders: list[list] = []

    # Sales expert: sell available output promptly, retaining only today's feed
    # and fertilizer reserve.  Premium products lead the queue because their
    # supply impact is steeper in the Top20 episodes.
    feed_reserve = min(12, max(0, sum(1 for queue in (ROLE.CONTRACT["days"].get(str(day), {}).get("actors") or {}).values()
                                      for task in queue if (task.get("order") or [""])[0] == "FEED")))
    fert_reserve = min(6, max(0, sum(1 for queue in (ROLE.CONTRACT["days"].get(str(day), {}).get("actors") or {}).values()
                                    for task in queue if (task.get("order") or [""])[0] == "FERTILIZE")))
    reserve = {"WHEAT": feed_reserve, "FERTILIZER": fert_reserve}
    for item in SELLABLE:
        quantity = max(0, shed.get(item, 0) - reserve.get(item, 0))
        if quantity <= 0 or len(orders) >= 10:
            continue
        orders.append(["SELL", item, quantity])
        money += _simulate_sell(obs, item, quantity)
        shed[item] -= quantity

    # Expansion expert runs before labor because the ten-slot market queue is
    # often saturated at day open; delaying land by one day destroys the role
    # graph's lower-quadrant tasks.
    if len(orders) < 10 and lands < 4:
        needed_land = 1
        row = ROLE.CONTRACT["days"].get(str(day), {})
        for queue in (row.get("actors") or {}).values():
            for task in queue:
                x, y = map(int, task.get("target") or [0, 0])
                needed_land = max(needed_land, 1 + int(x >= 5) + 2 * int(y >= 5))
        costs = (1000, 2000, 4000)
        if needed_land > lands and money >= costs[lands - 1]:
            orders.append(["BUY_LAND"])
            money -= costs[lands - 1]
            lands += 1

    # Labor expert: daily workers are bought from the task graph's actor width.
    # Repeat at hour 0/1 so a temporarily unaffordable hire can recover after a
    # preceding sale without consulting a stored turn action.
    if hour <= 1:
        missing = max(0, target_hands - len(farm.get("hands") or []))
        while missing > 0 and len(orders) < 10:
            cost = _fib(hires)
            if money < cost:
                break
            orders.append(["HIRE"])
            money -= cost
            hires += 1
            missing -= 1

    # Seed expert: satisfy the remaining daily semantic plant leaves.  A small
    # carry buffer prevents one failed/late task from starving the next day.
    for crop in SEED_COST:
        if len(orders) >= 10:
            break
        desired = max(0, daily_seed.get(crop, 0) - _int(initial["seed"].get(crop)))
        quantity = max(0, min(24, desired - _int(bought["seed"].get(crop))))
        quantity = min(quantity, money // SEED_COST[crop])
        if quantity > 0:
            orders.append(["BUY_SEED", crop, quantity])
            money -= quantity * SEED_COST[crop]
            seeds[crop] = seeds.get(crop, 0) + quantity
            bought["seed"][crop] = _int(bought["seed"].get(crop)) + quantity

    # Livestock expert: outstanding place leaves are backed by actual stock;
    # center placement itself remains controlled by the role-option layer.
    used = sum(shed.values()) + sum(carried.values())
    for animal in ANIMAL_COST:
        if len(orders) >= 10:
            break
        starting = _int(initial["stock"].get(animal)) + _int(initial["carried"].get(animal))
        desired = max(0, daily_animal.get(animal, 0) - starting)
        quantity = min(max(0, desired - _int(bought["animal"].get(animal))), money // ANIMAL_COST[animal], max(0, 100 - used))
        if quantity > 0:
            orders.append(["BUY_ANIMAL", animal, quantity])
            money -= quantity * ANIMAL_COST[animal]
            used += quantity
            bought["animal"][animal] = _int(bought["animal"].get(animal)) + quantity

    # Input expert: only buy when today's graph has a concrete unsatisfied
    # consumption contract.  Purchases are state bounded, never time copied.
    for item, reserve_floor in (("WHEAT", feed_reserve), ("FERTILIZER", fert_reserve)):
        if len(orders) >= 10:
            break
        starting = _int(initial["stock"].get(item)) + _int(initial["carried"].get(item))
        desired = max(reserve_floor, daily_input.get(item, 0))
        purchase_budget = max(0, desired - starting)
        quantity = max(0, min(30, purchase_budget - _int(bought["input"].get(item))))
        if quantity <= 0:
            continue
        price = max(1, _int(((obs.get("market") or {}).get("prices") or {}).get(item)))
        quantity = min(quantity, money // price, max(0, 100 - used))
        if quantity > 0:
            orders.append(["BUY_PRODUCT", item, quantity])
            money -= quantity * price
            used += quantity
            bought["input"][item] = _int(bought["input"].get(item)) + quantity

    action = {**unit_action, "market": orders[:10]}
    action = ROLE._room_guard(obs, action, step)
    action = ROLE._terminal_liquidate(obs, action, step)
    action = ROLE._rank_sales(obs, action)
    action = ROLE._sell_bubble(action)
    return [list(order) for order in action.get("market") or []]


def agent(obs, configuration=None):
    seat = _seat(obs)
    day, hour = _int(obs.get("day")), _int(obs.get("hour"))
    step = day * 24 + hour
    state = STATE[seat]
    if step == 0 or step <= _int(state.get("last_step", -1)):
        state.clear()
    if state.get("day") != day:
        state.clear()
        state["day"] = day
    state["last_step"] = step
    unit = ROLE.agent(obs, configuration)
    unit["market"] = _market(obs, unit, state)
    return unit


def model_status() -> dict:
    return {
        "kind": "research_top20_role_causal_market_hmoe",
        "strategy_parent": None,
        "unit_tape": False,
        "market_tape": False,
        "future_features": False,
        "promotable": False,
        "experts": ["sales", "labor", "expansion", "seed", "livestock", "input", "terminal"],
    }
