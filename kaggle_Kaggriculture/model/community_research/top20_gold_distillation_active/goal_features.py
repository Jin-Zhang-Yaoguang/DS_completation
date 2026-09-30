#!/usr/bin/env python3
"""单位级目标路由特征；训练和 serving 共用。"""

from __future__ import annotations

from typing import Any

from contract_features import ANIMALS, CROPS, PRODUCTS, center_distance, state_features


ITEMS = PRODUCTS + ANIMALS
KINDS = ("EMPTY", "PLANT", "PASTURE", "COOP", "WEED", "LOCKED")
TASKS = ("animal_unfed", "animal_uncared", "animal_fertilizer", "animal_harvest", "crop_harvest", "crop_water", "empty", "shed")


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _tile(grid: list, x: int, y: int) -> Any:
    if not (0 <= y < len(grid) and 0 <= x < len(grid[y])):
        return "LOCKED"
    return grid[y][x]


def _kind(tile: Any) -> str:
    if tile is None:
        return "EMPTY"
    return str(tile.get("kind") or "EMPTY") if isinstance(tile, dict) else str(tile)


def _animal(tile: Any) -> str:
    if not isinstance(tile, dict):
        return ""
    value = tile.get("animal")
    return str(value.get("kind") or "") if isinstance(value, dict) else str(value or "")


def _dist(position: tuple[int, int], points: list[tuple[int, int]]) -> float:
    if not points:
        return 20.0
    return float(min(abs(position[0]-x) + abs(position[1]-y) for x, y in points))


def unit_context(obs: dict, previous: dict | None = None) -> dict:
    seat = 1 if int(obs.get("player", 0) or 0) == 1 else 0
    farm = list(obs.get("farms", []) or [{}, {}])[seat]
    positions = [farm.get("farmer") or [4, 4], *(farm.get("hands") or [])]
    inventories = list((obs.get("private") or {}).get("inventories") or [])
    grid = list(farm.get("tiles") or [])
    points = {task: [] for task in TASKS}
    for yy, row in enumerate(grid):
        for xx, value in enumerate(row):
            if value == "LOCKED":
                continue
            value_kind, value_animal = _kind(value), _animal(value)
            if value_animal:
                if not bool(value.get("fed_today")): points["animal_unfed"].append((xx, yy))
                if not bool(value.get("cared_today")): points["animal_uncared"].append((xx, yy))
                if bool(value.get("fertilizer_available")): points["animal_fertilizer"].append((xx, yy))
                if int(value.get("yield_units", 0) or 0) >= 2: points["animal_harvest"].append((xx, yy))
            elif value_kind == "PLANT":
                if int(value.get("yield_units", 0) or 0) >= 2: points["crop_harvest"].append((xx, yy))
                elif not bool(value.get("watered_today")): points["crop_water"].append((xx, yy))
            elif value_kind == "EMPTY":
                points["empty"].append((xx, yy))
    points["shed"] = [(4, 4), (5, 4), (4, 5), (5, 5)]
    return {"base": state_features(obs, previous), "positions": positions, "inventories": inventories, "grid": grid, "points": points}


def unit_features(obs: dict, actor: int, previous: dict | None = None, context: dict | None = None) -> dict[str, float]:
    context = context or unit_context(obs, previous)
    positions, inventories, grid, points = context["positions"], context["inventories"], context["grid"], context["points"]
    position = positions[actor] if actor < len(positions) else [4, 4]
    x, y = int(position[0]), int(position[1])
    inventory = dict(inventories[actor] if actor < len(inventories) else {})
    tile = _tile(grid, x, y); kind = _kind(tile); animal = _animal(tile)
    crop = str(tile.get("crop") or "") if isinstance(tile, dict) else ""
    features = dict(context["base"])
    features.update({
        "actor_index": float(actor), "actor_fraction": actor / max(1.0, len(positions)-1),
        "is_farmer": float(actor == 0), "unit_x": float(x), "unit_y": float(y),
        "unit_center_distance": float(center_distance((x, y))),
        "unit_inventory_total": float(sum(max(0, int(v or 0)) for v in inventory.values())),
        "tile_yield": _number(tile.get("yield_units")) if isinstance(tile, dict) else 0.0,
        "tile_watered": float(bool(tile.get("watered_today"))) if isinstance(tile, dict) else 0.0,
        "tile_fed": float(bool(tile.get("fed_today"))) if isinstance(tile, dict) else 0.0,
        "tile_cared": float(bool(tile.get("cared_today"))) if isinstance(tile, dict) else 0.0,
        "tile_fertilizer_available": float(bool(tile.get("fertilizer_available"))) if isinstance(tile, dict) else 0.0,
    })
    for item in ITEMS:
        features[f"unit_inventory_{item}"] = _number(inventory.get(item))
    for value in KINDS:
        features[f"tile_kind_{value}"] = float(kind == value)
    for value in CROPS:
        features[f"tile_crop_{value}"] = float(crop == value)
    for value in ANIMALS:
        features[f"tile_animal_{value}"] = float(animal == value)
    for task in TASKS:
        features[f"distance_{task}"] = _dist((x, y), points[task])
        features[f"count_{task}"] = float(len(points[task]))
    return features


def goal_label(order: list, target_tile: Any) -> str:
    op = str(order[0]) if order else "PASS"
    if op == "HARVEST":
        return "HARVEST_ANIMAL" if _animal(target_tile) else "HARVEST_CROP"
    if op == "PLANT":
        crop = str(order[1]) if len(order) > 1 else "WHEAT"
        return f"PLANT_{crop}" if crop in CROPS else "PLANT_WHEAT"
    if op == "PLACE":
        animal = str(order[1]) if len(order) > 1 else "COW"
        return f"PLACE_{animal}" if animal in ANIMALS else "PLACE_COW"
    if op == "PICKUP":
        item = str(order[1]) if len(order) > 1 else "WHEAT"
        if item in ANIMALS: return f"PICKUP_{item}"
        if item == "WHEAT": return "PICKUP_WHEAT"
        return "PICKUP_OUTPUT"
    if op in {"FEED", "CARE", "COLLECT_FERTILIZER", "WATER", "FERTILIZE", "DIG", "BUILD_PASTURE", "BUILD_COOP", "DROP"}:
        return op
    return "IDLE"
