"""Hierarchical BC+PPO wrapper around the frozen v2 Kaggriculture agent.

The neural policy acts once per in-game day.  It chooses the production route
on day seven and applies conservative residual controls to existing SELL
orders.  All unit-level actions and safety repairs remain owned by base_agent.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import base_agent


SCHEMA_VERSION = "kaggriculture-v3-macro-1"
_SOURCE_PATH = globals().get("__file__")
MODEL_FILE = (Path(_SOURCE_PATH).resolve().parent if _SOURCE_PATH else Path.cwd()) / "policy_weights.npz"

CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
INVENTORY_ITEMS = PRODUCTS + ANIMALS
SHOPS = (
    "BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE",
    "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET",
)
BASE_PRICES = {
    "WHEAT": 25.0, "CARROT": 35.0, "TOMATO": 60.0,
    "STRAWBERRY": 120.0, "MELON": 250.0, "EGG": 50.0,
    "MILK": 160.0, "WOOL": 200.0, "FERTILIZER": 100.0,
}
MARKET_T = {
    "WHEAT": 400.0, "CARROT": 450.0, "TOMATO": 200.0,
    "STRAWBERRY": 100.0, "MELON": 300.0, "EGG": 332.0,
    "MILK": 122.0, "WOOL": 105.0, "FERTILIZER": 200.0,
}
PRODUCT_FROM_ANIMAL = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}

HEAD_SIZES = (2, 3, 3, 3, 3, 3)
SCALE_VALUES = (0.5, 1.0, 1.5)
DEFAULT_MACRO = np.asarray([0, 1, 1, 1, 0, 0], dtype=np.int16)
HIDDEN_SIZE = 64


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _feature_names():
    names = ["day", "remaining", "hour", "player", "route_decision"]
    for side in ("self", "opponent"):
        names.extend(
            f"{side}.{name}" for name in (
                "money", "money_delta", "unlocked", "hands", "hires",
                "farmer_x", "farmer_y", "empty", "locked", "weeds",
            )
        )
        for crop in CROPS:
            names.extend(
                f"{side}.{crop}.{name}"
                for name in ("count", "yield", "risk", "watered")
            )
        for animal in ANIMALS:
            names.extend(
                f"{side}.{animal}.{name}"
                for name in ("count", "yield", "risk", "fed")
            )
    names.extend(f"private.shed.{item}" for item in INVENTORY_ITEMS)
    names.extend(f"private.seed.{item}" for item in CROPS)
    names.extend(f"private.carried.{item}" for item in INVENTORY_ITEMS)
    names.append("private.free_capacity")
    for item in PRODUCTS:
        names.extend(
            f"market.{item}.{name}"
            for name in ("inventory", "price", "inventory_delta", "price_delta")
        )
    names.extend(f"town.{shop}" for shop in SHOPS)
    names.extend(("previous.route.low", "previous.route.high"))
    for head in ("staple", "premium", "animal", "priority", "wheat_reserve"):
        names.extend(f"previous.{head}.{index}" for index in range(3))
    return tuple(names)


FEATURE_NAMES = _feature_names()
FEATURE_DIM = len(FEATURE_NAMES)


def teacher_route(obs):
    """Return the frozen v2 production expert for the observed shop layout."""
    shops = tuple(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])
    dominated = len(shops) >= 2 and shops[0] == "ICE_CREAM_SHOP" and shops[1] == "YARN_STORE"
    return 1 if "YARN_STORE" in shops and not dominated else 0


def default_macro(obs):
    action = DEFAULT_MACRO.copy()
    if int(_get(obs, "day", 0) or 0) >= 7:
        action[0] = teacher_route(obs)
    return action


def _farm_features(target, prefix, farm, previous_money):
    money = float(_get(farm, "money", 0.0) or 0.0)
    target[f"{prefix}.money"] = money / 200000.0
    target[f"{prefix}.money_delta"] = (money - float(previous_money or money)) / 50000.0
    target[f"{prefix}.unlocked"] = len(_get(farm, "unlocked_quadrants", []) or []) / 4.0
    target[f"{prefix}.hands"] = len(_get(farm, "hands", []) or []) / 16.0
    target[f"{prefix}.hires"] = float(_get(farm, "hires_today", 0) or 0) / 16.0
    farmer = list(_get(farm, "farmer", [4, 4]) or [4, 4])
    target[f"{prefix}.farmer_x"] = float(farmer[0]) / 9.0
    target[f"{prefix}.farmer_y"] = float(farmer[1]) / 9.0
    counts = {crop: [0, 0, 0, 0] for crop in CROPS}
    animal_counts = {animal: [0, 0, 0, 0] for animal in ANIMALS}
    empty = locked = weeds = 0
    for row in list(_get(farm, "tiles", []) or []):
        for tile in list(row or []):
            if tile is None:
                empty += 1
                continue
            if tile == "LOCKED":
                locked += 1
                continue
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "WEED":
                weeds += 1
            crop = tile.get("crop")
            if crop in counts:
                values = counts[crop]
                values[0] += 1
                values[1] += max(0, int(tile.get("yield_units", 0) or 0))
                values[2] += int(tile.get("consecutive_unwatered", 0) or 0) >= 1 and not tile.get("watered_today", False)
                values[3] += bool(tile.get("watered_today", False))
            animal = tile.get("animal")
            if animal in animal_counts:
                values = animal_counts[animal]
                values[0] += 1
                values[1] += max(0, int(tile.get("yield_units", 0) or 0))
                values[2] += int(tile.get("consecutive_unfed", 0) or 0) >= 1 and not tile.get("fed_today", False)
                values[3] += bool(tile.get("fed_today", False))
    target[f"{prefix}.empty"] = empty / 100.0
    target[f"{prefix}.locked"] = locked / 100.0
    target[f"{prefix}.weeds"] = weeds / 25.0
    for crop, values in counts.items():
        for name, value, scale in zip(("count", "yield", "risk", "watered"), values, (25.0, 100.0, 25.0, 25.0)):
            target[f"{prefix}.{crop}.{name}"] = float(value) / scale
    for animal, values in animal_counts.items():
        for name, value, scale in zip(("count", "yield", "risk", "fed"), values, (25.0, 100.0, 25.0, 25.0)):
            target[f"{prefix}.{animal}.{name}"] = float(value) / scale


def encode_observation(obs, history=None, previous_macro=None):
    """Encode an observation into the stable daily macro feature schema."""
    history = history or {}
    previous_macro = np.asarray(previous_macro if previous_macro is not None else DEFAULT_MACRO)
    player = int(_get(obs, "player", 0) or 0)
    farms = list(_get(obs, "farms", []) or [])
    own = farms[player]
    opponent = farms[1 - player]
    day = int(_get(obs, "day", 0) or 0)
    hour = int(_get(obs, "hour", 0) or 0)
    values = {
        "day": day / 29.0,
        "remaining": (29 - min(day, 29)) / 29.0,
        "hour": hour / 23.0,
        "player": float(player),
        "route_decision": float(day == 7 and hour == 0),
    }
    previous_money = history.get("money", [None, None])
    _farm_features(values, "self", own, previous_money[player] if len(previous_money) > player else None)
    _farm_features(values, "opponent", opponent, previous_money[1 - player] if len(previous_money) > 1 - player else None)

    private = _get(obs, "private", {}) or {}
    shed = dict(_get(private, "shed", {}) or {})
    seeds = dict(_get(private, "seeds", {}) or {})
    inventories = [dict(item or {}) for item in list(_get(private, "inventories", []) or [])]
    carried = {item: sum(max(0, int(inv.get(item, 0) or 0)) for inv in inventories) for item in INVENTORY_ITEMS}
    for item in INVENTORY_ITEMS:
        values[f"private.shed.{item}"] = max(0, int(shed.get(item, 0) or 0)) / 100.0
        values[f"private.carried.{item}"] = carried[item] / 100.0
    for crop in CROPS:
        values[f"private.seed.{crop}"] = max(0, int(seeds.get(crop, 0) or 0)) / 50.0
    used = sum(max(0, int(shed.get(item, 0) or 0)) for item in INVENTORY_ITEMS)
    values["private.free_capacity"] = max(0, 100 - used) / 100.0

    market = _get(obs, "market", {}) or {}
    inventory = dict(_get(market, "inventory", {}) or {})
    prices = dict(_get(market, "prices", {}) or {})
    old_inventory = dict(history.get("market_inventory", {}) or {})
    old_prices = dict(history.get("market_prices", {}) or {})
    for item in PRODUCTS:
        inv = float(inventory.get(item, 10000) or 10000)
        price = float(prices.get(item, BASE_PRICES[item]) or BASE_PRICES[item])
        scale = MARKET_T[item]
        values[f"market.{item}.inventory"] = (inv - 10000.0) / scale
        values[f"market.{item}.price"] = price / BASE_PRICES[item]
        values[f"market.{item}.inventory_delta"] = (inv - float(old_inventory.get(item, inv))) / scale
        values[f"market.{item}.price_delta"] = (price - float(old_prices.get(item, price))) / BASE_PRICES[item]

    shops = list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])
    for shop in SHOPS:
        values[f"town.{shop}"] = shops.count(shop) / 8.0

    route = int(previous_macro[0]) if len(previous_macro) else 0
    values["previous.route.low"] = float(route == 0)
    values["previous.route.high"] = float(route == 1)
    for offset, head in enumerate(("staple", "premium", "animal", "priority", "wheat_reserve"), start=1):
        selected = int(previous_macro[offset]) if len(previous_macro) > offset else int(DEFAULT_MACRO[offset])
        for index in range(3):
            values[f"previous.{head}.{index}"] = float(selected == index)

    vector = np.asarray([values.get(name, 0.0) for name in FEATURE_NAMES], dtype=np.float32)
    if vector.shape != (FEATURE_DIM,) or not np.all(np.isfinite(vector)):
        raise ValueError("invalid macro feature vector")
    return np.clip(vector, -5.0, 5.0)


def update_history(obs, macro):
    farms = list(_get(obs, "farms", []) or [])
    market = _get(obs, "market", {}) or {}
    return {
        "money": [float(_get(farm, "money", 0.0) or 0.0) for farm in farms],
        "market_inventory": dict(_get(market, "inventory", {}) or {}),
        "market_prices": dict(_get(market, "prices", {}) or {}),
        "macro": np.asarray(macro, dtype=np.int16),
    }


def liquid_net_worth(obs):
    """Observable potential used for reward shaping; not used by the agent."""
    player = int(_get(obs, "player", 0) or 0)
    farms = list(_get(obs, "farms", []) or [])
    private = _get(obs, "private", {}) or {}
    prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
    quantities = {item: max(0, int(dict(_get(private, "shed", {}) or {}).get(item, 0) or 0)) for item in PRODUCTS}
    for inventory in list(_get(private, "inventories", []) or []):
        for item in PRODUCTS:
            quantities[item] += max(0, int(dict(inventory or {}).get(item, 0) or 0))
    own = farms[player]
    for row in list(_get(own, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, dict):
                continue
            item = tile.get("crop") or PRODUCT_FROM_ANIMAL.get(tile.get("animal"))
            if item in quantities:
                quantities[item] += max(0, int(tile.get("yield_units", 0) or 0))
    total = float(_get(own, "money", 0.0) or 0.0)
    total += sum(quantities[item] * float(prices.get(item, BASE_PRICES[item]) or 0.0) for item in PRODUCTS)
    opponent_money = float(_get(farms[1 - player], "money", 0.0) or 0.0)
    return total, opponent_money


def potential(obs):
    own, opponent = liquid_net_worth(obs)
    return 0.05 * math.tanh((own - opponent) / 100000.0)


class NumpyPolicy:
    def __init__(self, path=MODEL_FILE):
        data = np.load(path, allow_pickle=False)
        schema = str(data["schema"].item())
        feature_dim = int(data["feature_dim"].item())
        if schema != SCHEMA_VERSION or feature_dim != FEATURE_DIM:
            raise ValueError(f"incompatible policy schema: {schema}/{feature_dim}")
        self.arrays = {key: np.asarray(data[key], dtype=np.float32) for key in data.files if key not in {"schema", "feature_dim"}}
        required = {
            "enc_w", "enc_b", "z_x_w", "z_x_b", "z_h_w", "r_x_w", "r_x_b", "r_h_w",
            "n_x_w", "n_x_b", "n_h_w", "mlp_w", "mlp_b", "value_w", "value_b",
            *(f"head_{index}_{suffix}" for index in range(len(HEAD_SIZES)) for suffix in ("w", "b")),
        }
        missing = required.difference(self.arrays)
        if missing:
            raise ValueError(f"missing policy arrays: {sorted(missing)}")

    @staticmethod
    def _sigmoid(value):
        return 1.0 / (1.0 + np.exp(-np.clip(value, -30.0, 30.0)))

    def step(self, features, hidden):
        a = self.arrays
        features = np.asarray(features, dtype=np.float32)
        hidden = np.asarray(hidden, dtype=np.float32)
        encoded = np.tanh(features @ a["enc_w"] + a["enc_b"])
        z = self._sigmoid(encoded @ a["z_x_w"] + a["z_x_b"] + hidden @ a["z_h_w"])
        r = self._sigmoid(encoded @ a["r_x_w"] + a["r_x_b"] + hidden @ a["r_h_w"])
        candidate = np.tanh(encoded @ a["n_x_w"] + a["n_x_b"] + (r * hidden) @ a["n_h_w"])
        next_hidden = z * hidden + (1.0 - z) * candidate
        trunk = np.tanh(next_hidden @ a["mlp_w"] + a["mlp_b"])
        logits = [trunk @ a[f"head_{index}_w"] + a[f"head_{index}_b"] for index in range(len(HEAD_SIZES))]
        value = float((trunk @ a["value_w"] + a["value_b"]).reshape(-1)[0])
        return logits, value, next_hidden.astype(np.float32)

    def act(self, features, hidden, stochastic=False, rng=None, route_enabled=True):
        logits, value, next_hidden = self.step(features, hidden)
        rng = rng or np.random.default_rng()
        actions = []
        log_probability = 0.0
        for index, raw in enumerate(logits):
            values = np.asarray(raw, dtype=np.float64)
            values -= values.max()
            probabilities = np.exp(values)
            probabilities /= probabilities.sum()
            selected = int(rng.choice(len(probabilities), p=probabilities)) if stochastic else int(np.argmax(probabilities))
            if index == 0 and not route_enabled:
                selected = 0
            else:
                log_probability += math.log(max(1e-12, float(probabilities[selected])))
            actions.append(selected)
        return np.asarray(actions, dtype=np.int16), float(log_probability), value, next_hidden, logits


def _copy_action(action):
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in list(action.get("hands") or [])],
        "market": [list(order) for order in list(action.get("market") or [])],
    }


def _opponent_overlap(obs, item):
    player = int(_get(obs, "player", 0) or 0)
    farms = list(_get(obs, "farms", []) or [])
    opponent = farms[1 - player]
    score = 0
    for row in list(_get(opponent, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, dict):
                continue
            if tile.get("crop") == item or PRODUCT_FROM_ANIMAL.get(tile.get("animal")) == item:
                score += 1
    return score


def apply_macro(obs, base_action, macro, step=None):
    """Apply conservative market residuals; default macro is byte-for-byte no-op."""
    macro = np.asarray(macro, dtype=np.int16)
    step = int(_get(obs, "step", 0) or 0) if step is None else int(step)
    if step >= 716 or np.array_equal(macro[1:], DEFAULT_MACRO[1:]):
        return base_action
    if macro.shape != (6,) or any(not 0 <= int(value) < HEAD_SIZES[index] for index, value in enumerate(macro)):
        raise ValueError("invalid macro action")
    action = _copy_action(base_action)
    projected = dict(base_agent._projected_shed(obs, action))
    group_scale = {}
    for item in ("WHEAT", "CARROT", "TOMATO"):
        group_scale[item] = SCALE_VALUES[int(macro[1])]
    for item in ("STRAWBERRY", "MELON"):
        group_scale[item] = SCALE_VALUES[int(macro[2])]
    for item in ("EGG", "MILK", "WOOL"):
        group_scale[item] = SCALE_VALUES[int(macro[3])]
    remaining = {item: max(0, int(projected.get(item, 0) or 0)) for item in PRODUCTS}
    wheat_reserve = (0, 4, 8)[int(macro[5])]
    for order in action["market"]:
        if len(order) < 3 or order[0] != "SELL" or order[1] not in group_scale:
            continue
        item = str(order[1])
        available = remaining[item] - (wheat_reserve if item == "WHEAT" else 0)
        requested = max(0, int(order[2] or 0))
        quantity = min(max(0, available), max(0, int(round(requested * group_scale[item]))))
        order[2] = quantity
        remaining[item] = max(0, remaining[item] - quantity)

    priority = int(macro[4])
    if priority:
        market = action["market"]
        sell_indices = [index for index, order in enumerate(market) if len(order) >= 3 and order[0] == "SELL"]
        sells = [market[index] for index in sell_indices]
        prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
        if priority == 1:
            sells.sort(key=lambda order: float(prices.get(order[1], 0) or 0) / BASE_PRICES.get(order[1], 1.0), reverse=True)
        else:
            sells.sort(key=lambda order: (_opponent_overlap(obs, str(order[1])), float(prices.get(order[1], 0) or 0)), reverse=True)
        for index, order in zip(sell_indices, sells):
            market[index] = order
    action["market"] = action["market"][:10]
    return action


_POLICY = None
_POLICY_ERROR = None
_GAME = {
    0: {},
    1: {},
}


def _load_policy():
    global _POLICY, _POLICY_ERROR
    if _POLICY is None and _POLICY_ERROR is None:
        try:
            _POLICY = NumpyPolicy(MODEL_FILE)
        except Exception as error:  # submission must remain playable
            _POLICY_ERROR = repr(error)
    return _POLICY


def _reset_game(player):
    _GAME[player] = {
        "last_step": -1,
        "hidden": np.zeros(HIDDEN_SIZE, dtype=np.float32),
        "macro": DEFAULT_MACRO.copy(),
        "route": None,
        "history": {},
        "fallback": False,
    }
    return _GAME[player]


def model_status():
    return {"loaded": _POLICY is not None, "error": _POLICY_ERROR, "feature_dim": FEATURE_DIM}


def _base_action(obs, route):
    if route is None:
        return base_agent.agent(obs)
    base_agent._ACTIONS = base_agent._HIGH_ROUTE_ACTIONS if int(route) == 1 else base_agent._LOW_ROUTE_ACTIONS
    return base_agent._CORE_AGENT(obs)


def agent(obs):
    player = int(_get(obs, "player", 0) or 0)
    step = int(_get(obs, "step", 0) or 0)
    day = int(_get(obs, "day", step // 24) or 0)
    hour = int(_get(obs, "hour", step % 24) or 0)
    state = _GAME[player]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = _reset_game(player)
    state["last_step"] = step
    policy = _load_policy()
    if policy is None:
        state["fallback"] = True

    try:
        if not state["fallback"] and hour == 0:
            features = encode_observation(obs, state["history"], state["macro"])
            sampled, _, _, hidden, _ = policy.act(
                features,
                state["hidden"],
                stochastic=False,
                route_enabled=(day == 7),
            )
            if day < 7:
                sampled[0] = 0
            elif day == 7:
                state["route"] = int(sampled[0])
            else:
                sampled[0] = int(state["route"] if state["route"] is not None else teacher_route(obs))
            state["hidden"] = hidden
            state["macro"] = sampled
            state["history"] = update_history(obs, sampled)
        base = _base_action(obs, state.get("route"))
        if state["fallback"]:
            return base
        return apply_macro(obs, base, state["macro"], step)
    except Exception:
        state["fallback"] = True
        return _base_action(obs, state.get("route"))


__version__ = "bc-ppo-hybrid-v3"
