#!/usr/bin/env python3
"""V116 R26: persistent feasible option graph, self-contained rule MoE.

Five experts compile compact aggregate parameters into thirty daily goals.
It stores no recorded action table or coordinate route; every action is
regenerated from the current observation.  R17 keeps R15 settlement safety and
R16's fixed eleven-hand value backbone and R17's deterministic local tours,
then adds persistent confirmed options and feasible-path MCMF scheduling to
R24's observation-independent expert asset slots.  It imports no strategy.
"""

from __future__ import annotations

import math
import copy
import hashlib
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PARAM_SPEC_VERSION = "v116-rc8-param-spec-v1"
HASH_DOMAIN = PARAM_SPEC_VERSION + "\0"
SCHEMA = "v116-r26-persistent-feasible-option-graph-hmoe-v1"
STRATEGY_PARENT = None
MODES = ("router", "fixed_wool", "fixed_dairy_berry", "fixed_tomato_market",
         "fixed_root", "fixed_grain_egg")
PLANT_CUTOFF_HOUR = 18
MAX_PARALLEL_PLANT = 3
DELIVERY_BATCH = 12
FINANCE_DROP_FLOOR = 750
TERMINAL_ASSET_FLOOR = 58
LABOR_HAND_CAP = 11
SETTLEMENT_PURCHASE_CUTOFF_STEP = 696
TOUR_MAX_STEPS = 24
PREEMPTIVE_OPS = frozenset({"WATER", "FEED"})
GROWTH_DEBT_START_DAY = 8
PRIMARY_OPS = frozenset({"PLANT", "HARVEST", "PLACE", "BUILD_PASTURE", "BUILD_COOP"})
SECONDARY_OPS = frozenset({"CARE", "COLLECT_FERTILIZER", "DIG"})


PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 8, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 10, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "first": 10, "max_day": 12, "max_yield": 6, "ongoing": False},
}
NON_ONGOING = frozenset(
    crop for crop, facts in CROPS.items() if not bool(facts["ongoing"])
)
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "max": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "max": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "max": 6, "product": "WOOL"},
}
BASE_PRICE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
              "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200,
              "FERTILIZER": 100}
MARKET_PARAMS = {
    "WHEAT": (25, 400, "sqrt", .80, "log", .20),
    "CARROT": (35, 450, "hinge", 1.00, "sqrt", .70),
    "TOMATO": (60, 200, "hinge", .40, "sqrt", .60),
    "STRAWBERRY": (120, 100, "sqrt", .70, "linear", 1.60),
    "MELON": (250, 300, "log", .20, "sq", 3.60),
    "EGG": (50, 332, "hinge", .40, "log", .20),
    "MILK": (160, 122, "sqrt", .60, "linear", 1.60),
    "WOOL": (200, 105, "log", .20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", .40, "linear", .40),
}
LAND_PRICES = (1000, 2000, 4000)
SHED_TILES = ((4, 4), (5, 4), (4, 5), (5, 5))
SHED_CAPACITY = 100
PASS = ["PASS"]
QUADRANTS = ("NW", "NE", "SW", "SE")
LAND_STAGE_DAYS = (0, 5, 9)
LAND_STAGE_QUADRANTS = (("NW",), ("NW", "NE"), ("NW", "NE", "SW"))

# Target maintenance rings around the four shed tiles.  Daily-service assets
# take the inner ring.  All crops still require daily WATER, so slower MELON is
# kept on ring two rather than being pushed to a movement-heavy outer edge.
PLACEMENT_RING = {
    "PASTURE": 0,
    "COOP": 0,
    "WHEAT": 1,
    "TOMATO": 1,
    "STRAWBERRY": 1,
    "CARROT": 2,
    "MELON": 2,
}

SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "YARN_STORE": ("WOOL",),
}

# ParamSpec contains only bounded aggregate choices.  Stage totals and the
# common opening are compiler constants, not searched coordinates.
EXPERT_NAMES = ("wool", "dairy_berry", "tomato_market", "root", "grain_egg")
EXPERT_FIELDS = ("focus2", "focus3", "donor_template", "animal_suffix")
COMMON_OPENING = {"WHEAT": 8, "MELON": 7}
BASE_STAGE2 = {"WHEAT": 8, "MELON": 5, "STRAWBERRY": 6}
BASE_STAGE3 = {"WHEAT": 10, "MELON": 7, "STRAWBERRY": 5, "CARROT": 3}
FOCUS_CROP = {
    "wool": "WHEAT",
    "dairy_berry": "STRAWBERRY",
    "tomato_market": "TOMATO",
    "root": "CARROT",
    "grain_egg": "WHEAT",
}
DONOR_ORDERS = {
    0: ("MELON", "STRAWBERRY", "CARROT", "TOMATO", "WHEAT"),
    1: ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO"),
    2: ("STRAWBERRY", "CARROT", "MELON", "TOMATO", "WHEAT"),
}
ANIMAL_SUFFIXES = {
    "wool": {
        0: ((5, "SHEEP", 2), (9, "COW", 4)),
        1: ((5, "COW", 4), (9, "SHEEP", 2)),
        2: ((5, "SHEEP", 1), (9, "COW", 4)),
    },
    "dairy_berry": {
        0: ((5, "COW", 4), (9, "COW", 2)),
        1: ((5, "COW", 4), (9, "SHEEP", 2)),
        2: ((5, "COW", 6),),
    },
    "tomato_market": {
        0: ((5, "COW", 2),),
        1: ((5, "COW", 4),),
        2: ((5, "COW", 2), (9, "SHEEP", 2)),
    },
    "root": {
        0: ((5, "COW", 4), (9, "SHEEP", 2)),
        1: ((5, "SHEEP", 2), (9, "COW", 4)),
        2: ((5, "COW", 4),),
    },
    "grain_egg": {
        0: ((5, "GOOSE", 2), (9, "COW", 2)),
        1: ((5, "GOOSE", 4),),
        2: ((5, "GOOSE", 2), (9, "SHEEP", 2)),
    },
}

PARAM_SPEC: dict[str, Any] = {
    "experts": {
        "focus2": (0, 2, 4, 6),
        "focus3": (2, 4, 6, 8, 10),
        "donor_template": (0, 1, 2),
        "animal_suffix": (0, 1, 2),
    },
    "auction": {
        "harvest_priority": (2, 3),
        "plant_priority": (2, 3, 4),
        "place_priority": (2, 3),
        "sticky_bonus": (0, 3, 5),
        "role_penalty": (0, 2, 3),
        "replacement": ("none", "same_turn_seed_reserve_only"),
    },
    "market": {
        "finance_stress": (16, 24, 32, 48),
        "ordinary_stress": (8, 12, 16),
        "sale_floor": (.45, .55, .65),
        "pressure": (84, 88, 92),
        "liquidation": (708, 712, 716),
        "regular_cap": (12, 24, 36),
    },
}
ParamSpec = dict[str, Any]

# <DEFAULT_PARAMS_START>
DEFAULT_PARAMS: dict[str, Any] = json.loads('{"auction":{"harvest_priority":2,"place_priority":3,"plant_priority":2,"replacement":"same_turn_seed_reserve_only","role_penalty":0,"sticky_bonus":3},"experts":{"dairy_berry":{"animal_suffix":0,"donor_template":2,"focus2":0,"focus3":2},"grain_egg":{"animal_suffix":0,"donor_template":2,"focus2":0,"focus3":2},"root":{"animal_suffix":0,"donor_template":2,"focus2":0,"focus3":6},"tomato_market":{"animal_suffix":0,"donor_template":2,"focus2":0,"focus3":6},"wool":{"animal_suffix":0,"donor_template":2,"focus2":0,"focus3":2}},"market":{"finance_stress":16,"liquidation":712,"ordinary_stress":16,"pressure":88,"regular_cap":36,"sale_floor":0.45}}')
# <DEFAULT_PARAMS_END>


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def canonical_json(params: dict[str, Any]) -> str:
    return json.dumps(_canonical_value(params), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def canonical_hash(params: dict[str, Any]) -> str:
    errors = validate_params(params)
    if errors:
        raise ValueError("; ".join(errors))
    payload = (HASH_DOMAIN + canonical_json(params)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _focus_block(base: dict[str, int], focus: str, amount: int,
                 donor_template: int) -> dict[str, int]:
    block = Counter({crop: int(count) for crop, count in base.items()})
    remaining = int(amount)
    for donor in DONOR_ORDERS[int(donor_template)]:
        if donor == focus or remaining <= 0:
            continue
        taken = min(remaining, block[donor])
        block[donor] -= taken
        block[focus] += taken
        remaining -= taken
    if remaining:
        raise ValueError(f"cannot transfer {amount} tiles to {focus}")
    return {crop: block[crop] for crop in CROPS if block[crop] > 0}


def compile_expert_genome(name: str, config: dict[str, Any]) -> dict[str, Any]:
    focus = FOCUS_CROP[name]
    suffix = ANIMAL_SUFFIXES[name][int(config["animal_suffix"])]
    return {
        "land_days": [0, 5, 9],
        "crop_blocks": [
            dict(COMMON_OPENING),
            _focus_block(BASE_STAGE2, focus, int(config["focus2"]),
                         int(config["donor_template"])),
            _focus_block(BASE_STAGE3, focus, int(config["focus3"]),
                         int(config["donor_template"])),
        ],
        "animal_waves": [(0, "SHEEP", 4), *[tuple(wave) for wave in suffix]],
    }


def compile_genomes(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {name: compile_expert_genome(name, params["experts"][name])
            for name in EXPERT_NAMES}


def _validate_genomes(genomes: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for name, genome in genomes.items():
        days = genome["land_days"]
        blocks = genome["crop_blocks"]
        if len(days) != len(blocks) or len(days) > 4 or days[0] != 0 or days != sorted(days):
            errors.append(f"{name}: invalid land stages")
        if [sum(int(v) for v in block.values()) for block in blocks] != [15, 19, 25]:
            errors.append(f"{name}: crop block totals must be 15/19/25")
        if blocks[0] != COMMON_OPENING:
            errors.append(f"{name}: opening must be W8+M7")
        totals: Counter[str] = Counter()
        for day, kind, count in genome["animal_waves"]:
            totals[kind] += int(count)
            if kind not in ANIMALS or not 0 <= int(day) <= 29:
                errors.append(f"{name}: invalid animal wave")
        for kind, count in totals.items():
            if count > ANIMALS[kind]["max"]:
                errors.append(f"{name}: {kind} cap")
        for stage in range(len(days)):
            crops = sum(sum(block.values()) for block in blocks[:stage + 1])
            animals = sum(n for day, _kind, n in genome["animal_waves"] if day <= days[stage])
            if crops + animals > 25 * (stage + 1):
                errors.append(f"{name}: stage {stage} capacity")
        final_crops: Counter[str] = Counter()
        for block in blocks:
            final_crops.update(block)
        if sum(final_crops.values()) != 59 or final_crops["WHEAT"] < 18:
            errors.append(f"{name}: final crop total/WHEAT floor")
        if name == "root" and final_crops["CARROT"] < 8:
            errors.append("root: CARROT floor")
        if name == "dairy_berry" and (final_crops["STRAWBERRY"] < 12 or totals["COW"] < 4):
            errors.append("dairy_berry: STRAWBERRY/COW floor")
        if name == "tomato_market" and final_crops["TOMATO"] < 6:
            errors.append("tomato_market: TOMATO floor")
        if name == "wool" and totals["SHEEP"] < 5:
            errors.append("wool: SHEEP floor")
        if name == "grain_egg" and (final_crops["WHEAT"] < 24 or totals["GOOSE"] < 2):
            errors.append("grain_egg: WHEAT/GOOSE floor")
    return errors


def validate_params(params: dict[str, Any]) -> list[str]:
    def allowed_value(value: Any, allowed: tuple[Any, ...]) -> bool:
        return any(type(value) is type(choice) and value == choice for choice in allowed)

    errors: list[str] = []
    if not isinstance(params, dict) or set(params) != {"experts", "auction", "market"}:
        return ["top-level keys must be experts/auction/market"]
    experts = params.get("experts")
    if not isinstance(experts, dict) or set(experts) != set(EXPERT_NAMES):
        errors.append("expert names do not match the five frozen experts")
    else:
        for name in EXPERT_NAMES:
            config = experts[name]
            if not isinstance(config, dict) or set(config) != set(EXPERT_FIELDS):
                errors.append(f"{name}: invalid expert fields")
                continue
            for field in EXPERT_FIELDS:
                if not allowed_value(config[field], PARAM_SPEC["experts"][field]):
                    errors.append(f"{name}.{field}: outside discrete set")
    for group in ("auction", "market"):
        values = params.get(group)
        spec = PARAM_SPEC[group]
        if not isinstance(values, dict) or set(values) != set(spec):
            errors.append(f"{group}: invalid fields")
            continue
        for field, allowed in spec.items():
            if not allowed_value(values[field], allowed):
                errors.append(f"{group}.{field}: outside discrete set")
    if not errors:
        try:
            errors.extend(_validate_genomes(compile_genomes(params)))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"compile error: {exc}")
    return errors


def _dist(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _toward(pos: tuple[int, int], target: tuple[int, int]) -> list[str]:
    x, y = pos
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return PASS.copy()


def _shed_gate(pos: tuple[int, int]) -> tuple[int, int]:
    return min(SHED_TILES, key=lambda value: (_dist(pos, value), value))


def _quadrant(pos: tuple[int, int]) -> int:
    return (2 if pos[1] >= 5 else 0) + (1 if pos[0] >= 5 else 0)


def _animal(tile: Any) -> str | None:
    if not isinstance(tile, dict) or not tile.get("animal"):
        return None
    value = tile["animal"]
    return value.get("kind") if isinstance(value, dict) else str(value)


def _unlocked(grid: list[list[Any]]) -> list[tuple[int, int]]:
    return [(x, y) for y, row in enumerate(grid) for x, tile in enumerate(row)
            if tile != "LOCKED" and not (isinstance(tile, dict) and tile.get("kind") == "LOCKED")]


def _position_order(positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted(positions, key=lambda pos: (min(_dist(pos, shed) for shed in SHED_TILES), pos[1], pos[0]))


def _shed_distance(pos: tuple[int, int]) -> int:
    return min(_dist(pos, shed) for shed in SHED_TILES)


def _placement_key(pos: tuple[int, int], asset: str) -> tuple[int, int, int, int, int]:
    """Deterministic frequency-aware layout key with no stored route table."""
    distance = _shed_distance(pos)
    ring = int(PLACEMENT_RING.get(str(asset), 2))
    return (abs(distance - ring), distance, _quadrant(pos), pos[1], pos[0])


def _placement_order(positions: list[tuple[int, int]], asset: str) -> list[tuple[int, int]]:
    return sorted(positions, key=lambda pos: _placement_key(pos, asset))


def _land_prefix(stage: int) -> tuple[tuple[int, int], ...]:
    """Fixed NW25 -> NW+NE50 -> NW+NE+SW75 land prefix."""
    quadrants = set(LAND_STAGE_QUADRANTS[max(0, min(2, int(stage)))])
    return tuple(
        (x, y) for y in range(10) for x in range(10)
        if QUADRANTS[_quadrant((x, y))] in quadrants
    )


def _zone_snake(zone: int) -> tuple[tuple[int, int], ...]:
    """Five-by-five service route, beginning at the shed-facing corner."""
    zone = int(zone)
    xs_near = list(range(4, -1, -1)) if zone % 2 == 0 else list(range(5, 10))
    ys = list(range(4, -1, -1)) if zone < 2 else list(range(5, 10))
    route: list[tuple[int, int]] = []
    for row_index, y in enumerate(ys):
        xs = xs_near if row_index % 2 == 0 else list(reversed(xs_near))
        route.extend((x, y) for x in xs)
    return tuple(route)


def _counts(grid: list[list[Any]]) -> tuple[Counter[str], Counter[str], Counter[str]]:
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    structures: Counter[str] = Counter()
    for row in grid:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT" and tile.get("crop") in CROPS:
                crops[tile["crop"]] += 1
            animal = _animal(tile)
            if animal:
                animals[animal] += 1
            if tile.get("kind") in {"PASTURE", "COOP"}:
                structures[tile["kind"]] += 1
    return crops, animals, structures


def _inventory_totals(inventories: list[dict[str, Any]]) -> Counter[str]:
    total: Counter[str] = Counter()
    for inventory in inventories:
        total.update({key: int(value or 0) for key, value in dict(inventory or {}).items()})
    return total


def _fib(index: int) -> int:
    left, right = 1, 1
    for _ in range(max(0, int(index))):
        left, right = right, left + right
    return left


def _shape(name: str, value: float, target: float) -> float:
    value = max(0.0, value)
    if name == "linear":
        return value
    if name == "sq":
        return value * value
    if name == "sqrt":
        return math.sqrt(value)
    if name == "log":
        return math.log1p(value)
    if name == "hinge":
        unit = value / target if target > 0 else value
        return unit + 8.0 * max(0.0, unit - 1.0) ** 2
    return value


def market_price(item: str, inventory: int) -> int:
    base, target, below_name, below_target, above_name, above_target = MARKET_PARAMS[item]
    if inventory < 10000:
        amplitude = below_target * base / _shape(below_name, target, target)
        value = base + amplitude * _shape(below_name, 10000 - inventory, target)
    else:
        amplitude = above_target * base / _shape(above_name, target, target)
        value = base - amplitude * _shape(above_name, inventory - 10000, target)
    return max(1, int(round(value)))


def route_expert(shops: list[str]) -> str:
    first = str(shops[0]) if shops else ""
    if first in {"YARN_STORE", "PIZZA_SHOP"}:
        return "wool"
    if first in {"SMOOTHIE_SHOP", "ICE_CREAM_SHOP", "PET_CAFE"}:
        return "dairy_berry"
    if first == "FARMERS_MARKET":
        return "tomato_market"
    return "grain_egg"


def daily_goal(genome: dict[str, Any], day: int) -> dict[str, Any]:
    lands = sum(day >= int(value) for value in genome["land_days"])
    crops: Counter[str] = Counter()
    for block in genome["crop_blocks"][:lands]:
        crops.update(block)
    animals: Counter[str] = Counter()
    for wave_day, kind, count in genome["animal_waves"]:
        if day >= int(wave_day):
            animals[kind] += int(count)
    active = sum(crops.values()) + 2 * sum(animals.values())
    hands = min(LABOR_HAND_CAP, 4 + 10 * min(day, 7) // 7,
                max(4, math.ceil(active / 4)))
    return {"day": day, "lands": lands, "hands": hands, "crops": dict(crops),
            "animals": dict(animals), "feed_reserve": 2 * sum(animals.values()),
            "cash_reserve": 100}


def compile_daily_goals(genome: dict[str, Any]) -> list[dict[str, Any]]:
    return [daily_goal(genome, day) for day in range(30)]


Job = tuple[int, int, int, tuple[Any, ...]]


@dataclass(frozen=True)
class AnimalSlot:
    coord: tuple[int, int]
    structure_kind: str
    animal_kind: str
    activation_day: int
    activation_stage: int
    ordinal: int
    service_zone: int
    service_lane: int
    circuit_ordinal: int


@dataclass(frozen=True)
class CropSlot:
    coord: tuple[int, int]
    crop: str
    activation_stage: int
    ordinal: int
    service_zone: int
    service_lane: int
    circuit_ordinal: int


@dataclass(frozen=True)
class ExpertSlotContract:
    expert: str
    animal_slots: tuple[AnimalSlot, ...]
    crop_slots: tuple[CropSlot, ...]


def compile_slot_contract(name: str, genome: dict[str, Any]) -> ExpertSlotContract:
    """Compile a coordinate contract from a genome, without observations."""
    used: set[tuple[int, int]] = set()
    animal_slots: list[AnimalSlot] = []
    crop_slots: list[CropSlot] = []
    animal_ordinal = 0
    crop_ordinal = 0
    for stage, activation_day in enumerate(LAND_STAGE_DAYS):
        available = set(_land_prefix(stage)) - used
        waves = [wave for wave in genome["animal_waves"]
                 if int(wave[0]) == int(activation_day)]
        for wave_day, animal_kind, count in waves:
            structure = str(ANIMALS[str(animal_kind)]["structure"])
            for _ in range(int(count)):
                if not available:
                    raise ValueError(f"{name}: no coordinate for animal slot")
                coord = _placement_order(list(available), structure)[0]
                animal_slots.append(AnimalSlot(
                    coord, structure, str(animal_kind), int(wave_day),
                    int(stage), int(animal_ordinal), _quadrant(coord), -1, -1))
                animal_ordinal += 1
                used.add(coord)
                available.remove(coord)
        block = genome["crop_blocks"][stage]
        for crop in CROPS:
            for _ in range(int(block.get(crop, 0))):
                if not available:
                    raise ValueError(f"{name}: no coordinate for crop slot")
                coord = _placement_order(list(available), crop)[0]
                crop_slots.append(CropSlot(
                    coord, str(crop), int(stage), int(crop_ordinal),
                    _quadrant(coord), -1, -1))
                crop_ordinal += 1
                used.add(coord)
                available.remove(coord)
    # Service metadata is compiled after asset coordinates are frozen.  Each
    # lane is a contiguous prefix of the zone's shed-facing snake and contains
    # at most five stops, so a lane never joins unrelated placement order.
    service: dict[tuple[int, int], tuple[int, int, int]] = {}
    for zone in range(4):
        zone_coords = set(coord for coord in used if _quadrant(coord) == zone)
        ordered = [coord for coord in _zone_snake(zone) if coord in zone_coords]
        lane = -1
        lane_size = 0
        previous: tuple[int, int] | None = None
        for circuit, coord in enumerate(ordered):
            if previous is None or _dist(previous, coord) != 1 or lane_size >= 5:
                lane += 1
                lane_size = 0
            service[coord] = (zone, lane, circuit)
            lane_size += 1
            previous = coord

    animal_slots = [AnimalSlot(
        slot.coord, slot.structure_kind, slot.animal_kind,
        slot.activation_day, slot.activation_stage, slot.ordinal,
        *service[slot.coord]) for slot in animal_slots]
    crop_slots = [CropSlot(
        slot.coord, slot.crop, slot.activation_stage, slot.ordinal,
        *service[slot.coord]) for slot in crop_slots]
    return ExpertSlotContract(name, tuple(animal_slots), tuple(crop_slots))


def compile_slot_contracts(
        genomes: dict[str, dict[str, Any]]) -> dict[str, ExpertSlotContract]:
    return {name: compile_slot_contract(name, genomes[name]) for name in EXPERT_NAMES}


@dataclass(frozen=True)
class PendingReceipt:
    order_step: int
    operation: str
    item: str | None
    quantity: int


@dataclass(frozen=True)
class PendingHarvestBatch:
    action_step: int
    counts: dict[str, int]
    before_totals: dict[str, int]


@dataclass(frozen=True)
class PendingProductBatch:
    action_step: int
    action_day: int
    before_totals: dict[str, int]
    buy_requested: dict[str, int]
    sell_requested: dict[str, int]
    harvest_attempted: dict[str, int]


@dataclass
class ActorTour:
    day: int
    zone: int
    started_step: int
    last_step: int
    last_job_key: tuple[Any, ...]


@dataclass
class TileWork:
    coord: tuple[int, int]
    owner: int | None
    ready_ops: tuple[tuple[int, tuple[Any, ...]], ...]
    phase: str
    ready_since: int
    crop_if_needed: str | None = None
    owner_day: int | None = None
    reserved_seed: str | None = None
    deadline_step: int | None = None
    lane_key: tuple[int, int] | None = None
    species: str | None = None


def _job_key(job: Job) -> tuple[Any, ...]:
    """Semantic identity survives a priority change."""
    _priority, x, y, verb = job
    return (verb[0], x, y, *verb[1:])


def _economic_tier(job: Job) -> int:
    op = str(job[3][0])
    if op in PRIMARY_OPS:
        return 0
    if op in SECONDARY_OPS:
        return 1
    return 0


def _job_zone(job: Job) -> int:
    return _quadrant((int(job[1]), int(job[2])))


class ShopRouterExecutor:
    def __init__(self, params: dict[str, Any], fixed_expert: str | None = None) -> None:
        errors = validate_params(params)
        if errors:
            raise ValueError("; ".join(errors))
        if fixed_expert is not None and fixed_expert not in EXPERT_NAMES:
            raise ValueError(f"unknown fixed expert: {fixed_expert}")
        self.params = copy.deepcopy(params)
        self.genomes = compile_genomes(self.params)
        self.slot_contracts = compile_slot_contracts(self.genomes)
        self.auction = self.params["auction"]
        self.market_params = self.params["market"]
        self.fixed_expert = fixed_expert
        self.expert = fixed_expert or "grain_egg"
        self.committed = fixed_expert is not None
        self.commit_step: int | None = 0 if fixed_expert is not None else None
        self.first_shops: tuple[str, ...] = ()
        self.day = -1
        self.sticky: dict[int, tuple[Any, ...]] = {}
        self.tours: dict[int, ActorTour] = {}
        self.actual_plant_events: list[dict[str, Any]] = []
        self.tile_work: dict[tuple[int, int], TileWork] = {}
        self.seed_reservations: dict[tuple[int, int], str] = {}
        self._assigned_first_steps: dict[int, list[Any]] = {}
        self.roles: dict[tuple[int, int], int] = {}
        self.crop_cursor = 0
        self.pending_receipts: list[PendingReceipt] = []
        self.pending_harvests: list[PendingHarvestBatch] = []
        self.pending_product_batches: list[PendingProductBatch] = []
        self.replacement_credits: Counter[str] = Counter()
        self.product_ledger: dict[str, Counter[str]] = {
            product: Counter() for product in PRODUCTS
        }
        self.daily_product_ledger: dict[int, dict[str, Counter[str]]] = {}
        self.daily_operations: dict[int, Counter[str]] = {}
        self.last_product_totals: Counter[str] = Counter()
        self.last_step = -1
        self.audit: Counter[str] = Counter()

    def _reconcile_receipts(self, step: int) -> None:
        """Receipts live for one observation boundary, never as fake assets."""
        retained: list[PendingReceipt] = []
        for receipt in self.pending_receipts:
            if step > receipt.order_step:
                self.audit["receipts_reconciled"] += 1
            else:
                retained.append(receipt)
        self.pending_receipts = retained

    def _record_receipts(self, step: int, orders: list[list[Any]]) -> None:
        for order in orders:
            if not order or order[0] not in {"BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL", "HIRE", "BUY_LAND"}:
                continue
            item = str(order[1]) if len(order) >= 2 else None
            quantity = int(order[2]) if len(order) >= 3 else 1
            self.pending_receipts.append(PendingReceipt(step, str(order[0]), item, quantity))
            self.audit["receipts_recorded"] += 1

    @staticmethod
    def _product_totals(shed: dict[str, int], inventories: list[dict[str, Any]]) -> Counter[str]:
        totals = Counter({str(item): int(quantity or 0) for item, quantity in shed.items()})
        totals.update(_inventory_totals(inventories))
        return totals

    def _ledger_add(self, day: int, product: str, field: str, quantity: int) -> None:
        quantity = int(quantity)
        if quantity <= 0 or product not in self.product_ledger:
            return
        self.product_ledger[product][field] += quantity
        daily = self.daily_product_ledger.setdefault(
            int(day), {name: Counter() for name in PRODUCTS})
        daily[product][field] += quantity

    def _daily_add(self, day: int, field: str, quantity: int = 1) -> None:
        quantity = int(quantity)
        if quantity > 0:
            self.daily_operations.setdefault(int(day), Counter())[field] += quantity

    @staticmethod
    def _harvest_product_attempts(grid: list[list[Any]], units: list[Any],
                                  verbs: list[list[Any]]) -> Counter[str]:
        attempts: Counter[str] = Counter()
        for unit, verb in zip(units, verbs):
            if not unit or not verb or verb[0] != "HARVEST":
                continue
            x, y = int(unit[0]), int(unit[1])
            tile = grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else None
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT" and str(tile.get("crop")) in PRODUCTS:
                attempts[str(tile["crop"])] += 1
            else:
                animal = _animal(tile)
                product = str(ANIMALS.get(str(animal), {}).get("product", ""))
                if product in PRODUCTS:
                    attempts[product] += 1
        return attempts

    def _record_product_batch(self, step: int, day: int,
                              shed: dict[str, int], inventories: list[dict[str, Any]],
                              grid: list[list[Any]], units: list[Any],
                              verbs: list[list[Any]], orders: list[list[Any]]) -> None:
        buys: Counter[str] = Counter()
        sells: Counter[str] = Counter()
        for order in orders:
            if len(order) < 3 or str(order[1]) not in PRODUCTS:
                continue
            quantity = max(0, int(order[2]))
            if order[0] == "BUY_PRODUCT":
                buys[str(order[1])] += quantity
            elif order[0] == "SELL":
                sells[str(order[1])] += quantity
        harvests = self._harvest_product_attempts(grid, units, verbs)
        totals = self._product_totals(shed, inventories)
        batch = PendingProductBatch(
            action_step=int(step),
            action_day=int(day),
            before_totals={product: int(totals[product]) for product in PRODUCTS},
            buy_requested=dict(buys),
            sell_requested=dict(sells),
            harvest_attempted=dict(harvests),
        )
        self.pending_product_batches.append(batch)
        for product in PRODUCTS:
            self._ledger_add(day, product, "buy_requested_units", buys[product])
            self._ledger_add(day, product, "sell_requested_units", sells[product])
            self._ledger_add(day, product, "harvest_attempted_actions", harvests[product])

    def _reconcile_product_batches(self, step: int, shed: dict[str, int],
                                   inventories: list[dict[str, Any]]) -> None:
        """Record only next-boundary private-inventory deltas.

        Negative deltas are never attributed to SELL: FEED, FERTILIZE, PLACE,
        end-of-day discard and other engine effects can share that direction.
        Positive deltas are likewise not called realised BUY or production.
        Exact sold/produced/discarded quantities belong to an independently
        instrumented evaluator, not to this candidate-side ledger.
        """
        current = self._product_totals(shed, inventories)
        retained: list[PendingProductBatch] = []
        for batch in self.pending_product_batches:
            if int(step) <= batch.action_step:
                retained.append(batch)
                continue
            exact_boundary = int(step) == batch.action_step + 1
            for product in PRODUCTS:
                buy = int(batch.buy_requested.get(product, 0))
                sell = int(batch.sell_requested.get(product, 0))
                harvest = int(batch.harvest_attempted.get(product, 0))
                if not exact_boundary:
                    self._ledger_add(batch.action_day, product,
                                     "buy_not_observed_units", buy)
                    self._ledger_add(batch.action_day, product,
                                     "sell_not_observed_units", sell)
                    self._ledger_add(batch.action_day, product,
                                     "harvest_not_observed_actions", harvest)
                    if buy or sell or harvest:
                        self._ledger_add(batch.action_day, product,
                                         "missing_observation_boundaries", 1)
                    continue
                delta = int(current[product]) - int(batch.before_totals.get(product, 0))
                self._ledger_add(batch.action_day, product,
                                 "observed_inventory_increase_units", max(0, delta))
                self._ledger_add(batch.action_day, product,
                                 "observed_inventory_decrease_units", max(0, -delta))
                if delta < 0:
                    self._ledger_add(batch.action_day, product,
                                     "negative_delta_ambiguous_boundaries", 1)
                conflicts = sum(value > 0 for value in (buy, sell, harvest))
                if conflicts > 1:
                    self._ledger_add(batch.action_day, product,
                                     "ambiguous_intent_boundaries", 1)
                    self._ledger_add(batch.action_day, product,
                                     "buy_not_observed_units", buy)
                    self._ledger_add(batch.action_day, product,
                                     "sell_not_observed_units", sell)
                    self._ledger_add(batch.action_day, product,
                                     "harvest_not_observed_actions", harvest)
                elif buy:
                    compatible = min(buy, max(0, delta))
                    self._ledger_add(batch.action_day, product,
                                     "buy_direction_compatible_units", compatible)
                    self._ledger_add(batch.action_day, product,
                                     "buy_not_observed_units", buy - compatible)
                elif sell:
                    compatible = min(sell, max(0, -delta))
                    self._ledger_add(batch.action_day, product,
                                     "sell_direction_compatible_units", compatible)
                    self._ledger_add(batch.action_day, product,
                                     "sell_not_observed_units", sell - compatible)
                elif harvest:
                    if delta > 0:
                        self._ledger_add(batch.action_day, product,
                                         "harvest_direction_compatible_boundaries", 1)
                        self._ledger_add(batch.action_day, product,
                                         "positive_delta_with_harvest_attempt_units", delta)
                        self._ledger_add(batch.action_day, product,
                                         "harvest_not_observed_actions", max(0, harvest - 1))
                    else:
                        self._ledger_add(batch.action_day, product,
                                         "harvest_not_observed_actions", harvest)
        self.pending_product_batches = retained
        self.last_product_totals = Counter(
            {product: int(current[product]) for product in PRODUCTS})

    def _reconcile_harvests(self, step: int, shed: dict[str, int],
                            inventories: list[dict[str, Any]]) -> None:
        """Only an observed inventory increase creates bounded continuity."""
        current = self._product_totals(shed, inventories)
        retained: list[PendingHarvestBatch] = []
        for batch in self.pending_harvests:
            if step <= batch.action_step:
                retained.append(batch)
                continue
            for crop, attempted in batch.counts.items():
                observed = max(0, current[crop] - int(batch.before_totals.get(crop, 0)))
                succeeded = min(int(attempted), observed)
                room = max(0, MAX_PARALLEL_PLANT - sum(self.replacement_credits.values()))
                admitted = min(succeeded, room)
                if admitted:
                    self.replacement_credits[crop] += admitted
                    self.audit["replacement_success_registered"] += admitted
                self.audit["replacement_failed_not_registered"] += max(0, int(attempted) - succeeded)
                self.audit["replacement_success_overflow"] += max(0, succeeded - admitted)
        self.pending_harvests = retained

    def _record_harvest_batch(self, step: int, grid: list[list[Any]], units: list[Any],
                              verbs: list[list[Any]], shed: dict[str, int],
                              inventories: list[dict[str, Any]]) -> None:
        counts: Counter[str] = Counter()
        for unit, verb in zip(units, verbs):
            if not unit or not verb or verb[0] != "HARVEST":
                continue
            x, y = int(unit[0]), int(unit[1])
            tile = grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else None
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            crop = str(tile.get("crop") or "")
            if crop in NON_ONGOING:
                counts[crop] += 1
        if counts:
            totals = self._product_totals(shed, inventories)
            self.pending_harvests.append(PendingHarvestBatch(
                step, dict(counts), {crop: totals[crop] for crop in counts}))
            self.audit["replacement_attempted"] += sum(counts.values())

    @staticmethod
    def _seat(obs: dict[str, Any]) -> int:
        for key in ("player_index", "index", "player"):
            if obs.get(key) is not None:
                return int(obs[key])
        return 0

    def _route(self, obs: dict[str, Any]) -> None:
        shops = [str(value) for value in list((obs.get("town") or {}).get("unlocked_shops", []) or [])]
        if not shops:
            return
        if not self.first_shops:
            self.first_shops = (shops[0],)
        if self.committed:
            return
        self.expert = route_expert(shops)
        self.committed = True
        self.commit_step = int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)
        self.audit[f"router_{self.expert}"] += 1

    def goal(self, day: int) -> dict[str, Any]:
        return daily_goal(self.genomes[self.expert], min(29, int(day)))

    def active_slot_contract(
            self, day: int) -> tuple[tuple[AnimalSlot, ...], tuple[CropSlot, ...]]:
        """Permanent active prefixes; an uncommitted router exposes common only."""
        max_stage = 0 if not self.committed else min(
            2, sum(int(day) >= value for value in LAND_STAGE_DAYS) - 1)
        contract = self.slot_contracts[self.expert]
        animals = tuple(slot for slot in contract.animal_slots
                        if slot.activation_stage <= max_stage
                        and slot.activation_day <= int(day))
        crops = tuple(slot for slot in contract.crop_slots
                      if slot.activation_stage <= max_stage)
        return animals, crops

    def _eligible_replacement_crop(self, crop: str) -> bool:
        if not self.first_shops or crop not in NON_ONGOING:
            return False
        return crop in SHOP_PRODUCTS.get(self.first_shops[0], ())

    def _true_eligible_harvests(self, grid: list[list[Any]], units: list[Any],
                                verbs: list[list[Any]]) -> Counter[str]:
        if self.auction["replacement"] != "same_turn_seed_reserve_only":
            return Counter()
        harvested: Counter[str] = Counter()
        for unit, verb in zip(units, verbs):
            if not unit or not verb or verb[0] != "HARVEST":
                continue
            x, y = int(unit[0]), int(unit[1])
            if y >= len(grid) or x >= len(grid[y]):
                continue
            tile = grid[y][x]
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            crop = str(tile.get("crop"))
            if self._eligible_replacement_crop(crop):
                harvested[crop] += 1
                self.audit["same_turn_seed_reserve_harvest"] += 1
        return harvested

    def _fair_crop_order(self, have: Counter[str], target: dict[str, int],
                         assigned: Counter[str] | None = None,
                         cursor: int | None = None) -> list[str]:
        assigned = assigned or Counter()
        cycle = list(CROPS)
        offset = int(self.crop_cursor if cursor is None else cursor) % len(cycle)
        tie_order = cycle[offset:] + cycle[:offset]
        return sorted((crop for crop, count in target.items() if int(count) > 0),
                      key=lambda crop: (-int(self.replacement_credits[crop] > 0),
                                        (have[crop] + assigned[crop]) / int(target[crop]),
                                        tie_order.index(crop)))

    def _service_route_work(self, jobs: list[Job],
                            unit_positions: list[tuple[int, int]],
                            day: int) -> int:
        """Executable shed-closed route work on compiled contiguous lanes."""
        return sum(self._service_route_costs(jobs, day))

    def _service_route_costs(self, jobs: list[Job], day: int) -> list[int]:
        """One closed-route cost per lane; no actor start is reused."""
        if not jobs:
            return []
        animal_slots, crop_slots = self.active_slot_contract(day)
        slot_by_coord = {slot.coord: slot for slot in (*animal_slots, *crop_slots)}
        grouped: dict[tuple[Any, ...], list[Job]] = {}
        for job in jobs:
            coord = (int(job[1]), int(job[2]))
            slot = slot_by_coord.get(coord)
            key = (("slot", int(slot.service_zone), int(slot.service_lane))
                   if slot is not None else ("off_contract", coord))
            grouped.setdefault(key, []).append(job)
        costs: list[int] = []
        gate = SHED_TILES[0]
        for lane_jobs in grouped.values():
            coords = sorted(
                {(int(job[1]), int(job[2])) for job in lane_jobs},
                key=lambda coord: (
                    int(slot_by_coord[coord].circuit_ordinal)
                    if coord in slot_by_coord else 0,
                    coord,
                ))
            if not coords:
                continue
            traversal = sum(_dist(left, right)
                            for left, right in zip(coords, coords[1:]))
            forward = _dist(gate, coords[0]) + traversal + _dist(coords[-1], gate)
            reverse = _dist(gate, coords[-1]) + traversal + _dist(coords[0], gate)
            costs.append(int(min(forward, reverse) + len(lane_jobs)))
        return sorted(costs, reverse=True)

    def _service_capacity_fits(self, jobs: list[Job],
                               unit_positions: list[tuple[int, int]],
                               hour: int, day: int) -> bool:
        """Construct a deterministic actor-to-closed-lane schedule."""
        remaining = max(0, 23 - int(hour))
        bins = sorted(
            (max(0, remaining - _dist(position, SHED_TILES[0]))
             for position in unit_positions), reverse=True)
        for route_cost in self._service_route_costs(jobs, day):
            feasible = [index for index, room in enumerate(bins)
                        if room >= int(route_cost)]
            if not feasible:
                return False
            # Best fit leaves the larger bins for a later long circuit.
            index = min(feasible, key=lambda value: (bins[value] - route_cost, value))
            bins[index] -= int(route_cost)
        return True

    def _jobs(self, day: int, hour: int, units: list[Any], grid: list[list[Any]],
              goal: dict[str, Any], seeds: dict[str, int],
              structure_goal: dict[str, Any]) -> list[Job]:
        """Pure current-frontier planner; persistent reservations are read only."""
        del structure_goal
        jobs: list[Job] = []
        crop_have, animal_have, _structures = _counts(grid)
        productive_assets = sum(crop_have.values()) + sum(animal_have.values())
        target_assets = min(
            TERMINAL_ASSET_FLOOR,
            sum(int(value) for value in goal["crops"].values())
            + sum(int(value) for value in goal["animals"].values()))
        growth_debt = (max(0, target_assets - productive_assets)
                       if int(day) >= GROWTH_DEBT_START_DAY else 0)
        step = int(day) * 24 + int(hour)
        animal_slots, crop_slots = self.active_slot_contract(day)
        active_crop_by_coord = {slot.coord: slot for slot in crop_slots}
        active_animal_by_coord = {slot.coord: slot for slot in animal_slots}
        slot_crop_targets = Counter(slot.crop for slot in crop_slots)
        slot_animal_targets = Counter(slot.animal_kind for slot in animal_slots)
        reserved = Counter(self.seed_reservations.values())
        seed_budget = Counter({
            crop: max(0, int(seeds.get(crop, 0) or 0) - int(reserved[crop]))
            for crop in CROPS
        })
        terminal_window = int(day) >= 27
        terminal_asset_budget = (max(0, productive_assets - TERMINAL_ASSET_FLOOR)
                                 if terminal_window else 10 ** 9)
        finite_candidates: list[tuple[Job, str, bool, int]] = []

        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict):
                    continue
                kind = tile.get("kind")
                if kind == "PLANT":
                    crop = str(tile.get("crop") or "")
                    facts = CROPS.get(crop) or {}
                    planted = tile.get("planted_day")
                    age = int(day) - (int(day) if planted is None else int(planted))
                    if not bool(tile.get("watered_today")):
                        urgent = int(tile.get("consecutive_unwatered", 0) or 0) >= 1
                        jobs.append((0 if urgent else 2, x, y, ("WATER",)))
                    yield_units = int(tile.get("yield_units", 0) or 0)
                    ripe = (bool(facts.get("ongoing"))
                            or yield_units >= int(facts.get("max_yield", 99))
                            or age >= int(facts.get("max_day", 99)))
                    if yield_units <= 0 or age < int(facts.get("first", 0)) or not ripe:
                        continue
                    head = (int(self.auction["harvest_priority"]), x, y, ("HARVEST",))
                    if crop not in NON_ONGOING:
                        jobs.append(head)
                        continue
                    slot = active_crop_by_coord.get((x, y))
                    if slot is None or slot.crop != crop:
                        self.audit["slot_finite_harvest_conflict"] += 1
                        continue
                    lifespan = int(tile.get("max_lifespan_step", -1) or -1)
                    weed_step = (lifespan + 2 * max(0, yield_units - 1)
                                 if lifespan >= 0 else 1 << 30)
                    expires_before_terminal = weed_step < 720
                    finite_candidates.append((head, crop, expires_before_terminal, weed_step))
                elif _animal(tile):
                    if not bool(tile.get("fed_today")):
                        jobs.append((1, x, y, ("FEED",)))
                    if int(tile.get("yield_units", 0) or 0) > 0:
                        jobs.append((int(self.auction["harvest_priority"]),
                                     x, y, ("HARVEST",)))
                    if bool(tile.get("fertilizer_available")):
                        jobs.append((5, x, y, ("COLLECT_FERTILIZER",)))
                    if not bool(tile.get("cared_today")):
                        jobs.append((6, x, y, ("CARE",)))
                elif kind == "WEED":
                    if (x, y) not in active_crop_by_coord \
                            and (x, y) not in active_animal_by_coord:
                        jobs.append((7, x, y, ("DIG",)))

        # Persistent finite options reserve one observed seed.  Existing
        # reservations are idempotent; a new candidate borrows locally now and
        # is persisted by _sync_tile_work before assignment.
        for head, crop, expires_before_terminal, weed_step in sorted(
                finite_candidates,
                key=lambda value: (not value[2], value[3], _job_key(value[0]))):
            coord = (int(head[1]), int(head[2]))
            already_reserved = self.seed_reservations.get(coord) == crop
            if not already_reserved and seed_budget[crop] <= 0:
                self.audit["finite_seed_reserve_withheld"] += 1
                continue
            if terminal_window and not expires_before_terminal \
                    and terminal_asset_budget <= 0:
                self.audit["terminal_finite_floor_withheld"] += 1
                continue
            # Terminal closure remains hard: three confirmed actions must fit
            # before both the public decay deadline and episode end.
            if terminal_window and step + 2 >= min(720, int(weed_step)):
                self.audit["terminal_expiry_closure_withheld"] += 1
                continue
            jobs.append(head)
            if not already_reserved:
                seed_budget[crop] -= 1
            if terminal_window and not expires_before_terminal:
                terminal_asset_budget -= 1
            if terminal_window and expires_before_terminal:
                self.audit["terminal_expiry_floor_bypass"] += 1

        # AnimalSlot expansion is current-head work conserving.  A structure
        # reservation is tied to this slot's species, so off-contract PASTURE
        # or another species can never satisfy the wrong animal deficit.
        animal_deficit = Counter({
            kind: max(0, int(slot_animal_targets[kind]) - int(animal_have[kind]))
            for kind in ANIMALS
        })
        animal_reserved: Counter[str] = Counter()
        for slot in sorted(animal_slots,
                           key=lambda value: (value.service_zone,
                                              value.service_lane,
                                              value.circuit_ordinal,
                                              value.ordinal)):
            kind = slot.animal_kind
            if animal_reserved[kind] >= animal_deficit[kind]:
                continue
            x, y = slot.coord
            tile = self._tile_at(grid, slot.coord)
            if isinstance(tile, dict) and tile.get("kind") == "WEED":
                jobs.append((0, x, y, ("DIG",)))
                self.audit["slot_weed_dependencies"] += 1
                continue
            if tile is None:
                jobs.append((4, x, y,
                             ("BUILD_PASTURE",) if slot.structure_kind == "PASTURE"
                             else ("BUILD_COOP",)))
                animal_reserved[kind] += 1
                self.audit[f"structure_species_reserved_{kind.lower()}"] += 1
                continue
            if isinstance(tile, dict) and tile.get("kind") == slot.structure_kind:
                occupant = _animal(tile)
                if occupant is None:
                    jobs.append((int(self.auction["place_priority"]), x, y,
                                 ("PLACE", kind)))
                    animal_reserved[kind] += 1
                elif occupant != kind:
                    self.audit["slot_animal_conflict"] += 1
                continue
            self.audit["slot_structure_conflict"] += 1

        # Each lane owns an independent immutable slot prefix.  A weed,
        # conflict, or missing seed blocks only that lane.  Round-robin merge
        # lets another feasible lane progress without remapping any slot.
        lanes: dict[tuple[int, int], list[CropSlot]] = {}
        for slot in crop_slots:
            lanes.setdefault((slot.service_zone, slot.service_lane), []).append(slot)
        assigned: Counter[str] = Counter()
        lane_candidates: dict[tuple[int, int], list[Job]] = {}
        lane_order = sorted(
            lanes,
            key=lambda lane: (
                not any(isinstance(self._tile_at(grid, slot.coord), dict)
                        and self._tile_at(grid, slot.coord).get("kind") == "WEED"
                        for slot in lanes[lane]),
                lane,
            ))
        for lane in lane_order:
            slots = lanes[lane]
            candidates: list[Job] = []
            for slot in sorted(slots,
                               key=lambda value: (value.circuit_ordinal,
                                                  value.ordinal)):
                crop = slot.crop
                if crop_have[crop] + assigned[crop] >= int(slot_crop_targets[crop]):
                    continue
                tile = self._tile_at(grid, slot.coord)
                if isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == crop:
                    continue
                if isinstance(tile, dict) and tile.get("kind") == "WEED":
                    if seed_budget[crop] > assigned[crop]:
                        jobs.append((0, slot.coord[0], slot.coord[1], ("DIG",)))
                        assigned[crop] += 1
                        self.audit["slot_weed_dependencies"] += 1
                    else:
                        self.audit["slot_lane_blocked_seed"] += 1
                    break
                if tile is not None:
                    self.audit["slot_crop_conflict"] += 1
                    self.audit["slot_lane_blocked_conflict"] += 1
                    break
                if seed_budget[crop] <= assigned[crop]:
                    self.audit["slot_lane_blocked_seed"] += 1
                    break
                candidates.append((int(self.auction["plant_priority"]),
                                   slot.coord[0], slot.coord[1],
                                   ("PLANT", crop)))
                assigned[crop] += 1
            lane_candidates[lane] = candidates

        plant_admission = 0 if int(hour) > PLANT_CUTOFF_HOUR else MAX_PARALLEL_PLANT
        plants: list[Job] = []
        depth = 0
        while len(plants) < int(plant_admission):
            progressed = False
            for lane in sorted(lane_candidates):
                candidates = lane_candidates[lane]
                if depth < len(candidates):
                    plants.append(candidates[depth])
                    progressed = True
                    if len(plants) >= int(plant_admission):
                        break
            if not progressed:
                break
            depth += 1
        if growth_debt > 0 and plants:
            priority, x, y, verb = plants[0]
            plants[0] = (1, x, y, verb)
        jobs.extend(plants)
        self.audit["work_conserving_current_heads"] += len(jobs)
        return jobs

    def _cost(self, unit_index: int, pos: tuple[int, int], inventory: dict[str, int],
              job: Job, hour: int, lands: int) -> float:
        priority, x, y, verb = job
        if verb[0] == "FEED" and int(inventory.get("WHEAT", 0) or 0) <= 0:
            return math.inf
        if verb[0] == "PLACE" and int(inventory.get(verb[1], 0) or 0) <= 0:
            return math.inf
        distance = _dist(pos, (x, y))
        deadline = 23 if verb[0] in {"WATER", "FEED", "PLANT", "PLACE", "DIG"} else 24
        late = max(0, hour + distance + 1 - deadline)
        sticky = (-float(self.auction["sticky_bonus"])
                  if self.sticky.get(unit_index) == _job_key(job) else 0.0)
        stage = max(1, int(lands))
        role = self.roles.setdefault((stage, unit_index), unit_index % stage)
        role_cost = (float(self.auction["role_penalty"])
                     if _quadrant((x, y)) != role else 0.0)
        return priority * 100.0 + late * 1000.0 + distance + sticky + role_cost

    def _tour_valid(self, unit_index: int, day: int, step: int) -> bool:
        tour = self.tours.get(int(unit_index))
        return bool(tour is not None and tour.day == int(day)
                    and 0 <= int(step) - tour.started_step < TOUR_MAX_STEPS)

    @staticmethod
    def _tile_at(grid: list[list[Any]], coord: tuple[int, int]) -> Any:
        x, y = coord
        return grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else "LOCKED"

    @staticmethod
    def _bfs_first_step(grid: list[list[Any]], start: tuple[int, int],
                        target: tuple[int, int]) -> tuple[int, list[Any]] | None:
        """Shortest in-bounds path; official movement may enter LOCKED tiles."""
        height = len(grid)
        if height <= 0:
            return None
        if not (0 <= start[1] < height and 0 <= target[1] < height):
            return None
        if not (0 <= start[0] < len(grid[start[1]])
                and 0 <= target[0] < len(grid[target[1]])):
            return None
        if start == target:
            return 0, PASS.copy()
        moves = ((1, 0, "EAST"), (-1, 0, "WEST"),
                 (0, 1, "SOUTH"), (0, -1, "NORTH"))
        queue = [start]
        parent: dict[tuple[int, int], tuple[tuple[int, int], str]] = {}
        seen = {start}
        cursor = 0
        while cursor < len(queue):
            x, y = queue[cursor]
            cursor += 1
            for dx, dy, verb in moves:
                nxt = (x + dx, y + dy)
                if nxt in seen or not (0 <= nxt[1] < height):
                    continue
                if not (0 <= nxt[0] < len(grid[nxt[1]])):
                    continue
                seen.add(nxt)
                parent[nxt] = ((x, y), verb)
                if nxt == target:
                    node = nxt
                    distance = 0
                    first = "PASS"
                    while node != start:
                        previous, used_verb = parent[node]
                        distance += 1
                        if previous == start:
                            first = used_verb
                        node = previous
                    return distance, [first]
                queue.append(nxt)
        return None

    @staticmethod
    def _head_job(work: TileWork) -> Job | None:
        if not work.ready_ops:
            return None
        priority, verb = work.ready_ops[0]
        return (int(priority), int(work.coord[0]), int(work.coord[1]), tuple(verb))

    @staticmethod
    def _op_map(jobs: list[Job]) -> dict[str, Job]:
        selected: dict[str, Job] = {}
        for job in jobs:
            op = str(job[3][0])
            current = selected.get(op)
            if current is None or (int(job[0]), _job_key(job)) < (int(current[0]), _job_key(current)):
                selected[op] = job
        return selected

    def _set_work_ready(self, work: TileWork,
                        sequence: list[tuple[int, tuple[Any, ...]]],
                        phase: str, step: int, crop: str | None = None) -> None:
        new_ops = tuple((int(priority), tuple(verb)) for priority, verb in sequence)
        work.ready_ops = new_ops
        work.phase = str(phase)
        if crop is not None:
            work.crop_if_needed = str(crop)

    def _release_seed_reservation(self, coord: tuple[int, int], reason: str) -> None:
        crop = self.seed_reservations.pop(coord, None)
        work = self.tile_work.get(coord)
        if work is not None:
            work.reserved_seed = None
        if crop is not None:
            self.audit[f"persistent_seed_released_{reason}"] += 1

    def _sync_tile_work(self, step: int, grid: list[list[Any]], jobs: list[Job],
                        seeds: dict[str, int] | None = None) -> None:
        """Advance bundles only from the new, observed tile state."""
        seeds = seeds or {}
        grouped: dict[tuple[int, int], list[Job]] = {}
        for job in jobs:
            grouped.setdefault((int(job[1]), int(job[2])), []).append(job)
        contract = self.slot_contracts[self.expert]
        crop_slot_by_coord = {slot.coord: slot for slot in contract.crop_slots}
        animal_slot_by_coord = {slot.coord: slot for slot in contract.animal_slots}

        coords = sorted(set(grouped) | set(self.tile_work))
        for coord in coords:
            tile = self._tile_at(grid, coord)
            current_jobs = grouped.get(coord, [])
            op_map = self._op_map(current_jobs)
            work = self.tile_work.get(coord)

            if work is not None and work.phase == "await_weed_empty":
                if tile is None and work.crop_if_needed:
                    self._set_work_ready(
                        work, [(int(self.auction["plant_priority"]),
                                ("PLANT", str(work.crop_if_needed)))],
                        "replacement_plant", step, work.crop_if_needed)
                    self.audit["weed_dependency_empty_confirmed"] += 1
                    continue
                if isinstance(tile, dict) and tile.get("kind") == "WEED":
                    self._set_work_ready(work, [(0, ("DIG",))],
                                         "weed_dependency", step)
                    continue
                self._release_seed_reservation(coord, "weed_conflict")
                self.tile_work.pop(coord, None)
                continue

            if work is not None and work.phase == "await_structure":
                species = str(work.species or "")
                expected = str(ANIMALS.get(species, {}).get("structure", ""))
                if isinstance(tile, dict) and tile.get("kind") == expected \
                        and not _animal(tile):
                    self._set_work_ready(
                        work, [(int(self.auction["place_priority"]),
                                ("PLACE", species))],
                        "structure_place", step)
                    continue
                if tile is None and expected:
                    verb = (("BUILD_COOP",) if expected == "COOP"
                            else ("BUILD_PASTURE",))
                    self._set_work_ready(work, [(4, verb)],
                                         "structure_build", step)
                    continue
                self.tile_work.pop(coord, None)
                self.audit["structure_option_conflict"] += 1
                continue

            if work is not None and work.phase == "await_animal":
                species = str(work.species or "")
                expected = str(ANIMALS.get(species, {}).get("structure", ""))
                if _animal(tile) == species:
                    self.tile_work.pop(coord, None)
                    self.audit["structure_option_animal_confirmed"] += 1
                    continue
                if isinstance(tile, dict) and tile.get("kind") == expected \
                        and not _animal(tile):
                    self._set_work_ready(
                        work, [(int(self.auction["place_priority"]),
                                ("PLACE", species))],
                        "structure_place", step)
                    continue
                self.tile_work.pop(coord, None)
                self.audit["structure_option_animal_conflict"] += 1
                continue

            if work is not None and work.phase == "await_empty":
                if tile is None:
                    self._set_work_ready(
                        work, [(int(self.auction["plant_priority"]),
                                ("PLANT", str(work.crop_if_needed)))],
                        "replacement_plant", step, work.crop_if_needed)
                    self.audit["tile_bundle_empty_confirmed"] += 1
                    self.audit["persistent_option_replant_ready"] += 1
                    continue
                if isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == str(work.crop_if_needed):
                    harvest = op_map.get("HARVEST")
                    if harvest is not None:
                        self._set_work_ready(
                            work, [(int(harvest[0]), tuple(harvest[3]))],
                            "nonongoing_crop", step, work.crop_if_needed)
                    else:
                        self._release_seed_reservation(coord, "harvest_conflict")
                        self.tile_work.pop(coord, None)
                    continue
                self._release_seed_reservation(coord, "empty_conflict")
                self.tile_work.pop(coord, None)
                self.audit["tile_bundle_empty_conflict"] += 1
                continue

            if work is not None and work.phase in {"await_replacement_plant",
                                                    "await_ordinary_plant"}:
                replacement = work.phase == "await_replacement_plant"
                crop = str(work.crop_if_needed)
                if isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == crop:
                    if replacement:
                        self._release_seed_reservation(coord, "plant_success")
                    self._set_work_ready(work, [(2, ("WATER",))],
                                         "planted_water", step, crop)
                    self.audit["tile_bundle_plant_confirmed"] += 1
                    continue
                if tile is None:
                    self._set_work_ready(
                        work, [(int(self.auction["plant_priority"]), ("PLANT", crop))],
                        "replacement_plant" if replacement else "ordinary_plant",
                        step, crop)
                    continue
                if replacement:
                    self._release_seed_reservation(coord, "plant_conflict")
                self.tile_work.pop(coord, None)
                self.audit["tile_bundle_plant_conflict"] += 1
                continue

            if work is not None and work.phase == "await_water":
                crop = str(work.crop_if_needed)
                if isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == crop and bool(tile.get("watered_today")):
                    self.tile_work.pop(coord, None)
                    self.audit["tile_bundle_water_confirmed"] += 1
                    continue
                if isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == crop:
                    self._set_work_ready(work, [(2, ("WATER",))],
                                         "planted_water", step, crop)
                    continue
                self.tile_work.pop(coord, None)
                continue

            # Unissued planner intents are leases on the current semantic
            # frontier, not promises to stale coordinates.  Confirmation
            # phases above remain observation-driven and survive the absence
            # of a planner proposal; ordinary PLANT and generic structure/
            # placement/dig work must still be proposed at this coordinate
            # with the same semantic key.  A retarget creates a fresh bundle
            # below, so it cannot inherit the stale ready_since or owner.
            if work is not None and work.phase in {"ordinary_plant", "generic"} \
                    and work.ready_ops:
                old_job = self._head_job(work)
                same_job = next(
                    (job for job in current_jobs
                     if old_job is not None and _job_key(job) == _job_key(old_job)),
                    None)
                if same_job is not None:
                    self._set_work_ready(
                        work, [(int(same_job[0]), tuple(same_job[3]))],
                        work.phase, step,
                        (str(same_job[3][1])
                         if work.phase == "ordinary_plant" else None))
                    continue
                self.tile_work.pop(coord, None)
                self.audit["tile_bundle_stale_intent_expired"] += 1
                work = None

            if isinstance(tile, dict) and _animal(tile):
                defaults = {"FEED": 1, "CARE": 6, "HARVEST": 2,
                            "COLLECT_FERTILIZER": 5}
                sequence = [
                    (int(op_map.get(op, (defaults[op], 0, 0, (op,)))[0]),
                     tuple(op_map.get(op, (defaults[op], 0, 0, (op,)))[3]))
                    for op in ("FEED", "CARE", "HARVEST", "COLLECT_FERTILIZER")
                    if op in op_map
                ]
                if sequence:
                    if work is None:
                        work = TileWork(coord, None, (), "animal", int(step))
                        self.tile_work[coord] = work
                    self._set_work_ready(work, sequence, "animal", step)
                else:
                    self.tile_work.pop(coord, None)
                continue

            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop = str(tile.get("crop"))
                ongoing = bool(CROPS.get(crop, {}).get("ongoing"))
                order = ("WATER", "HARVEST")
                sequence = [(int(op_map[op][0]), tuple(op_map[op][3]))
                            for op in order if op in op_map]
                if sequence:
                    if work is None:
                        work = TileWork(coord, None, (), "ongoing_crop" if ongoing else
                                        "nonongoing_crop", int(step), crop)
                        self.tile_work[coord] = work
                    self._set_work_ready(work, sequence,
                                         "ongoing_crop" if ongoing else "nonongoing_crop",
                                         step, crop)
                    if not ongoing and "HARVEST" in op_map:
                        existing = self.seed_reservations.get(coord)
                        other_reserved = sum(
                            value == crop for key, value in self.seed_reservations.items()
                            if key != coord)
                        if existing == crop or int(seeds.get(crop, 0) or 0) > other_reserved:
                            self.seed_reservations[coord] = crop
                            work.reserved_seed = crop
                            lifespan = int(tile.get("max_lifespan_step", -1) or -1)
                            if lifespan >= 0:
                                work.deadline_step = min(
                                    719, lifespan + 2 * max(
                                        0, int(tile.get("yield_units", 0) or 0) - 1))
                            if existing is None:
                                self.audit["persistent_seed_reserved"] += 1
                        else:
                            self.tile_work.pop(coord, None)
                            self.audit["persistent_seed_reserve_race_prevented"] += 1
                else:
                    self._release_seed_reservation(coord, "option_complete")
                    self.tile_work.pop(coord, None)
                continue

            if tile is None and "PLANT" in op_map:
                plant_job = op_map["PLANT"]
                crop = str(plant_job[3][1])
                if work is None:
                    work = TileWork(coord, None, (), "ordinary_plant", int(step), crop)
                    self.tile_work[coord] = work
                self._set_work_ready(work, [(int(plant_job[0]), tuple(plant_job[3]))],
                                     "ordinary_plant", step, crop)
                continue

            generic_order = ("PLACE", "BUILD_PASTURE", "BUILD_COOP", "DIG")
            generic = [op_map[op] for op in generic_order if op in op_map]
            if generic:
                job = generic[0]
                if work is None:
                    crop_slot = crop_slot_by_coord.get(coord)
                    animal_slot = animal_slot_by_coord.get(coord)
                    phase = ("weed_dependency"
                             if job[3][0] == "DIG" and crop_slot is not None
                             else "structure_build"
                             if str(job[3][0]).startswith("BUILD_")
                             and animal_slot is not None else "structure_place"
                             if job[3][0] == "PLACE" and animal_slot is not None
                             else "generic")
                    work = TileWork(
                        coord, None, (), phase, int(step),
                        (crop_slot.crop if crop_slot is not None
                         and job[3][0] == "DIG" else None),
                        None, None, None,
                        ((crop_slot.service_zone, crop_slot.service_lane)
                         if crop_slot is not None else
                         (animal_slot.service_zone, animal_slot.service_lane)
                         if animal_slot is not None else None),
                        (animal_slot.animal_kind if animal_slot is not None else None))
                    self.tile_work[coord] = work
                    if phase == "weed_dependency" and crop_slot is not None:
                        crop = crop_slot.crop
                        other_reserved = sum(value == crop
                                             for value in self.seed_reservations.values())
                        if int(seeds.get(crop, 0) or 0) <= other_reserved:
                            self.tile_work.pop(coord, None)
                            self.audit["weed_seed_reserve_race_prevented"] += 1
                            continue
                        self.seed_reservations[coord] = crop
                        work.reserved_seed = crop
                        self.audit["persistent_seed_reserved"] += 1
                self._set_work_ready(work, [(int(job[0]), tuple(job[3]))],
                                     work.phase, step)
            else:
                self.tile_work.pop(coord, None)

    def _target_state_valid(self, job: Job, grid: list[list[Any]],
                            seeds: dict[str, int]) -> bool:
        _priority, x, y, verb = job
        tile = self._tile_at(grid, (int(x), int(y)))
        op = str(verb[0])
        if op == "WATER":
            return isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                and not bool(tile.get("watered_today"))
        if op == "FEED":
            return bool(_animal(tile)) and not bool(tile.get("fed_today"))
        if op == "CARE":
            return bool(_animal(tile)) and not bool(tile.get("cared_today"))
        if op == "HARVEST":
            return isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
        if op == "COLLECT_FERTILIZER":
            return bool(_animal(tile)) and bool(tile.get("fertilizer_available"))
        if op == "PLANT":
            return tile is None and len(verb) > 1 \
                and int(seeds.get(str(verb[1]), 0) or 0) > 0
        if op == "PLACE":
            animal = str(verb[1]) if len(verb) > 1 else ""
            expected = "COOP" if animal == "GOOSE" else "PASTURE"
            return isinstance(tile, dict) and tile.get("kind") == expected and not _animal(tile)
        if op in {"BUILD_PASTURE", "BUILD_COOP"}:
            return tile is None
        if op == "DIG":
            return isinstance(tile, dict) and tile.get("kind") == "WEED"
        return True

    def _mark_tile_work_emitted(self, step: int, position: tuple[int, int],
                                verb: list[Any]) -> None:
        work = self.tile_work.get((int(position[0]), int(position[1])))
        head = self._head_job(work) if work is not None else None
        if work is None or head is None or str(head[3][0]) != str(verb[0]):
            return
        op = str(verb[0])
        if op == "HARVEST" and work.phase == "nonongoing_crop":
            work.phase = "await_empty"
            work.ready_ops = ()
        elif op == "DIG" and work.phase == "weed_dependency":
            work.phase = "await_weed_empty"
            work.ready_ops = ()
        elif op in {"BUILD_PASTURE", "BUILD_COOP"} \
                and work.species is not None:
            work.phase = "await_structure"
            work.ready_ops = ()
        elif op == "PLACE" and work.species is not None:
            work.phase = "await_animal"
            work.ready_ops = ()
        elif op == "PLANT":
            work.phase = ("await_replacement_plant"
                          if work.phase == "replacement_plant" else
                          "await_ordinary_plant")
            work.crop_if_needed = str(verb[1])
            work.ready_ops = ()
        elif op == "WATER" and work.phase == "planted_water":
            work.phase = "await_water"
            work.ready_ops = ()
        else:
            work.phase = "await_confirm"
            work.ready_ops = ()
        self.audit[f"tile_bundle_emitted_{op.lower()}"] += 1
        self._daily_add(self.day, f"tile_bundle_emitted_{op.lower()}")

    def _assign(self, units: list[Any], inventories: list[dict[str, Any]], jobs: list[Job],
                hour: int, lands: int, unavailable: set[int], day: int,
                step: int, grid: list[list[Any]] | None = None,
                seeds: dict[str, int] | None = None) -> dict[int, Job]:
        """Full-edge risk/slack/zone matcher over observation-valid heads."""
        grid = grid or []
        seeds = seeds or {}
        self._sync_tile_work(step, grid, jobs, seeds)
        # Ownership is a same-day reachability promise, never a season-long
        # reservation.  Day rollover clears it before any new matching.
        for work in self.tile_work.values():
            if work.owner is not None and work.owner_day != int(day):
                work.owner = None
                work.owner_day = None
                self.audit["owner_day_boundary_releases"] += 1
                self._daily_add(day, "owner_day_boundary_releases")
        leases: dict[int, list[TileWork]] = {}
        for work in self.tile_work.values():
            if work.owner is not None:
                leases.setdefault(int(work.owner), []).append(work)
        for owner, works in leases.items():
            ordered = sorted(works, key=lambda work: work.coord)
            for duplicate in ordered[1:]:
                duplicate.owner = None
                duplicate.owner_day = None
                self.audit["soft_lease_duplicate_repairs"] += 1
                self._daily_add(day, "soft_lease_duplicate_repairs")
        result: dict[int, Job] = {}
        free = {index for index, unit in enumerate(units) if unit and index not in unavailable}
        pending = {coord for coord, work in self.tile_work.items() if work.ready_ops}
        reserved_seeds = Counter(self.seed_reservations.values())
        seed_budget = Counter({
            crop: max(0, int(seeds.get(crop, 0) or 0) - int(reserved_seeds[crop]))
            for crop in CROPS
        })
        animal_slots, crop_slots = self.active_slot_contract(day)
        slot_by_coord = {slot.coord: slot for slot in (*animal_slots, *crop_slots)}

        for index in sorted(free):
            if index in self.tours and not self._tour_valid(index, day, step):
                self.tours.pop(index, None)
                self.sticky.pop(index, None)
                self.audit["tour_expired"] += 1
                self._daily_add(day, "tour_expired")

        def edge(index: int, coord: tuple[int, int]) \
                -> tuple[tuple[Any, ...], int, list[Any]] | None:
            work = self.tile_work[coord]
            job = self._head_job(work)
            validation_seeds = Counter(seed_budget)
            if job is not None and job[3][0] == "PLANT" and len(job[3]) > 1 \
                    and work.reserved_seed == str(job[3][1]):
                validation_seeds[str(job[3][1])] = max(
                    1, int(seeds.get(str(job[3][1]), 0) or 0))
            if job is None or not self._target_state_valid(job, grid, validation_seeds):
                return None
            pos = (int(units[index][0]), int(units[index][1]))
            path = self._bfs_first_step(grid, pos, coord)
            if path is None:
                return None
            distance, first_step = path
            inventory = dict(inventories[index] or {})
            cost = self._cost(index, pos, inventory, job, hour, lands)
            if not math.isfinite(cost):
                return None
            op = str(job[3][0])
            deadline = 23 if op in {"WATER", "FEED", "PLANT", "PLACE", "DIG"} else 24
            slack = int(deadline - int(hour) - distance - 1)
            if work.deadline_step is not None:
                slack = min(slack, int(work.deadline_step) - int(step) - distance)
            if slack < 0:
                return None
            task_slack = int(deadline - int(hour) - 1)
            confirmation = work.phase in {
                "await_empty", "await_replacement_plant", "await_ordinary_plant",
                "await_water", "await_confirm", "replacement_plant", "planted_water",
                "await_weed_empty", "await_structure", "await_animal",
                "structure_build", "structure_place"
            }
            if work.phase == "weed_dependency" or (op == "DIG" and int(job[0]) == 0):
                safety = 0
            elif op in PREEMPTIVE_OPS:
                safety = 0 if int(job[0]) == 0 or slack <= 1 else 1
            elif work.phase == "nonongoing_crop" and work.reserved_seed is not None:
                # A finite replacement option has already consumed its seed budget.
                # Letting an unrelated expansion head displace its HARVEST would
                # strand that reservation and break the deadline-safe closure.
                safety = 1
            elif confirmation:
                safety = 1
            elif op in PRIMARY_OPS:
                safety = 2
            else:
                safety = 3
            edge_key = (
                safety,
                task_slack,
                0 if work.owner == index else 1,
                0 if pos == coord else 1,
                0 if (pos in slot_by_coord and coord in slot_by_coord
                      and slot_by_coord[pos].service_zone == slot_by_coord[coord].service_zone
                      and slot_by_coord[pos].service_lane == slot_by_coord[coord].service_lane)
                else 1,
                0 if _quadrant(pos) == _job_zone(job) else 1,
                distance,
                _job_key(job),
                index,
                coord,
            )
            return edge_key, slack, first_step

        def claim(index: int, coord: tuple[int, int]) -> Job:
            work = self.tile_work[coord]
            job = self._head_job(work)
            assert job is not None
            result[index] = job
            free.remove(index)
            pending.discard(coord)
            if work.owner is not None and work.owner != index:
                self.audit["tile_bundle_owner_takeovers"] += 1
                self._daily_add(day, "tile_bundle_owner_takeovers")
            for other_coord, other_work in self.tile_work.items():
                if other_coord != coord and other_work.owner == index:
                    other_work.owner = None
                    other_work.owner_day = None
                    self.audit["soft_lease_releases"] += 1
                    self._daily_add(day, "soft_lease_releases")
            work.owner = index
            work.owner_day = int(day)
            if job[3][0] == "PLANT" and len(job[3]) > 1:
                if work.reserved_seed != str(job[3][1]):
                    seed_budget[str(job[3][1])] -= 1
            tour = self.tours.get(index)
            if job[3][0] not in PREEMPTIVE_OPS:
                if tour is not None and self._tour_valid(index, day, step) \
                        and _job_zone(job) == tour.zone:
                    tour.last_step = int(step)
                    tour.last_job_key = _job_key(job)
                else:
                    self.tours[index] = ActorTour(
                        day=int(day), zone=_job_zone(job), started_step=int(step),
                        last_step=int(step), last_job_key=_job_key(job))
                    self.audit["tour_started"] += 1
                    self._daily_add(day, "tour_started")
            self.audit["tile_bundle_assigned_full_edge"] += 1
            self._daily_add(day, "tile_bundle_assigned_full_edge")
            if job[3][0] in PREEMPTIVE_OPS:
                self.audit[f"preemptive_{str(job[3][0]).lower()}_assignments"] += 1
                self._daily_add(day, f"preemptive_{str(job[3][0]).lower()}_assignments")
            return job

        # Polynomial min-cost maximum flow over the complete finite frontier.
        # Crop nodes enforce observed seed quotas; task and actor capacities
        # enforce one coordinate/one actor.  This keeps the full frontier even
        # with eleven actors and many simultaneous confirmation PLANT heads.
        actor_order = tuple(sorted(free))
        crop_order = tuple(CROPS)
        edge_by_coord: dict[
            tuple[int, int], list[tuple[int, tuple[Any, ...], list[Any]]]] = {}
        edge_count = 0
        for coord in sorted(pending):
            options: list[tuple[int, tuple[Any, ...], list[Any]]] = []
            for index in actor_order:
                candidate_edge = edge(index, coord)
                if candidate_edge is not None:
                    options.append((index, candidate_edge[0], candidate_edge[2]))
                    edge_count += 1
            if options:
                edge_by_coord[coord] = options
        self.audit["scheduler_full_edges_evaluated"] += edge_count
        self._daily_add(day, "scheduler_full_edges_evaluated", edge_count)

        coords = tuple(sorted(edge_by_coord))
        stable_jobs = {key: rank for rank, key in enumerate(sorted(
            {_job_key(self._head_job(self.tile_work[coord]))
             for coord in coords
             if self._head_job(self.tile_work[coord]) is not None}))}
        coord_rank = {coord: rank for rank, coord in enumerate(coords)}
        flow_limit = max(1, len(actor_order))

        def scalar_cost(edge_key: tuple[Any, ...]) -> int:
            components = (
                int(edge_key[0]), int(edge_key[1]), int(edge_key[2]),
                int(edge_key[3]), int(edge_key[4]), int(edge_key[5]),
                int(edge_key[6]), int(stable_jobs[edge_key[7]]),
                int(edge_key[8]), int(coord_rank[edge_key[9]]),
            )
            maxima = (3, 23, 1, 1, 1, 1, 18,
                      max(0, len(stable_jobs) - 1),
                      max(actor_order, default=0), max(0, len(coords) - 1))
            value = components[0]
            for component, maximum in zip(components[1:], maxima[1:]):
                value = value * (flow_limit * int(maximum) + 1) + component
            return int(value)

        # Mutable edge: [to, reverse_index, residual_capacity, cost, metadata].
        source = 0
        crop_node = {crop: 1 + offset for offset, crop in enumerate(crop_order)}
        task_base = 1 + len(crop_order)
        task_node = {coord: task_base + offset for offset, coord in enumerate(coords)}
        actor_base = task_base + len(coords)
        actor_node = {index: actor_base + offset
                      for offset, index in enumerate(actor_order)}
        sink = actor_base + len(actor_order)
        graph: list[list[list[Any]]] = [[] for _ in range(sink + 1)]

        def add_edge(left: int, right: int, capacity: int, cost: int,
                     metadata: Any = None) -> None:
            forward = [right, len(graph[right]), int(capacity), int(cost), metadata]
            reverse = [left, len(graph[left]), 0, -int(cost), None]
            graph[left].append(forward)
            graph[right].append(reverse)

        for crop in crop_order:
            add_edge(source, crop_node[crop], max(0, int(seed_budget[crop])), 0)
        for coord in coords:
            work = self.tile_work[coord]
            job = self._head_job(work)
            assert job is not None
            reserved_plant = (job[3][0] == "PLANT" and len(job[3]) > 1
                              and work.reserved_seed == str(job[3][1]))
            if job[3][0] == "PLANT" and len(job[3]) > 1 \
                    and str(job[3][1]) in crop_node and not reserved_plant:
                add_edge(crop_node[str(job[3][1])], task_node[coord], 1, 0)
            else:
                add_edge(source, task_node[coord], 1, 0)
            for index, edge_key, first_step in edge_by_coord[coord]:
                add_edge(task_node[coord], actor_node[index], 1,
                         scalar_cost(edge_key), (index, coord, first_step))
        for index in actor_order:
            add_edge(actor_node[index], sink, 1, 0)

        flow = 0
        node_count = len(graph)
        while True:
            distance: list[int | None] = [None] * node_count
            parent: list[tuple[int, int] | None] = [None] * node_count
            queued = [False] * node_count
            queue = [source]
            queued[source] = True
            distance[source] = 0
            cursor = 0
            while cursor < len(queue):
                node = queue[cursor]
                cursor += 1
                queued[node] = False
                base = distance[node]
                assert base is not None
                for edge_index, residual in enumerate(graph[node]):
                    if int(residual[2]) <= 0:
                        continue
                    candidate_distance = base + int(residual[3])
                    target = int(residual[0])
                    if distance[target] is None or candidate_distance < distance[target]:
                        distance[target] = candidate_distance
                        parent[target] = (node, edge_index)
                        if not queued[target]:
                            queue.append(target)
                            queued[target] = True
            if parent[sink] is None:
                break
            node = sink
            while node != source:
                previous, edge_index = parent[node] or (source, 0)
                residual = graph[previous][edge_index]
                residual[2] -= 1
                graph[node][int(residual[1])][2] += 1
                node = previous
            flow += 1
            if flow >= len(actor_order):
                break

        matched: list[tuple[int, tuple[int, int], list[Any]]] = []
        for coord in coords:
            for residual in graph[task_node[coord]]:
                metadata = residual[4]
                if metadata is not None and int(residual[2]) == 0:
                    matched.append(metadata)
        self.audit["scheduler_max_flow"] += int(flow)
        self._daily_add(day, "scheduler_max_flow", int(flow))
        self._assigned_first_steps = {}
        for index, coord, first_step in sorted(matched):
            if index in free and coord in pending:
                self._assigned_first_steps[index] = list(first_step)
                claim(index, coord)

        self.audit["tile_bundle_claimed_coordinates"] += len(result)
        self._daily_add(day, "tile_bundle_claimed_coordinates", len(result))
        return result

    @staticmethod
    def _projected_shed(shed: dict[str, int], inventories: list[dict[str, Any]],
                        verbs: list[list[Any]]) -> dict[str, int]:
        projected = {key: int(value or 0) for key, value in shed.items()}
        total = sum(projected.values())
        for index, verb in enumerate(verbs):
            inventory = dict(inventories[index] or {})
            if verb[0] == "DROP":
                for item, quantity in inventory.items():
                    take = min(int(quantity or 0), max(0, SHED_CAPACITY - total))
                    projected[item] = projected.get(item, 0) + take
                    total += take
            elif verb[0] == "PICKUP" and len(verb) >= 3:
                item, quantity = verb[1], int(verb[2])
                projected[item] = max(0, projected.get(item, 0) - quantity)
                total = sum(projected.values())
        return projected

    def _feeder_overrides(self, jobs: list[Job], units: list[Any],
                          inventories: list[dict[str, Any]], shed: dict[str, int],
                          occupied: set[int] | None = None,
                          hour: int = 0) -> dict[int, list[Any]]:
        """Deadline-feasible carried supply plus parallel shed reservations."""
        occupied = occupied or set()
        feed_coords = [(int(job[1]), int(job[2])) for job in jobs
                       if job[3][0] == "FEED"]
        if not feed_coords:
            return {}
        deadline = 23
        carriers = [index for index, unit in enumerate(units)
                    if unit and index not in occupied
                    and int(dict(inventories[index] or {}).get("WHEAT", 0) or 0) > 0]
        matched_feed: dict[int, int] = {}

        def augment(index: int, seen: set[int]) -> bool:
            pos = (int(units[index][0]), int(units[index][1]))
            for feed_index, coord in sorted(
                    enumerate(feed_coords), key=lambda value: (_dist(pos, value[1]), value[1])):
                if feed_index in seen or int(hour) + _dist(pos, coord) > deadline:
                    continue
                seen.add(feed_index)
                if feed_index not in matched_feed \
                        or augment(matched_feed[feed_index], seen):
                    matched_feed[feed_index] = index
                    return True
            return False

        reachable_carried = sum(augment(index, set()) for index in carriers)
        gap = max(0, len(feed_coords) - int(reachable_carried))
        available = min(gap, int(shed.get("WHEAT", 0) or 0))
        if available <= 0:
            return {}
        candidates: list[tuple[int, int, tuple[int, int], tuple[int, int]]] = []
        for index, unit in enumerate(units):
            if not unit or index in occupied or index in carriers:
                continue
            pos = (int(unit[0]), int(unit[1]))
            gate = _shed_gate(pos)
            to_shed = 0 if pos in SHED_TILES else _dist(pos, gate)
            nearest_feed = min(feed_coords,
                               key=lambda coord: (_dist(gate, coord), coord))
            total_actions = to_shed + 1 + _dist(gate, nearest_feed) + 1
            if int(hour) + total_actions - 1 <= deadline:
                candidates.append((total_actions, index, pos, gate))
        overrides: dict[int, list[Any]] = {}
        for _total, index, pos, gate in sorted(candidates)[:available]:
            overrides[index] = (["PICKUP", "WHEAT", 1]
                                if pos in SHED_TILES else _toward(pos, gate))
        self.audit["feeder_global_unfed"] += len(feed_coords)
        self.audit["feeder_deadline_reachable_carriers"] += int(reachable_carried)
        self.audit["feeder_reserved_wheat_units"] += len(overrides)
        return overrides

    @staticmethod
    def _safe_unit_verb(verb: list[Any], position: tuple[int, int],
                        grid: list[list[Any]], inventory: dict[str, Any],
                        seeds: dict[str, int],
                        shed: dict[str, int] | None = None,
                        shed_capacity: int = SHED_CAPACITY) -> bool:
        """Fail closed for typed actions; movement and PASS remain unchanged."""
        if not verb:
            return False
        x, y = position
        tile = grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else "LOCKED"
        op = str(verb[0])
        unary = {"WATER", "FEED", "CARE", "HARVEST",
                 "COLLECT_FERTILIZER", "BUILD_PASTURE", "BUILD_COOP",
                 "DIG", "FERTILIZE", "DROP", "PASS",
                 "NORTH", "SOUTH", "EAST", "WEST"}
        if op in unary and len(verb) != 1:
            return False
        if op in {"PLANT", "PLACE"} and len(verb) != 2:
            return False
        if op == "PICKUP" and len(verb) != 3:
            return False
        if op == "WATER":
            return isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                and not bool(tile.get("watered_today"))
        if op == "FEED":
            return bool(_animal(tile)) and not bool(tile.get("fed_today")) \
                and int(inventory.get("WHEAT", 0) or 0) > 0
        if op == "CARE":
            return bool(_animal(tile)) and not bool(tile.get("cared_today"))
        if op == "PLACE":
            animal = str(verb[1])
            if animal not in ANIMALS:
                return False
            want = "COOP" if animal == "GOOSE" else "PASTURE"
            return isinstance(tile, dict) and tile.get("kind") == want \
                and not _animal(tile) and int(inventory.get(animal, 0) or 0) > 0
        if op == "PLANT":
            crop = str(verb[1])
            if crop not in CROPS:
                return False
            return tile is None and int(seeds.get(crop, 0) or 0) > 0
        if op == "HARVEST":
            return isinstance(tile, dict) and (
                (tile.get("kind") == "PLANT" and int(tile.get("yield_units", 0) or 0) > 0)
                or (bool(_animal(tile)) and int(tile.get("yield_units", 0) or 0) > 0))
        if op == "COLLECT_FERTILIZER":
            return bool(_animal(tile)) and bool(tile.get("fertilizer_available"))
        if op in {"BUILD_PASTURE", "BUILD_COOP"}:
            return tile is None
        if op == "DIG":
            return isinstance(tile, dict) and tile.get("kind") == "WEED"
        if op == "FERTILIZE":
            return isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                and int(inventory.get("FERTILIZER", 0) or 0) > 0
        if op == "PICKUP":
            item = str(verb[1])
            quantity = verb[2]
            return position in SHED_TILES and item in {*PRODUCTS, *ANIMALS} \
                and type(quantity) is int and quantity > 0 and shed is not None \
                and int(shed.get(item, 0) or 0) >= int(quantity)
        if op == "DROP":
            return position in SHED_TILES and shed is not None \
                and sum(int(value or 0) for value in shed.values()) \
                + sum(int(value or 0) for value in inventory.values()) \
                <= int(shed_capacity)
        if op == "PASS":
            return len(verb) == 1
        if op in {"NORTH", "SOUTH", "EAST", "WEST"} and len(verb) == 1:
            dx, dy = {"NORTH": (0, -1), "SOUTH": (0, 1),
                      "EAST": (1, 0), "WEST": (-1, 0)}[op]
            nx, ny = x + dx, y + dy
            return 0 <= ny < len(grid) and 0 <= nx < len(grid[ny])
        return False

    def _delivery_overrides(self, step: int, farm: dict[str, Any],
                            units: list[Any], inventories: list[dict[str, Any]],
                            shed: dict[str, int]) -> dict[int, list[Any]]:
        """Carry harvests in batches; return only for finance or liquidation."""
        overrides: dict[int, list[Any]] = {}
        terminal = step >= int(self.market_params["liquidation"])
        carried = [sum(int(value or 0) for value in dict(inv or {}).values())
                   for inv in inventories]
        total_carried = sum(carried)
        shed_room = max(0, SHED_CAPACITY - sum(int(value or 0) for value in shed.values()))
        finance_need = int(farm.get("money", 0) or 0) < FINANCE_DROP_FLOOR
        if not terminal and (not finance_need or total_carried < DELIVERY_BATCH or shed_room <= 0):
            return overrides
        candidates = [index for index, quantity in enumerate(carried)
                      if index < len(units) and units[index] and quantity > 0]
        if not terminal and candidates:
            candidates = [max(candidates, key=lambda index: (carried[index], -index))]
        for index in candidates:
            position = (int(units[index][0]), int(units[index][1]))
            overrides[index] = (["DROP"] if position in SHED_TILES
                                else _toward(position, _shed_gate(position)))
        if overrides:
            self.audit["terminal_delivery_dispatch" if terminal else "finance_batch_delivery_dispatch"] \
                += len(overrides)
        return overrides

    def _demand_now(self, obs: dict[str, Any]) -> Counter[str]:
        step = int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)
        demand: Counter[str] = Counter()
        if step % 4 == 0:
            for shop in list((obs.get("town") or {}).get("unlocked_shops", []) or []):
                goods = SHOP_PRODUCTS.get(str(shop), ())
                multiplier = 2 if len(goods) == 1 else 1
                for good in goods:
                    demand[good] += multiplier
        if step % 24 == 0:
            for good in PRODUCTS:
                if good != "FERTILIZER":
                    demand[good] += 1
        return demand

    @staticmethod
    def _wheat_buy_plan(requested: int, inventory: int, spendable: int,
                        shed_room: int) -> tuple[int, int]:
        """Mirror engine BUY_PRODUCT quotes at inventory-1, -2, ... per unit."""
        quantity = 0
        cumulative_cost = 0
        limit = min(max(0, int(requested)), max(0, int(shed_room)))
        for offset in range(limit):
            quote = market_price("WHEAT", int(inventory) - offset - 1)
            if cumulative_cost + quote > max(0, int(spendable)):
                break
            cumulative_cost += quote
            quantity += 1
        return quantity, cumulative_cost

    @staticmethod
    def _terminal_closure_cardinality(
            step: int, grid: list[list[Any]], seeds: dict[str, int],
            actors: list[tuple[tuple[int, int], int]]) -> int:
        """One-option-per-actor conservative deadline matching."""
        remaining = Counter({crop: int(seeds.get(crop, 0) or 0) for crop in CROPS})
        options: list[tuple[tuple[int, int], int, str]] = []
        raw: list[tuple[int, tuple[int, int], str]] = []
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                    continue
                crop = str(tile.get("crop") or "")
                if crop not in NON_ONGOING or int(tile.get("yield_units", 0) or 0) <= 0:
                    continue
                lifespan = int(tile.get("max_lifespan_step", -1) or -1)
                if lifespan < 0:
                    continue
                weed_step = lifespan + 2 * max(
                    0, int(tile.get("yield_units", 0) or 0) - 1)
                if weed_step < 720:
                    raw.append((weed_step, (x, y), crop))
        for deadline, coord, crop in sorted(raw):
            if remaining[crop] <= 0:
                continue
            remaining[crop] -= 1
            options.append((coord, min(719, int(deadline)), crop))
        matched: dict[int, int] = {}

        def augment(actor_index: int, seen: set[int]) -> bool:
            position, available_step = actors[actor_index]
            for option_index, (coord, deadline, _crop) in sorted(
                    enumerate(options), key=lambda value: (value[1][1], value[1][0])):
                if option_index in seen:
                    continue
                if int(available_step) + _dist(position, coord) + 2 >= int(deadline):
                    continue
                seen.add(option_index)
                if option_index not in matched \
                        or augment(matched[option_index], seen):
                    matched[option_index] = actor_index
                    return True
            return False

        return sum(augment(index, set()) for index in range(len(actors)))

    def _safe_terminal_hire(self, step: int, farm: dict[str, Any],
                            grid: list[list[Any]], seeds: dict[str, int],
                            money: int, reserve: int) -> bool:
        if int(step) < SETTLEMENT_PURCHASE_CUTOFF_STEP:
            return False
        units = [farm.get("farmer")] + list(farm.get("hands", []) or [])
        positions = [(int(unit[0]), int(unit[1])) for unit in units if unit]
        if not positions or len(positions) >= LABOR_HAND_CAP:
            return False
        actors = [(position, int(step)) for position in positions]
        before = self._terminal_closure_cardinality(step, grid, seeds, actors)
        occupancy = Counter(positions)
        spawn = min(SHED_TILES,
                    key=lambda coord: (int(occupancy[coord]), SHED_TILES.index(coord)))
        after = self._terminal_closure_cardinality(
            step, grid, seeds, actors + [(spawn, int(step) + 1)])
        cost = _fib(int(farm.get("hires_today", 0) or 0))
        safe = after > before and int(money) - int(cost) >= int(reserve)
        if safe:
            self.audit["settlement_safe_hire_closure_gain"] += after - before
        return safe

    def _market(self, obs: dict[str, Any], farm: dict[str, Any], grid: list[list[Any]],
                goal: dict[str, Any], seeds: dict[str, int], projected: dict[str, int],
                inventories: list[dict[str, Any]], pending_plants: Counter[str],
                true_harvests: Counter[str]) -> list[list[Any]]:
        step = int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)
        money = int(farm.get("money", 0) or 0)
        crop_have, animal_have, _structures = _counts(grid)
        carried = _inventory_totals(inventories)
        total = sum(projected.values())
        terminal = step >= int(self.market_params["liquidation"])
        settlement_purchase_closed = step >= SETTLEMENT_PURCHASE_CUTOFF_STEP
        demand_now = self._demand_now(obs)
        prices = (obs.get("market") or {}).get("prices", {}) or {}
        market_inventory = (obs.get("market") or {}).get("inventory", {}) or {}

        purchases: list[tuple[int, list[Any], int]] = []
        feed_gap = max(0, int(goal["feed_reserve"]) - int(projected.get("WHEAT", 0)) - carried["WHEAT"])
        hires_today = int(farm.get("hires_today", len(farm.get("hands", []) or [])) or 0)
        feed_quote = market_price("WHEAT", int(market_inventory.get("WHEAT", 10000) or 10000) - 33)
        reserve = max(150, _fib(hires_today) + feed_gap * feed_quote)
        if feed_gap:
            purchases.append((100, ["BUY_PRODUCT", "WHEAT", min(feed_gap, 18)],
                              int(prices.get("WHEAT", 25) or 25)))
        current_hands = len(farm.get("hands", []) or [])
        for offset in range(max(0, min(LABOR_HAND_CAP, int(goal["hands"])) - current_hands)):
            purchases.append((92, ["HIRE"], _fib(hires_today + offset)))
        for kind in ("SHEEP", "COW", "GOOSE"):
            target = int(goal["animals"].get(kind, 0))
            have = animal_have[kind] + int(projected.get(kind, 0)) + carried[kind]
            if target > have:
                purchases.append((88, ["BUY_ANIMAL", kind, target - have], ANIMALS[kind]["cost"]))
        # Fair seed batch: total <=12, every positive gap gets one before
        # extras, and no product monopolises more than 40% of the batch.
        gaps = {
            crop: max(0, int(goal["crops"].get(crop, 0))
                      - max(0, crop_have[crop] - true_harvests[crop])
                      - int(seeds.get(crop, 0) or 0) - pending_plants[crop])
            for crop in CROPS
        }
        batch_size = min(12, sum(gaps.values()))
        seed_batch: Counter[str] = Counter()
        if batch_size:
            per_crop_cap = max(1, math.ceil(.4 * batch_size))
            ranked = sorted((crop for crop in CROPS if gaps[crop] > 0),
                            key=lambda crop: (-(gaps[crop] / max(1, int(goal["crops"].get(crop, 0)))),
                                              list(CROPS).index(crop)))
            for crop in ranked:
                if sum(seed_batch.values()) >= batch_size:
                    break
                seed_batch[crop] += 1
            while sum(seed_batch.values()) < batch_size:
                choices = [crop for crop in ranked
                           if seed_batch[crop] < min(gaps[crop], per_crop_cap)]
                if not choices:
                    break
                crop = max(choices, key=lambda value: ((gaps[value] - seed_batch[value])
                                                        / max(1, int(goal["crops"].get(value, 0))),
                                                       -list(CROPS).index(value)))
                seed_batch[crop] += 1
        for crop in CROPS:
            if seed_batch[crop]:
                purchases.append((80, ["BUY_SEED", crop, seed_batch[crop]], CROPS[crop]["seed"]))
        lands = len(farm.get("unlocked_quadrants", []) or [])
        if lands < int(goal["lands"]):
            purchases.append((70, ["BUY_LAND"], LAND_PRICES[max(0, lands - 1)]))
        purchases.sort(key=lambda value: -value[0])
        if settlement_purchase_closed:
            self.audit["settlement_purchases_suppressed"] += len(purchases)
            purchases = ([(101, ["HIRE"],
                           _fib(int(farm.get("hires_today", 0) or 0)))]
                         if self._safe_terminal_hire(
                             step, farm, grid, seeds, money, reserve) else [])

        rough = reserve
        for _priority, order, unit_cost in purchases[:9]:
            if order[0] == "BUY_PRODUCT" and len(order) >= 3 and order[1] == "WHEAT":
                _quantity, quoted_cost = self._wheat_buy_plan(
                    int(order[2]), int(market_inventory.get("WHEAT", 10000) or 10000),
                    1 << 60, SHED_CAPACITY - total)
                rough += quoted_cost
            else:
                rough += unit_cost * (int(order[2]) if len(order) >= 3 else 1)
        financing = max(0, rough - money)
        saleable = {good: max(0, int(projected.get(good, 0))
                                      - (int(goal["feed_reserve"]) if good == "WHEAT" and not terminal else 0))
                    for good in PRODUCTS}
        pressure = total >= int(self.market_params["pressure"])
        sale_quantities: Counter[str] = Counter()
        finance_stress = int(self.market_params["finance_stress"])
        ordinary_stress = int(self.market_params["ordinary_stress"])
        for good in sorted(PRODUCTS,
                           key=lambda item: (-market_price(item, int(market_inventory.get(item, 10000) or 10000)
                                                          + finance_stress),
                                             PRODUCTS.index(item))):
            while financing > 0 and sale_quantities[good] < saleable[good]:
                quote = market_price(good, int(market_inventory.get(good, 10000) or 10000)
                                     + finance_stress + sale_quantities[good])
                sale_quantities[good] += 1
                financing -= quote
        for good in PRODUCTS:
            left = saleable[good] - sale_quantities[good]
            if left <= 0 or (demand_now[good] > 0 and not pressure and not terminal):
                continue
            quote = market_price(good, int(market_inventory.get(good, 10000) or 10000)
                                 + ordinary_stress + sale_quantities[good])
            if terminal or pressure or quote >= max(1, int(BASE_PRICE[good]
                                                            * float(self.market_params["sale_floor"]))):
                sale_quantities[good] += (left if terminal else
                                          min(left, int(self.market_params["regular_cap"])))

        orders: list[list[Any]] = []
        for good in sorted((name for name, count in sale_quantities.items() if count > 0),
                           key=lambda item: (-int(prices.get(item, BASE_PRICE[item]) or 1), PRODUCTS.index(item))):
            if len(orders) >= 10:
                break
            quantity = sale_quantities[good]
            orders.append(["SELL", good, quantity])
            # Conservative slippage: each additional unit is worth no more
            # than the currently visible price.
            level = int(market_inventory.get(good, 10000) or 10000)
            money += sum(market_price(good, level + finance_stress + offset)
                         for offset in range(quantity))
            total -= quantity
            projected[good] = max(0, projected.get(good, 0) - quantity)

        for _priority, raw, unit_cost in purchases:
            if len(orders) >= 10:
                break
            op = raw[0]
            requested = int(raw[2]) if len(raw) >= 3 else 1
            purchase_cost = 0
            if op == "BUY_PRODUCT" and len(raw) >= 2 and raw[1] == "WHEAT":
                quantity, purchase_cost = self._wheat_buy_plan(
                    requested, int(market_inventory.get("WHEAT", 10000) or 10000),
                    money - reserve, SHED_CAPACITY - total)
                self.audit["wheat_buy_quoted_units"] += quantity
                self.audit["wheat_buy_quoted_cost"] += purchase_cost
            elif op == "BUY_PRODUCT":
                quantity = min(requested, (money - reserve) // max(1, unit_cost),
                               SHED_CAPACITY - total)
                purchase_cost = int(unit_cost) * int(quantity)
            elif op == "BUY_ANIMAL":
                quantity = min(requested, (money - reserve) // max(1, unit_cost), SHED_CAPACITY - total)
                purchase_cost = int(unit_cost) * int(quantity)
            elif op == "BUY_SEED":
                quantity = min(requested, (money - reserve) // max(1, unit_cost))
                purchase_cost = int(unit_cost) * int(quantity)
            else:
                quantity = int(money - unit_cost >= reserve)
                purchase_cost = int(unit_cost) * int(quantity)
            if quantity <= 0:
                self.audit["purchase_withheld_budget"] += 1
                continue
            order = list(raw) if len(raw) < 3 else [raw[0], raw[1], int(quantity)]
            orders.append(order)
            money -= purchase_cost
            if op in {"BUY_PRODUCT", "BUY_ANIMAL"}:
                total += int(quantity)
        return orders[:10]

    def act(self, obs: dict[str, Any]) -> dict[str, Any]:
        step = int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)
        self._reconcile_receipts(step)
        self._route(obs)
        seat = self._seat(obs)
        day = min(29, int(obs.get("day", 0) or 0))
        hour = int(obs.get("hour", 0) or 0)
        if day != self.day:
            if self.day >= 0:
                self.audit["tours_closed_at_day_boundary"] += len(self.tours)
                self._daily_add(self.day, "tours_closed_at_day_boundary", len(self.tours))
            self.tours.clear()
            self.sticky.clear()
            self.day = day
        goal = self.goal(day)
        farm = (obs.get("farms") or [{}, {}])[seat]
        grid = list(farm.get("tiles", []) or [])
        private = obs.get("private", {}) or {}
        seeds = dict(private.get("seeds", {}) or {})
        shed = dict(private.get("shed", {}) or {})
        inventories = list(private.get("inventories", []) or [])
        units = [farm.get("farmer")] + list(farm.get("hands", []) or [])
        while len(inventories) < len(units):
            inventories.append({})
        self._reconcile_product_batches(step, shed, inventories)
        self._reconcile_harvests(step, shed, inventories)
        jobs = self._jobs(day, hour, units, grid, goal, seeds, goal)
        for job in jobs:
            op = str(job[3][0]).lower()
            self.audit[f"job_generated_{op}"] += 1
            self._daily_add(day, f"job_generated_{op}")
        planned_plants = sum(job[3][0] == "PLANT" for job in jobs)
        self.audit["plant_jobs_planned"] += planned_plants
        self._daily_add(day, "plant_jobs_planned", planned_plants)
        synthetic: dict[int, list[Any]] = {}

        synthetic.update(self._feeder_overrides(
            jobs, units, inventories, shed, set(synthetic), hour))
        for job in jobs:
            if job[3][0] != "PLACE":
                continue
            kind = job[3][1]
            if any(int(dict(value or {}).get(kind, 0) or 0) > 0 for value in inventories):
                continue
            if int(shed.get(kind, 0) or 0) <= 0:
                continue
            candidates = [i for i in range(len(units)) if i not in synthetic]
            if candidates:
                index = min(candidates, key=lambda i: _dist(tuple(units[i]), _shed_gate(tuple(units[i]))))
                pos = tuple(units[index])
                synthetic[index] = ["PICKUP", kind, 1] if pos in SHED_TILES else _toward(pos, _shed_gate(pos))
            break

        delivery = self._delivery_overrides(step, farm, units, inventories, shed)
        terminal = step >= int(self.market_params["liquidation"])
        for index, verb in delivery.items():
            if terminal or index not in synthetic:
                synthetic[index] = verb

        assignments = self._assign(units, inventories, jobs, hour, int(goal["lands"]),
                                   set(synthetic), day, step, grid, seeds)
        verbs: list[list[Any]] = []
        for index, unit in enumerate(units):
            pos = (int(unit[0]), int(unit[1]))
            if index in synthetic:
                verb = synthetic[index]
            elif index in assignments:
                priority, x, y, task = assignments[index]
                self.sticky[index] = _job_key(assignments[index])
                assigned_op = str(task[0]).lower()
                self.audit[f"job_assigned_{assigned_op}"] += 1
                self._daily_add(day, f"job_assigned_{assigned_op}")
                verb = (list(task) if pos == (x, y)
                        else list(self._assigned_first_steps.get(index, PASS)))
            else:
                self.sticky.pop(index, None)
                verb = PASS.copy()
            inventory = dict(inventories[index] or {}) if index < len(inventories) else {}
            if not self._safe_unit_verb(verb, pos, grid, inventory, seeds, shed):
                self.audit[f"invalid_{str(verb[0]).lower()}_prevented"] += 1
                self.sticky.pop(index, None)
                verb = PASS.copy()
            if verb[0] == "PLANT" and len(verb) > 1 \
                    and self.replacement_credits[str(verb[1])] > 0:
                self.replacement_credits[str(verb[1])] -= 1
                self.audit["replacement_credit_consumed"] += 1
            if index in assignments and verb[0] == assignments[index][3][0]:
                emitted_op = str(verb[0]).lower()
                self.audit[f"job_emitted_{emitted_op}"] += 1
                self._daily_add(day, f"job_emitted_{emitted_op}")
                self._mark_tile_work_emitted(step, pos, verb)
            if verb[0] == "PLANT" and len(verb) > 1:
                crop = str(verb[1])
                self.crop_cursor = (self.crop_cursor + 1) % len(CROPS)
                event = {"step": int(step), "crop": crop,
                         "zone": QUADRANTS[_quadrant(pos)],
                         "shed_distance": _shed_distance(pos)}
                self.actual_plant_events.append(event)
                self.audit[f"actual_plant_crop_{crop.lower()}"] += 1
                self.audit[f"actual_plant_zone_{str(event['zone']).lower()}"] += 1
                self.audit["actual_plant_shed_distance"] += int(event["shed_distance"])
            verbs.append(verb)
            self.audit[f"action_{verb[0].lower()}"] += 1
            self._daily_add(day, f"action_{verb[0].lower()}")
            if verb[0] in {"NORTH", "SOUTH", "EAST", "WEST"}:
                self.audit["directional_moves"] += 1
                self._daily_add(day, "directional_moves")
        projected = self._projected_shed(shed, inventories, verbs)
        pending_plants: Counter[str] = Counter(
            verb[1] for verb in verbs if verb and verb[0] == "PLANT" and len(verb) > 1
        )
        self._record_harvest_batch(step, grid, units, verbs, shed, inventories)
        true_harvests = self._true_eligible_harvests(grid, units, verbs)
        market = self._market(obs, farm, grid, goal, seeds, projected, inventories,
                              pending_plants, true_harvests)
        self._record_receipts(step, market)
        self._record_product_batch(step, day, shed, inventories,
                                   grid, units, verbs, market)
        self.last_step = step
        self.audit["calls"] += 1
        self.audit["jobs_generated"] += len(jobs)
        self._daily_add(day, "calls")
        self._daily_add(day, "jobs_generated", len(jobs))
        return {"farmer": verbs[0] if verbs else PASS.copy(), "hands": verbs[1:], "market": market}

    @staticmethod
    def _ledger_snapshot(ledger: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
        return {
            product: {field: int(quantity) for field, quantity in sorted(fields.items())
                      if int(quantity) != 0}
            for product, fields in sorted(ledger.items())
        }

    def daily_diagnostics(self) -> list[dict[str, Any]]:
        days = sorted(set(self.daily_product_ledger) | set(self.daily_operations))
        return [
            {"day": int(day),
             "operations": {field: int(quantity) for field, quantity
                            in sorted(self.daily_operations.get(day, {}).items())},
             "products": self._ledger_snapshot(self.daily_product_ledger.get(
                 day, {product: Counter() for product in PRODUCTS}))}
            for day in days
        ]

    def terminal_diagnostic(self) -> dict[str, Any]:
        pending_buy: Counter[str] = Counter()
        pending_sell: Counter[str] = Counter()
        pending_harvest: Counter[str] = Counter()
        for batch in self.pending_product_batches:
            pending_buy.update(batch.buy_requested)
            pending_sell.update(batch.sell_requested)
            pending_harvest.update(batch.harvest_attempted)
        return {
            "last_step": int(self.last_step),
            "last_day": int(self.day),
            "observed_products": {product: int(self.last_product_totals[product])
                                  for product in PRODUCTS},
            "pending_buy_requested": dict(sorted(pending_buy.items())),
            "pending_sell_requested": dict(sorted(pending_sell.items())),
            "pending_harvest_attempted": dict(sorted(pending_harvest.items())),
            "active_tours": {str(index): asdict(tour)
                             for index, tour in sorted(self.tours.items())},
            "actual_plant_events": list(self.actual_plant_events),
            "tile_work": [asdict(work) for _coord, work in sorted(self.tile_work.items())],
            "directional_moves": int(self.audit["directional_moves"]),
            "calls": int(self.audit["calls"]),
        }

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "strategy_parent": STRATEGY_PARENT,
            "expert": self.expert,
            "committed": self.committed,
            "commit_step": self.commit_step,
            "first_shops": list(self.first_shops),
            "pending_receipts": [asdict(receipt) for receipt in self.pending_receipts],
            "pending_harvests": [asdict(batch) for batch in self.pending_harvests],
            "pending_product_batches": [asdict(batch) for batch in self.pending_product_batches],
            "replacement_credits": dict(sorted(self.replacement_credits.items())),
            "actual_plant_events": list(self.actual_plant_events),
            "tile_work": [asdict(work) for _coord, work in sorted(self.tile_work.items())],
            "product_ledger": self._ledger_snapshot(self.product_ledger),
            "daily_diagnostics": self.daily_diagnostics(),
            "terminal_diagnostic": self.terminal_diagnostic(),
            "audit": dict(sorted(self.audit.items())),
            "params_hash": canonical_hash(self.params),
        }


def build_executor(params: dict[str, Any] | None = None, mode: str = "router") -> ShopRouterExecutor:
    params = copy.deepcopy(DEFAULT_PARAMS if params is None else params)
    errors = validate_params(params)
    if errors:
        raise ValueError("; ".join(errors))
    if mode == "router":
        return ShopRouterExecutor(params)
    fixed = mode.removeprefix("fixed_")
    if fixed in EXPERT_NAMES:
        return ShopRouterExecutor(params, fixed_expert=fixed)
    raise ValueError(f"unknown mode {mode!r}")


def freeze_candidate(params: dict[str, Any], output_main_py: str | os.PathLike[str]) -> str:
    """Atomically freeze validated parameters into a self-contained main.py."""
    errors = validate_params(params)
    if errors:
        raise ValueError("; ".join(errors))
    source = Path(__file__).read_text(encoding="utf-8")
    start_marker = "# <DEFAULT_PARAMS_START>"
    end_marker = "# <DEFAULT_PARAMS_END>"
    before, rest = source.split(start_marker, 1)
    _old, after = rest.split(end_marker, 1)
    frozen_json = canonical_json(params)
    replacement = (f"{start_marker}\nDEFAULT_PARAMS: dict[str, Any] = "
                   f"json.loads({frozen_json!r})\n{end_marker}")
    frozen_source = before + replacement + after
    compile(frozen_source, str(output_main_py), "exec")
    output = Path(output_main_py)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(frozen_source, encoding="utf-8")
    os.replace(temporary, output)
    return canonical_hash(params)


DEFAULT_PARAMS_HASH = canonical_hash(DEFAULT_PARAMS)


def make_agent() -> Any:
    return build_executor(DEFAULT_PARAMS).act


_EXECUTOR: ShopRouterExecutor | None = None


def agent(obs: dict[str, Any]) -> dict[str, Any]:
    global _EXECUTOR
    if _EXECUTOR is None or int(obs.get("step", 0) or 0) == 0:
        _EXECUTOR = build_executor(DEFAULT_PARAMS, "router")
    return _EXECUTOR.act(obs)


__all__ = [
    "PARAM_SPEC", "ParamSpec", "DEFAULT_PARAMS", "DEFAULT_PARAMS_HASH", "EXPERT_NAMES",
    "SCHEMA", "STRATEGY_PARENT", "MODES", "PendingReceipt", "PendingProductBatch",
    "AnimalSlot", "CropSlot", "ExpertSlotContract", "ActorTour", "TileWork",
    "ShopRouterExecutor", "TOUR_MAX_STEPS", "PLACEMENT_RING", "agent",
    "build_executor", "canonical_hash", "canonical_json", "compile_genomes",
    "compile_slot_contract", "compile_slot_contracts", "freeze_candidate",
    "make_agent", "route_expert", "validate_params",
]
