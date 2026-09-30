#!/usr/bin/env python3
"""Executable day-3 town-shop router with a state-aware route executor.

The route is selected once.  Seed, animal, land, labour and sell orders remain
from the same replay-derived route tail; individual subsystems are never mixed.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
DATA = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
BASE = MODEL / "v1_adaptive_market" / "main.py"
ROUTER_STEP = 72
PREFIX = ("tyz123456", 99609968)
DEFAULT = ("tyz123456", 99609968)
YARN = ("Kronki", 99596430)
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}


def _route(team: str, episode: int) -> list[dict]:
    replay = json.loads((DATA / f"{episode}.json").read_text())
    seat = replay["info"]["TeamNames"].index(team)
    return [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]


_PREFIX_ACTIONS = _route(*PREFIX)
_DEFAULT_ACTIONS = _PREFIX_ACTIONS[:ROUTER_STEP] + _route(*DEFAULT)[ROUTER_STEP:]
_YARN_ACTIONS = _PREFIX_ACTIONS[:ROUTER_STEP] + _route(*YARN)[ROUTER_STEP:]


def _fresh_base():
    name = f"portfolio_repair_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, BASE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _step(obs) -> int:
    if isinstance(obs, dict) and obs.get("step") is not None:
        return int(obs.get("step") or 0)
    return int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)


def _seat(obs) -> int:
    return 1 if int(obs.get("player", 0) or 0) == 1 else 0


def _fail_closed_units(obs, action):
    """Turn engine-rejected unit orders into explicit PASS without changing state."""
    action = copy.deepcopy(action)
    seat = _seat(obs)
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *farm["hands"]]
    inventories = obs["private"]["inventories"]
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    seed_demand = {}
    for order in orders:
        if len(order) >= 2 and order[0] == "PLANT":
            seed_demand[order[1]] = seed_demand.get(order[1], 0) + 1
    size = len(farm["tiles"])
    access = {(size // 2 - 1, size // 2 - 1), (size // 2, size // 2 - 1), (size // 2 - 1, size // 2), (size // 2, size // 2)}
    for index, (position, order) in enumerate(zip(positions, orders)):
        op = order[0] if order else "PASS"
        x, y = map(int, position)
        tile = farm["tiles"][y][x]
        inv = inventories[index] if index < len(inventories) else {}
        valid = True
        if op in _MOVES:
            dx, dy = _MOVES[op]
            valid = 0 <= x + dx < size and 0 <= y + dy < size
        elif op == "PLANT":
            valid = tile is None and seed_demand[order[1]] <= int(obs["private"]["seeds"].get(order[1], 0) or 0)
        elif op == "WATER":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
        elif op == "HARVEST":
            valid = isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
        elif op == "FERTILIZE":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inv.get("FERTILIZER", 0) or 0) > 0
        elif op == "DIG":
            valid = tile is not None and tile != "LOCKED" and not (isinstance(tile, dict) and tile.get("animal"))
        elif op in {"BUILD_COOP", "BUILD_PASTURE"}:
            valid = tile is None
        elif op == "FEED":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inv.get("WHEAT", 0) or 0) > 0
        elif op == "CARE":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
        elif op == "COLLECT_FERTILIZER":
            valid = isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
        elif op == "PICKUP":
            valid = (x, y) in access and len(order) >= 3 and int(obs["private"]["shed"].get(order[1], 0) or 0) > 0
        elif op == "DROP":
            valid = (x, y) in access and sum(int(v or 0) for v in inv.values()) > 0
        elif op == "PLACE":
            valid = len(order) >= 2 and int(inv.get(order[1], 0) or 0) > 0
        if not valid:
            orders[index] = ["PASS"]
    action["farmer"] = orders[0]
    action["hands"] = orders[1:]
    return action


def _prebuy_next_step_seeds(obs, action, actions, step):
    """Finance repair for a scheduled next-turn plant after a partial seed fill."""
    if step + 1 >= len(actions):
        return action
    action = copy.deepcopy(action)
    future = actions[step + 1] or {}
    needed = {}
    for order in [future.get("farmer") or ["PASS"], *(future.get("hands") or [])]:
        if len(order) >= 2 and order[0] == "PLANT":
            needed[order[1]] = needed.get(order[1], 0) + 1
    if not needed:
        return action
    market = action.get("market") or []
    planned = {}
    for order in market:
        if len(order) >= 3 and order[0] == "BUY_SEED":
            planned[order[1]] = planned.get(order[1], 0) + max(0, int(order[2] or 0))
    seeds = obs["private"]["seeds"]
    money = int(obs["farms"][_seat(obs)]["money"] or 0)
    for item, demand in needed.items():
        shortage = max(0, demand - int(seeds.get(item, 0) or 0) - planned.get(item, 0))
        affordable = money // _SEED_COST[item]
        quantity = min(shortage, affordable)
        if quantity > 0 and len(market) < 10:
            market.append(["BUY_SEED", item, quantity])
            money -= quantity * _SEED_COST[item]
    action["market"] = market
    return action


def _fib(index):
    a, b = 0, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _cap_fixed_purchases(obs, action, base):
    """Cap fixed-price buys to a guaranteed executable quantity.

    Planned own sales are credited at a conservative price after assuming the
    opponent dumps its entire 100-unit shed into the same product first.  This
    preserves every unit that is finance-safe under any legal opponent action.
    """
    action = copy.deepcopy(action)
    seat = _seat(obs)
    farm = obs["farms"][seat]
    money = int(farm["money"] or 0)
    shed = {key: int(value or 0) for key, value in obs["private"]["shed"].items()}
    inventory = {key: int(value or 0) for key, value in obs["market"]["inventory"].items()}
    own_sales = {}
    hires = int(farm.get("hires_today", 0) or 0)
    quadrants = len(farm["unlocked_quadrants"])
    room = max(0, 100 - sum(shed.values()))
    for order in action.get("market") or []:
        if not order:
            continue
        op = order[0]
        if op == "SELL" and len(order) >= 3:
            item = order[1]
            units = min(max(0, int(order[2] or 0)), shed.get(item, 0))
            start = inventory.get(item, 10000) + 100 + own_sales.get(item, 0)
            for offset in range(units):
                price = int(base._market_price(item, start + offset))
                money += price
                if price > 1:
                    own_sales[item] = own_sales.get(item, 0) + 1
            shed[item] = max(0, shed.get(item, 0) - units)
            room += units
        elif op == "HIRE":
            cost = _fib(hires)
            if money >= cost:
                money -= cost
                hires += 1
        elif op == "BUY_LAND":
            extra = quadrants - 1
            cost = (1000, 2000, 4000)[extra] if 0 <= extra < 3 else 10**18
            if money >= cost:
                money -= cost
                quadrants += 1
        elif op == "BUY_SEED" and len(order) >= 3 and order[1] in _SEED_COST:
            requested = max(0, int(order[2] or 0))
            executable = min(requested, money // _SEED_COST[order[1]])
            order[2] = executable
            money -= executable * _SEED_COST[order[1]]
        elif op == "BUY_ANIMAL" and len(order) >= 3 and order[1] in _ANIMAL_COST:
            requested = max(0, int(order[2] or 0))
            executable = min(requested, money // _ANIMAL_COST[order[1]], room)
            order[2] = executable
            money -= executable * _ANIMAL_COST[order[1]]
            room -= executable
    return action


def make_agent(mode: str = "router"):
    """Return a fresh policy; mode is router, single_default, or single_yarn."""
    if mode not in {"router", "single_default", "single_yarn"}:
        raise ValueError(mode)
    base = _fresh_base()
    # Keep the route's own feeding schedule; fail-closed sanitization below
    # removes the rare already-fed/no-wheat no-op without rerouting labour.
    base._V17_FEED_GUARD = False
    default = _DEFAULT_ACTIONS
    yarn = _YARN_ACTIONS
    state = {0: {"last": -1, "choice": None}, 1: {"last": -1, "choice": None}}

    def policy(obs, configuration=None):
        del configuration
        seat = _seat(obs)
        step = _step(obs)
        local = state[seat]
        if step == 0 or step < int(local["last"]):
            local.update(last=step, choice=None)
        local["last"] = step
        if mode == "single_default":
            local["choice"] = "default"
        elif mode == "single_yarn":
            local["choice"] = "yarn"
        elif local["choice"] is None and step >= ROUTER_STEP:
            shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
            local["choice"] = "yarn" if shops and shops[0] == "YARN_STORE" else "default"
        actions = yarn if local["choice"] == "yarn" else default
        # _CORE_AGENT is used only as a state executor: hand-count alignment,
        # weed recovery, legal shed transfer, executable sales, market ordering,
        # seed-surplus pruning and terminal liquidation.  It does not choose
        # the production portfolio; _ACTIONS is the selected complete route.
        base._ACTIONS = actions
        action = base._CORE_AGENT(obs)
        action = _cap_fixed_purchases(obs, action, base)
        return _fail_closed_units(obs, action)

    policy.__name__ = f"portfolio_{mode}"
    return policy


agent = make_agent("router")
