"""State-conditioned full action codec for V113.

The codec is policy-free: it enumerates legal Kaggriculture primitives and
converts neural tokens to executable actions.  It never calls another agent.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping, Sequence


CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
ITEMS = PRODUCTS + ANIMALS
MOVES = ("NORTH", "SOUTH", "EAST", "WEST")
UNIT_SIMPLE = (
    "PASS", *MOVES, "DROP", "WATER", "HARVEST", "FERTILIZE", "DIG",
    "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
)
UNIT_TOKENS = UNIT_SIMPLE + tuple(f"PLANT:{item}" for item in CROPS) + tuple(
    f"PICKUP:{item}" for item in ITEMS
) + tuple(f"PLACE:{item}" for item in ITEMS)
UNIT_INDEX = {name: index for index, name in enumerate(UNIT_TOKENS)}

MARKET_TOKENS = (
    "STOP", "HIRE", "BUY_LAND",
    *(f"BUY_SEED:{item}" for item in CROPS),
    "BUY_PRODUCT:WHEAT", "BUY_PRODUCT:FERTILIZER",
    *(f"BUY_ANIMAL:{item}" for item in ANIMALS),
    *(f"SELL:{item}" for item in PRODUCTS),
)
MARKET_INDEX = {name: index for index, name in enumerate(MARKET_TOKENS)}
MAX_MARKET_SLOTS = 10
MAX_QUANTITY = 100
MAX_QUANTITY_TOKEN = MAX_QUANTITY + 1
QUANTITY_DIM = MAX_QUANTITY + 2

SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND_PRICES = (1000, 2000, 4000)
BASE_PRICES = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
CROP_FIRST_YIELD_DAY = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
SHED_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}


def get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def seat(obs: Any) -> int:
    return 1 if int(get(obs, "player", 0) or 0) == 1 else 0


def own_farm(obs: Any) -> Mapping[str, Any]:
    farms = list(get(obs, "farms", []) or [])
    player = seat(obs)
    return farms[player] if player < len(farms) else {}


def private(obs: Any) -> Mapping[str, Any]:
    return get(obs, "private", {}) or {}


def unit_count(obs: Any) -> int:
    return 1 + len(get(own_farm(obs), "hands", []) or [])


def unit_position(obs: Any, unit_index: int) -> tuple[int, int]:
    farm = own_farm(obs)
    position = get(farm, "farmer", [0, 0]) if unit_index == 0 else list(get(farm, "hands", []) or [])[unit_index - 1]
    return int(position[0]), int(position[1])


def unit_inventory(obs: Any, unit_index: int) -> Mapping[str, Any]:
    inventories = list(get(private(obs), "inventories", []) or [])
    return inventories[unit_index] if unit_index < len(inventories) else {}


def _tile(obs: Any, x: int, y: int) -> Any:
    tiles = list(get(own_farm(obs), "tiles", []) or [])
    return tiles[y][x] if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]) else "LOCKED"


def _is_shed_adjacent(x: int, y: int) -> bool:
    return (x, y) in SHED_ACCESS


def unit_legal_mask(obs: Any, unit_index: int) -> list[bool]:
    mask = [False] * len(UNIT_TOKENS)
    mask[UNIT_INDEX["PASS"]] = True
    farm = own_farm(obs)
    board_size = len(get(farm, "tiles", []) or []) or 10
    x, y = unit_position(obs, unit_index)
    for move, (dx, dy) in zip(MOVES, ((0, -1), (0, 1), (1, 0), (-1, 0))):
        mask[UNIT_INDEX[move]] = 0 <= x + dx < board_size and 0 <= y + dy < board_size
    inv = unit_inventory(obs, unit_index)
    own_private = private(obs)
    shed = get(own_private, "shed", {}) or {}
    shed_room = max(0, 100 - sum(max(0, int(value or 0)) for value in shed.values()))
    adjacent = _is_shed_adjacent(x, y)
    mask[UNIT_INDEX["DROP"]] = adjacent and shed_room > 0 and any(int(value or 0) > 0 for value in inv.values())
    for item in ITEMS:
        mask[UNIT_INDEX[f"PICKUP:{item}"]] = adjacent and int(get(shed, item, 0) or 0) > 0
        can_place_shed = adjacent and int(get(inv, item, 0) or 0) > 0 and shed_room > 0
        tile = _tile(obs, x, y)
        can_place_animal = bool(
            item in ANIMALS and isinstance(tile, Mapping)
            and get(tile, "kind", "") == ("COOP" if item == "GOOSE" else "PASTURE")
            and not get(tile, "animal", None) and int(get(inv, item, 0) or 0) > 0
        )
        mask[UNIT_INDEX[f"PLACE:{item}"]] = can_place_shed or can_place_animal
    tile = _tile(obs, x, y)
    if tile == "LOCKED":
        return mask
    if tile is None:
        seeds = get(own_private, "seeds", {}) or {}
        for crop in CROPS:
            mask[UNIT_INDEX[f"PLANT:{crop}"]] = int(get(seeds, crop, 0) or 0) > 0
        mask[UNIT_INDEX["BUILD_COOP"]] = True
        mask[UNIT_INDEX["BUILD_PASTURE"]] = True
    if tile is not None and not (isinstance(tile, Mapping) and get(tile, "animal", None)):
        mask[UNIT_INDEX["DIG"]] = True
    if isinstance(tile, Mapping) and get(tile, "kind", "") == "PLANT":
        mask[UNIT_INDEX["WATER"]] = not bool(get(tile, "watered_today", False))
        crop = str(get(tile, "crop", ""))
        day = int(get(obs, "step", 0) or 0) // 24
        mature = day - int(get(tile, "planted_day", day) or 0) >= CROP_FIRST_YIELD_DAY.get(crop, 10**9)
        mask[UNIT_INDEX["HARVEST"]] = mature and int(get(tile, "yield_units", 0) or 0) > 0
        mask[UNIT_INDEX["FERTILIZE"]] = int(get(inv, "FERTILIZER", 0) or 0) > 0
    if isinstance(tile, Mapping) and get(tile, "animal", None):
        mask[UNIT_INDEX["HARVEST"]] = int(get(tile, "yield_units", 0) or 0) > 0
        mask[UNIT_INDEX["FEED"]] = not bool(get(tile, "fed_today", False)) and int(get(inv, "WHEAT", 0) or 0) > 0
        mask[UNIT_INDEX["CARE"]] = not bool(get(tile, "cared_today", False))
        mask[UNIT_INDEX["COLLECT_FERTILIZER"]] = bool(get(tile, "fertilizer_available", False))
    return mask


def _quantity_token(raw: Any) -> int:
    try:
        quantity = max(1, int(raw))
    except (TypeError, ValueError):
        quantity = 1
    return quantity if quantity <= MAX_QUANTITY else MAX_QUANTITY_TOKEN


def _resolve_quantity(token: int, feasible: int) -> int:
    feasible = max(0, int(feasible))
    if int(token) == MAX_QUANTITY_TOKEN:
        return feasible
    return min(feasible, max(1, int(token)))


def quantity_candidate_mask(feasible: int) -> list[bool]:
    """Expose every supervised quantity that the interpreter can execute."""
    feasible = max(0, int(feasible))
    mask = [False] * QUANTITY_DIM
    if feasible <= 0:
        mask[0] = True
        return mask
    for value in range(1, min(feasible, MAX_QUANTITY) + 1):
        mask[value] = True
    if feasible > MAX_QUANTITY:
        mask[MAX_QUANTITY_TOKEN] = True
    return mask


def unit_quantity_mask(obs: Any, unit_index: int, token: int) -> list[bool]:
    if not 0 <= int(token) < len(UNIT_TOKENS):
        return quantity_candidate_mask(0)
    name = UNIT_TOKENS[int(token)]
    if ":" not in name:
        return quantity_candidate_mask(0)
    op, item = name.split(":", 1)
    if op == "PICKUP":
        feasible = int(get(get(private(obs), "shed", {}) or {}, item, 0) or 0)
    elif op == "PLACE":
        feasible = int(get(unit_inventory(obs, unit_index), item, 0) or 0)
        tile = _tile(obs, *unit_position(obs, unit_index))
        if item in ANIMALS and isinstance(tile, Mapping) and get(tile, "kind", "") == ("COOP" if item == "GOOSE" else "PASTURE"):
            feasible = min(1, feasible)
    else:
        feasible = 0
    return quantity_candidate_mask(feasible)


def unit_token(order: Sequence[Any]) -> tuple[int, int, bool]:
    if not isinstance(order, Sequence) or isinstance(order, (str, bytes)) or not order:
        return UNIT_INDEX["PASS"], 0, False
    op = str(order[0])
    name = op
    if op in ("PLANT", "PICKUP", "PLACE"):
        if len(order) < 2:
            return UNIT_INDEX["PASS"], 0, False
        name = f"{op}:{order[1]}"
    if name not in UNIT_INDEX:
        return UNIT_INDEX["PASS"], 0, False
    quantity = _quantity_token(order[2] if len(order) >= 3 else 1) if op in ("PICKUP", "PLACE") else 0
    return UNIT_INDEX[name], quantity, True


def decode_unit(obs: Any, unit_index: int, token: int, quantity_token: int = 1) -> list[Any]:
    mask = unit_legal_mask(obs, unit_index)
    if not 0 <= int(token) < len(mask) or not mask[int(token)]:
        return ["PASS"]
    name = UNIT_TOKENS[int(token)]
    if ":" not in name:
        return [name]
    op, item = name.split(":", 1)
    if op == "PLANT":
        return [op, item]
    available = int(get(private(obs).get("shed", {}), item, 0) or 0) if op == "PICKUP" else int(get(unit_inventory(obs, unit_index), item, 0) or 0)
    quantity = _resolve_quantity(quantity_token, available)
    return [op, item, quantity] if quantity > 0 else ["PASS"]


def market_token(order: Sequence[Any]) -> tuple[int, int, bool]:
    if not isinstance(order, Sequence) or isinstance(order, (str, bytes)) or not order:
        return MARKET_INDEX["STOP"], 0, False
    op = str(order[0])
    name = op
    if op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"):
        if len(order) < 2:
            return MARKET_INDEX["STOP"], 0, False
        name = f"{op}:{order[1]}"
    if name not in MARKET_INDEX:
        return MARKET_INDEX["STOP"], 0, False
    quantity = _quantity_token(order[2] if len(order) >= 3 else 1) if op not in ("HIRE", "BUY_LAND") else 0
    return MARKET_INDEX[name], quantity, True


def _fib(index: int) -> int:
    a, b = 1, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def market_shadow(obs: Any) -> dict[str, Any]:
    farm = own_farm(obs)
    own_private = private(obs)
    return {
        "money": float(get(farm, "money", 0.0) or 0.0),
        "hires": int(get(farm, "hires_today", 0) or 0),
        "units": unit_count(obs),
        "land": len(get(farm, "unlocked_quadrants", []) or []),
        "shed": {item: int(get(get(own_private, "shed", {}) or {}, item, 0) or 0) for item in ITEMS},
        "seeds": {item: int(get(get(own_private, "seeds", {}) or {}, item, 0) or 0) for item in CROPS},
        "prices": {item: int(get(get(get(obs, "market", {}) or {}, "prices", {}) or {}, item, BASE_PRICES[item]) or BASE_PRICES[item]) for item in PRODUCTS},
    }


def project_unit_orders(obs: Any, unit_orders: Sequence[Sequence[Any]], shadow: dict[str, Any]) -> None:
    """Project same-turn deposits that execute before the market queue.

    Kaggriculture applies all unit actions before market orders.  A policy may
    therefore PLACE/DROP into its shed and sell the deposited goods in the same
    action.  This projection is deliberately limited to deterministic shed
    transfers; other unit effects remain owned by the official interpreter.
    """
    room = max(0, 100 - sum(max(0, int(value)) for value in shadow["shed"].values()))
    for unit_index, order in enumerate(unit_orders):
        if not isinstance(order, Sequence) or isinstance(order, (str, bytes)) or not order:
            continue
        x, y = unit_position(obs, unit_index)
        if not _is_shed_adjacent(x, y):
            continue
        inventory = {str(key): max(0, int(value or 0)) for key, value in unit_inventory(obs, unit_index).items()}
        op = str(order[0])
        if op == "DROP":
            for item, available in inventory.items():
                take = min(available, room)
                if take > 0:
                    shadow["shed"][item] = int(shadow["shed"].get(item, 0)) + take
                    room -= take
        elif op == "PLACE" and len(order) >= 2:
            item = str(order[1])
            requested = int(order[2]) if len(order) >= 3 else 1
            take = min(max(0, requested), inventory.get(item, 0), room)
            if take > 0:
                shadow["shed"][item] = int(shadow["shed"].get(item, 0)) + take
                room -= take


def market_legal_mask(shadow: Mapping[str, Any]) -> list[bool]:
    mask = [False] * len(MARKET_TOKENS)
    mask[MARKET_INDEX["STOP"]] = True
    money = float(shadow["money"])
    hires = int(shadow["hires"])
    land = int(shadow["land"])
    shed = shadow["shed"]
    room = max(0, 100 - sum(max(0, int(value)) for value in shed.values()))
    # The neural state contract represents at most 16 controllable units.
    # Creating an unrepresented hand would make the emitted joint action
    # incomplete, so capacity is part of action safety rather than strategy.
    mask[MARKET_INDEX["HIRE"]] = int(shadow.get("units", 1)) < 16 and money >= _fib(hires)
    extra = land - 1
    mask[MARKET_INDEX["BUY_LAND"]] = 0 <= extra < len(LAND_PRICES) and money >= LAND_PRICES[extra]
    for crop in CROPS:
        mask[MARKET_INDEX[f"BUY_SEED:{crop}"]] = money >= SEED_COST[crop]
    for item in ("WHEAT", "FERTILIZER"):
        mask[MARKET_INDEX[f"BUY_PRODUCT:{item}"]] = room > 0 and money >= int(shadow["prices"][item])
    for animal in ANIMALS:
        mask[MARKET_INDEX[f"BUY_ANIMAL:{animal}"]] = room > 0 and money >= ANIMAL_COST[animal]
    for item in PRODUCTS:
        mask[MARKET_INDEX[f"SELL:{item}"]] = int(shed.get(item, 0)) > 0
    return mask


def market_quantity_mask(shadow: Mapping[str, Any], token: int) -> list[bool]:
    if not 0 <= int(token) < len(MARKET_TOKENS):
        return quantity_candidate_mask(0)
    name = MARKET_TOKENS[int(token)]
    if name in {"STOP", "HIRE", "BUY_LAND"}:
        return quantity_candidate_mask(0)
    op, item = name.split(":", 1)
    money = float(shadow["money"])
    room = max(0, 100 - sum(max(0, int(value)) for value in shadow["shed"].values()))
    if op == "SELL":
        feasible = int(shadow["shed"].get(item, 0))
    elif op == "BUY_SEED":
        feasible = int(money // SEED_COST[item])
    elif op == "BUY_PRODUCT":
        feasible = min(room, int(money // max(1, int(shadow["prices"][item]))))
    elif op == "BUY_ANIMAL":
        feasible = min(room, int(money // ANIMAL_COST[item]))
    else:
        feasible = 0
    return quantity_candidate_mask(feasible)


def apply_market_token(shadow: dict[str, Any], token: int, quantity_token: int) -> list[Any] | None:
    mask = market_legal_mask(shadow)
    if not 0 <= int(token) < len(mask) or not mask[int(token)]:
        return None
    name = MARKET_TOKENS[int(token)]
    if name == "STOP":
        return None
    if name == "HIRE":
        cost = _fib(shadow["hires"])
        shadow["money"] -= cost
        shadow["hires"] += 1
        shadow["units"] = int(shadow.get("units", 1)) + 1
        return ["HIRE"]
    if name == "BUY_LAND":
        cost = LAND_PRICES[shadow["land"] - 1]
        shadow["money"] -= cost
        shadow["land"] += 1
        return ["BUY_LAND"]
    op, item = name.split(":", 1)
    room = max(0, 100 - sum(max(0, int(value)) for value in shadow["shed"].values()))
    if op == "SELL":
        feasible = int(shadow["shed"].get(item, 0))
        quantity = _resolve_quantity(quantity_token, feasible)
        shadow["shed"][item] -= quantity
        shadow["money"] += quantity * int(shadow["prices"][item])
    elif op == "BUY_SEED":
        feasible = int(shadow["money"] // SEED_COST[item])
        quantity = _resolve_quantity(quantity_token, feasible)
        shadow["money"] -= quantity * SEED_COST[item]
        shadow["seeds"][item] += quantity
    elif op == "BUY_PRODUCT":
        price = int(shadow["prices"][item])
        feasible = min(room, int(shadow["money"] // max(1, price)))
        quantity = _resolve_quantity(quantity_token, feasible)
        shadow["money"] -= quantity * price
        shadow["shed"][item] += quantity
    elif op == "BUY_ANIMAL":
        feasible = min(room, int(shadow["money"] // ANIMAL_COST[item]))
        quantity = _resolve_quantity(quantity_token, feasible)
        shadow["money"] -= quantity * ANIMAL_COST[item]
        shadow["shed"][item] += quantity
    else:
        return None
    return [op, item, quantity] if quantity > 0 else None


def encode_action(obs: Any, action: Mapping[str, Any]) -> dict[str, Any]:
    orders = [list(get(action, "farmer", ["PASS"]) or ["PASS"])] + [
        list(order or ["PASS"]) for order in list(get(action, "hands", []) or [])
    ]
    count = unit_count(obs)
    orders = (orders + [["PASS"]] * count)[:count]
    unit_rows = [unit_token(order) for order in orders]
    market_orders = list(get(action, "market", []) or [])[:MAX_MARKET_SLOTS]
    market_rows = [market_token(order) for order in market_orders]
    while len(market_rows) < MAX_MARKET_SLOTS:
        market_rows.append((MARKET_INDEX["STOP"], 0, True))
    return {
        "unit_tokens": [row[0] for row in unit_rows],
        "unit_quantities": [row[1] for row in unit_rows],
        "unit_known": [row[2] for row in unit_rows],
        "market_tokens": [row[0] for row in market_rows],
        "market_quantities": [row[1] for row in market_rows],
        "market_known": [row[2] for row in market_rows],
    }


def decode_action(obs: Any, encoded: Mapping[str, Any]) -> dict[str, Any]:
    count = unit_count(obs)
    tokens = list(get(encoded, "unit_tokens", []) or [])
    quantities = list(get(encoded, "unit_quantities", []) or [])
    unit_orders = [
        decode_unit(obs, index, tokens[index] if index < len(tokens) else UNIT_INDEX["PASS"], quantities[index] if index < len(quantities) else 1)
        for index in range(count)
    ]
    market_tokens = list(get(encoded, "market_tokens", []) or [])[:MAX_MARKET_SLOTS]
    market_quantities = list(get(encoded, "market_quantities", []) or [])[:MAX_MARKET_SLOTS]
    shadow = market_shadow(obs)
    project_unit_orders(obs, unit_orders, shadow)
    market: list[list[Any]] = []
    for index, token in enumerate(market_tokens):
        if int(token) == MARKET_INDEX["STOP"]:
            break
        order = apply_market_token(shadow, int(token), int(market_quantities[index] if index < len(market_quantities) else 1))
        if order is not None:
            market.append(order)
    return {"farmer": unit_orders[0], "hands": unit_orders[1:], "market": market}


def functional_expert_label(action: Mapping[str, Any], step: int) -> int:
    """Offline initialization label for six learnable experts, not a runtime rule."""
    unit_ops = [str((get(action, "farmer", ["PASS"]) or ["PASS"])[0])]
    unit_ops += [str((order or ["PASS"])[0]) for order in list(get(action, "hands", []) or [])]
    market_ops = [str((order or ["STOP"])[0]) for order in list(get(action, "market", []) or [])]
    if int(step) >= 672 or "SELL" in market_ops:
        return 5 if int(step) >= 672 else 3
    if any(op in {"FEED", "CARE", "COLLECT_FERTILIZER", "BUILD_COOP", "BUILD_PASTURE"} for op in unit_ops) or "BUY_ANIMAL" in market_ops:
        return 1
    if any(op in {"PLANT", "WATER", "HARVEST", "FERTILIZE"} for op in unit_ops):
        return 0
    if any(op in {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT"} for op in market_ops):
        return 4
    if any(op in {*MOVES, "PICKUP", "PLACE", "DROP", "DIG"} for op in unit_ops):
        return 2
    return 4


def functional_unit_expert_label(action: Mapping[str, Any], step: int) -> int:
    """Teacher-independent unit role used to initialize action MoE experts.

    The label is derived only from the canonical action and public game step;
    teacher identity is deliberately excluded so the runtime Router can infer
    the role from observable state rather than memorize a hidden teacher id.
    """
    if int(step) >= 671:
        return 5
    unit_ops = [str((get(action, "farmer", ["PASS"]) or ["PASS"])[0])]
    unit_ops += [
        str((order or ["PASS"])[0])
        for order in list(get(action, "hands", []) or [])
    ]
    if any(op in {
        "FEED", "CARE", "COLLECT_FERTILIZER", "BUILD_COOP", "BUILD_PASTURE",
    } for op in unit_ops):
        return 1
    if any(op in {"PLANT", "WATER", "HARVEST", "FERTILIZE"} for op in unit_ops):
        return 0
    if any(op in {*MOVES, "PICKUP", "PLACE", "DROP", "DIG"} for op in unit_ops):
        return 2
    return 4


def functional_market_expert_label(action: Mapping[str, Any], step: int) -> int:
    """Teacher-independent market role for procurement, selling and terminal play."""
    if int(step) >= 671:
        return 5
    market_ops = [
        str((order or ["STOP"])[0])
        for order in list(get(action, "market", []) or [])
    ]
    if "SELL" in market_ops:
        return 3
    return 4


def normalise_action(action: Mapping[str, Any], expected_hands: int) -> dict[str, Any]:
    farmer = list(get(action, "farmer", ["PASS"]) or ["PASS"])
    hands = [list(order or ["PASS"]) for order in list(get(action, "hands", []) or [])[:expected_hands]]
    hands.extend([["PASS"] for _ in range(expected_hands - len(hands))])
    market = [list(order) for order in list(get(action, "market", []) or [])[:MAX_MARKET_SLOTS] if isinstance(order, Sequence) and not isinstance(order, (str, bytes)) and order]
    return {"farmer": farmer, "hands": hands, "market": market}
