"""Leakage-safe fixed-shape observation encoder for V113."""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

import action_space as space


BOARD_SIZE = 10
MAX_UNITS = 16
BOARD_CHANNELS = 21
UNIT_BASE_FEATURES = 16
UNIT_FEATURES = UNIT_BASE_FEATURES + 5 * BOARD_CHANNELS
SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _inventory_vector(inventory: Mapping[str, Any]) -> list[float]:
    return [_f(space.get(inventory, item, 0)) / 100.0 for item in space.ITEMS]


def _board(farm: Mapping[str, Any], day: int) -> np.ndarray:
    out = np.zeros((BOARD_SIZE, BOARD_SIZE, BOARD_CHANNELS), dtype=np.float32)
    tiles = list(space.get(farm, "tiles", []) or [])
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = tiles[y][x] if y < len(tiles) and x < len(tiles[y]) else "LOCKED"
            row = out[y, x]
            if tile == "LOCKED":
                row[0] = 1.0
                continue
            if tile is None:
                row[1] = 1.0
                continue
            kind = str(space.get(tile, "kind", ""))
            if kind == "WEED":
                row[2] = 1.0
            elif kind == "COOP":
                row[3] = 1.0
            elif kind == "PASTURE":
                row[4] = 1.0
            elif kind == "PLANT":
                crop = str(space.get(tile, "crop", ""))
                if crop in space.CROPS:
                    row[5 + space.CROPS.index(crop)] = 1.0
            animal = str(space.get(tile, "animal", ""))
            if animal in space.ANIMALS:
                row[10 + space.ANIMALS.index(animal)] = 1.0
            row[13] = min(1.0, _f(space.get(tile, "yield_units", 0)) / 10.0)
            row[14] = float(bool(space.get(tile, "watered_today", False)))
            row[15] = float(_f(space.get(tile, "fertilized_until_day", -1)) >= day)
            row[16] = float(bool(space.get(tile, "fed_today", False)))
            row[17] = float(bool(space.get(tile, "cared_today", False)))
            row[18] = float(bool(space.get(tile, "fertilizer_available", False)))
            born = space.get(tile, "planted_day", space.get(tile, "placed_day", day))
            row[19] = min(1.0, max(0.0, day - _f(born, day)) / 30.0)
            lifespan = _f(space.get(tile, "max_lifespan_step", 719), 719)
            row[20] = min(1.0, max(-1.0, (lifespan - day * 24) / 720.0))
    return out


def encode_observation(obs: Mapping[str, Any], opponent_blind: bool = False) -> dict[str, np.ndarray]:
    """Encode only fields visible to the acting seat."""
    player = space.seat(obs)
    farms = list(space.get(obs, "farms", []) or [])
    own = farms[player]
    opponent = farms[1 - player]
    day = int(space.get(obs, "day", int(space.get(obs, "step", 0)) // 24) or 0)
    hour = int(space.get(obs, "hour", int(space.get(obs, "step", 0)) % 24) or 0)

    global_features = [
        day / 30.0,
        hour / 24.0,
        math.sin(2.0 * math.pi * hour / 24.0),
        math.cos(2.0 * math.pi * hour / 24.0),
    ]
    for farm in (own, opponent):
        farmer = list(space.get(farm, "farmer", [0, 0]) or [0, 0])
        global_features.extend([
            math.log1p(max(0.0, _f(space.get(farm, "money", 0)))) / 12.0,
            _f(space.get(farm, "hires_today", 0)) / 16.0,
            len(space.get(farm, "unlocked_quadrants", []) or []) / 4.0,
            len(space.get(farm, "hands", []) or []) / 16.0,
            _f(farmer[0]) / 9.0,
            _f(farmer[1]) / 9.0,
        ])
    if opponent_blind:
        global_features[10:16] = [0.0] * 6
    own_private = space.private(obs)
    global_features.extend(_inventory_vector(space.get(own_private, "shed", {}) or {}))
    global_features.extend([_f(space.get(space.get(own_private, "seeds", {}) or {}, crop, 0)) / 100.0 for crop in space.CROPS])
    market = space.get(obs, "market", {}) or {}
    inventory = space.get(market, "inventory", {}) or {}
    prices = space.get(market, "prices", {}) or {}
    for item in space.PRODUCTS:
        global_features.append((_f(space.get(inventory, item, 10000)) - 10000.0) / 1000.0)
        global_features.append(math.log1p(max(0.0, _f(space.get(prices, item, space.BASE_PRICES[item])))) / math.log1p(500.0))
    demand = {item: 0.0 for item in space.PRODUCTS}
    for shop in list(space.get(space.get(obs, "town", {}) or {}, "unlocked_shops", []) or []):
        products = SHOP_PRODUCTS.get(str(shop), ())
        multiplier = 2.0 if len(products) == 1 else 1.0
        for item in products:
            demand[item] += multiplier
    global_features.extend([demand[item] / 8.0 for item in space.PRODUCTS])

    boards = np.stack((_board(own, day), _board(opponent, day)), axis=0)
    if opponent_blind:
        boards[1] = 0.0
    units = np.zeros((MAX_UNITS, UNIT_FEATURES), dtype=np.float32)
    unit_mask = np.zeros((MAX_UNITS,), dtype=np.float32)
    positions = [space.get(own, "farmer", [0, 0])] + list(space.get(own, "hands", []) or [])
    inventories = list(space.get(own_private, "inventories", []) or [])
    for index, position in enumerate(positions[:MAX_UNITS]):
        unit_mask[index] = 1.0
        units[index, 0] = 1.0
        units[index, 1] = float(index == 0)
        units[index, 2] = _f(position[0]) / 9.0
        units[index, 3] = _f(position[1]) / 9.0
        inv = inventories[index] if index < len(inventories) else {}
        units[index, 4:UNIT_BASE_FEATURES] = np.asarray(_inventory_vector(inv), dtype=np.float32)
        x, y = int(round(_f(position[0]))), int(round(_f(position[1])))
        local = []
        for dx, dy in ((0, 0), (0, -1), (0, 1), (1, 0), (-1, 0)):
            if 0 <= x + dx < BOARD_SIZE and 0 <= y + dy < BOARD_SIZE:
                local.extend(boards[0, y + dy, x + dx])
            else:
                boundary = np.zeros((BOARD_CHANNELS,), dtype=np.float32)
                boundary[0] = 1.0
                local.extend(boundary)
        units[index, UNIT_BASE_FEATURES:] = np.asarray(local, dtype=np.float32)
    return {
        "global": np.asarray(global_features, dtype=np.float32),
        "board": boards,
        "units": units,
        "unit_mask": unit_mask,
    }


GLOBAL_FEATURES = 60
