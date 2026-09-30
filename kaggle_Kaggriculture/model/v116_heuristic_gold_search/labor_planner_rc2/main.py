#!/usr/bin/env python3
"""V116 RC2: daily aggregate goals and an online state-task executor.

Originality boundary
--------------------
The policy stores only a compact declarative genome.  It contains no Replay
action, no per-turn position, no parent-agent call and no 719-element payload.
At every call it derives market orders, target gaps, tile jobs and unit actions
from the current observation.

The public engine constants and the high-level idea of a genome compiler are
derived from ``destbreso/kaggriculture-island-ga`` (MIT).  The aggregate-goal
compiler, market controller, dynamic layout and joint dispatcher below are new
and do not import its compiler or executor.
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
EXTERNAL = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos"
ISLAND = EXTERNAL / "kaggriculture-island-ga"
sys.path.insert(0, str(ISLAND))

# Public engine facts only.  No Island-GA action/compiler/executor is imported.
from islandga.engine_facts import (  # noqa: E402
    ANIMALS,
    CROPS,
    LAND_PRICES,
    PRODUCTS,
    SHED_CAPACITY,
    SHED_TILES,
    fib_hire_cost,
)


CROP_ORDER = ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO")
ANIMAL_ORDER = ("SHEEP", "COW", "GOOSE")
PASS = ["PASS"]

# A compact, declarative genome. Crop blocks are *counts added at a land
# stage*, not tile coordinates. Animal waves are daily aggregate counts.
DEFAULT_GENOME: dict[str, Any] = {
    "schema": "v116-daily-aggregate-genome-v1",
    "land_days": [0, 5, 9],
    "crop_blocks": [
        {"WHEAT": 8, "MELON": 7},
        {"WHEAT": 8, "MELON": 5, "STRAWBERRY": 6},
        {"WHEAT": 10, "MELON": 7, "STRAWBERRY": 5, "CARROT": 3},
    ],
    "animal_waves": [
        {"day": 0, "kind": "SHEEP", "count": 4},
        {"day": 5, "kind": "COW", "count": 4},
        {"day": 9, "kind": "SHEEP", "count": 2},
    ],
    "labour": {"plateau": 14, "ramp_days": 7, "tiles_per_hand": 4},
    "market": {"cash_reserve": 100, "feed_days": 2, "sell_buffer": 8},
}


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
    return min(SHED_TILES, key=lambda p: (_dist(pos, p), p))


def _tile_animal(tile: Any) -> str | None:
    if not isinstance(tile, dict) or not tile.get("animal"):
        return None
    value = tile["animal"]
    return value.get("kind") if isinstance(value, dict) else str(value)


def _unlocked(grid: list[list[Any]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            # The official interpreter serialises locked tiles as the literal
            # string ``"LOCKED"``; some wrappers expose ``{"kind":"LOCKED"}``.
            if tile != "LOCKED" and not (isinstance(tile, dict) and tile.get("kind") == "LOCKED"):
                out.append((x, y))
    return out


def _position_order(positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Deterministic runtime layout preference, never a stored position plan."""
    return sorted(positions, key=lambda p: (min(_dist(p, s) for s in SHED_TILES), p[1], p[0]))


def validate_genome(genome: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if genome.get("schema") != "v116-daily-aggregate-genome-v1":
        errors.append("invalid schema")
    days = list(genome.get("land_days") or [])
    blocks = list(genome.get("crop_blocks") or [])
    if not days or len(days) != len(blocks) or len(days) > 4:
        errors.append("land_days/crop_blocks mismatch")
    if days and (days[0] != 0 or days != sorted(days) or any(not 0 <= int(d) <= 29 for d in days)):
        errors.append("invalid land days")
    for block in blocks:
        if sum(int(n) for n in block.values()) > 25:
            errors.append("crop block exceeds quadrant capacity")
        if any(crop not in CROPS or int(n) < 0 for crop, n in block.items()):
            errors.append("invalid crop block")
    totals = Counter()
    for wave in genome.get("animal_waves") or []:
        kind = wave.get("kind")
        if kind not in ANIMALS or not 0 <= int(wave.get("day", -1)) <= 29:
            errors.append("invalid animal wave")
            continue
        totals[kind] += int(wave.get("count", 0))
    for kind, total in totals.items():
        if not 0 <= total <= ANIMALS[kind]["max_held"]:
            errors.append(f"{kind} exceeds species cap")
    for stage, block in enumerate(blocks):
        animal_due = sum(int(w["count"]) for w in genome.get("animal_waves") or []
                         if int(w["day"]) <= int(days[stage]))
        capacity = 25 * (stage + 1)
        crops = sum(sum(int(n) for n in blocks[i].values()) for i in range(stage + 1))
        if crops + animal_due > capacity:
            errors.append(f"stage {stage} exceeds land capacity")
    return errors


def daily_goal(genome: dict[str, Any], day: int) -> dict[str, Any]:
    """Compile one of at most 30 aggregate daily records from 20-ish numbers."""
    land_days = [int(x) for x in genome["land_days"]]
    lands = sum(day >= d for d in land_days)
    crops = Counter()
    for block in genome["crop_blocks"][:lands]:
        crops.update({k: int(v) for k, v in block.items()})
    animals = Counter()
    for wave in genome["animal_waves"]:
        if day >= int(wave["day"]):
            animals[wave["kind"]] += int(wave["count"])
    active = sum(crops.values()) + 2 * sum(animals.values())
    labour = genome["labour"]
    ramp_cap = 4 + (int(labour["plateau"]) - 4) * min(day, int(labour["ramp_days"])) // max(1, int(labour["ramp_days"]))
    hands = min(int(labour["plateau"]), ramp_cap,
                max(4, math.ceil(active / int(labour["tiles_per_hand"]))))
    return {
        "day": int(day),
        "lands": lands,
        "hands": hands,
        "crops": dict(crops),
        "animals": dict(animals),
        "feed_reserve": int(genome["market"]["feed_days"]) * sum(animals.values()),
        "cash_reserve": int(genome["market"]["cash_reserve"]),
    }


def compile_daily_goals(genome: dict[str, Any]) -> list[dict[str, Any]]:
    errors = validate_genome(genome)
    if errors:
        raise ValueError("; ".join(errors))
    return [daily_goal(genome, day) for day in range(30)]


def _job_key(job: tuple[int, int, int, tuple[Any, ...]]) -> tuple[Any, ...]:
    priority, x, y, verb = job
    return (priority, verb[0], x, y, *verb[1:])


class DailyGoalExecutor:
    """State-safe executor: target gap -> task DAG -> joint unit actions."""

    def __init__(self, genome: dict[str, Any] | None = None):
        self.genome = genome or DEFAULT_GENOME
        self.goals = compile_daily_goals(self.genome)
        self.day = -1
        self.hires_sent = 0
        self.sticky: dict[int, tuple[Any, ...]] = {}
        self.audit: Counter[str] = Counter()

    @staticmethod
    def _seat(obs: dict[str, Any]) -> int:
        for key in ("player_index", "index", "player"):
            if obs.get(key) is not None:
                return int(obs[key])
        return 0

    @staticmethod
    def _inventory_totals(invs: list[dict[str, Any]]) -> Counter[str]:
        total: Counter[str] = Counter()
        for inv in invs:
            total.update({k: int(v or 0) for k, v in dict(inv or {}).items()})
        return total

    @staticmethod
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
                animal = _tile_animal(tile)
                if animal:
                    animals[animal] += 1
                if tile.get("kind") in {"PASTURE", "COOP"}:
                    structures[tile["kind"]] += 1
        return crops, animals, structures

    def _market_orders(self, obs: dict[str, Any], farm: dict[str, Any], grid: list[list[Any]],
                       goal: dict[str, Any], seeds: dict[str, int], shed: dict[str, int],
                       invs: list[dict[str, Any]]) -> list[list[Any]]:
        """Closed-loop sale/finance/input orders; no scheduled action table."""
        day = int(obs.get("day", 0) or 0)
        hour = int(obs.get("hour", 0) or 0)
        money = int(farm.get("money", 0) or 0)
        reserve = int(goal["cash_reserve"])
        carried = self._inventory_totals(invs)
        crop_have, animal_have, _structures = self._counts(grid)
        shed_total = sum(int(v or 0) for v in shed.values())
        orders: list[list[Any]] = []

        # Sell visible stock whenever there is something meaningful to clear.
        # Wheat required for two feeding days is protected except at terminal.
        terminal = day >= 29
        for good in PRODUCTS:
            held = int(shed.get(good, 0) or 0)
            keep = 0 if terminal else int(goal["feed_reserve"]) if good == "WHEAT" else 0
            quantity = max(0, held - keep)
            if quantity and (hour <= 2 or terminal or shed_total >= SHED_CAPACITY - int(self.genome["market"]["sell_buffer"])):
                orders.append(["SELL", good, quantity])
                money += quantity * int(obs.get("market", {}).get("prices", {}).get(good, 1) or 1)
                shed_total -= quantity
                if len(orders) == 10:
                    return orders

        def afford(cost: int) -> bool:
            nonlocal money
            if money - cost < reserve:
                self.audit["market_withheld"] += 1
                return False
            money -= cost
            return True

        def affordable_quantity(requested: int, unit_cost: int) -> int:
            return max(0, min(int(requested), (money - reserve) // max(1, int(unit_cost))))

        # Feed stock is a production prerequisite and has first claim on cash.
        feed_need = max(0, int(goal["feed_reserve"]) - int(shed.get("WHEAT", 0) or 0)
                        - int(carried.get("WHEAT", 0) or 0))
        if feed_need and shed_total < SHED_CAPACITY and len(orders) < 10:
            qty = min(feed_need, SHED_CAPACITY - shed_total, 18)
            px = int(obs.get("market", {}).get("prices", {}).get("WHEAT", 25) or 25)
            qty = affordable_quantity(qty, px)
            if qty > 0 and afford(qty * px):
                orders.append(["BUY_PRODUCT", "WHEAT", qty])
                shed_total += qty

        # Seeds are derived from the observed crop deficit, not a planting tape.
        for crop in CROP_ORDER:
            missing = max(0, int(goal["crops"].get(crop, 0)) - int(crop_have.get(crop, 0))
                          - int(seeds.get(crop, 0) or 0))
            if not missing or len(orders) >= 10:
                continue
            qty = min(missing, 12)
            unit_cost = int(CROPS[crop]["seed"])
            qty = affordable_quantity(qty, unit_cost)
            if qty > 0 and afford(qty * unit_cost):
                orders.append(["BUY_SEED", crop, qty])

        # Structural purchases are retried until state proves they succeeded.
        unlocked_count = max(1, len(_unlocked(grid)) // 25)
        if unlocked_count < int(goal["lands"]) and len(orders) < 10:
            price = int(LAND_PRICES[max(0, unlocked_count - 1)])
            if afford(price):
                orders.append(["BUY_LAND"])

        for kind in ANIMAL_ORDER:
            target = int(goal["animals"].get(kind, 0))
            have = (int(animal_have.get(kind, 0)) + int(shed.get(kind, 0) or 0)
                    + int(carried.get(kind, 0) or 0))
            missing = min(target - have, ANIMALS[kind]["max_held"] - have)
            if missing <= 0 or len(orders) >= 10:
                continue
            qty = min(missing, SHED_CAPACITY - shed_total)
            unit_cost = int(ANIMALS[kind]["cost"])
            qty = affordable_quantity(qty, unit_cost)
            if qty > 0 and afford(qty * unit_cost):
                orders.append(["BUY_ANIMAL", kind, qty])
                shed_total += qty

        # Hires are cheap but emitted only up to the observed daily gap.
        current_hands = len(farm.get("hands", []) or [])
        missing_hands = max(0, int(goal["hands"]) - current_hands - self.hires_sent)
        for _ in range(missing_hands):
            if len(orders) >= 10:
                break
            cost = fib_hire_cost(self.hires_sent)
            if not afford(cost):
                break
            orders.append(["HIRE"])
            self.hires_sent += 1
        return orders[:10]

    def _jobs(self, day: int, hour: int, grid: list[list[Any]], goal: dict[str, Any],
              seeds: dict[str, int]) -> list[tuple[int, int, int, tuple[Any, ...]]]:
        jobs: list[tuple[int, int, int, tuple[Any, ...]]] = []
        crop_have, animal_have, structures = self._counts(grid)

        # Preserve and service all productive assets already present.
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
                    ripe = facts.get("ongoing") or units >= int(facts.get("max_yield", 99)) \
                        or age >= int(facts.get("max_yield_day", 99))
                    if units > 0 and age >= int(facts.get("first_yield_day", 0)) and ripe:
                        jobs.append((2, x, y, ("HARVEST",)))
                elif _tile_animal(tile):
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

        # Dynamic layout: reserve nearest empty cells for current animal gaps;
        # crops consume the remainder. No coordinate is persisted in the genome.
        empty = _position_order([(x, y) for x, y in _unlocked(grid) if grid[y][x] is None])
        pasture_goal = int(goal["animals"].get("SHEEP", 0)) + int(goal["animals"].get("COW", 0))
        coop_goal = int(goal["animals"].get("GOOSE", 0))
        pasture_gap = max(0, pasture_goal - int(structures.get("PASTURE", 0)))
        coop_gap = max(0, coop_goal - int(structures.get("COOP", 0)))
        cursor = 0
        for structure, count in (("PASTURE", pasture_gap), ("COOP", coop_gap)):
            for _ in range(min(count, max(0, len(empty) - cursor))):
                x, y = empty[cursor]
                cursor += 1
                jobs.append((4, x, y, ("BUILD_PASTURE" if structure == "PASTURE" else "BUILD_COOP",)))

        # Fill observed empty structures with an animal actually present in a
        # unit. PLACE itself is filtered per unit later; the job remains visible
        # so a shed pickup mission can be generated.
        animal_deficit = {kind: max(0, int(goal["animals"].get(kind, 0)) - int(animal_have.get(kind, 0)))
                          for kind in ANIMAL_ORDER}
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if not isinstance(tile, dict) or _tile_animal(tile):
                    continue
                struct = tile.get("kind")
                compatible = ("GOOSE",) if struct == "COOP" else ("SHEEP", "COW") if struct == "PASTURE" else ()
                for kind in compatible:
                    if animal_deficit[kind] > 0:
                        jobs.append((3, x, y, ("PLACE", kind)))
                        animal_deficit[kind] -= 1
                        break

        # Seed-budgeted plant jobs avoid the engine's atomic same-crop failure.
        plantable = empty[cursor:]
        seed_budget = {crop: int(seeds.get(crop, 0) or 0) for crop in CROP_ORDER}
        for crop in CROP_ORDER:
            gap = max(0, int(goal["crops"].get(crop, 0)) - int(crop_have.get(crop, 0)))
            take = min(gap, seed_budget[crop], len(plantable))
            for _ in range(take):
                x, y = plantable.pop(0)
                jobs.append((3, x, y, ("PLANT", crop)))
            seed_budget[crop] -= take
        return jobs

    def _cost(self, unit_index: int, pos: tuple[int, int], inv: dict[str, int],
              job: tuple[int, int, int, tuple[Any, ...]], hour: int) -> float:
        priority, x, y, verb = job
        op = verb[0]
        if op == "FEED" and int(inv.get("WHEAT", 0) or 0) <= 0:
            return math.inf
        if op == "PLACE" and int(inv.get(verb[1], 0) or 0) <= 0:
            return math.inf
        distance = _dist(pos, (x, y))
        deadline = 23 if op in {"WATER", "FEED", "PLANT", "PLACE", "DIG"} else 24
        late = max(0, hour + distance + 1 - deadline)
        sticky = -5.0 if self.sticky.get(unit_index) == _job_key(job) else 0.0
        return priority * 100.0 + late * 1000.0 + distance + sticky

    def _assign(self, units: list[Any], invs: list[dict[str, Any]], jobs: list[Any], hour: int,
                unavailable: set[int]) -> dict[int, Any]:
        """Joint greedy auction: global best unit-job edge on every round."""
        assignments: dict[int, Any] = {}
        remaining_units = {i for i, unit in enumerate(units) if unit and i not in unavailable}
        remaining_jobs = {_job_key(job): job for job in jobs}
        while remaining_units and remaining_jobs:
            best: tuple[float, int, tuple[Any, ...]] | None = None
            for i in remaining_units:
                pos = (int(units[i][0]), int(units[i][1]))
                inv = dict(invs[i] or {})
                for key, job in remaining_jobs.items():
                    cost = self._cost(i, pos, inv, job, hour)
                    edge = (cost, i, key)
                    if math.isfinite(cost) and (best is None or edge < best):
                        best = edge
            if best is None:
                break
            _cost, i, key = best
            assignments[i] = remaining_jobs.pop(key)
            remaining_units.remove(i)
        return assignments

    def act(self, obs: dict[str, Any]) -> dict[str, Any]:
        seat = self._seat(obs)
        day = min(29, int(obs.get("day", 0) or 0))
        hour = int(obs.get("hour", 0) or 0)
        if day != self.day:
            self.day = day
            self.hires_sent = 0
            self.sticky.clear()
        goal = self.goals[day]
        farm = (obs.get("farms") or [{}, {}])[seat]
        grid = list(farm.get("tiles", []) or [])
        private = obs.get("private", {}) or {}
        seeds = dict(private.get("seeds", {}) or {})
        shed = dict(private.get("shed", {}) or {})
        invs = list(private.get("inventories", []) or [])
        units = [farm.get("farmer")] + list(farm.get("hands", []) or [])
        while len(invs) < len(units):
            invs.append({})

        market = self._market_orders(obs, farm, grid, goal, seeds, shed, invs)
        jobs = self._jobs(day, hour, grid, goal, seeds)
        synthetic: dict[int, list[Any]] = {}

        # One wheat runner is enough: inventories are unbounded and the same
        # runner feeds several animals without returning to the shed.
        unfed = sum(job[3][0] == "FEED" for job in jobs)
        wheat_carrier = any(int(dict(inv or {}).get("WHEAT", 0) or 0) > 0 for inv in invs)
        if unfed and not wheat_carrier and int(shed.get("WHEAT", 0) or 0) > 0:
            i = min(range(len(units)), key=lambda j: _dist(tuple(units[j]), _shed_gate(tuple(units[j]))))
            pos = tuple(units[i])
            synthetic[i] = (["PICKUP", "WHEAT", min(unfed, int(shed["WHEAT"]))]
                            if pos in SHED_TILES else _toward(pos, _shed_gate(pos)))

        # Fetch one missing animal kind at a time. A carrier then becomes the
        # only feasible unit for its PLACE job, so the auction routes it there.
        for job in jobs:
            if job[3][0] != "PLACE":
                continue
            kind = job[3][1]
            if any(int(dict(inv or {}).get(kind, 0) or 0) > 0 for inv in invs):
                continue
            if int(shed.get(kind, 0) or 0) <= 0:
                continue
            candidates = [i for i in range(len(units)) if i not in synthetic]
            if candidates:
                i = min(candidates, key=lambda j: _dist(tuple(units[j]), _shed_gate(tuple(units[j]))))
                pos = tuple(units[i])
                synthetic[i] = (["PICKUP", kind, 1] if pos in SHED_TILES else _toward(pos, _shed_gate(pos)))
            break

        # Final evening: turn carried goods into cash. DROP resolves before
        # same-turn SELL, so a unit already at the shed can finance immediately.
        if day == 29 and hour >= 18:
            for i, unit in enumerate(units):
                if i in synthetic or not any(int(v or 0) > 0 for v in dict(invs[i] or {}).values()):
                    continue
                pos = tuple(unit)
                synthetic[i] = ["DROP"] if pos in SHED_TILES else _toward(pos, _shed_gate(pos))
            # Existing terminal sells must also cover goods dropped by unit
            # actions earlier in this same engine turn.
            for order in market:
                if order[0] == "SELL":
                    order[2] = 999
            present = set(order[1] for order in market if order[0] == "SELL")
            for good in PRODUCTS:
                if good not in present and len(market) < 10:
                    market.append(["SELL", good, 999])

        assignments = self._assign(units, invs, jobs, hour, set(synthetic))
        verbs: list[list[Any]] = []
        for i, unit in enumerate(units):
            pos = (int(unit[0]), int(unit[1]))
            if i in synthetic:
                verb = synthetic[i]
            elif i in assignments:
                job = assignments[i]
                _priority, x, y, task = job
                self.sticky[i] = _job_key(job)
                verb = list(task) if pos == (x, y) else _toward(pos, (x, y))
            else:
                self.sticky.pop(i, None)
                verb = PASS.copy()
            self.audit[f"action_{verb[0].lower()}"] += 1
            verbs.append(verb)
        self.audit["calls"] += 1
        self.audit["jobs_generated"] += len(jobs)
        return {"farmer": verbs[0] if verbs else PASS.copy(), "hands": verbs[1:], "market": market[:10]}


def make_agent(genome: dict[str, Any] | None = None) -> Any:
    return DailyGoalExecutor(genome).act
