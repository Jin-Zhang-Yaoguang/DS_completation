"""Stable daily public-state features for the PPO v3 MoVE router.

The router may only use fields visible to a submitted Kaggle agent.  This file
has no dependency on JAX or kaggle-environments, so it is also used by the
NumPy-only submission path.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np


CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("COW", "SHEEP", "GOOSE")
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET")
BASE_PRICES = {
    "WHEAT": 25.0, "CARROT": 35.0, "TOMATO": 60.0, "STRAWBERRY": 120.0,
    "MELON": 250.0, "EGG": 50.0, "MILK": 160.0, "WOOL": 200.0, "FERTILIZER": 100.0,
}


def get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def seat(obs: Any) -> int:
    return 1 if int(get(obs, "player", 0) or 0) == 1 else 0


def farm(obs: Any, player: int | None = None) -> Any:
    farms = list(get(obs, "farms", []) or [])
    player = seat(obs) if player is None else int(player)
    return farms[player] if 0 <= player < len(farms) else {}


def _tile_counts(target: Mapping[str, Any]) -> dict[str, float]:
    values = {f"crop.{item}": 0.0 for item in CROPS}
    values.update({f"animal.{item}": 0.0 for item in ANIMALS})
    values.update({"weed": 0.0, "crop_yield": 0.0, "animal_yield": 0.0, "at_risk": 0.0})
    for row in list(get(target, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, Mapping):
                continue
            if str(tile.get("kind", "")) == "WEED":
                values["weed"] += 1.0
            crop = tile.get("crop")
            animal = tile.get("animal")
            if crop in CROPS:
                values[f"crop.{crop}"] += 1.0
                values["crop_yield"] += max(0.0, float(tile.get("yield_units", 0) or 0))
                if int(tile.get("consecutive_unwatered", 0) or 0) >= 1 and not bool(tile.get("watered_today", False)):
                    values["at_risk"] += 1.0
            if animal in ANIMALS:
                values[f"animal.{animal}"] += 1.0
                values["animal_yield"] += max(0.0, float(tile.get("yield_units", 0) or 0))
                if int(tile.get("consecutive_unfed", 0) or 0) >= 1 and not bool(tile.get("fed_today", False)):
                    values["at_risk"] += 1.0
    return values


FEATURE_NAMES: list[str] = ["day", "remaining", "seat"]
for prefix in ("self", "opponent"):
    FEATURE_NAMES += [f"{prefix}.money", f"{prefix}.money_delta", f"{prefix}.unlocked", f"{prefix}.hands"]
    FEATURE_NAMES += [f"{prefix}.crop.{item}" for item in CROPS]
    FEATURE_NAMES += [f"{prefix}.animal.{item}" for item in ANIMALS]
    FEATURE_NAMES += [f"{prefix}.weed", f"{prefix}.crop_yield", f"{prefix}.animal_yield", f"{prefix}.at_risk"]
FEATURE_NAMES += [f"shed.{item}" for item in PRODUCTS]
FEATURE_NAMES += [f"seed.{item}" for item in CROPS]
FEATURE_NAMES += ["shed_free_capacity"]
for item in PRODUCTS:
    FEATURE_NAMES += [f"market.{item}.inventory", f"market.{item}.price", f"market.{item}.inventory_delta", f"market.{item}.price_delta"]
FEATURE_NAMES += [f"shop.{shop}" for shop in SHOPS]
FEATURE_NAMES += ["previous.production", "previous.market", "opponent.structure_delta"]
FEATURE_DIM = len(FEATURE_NAMES)
SCHEMA_VERSION = "kaggriculture-ppo-v3-move-features-1"


def _farm_features(values: dict[str, float], prefix: str, target: Any, previous_money: float | None) -> None:
    money = float(get(target, "money", 0.0) or 0.0)
    values[f"{prefix}.money"] = money / 200000.0
    values[f"{prefix}.money_delta"] = (money - (money if previous_money is None else previous_money)) / 50000.0
    values[f"{prefix}.unlocked"] = len(get(target, "unlocked_quadrants", []) or []) / 4.0
    values[f"{prefix}.hands"] = len(get(target, "hands", []) or []) / 16.0
    counts = _tile_counts(target)
    for item in CROPS:
        values[f"{prefix}.crop.{item}"] = counts[f"crop.{item}"] / 25.0
    for item in ANIMALS:
        values[f"{prefix}.animal.{item}"] = counts[f"animal.{item}"] / 25.0
    values[f"{prefix}.weed"] = counts["weed"] / 25.0
    values[f"{prefix}.crop_yield"] = counts["crop_yield"] / 100.0
    values[f"{prefix}.animal_yield"] = counts["animal_yield"] / 100.0
    values[f"{prefix}.at_risk"] = counts["at_risk"] / 25.0


def encode_observation(obs: Any, history: Mapping[str, Any] | None = None, previous_decision: tuple[int, int] = (0, 0)) -> np.ndarray:
    """Encode only public/current-player information into a fixed float vector."""
    history = history or {}
    player = seat(obs)
    farms = list(get(obs, "farms", []) or [])
    if len(farms) < 2:
        raise ValueError("expected two farms")
    day = int(get(obs, "day", int(get(obs, "step", 0) or 0) // 24) or 0)
    values = {name: 0.0 for name in FEATURE_NAMES}
    values["day"] = min(29, max(0, day)) / 29.0
    values["remaining"] = max(0, 29 - min(29, day)) / 29.0
    values["seat"] = float(player)
    old_money = list(history.get("money", [None, None]) or [None, None])
    _farm_features(values, "self", farms[player], old_money[player] if len(old_money) > player else None)
    other = 1 - player
    _farm_features(values, "opponent", farms[other], old_money[other] if len(old_money) > other else None)

    private = get(obs, "private", {}) or {}
    shed = dict(get(private, "shed", {}) or {})
    seeds = dict(get(private, "seeds", {}) or {})
    for item in PRODUCTS:
        values[f"shed.{item}"] = max(0.0, float(shed.get(item, 0) or 0)) / 100.0
    for item in CROPS:
        values[f"seed.{item}"] = max(0.0, float(seeds.get(item, 0) or 0)) / 50.0
    values["shed_free_capacity"] = max(0.0, 100.0 - sum(max(0.0, float(shed.get(item, 0) or 0)) for item in PRODUCTS)) / 100.0

    market = get(obs, "market", {}) or {}
    inventory = dict(get(market, "inventory", {}) or {})
    prices = dict(get(market, "prices", {}) or {})
    old_inventory = dict(history.get("market_inventory", {}) or {})
    old_prices = dict(history.get("market_prices", {}) or {})
    for item in PRODUCTS:
        inv = float(inventory.get(item, 10000) or 10000)
        price = float(prices.get(item, BASE_PRICES[item]) or BASE_PRICES[item])
        values[f"market.{item}.inventory"] = (inv - 10000.0) / 10000.0
        values[f"market.{item}.price"] = price / BASE_PRICES[item]
        values[f"market.{item}.inventory_delta"] = (inv - float(old_inventory.get(item, inv))) / 10000.0
        values[f"market.{item}.price_delta"] = (price - float(old_prices.get(item, price))) / BASE_PRICES[item]

    shops = list(get(get(obs, "town", {}) or {}, "unlocked_shops", []) or [])
    for shop in SHOPS:
        values[f"shop.{shop}"] = shops.count(shop) / 8.0
    values["previous.production"] = float(previous_decision[0]) / 8.0
    values["previous.market"] = float(previous_decision[1]) / 8.0
    old_signature = float(history.get("opponent_signature", 0.0) or 0.0)
    signature = sum(_tile_counts(farms[other]).values()) + 5.0 * len(get(farms[other], "hands", []) or [])
    values["opponent.structure_delta"] = (signature - old_signature) / 50.0
    vector = np.asarray([values[name] for name in FEATURE_NAMES], dtype=np.float32)
    if vector.shape != (FEATURE_DIM,) or not np.all(np.isfinite(vector)):
        raise ValueError("invalid PPO v3 feature vector")
    return np.clip(vector, -5.0, 5.0)


def update_history(obs: Any) -> dict[str, Any]:
    farms = list(get(obs, "farms", []) or [])
    market = get(obs, "market", {}) or {}
    player = seat(obs)
    other = 1 - player
    signature = 0.0
    if len(farms) > other:
        signature = sum(_tile_counts(farms[other]).values()) + 5.0 * len(get(farms[other], "hands", []) or [])
    return {
        "money": [float(get(item, "money", 0.0) or 0.0) for item in farms],
        "market_inventory": dict(get(market, "inventory", {}) or {}),
        "market_prices": dict(get(market, "prices", {}) or {}),
        "opponent_signature": signature,
    }


def potential(obs: Any) -> float:
    """Small observable potential for correctly terminal-cancelled shaping."""
    player = seat(obs)
    farms = list(get(obs, "farms", []) or [])
    if len(farms) < 2:
        return 0.0
    own = float(get(farms[player], "money", 0.0) or 0.0)
    other = float(get(farms[1 - player], "money", 0.0) or 0.0)
    return 0.05 * math.tanh((own - other) / 100000.0)
