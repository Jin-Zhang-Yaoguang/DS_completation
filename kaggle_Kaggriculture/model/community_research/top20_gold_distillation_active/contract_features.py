#!/usr/bin/env python3
"""V122 三层合同的共享特征与教师目标；只依赖当前/历史观测。"""

from __future__ import annotations

from collections import Counter
from typing import Any


PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "ICE_CREAM_SHOP", "FARMERS_MARKET", "YARN_STORE", "PET_CAFE", "JUICE_BAR", "SMOOTHIE_SHOP")
MOVE = {"NORTH", "SOUTH", "EAST", "WEST"}
UNIT_OPS = ("PLANT", "WATER", "FERTILIZE", "DIG", "HARVEST", "BUILD_PASTURE", "BUILD_COOP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER", "PICKUP", "DROP")
MARKET_OPS = ("HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "SELL")
CENTERS = ((4, 4), (5, 4), (4, 5), (5, 5))


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _seat(obs: dict) -> int:
    return 1 if int(obs.get("player", 0) or 0) == 1 else 0


def tile_summary(farm: dict) -> tuple[Counter, list[tuple[int, int, dict]]]:
    counts: Counter = Counter()
    cells: list[tuple[int, int, dict]] = []
    for y, row in enumerate(farm.get("tiles", []) or []):
        for x, tile in enumerate(row if isinstance(row, list) else []):
            if not isinstance(tile, dict):
                continue
            cells.append((x, y, tile))
            crop, animal, kind = tile.get("crop"), tile.get("animal"), tile.get("kind")
            if isinstance(animal, dict):
                animal = animal.get("kind")
            if crop:
                counts[f"crop_{crop}"] += 1
            if animal:
                counts[f"animal_{animal}"] += 1
                counts["animals"] += 1
                counts["center_animals"] += float(center_distance((x, y)) <= 2)
            if kind:
                counts[f"kind_{kind}"] += 1
            if crop and y % 5 <= 1:
                counts["top_two_row_crops"] += 1
    return counts, cells


def center_distance(position: list | tuple) -> int:
    x, y = int(position[0]), int(position[1])
    return min(abs(x - sx) + abs(y - sy) for sx, sy in CENTERS)


def state_features(obs: dict, previous: dict | None = None) -> dict[str, float]:
    """运行时合法特征。previous 只能是该局已经发生的观测。"""
    seat = _seat(obs)
    farms = list(obs.get("farms", []) or [{}, {}])
    while len(farms) < 2:
        farms.append({})
    own, rival = farms[seat], farms[1 - seat]
    own_counts, _ = tile_summary(own)
    rival_counts, _ = tile_summary(rival)
    private = obs.get("private", {}) or {}
    day, hour = int(obs.get("day", 0) or 0), int(obs.get("hour", 0) or 0)
    old_farms = list((previous or {}).get("farms", []) or [{}, {}])
    while len(old_farms) < 2:
        old_farms.append({})
    features: dict[str, float] = {
        "day": float(day), "hour": float(hour), "cycle_phase": float(day % 3),
        "season_step": float(day * 24 + hour),
        "season_fraction": day / 30.0,
        "own_money": number(own.get("money")), "rival_money": number(rival.get("money")),
        "money_gap": number(own.get("money")) - number(rival.get("money")),
        "own_money_change": number(own.get("money")) - number(old_farms[seat].get("money", own.get("money"))),
        "rival_money_change": number(rival.get("money")) - number(old_farms[1-seat].get("money", rival.get("money"))),
        "own_workers": 1.0 + float(len(own.get("hands", []) or [])),
        "rival_workers": 1.0 + float(len(rival.get("hands", []) or [])),
        "worker_gap": float(len(own.get("hands", []) or [])) - float(len(rival.get("hands", []) or [])),
        "own_lands": float(len(own.get("unlocked_quadrants", []) or [])),
        "rival_lands": float(len(rival.get("unlocked_quadrants", []) or [])),
        "shed_used": float(sum(max(0, int(v or 0)) for v in (private.get("shed", {}) or {}).values())),
        "own_center_animal_share": float(own_counts.get("center_animals", 0)) / max(1.0, float(own_counts.get("animals", 0))),
        "own_top_two_row_crop_share": float(own_counts.get("top_two_row_crops", 0)) / max(1.0, sum(float(own_counts.get(f"crop_{c}", 0)) for c in CROPS)),
    }
    shops = Counter(str(value) for value in (obs.get("town", {}).get("unlocked_shops", []) or []))
    for shop in SHOPS:
        features[f"shop_{shop}"] = float(shops.get(shop, 0))
    for crop in CROPS:
        features[f"own_crop_{crop}"] = float(own_counts.get(f"crop_{crop}", 0))
        features[f"rival_crop_{crop}"] = float(rival_counts.get(f"crop_{crop}", 0))
        features[f"seed_{crop}"] = number((private.get("seeds", {}) or {}).get(crop))
    for animal in ANIMALS:
        features[f"own_animal_{animal}"] = float(own_counts.get(f"animal_{animal}", 0))
        features[f"rival_animal_{animal}"] = float(rival_counts.get(f"animal_{animal}", 0))
    market, old_market = obs.get("market", {}) or {}, (previous or {}).get("market", {}) or {}
    for item in PRODUCTS:
        inventory = number((market.get("inventory", {}) or {}).get(item))
        old_inventory = number((old_market.get("inventory", {}) or {}).get(item, inventory))
        price = number((market.get("prices", {}) or {}).get(item))
        old_price = number((old_market.get("prices", {}) or {}).get(item, price))
        features[f"shed_{item}"] = number((private.get("shed", {}) or {}).get(item))
        features[f"market_{item}"] = inventory
        features[f"market_delta_{item}"] = inventory - old_inventory
        features[f"price_{item}"] = price
        features[f"price_delta_{item}"] = price - old_price
    return features


def action_at(replay: dict, turn: int, seat: int) -> dict:
    if turn + 1 >= len(replay.get("steps", [])):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    return replay["steps"][turn + 1][seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}


def _farm_money(replay: dict, seat: int, turn: int) -> float:
    step = replay["steps"][min(max(0, turn), len(replay["steps"]) - 1)][seat]
    obs = step.get("observation", {}) or {}
    farms = list(obs.get("farms", []) or [{}, {}])
    return number(farms[seat].get("money")) if seat < len(farms) else 0.0


def window_targets(replay: dict, seat: int, start: int, stop: int) -> dict[str, float]:
    """把未来动作压缩为可执行预算/产能合同，不保留动作顺序。"""
    result: Counter = Counter()
    task_distance: list[int] = []
    center_livestock: list[int] = []
    top_row_plants: list[int] = []
    stop = min(stop, len(replay.get("steps", [])) - 1)
    for turn in range(start, stop):
        obs = replay["steps"][turn][seat]["observation"]
        farm = obs["farms"][seat]
        positions = [farm.get("farmer", [4, 4]), *(farm.get("hands", []) or [])]
        action = action_at(replay, turn, seat)
        units = [action.get("farmer", ["PASS"]), *(action.get("hands", []) or [])]
        for actor, raw in enumerate(units):
            order = list(raw or ["PASS"])
            op = str(order[0])
            if op in MOVE:
                result["moves"] += 1
                continue
            if op == "PASS":
                result["idle"] += 1
                continue
            result["productive"] += 1
            result[f"unit_{op}"] += 1
            if actor < len(positions):
                pos = positions[actor]
                distance = center_distance(pos)
                task_distance.append(distance)
                result["center_tasks"] += float(distance <= 2)
                if op in {"BUILD_PASTURE", "BUILD_COOP", "PLACE"}:
                    center_livestock.append(int(distance <= 2))
                if op == "PLANT":
                    top_row_plants.append(int(int(pos[1]) % 5 <= 1))
                    if len(order) >= 2:
                        result[f"plant_{order[1]}"] += 1
        for raw in action.get("market", []) or []:
            order = list(raw or [])
            if not order:
                continue
            op = str(order[0])
            quantity = number(order[2]) if len(order) >= 3 else 1.0
            result[f"market_{op}"] += quantity
            if len(order) >= 2:
                result[f"market_{op}_{order[1]}"] += quantity
            if op == "SELL" and len(order) >= 2:
                result[f"sell_{order[1]}"] += quantity
                if turn % 24 < 20:
                    result[f"early_sell_{order[1]}"] += quantity
    result["mean_task_distance"] = sum(task_distance) / len(task_distance) if task_distance else 0.0
    result["productive_per_move"] = result["productive"] / max(1.0, result["moves"])
    result["center_task_share"] = result["center_tasks"] / max(1.0, result["productive"])
    result["center_livestock_share"] = sum(center_livestock) / len(center_livestock) if center_livestock else 0.0
    result["top_two_row_plant_share"] = sum(top_row_plants) / len(top_row_plants) if top_row_plants else 0.0
    start_money, end_money = _farm_money(replay, seat, start), _farm_money(replay, seat, stop)
    rival_start, rival_end = _farm_money(replay, 1-seat, start), _farm_money(replay, 1-seat, stop)
    result["money_delta"] = end_money - start_money
    result["rival_money_delta"] = rival_end - rival_start
    result["money_gap_delta"] = (end_money - rival_end) - (start_money - rival_start)
    # 显式补零使聚类维度稳定。
    for op in UNIT_OPS:
        result[f"unit_{op}"] += 0
    for op in MARKET_OPS:
        result[f"market_{op}"] += 0
    for item in PRODUCTS:
        result[f"sell_{item}"] += 0
        result[f"early_sell_{item}"] += 0
    for crop in CROPS:
        result[f"market_BUY_SEED_{crop}"] += 0
        result[f"plant_{crop}"] += 0
    for animal in ANIMALS:
        result[f"market_BUY_ANIMAL_{animal}"] += 0
    return {str(key): float(value) for key, value in result.items()}
