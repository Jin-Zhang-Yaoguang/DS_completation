#!/usr/bin/env python3
"""V116 R18: semantic-bundle restore, self-contained hierarchical rule MoE.

Five experts compile compact aggregate parameters into thirty daily goals.
It stores no recorded action table or coordinate route; every action is
regenerated from the current observation.  R18 keeps the cap-eleven value
backbone and settlement safety, then adds semantic target locking, unique-tile
ownership, a confirmed non-ongoing HARVEST->PLANT->WATER chain, one growth lane
and a strict late asset-restoration budget.  It imports no strategy.
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
SCHEMA = "v116-r18-semantic-bundle-restore-hmoe-v1"
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
ASSET_GUARD_START_DAY = 27
GROWTH_LANE_CAP = 1
CHAIN_SEED_BUFFER_CAP = 3

BUNDLE_OP_RANK = {
    "WATER": 0,
    "FEED": 1,
    "PLANT": 2,
    "HARVEST": 3,
    "PLACE": 4,
    "BUILD_PASTURE": 5,
    "BUILD_COOP": 5,
    "CARE": 6,
    "COLLECT_FERTILIZER": 7,
    "DIG": 8,
}


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
class GrowthChain:
    owner: int
    x: int
    y: int
    crop: str
    state: str
    opened_step: int
    action_step: int


def _job_key(job: Job) -> tuple[Any, ...]:
    """Semantic target identity: priority changes never invalidate a lock."""
    _priority, x, y, verb = job
    return (verb[0], x, y, *verb[1:])


def _job_coord(job: Job) -> tuple[int, int]:
    return (int(job[1]), int(job[2]))


def _key_coord(key: tuple[Any, ...]) -> tuple[int, int]:
    return (int(key[1]), int(key[2]))


def _bundle_jobs(jobs: list[Job]) -> list[Job]:
    """One tile, one owner: retain only the highest-priority semantic op."""
    selected: dict[tuple[int, int], Job] = {}
    for job in jobs:
        coord = _job_coord(job)
        edge = (int(job[0]), int(BUNDLE_OP_RANK.get(str(job[3][0]), 99)), _job_key(job))
        current = selected.get(coord)
        if current is None:
            selected[coord] = job
            continue
        current_edge = (int(current[0]),
                        int(BUNDLE_OP_RANK.get(str(current[3][0]), 99)),
                        _job_key(current))
        if edge < current_edge:
            selected[coord] = job
    return sorted(selected.values(), key=lambda job: (int(job[0]),
                                                       BUNDLE_OP_RANK.get(str(job[3][0]), 99),
                                                       _job_key(job)))


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
        self.growth_chains: list[GrowthChain] = []
        self.bundle_followups: dict[int, tuple[int, int, int]] = {}
        self.actual_plant_events: list[dict[str, Any]] = []
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
        instrumented measurement module, not to this candidate-side ledger.
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

    @staticmethod
    def _tile_at(grid: list[list[Any]], x: int, y: int) -> Any:
        return grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else "LOCKED"

    def _reconcile_growth_chains(self, step: int, grid: list[list[Any]]) -> None:
        retained: list[GrowthChain] = []
        for chain in self.growth_chains:
            tile = self._tile_at(grid, chain.x, chain.y)
            if int(step) <= chain.action_step:
                retained.append(chain)
                continue
            if chain.state == "await_empty":
                if tile is None:
                    chain.state = "plant_ready"
                    self.audit["growth_chain_empty_confirmed"] += 1
                    retained.append(chain)
                else:
                    self.audit["growth_chain_harvest_unconfirmed"] += 1
            elif chain.state == "await_plant":
                if isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == chain.crop:
                    chain.state = "water_ready"
                    self.audit["growth_chain_plant_confirmed"] += 1
                    retained.append(chain)
                elif tile is None:
                    chain.state = "plant_ready"
                    self.audit["growth_chain_plant_retry"] += 1
                    retained.append(chain)
                else:
                    self.audit["growth_chain_plant_conflict"] += 1
            elif chain.state == "await_water":
                if isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == chain.crop \
                        and bool(tile.get("watered_today")):
                    self.audit["growth_chain_completed"] += 1
                elif isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                        and str(tile.get("crop")) == chain.crop:
                    chain.state = "water_ready"
                    self.audit["growth_chain_water_retry"] += 1
                    retained.append(chain)
                else:
                    self.audit["growth_chain_water_conflict"] += 1
            else:
                retained.append(chain)
        self.growth_chains = retained

    def _ready_chain_job(self, grid: list[list[Any]], seeds: dict[str, int]) \
            -> tuple[int, Job, GrowthChain] | None:
        for chain in sorted(self.growth_chains,
                            key=lambda value: (value.opened_step, value.x, value.y, value.owner)):
            tile = self._tile_at(grid, chain.x, chain.y)
            if chain.state == "plant_ready" and tile is None \
                    and int(seeds.get(chain.crop, 0) or 0) > 0:
                return chain.owner, (0, chain.x, chain.y, ("PLANT", chain.crop)), chain
            if chain.state == "water_ready" and isinstance(tile, dict) \
                    and tile.get("kind") == "PLANT" \
                    and str(tile.get("crop")) == chain.crop \
                    and not bool(tile.get("watered_today")):
                return chain.owner, (0, chain.x, chain.y, ("WATER",)), chain
        return None

    def _chain_seed_needs(self, additional: Counter[str] | None = None) -> Counter[str]:
        needs: Counter[str] = Counter(additional or {})
        for chain in self.growth_chains:
            if chain.state in {"await_empty", "plant_ready", "await_plant"}:
                needs[chain.crop] += 1
        return Counter({crop: min(CHAIN_SEED_BUFFER_CAP, int(needs[crop]))
                        for crop in NON_ONGOING if int(needs[crop]) > 0})

    def _ready_bundle_followups(self, step: int, jobs: list[Job]) -> dict[int, Job]:
        """Offer exactly-next-observation same-tile work to the prior owner."""
        by_coord = {_job_coord(job): job for job in jobs
                    if job[3][0] in {"HARVEST", "CARE", "COLLECT_FERTILIZER"}}
        claims: dict[int, Job] = {}
        retained: dict[int, tuple[int, int, int]] = {}
        for owner, (action_step, x, y) in sorted(self.bundle_followups.items()):
            if int(step) <= int(action_step):
                retained[int(owner)] = (int(action_step), int(x), int(y))
                continue
            if int(step) == int(action_step) + 1 and (int(x), int(y)) in by_coord:
                claims[int(owner)] = by_coord[(int(x), int(y))]
        self.bundle_followups = retained
        return claims

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

    def _jobs(self, day: int, hour: int, units: list[Any], grid: list[list[Any]],
              goal: dict[str, Any], seeds: dict[str, int],
              structure_goal: dict[str, Any]) -> list[Job]:
        jobs: list[Job] = []
        crop_have, animal_have, structures = _counts(grid)
        productive_assets = sum(crop_have.values()) + sum(animal_have.values())
        destructive_budget = (max(0, productive_assets - TERMINAL_ASSET_FLOOR)
                              if int(day) >= ASSET_GUARD_START_DAY else 1 << 30)
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict):
                    continue
                kind = tile.get("kind")
                if kind == "PLANT":
                    crop = tile.get("crop")
                    facts = CROPS.get(crop) or {}
                    planted = tile.get("planted_day")
                    age = day - (day if planted is None else int(planted))
                    if not tile.get("watered_today"):
                        urgent = int(tile.get("consecutive_unwatered", 0) or 0) >= 1
                        jobs.append((0 if urgent else 2, x, y, ("WATER",)))
                    yield_units = int(tile.get("yield_units", 0) or 0)
                    ripe = bool(facts.get("ongoing")) or yield_units >= int(facts.get("max_yield", 99)) \
                        or age >= int(facts.get("max_day", 99))
                    if yield_units > 0 and age >= int(facts.get("first", 0)) and ripe:
                        destructive = crop in NON_ONGOING
                        if destructive and int(day) >= ASSET_GUARD_START_DAY:
                            if destructive_budget <= 0:
                                continue
                            destructive_budget -= 1
                        jobs.append((int(self.auction["harvest_priority"]), x, y, ("HARVEST",)))
                elif _animal(tile):
                    if not tile.get("fed_today"):
                        jobs.append((1, x, y, ("FEED",)))
                    if int(tile.get("yield_units", 0) or 0) > 0:
                        jobs.append((int(self.auction["harvest_priority"]), x, y, ("HARVEST",)))
                    if tile.get("fertilizer_available"):
                        jobs.append((5, x, y, ("COLLECT_FERTILIZER",)))
                    if not tile.get("cared_today"):
                        jobs.append((6, x, y, ("CARE",)))
                elif kind == "WEED":
                    jobs.append((7, x, y, ("DIG",)))

        available = set((x, y) for x, y in _unlocked(grid) if grid[y][x] is None)
        pasture_goal = (int(structure_goal["animals"].get("SHEEP", 0))
                        + int(structure_goal["animals"].get("COW", 0)))
        coop_goal = int(structure_goal["animals"].get("GOOSE", 0))
        for structure, count in (("PASTURE", max(0, pasture_goal - structures["PASTURE"])),
                                 ("COOP", max(0, coop_goal - structures["COOP"]))):
            for _ in range(min(count, len(available))):
                x, y = _placement_order(list(available), structure)[0]
                available.remove((x, y))
                jobs.append((4, x, y, ("BUILD_PASTURE" if structure == "PASTURE" else "BUILD_COOP",)))

        deficit = {kind: max(0, int(goal["animals"].get(kind, 0)) - animal_have[kind]) for kind in ANIMALS}
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or _animal(tile):
                    continue
                compatible = (("GOOSE",) if tile.get("kind") == "COOP" else
                              ("SHEEP", "COW") if tile.get("kind") == "PASTURE" else ())
                for kind in compatible:
                    if deficit[kind] > 0:
                        jobs.append((int(self.auction["place_priority"]), x, y, ("PLACE", kind)))
                        deficit[kind] -= 1
                        break

        # Fair replacement: repeatedly serve the lowest realised target ratio.
        # Unlike R12 this is a parallel admission budget, not a global one-bundle
        # lock.  Every admitted PLANT reserves enough remaining unit-actions for
        # travel/plant plus a same-day WATER pass.
        plantable = list(available)
        assigned: Counter[str] = Counter()
        budgets = {crop: int(seeds.get(crop, 0) or 0) for crop in CROPS}
        unit_positions = [(int(unit[0]), int(unit[1])) for unit in units if unit]
        maintenance_work = 0
        for _priority, x, y, verb in jobs:
            if verb[0] not in {"WATER", "FEED", "CARE"}:
                continue
            travel = min((_dist(position, (x, y)) for position in unit_positions), default=20)
            maintenance_work += travel + 1
        remaining_unit_actions = max(0, (23 - int(hour)) * max(1, len(unit_positions))
                                     - maintenance_work)
        restoration = int(day) >= ASSET_GUARD_START_DAY \
            and productive_assets < TERMINAL_ASSET_FLOOR
        plant_admission = 0 if int(hour) > PLANT_CUTOFF_HOUR else (
            GROWTH_LANE_CAP if restoration else MAX_PARALLEL_PLANT)
        plant_admission = min(len(plantable), max(0, plant_admission))
        planted = 0
        while plantable and planted < plant_admission:
            order = self._fair_crop_order(
                crop_have, goal["crops"], assigned, self.crop_cursor + planted)
            crop = next((name for name in order
                         if crop_have[name] + assigned[name] < int(goal["crops"][name])
                         and assigned[name] < budgets[name]), None)
            if crop is None:
                break
            x, y = _placement_order(plantable, crop)[0]
            travel = min((_dist(position, (x, y)) for position in unit_positions), default=20)
            bundle_work = travel + 2  # target travel + PLANT + same-day WATER
            if bundle_work > remaining_unit_actions:
                break
            plantable.remove((x, y))
            plant_priority = 1 if restoration else int(self.auction["plant_priority"])
            jobs.append((plant_priority, x, y, ("PLANT", crop)))
            assigned[crop] += 1
            planted += 1
            remaining_unit_actions -= bundle_work
        return _bundle_jobs(jobs)

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

    def _assign(self, units: list[Any], inventories: list[dict[str, Any]], jobs: list[Job],
                hour: int, lands: int, unavailable: set[int], day: int,
                step: int,
                chain_claim: tuple[int, Job, GrowthChain] | None = None,
                followup_claims: dict[int, Job] | None = None) -> dict[int, Job]:
        """Semantic locks, scoped maintenance, chain ownership, then safe tours."""
        result: dict[int, Job] = {}
        free = {index for index, unit in enumerate(units) if unit and index not in unavailable}
        remaining = {_job_key(job): job for job in jobs}

        for index in sorted(free):
            if index in self.tours and not self._tour_valid(index, day, step):
                self.tours.pop(index, None)
                self.sticky.pop(index, None)
                self.audit["tour_expired"] += 1
                self._daily_add(day, "tour_expired")

        def best_edge(keys: set[tuple[Any, ...]], restrict_zone: bool = False,
                      eligible: set[int] | None = None) \
                -> tuple[float, int, tuple[Any, ...]] | None:
            best: tuple[float, int, tuple[Any, ...]] | None = None
            for index in sorted(free if eligible is None else free & eligible):
                pos = (int(units[index][0]), int(units[index][1]))
                inventory = dict(inventories[index] or {})
                tour = self.tours.get(index)
                for key in sorted(keys):
                    job = remaining[key]
                    if restrict_zone and (not self._tour_valid(index, day, step)
                                          or tour is None or _job_zone(job) != tour.zone):
                        continue
                    cost = self._cost(index, pos, inventory, job, hour, lands)
                    edge = (cost, index, key)
                    if math.isfinite(cost) and (best is None or edge < best):
                        best = edge
            return best

        def claim(index: int, key: tuple[Any, ...], reason: str) -> Job:
            job = remaining.pop(key)
            old = self.sticky.get(index)
            pos = (int(units[index][0]), int(units[index][1]))
            if old is not None and old != key and _key_coord(old) != pos \
                    and _key_coord(old) != _job_coord(job):
                self.audit["target_switches_before_arrival"] += 1
                self._daily_add(day, "target_switches_before_arrival")
            if reason == "exact":
                self.audit["exact_target_continuations"] += 1
                self._daily_add(day, "exact_target_continuations")
            elif reason == "urgent_exact":
                self.audit["urgent_target_continuations"] += 1
                self._daily_add(day, "urgent_target_continuations")
            tour = self.tours.get(index)
            if reason in {"global", "growth"} and tour is not None \
                    and self._tour_valid(index, day, step) and _job_zone(job) != tour.zone:
                local_priorities = [int(value[0]) for value in remaining.values()
                                    if _job_zone(value) == tour.zone]
                if local_priorities and int(job[0]) < min(local_priorities):
                    self.audit["tour_priority_breaks"] += 1
                    self._daily_add(day, "tour_priority_breaks")
            result[index] = job
            free.remove(index)
            if job[3][0] not in PREEMPTIVE_OPS and reason != "chain":
                if tour is not None and self._tour_valid(index, day, step) \
                        and _job_zone(job) == tour.zone:
                    tour.last_step = int(step)
                    tour.last_job_key = key
                else:
                    self.tours[index] = ActorTour(
                        day=int(day), zone=_job_zone(job), started_step=int(step),
                        last_step=int(step), last_job_key=key)
                    self.audit["tour_started"] += 1
                    self._daily_add(day, "tour_started")
            return job

        chain_key = _job_key(chain_claim[1]) if chain_claim is not None else None
        urgent = {key for key, job in remaining.items()
                  if key != chain_key and (job[3][0] == "FEED"
                     or (job[3][0] == "WATER"
                         and (int(job[0]) == 0 or int(hour) >= 18)))}

        # A still-visible urgent semantic target is a hard lock.
        for index in sorted(list(free)):
            key = self.sticky.get(index)
            if key not in urgent:
                continue
            job = remaining[key]
            pos = (int(units[index][0]), int(units[index][1]))
            if math.isfinite(self._cost(index, pos, dict(inventories[index] or {}),
                                        job, hour, lands)):
                claim(index, key, "urgent_exact")
                urgent.remove(key)
        while free and urgent:
            best = best_edge(urgent)
            if best is None:
                break
            _cost_value, index, key = best
            job = claim(index, key, "global")
            urgent.remove(key)
            self.audit[f"preemptive_{str(job[3][0]).lower()}_assignments"] += 1
            self._daily_add(day, f"preemptive_{str(job[3][0]).lower()}_assignments")
        for key in list(urgent):
            remaining.pop(key, None)

        # Priority-2 WATER stays in its current tour zone.  Untoured actors may
        # establish ownership; live actors never cross a zone for ordinary WATER.
        ordinary_water = {key for key, job in remaining.items()
                          if key != chain_key and job[3][0] == "WATER"}
        for index in sorted(list(free)):
            key = self.sticky.get(index)
            if key in ordinary_water and (not self._tour_valid(index, day, step)
                                          or _job_zone(remaining[key]) == self.tours[index].zone):
                claim(index, key, "exact")
                ordinary_water.remove(key)
        while free and ordinary_water:
            local = best_edge(ordinary_water, restrict_zone=True)
            untoured = {index for index in free if not self._tour_valid(index, day, step)}
            fresh = best_edge(ordinary_water, eligible=untoured)
            best = min((edge for edge in (local, fresh) if edge is not None), default=None)
            if best is None:
                break
            _cost_value, index, key = best
            claim(index, key, "local" if local == best else "global")
            ordinary_water.remove(key)
        for key in list(ordinary_water):
            remaining.pop(key, None)

        # At most one already-open confirmed chain advances, and only its owner
        # may receive the same-coordinate follow-up.
        if chain_claim is not None and chain_key in remaining:
            owner, _chain_job, _chain = chain_claim
            if owner in free:
                pos = (int(units[owner][0]), int(units[owner][1]))
                if math.isfinite(self._cost(owner, pos, dict(inventories[owner] or {}),
                                            remaining[chain_key], hour, lands)):
                    claim(owner, chain_key, "chain")
                    self.audit["chain_owner_continuations"] += 1
                    self._daily_add(day, "chain_owner_continuations")
            if chain_key in remaining:
                remaining.pop(chain_key)

        # A completed WATER/FEED grants its actor one exact next-observation
        # continuation on that tile.  If that owner is unavailable, the tile is
        # deliberately withheld for this observation rather than converged on.
        for owner, followup_job in sorted((followup_claims or {}).items()):
            key = _job_key(followup_job)
            if key not in remaining:
                continue
            if owner in free:
                pos = (int(units[owner][0]), int(units[owner][1]))
                if math.isfinite(self._cost(owner, pos, dict(inventories[owner] or {}),
                                            remaining[key], hour, lands)):
                    claim(owner, key, "bundle")
                    self.audit["bundle_owner_followups"] += 1
                    self._daily_add(day, "bundle_owner_followups")
            remaining.pop(key, None)

        # Restoration is a single actor lane.  Ordinary priority-2 planting
        # remains parallel and is handled by the normal auction below.
        restoration = {key for key, job in remaining.items()
                       if job[3][0] == "PLANT" and int(job[0]) == 1}
        if free and restoration:
            best = best_edge(restoration)
            if best is not None:
                _cost_value, index, key = best
                claim(index, key, "growth")
        for key in list(restoration):
            remaining.pop(key, None)

        # Exact target locks are semantic, but never preserve a lower-priority
        # local task over the current global best priority.
        while free and remaining:
            global_priority = min(int(job[0]) for job in remaining.values())
            candidates = [(index, self.sticky.get(index)) for index in sorted(free)]
            exact = next(((index, key) for index, key in candidates
                          if key in remaining and int(remaining[key][0]) <= global_priority), None)
            if exact is None:
                break
            claim(exact[0], exact[1], "exact")

        # A local tour may continue only inside the globally best priority band.
        while free and remaining:
            global_priority = min(int(job[0]) for job in remaining.values())
            priority_band = {key for key, job in remaining.items()
                             if int(job[0]) <= global_priority}
            best = best_edge(priority_band, restrict_zone=True)
            if best is None:
                break
            _cost_value, index, key = best
            claim(index, key, "local")
            self.audit["tour_local_continuations"] += 1
            self._daily_add(day, "tour_local_continuations")

        # Unassigned actors start a new local tour at the globally best edge.
        while free and remaining:
            best = best_edge(set(remaining))
            if best is None:
                break
            _cost_value, index, key = best
            claim(index, key, "global")
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

    @staticmethod
    def _safe_unit_verb(verb: list[Any], position: tuple[int, int],
                        grid: list[list[Any]], inventory: dict[str, Any],
                        seeds: dict[str, int]) -> bool:
        """Fail closed for typed actions; movement and PASS remain unchanged."""
        if not verb:
            return False
        x, y = position
        tile = grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else "LOCKED"
        op = str(verb[0])
        if op == "WATER":
            return isinstance(tile, dict) and tile.get("kind") == "PLANT" \
                and not bool(tile.get("watered_today"))
        if op == "FEED":
            return bool(_animal(tile)) and not bool(tile.get("fed_today")) \
                and int(inventory.get("WHEAT", 0) or 0) > 0
        if op == "CARE":
            return bool(_animal(tile)) and not bool(tile.get("cared_today"))
        if op == "PLACE":
            animal = str(verb[1]) if len(verb) > 1 else ""
            want = "COOP" if animal == "GOOSE" else "PASTURE"
            return isinstance(tile, dict) and tile.get("kind") == want \
                and not _animal(tile) and int(inventory.get(animal, 0) or 0) > 0
        if op == "PLANT":
            crop = str(verb[1]) if len(verb) > 1 else ""
            return tile is None and int(seeds.get(crop, 0) or 0) > 0
        if op == "HARVEST":
            return isinstance(tile, dict) and (
                (tile.get("kind") == "PLANT" and int(tile.get("yield_units", 0) or 0) > 0)
                or (bool(_animal(tile)) and int(tile.get("yield_units", 0) or 0) > 0))
        if op in {"BUILD_PASTURE", "BUILD_COOP"}:
            return tile is None
        return True

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

    def _market(self, obs: dict[str, Any], farm: dict[str, Any], grid: list[list[Any]],
                goal: dict[str, Any], seeds: dict[str, int], projected: dict[str, int],
                inventories: list[dict[str, Any]], pending_plants: Counter[str],
                true_harvests: Counter[str],
                chain_seed_needs: Counter[str] | None = None) -> list[list[Any]]:
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
        chain_seed_needs = chain_seed_needs or Counter()
        gaps = {}
        for crop in CROPS:
            target_gap = max(0, int(goal["crops"].get(crop, 0))
                             - max(0, crop_have[crop] - true_harvests[crop])
                             - int(seeds.get(crop, 0) or 0) - pending_plants[crop])
            buffer_gap = max(0, min(CHAIN_SEED_BUFFER_CAP, int(chain_seed_needs[crop]))
                             - int(seeds.get(crop, 0) or 0) - pending_plants[crop])
            gaps[crop] = max(target_gap, buffer_gap)
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
            purchases = []

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
        self._reconcile_growth_chains(step, grid)
        jobs = self._jobs(day, hour, units, grid, goal, seeds, goal)
        chain_claim = self._ready_chain_job(grid, seeds)
        if chain_claim is not None:
            jobs = _bundle_jobs([*jobs, chain_claim[1]])
        followup_claims = self._ready_bundle_followups(step, jobs)
        for job in jobs:
            op = str(job[3][0]).lower()
            self.audit[f"job_generated_{op}"] += 1
            self._daily_add(day, f"job_generated_{op}")
        planned_plants = sum(job[3][0] == "PLANT" for job in jobs)
        self.audit["plant_jobs_planned"] += planned_plants
        self._daily_add(day, "plant_jobs_planned", planned_plants)
        synthetic: dict[int, list[Any]] = {}

        unfed = sum(job[3][0] == "FEED" for job in jobs)
        if unfed and not any(int(dict(value or {}).get("WHEAT", 0) or 0) > 0 for value in inventories) \
                and int(shed.get("WHEAT", 0) or 0) > 0:
            index = min(range(len(units)), key=lambda i: _dist(tuple(units[i]), _shed_gate(tuple(units[i]))))
            pos = tuple(units[index])
            synthetic[index] = (["PICKUP", "WHEAT", min(unfed, int(shed["WHEAT"]))]
                                if pos in SHED_TILES else _toward(pos, _shed_gate(pos)))
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
                                   set(synthetic), day, step, chain_claim,
                                   followup_claims)
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
                verb = list(task) if pos == (x, y) else _toward(pos, (x, y))
            else:
                self.sticky.pop(index, None)
                verb = PASS.copy()
            inventory = dict(inventories[index] or {}) if index < len(inventories) else {}
            if not self._safe_unit_verb(verb, pos, grid, inventory, seeds):
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
                if verb[0] in {"WATER", "FEED"}:
                    self.bundle_followups[index] = (int(step), int(pos[0]), int(pos[1]))
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
        if chain_claim is not None:
            owner, chain_job, chain = chain_claim
            if owner < len(verbs) and owner in assignments \
                    and _job_key(chain_job) == _job_key(assignments[owner]):
                if verbs[owner][0] == "PLANT" and chain.state == "plant_ready":
                    chain.state = "await_plant"
                    chain.action_step = int(step)
                    self.audit["growth_chain_plant_emitted"] += 1
                elif verbs[owner][0] == "WATER" and chain.state == "water_ready":
                    chain.state = "await_water"
                    chain.action_step = int(step)
                    self.audit["growth_chain_water_emitted"] += 1
        for index, (unit, verb) in enumerate(zip(units, verbs)):
            if not unit or not verb or verb[0] != "HARVEST":
                continue
            x, y = int(unit[0]), int(unit[1])
            tile = self._tile_at(grid, x, y)
            crop = str(tile.get("crop")) if isinstance(tile, dict) else ""
            if crop not in NON_ONGOING:
                continue
            if any(chain.x == x and chain.y == y for chain in self.growth_chains):
                continue
            self.growth_chains.append(GrowthChain(
                owner=index, x=x, y=y, crop=crop, state="await_empty",
                opened_step=int(step), action_step=int(step)))
            self.audit["growth_chain_harvest_emitted"] += 1
        self._record_harvest_batch(step, grid, units, verbs, shed, inventories)
        true_harvests = self._true_eligible_harvests(grid, units, verbs)
        market = self._market(obs, farm, grid, goal, seeds, projected, inventories,
                              pending_plants, true_harvests,
                              self._chain_seed_needs())
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
            "active_growth_chains": [asdict(chain) for chain in self.growth_chains],
            "pending_bundle_followups": {
                str(index): {"action_step": int(value[0]), "x": int(value[1]),
                             "y": int(value[2])}
                for index, value in sorted(self.bundle_followups.items())},
            "actual_plant_events": list(self.actual_plant_events),
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
            "growth_chains": [asdict(chain) for chain in self.growth_chains],
            "actual_plant_events": list(self.actual_plant_events),
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
    "ActorTour", "GrowthChain", "ShopRouterExecutor", "TOUR_MAX_STEPS", "PLACEMENT_RING", "agent",
    "build_executor", "canonical_hash", "canonical_json", "compile_genomes",
    "freeze_candidate", "make_agent", "route_expert", "validate_params",
]
