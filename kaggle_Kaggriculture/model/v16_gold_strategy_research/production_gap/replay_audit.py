"""Instrumentation for exact Kaggriculture replay counterfactuals.

This module wraps the installed official interpreter only to collect metrics.
It does not replace any game rule or action outcome.
"""

from __future__ import annotations

import copy
import hashlib
from collections import Counter
from pathlib import Path

import kaggle_environments
import kaggle_environments.envs.kaggriculture.kaggriculture as kg


REPO_ROOT = Path(__file__).resolve().parents[4]
REPLAY_ROOT = (
    REPO_ROOT
    / "kaggle_Kaggriculture/model_data/kaggriculture_episodes_index/date=2026-08-25/data"
)
OFFICIAL_RULES = (
    REPO_ROOT
    / "kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py"
)
PRODUCTS = [
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
]
CROPS = set(PRODUCTS[:5])
ANIMAL_PRODUCTS = {"EGG", "MILK", "WOOL"}

CURRENT = None
_ORIG_APPLY = kg._apply_unit_action
_ORIG_DROP = kg._drop_inventories_to_shed
_ORIG_COMMIT = kg._commit_unit
_ORIG_HIRE = kg._do_hire
_ORIG_LAND = kg._do_buy_land
_ORIG_INTERPRETER = kg.interpreter


def engine_metadata():
    installed = Path(kg.__file__).resolve()

    def sha256(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    return {
        "version": kaggle_environments.__version__,
        "official_rules": str(OFFICIAL_RULES),
        "installed_rules": str(installed),
        "official_sha256": sha256(OFFICIAL_RULES),
        "installed_sha256": sha256(installed),
    }


def interpreter_wrap(state, env):
    ctx = CURRENT
    if state and hasattr(state[0].observation, "farms") and state[0].observation.farms:
        ctx["step"] = int(state[0].observation.step)
        ctx["privmap"] = {id(state[i].observation.private): i for i in range(2)}
        ctx["farmmap"] = {id(state[0].observation.farms[i]): i for i in range(2)}
    return _ORIG_INTERPRETER(state, env)


def apply_wrap(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity=100):
    ctx = CURRENT
    pid = ctx["privmap"].get(id(private), -1)
    op = action[0] if isinstance(action, list) and action else None
    inv = private["inventories"][idx] if idx < len(private["inventories"]) else {}
    before = Counter(inv)
    total_before = sum(private["shed"].values()) + sum(
        sum(x.values()) for x in private["inventories"]
    )
    ret = _ORIG_APPLY(
        farm, private, idx, action, board_size, day, turns_per_day, shed_capacity
    )
    if pid >= 0:
        # A hire ablation can leave later recorded actions addressing a missing
        # hand. The official engine treats them as no-ops; the wrapper must not
        # index beyond the shortened inventory list.
        after = (
            Counter(private["inventories"][idx])
            if idx < len(private["inventories"])
            else Counter()
        )
        if op in ("HARVEST", "COLLECT_FERTILIZER"):
            for item, n in (after - before).items():
                if n > 0:
                    ctx["harvest"][pid][item] += n
        elif op == "FEED":
            n = before.get("WHEAT", 0) - after.get("WHEAT", 0)
            if n > 0:
                ctx["feed"][pid] += n
        if op == "DROP":
            total_after = sum(private["shed"].values()) + sum(
                sum(x.values()) for x in private["inventories"]
            )
            if total_after < total_before:
                ctx["shed_loss"][pid]["manual_drop"] += total_before - total_after
    return ret


def drop_wrap(private, capacity):
    ctx = CURRENT
    pid = ctx["privmap"].get(id(private), -1)
    if pid >= 0:
        room = max(0, capacity - sum(private["shed"].values()))
        for inv in private["inventories"]:
            for item, n in list(inv.items()):
                take = min(max(0, n), room)
                room -= take
                if n > take:
                    ctx["shed_loss"][pid][item] += n - take
    return _ORIG_DROP(private, capacity)


def commit_wrap(op, item, price, farm, private, market, shed_capacity=100):
    ctx = CURRENT
    pid = ctx["privmap"].get(id(private), -1)
    ok = _ORIG_COMMIT(op, item, price, farm, private, market, shed_capacity)
    if ok and pid >= 0:
        if op == "SELL":
            ctx["sell_qty"][pid][item] += 1
            ctx["sell_cash"][pid][item] += price
        elif op == "BUY_PRODUCT":
            ctx["spend"][pid]["buy_product"] += price
        elif op == "BUY_SEED":
            ctx["spend"][pid]["seed"] += price
        elif op == "BUY_ANIMAL":
            ctx["spend"][pid]["animal"] += price
    return ok


def hire_wrap(farm, private, board_size, mult=kg.FARM_HAND_COST_MULT):
    ctx = CURRENT
    pid = ctx["farmmap"].get(id(farm), -1)
    money, hands = farm["money"], len(farm["hands"])
    ret = _ORIG_HIRE(farm, private, board_size, mult)
    if pid >= 0 and len(farm["hands"]) > hands:
        ctx["spend"][pid]["hire"] += money - farm["money"]
    return ret


def land_wrap(farm, board_size):
    ctx = CURRENT
    pid = ctx["farmmap"].get(id(farm), -1)
    money, land = farm["money"], len(farm["unlocked_quadrants"])
    ret = _ORIG_LAND(farm, board_size)
    if pid >= 0 and len(farm["unlocked_quadrants"]) > land:
        ctx["spend"][pid]["land"] += money - farm["money"]
    return ret


kg._apply_unit_action = apply_wrap
kg._drop_inventories_to_shed = drop_wrap
kg._commit_unit = commit_wrap
kg._do_hire = hire_wrap
kg._do_buy_land = land_wrap


def new_ctx(env):
    return {
        "privmap": {id(env.state[i].observation.private): i for i in range(2)},
        "farmmap": {id(env.state[0].observation.farms[i]): i for i in range(2)},
        "harvest": [Counter(), Counter()],
        "feed": [0, 0],
        "shed_loss": [Counter(), Counter()],
        "sell_qty": [Counter(), Counter()],
        "sell_cash": [Counter(), Counter()],
        "spend": [Counter(), Counter()],
    }


class Stream:
    def __init__(self, actions):
        self.actions = actions

    def __call__(self, obs, configuration=None):
        return copy.deepcopy(self.actions[int(obs.step)])


def terminal(obs, pid):
    private, farm = obs["private"], obs["farms"][pid]
    liquid = Counter(private["shed"])
    for inv in private["inventories"]:
        liquid.update(inv)
    yields = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if "animal" in tile:
                yields[kg.ANIMALS[tile["animal"]]["product"]] += int(
                    tile.get("yield_units", 0) or 0
                )
            elif tile.get("kind") == "PLANT":
                yields[tile["crop"]] += int(tile.get("yield_units", 0) or 0)
    prices = obs["market"]["prices"]
    return {
        "liquid_value": sum(liquid[p] * prices[p] for p in PRODUCTS),
        "tile_yield_value": sum(yields[p] * prices[p] for p in PRODUCTS),
        "seed_cost_value": sum(
            int(private["seeds"].get(p, 0)) * kg.CROPS[p]["seed"] for p in CROPS
        ),
    }


def rows(env, ctx, labels):
    result = []
    for pid, label in enumerate(labels):
        daily_hands = []
        land2 = land3 = None
        for day in range(30):
            start = day * 24
            end = min((day + 1) * 24, len(env.steps) - 1)
            hands = []
            for step in range(start, end + 1):
                farm = env.steps[step][pid]["observation"]["farms"][pid]
                hands.append(len(farm["hands"]))
                if land2 is None and len(farm["unlocked_quadrants"]) >= 2:
                    land2 = day
                if land3 is None and len(farm["unlocked_quadrants"]) >= 3:
                    land3 = day
            daily_hands.append(max(hands))
        harvest = ctx["harvest"][pid]
        result.append({
            "label": label,
            "reward": float(env.state[pid].reward or 0),
            "daily_hands": daily_hands,
            "hand_days": sum(daily_hands),
            "land2": land2,
            "land3": land3,
            "harvest": dict(harvest),
            "crop_harvest": sum(harvest[x] for x in CROPS),
            "animal_harvest": sum(harvest[x] for x in ANIMAL_PRODUCTS),
            "shed_loss": dict(ctx["shed_loss"][pid]),
            "sell_cash": dict(ctx["sell_cash"][pid]),
            "sell_qty": dict(ctx["sell_qty"][pid]),
            "spend": dict(ctx["spend"][pid]),
            "terminal": terminal(env.steps[-1][pid]["observation"], pid),
        })
    return result
