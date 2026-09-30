"""V121 行为蒸馏特征与动作合法化；训练和闭环推理共享。"""

from __future__ import annotations

from collections import Counter
import json
from typing import Any, Mapping


PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "ICE_CREAM_SHOP", "FARMERS_MARKET", "YARN_STORE", "PET_CAFE", "JUICE_BAR", "SMOOTHIE_SHOP")
MOVE_DELTA = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
SHED_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}


def integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def animal_kind(tile: Any) -> str:
    if not isinstance(tile, Mapping):
        return "NONE"
    animal = tile.get("animal")
    if isinstance(animal, Mapping):
        return str(animal.get("kind") or "NONE")
    return str(animal or "NONE")


def tile_kind(tile: Any) -> str:
    if tile == "LOCKED":
        return "LOCKED"
    if not isinstance(tile, Mapping):
        return "EMPTY"
    return str(tile.get("kind") or "OTHER")


def positions(farm: Mapping[str, Any]) -> list[tuple[int, int]]:
    values = [farm.get("farmer") or [4, 4], *list(farm.get("hands") or [])]
    return [(integer(value[0], 4), integer(value[1], 4)) for value in values]


def grid_at(grid: list, x: int, y: int) -> Any:
    if y < 0 or y >= len(grid) or x < 0 or x >= len(grid[y]):
        return "LOCKED"
    return grid[y][x]


def farm_counts(grid: list) -> Counter:
    counts: Counter = Counter()
    for row in grid:
        for tile in row if isinstance(row, list) else []:
            kind = tile_kind(tile)
            counts[f"kind_{kind}"] += 1
            if isinstance(tile, Mapping):
                crop = str(tile.get("crop") or "NONE")
                animal = animal_kind(tile)
                if crop != "NONE":
                    counts[f"crop_{crop}"] += 1
                if animal != "NONE":
                    counts[f"animal_{animal}"] += 1
    return counts


def global_features(obs: Mapping[str, Any]) -> dict[str, float]:
    seat = 1 if integer(obs.get("player")) == 1 else 0
    farms = list(obs.get("farms") or [{}, {}])
    while len(farms) < 2:
        farms.append({})
    own, rival = farms[seat], farms[1 - seat]
    own_grid = list(own.get("tiles") or [])
    rival_grid = list(rival.get("tiles") or [])
    own_counts, rival_counts = farm_counts(own_grid), farm_counts(rival_grid)
    private = dict(obs.get("private") or {})
    market = dict(obs.get("market") or {})
    town = dict(obs.get("town") or {})
    day, hour = integer(obs.get("day")), integer(obs.get("hour"))
    own_pos, rival_pos = positions(own), positions(rival)
    result: dict[str, float] = {
        "day": float(day), "hour": float(hour), "season_fraction": day / 30.0,
        "own_money": float(integer(own.get("money"))), "rival_money": float(integer(rival.get("money"))),
        "money_gap": float(integer(own.get("money")) - integer(rival.get("money"))),
        "own_hands": float(max(0, len(own_pos) - 1)), "rival_hands": float(max(0, len(rival_pos) - 1)),
        "own_actors": float(len(own_pos)), "rival_actors": float(len(rival_pos)),
        "own_lands": float(len(own.get("unlocked_quadrants") or [])),
        "rival_lands": float(len(rival.get("unlocked_quadrants") or [])),
        "hires_today": float(integer(own.get("hires_today"))),
        "shed_used": float(sum(max(0, integer(v)) for v in dict(private.get("shed") or {}).values())),
    }
    shops = Counter(str(value) for value in list(town.get("unlocked_shops") or []))
    for shop in SHOPS:
        result[f"shop_{shop}"] = float(shops.get(shop, 0))
    for crop in CROPS:
        result[f"own_crop_{crop}"] = float(own_counts.get(f"crop_{crop}", 0))
        result[f"rival_crop_{crop}"] = float(rival_counts.get(f"crop_{crop}", 0))
        result[f"seed_{crop}"] = float(integer(dict(private.get("seeds") or {}).get(crop)))
    for animal in ANIMALS:
        result[f"own_animal_{animal}"] = float(own_counts.get(f"animal_{animal}", 0))
        result[f"rival_animal_{animal}"] = float(rival_counts.get(f"animal_{animal}", 0))
    for kind in ("PLANT", "PASTURE", "COOP", "EMPTY"):
        result[f"own_kind_{kind}"] = float(own_counts.get(f"kind_{kind}", 0))
    for item in PRODUCTS:
        result[f"shed_{item}"] = float(integer(dict(private.get("shed") or {}).get(item)))
        result[f"price_{item}"] = float(integer(dict(market.get("prices") or {}).get(item)))
        result[f"market_{item}"] = float(integer(dict(market.get("inventory") or {}).get(item), 10000))
    return result


def _task_points(grid: list) -> dict[str, list[tuple[int, int]]]:
    points: dict[str, list[tuple[int, int]]] = {key: [] for key in ("EMPTY", "WATER", "HARVEST", "ANIMAL", "FERTILIZER")}
    for y, row in enumerate(grid):
        for x, tile in enumerate(row if isinstance(row, list) else []):
            kind = tile_kind(tile)
            if kind == "EMPTY":
                points["EMPTY"].append((x, y))
            if not isinstance(tile, Mapping):
                continue
            if kind == "PLANT" and not bool(tile.get("watered_today")):
                points["WATER"].append((x, y))
            if integer(tile.get("yield_units")) > 0:
                points["HARVEST"].append((x, y))
            if animal_kind(tile) != "NONE":
                points["ANIMAL"].append((x, y))
                points["FERTILIZER"].append((x, y))
    return points


def actor_features(obs: Mapping[str, Any], actor: int) -> dict[str, float]:
    result = global_features(obs)
    seat = 1 if integer(obs.get("player")) == 1 else 0
    farm = list(obs.get("farms") or [{}, {}])[seat]
    grid = list(farm.get("tiles") or [])
    actor_positions = positions(farm)
    x, y = actor_positions[actor]
    private = dict(obs.get("private") or {})
    inventories = [dict(value or {}) for value in list(private.get("inventories") or [])]
    inventory = inventories[actor] if actor < len(inventories) else {}
    tile = grid_at(grid, x, y)
    kind, crop, animal = tile_kind(tile), "NONE", animal_kind(tile)
    if isinstance(tile, Mapping):
        crop = str(tile.get("crop") or "NONE")
    result.update({
        "actor_index": float(actor), "actor_fraction": actor / max(1, len(actor_positions) - 1),
        "is_farmer": float(actor == 0), "actor_x": float(x), "actor_y": float(y),
        "center_distance": float(min(abs(x - sx) + abs(y - sy) for sx, sy in ((4, 4), (5, 4), (4, 5), (5, 5)))),
        "on_shed_access": float((x, y) in SHED_ACCESS), "tile_yield": float(integer(tile.get("yield_units")) if isinstance(tile, Mapping) else 0),
        "tile_watered": float(bool(tile.get("watered_today")) if isinstance(tile, Mapping) else 0),
        "tile_unwatered_streak": float(integer(tile.get("consecutive_unwatered")) if isinstance(tile, Mapping) else 0),
        "tile_fed": float(bool(tile.get("fed_today")) if isinstance(tile, Mapping) else 0),
        "tile_cared": float(bool(tile.get("cared_today")) if isinstance(tile, Mapping) else 0),
        "tile_fertilizer_available": float(bool(tile.get("fertilizer_available")) if isinstance(tile, Mapping) else 0),
    })
    for value in ("EMPTY", "PLANT", "PASTURE", "COOP", "OTHER"):
        result[f"tile_kind_{value}"] = float(kind == value)
    for value in (*CROPS, "NONE"):
        result[f"tile_crop_{value}"] = float(crop == value)
    for value in (*ANIMALS, "NONE"):
        result[f"tile_animal_{value}"] = float(animal == value)
    result["actor_inventory_total"] = float(sum(max(0, integer(v)) for v in inventory.values()))
    for item in (*PRODUCTS, *ANIMALS):
        result[f"actor_inv_{item}"] = float(integer(inventory.get(item)))
    points = _task_points(grid)
    for task, values in points.items():
        distance = min((abs(x - tx) + abs(y - ty) for tx, ty in values), default=20)
        result[f"nearest_{task}"] = float(distance)
        result[f"count_{task}"] = float(len(values))
    return result


def normalize_unit(raw: Any) -> tuple[str, int]:
    order = list(raw or ["PASS"])
    op = str(order[0])
    item = str(order[1]) if len(order) >= 2 else ""
    quantity = integer(order[2], 1) if len(order) >= 3 else 1
    if op == "PLANT" and item:
        return f"{op}:{item}", 1
    if op in {"PICKUP", "PLACE"} and item:
        return f"{op}:{item}:{max(1, quantity)}", max(1, quantity)
    return op, 1


def market_names() -> list[str]:
    names = ["HIRE", "BUY_LAND"]
    names += [f"BUY_SEED:{item}" for item in CROPS]
    names += [f"BUY_ANIMAL:{item}" for item in ANIMALS]
    names += [f"BUY_PRODUCT:{item}" for item in PRODUCTS]
    names += [f"SELL:{item}" for item in PRODUCTS]
    return names


def market_vector(action: Mapping[str, Any], names: list[str]) -> list[float]:
    values: Counter = Counter()
    for raw in action.get("market", []) or []:
        order = list(raw or [])
        if not order:
            continue
        op = str(order[0])
        key = op if op in {"HIRE", "BUY_LAND"} else f"{op}:{order[1]}" if len(order) >= 2 else op
        values[key] += integer(order[2], 1) if len(order) >= 3 else 1
    return [float(values.get(name, 0)) for name in names]


def _available_tile(grid: list, x: int, y: int) -> bool:
    return grid_at(grid, x, y) != "LOCKED"


def legalize_unit(label: str, quantity: int, obs: Mapping[str, Any], actor: int) -> list[Any]:
    seat = 1 if integer(obs.get("player")) == 1 else 0
    farm = list(obs.get("farms") or [{}, {}])[seat]
    grid = list(farm.get("tiles") or [])
    actor_positions = positions(farm)
    if actor >= len(actor_positions):
        return ["PASS"]
    x, y = actor_positions[actor]
    tile = grid_at(grid, x, y)
    private = dict(obs.get("private") or {})
    inventories = [dict(value or {}) for value in list(private.get("inventories") or [])]
    inventory = inventories[actor] if actor < len(inventories) else {}
    if label in MOVE_DELTA:
        dx, dy = MOVE_DELTA[label]
        nx, ny = x + dx, y + dy
        return [label] if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]) else ["PASS"]
    if label in {"PASS", "DROP"}:
        if label == "DROP" and ((x, y) not in SHED_ACCESS or not any(integer(v) > 0 for v in inventory.values())):
            return ["PASS"]
        return [label]
    kind = tile_kind(tile)
    animal = animal_kind(tile)
    if label == "WATER" and kind == "PLANT" and not bool(tile.get("watered_today")):
        return ["WATER"]
    if label == "HARVEST" and isinstance(tile, Mapping) and integer(tile.get("yield_units")) > 0:
        return ["HARVEST"]
    if label == "FERTILIZE" and kind == "PLANT":
        return ["FERTILIZE"]
    if label in {"FEED", "CARE", "COLLECT_FERTILIZER"} and animal != "NONE":
        return [label]
    if label == "DIG" and kind not in {"EMPTY", "LOCKED"}:
        return ["DIG"]
    if label in {"BUILD_PASTURE", "BUILD_COOP"} and kind == "EMPTY":
        return [label]
    if ":" in label:
        parts = label.split(":")
        op, item = parts[0], parts[1]
        if len(parts) >= 3:
            quantity = integer(parts[2], quantity)
        quantity = max(1, integer(quantity, 1))
        if op == "PLANT" and item in CROPS and kind == "EMPTY" and integer(dict(private.get("seeds") or {}).get(item)) > 0:
            return ["PLANT", item]
        if op == "PICKUP" and (x, y) in SHED_ACCESS:
            available = integer(dict(private.get("shed") or {}).get(item))
            if available > 0:
                return ["PICKUP", item, min(quantity, available)]
        if op == "PLACE":
            available = integer(inventory.get(item))
            if item in ANIMALS and available > 0:
                required = "COOP" if item == "GOOSE" else "PASTURE"
                if kind == required and animal == "NONE":
                    return ["PLACE", item]
            if available > 0 and (x, y) in SHED_ACCESS:
                return ["PLACE", item, min(quantity, available)]
    return ["PASS"]


def decode_market(values: list[float], names: list[str], obs: Mapping[str, Any]) -> list[list[Any]]:
    seat = 1 if integer(obs.get("player")) == 1 else 0
    farm = list(obs.get("farms") or [{}, {}])[seat]
    private = dict(obs.get("private") or {})
    money = integer(farm.get("money"))
    shed = dict(private.get("shed") or {})
    output: list[list[Any]] = []
    rounded = {name: max(0, int(round(value))) for name, value in zip(names, values)}
    # 先卖出，随后按冠军数据的常见顺序安排采购；每回合最多十单。
    for item in PRODUCTS:
        quantity = min(rounded.get(f"SELL:{item}", 0), integer(shed.get(item)))
        if quantity > 0:
            output.append(["SELL", item, quantity])
    for item in PRODUCTS:
        quantity = rounded.get(f"BUY_PRODUCT:{item}", 0)
        if quantity > 0:
            output.append(["BUY_PRODUCT", item, quantity])
    for item in CROPS:
        quantity = rounded.get(f"BUY_SEED:{item}", 0)
        if quantity > 0:
            output.append(["BUY_SEED", item, quantity])
    output.extend([["HIRE"] for _ in range(min(rounded.get("HIRE", 0), 15))])
    output.extend([["BUY_LAND"] for _ in range(min(rounded.get("BUY_LAND", 0), 1))])
    for item in ANIMALS:
        quantity = rounded.get(f"BUY_ANIMAL:{item}", 0)
        if quantity > 0:
            output.append(["BUY_ANIMAL", item, quantity])
    return output[:10]


def label_json(label: str) -> str:
    return json.dumps(label, ensure_ascii=True)
