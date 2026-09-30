#!/usr/bin/env python3
"""V124 独立运行代理：自身 Router、合同、任务规划、执行与市场闭环。"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import joblib
import numpy as np


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from contract import ANIMALS, CENTERS, CROPS, PRODUCTS, state_features  # noqa: E402
from train_hmoe import EXPERT_DOMAINS, predict_hmoe  # noqa: E402


VERSION = "V124-R0"
ENGINE = "1.32.7"
MODEL_PATH = HERE / "training" / "contract_hmoe.joblib"
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
BASE_PRICE = {
    "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
    "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100,
}
LAND_COST = (1000, 2000, 4000)
CROP_FIRST_DAYS = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
PASS = ["PASS"]


def integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_step(grid: list, source: tuple[int, int], target: tuple[int, int], actor: int) -> list[str]:
    if source == target:
        return PASS.copy()
    directions = (("EAST", 1, 0), ("SOUTH", 0, 1), ("WEST", -1, 0), ("NORTH", 0, -1))
    if actor % 2:
        directions = (("SOUTH", 0, 1), ("WEST", -1, 0), ("NORTH", 0, -1), ("EAST", 1, 0))
    queue = deque([(source, None)])
    visited = {source}
    while queue:
        (x, y), first = queue.popleft()
        for verb, dx, dy in directions:
            nx, ny = x + dx, y + dy
            if ny < 0 or nx < 0 or ny >= len(grid) or nx >= len(grid[ny]):
                continue
            position = (nx, ny)
            if position in visited or grid[ny][nx] == "LOCKED":
                continue
            next_first = first or verb
            if position == target:
                return [next_first]
            visited.add(position)
            queue.append((position, next_first))
    return PASS.copy()


def nearest_center(position: tuple[int, int]) -> tuple[int, int]:
    return min(CENTERS, key=lambda target: (distance(position, target), target))


def animal_kind(tile: Any) -> str | None:
    if not isinstance(tile, Mapping):
        return None
    raw = tile.get("animal")
    if isinstance(raw, Mapping):
        raw = raw.get("kind")
    return str(raw) if raw in ANIMALS else None


def inventory_total(inventory: Mapping[str, Any]) -> int:
    return sum(max(0, integer(value)) for value in inventory.values())


@dataclass
class SeatRuntime:
    day: int = -1
    previous_day_observation: dict | None = None
    contract: dict[str, float] = field(default_factory=dict)
    route: dict[str, float] = field(default_factory=dict)
    executed: Counter = field(default_factory=Counter)
    calls: int = 0
    contract_id: str = ""


class V124Policy:
    """不调用任何旧策略；所有动作由 V124 合同和本地任务图生成。"""

    def __init__(self) -> None:
        artifact = joblib.load(MODEL_PATH)
        if artifact.get("schema") != "kaggriculture-v124-contract-hmoe-model-v1":
            raise ValueError("V124 模型 schema 不匹配")
        self.artifact = artifact
        self.model = artifact["model"]
        self.feature_names = list(artifact["feature_names"])
        self.target_names = list(artifact["target_names"])
        self.seats = {0: SeatRuntime(), 1: SeatRuntime()}

    def _predict_day_contract(self, observation: dict, runtime: SeatRuntime) -> None:
        features = state_features(observation, runtime.previous_day_observation)
        x = np.asarray([[float(features.get(name, 0.0)) for name in self.feature_names]])
        prediction = predict_hmoe(self.model, x, self.target_names)[0]
        contract = {name: float(value) for name, value in zip(self.target_names, prediction, strict=True)}
        raw_route = np.maximum(1e-9, np.asarray(self.model["router"].predict(x))[0])
        raw_route /= raw_route.sum()
        route = {name: float(value) for name, value in zip(EXPERT_DOMAINS, raw_route, strict=True)}
        payload = json.dumps({"day": integer(observation.get("day")), "route": route, "contract": contract}, sort_keys=True)
        runtime.contract = contract
        runtime.route = route
        runtime.executed = Counter()
        runtime.contract_id = hashlib.sha256(payload.encode()).hexdigest()[:16]
        runtime.previous_day_observation = dict(observation)
        runtime.day = integer(observation.get("day"))

    @staticmethod
    def _state(observation: dict) -> dict:
        seat = 1 if integer(observation.get("player")) == 1 else 0
        farms = list(observation.get("farms", []) or [{}, {}])
        while len(farms) < 2:
            farms.append({})
        farm = farms[seat] or {}
        private = observation.get("private", {}) or {}
        positions = [farm.get("farmer", [4, 4]), *(farm.get("hands", []) or [])]
        inventories = list(private.get("inventories", []) or [])
        while len(inventories) < len(positions):
            inventories.append({})
        return {
            "seat": seat,
            "step": integer(observation.get("step"), integer(observation.get("day")) * 24 + integer(observation.get("hour"))),
            "day": integer(observation.get("day")),
            "hour": integer(observation.get("hour")),
            "money": float(farm.get("money", 0) or 0),
            "grid": list(farm.get("tiles", []) or []),
            "positions": [(integer(p[0], 4), integer(p[1], 4)) for p in positions],
            "inventories": [dict(value or {}) for value in inventories[:len(positions)]],
            "shed": {str(k): max(0, integer(v)) for k, v in (private.get("shed", {}) or {}).items()},
            "seeds": {str(k): max(0, integer(v)) for k, v in (private.get("seeds", {}) or {}).items()},
            "market_prices": {str(k): max(1, integer(v, 1)) for k, v in ((observation.get("market", {}) or {}).get("prices", {}) or {}).items()},
            "market_inventory": {str(k): integer(v, 10000) for k, v in ((observation.get("market", {}) or {}).get("inventory", {}) or {}).items()},
            "hires_today": integer(farm.get("hires_today")),
            "lands": max(1, len(farm.get("unlocked_quadrants", []) or [])),
        }

    @staticmethod
    def _quota(contract: dict[str, float], key: str, cap: int) -> int:
        return max(0, min(cap, int(round(float(contract.get(key, 0.0))))))

    def _plant_plan(self, state: dict, runtime: SeatRuntime) -> Counter:
        result: Counter = Counter()
        for crop in CROPS:
            quota = self._quota(runtime.contract, f"plant_{crop}", 24)
            result[crop] = max(0, quota - runtime.executed[f"plant_{crop}"])
        # 模型输出极低时只维持一个小麦现金闭环；这是显式安全下限，不读取教师或未来信息。
        if state["day"] < 25 and sum(result.values()) == 0:
            result["WHEAT"] = 2
        return result

    def _tasks(self, state: dict, runtime: SeatRuntime) -> list[tuple[int, int, int, list[Any], str]]:
        tasks: list[tuple[int, int, int, list[Any], str]] = []
        plant_plan = self._plant_plan(state, runtime)
        empty: list[tuple[int, int]] = []
        for y, row in enumerate(state["grid"]):
            for x, tile in enumerate(row):
                if tile is None:
                    empty.append((x, y))
                    continue
                if not isinstance(tile, Mapping):
                    continue
                kind = str(tile.get("kind") or "")
                animal = animal_kind(tile)
                if kind == "WEED":
                    tasks.append((0, x, y, ["DIG"], "dig_weed"))
                    continue
                if kind == "PLANT":
                    crop = str(tile.get("crop") or "")
                    mature = state["day"] - integer(tile.get("planted_day")) >= CROP_FIRST_DAYS.get(crop, 30)
                    if integer(tile.get("yield_units")) > 0 and mature:
                        tasks.append((0, x, y, ["HARVEST"], f"harvest_{crop}"))
                    elif 0 <= integer(tile.get("max_lifespan_step"), -1) <= state["step"]:
                        tasks.append((0, x, y, ["DIG"], f"dig_expired_{crop}"))
                    elif not bool(tile.get("watered_today")):
                        tasks.append((1, x, y, ["WATER"], f"water_{crop}"))
                    elif crop in {"TOMATO", "STRAWBERRY", "MELON"} and integer(tile.get("fertilized_until_day"), -1) < state["day"]:
                        tasks.append((2, x, y, ["FERTILIZE"], f"fertilize_{crop}"))
                elif kind in {"PASTURE", "COOP"} and animal:
                    if integer(tile.get("yield_units")) > 0:
                        tasks.append((0, x, y, ["HARVEST"], f"animal_harvest_{animal}"))
                    elif not bool(tile.get("cared_today")):
                        tasks.append((1, x, y, ["CARE"], f"care_{animal}"))
                    elif bool(tile.get("fertilizer_available")):
                        tasks.append((2, x, y, ["COLLECT_FERTILIZER"], "collect_fertilizer"))
                    elif not bool(tile.get("fed_today")):
                        tasks.append((2, x, y, ["FEED"], f"feed_{animal}"))
        empty.sort(key=lambda pos: (distance(pos, nearest_center(pos)), pos[1], pos[0]))
        cursor = 0
        crop_order = sorted(CROPS, key=lambda crop: (-plant_plan[crop], CROPS.index(crop)))
        for crop in crop_order:
            available = max(0, state["seeds"].get(crop, 0))
            count = min(plant_plan[crop], available, max(0, len(empty) - cursor))
            for x, y in empty[cursor:cursor + count]:
                tasks.append((3, x, y, ["PLANT", crop], f"plant_{crop}"))
            cursor += count
        return tasks

    def _unit_actions(self, state: dict, runtime: SeatRuntime) -> list[list[Any]]:
        tasks = self._tasks(state, runtime)
        claimed: set[tuple[int, int, str]] = set()
        actions: list[list[Any]] = []
        terminal = state["step"] >= 708
        shed = state["shed"]
        for actor, (position, inventory) in enumerate(zip(state["positions"], state["inventories"], strict=True)):
            carried_animals = [animal for animal in ANIMALS if integer(inventory.get(animal)) > 0]
            carried_products = sum(integer(inventory.get(item)) for item in PRODUCTS)
            tile = state["grid"][position[1]][position[0]]
            at_center = position in CENTERS

            if terminal:
                action = ["DROP"] if at_center and inventory_total(inventory) else path_step(state["grid"], position, nearest_center(position), actor)
                actions.append(action)
                runtime.executed[f"unit_{action[0]}"] += 1
                continue
            remaining_today = 23 - state["hour"]
            if carried_products > 0 and at_center:
                actions.append(["DROP"])
                runtime.executed["unit_DROP"] += 1
                continue
            if actor > 0 and carried_products > 0 and remaining_today <= distance(position, nearest_center(position)) + 1:
                action = path_step(state["grid"], position, nearest_center(position), actor)
                actions.append(action)
                runtime.executed[f"unit_{action[0]}"] += 1
                continue
            if carried_animals:
                animal = carried_animals[0]
                required = "COOP" if animal == "GOOSE" else "PASTURE"
                if isinstance(tile, Mapping) and tile.get("kind") == required and not animal_kind(tile):
                    action = ["PLACE", animal]
                elif tile is None:
                    action = [f"BUILD_{required}"]
                else:
                    candidates = [
                        (x, y) for y, row in enumerate(state["grid"]) for x, value in enumerate(row)
                        if value is None
                    ]
                    target = min(candidates, key=lambda p: (distance(position, p), p)) if candidates else nearest_center(position)
                    action = path_step(state["grid"], position, target, actor)
                actions.append(action)
                runtime.executed[f"unit_{action[0]}"] += 1
                continue
            if at_center and shed:
                animal = next((name for name in ANIMALS if shed.get(name, 0) > 0), None)
                if animal:
                    actions.append(["PICKUP", animal, 1])
                    runtime.executed["unit_PICKUP"] += 1
                    continue
            if carried_products >= 5 or (state["hour"] >= 20 and carried_products > 0):
                action = ["DROP"] if at_center else path_step(state["grid"], position, nearest_center(position), actor)
                actions.append(action)
                runtime.executed[f"unit_{action[0]}"] += 1
                continue

            candidates = []
            for priority, x, y, action, key in tasks:
                claim = (x, y, key)
                if claim in claimed:
                    continue
                if action[0] == "FEED" and integer(inventory.get("WHEAT")) <= 0:
                    continue
                if action[0] == "FERTILIZE" and integer(inventory.get("FERTILIZER")) <= 0:
                    continue
                if (
                    actor > 0 and action[0] == "HARVEST"
                    and distance(position, (x, y)) + distance((x, y), nearest_center((x, y))) + 1 > remaining_today
                ):
                    continue
                candidates.append((priority, distance(position, (x, y)), y, x, action, key))
            if candidates:
                _, _, y, x, task_action, key = min(candidates)
                claimed.add((x, y, key))
                action = task_action if position == (x, y) else path_step(state["grid"], position, (x, y), actor)
            elif at_center and shed.get("WHEAT", 0) > 0 and any(task[3][0] == "FEED" for task in tasks):
                action = ["PICKUP", "WHEAT", min(5, shed["WHEAT"])]
            elif at_center and shed.get("FERTILIZER", 0) > 0 and any(task[3][0] == "FERTILIZE" for task in tasks):
                action = ["PICKUP", "FERTILIZER", min(3, shed["FERTILIZER"])]
            elif carried_products > 0:
                action = ["DROP"] if at_center else path_step(state["grid"], position, nearest_center(position), actor)
            else:
                action = PASS.copy()
            actions.append(action)
            runtime.executed[f"unit_{action[0]}"] += 1
            if action[0] == "PLANT" and len(action) > 1:
                runtime.executed[f"plant_{action[1]}"] += 1
        return actions

    def _market_actions(self, state: dict, runtime: SeatRuntime) -> list[list[Any]]:
        contract = runtime.contract
        orders: list[list[Any]] = []
        money = state["money"]
        terminal = state["day"] == 29 or state["step"] >= 696
        animal_count = sum(
            1 for row in state["grid"] for tile in row if animal_kind(tile)
        )
        reserves = {
            "WHEAT": min(18, animal_count * 2),
            "FERTILIZER": 3 if any(
                isinstance(tile, Mapping) and tile.get("crop") in {"TOMATO", "STRAWBERRY", "MELON"}
                for row in state["grid"] for tile in row
            ) else 0,
        }
        # 已入仓产品先按模型日合同出售；终局清仓。单条订单合并数量以控制十槽限制。
        ranked_products = sorted(PRODUCTS, key=lambda item: (-state["market_prices"].get(item, BASE_PRICE[item]), PRODUCTS.index(item)))
        for item in ranked_products:
            raw_have = state["shed"].get(item, 0)
            have = raw_have if terminal else max(0, raw_have - reserves.get(item, 0))
            quota = have if terminal else self._quota(contract, f"sell_{item}", 36) - runtime.executed[f"sell_{item}"]
            quantity = min(have, max(0, quota))
            if quantity > 0 and len(orders) < 10:
                orders.append(["SELL", item, quantity])
                runtime.executed[f"sell_{item}"] += quantity
                money += quantity * state["market_prices"].get(item, BASE_PRICE[item])
        if terminal:
            return orders[:10]

        reserve = max(50.0, min(500.0, 0.05 * money))
        budget = max(0.0, money - reserve)

        hire_quota = self._quota(contract, "market_HIRE", 8)
        hire_gap = max(0, hire_quota - runtime.executed["market_HIRE"])
        while hire_gap and len(state["positions"]) + runtime.executed["market_HIRE"] < 12 and len(orders) < 10:
            cost = 1
            for _ in range(state["hires_today"] + runtime.executed["market_HIRE"]):
                cost = max(1, int(round(cost * 1.618)))
            if cost > budget:
                break
            orders.append(["HIRE"])
            budget -= cost
            runtime.executed["market_HIRE"] += 1
            hire_gap -= 1

        land_quota = self._quota(contract, "market_BUY_LAND", 1)
        if land_quota > runtime.executed["market_BUY_LAND"] and state["lands"] < 4 and len(orders) < 10:
            cost = LAND_COST[min(state["lands"] - 1, len(LAND_COST) - 1)]
            if cost <= budget and state["day"] <= 18:
                orders.append(["BUY_LAND"])
                budget -= cost
                runtime.executed["market_BUY_LAND"] += 1

        plant_plan = self._plant_plan(state, runtime)
        for crop in sorted(CROPS, key=lambda item: (-plant_plan[item], CROPS.index(item))):
            learned = self._quota(contract, f"market_BUY_SEED_{crop}", 24)
            need = max(learned, plant_plan[crop] - state["seeds"].get(crop, 0))
            gap = max(0, need - runtime.executed[f"buy_seed_{crop}"])
            quantity = min(24, gap, int(budget // SEED_COST[crop]))
            if quantity > 0 and len(orders) < 10:
                orders.append(["BUY_SEED", crop, quantity])
                budget -= quantity * SEED_COST[crop]
                runtime.executed[f"buy_seed_{crop}"] += quantity

        wheat_learned = max(
            self._quota(contract, "market_BUY_PRODUCT_WHEAT", 18),
            self._quota(contract, "market_BUY_PRODUCT", 18),
            reserves["WHEAT"] - state["shed"].get("WHEAT", 0),
        )
        wheat_gap = max(0, wheat_learned - state["shed"].get("WHEAT", 0) - runtime.executed["buy_product_WHEAT"])
        wheat_quantity = min(18, wheat_gap, int(budget // state["market_prices"].get("WHEAT", BASE_PRICE["WHEAT"])))
        if wheat_quantity > 0 and len(orders) < 10:
            orders.append(["BUY_PRODUCT", "WHEAT", wheat_quantity])
            budget -= wheat_quantity * state["market_prices"].get("WHEAT", BASE_PRICE["WHEAT"])
            runtime.executed["buy_product_WHEAT"] += wheat_quantity

        for animal in ANIMALS:
            learned = self._quota(contract, f"market_BUY_ANIMAL_{animal}", 4)
            gap = max(0, learned - runtime.executed[f"buy_animal_{animal}"])
            quantity = min(2, gap, int(budget // ANIMAL_COST[animal]))
            if quantity > 0 and len(orders) < 10:
                orders.append(["BUY_ANIMAL", animal, quantity])
                budget -= quantity * ANIMAL_COST[animal]
                runtime.executed[f"buy_animal_{animal}"] += quantity
        return orders[:10]

    def act(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        obs = dict(observation)
        seat = 1 if integer(obs.get("player")) == 1 else 0
        step = integer(obs.get("step"), integer(obs.get("day")) * 24 + integer(obs.get("hour")))
        if step == 0:
            self.seats[seat] = SeatRuntime()
        runtime = self.seats[seat]
        if runtime.day != integer(obs.get("day")):
            self._predict_day_contract(obs, runtime)
        state = self._state(obs)
        units = self._unit_actions(state, runtime)
        market = self._market_actions(state, runtime)
        runtime.calls += 1
        return {
            "farmer": units[0] if units else PASS.copy(),
            "hands": units[1:] if len(units) > 1 else [],
            "market": market,
        }

    def status(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "engine": ENGINE,
            "architecture": "INDEPENDENT_PROTOCOL_FIRST_CONTRACT_HMOE",
            "strategy_parent": None,
            "feature_count": len(self.feature_names),
            "target_count": len(self.target_names),
            "expert_domains": list(EXPERT_DOMAINS),
            "seats": {
                str(seat): {
                    "calls": runtime.calls,
                    "day": runtime.day,
                    "contract_id": runtime.contract_id,
                    "route": runtime.route,
                }
                for seat, runtime in self.seats.items()
            },
        }


_POLICY = V124Policy()


def agent(observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
    return _POLICY.act(observation, configuration)


def model_status() -> dict[str, Any]:
    return _POLICY.status()
