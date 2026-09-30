#!/usr/bin/env python3
"""V116 R14: adaptive-labor, self-contained hierarchical rule MoE.

Five experts compile compact aggregate parameters into thirty daily goals.
It stores no recorded action table or coordinate route; every action is
regenerated from the current observation.  R13 keeps the high-throughput RC8
state auction, then adds typed action guards, short-lived purchase receipts,
parallel plant-water admission and batched delivery.  R14 replaces the fixed
14-hand plateau with a current-workload labor budget capped at ten hands.
It imports no strategy.
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
SCHEMA = "v116-r14-adaptive-labor-hmoe-v1"
STRATEGY_PARENT = None
MODES = ("router", "fixed_wool", "fixed_dairy_berry", "fixed_tomato_market",
         "fixed_root", "fixed_grain_egg")
PLANT_CUTOFF_HOUR = 18
MAX_PARALLEL_PLANT = 3
DELIVERY_BATCH = 12
FINANCE_DROP_FLOOR = 750
TERMINAL_ASSET_FLOOR = 58
LABOR_HAND_CAP = 10
LABOR_HIRE_CUTOFF_HOUR = 8
LABOR_PRODUCTIVE_FRACTION = 0.72


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
DEFAULT_PARAMS: dict[str, Any] = json.loads('{"auction":{"harvest_priority":2,"place_priority":3,"plant_priority":2,"replacement":"same_turn_seed_reserve_only","role_penalty":0,"sticky_bonus":3},"experts":{"dairy_berry":{"animal_suffix":0,"donor_template":0,"focus2":2,"focus3":4},"grain_egg":{"animal_suffix":0,"donor_template":0,"focus2":2,"focus3":4},"root":{"animal_suffix":0,"donor_template":0,"focus2":2,"focus3":4},"tomato_market":{"animal_suffix":0,"donor_template":0,"focus2":2,"focus3":6},"wool":{"animal_suffix":0,"donor_template":0,"focus2":2,"focus3":4}},"market":{"finance_stress":16,"liquidation":712,"ordinary_stress":16,"pressure":88,"regular_cap":36,"sale_floor":0.45}}')
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
    if first == "YARN_STORE":
        return "wool"
    if first in {"SMOOTHIE_SHOP", "ICE_CREAM_SHOP"}:
        return "dairy_berry"
    if first in {"PIZZA_SHOP", "FARMERS_MARKET"}:
        return "tomato_market"
    if first == "PET_CAFE":
        return "root"
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
    return {"day": day, "lands": lands, "hands_cap": LABOR_HAND_CAP, "crops": dict(crops),
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


def _job_key(job: Job) -> tuple[Any, ...]:
    priority, x, y, verb = job
    return (priority, verb[0], x, y, *verb[1:])


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
        self.roles: dict[tuple[int, int], int] = {}
        self.crop_cursor = 0
        self.pending_receipts: list[PendingReceipt] = []
        self.pending_harvests: list[PendingHarvestBatch] = []
        self.replacement_credits: Counter[str] = Counter()
        self.labor_day = -1
        self.labor_current: dict[str, Any] = {}
        self.labor_history: list[dict[str, Any]] = []
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

    def _fair_crop_order(self, have: Counter[str], target: dict[str, int],
                         assigned: Counter[str] | None = None) -> list[str]:
        assigned = assigned or Counter()
        cycle = list(CROPS)
        offset = self.crop_cursor % len(cycle)
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
                        productive_assets = sum(crop_have.values()) + sum(animal_have.values())
                        terminal_protected = (crop in NON_ONGOING and day >= 29 and hour > 18
                                              and productive_assets <= TERMINAL_ASSET_FLOOR)
                        if terminal_protected:
                            self.audit["terminal_asset_harvest_protected"] += 1
                        else:
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

        empty = _position_order([(x, y) for x, y in _unlocked(grid) if grid[y][x] is None])
        pasture_goal = (int(structure_goal["animals"].get("SHEEP", 0))
                        + int(structure_goal["animals"].get("COW", 0)))
        coop_goal = int(structure_goal["animals"].get("GOOSE", 0))
        cursor = 0
        for structure, count in (("PASTURE", max(0, pasture_goal - structures["PASTURE"])),
                                 ("COOP", max(0, coop_goal - structures["COOP"]))):
            for _ in range(min(count, max(0, len(empty) - cursor))):
                x, y = empty[cursor]
                cursor += 1
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
        plantable = empty[cursor:]
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
        plant_admission = 0 if int(hour) > PLANT_CUTOFF_HOUR else MAX_PARALLEL_PLANT
        plant_admission = min(len(plantable), max(0, plant_admission))
        planted = 0
        while plantable and planted < plant_admission:
            order = self._fair_crop_order(crop_have, goal["crops"], assigned)
            crop = next((name for name in order
                         if crop_have[name] + assigned[name] < int(goal["crops"][name])
                         and assigned[name] < budgets[name]), None)
            if crop is None:
                break
            x, y = plantable[0]
            travel = min((_dist(position, (x, y)) for position in unit_positions), default=20)
            bundle_work = travel + 2  # target travel + PLANT + same-day WATER
            if bundle_work > remaining_unit_actions:
                break
            plantable.pop(0)
            jobs.append((int(self.auction["plant_priority"]), x, y, ("PLANT", crop)))
            assigned[crop] += 1
            planted += 1
            remaining_unit_actions -= bundle_work
            self.crop_cursor = (self.crop_cursor + 1) % len(CROPS)
        self.audit["plant_admitted"] += planted
        self.audit["plant_withheld_budget"] += max(0, len(plantable))
        self.audit["max_parallel_plant_admission"] = max(
            self.audit["max_parallel_plant_admission"], planted)
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

    def _assign(self, units: list[Any], inventories: list[dict[str, Any]], jobs: list[Job],
                hour: int, lands: int, unavailable: set[int]) -> dict[int, Job]:
        result: dict[int, Job] = {}
        free = {index for index, unit in enumerate(units) if unit and index not in unavailable}
        remaining = {_job_key(job): job for job in jobs}
        while free and remaining:
            best: tuple[float, int, tuple[Any, ...]] | None = None
            for index in free:
                pos = (int(units[index][0]), int(units[index][1]))
                inventory = dict(inventories[index] or {})
                for key, job in remaining.items():
                    cost = self._cost(index, pos, inventory, job, hour, lands)
                    edge = (cost, index, key)
                    if math.isfinite(cost) and (best is None or edge < best):
                        best = edge
            if best is None:
                break
            _cost, index, key = best
            result[index] = remaining.pop(key)
            free.remove(index)
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

    def _adaptive_labor_target(self, day: int, hour: int, farm: dict[str, Any],
                               grid: list[list[Any]], goal: dict[str, Any],
                               jobs: list[Job], units: list[Any]) -> int:
        """Convert current critical work and route distance into a <=10 hand cap."""
        if day != self.labor_day:
            if self.labor_current:
                self.labor_history.append(dict(self.labor_current))
            self.labor_day = day
            self.labor_current = {
                "day": day,
                "target_hands": 0,
                "peak_actual_hands": 0,
                "critical_jobs": 0,
                "movement_budget": 0,
                "backlog_work": 0,
                "required_unit_actions": 0,
                "wage_budget": 0,
                "hire_orders_emitted": 0,
                "hire_wage_emitted": 0,
            }

        current_hands = len(farm.get("hands", []) or [])
        self.labor_current["peak_actual_hands"] = max(
            int(self.labor_current["peak_actual_hands"]), current_hands)
        origins = [(int(unit[0]), int(unit[1])) for unit in units if unit]
        origins.extend(SHED_TILES)
        critical_ops = {"WATER", "FEED", "CARE", "HARVEST", "PLANT", "PLACE",
                        "BUILD_PASTURE", "BUILD_COOP"}
        critical = [job for job in jobs if job[3][0] in critical_ops]
        movement_budget = sum(min(4, min((_dist(origin, (job[1], job[2]))
                                          for origin in origins), default=4))
                              for job in critical)

        crops, animals, structures = _counts(grid)
        crop_gap = sum(max(0, int(goal["crops"].get(crop, 0)) - crops[crop])
                       for crop in CROPS)
        animal_gap = sum(max(0, int(goal["animals"].get(kind, 0)) - animals[kind])
                         for kind in ANIMALS)
        plant_jobs = sum(job[3][0] == "PLANT" for job in jobs)
        place_jobs = sum(job[3][0] == "PLACE" for job in jobs)
        structure_gap = max(0, int(goal["animals"].get("SHEEP", 0))
                            + int(goal["animals"].get("COW", 0)) - structures["PASTURE"]) \
            + max(0, int(goal["animals"].get("GOOSE", 0)) - structures["COOP"])
        backlog_work = max(0, crop_gap - plant_jobs) * 3 \
            + max(0, animal_gap - place_jobs) * 4 + structure_gap * 2
        required_actions = len(critical) + movement_budget + backlog_work
        remaining_hours = max(6, 24 - int(hour))
        productive_actions_per_unit = max(
            4, int(math.floor(remaining_hours * LABOR_PRODUCTIVE_FRACTION)))
        required_units = max(1, math.ceil(required_actions / productive_actions_per_unit))
        computed_hands = min(LABOR_HAND_CAP, max(2, required_units - 1))
        target_hands = max(current_hands, computed_hands)
        target_hands = min(LABOR_HAND_CAP, target_hands)

        hires_today = int(farm.get("hires_today", current_hands) or 0)
        missing = max(0, target_hands - current_hands) if hour <= LABOR_HIRE_CUTOFF_HOUR else 0
        wage_budget = sum(_fib(hires_today + offset) for offset in range(missing))
        self.labor_current.update({
            "target_hands": max(int(self.labor_current["target_hands"]), target_hands),
            "critical_jobs": max(int(self.labor_current["critical_jobs"]), len(critical)),
            "movement_budget": max(int(self.labor_current["movement_budget"]), movement_budget),
            "backlog_work": max(int(self.labor_current["backlog_work"]), backlog_work),
            "required_unit_actions": max(int(self.labor_current["required_unit_actions"]),
                                         required_actions),
            "wage_budget": max(int(self.labor_current["wage_budget"]), wage_budget),
        })
        self.audit["max_adaptive_hands_target"] = max(
            self.audit["max_adaptive_hands_target"], target_hands)
        return target_hands

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

    def _market(self, obs: dict[str, Any], farm: dict[str, Any], grid: list[list[Any]],
                goal: dict[str, Any], seeds: dict[str, int], projected: dict[str, int],
                inventories: list[dict[str, Any]], pending_plants: Counter[str],
                true_harvests: Counter[str], labor_target: int) -> list[list[Any]]:
        step = int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)
        money = int(farm.get("money", 0) or 0)
        crop_have, animal_have, _structures = _counts(grid)
        carried = _inventory_totals(inventories)
        total = sum(projected.values())
        terminal = step >= int(self.market_params["liquidation"])
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
        if int(obs.get("hour", 0) or 0) <= LABOR_HIRE_CUTOFF_HOUR:
            for offset in range(max(0, min(LABOR_HAND_CAP, int(labor_target)) - current_hands)):
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

        rough = reserve
        for _priority, order, unit_cost in purchases[:9]:
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
            if op == "BUY_PRODUCT":
                quantity = min(requested, (money - reserve) // max(1, unit_cost), SHED_CAPACITY - total)
            elif op == "BUY_ANIMAL":
                quantity = min(requested, (money - reserve) // max(1, unit_cost), SHED_CAPACITY - total)
            elif op == "BUY_SEED":
                quantity = min(requested, (money - reserve) // max(1, unit_cost))
            else:
                quantity = int(money - unit_cost >= reserve)
            if quantity <= 0:
                self.audit["market_withheld"] += 1
                continue
            order = list(raw) if len(raw) < 3 else [raw[0], raw[1], int(quantity)]
            orders.append(order)
            money -= int(unit_cost) * int(quantity)
            if op == "HIRE" and self.labor_current:
                self.labor_current["hire_orders_emitted"] += int(quantity)
                self.labor_current["hire_wage_emitted"] += int(unit_cost) * int(quantity)
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
        self._reconcile_harvests(step, shed, inventories)
        jobs = self._jobs(day, hour, units, grid, goal, seeds, goal)
        labor_target = self._adaptive_labor_target(day, hour, farm, grid, goal, jobs, units)
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

        assignments = self._assign(units, inventories, jobs, hour, int(goal["lands"]), set(synthetic))
        verbs: list[list[Any]] = []
        for index, unit in enumerate(units):
            pos = (int(unit[0]), int(unit[1]))
            if index in synthetic:
                verb = synthetic[index]
            elif index in assignments:
                priority, x, y, task = assignments[index]
                self.sticky[index] = _job_key(assignments[index])
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
            verbs.append(verb)
            self.audit[f"action_{verb[0].lower()}"] += 1
        projected = self._projected_shed(shed, inventories, verbs)
        pending_plants: Counter[str] = Counter(
            verb[1] for verb in verbs if verb and verb[0] == "PLANT" and len(verb) > 1
        )
        self._record_harvest_batch(step, grid, units, verbs, shed, inventories)
        true_harvests: Counter[str] = Counter()
        market = self._market(obs, farm, grid, goal, seeds, projected, inventories,
                              pending_plants, true_harvests, labor_target)
        self._record_receipts(step, market)
        self.last_step = step
        self.audit["calls"] += 1
        self.audit["jobs_generated"] += len(jobs)
        return {"farmer": verbs[0] if verbs else PASS.copy(), "hands": verbs[1:], "market": market}

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
            "replacement_credits": dict(sorted(self.replacement_credits.items())),
            "labor_cap": LABOR_HAND_CAP,
            "labor_current_day": dict(self.labor_current),
            "labor_history": [dict(row) for row in self.labor_history],
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
    "SCHEMA", "STRATEGY_PARENT", "MODES", "PendingReceipt", "ShopRouterExecutor", "agent",
    "build_executor", "canonical_hash", "canonical_json", "compile_genomes",
    "freeze_candidate", "make_agent", "route_expert", "validate_params",
]
