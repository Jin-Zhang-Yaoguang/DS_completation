#!/usr/bin/env python3
"""V124 独立合同：只从当前与已经发生的观测构造运行时特征。"""

from __future__ import annotations

from collections import Counter
from typing import Any


PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
SHOPS = (
    "BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "ICE_CREAM_SHOP",
    "FARMERS_MARKET", "YARN_STORE", "PET_CAFE", "JUICE_BAR",
    "SMOOTHIE_SHOP",
)
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
UNIT_OPS = (
    "PLANT", "WATER", "FERTILIZE", "DIG", "HARVEST", "BUILD_PASTURE",
    "BUILD_COOP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
    "PICKUP", "DROP",
)
MARKET_OPS = ("HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "SELL")
CENTERS = ((4, 4), (5, 4), (4, 5), (5, 5))


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def seat_of(obs: dict) -> int:
    return 1 if int(obs.get("player", 0) or 0) == 1 else 0


def center_distance(position: list | tuple) -> int:
    x, y = int(position[0]), int(position[1])
    return min(abs(x - cx) + abs(y - cy) for cx, cy in CENTERS)


def tile_summary(farm: dict) -> Counter:
    result: Counter = Counter()
    for y, row in enumerate(farm.get("tiles", []) or []):
        for x, tile in enumerate(row if isinstance(row, list) else []):
            if tile == "LOCKED":
                result["locked"] += 1
                continue
            if tile is None:
                result["empty"] += 1
                continue
            if not isinstance(tile, dict):
                continue
            crop = tile.get("crop")
            animal = tile.get("animal")
            if isinstance(animal, dict):
                animal = animal.get("kind")
            kind = tile.get("kind")
            if crop:
                result[f"crop_{crop}"] += 1
                result["crops"] += 1
                result["dry_crops"] += float(not bool(tile.get("watered_today")))
                result["top_crop"] += float(y % 5 <= 1)
            if animal:
                result[f"animal_{animal}"] += 1
                result["animals"] += 1
                result["center_animal"] += float(center_distance((x, y)) <= 2)
            if kind:
                result[f"kind_{kind}"] += 1
    return result


def state_features(obs: dict, previous: dict | None = None) -> dict[str, float]:
    """运行时白名单特征；previous 必须来自同局更早时刻。"""
    seat = seat_of(obs)
    farms = list(obs.get("farms", []) or [{}, {}])
    while len(farms) < 2:
        farms.append({})
    own, rival = farms[seat], farms[1 - seat]
    own_counts, rival_counts = tile_summary(own), tile_summary(rival)

    old_farms = list((previous or {}).get("farms", []) or [{}, {}])
    while len(old_farms) < 2:
        old_farms.append({})
    private = obs.get("private", {}) or {}
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    own_money, rival_money = number(own.get("money")), number(rival.get("money"))
    own_workers = 1 + len(own.get("hands", []) or [])
    rival_workers = 1 + len(rival.get("hands", []) or [])

    features: dict[str, float] = {
        "day": float(day),
        "hour": float(hour),
        "cycle_phase": float(day % 3),
        "season_fraction": float(day * 24 + hour) / 720.0,
        "own_money": own_money,
        "rival_money": rival_money,
        "money_gap": own_money - rival_money,
        "own_money_change": own_money - number(old_farms[seat].get("money", own_money)),
        "rival_money_change": rival_money - number(old_farms[1 - seat].get("money", rival_money)),
        "own_workers": float(own_workers),
        "rival_workers": float(rival_workers),
        "worker_gap": float(own_workers - rival_workers),
        "own_hires_today": number(own.get("hires_today")),
        "rival_hires_today": number(rival.get("hires_today")),
        "own_unlocked_tiles": 100.0 - float(own_counts.get("locked", 0)),
        "rival_unlocked_tiles": 100.0 - float(rival_counts.get("locked", 0)),
        "own_empty_tiles": float(own_counts.get("empty", 0)),
        "rival_empty_tiles": float(rival_counts.get("empty", 0)),
        "shed_used": float(sum(max(0.0, number(v)) for v in (private.get("shed", {}) or {}).values())),
        "own_dry_crop_share": float(own_counts.get("dry_crops", 0)) / max(1.0, float(own_counts.get("crops", 0))),
        "own_center_animal_share": float(own_counts.get("center_animal", 0)) / max(1.0, float(own_counts.get("animals", 0))),
        "own_top_crop_share": float(own_counts.get("top_crop", 0)) / max(1.0, float(own_counts.get("crops", 0))),
    }

    shops = Counter(str(v) for v in (obs.get("town", {}).get("unlocked_shops", []) or []))
    for shop in SHOPS:
        features[f"shop_{shop}"] = float(shops.get(shop, 0))
    for crop in CROPS:
        features[f"own_crop_{crop}"] = float(own_counts.get(f"crop_{crop}", 0))
        features[f"rival_crop_{crop}"] = float(rival_counts.get(f"crop_{crop}", 0))
        features[f"seed_{crop}"] = number((private.get("seeds", {}) or {}).get(crop))
    for animal in ANIMALS:
        features[f"own_animal_{animal}"] = float(own_counts.get(f"animal_{animal}", 0))
        features[f"rival_animal_{animal}"] = float(rival_counts.get(f"animal_{animal}", 0))

    market = obs.get("market", {}) or {}
    old_market = (previous or {}).get("market", {}) or {}
    for item in PRODUCTS:
        inventory = number((market.get("inventory", {}) or {}).get(item))
        price = number((market.get("prices", {}) or {}).get(item))
        old_inventory = number((old_market.get("inventory", {}) or {}).get(item, inventory))
        old_price = number((old_market.get("prices", {}) or {}).get(item, price))
        features[f"shed_{item}"] = number((private.get("shed", {}) or {}).get(item))
        features[f"market_{item}"] = inventory
        features[f"market_delta_{item}"] = inventory - old_inventory
        features[f"price_{item}"] = price
        features[f"price_delta_{item}"] = price - old_price
    return features


def action_after_observation(replay: dict, turn: int, seat: int) -> dict:
    """Kaggle Replay 把 obs[t] 对应的动作记录在 steps[t+1].action。"""
    if turn + 1 >= len(replay.get("steps", [])):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    return replay["steps"][turn + 1][seat].get("action") or {
        "farmer": ["PASS"], "hands": [], "market": [],
    }


def _money_at(replay: dict, seat: int, turn: int) -> float:
    step = replay["steps"][min(max(0, turn), len(replay["steps"]) - 1)][seat]
    farms = list((step.get("observation", {}) or {}).get("farms", []) or [{}, {}])
    return number(farms[seat].get("money")) if seat < len(farms) else 0.0


def aggregate_contract(replay: dict, seat: int, start: int, stop: int) -> dict[str, float]:
    """压缩未来窗口为无顺序预算，严禁作为运行时特征。"""
    totals: Counter = Counter()
    distances: list[int] = []
    stop = min(stop, len(replay.get("steps", [])) - 1)
    for turn in range(start, stop):
        obs = replay["steps"][turn][seat].get("observation", {}) or {}
        farms = list(obs.get("farms", []) or [{}, {}])
        farm = farms[seat] if seat < len(farms) else {}
        positions = [farm.get("farmer", [4, 4]), *(farm.get("hands", []) or [])]
        action = action_after_observation(replay, turn, seat)
        unit_actions = [action.get("farmer", ["PASS"]), *(action.get("hands", []) or [])]
        for actor, raw in enumerate(unit_actions):
            order = list(raw or ["PASS"])
            op = str(order[0])
            totals["unit_decisions"] += 1
            if op in MOVES:
                totals["moves"] += 1
            elif op == "PASS":
                totals["idle"] += 1
            else:
                totals["productive"] += 1
                totals[f"unit_{op}"] += 1
                if actor < len(positions):
                    distance = center_distance(positions[actor])
                    distances.append(distance)
                    totals["center_tasks"] += float(distance <= 2)
                    if op == "PLANT" and len(order) >= 2:
                        totals[f"plant_{order[1]}"] += 1
        for raw in action.get("market", []) or []:
            order = list(raw or [])
            if not order:
                continue
            op = str(order[0])
            quantity = number(order[2]) if len(order) >= 3 else 1.0
            totals[f"market_{op}"] += quantity
            if len(order) >= 2:
                totals[f"market_{op}_{order[1]}"] += quantity
            if op == "SELL" and len(order) >= 2:
                totals[f"sell_{order[1]}"] += quantity
                if turn % 24 < 20:
                    totals[f"early_sell_{order[1]}"] += quantity

    totals["mean_task_distance"] = sum(distances) / len(distances) if distances else 0.0
    totals["productive_share"] = totals["productive"] / max(1.0, totals["unit_decisions"])
    totals["center_task_share"] = totals["center_tasks"] / max(1.0, totals["productive"])
    own_start, own_end = _money_at(replay, seat, start), _money_at(replay, seat, stop)
    rival_start, rival_end = _money_at(replay, 1 - seat, start), _money_at(replay, 1 - seat, stop)
    totals["money_delta"] = own_end - own_start
    totals["rival_money_delta"] = rival_end - rival_start
    totals["money_gap_delta"] = (own_end - rival_end) - (own_start - rival_start)

    for op in UNIT_OPS:
        totals[f"unit_{op}"] += 0
    for op in MARKET_OPS:
        totals[f"market_{op}"] += 0
    for crop in CROPS:
        totals[f"plant_{crop}"] += 0
        totals[f"market_BUY_SEED_{crop}"] += 0
    for animal in ANIMALS:
        totals[f"market_BUY_ANIMAL_{animal}"] += 0
    for item in PRODUCTS:
        totals[f"sell_{item}"] += 0
        totals[f"early_sell_{item}"] += 0
    return {str(k): float(v) for k, v in totals.items()}


def behavior_fingerprint(replay: dict, seat: int) -> dict[str, float]:
    """仅用于行为分族和数据切分，不进入运行时 Router。"""
    totals: Counter = Counter()
    for quarter, (start, stop) in enumerate(((0, 180), (180, 360), (360, 540), (540, 719))):
        contract = aggregate_contract(replay, seat, start, stop)
        decisions = max(1.0, contract.get("unit_decisions", 0.0))
        for name in ("moves", "idle", "productive"):
            totals[f"q{quarter}_{name}_share"] = contract.get(name, 0.0) / decisions
        for op in UNIT_OPS:
            totals[f"q{quarter}_unit_{op}_share"] = contract.get(f"unit_{op}", 0.0) / decisions
        for op in MARKET_OPS:
            totals[f"q{quarter}_market_{op}_per_turn"] = contract.get(f"market_{op}", 0.0) / max(1, stop - start)
        totals[f"q{quarter}_center_task_share"] = contract.get("center_task_share", 0.0)
        totals[f"q{quarter}_mean_task_distance"] = contract.get("mean_task_distance", 0.0) / 10.0
        totals[f"q{quarter}_money_delta_scaled"] = contract.get("money_delta", 0.0) / 100000.0
        seed_total = sum(contract.get(f"market_BUY_SEED_{crop}", 0.0) for crop in CROPS)
        for crop in CROPS:
            totals[f"q{quarter}_seed_{crop}_share"] = contract.get(f"market_BUY_SEED_{crop}", 0.0) / max(1.0, seed_total)
    return {str(k): float(v) for k, v in totals.items()}
