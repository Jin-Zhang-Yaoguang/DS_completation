#!/usr/bin/env python3
"""V116 RC4: RC3 plus one-day staging and balanced demand projection.

The candidate is self-contained.  It stores four compact daily aggregate
genomes, never an episode action stream or per-turn coordinate plan.  The
first visible town-shop snapshot selects one expert for the remainder of the
episode.  Every unit and market action is regenerated from the current state.
"""

from __future__ import annotations

import math
import copy
from collections import Counter
from typing import Any


ENABLE_STAGING = False
ENABLE_PROJECTION = True


PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 8, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 10, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "first": 10, "max_day": 12, "max_yield": 6, "ongoing": False},
}
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

# Every expert shares the complete day-0 opening, so the day-3 decision does
# not invalidate installed assets.  Blocks are counts, never coordinates.
GENOMES: dict[str, dict[str, Any]] = {
    "balanced_root": {
        "land_days": [0, 5, 9],
        "crop_blocks": [
            {"WHEAT": 8, "MELON": 7},
            {"WHEAT": 8, "MELON": 5, "STRAWBERRY": 6},
            {"WHEAT": 10, "MELON": 7, "STRAWBERRY": 5, "CARROT": 3},
        ],
        "animal_waves": [(0, "SHEEP", 4), (5, "COW", 4), (9, "SHEEP", 2)],
    },
    "wool": {
        "land_days": [0, 5, 9],
        "crop_blocks": [
            {"WHEAT": 8, "MELON": 7},
            {"WHEAT": 10, "MELON": 5, "STRAWBERRY": 4},
            {"WHEAT": 12, "MELON": 7, "STRAWBERRY": 4, "CARROT": 2},
        ],
        "animal_waves": [(0, "SHEEP", 4), (5, "SHEEP", 2), (9, "COW", 4)],
    },
    "dairy_berry": {
        "land_days": [0, 5, 9],
        "crop_blocks": [
            {"WHEAT": 8, "MELON": 7},
            {"WHEAT": 7, "MELON": 4, "STRAWBERRY": 8},
            {"WHEAT": 8, "MELON": 6, "STRAWBERRY": 8, "TOMATO": 3},
        ],
        "animal_waves": [(0, "SHEEP", 4), (5, "COW", 4), (9, "COW", 2)],
    },
    "tomato_crop": {
        "land_days": [0, 5, 9],
        "crop_blocks": [
            {"WHEAT": 8, "MELON": 7},
            {"WHEAT": 7, "MELON": 4, "STRAWBERRY": 5, "TOMATO": 3},
            {"WHEAT": 7, "MELON": 7, "STRAWBERRY": 5, "TOMATO": 6},
        ],
        "animal_waves": [(0, "SHEEP", 4), (5, "COW", 2)],
    },
}

# Only balanced_root's stage-2/stage-3 crop blocks may change.  The L1
# transfers are exactly three and five tiles respectively; day-0 stays frozen.
BALANCED_PROJECTIONS: dict[str, tuple[dict[str, int], dict[str, int]]] = {
    "PET_CAFE": (
        {"WHEAT": 7, "MELON": 4, "STRAWBERRY": 5, "CARROT": 3},
        {"WHEAT": 9, "MELON": 4, "STRAWBERRY": 4, "CARROT": 8},
    ),
    "BAKERY": (
        {"WHEAT": 11, "MELON": 3, "STRAWBERRY": 5},
        {"WHEAT": 15, "MELON": 4, "STRAWBERRY": 3, "CARROT": 3},
    ),
    "BRUNCH_SPOT": (
        {"WHEAT": 9, "MELON": 2, "STRAWBERRY": 8},
        {"WHEAT": 12, "MELON": 3, "STRAWBERRY": 8, "CARROT": 2},
    ),
}


def project_balanced(first_shop: str | None) -> dict[str, Any]:
    genome = copy.deepcopy(GENOMES["balanced_root"])
    blocks = BALANCED_PROJECTIONS.get(str(first_shop))
    if blocks is not None:
        genome["crop_blocks"][1] = dict(blocks[0])
        genome["crop_blocks"][2] = dict(blocks[1])
    return genome


def validate_genomes() -> list[str]:
    errors: list[str] = []
    for name, genome in GENOMES.items():
        days = genome["land_days"]
        blocks = genome["crop_blocks"]
        if len(days) != len(blocks) or len(days) > 4 or days[0] != 0 or days != sorted(days):
            errors.append(f"{name}: invalid land stages")
        if any(sum(int(v) for v in block.values()) > 25 for block in blocks):
            errors.append(f"{name}: crop block exceeds 25")
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
    # The first visible shop snapshot is frozen for the whole episode.
    # Precedence is explicit so the Router stays a shallow auditable rule.
    if "YARN_STORE" in shops:
        return "wool"
    if any(shop in {"SMOOTHIE_SHOP", "ICE_CREAM_SHOP"} for shop in shops):
        return "dairy_berry"
    if any(shop in {"PIZZA_SHOP", "FARMERS_MARKET"} for shop in shops):
        return "tomato_crop"
    return "balanced_root"


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
    hands = min(14, 4 + 10 * min(day, 7) // 7, max(4, math.ceil(active / 4)))
    return {"day": day, "lands": lands, "hands": hands, "crops": dict(crops),
            "animals": dict(animals), "feed_reserve": 2 * sum(animals.values()),
            "cash_reserve": 100}


def compile_daily_goals(genome: dict[str, Any]) -> list[dict[str, Any]]:
    return [daily_goal(genome, day) for day in range(30)]


Job = tuple[int, int, int, tuple[Any, ...]]


def _job_key(job: Job) -> tuple[Any, ...]:
    priority, x, y, verb = job
    return (priority, verb[0], x, y, *verb[1:])


class ShopRouterExecutor:
    def __init__(self, fixed_expert: str | None = None) -> None:
        errors = validate_genomes()
        if errors:
            raise ValueError("; ".join(errors))
        if fixed_expert is not None and fixed_expert not in GENOMES:
            raise ValueError(f"unknown fixed expert: {fixed_expert}")
        self.fixed_expert = fixed_expert
        self.expert = fixed_expert or "balanced_root"
        self.committed = fixed_expert is not None
        self.commit_step: int | None = 0 if fixed_expert is not None else None
        self.first_shops: tuple[str, ...] = ()
        self.balanced_genome = project_balanced(None)
        self.day = -1
        self.sticky: dict[int, tuple[Any, ...]] = {}
        self.roles: dict[tuple[int, int], int] = {}
        self.crop_cursor = 0
        self.audit: Counter[str] = Counter()

    @staticmethod
    def _seat(obs: dict[str, Any]) -> int:
        for key in ("player_index", "index", "player"):
            if obs.get(key) is not None:
                return int(obs[key])
        return 0

    def _route(self, obs: dict[str, Any]) -> None:
        if self.committed:
            return
        shops = [str(value) for value in list((obs.get("town") or {}).get("unlocked_shops", []) or [])]
        if not shops:
            return
        self.expert = route_expert(shops)
        self.committed = True
        self.commit_step = int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)
        self.first_shops = tuple(shops)
        if ENABLE_PROJECTION and self.expert == "balanced_root":
            self.balanced_genome = project_balanced(shops[0])
        self.audit[f"router_{self.expert}"] += 1

    def goal(self, day: int) -> dict[str, Any]:
        genome = self.balanced_genome if self.expert == "balanced_root" else GENOMES[self.expert]
        return daily_goal(genome, min(29, int(day)))

    def _fair_crop_order(self, have: Counter[str], target: dict[str, int],
                         assigned: Counter[str] | None = None) -> list[str]:
        assigned = assigned or Counter()
        cycle = list(CROPS)
        offset = self.crop_cursor % len(cycle)
        tie_order = cycle[offset:] + cycle[:offset]
        return sorted((crop for crop, count in target.items() if int(count) > 0),
                      key=lambda crop: ((have[crop] + assigned[crop]) / int(target[crop]),
                                        tie_order.index(crop)))

    def _jobs(self, day: int, grid: list[list[Any]], goal: dict[str, Any],
              seeds: dict[str, int], structure_goal: dict[str, Any]) -> list[Job]:
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
                    units = int(tile.get("yield_units", 0) or 0)
                    ripe = bool(facts.get("ongoing")) or units >= int(facts.get("max_yield", 99)) \
                        or age >= int(facts.get("max_day", 99))
                    if units > 0 and age >= int(facts.get("first", 0)) and ripe:
                        jobs.append((2, x, y, ("HARVEST",)))
                elif _animal(tile):
                    if not tile.get("fed_today"):
                        jobs.append((1, x, y, ("FEED",)))
                    if int(tile.get("yield_units", 0) or 0) > 0:
                        jobs.append((2, x, y, ("HARVEST",)))
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
                        jobs.append((3, x, y, ("PLACE", kind)))
                        deficit[kind] -= 1
                        break

        # Fair replacement: repeatedly serve the lowest realised target ratio.
        plantable = empty[cursor:]
        assigned: Counter[str] = Counter()
        budgets = {crop: int(seeds.get(crop, 0) or 0) for crop in CROPS}
        while plantable:
            order = self._fair_crop_order(crop_have, goal["crops"], assigned)
            crop = next((name for name in order
                         if crop_have[name] + assigned[name] < int(goal["crops"][name])
                         and assigned[name] < budgets[name]), None)
            if crop is None:
                break
            x, y = plantable.pop(0)
            jobs.append((3, x, y, ("PLANT", crop)))
            assigned[crop] += 1
            self.crop_cursor = (self.crop_cursor + 1) % len(CROPS)
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
        sticky = -5.0 if self.sticky.get(unit_index) == _job_key(job) else 0.0
        stage = max(1, int(lands))
        role = self.roles.setdefault((stage, unit_index), unit_index % stage)
        role_cost = 3.0 if _quadrant((x, y)) != role else 0.0
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
                inventories: list[dict[str, Any]], pending_plants: Counter[str]) -> list[list[Any]]:
        step = int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)
        money = int(farm.get("money", 0) or 0)
        crop_have, animal_have, _structures = _counts(grid)
        carried = _inventory_totals(inventories)
        total = sum(projected.values())
        terminal = step >= 712
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
        for offset in range(max(0, int(goal["hands"]) - current_hands)):
            purchases.append((92, ["HIRE"], _fib(hires_today + offset)))
        for kind in ("SHEEP", "COW", "GOOSE"):
            target = int(goal["animals"].get(kind, 0))
            have = animal_have[kind] + int(projected.get(kind, 0)) + carried[kind]
            if target > have:
                purchases.append((88, ["BUY_ANIMAL", kind, target - have], ANIMALS[kind]["cost"]))
        # Fair seed batch: total <=12, every positive gap gets one before
        # extras, and no product monopolises more than 40% of the batch.
        gaps = {
            crop: max(0, int(goal["crops"].get(crop, 0)) - crop_have[crop]
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
        pressure = total >= 88
        sale_quantities: Counter[str] = Counter()
        # Finance stress assumes 32 opponent units sell first; ordinary
        # valuation below uses 12.  Both are exact engine curves.
        for good in sorted(PRODUCTS,
                           key=lambda item: (-market_price(item, int(market_inventory.get(item, 10000) or 10000) + 32),
                                             PRODUCTS.index(item))):
            while financing > 0 and sale_quantities[good] < saleable[good]:
                quote = market_price(good, int(market_inventory.get(good, 10000) or 10000)
                                     + 32 + sale_quantities[good])
                sale_quantities[good] += 1
                financing -= quote
        for good in PRODUCTS:
            left = saleable[good] - sale_quantities[good]
            if left <= 0 or (demand_now[good] > 0 and not pressure and not terminal):
                continue
            quote = market_price(good, int(market_inventory.get(good, 10000) or 10000)
                                 + 12 + sale_quantities[good])
            if terminal or pressure or quote >= max(1, int(BASE_PRICE[good] * .55)):
                sale_quantities[good] += left if terminal else min(left, 24)

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
            money += sum(market_price(good, level + 32 + offset) for offset in range(quantity))
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
            if op in {"BUY_PRODUCT", "BUY_ANIMAL"}:
                total += int(quantity)
        return orders[:10]

    def act(self, obs: dict[str, Any]) -> dict[str, Any]:
        self._route(obs)
        seat = self._seat(obs)
        day = min(29, int(obs.get("day", 0) or 0))
        hour = int(obs.get("hour", 0) or 0)
        if day != self.day:
            self.day = day
        goal = self.goal(day)
        # Exactly one-day lookahead, only on the two pre-stage days.  Unit
        # planting/placing/maintenance remains tied to ``goal``; only structure
        # capacity below and the market controller use ``staging_goal``.
        staging_goal = self.goal(day + 1) if ENABLE_STAGING and day in {4, 8} else goal
        farm = (obs.get("farms") or [{}, {}])[seat]
        grid = list(farm.get("tiles", []) or [])
        private = obs.get("private", {}) or {}
        seeds = dict(private.get("seeds", {}) or {})
        shed = dict(private.get("shed", {}) or {})
        inventories = list(private.get("inventories", []) or [])
        units = [farm.get("farmer")] + list(farm.get("hands", []) or [])
        while len(inventories) < len(units):
            inventories.append({})
        jobs = self._jobs(day, grid, goal, seeds, staging_goal)
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

        step = int(obs.get("step", day * 24 + hour) or 0)
        if step >= 712:
            for index, unit in enumerate(units):
                if index in synthetic or not any(int(value or 0) > 0 for value in dict(inventories[index] or {}).values()):
                    continue
                pos = tuple(unit)
                synthetic[index] = ["DROP"] if pos in SHED_TILES else _toward(pos, _shed_gate(pos))

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
            verbs.append(verb)
            self.audit[f"action_{verb[0].lower()}"] += 1
        projected = self._projected_shed(shed, inventories, verbs)
        pending_plants: Counter[str] = Counter(
            verb[1] for verb in verbs if verb and verb[0] == "PLANT" and len(verb) > 1
        )
        market = self._market(obs, farm, grid, staging_goal, seeds, projected, inventories,
                              pending_plants)
        self.audit["calls"] += 1
        self.audit["jobs_generated"] += len(jobs)
        return {"farmer": verbs[0] if verbs else PASS.copy(), "hands": verbs[1:], "market": market}


def make_agent() -> Any:
    return ShopRouterExecutor().act
