#!/usr/bin/env python3
"""R10 Enterprise Queue HMoE: an original current-state enterprise executor.

The policy compiles aggregate production programs into current-observation
layout leases and persistent task tickets.  It contains no recorded route or
historical player action stream and has no strategy parent.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import Any, Mapping


SCHEMA = "v116-r10-enterprise-queue-hmoe-v1"
STRATEGY_PARENT = None
MODES = (
    "router",
    "fixed_root_exchange",
    "fixed_dairy_berry",
    "fixed_fiber_grain",
)
EXPERTS = ("root_exchange", "dairy_berry", "fiber_grain")
TASK_STATES = (
    "WAIT_RESOURCE", "ACQUIRE", "TRAVEL", "EXECUTE", "DELIVER",
    "COMPLETE", "CANCELLED",
)
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "max_day": 4, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first": 2, "max_day": 3, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first": 8, "max_day": 8, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first": 10, "max_day": 10, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "first": 10, "max_day": 12, "max_yield": 6, "ongoing": False},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first": 8, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first": 6, "product": "WOOL"},
}
BASE_PRICE = {
    "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
    "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200,
    "FERTILIZER": 100,
}
MARKET_CURVE = {
    "WHEAT": (400, "sqrt", .80, "log", .20),
    "CARROT": (450, "hinge", 1.00, "sqrt", .70),
    "TOMATO": (200, "hinge", .40, "sqrt", .60),
    "STRAWBERRY": (100, "sqrt", .70, "linear", 1.60),
    "MELON": (300, "log", .20, "sq", 3.60),
    "EGG": (332, "hinge", .40, "log", .20),
    "MILK": (122, "sqrt", .60, "linear", 1.60),
    "WOOL": (105, "log", .20, "sq", 3.20),
    "FERTILIZER": (200, "linear", .40, "linear", .40),
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
SHED_GATES = ((4, 4), (5, 4), (4, 5), (5, 5))
LAND_PRICES = (1000, 2000, 4000)
SHED_CAPACITY = 100
PASS = ["PASS"]


DEFAULT_PARAMS: dict[str, Any] = {
    "cash_floor": 150,
    "capacity_pressure": 88,
    "scarcity_ratio": 1.05,
    "max_daily_units": 12,
    "work_per_unit": 6,
    "delivery_load": 8,
    "terminal_buffer": 2,
}


ENTERPRISE_PROGRAMS: dict[str, tuple[dict[str, Any], ...]] = {
    "root_exchange": (
        {"day": 0, "crops": {"WHEAT": 8, "CARROT": 6, "MELON": 4}, "animals": {}},
        {"day": 3, "crops": {"WHEAT": 12, "CARROT": 16, "TOMATO": 6, "MELON": 6}, "animals": {}},
        {"day": 8, "crops": {"WHEAT": 18, "CARROT": 24, "TOMATO": 12, "MELON": 8}, "animals": {}},
    ),
    "dairy_berry": (
        {"day": 0, "crops": {"WHEAT": 8, "CARROT": 4, "MELON": 4}, "animals": {"COW": 2}},
        {"day": 3, "crops": {"WHEAT": 14, "STRAWBERRY": 12, "MELON": 6, "TOMATO": 4}, "animals": {"COW": 4}},
        {"day": 8, "crops": {"WHEAT": 20, "STRAWBERRY": 22, "TOMATO": 8, "MELON": 8}, "animals": {"COW": 6}},
    ),
    "fiber_grain": (
        {"day": 0, "crops": {"WHEAT": 10, "CARROT": 4, "MELON": 4}, "animals": {"SHEEP": 2, "GOOSE": 2}},
        {"day": 3, "crops": {"WHEAT": 20, "MELON": 8, "CARROT": 4}, "animals": {"SHEEP": 4, "GOOSE": 3}},
        {"day": 8, "crops": {"WHEAT": 30, "MELON": 12, "CARROT": 6, "TOMATO": 4}, "animals": {"SHEEP": 6, "GOOSE": 4}},
    ),
}


@dataclass
class LayoutLease:
    target: tuple[int, int]
    asset: str
    expert: str
    phase: int
    created_step: int


@dataclass
class TaskTicket:
    ticket_id: str
    kind: str
    target: tuple[int, int]
    verb: tuple[Any, ...]
    priority: int
    deadline: int
    created_step: int
    required_item: str | None = None
    quantity: int = 1
    state: str = "WAIT_RESOURCE"
    owner: int | None = None
    retries: int = 0
    expected_cash_value: float = 0.0
    daily: bool = False


@dataclass
class ActorState:
    unit_index: int
    day: int
    zone: int
    role: str
    active_ticket: str | None = None
    interrupted_ticket: str | None = None


@dataclass
class PendingReceipt:
    order_step: int
    kind: str
    item: str | None
    quantity: int


@dataclass
class ResourceLedger:
    shed: Counter[str] = field(default_factory=Counter)
    seeds: Counter[str] = field(default_factory=Counter)
    carried: Counter[str] = field(default_factory=Counter)
    reserved_seeds: Counter[str] = field(default_factory=Counter)
    pending: Counter[str] = field(default_factory=Counter)


@dataclass
class CashLedger:
    cash: int = 0
    reserve: int = 0
    planned_spend: int = 0
    conservative_sales: int = 0


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def canonical_hash(params: Mapping[str, Any]) -> str:
    errors = validate_params(params)
    if errors:
        raise ValueError("; ".join(errors))
    body = json.dumps(_canonical(dict(params)), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)
    return hashlib.sha256((SCHEMA + "\0" + body).encode("utf-8")).hexdigest()


def validate_params(params: Mapping[str, Any]) -> list[str]:
    if not isinstance(params, Mapping) or set(params) != set(DEFAULT_PARAMS):
        return ["params must have exactly the frozen R10 keys"]
    errors: list[str] = []
    integer_fields = {"cash_floor", "capacity_pressure", "max_daily_units",
                      "work_per_unit", "delivery_load", "terminal_buffer"}
    for name in integer_fields:
        value = params[name]
        if not isinstance(value, int) or isinstance(value, bool) or int(value) <= 0:
            errors.append(f"{name} must be a positive integer")
    ratio = params["scarcity_ratio"]
    if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not 1.0 <= float(ratio) <= 2.0:
        errors.append("scarcity_ratio must be in [1,2]")
    if isinstance(params.get("capacity_pressure"), int) and not 70 <= int(params["capacity_pressure"]) <= 99:
        errors.append("capacity_pressure must be in [70,99]")
    return errors


def _dist(left: tuple[int, int], right: tuple[int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _toward(position: tuple[int, int], target: tuple[int, int]) -> list[str]:
    dx, dy = target[0] - position[0], target[1] - position[1]
    if abs(dx) >= abs(dy) and dx:
        return ["EAST" if dx > 0 else "WEST"]
    if dy:
        return ["SOUTH" if dy > 0 else "NORTH"]
    return PASS.copy()


def _gate(position: tuple[int, int]) -> tuple[int, int]:
    return min(SHED_GATES, key=lambda gate: (_dist(position, gate), gate))


def _zone(position: tuple[int, int]) -> int:
    return (2 if position[1] >= 5 else 0) + (1 if position[0] >= 5 else 0)


def _tile(grid: list[list[Any]], target: tuple[int, int]) -> Any:
    x, y = target
    if y < 0 or y >= len(grid) or x < 0 or x >= len(grid[y]):
        return "LOCKED"
    return grid[y][x]


def _animal(tile: Any) -> str | None:
    if not isinstance(tile, Mapping) or not tile.get("animal"):
        return None
    value = tile["animal"]
    return str(value.get("kind")) if isinstance(value, Mapping) else str(value)


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
        unit = value / target if target else value
        return unit + 8.0 * max(0.0, unit - 1.0) ** 2
    return value


def market_price(item: str, inventory: int) -> int:
    target, below_shape, below_ratio, above_shape, above_ratio = MARKET_CURVE[item]
    base = BASE_PRICE[item]
    if inventory < 10000:
        amplitude = below_ratio * base / _shape(below_shape, target, target)
        price = base + amplitude * _shape(below_shape, 10000 - inventory, target)
    else:
        amplitude = above_ratio * base / _shape(above_shape, target, target)
        price = base - amplitude * _shape(above_shape, inventory - 10000, target)
    return max(1, int(round(price)))


def _counts(grid: list[list[Any]]) -> tuple[Counter[str], Counter[str], Counter[str]]:
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    structures: Counter[str] = Counter()
    for row in grid:
        for tile in row:
            if not isinstance(tile, Mapping):
                continue
            if tile.get("kind") == "PLANT" and tile.get("crop") in CROPS:
                crops[str(tile["crop"])] += 1
            animal = _animal(tile)
            if animal:
                animals[animal] += 1
            if tile.get("kind") in {"COOP", "PASTURE"}:
                structures[str(tile["kind"])] += 1
    return crops, animals, structures


def _inventory_total(inventories: list[dict[str, Any]]) -> Counter[str]:
    result: Counter[str] = Counter()
    for inventory in inventories:
        for item, quantity in dict(inventory or {}).items():
            result[str(item)] += int(quantity or 0)
    return result


class EnterpriseQueueExecutor:
    def __init__(self, params: Mapping[str, Any] | None = None, mode: str = "router") -> None:
        self.params = dict(DEFAULT_PARAMS if params is None else params)
        errors = validate_params(self.params)
        if errors:
            raise ValueError("; ".join(errors))
        if mode not in MODES:
            raise ValueError(f"unknown R10 mode {mode!r}")
        self.mode = mode
        self.expert = mode.removeprefix("fixed_") if mode.startswith("fixed_") else "bootstrap"
        self.committed = mode.startswith("fixed_")
        self.commit_step: int | None = 0 if self.committed else None
        self.first_shop: str | None = None
        self.bootstrap_goal: dict[str, Any] | None = None
        self.current_day = -1
        self.phase = -1
        self.layout_signature: tuple[Any, ...] | None = None
        self.leases: dict[tuple[int, int], LayoutLease] = {}
        self.tickets: dict[str, TaskTicket] = {}
        self.actors: dict[int, ActorState] = {}
        self.pending_unit_intents: dict[int, dict[str, Any]] = {}
        self.pending_receipts: list[PendingReceipt] = []
        self.resource_ledger = ResourceLedger()
        self.cash_ledger = CashLedger()
        self.sell_states: Counter[str] = Counter()
        self.audit: Counter[str] = Counter()
        self.route_scores: dict[str, float] = {}
        self.last_step: int | None = None
        self.last_action: dict[str, Any] | None = None

    @staticmethod
    def _seat(obs: Mapping[str, Any]) -> int:
        for key in ("player_index", "index", "player"):
            if obs.get(key) is not None:
                return int(obs[key])
        return 0

    @staticmethod
    def _step(obs: Mapping[str, Any]) -> int:
        return int(obs.get("step", int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))) or 0)

    def _optionality_goal(self, obs: Mapping[str, Any]) -> dict[str, Any]:
        prices = dict((obs.get("market") or {}).get("prices", {}) or {})
        scores = {
            crop: float(prices.get(crop, BASE_PRICE[crop]) or BASE_PRICE[crop])
                  * int(CROPS[crop]["max_yield"])
                  / max(1, int(CROPS[crop]["seed"]) * int(CROPS[crop]["first"]))
            for crop in ("WHEAT", "CARROT", "MELON")
        }
        crops: Counter[str] = Counter({"WHEAT": 8, "CARROT": 4, "MELON": 4})
        for _ in range(2):
            winner = max(scores, key=lambda crop: (scores[crop] / (1 + crops[crop]), -list(scores).index(crop)))
            crops[winner] += 1
        return {"crops": dict(crops), "animals": {}, "phase": 0, "expert": "bootstrap"}

    def _program_goal(self, day: int, obs: Mapping[str, Any]) -> dict[str, Any]:
        if not self.committed:
            if self.bootstrap_goal is None:
                self.bootstrap_goal = self._optionality_goal(obs)
            return dict(self.bootstrap_goal)
        rows = ENTERPRISE_PROGRAMS[self.expert]
        index = max(i for i, row in enumerate(rows) if day >= int(row["day"]))
        row = rows[index]
        return {"crops": dict(row["crops"]), "animals": dict(row["animals"]),
                "phase": index, "expert": self.expert}

    def _route(self, obs: Mapping[str, Any], grid: list[list[Any]]) -> None:
        shops = [str(value) for value in list((obs.get("town") or {}).get("unlocked_shops", []) or [])]
        if shops and self.first_shop is None:
            self.first_shop = shops[0]
        if self.committed or not shops:
            return
        first = shops[0]
        demanded = set(SHOP_PRODUCTS.get(first, ()))
        prices = dict((obs.get("market") or {}).get("prices", {}) or {})
        crops, animals, _ = _counts(grid)
        farms = list(obs.get("farms") or [{}, {}])
        seat = self._seat(obs)
        rival_grid = list((farms[1 - seat] if len(farms) >= 2 else {}).get("tiles", []) or [])
        rival_crops, rival_animals, _ = _counts(rival_grid)
        own_products = Counter(crops)
        rival_products = Counter(rival_crops)
        for kind, count in animals.items():
            own_products[ANIMALS[kind]["product"]] += count
        for kind, count in rival_animals.items():
            rival_products[ANIMALS[kind]["product"]] += count
        scores: dict[str, float] = {}
        for expert, rows in ENTERPRISE_PROGRAMS.items():
            final = rows[-1]
            products = Counter(final["crops"])
            for kind, count in final["animals"].items():
                products[ANIMALS[kind]["product"]] += int(count)
            demand_value = sum(min(12, products[item]) for item in demanded) * 5.0
            price_value = sum(products[item] * float(prices.get(item, BASE_PRICE[item]))
                              / max(1, BASE_PRICE[item]) for item in demanded)
            reuse = sum(min(products[item], own_products[item]) for item in products) * 1.5
            collision = sum(min(products[item], rival_products[item]) for item in demanded) * .5
            scores[expert] = demand_value + price_value + reuse - collision
        self.route_scores = scores
        self.expert = max(EXPERTS, key=lambda name: (scores[name], -EXPERTS.index(name)))
        self.committed = True
        self.commit_step = self._step(obs)
        self.layout_signature = None
        self.audit[f"route_{self.expert}"] += 1

    def _reconcile_receipts(self, step: int) -> None:
        retained: list[PendingReceipt] = []
        for receipt in self.pending_receipts:
            if step > receipt.order_step:
                self.audit["receipts_reconciled"] += 1
            else:
                retained.append(receipt)
        self.pending_receipts = retained

    def _ticket_satisfied(self, ticket: TaskTicket, grid: list[list[Any]]) -> bool:
        # DELIVER retargets a production ticket from its asset tile to a shed
        # gate.  Completion must therefore come from an observed DROP (or the
        # overnight inventory flush), never from inspecting the empty gate.
        if ticket.state == "DELIVER":
            return False
        tile = _tile(grid, ticket.target)
        if ticket.kind == "WATER":
            return not isinstance(tile, Mapping) or bool(tile.get("watered_today"))
        if ticket.kind == "FEED":
            return not _animal(tile) or bool(tile.get("fed_today"))
        if ticket.kind == "CARE":
            return not _animal(tile) or bool(tile.get("cared_today"))
        if ticket.kind == "COLLECT_FERTILIZER":
            return not _animal(tile) or not bool(tile.get("fertilizer_available"))
        if ticket.kind == "HARVEST":
            return (not isinstance(tile, Mapping) or tile.get("kind") in {None, "WEED"}
                    or int(tile.get("yield_units", 0) or 0) == 0)
        if ticket.kind == "DIG":
            return tile is None
        if ticket.kind == "PLANT":
            return isinstance(tile, Mapping) and tile.get("kind") == "PLANT" \
                and str(tile.get("crop")) == str(ticket.verb[1])
        if ticket.kind == "BUILD":
            want = "COOP" if ticket.verb[0] == "BUILD_COOP" else "PASTURE"
            return isinstance(tile, Mapping) and tile.get("kind") == want
        if ticket.kind == "PLACE":
            return _animal(tile) == str(ticket.verb[1])
        return False

    def _finish_ticket(self, ticket: TaskTicket) -> None:
        ticket.state = "COMPLETE"
        if ticket.owner is not None and ticket.owner in self.actors:
            self.actors[ticket.owner].active_ticket = None
        ticket.owner = None
        self.audit[f"completed_{ticket.kind.lower()}"] += 1

    def _reconcile_unit_intents(self, step: int, grid: list[list[Any]],
                                units: list[Any], inventories: list[dict[str, Any]]) -> None:
        for index, intent in list(self.pending_unit_intents.items()):
            ticket = self.tickets.get(str(intent.get("ticket_id")))
            if ticket is None or ticket.state in {"COMPLETE", "CANCELLED"}:
                continue
            verb = list(intent.get("verb") or [])
            inventory = dict(inventories[index] or {}) if index < len(inventories) else {}
            if not verb:
                continue
            op = str(verb[0])
            if op in {"NORTH", "SOUTH", "EAST", "WEST"}:
                if index < len(units) and units[index]:
                    position = tuple(units[index])
                    before = int(intent.get("distance", 0))
                    if _dist(position, ticket.target) >= before:
                        self.audit["nonprogress_move"] += 1
                continue
            if op == "PICKUP":
                item = str(verb[1])
                if int(inventory.get(item, 0) or 0) > int(intent.get("before_qty", 0)):
                    ticket.state = "TRAVEL"
                else:
                    ticket.retries += 1
                    ticket.state = "WAIT_RESOURCE"
            elif op == "DROP":
                if not any(int(value or 0) > 0 for value in inventory.values()):
                    self._finish_ticket(ticket)
            elif self._ticket_satisfied(ticket, grid):
                if ticket.kind == "HARVEST" and any(int(value or 0) > 0 for value in inventory.values()):
                    ticket.state = "DELIVER"
                    ticket.target = _gate(tuple(intent.get("position", (4, 4))))
                else:
                    self._finish_ticket(ticket)
            else:
                ticket.retries += 1
                ticket.state = "TRAVEL"
        self.pending_unit_intents.clear()

    def _day_rebind(self, day: int) -> None:
        if day == self.current_day:
            return
        for ticket in self.tickets.values():
            if ticket.state not in {"COMPLETE", "CANCELLED"}:
                ticket.owner = None
                if ticket.state in {"ACQUIRE", "TRAVEL", "EXECUTE", "DELIVER"}:
                    ticket.state = "WAIT_RESOURCE" if ticket.required_item else "TRAVEL"
        self.actors.clear()
        self.current_day = day
        self.audit["day_rebinds"] += 1

    def _unlocked(self, grid: list[list[Any]]) -> list[tuple[int, int]]:
        result = []
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                if tile == "LOCKED" or (isinstance(tile, Mapping) and tile.get("kind") == "LOCKED"):
                    continue
                result.append((x, y))
        return result

    @staticmethod
    def _asset_matches(tile: Any, asset: str) -> bool:
        if asset.startswith("CROP:"):
            return isinstance(tile, Mapping) and tile.get("kind") == "PLANT" \
                and str(tile.get("crop")) == asset.split(":", 1)[1]
        if asset.startswith("ANIMAL:"):
            return _animal(tile) == asset.split(":", 1)[1]
        return False

    def _layout_cost(self, target: tuple[int, int], asset: str) -> tuple[float, int, int]:
        distance = min(_dist(target, gate) for gate in SHED_GATES)
        name = asset.split(":", 1)[1]
        frequency = 4.0 if asset.startswith("ANIMAL:") else (
            2.5 if name in {"TOMATO", "STRAWBERRY"} else
            2.0 if name in {"WHEAT", "CARROT"} else 1.0
        )
        preferred_zone = (sum(ord(char) for char in name) + len(name)) % 4
        zone_cost = 0.0 if _zone(target) == preferred_zone else .25
        return distance * frequency + zone_cost, target[1], target[0]

    def _ensure_layout(self, step: int, grid: list[list[Any]], goal: Mapping[str, Any], lands: int) -> None:
        signature = (goal["expert"], int(goal["phase"]), int(lands))
        if signature == self.layout_signature:
            return
        desired: Counter[str] = Counter()
        desired.update({f"CROP:{crop}": int(count) for crop, count in goal["crops"].items()})
        desired.update({f"ANIMAL:{kind}": int(count) for kind, count in goal["animals"].items()})
        kept: dict[tuple[int, int], LayoutLease] = {}
        for target, lease in sorted(self.leases.items()):
            tile = _tile(grid, target)
            if desired[lease.asset] <= 0 or tile == "LOCKED":
                continue
            if tile is None or (isinstance(tile, Mapping) and tile.get("kind") == "WEED") \
                    or self._asset_matches(tile, lease.asset):
                kept[target] = LayoutLease(target, lease.asset, str(goal["expert"]),
                                           int(goal["phase"]), lease.created_step)
                desired[lease.asset] -= 1
        occupied = set(kept)
        for target in self._unlocked(grid):
            if target in occupied:
                continue
            tile = _tile(grid, target)
            for asset in sorted(desired):
                if desired[asset] > 0 and self._asset_matches(tile, asset):
                    kept[target] = LayoutLease(target, asset, str(goal["expert"]),
                                               int(goal["phase"]), step)
                    occupied.add(target)
                    desired[asset] -= 1
                    break
        empty = [target for target in self._unlocked(grid)
                 if target not in occupied and _tile(grid, target) is None]
        for asset in sorted(desired):
            for _ in range(desired[asset]):
                if not empty:
                    break
                target = min(empty, key=lambda value: self._layout_cost(value, asset))
                empty.remove(target)
                kept[target] = LayoutLease(target, asset, str(goal["expert"]),
                                           int(goal["phase"]), step)
        self.leases = kept
        self.layout_signature = signature
        self.phase = int(goal["phase"])
        self.audit["layout_rebuilds"] += 1

    def _upsert(self, key: str, kind: str, target: tuple[int, int], verb: tuple[Any, ...],
                priority: int, deadline: int, step: int, required_item: str | None = None,
                quantity: int = 1, daily: bool = False) -> None:
        existing = self.tickets.get(key)
        if existing and existing.state not in {"COMPLETE", "CANCELLED"}:
            existing.priority = min(existing.priority, priority)
            existing.deadline = min(existing.deadline, deadline)
            return
        self.tickets[key] = TaskTicket(
            ticket_id=key, kind=kind, target=target, verb=verb,
            priority=priority, deadline=deadline, created_step=step,
            required_item=required_item, quantity=quantity, daily=daily,
        )

    def _refresh_tickets(self, step: int, day: int, hour: int, grid: list[list[Any]]) -> None:
        for ticket in self.tickets.values():
            if ticket.state not in {"COMPLETE", "CANCELLED"} and self._ticket_satisfied(ticket, grid):
                self._finish_ticket(ticket)
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                target = (x, y)
                if not isinstance(tile, Mapping):
                    continue
                kind = tile.get("kind")
                if kind == "PLANT":
                    crop = str(tile.get("crop"))
                    if not tile.get("watered_today"):
                        urgent = int(tile.get("consecutive_unwatered", 0) or 0) >= 1 or hour >= 18
                        self._upsert(f"D{day}:WATER:{x}:{y}", "WATER", target, ("WATER",),
                                     0 if urgent else 1, day * 24 + 23, step, daily=True)
                    facts = CROPS.get(crop, {})
                    planted_day = tile.get("planted_day", day)
                    age = day - int(day if planted_day is None else planted_day)
                    units = int(tile.get("yield_units", 0) or 0)
                    ripe = bool(facts.get("ongoing")) or units >= int(facts.get("max_yield", 99)) \
                        or age >= int(facts.get("max_day", 99))
                    if units > 0 and age >= int(facts.get("first", 99)) and ripe:
                        self._upsert(f"HARVEST:{x}:{y}:{crop}:{int(tile.get('planted_day', 0) or 0)}",
                                     "HARVEST", target, ("HARVEST",), 2, step + 12, step)
                animal = _animal(tile)
                if animal:
                    if not tile.get("fed_today"):
                        urgent = int(tile.get("consecutive_unfed", 0) or 0) >= 1 or hour >= 18
                        self._upsert(f"D{day}:FEED:{x}:{y}", "FEED", target, ("FEED",),
                                     0 if urgent else 1, day * 24 + 23, step,
                                     required_item="WHEAT", daily=True)
                    if int(tile.get("yield_units", 0) or 0) > 0:
                        self._upsert(f"HARVEST:{x}:{y}:{animal}:{int(tile.get('placed_day', 0) or 0)}",
                                     "HARVEST", target, ("HARVEST",), 2, step + 12, step)
                    if tile.get("fertilizer_available"):
                        self._upsert(f"D{day}:FERT:{x}:{y}", "COLLECT_FERTILIZER", target,
                                     ("COLLECT_FERTILIZER",), 4, day * 24 + 22, step, daily=True)
                    if not tile.get("cared_today"):
                        self._upsert(f"D{day}:CARE:{x}:{y}", "CARE", target, ("CARE",),
                                     4, day * 24 + 22, step, daily=True)
                elif kind == "WEED":
                    self._upsert(f"DIG:{x}:{y}", "DIG", target, ("DIG",), 5, step + 24, step)
        for target, lease in self.leases.items():
            tile = _tile(grid, target)
            x, y = target
            if isinstance(tile, Mapping) and tile.get("kind") == "WEED":
                self._upsert(f"DIG:{x}:{y}", "DIG", target, ("DIG",), 3, step + 12, step)
                continue
            if lease.asset.startswith("CROP:"):
                crop = lease.asset.split(":", 1)[1]
                if tile is None and day + int(CROPS[crop]["first"]) <= 29:
                    self._upsert(f"PLANT:{x}:{y}:{crop}", "PLANT", target, ("PLANT", crop),
                                 3, step + 24, step, required_item=crop)
            else:
                animal = lease.asset.split(":", 1)[1]
                structure = str(ANIMALS[animal]["structure"])
                if tile is None:
                    self._upsert(f"BUILD:{x}:{y}:{structure}", "BUILD", target,
                                 ("BUILD_COOP" if structure == "COOP" else "BUILD_PASTURE",),
                                 3, step + 24, step)
                elif isinstance(tile, Mapping) and tile.get("kind") == structure and not _animal(tile) \
                        and day + int(ANIMALS[animal]["first"]) <= 29:
                    self._upsert(f"PLACE:{x}:{y}:{animal}", "PLACE", target,
                                 ("PLACE", animal), 2, step + 24, step,
                                 required_item=animal)
        for key, ticket in list(self.tickets.items()):
            if ticket.state in {"COMPLETE", "CANCELLED"} and step - ticket.created_step > 48:
                del self.tickets[key]

    def _sync_ledgers(self, farm: Mapping[str, Any], private: Mapping[str, Any],
                      inventories: list[dict[str, Any]]) -> None:
        self.resource_ledger.shed = Counter({str(k): int(v or 0)
                                             for k, v in dict(private.get("shed", {}) or {}).items()})
        self.resource_ledger.seeds = Counter({str(k): int(v or 0)
                                              for k, v in dict(private.get("seeds", {}) or {}).items()})
        self.resource_ledger.carried = _inventory_total(inventories)
        pending: Counter[str] = Counter()
        for receipt in self.pending_receipts:
            if receipt.item:
                pending[receipt.item] += receipt.quantity
        self.resource_ledger.pending = pending
        self.cash_ledger.cash = int(farm.get("money", 0) or 0)

    def _sync_actors(self, units: list[Any], lands: int) -> None:
        roles = ("runner", "builder_planter", "harvester", "caretaker")
        for index, unit in enumerate(units):
            if not unit:
                continue
            position = (int(unit[0]), int(unit[1]))
            if index not in self.actors:
                self.actors[index] = ActorState(index, self.current_day,
                                                index % max(1, lands), roles[index % len(roles)])
            actor = self.actors[index]
            actor.day = self.current_day
            if actor.zone >= max(1, lands):
                actor.zone = _zone(position) % max(1, lands)
        for index in list(self.actors):
            if index >= len(units):
                ticket = self.tickets.get(self.actors[index].active_ticket or "")
                if ticket:
                    ticket.owner = None
                del self.actors[index]

    def _prepare_ticket(self, ticket: TaskTicket, index: int,
                        inventory: Mapping[str, Any], seed_budget: Counter[str]) -> bool:
        if ticket.required_item is None:
            ticket.state = "TRAVEL"
            return True
        item = ticket.required_item
        if ticket.kind == "PLANT":
            if seed_budget[item] <= 0:
                ticket.state = "WAIT_RESOURCE"
                return False
            seed_budget[item] -= 1
            self.resource_ledger.reserved_seeds[item] += 1
            ticket.state = "TRAVEL"
            return True
        if int(inventory.get(item, 0) or 0) > 0:
            ticket.state = "TRAVEL"
            return True
        if self.resource_ledger.shed[item] > 0:
            ticket.state = "ACQUIRE"
            return True
        ticket.state = "WAIT_RESOURCE"
        return False

    def _choose_ticket(self, actor: ActorState, position: tuple[int, int],
                       inventory: Mapping[str, Any], seed_budget: Counter[str], step: int) -> TaskTicket | None:
        candidates: list[tuple[Any, TaskTicket]] = []
        for ticket in self.tickets.values():
            if ticket.owner is not None or ticket.state in {"COMPLETE", "CANCELLED"}:
                continue
            role_penalty = 0
            if actor.role == "runner" and ticket.kind not in {"FEED", "PLACE", "HARVEST"}:
                role_penalty = 1
            if actor.role == "builder_planter" and ticket.kind not in {"BUILD", "PLANT", "PLACE"}:
                role_penalty = 1
            zone_penalty = int(_zone(ticket.target) != actor.zone)
            slack = ticket.deadline - step - _dist(position, ticket.target) - 1
            candidates.append(((ticket.priority, int(slack < 0), slack, role_penalty,
                                zone_penalty, _dist(position, ticket.target), ticket.ticket_id), ticket))
        for _rank, ticket in sorted(candidates, key=lambda row: row[0]):
            if self._prepare_ticket(ticket, actor.unit_index, inventory, seed_budget):
                ticket.owner = actor.unit_index
                actor.active_ticket = ticket.ticket_id
                self.audit["tickets_assigned"] += 1
                return ticket
        return None

    def _advance_actor(self, actor: ActorState, position: tuple[int, int],
                       inventory: Mapping[str, Any], seed_budget: Counter[str], step: int,
                       units: list[Any]) -> list[Any]:
        ticket = self.tickets.get(actor.active_ticket or "")
        if ticket is None or ticket.state in {"COMPLETE", "CANCELLED"}:
            actor.active_ticket = None
            ticket = self._choose_ticket(actor, position, inventory, seed_budget, step)
        if ticket is None:
            self.audit["runnable_pass"] += int(any(
                value.owner is None and value.state not in {"COMPLETE", "CANCELLED", "WAIT_RESOURCE"}
                for value in self.tickets.values()
            ))
            return PASS.copy()
        if ticket.state == "WAIT_RESOURCE" and not self._prepare_ticket(
                ticket, actor.unit_index, inventory, seed_budget):
            ticket.owner = None
            actor.active_ticket = None
            return PASS.copy()
        if ticket.state == "ACQUIRE":
            gate = _gate(position)
            if position != gate:
                return _toward(position, gate)
            item = str(ticket.required_item)
            quantity = min(self.resource_ledger.shed[item], 4 if ticket.kind == "FEED" else 1)
            return ["PICKUP", item, max(1, int(quantity))]
        if ticket.state == "DELIVER":
            gate = _gate(position)
            ticket.target = gate
            if position != gate:
                return _toward(position, gate)
            return ["DROP"]
        if position != ticket.target:
            ticket.state = "TRAVEL"
            return _toward(position, ticket.target)
        ticket.state = "EXECUTE"
        return list(ticket.verb)

    def _projected_shed(self, shed: Counter[str], inventories: list[dict[str, Any]],
                        verbs: list[list[Any]]) -> Counter[str]:
        projected = Counter(shed)
        total = sum(projected.values())
        for index, verb in enumerate(verbs):
            inventory = dict(inventories[index] or {}) if index < len(inventories) else {}
            if verb and verb[0] == "DROP":
                for item, quantity in inventory.items():
                    take = min(int(quantity or 0), max(0, SHED_CAPACITY - total))
                    projected[str(item)] += take
                    total += take
            elif verb and verb[0] == "PICKUP" and len(verb) >= 3:
                projected[str(verb[1])] = max(0, projected[str(verb[1])] - int(verb[2]))
        return projected

    def _terminal(self, step: int, units: list[Any]) -> bool:
        max_return = max((_dist(tuple(unit), _gate(tuple(unit))) for unit in units if unit), default=0)
        return 718 - step <= max_return + int(self.params["terminal_buffer"])

    def _purchase_plan(self, step: int, day: int, hour: int, farm: Mapping[str, Any],
                       goal: Mapping[str, Any], grid: list[list[Any]], units: list[Any],
                       projected: Counter[str], market_inventory: Mapping[str, Any]) -> list[tuple[int, list[Any], int]]:
        if self._terminal(step, units):
            return []
        crops, animals, _ = _counts(grid)
        pending_seed_tasks: Counter[str] = Counter()
        pending_animals: Counter[str] = Counter()
        for ticket in self.tickets.values():
            if ticket.state in {"COMPLETE", "CANCELLED"}:
                continue
            if ticket.kind == "PLANT":
                pending_seed_tasks[str(ticket.verb[1])] += 1
            elif ticket.kind == "PLACE":
                pending_animals[str(ticket.verb[1])] += 1
        orders: list[tuple[int, list[Any], int]] = []
        animal_total = sum(int(value) for value in goal["animals"].values())
        feed_quote = market_price("WHEAT", int(market_inventory.get("WHEAT", 10000) or 10000) - 1)
        feed_gap = max(0, animal_total - projected["WHEAT"] - self.resource_ledger.carried["WHEAT"]
                       - self.resource_ledger.pending["WHEAT"])
        if feed_gap > 0:
            orders.append((100, ["BUY_PRODUCT", "WHEAT", min(12, feed_gap)], feed_quote))
        active_work = sum(ticket.state not in {"COMPLETE", "CANCELLED"}
                          for ticket in self.tickets.values())
        desired_units = min(int(self.params["max_daily_units"]),
                            max(1, math.ceil(active_work / int(self.params["work_per_unit"]))))
        if hour <= 10 and 23 - hour >= 4:
            for _ in range(max(0, desired_units - len(units))):
                hires_today = int(farm.get("hires_today", max(0, len(units) - 1)) or 0)
                cost = self._fib(hires_today + sum(order[1][0] == "HIRE" for order in orders))
                orders.append((95, ["HIRE"], cost))
        for crop, count in sorted(pending_seed_tasks.items()):
            if day + int(CROPS[crop]["first"]) > 29:
                continue
            gap = max(0, count - self.resource_ledger.seeds[crop]
                      - self.resource_ledger.pending[crop])
            if gap:
                orders.append((90, ["BUY_SEED", crop, min(12, gap)], int(CROPS[crop]["seed"])))
        for animal, count in sorted(pending_animals.items()):
            if day + int(ANIMALS[animal]["first"]) > 29:
                continue
            have = animals[animal] + projected[animal] + self.resource_ledger.carried[animal] \
                + self.resource_ledger.pending[animal]
            gap = max(0, count - have)
            if gap:
                orders.append((80, ["BUY_ANIMAL", animal, gap], int(ANIMALS[animal]["cost"])))
        assets = sum(int(value) for value in goal["crops"].values()) \
            + sum(int(value) for value in goal["animals"].values())
        desired_lands = min(4, max(1, math.ceil(assets / 25)))
        current_lands = max(1, len(farm.get("unlocked_quadrants", []) or []))
        if current_lands < desired_lands and day <= 19:
            orders.append((70, ["BUY_LAND"], LAND_PRICES[max(0, current_lands - 1)]))
        return sorted(orders, key=lambda value: (-value[0], tuple(map(str, value[1]))))

    @staticmethod
    def _fib(index: int) -> int:
        left, right = 1, 1
        for _ in range(max(0, int(index))):
            left, right = right, left + right
        return left

    def _known_demand(self, step: int, shops: list[str], item: str) -> bool:
        return step % 4 == 0 and any(item in SHOP_PRODUCTS.get(shop, ()) for shop in shops)

    def _market(self, obs: Mapping[str, Any], farm: Mapping[str, Any], goal: Mapping[str, Any],
                grid: list[list[Any]], units: list[Any], inventories: list[dict[str, Any]],
                verbs: list[list[Any]]) -> list[list[Any]]:
        step, day, hour = self._step(obs), int(obs.get("day", 0) or 0), int(obs.get("hour", 0) or 0)
        market = obs.get("market") or {}
        market_inventory = dict(market.get("inventory", {}) or {})
        prices = dict(market.get("prices", {}) or {})
        shops = [str(value) for value in list((obs.get("town") or {}).get("unlocked_shops", []) or [])]
        projected = self._projected_shed(self.resource_ledger.shed, inventories, verbs)
        purchases = self._purchase_plan(step, day, hour, farm, goal, grid, units,
                                        projected, market_inventory)
        feed_reserve = sum(int(value) for value in goal["animals"].values())
        reserve = int(self.params["cash_floor"]) + feed_reserve * int(prices.get("WHEAT", 25) or 25)
        self.cash_ledger.reserve = reserve
        money = int(farm.get("money", 0) or 0)
        planned_cost = sum(cost * (int(order[2]) if len(order) >= 3 else 1)
                           for _priority, order, cost in purchases[:9])
        financing = max(0, reserve + planned_cost - money)
        pressure = sum(projected.values()) >= int(self.params["capacity_pressure"])
        terminal = self._terminal(step, units)
        sale_orders: list[list[Any]] = []
        for item in sorted(PRODUCTS, key=lambda value: (-int(prices.get(value, BASE_PRICE[value]) or 1),
                                                       PRODUCTS.index(value))):
            operational = feed_reserve if item == "WHEAT" and not terminal else 0
            sellable = max(0, projected[item] - operational)
            if sellable <= 0:
                continue
            if terminal:
                state = "TERMINAL_LIQUIDATION"
                quantity = sellable
            elif financing > 0:
                state = "FINANCE_CAPEX"
                quote = max(1, market_price(item, int(market_inventory.get(item, 10000) or 10000)))
                quantity = min(sellable, math.ceil(financing / quote))
                financing -= quantity * quote
            elif pressure:
                state = "CAPACITY_RELIEF"
                quantity = min(sellable, 24)
            elif self._known_demand(step, shops, item):
                state = "HOLD_FOR_KNOWN_DEMAND"
                quantity = 0
            elif int(prices.get(item, BASE_PRICE[item]) or BASE_PRICE[item]) \
                    >= int(BASE_PRICE[item] * float(self.params["scarcity_ratio"])):
                state = "SCARCITY_RELEASE"
                quantity = min(sellable, 24)
            else:
                state = "OPERATING_RESERVE"
                quantity = 0
            self.sell_states[f"{item}:{state}"] += 1
            if quantity > 0:
                sale_orders.append(["SELL", item, int(quantity)])
                money += int(quantity) * int(prices.get(item, BASE_PRICE[item]) or 1)
                projected[item] -= int(quantity)
        orders = sale_orders[:10]
        for _priority, raw, unit_cost in purchases:
            if len(orders) >= 10:
                break
            quantity = int(raw[2]) if len(raw) >= 3 else 1
            affordable = max(0, (money - reserve) // max(1, unit_cost))
            if raw[0] in {"HIRE", "BUY_LAND"}:
                quantity = int(affordable >= 1)
            else:
                quantity = min(quantity, affordable)
            if quantity <= 0:
                self.audit["purchase_withheld"] += 1
                continue
            order = list(raw) if len(raw) < 3 else [raw[0], raw[1], int(quantity)]
            orders.append(order)
            money -= unit_cost * quantity
            item = str(raw[1]) if len(raw) >= 2 else None
            self.pending_receipts.append(PendingReceipt(step, str(raw[0]), item, quantity))
        self.cash_ledger.planned_spend = planned_cost
        return orders[:10]

    def act(self, obs: Mapping[str, Any]) -> dict[str, Any]:
        step = self._step(obs)
        day, hour = int(obs.get("day", step // 24) or 0), int(obs.get("hour", step % 24) or 0)
        seat = self._seat(obs)
        farms = list(obs.get("farms") or [{}, {}])
        farm = farms[seat] if seat < len(farms) else {}
        grid = list(farm.get("tiles", []) or [])
        private = dict(obs.get("private", {}) or {})
        inventories = list(private.get("inventories", []) or [])
        units = [farm.get("farmer")] + list(farm.get("hands", []) or [])
        while len(inventories) < len(units):
            inventories.append({})
        self._reconcile_receipts(step)
        self._reconcile_unit_intents(step, grid, units, inventories)
        self._day_rebind(day)
        self._route(obs, grid)
        goal = self._program_goal(day, obs)
        lands = max(1, len(farm.get("unlocked_quadrants", []) or []))
        self._ensure_layout(step, grid, goal, lands)
        self._refresh_tickets(step, day, hour, grid)
        self._sync_ledgers(farm, private, inventories)
        self._sync_actors(units, lands)
        self.resource_ledger.reserved_seeds.clear()
        seed_budget = Counter(self.resource_ledger.seeds)
        verbs: list[list[Any]] = []
        intents: dict[int, dict[str, Any]] = {}
        for index, unit in enumerate(units):
            if not unit:
                verbs.append(PASS.copy())
                continue
            position = (int(unit[0]), int(unit[1]))
            actor = self.actors[index]
            active = self.tickets.get(actor.active_ticket or "")
            if active and active.kind == "PLANT" and active.state not in {"COMPLETE", "CANCELLED"}:
                crop = str(active.verb[1])
                if seed_budget[crop] > 0:
                    seed_budget[crop] -= 1
                    self.resource_ledger.reserved_seeds[crop] += 1
                else:
                    active.owner = None
                    active.state = "WAIT_RESOURCE"
                    actor.active_ticket = None
            verb = self._advance_actor(actor, position, dict(inventories[index] or {}),
                                       seed_budget, step, units)
            verbs.append(verb)
            ticket = self.tickets.get(actor.active_ticket or "")
            if ticket and verb != PASS:
                intents[index] = {
                    "ticket_id": ticket.ticket_id, "verb": list(verb), "position": position,
                    "before_qty": int(dict(inventories[index] or {}).get(ticket.required_item, 0) or 0)
                                  if ticket.required_item else 0,
                    "distance": _dist(position, ticket.target),
                }
            self.audit[f"action_{verb[0].lower()}"] += 1
        self.pending_unit_intents = intents
        market_orders = self._market(obs, farm, goal, grid, units, inventories, verbs)
        self.last_step = step
        self.audit["calls"] += 1
        self.audit["max_live_tickets"] = max(self.audit["max_live_tickets"], sum(
            ticket.state not in {"COMPLETE", "CANCELLED"} for ticket in self.tickets.values()
        ))
        action = {"farmer": verbs[0] if verbs else PASS.copy(),
                  "hands": verbs[1:], "market": market_orders}
        self.last_action = action
        return action

    def diagnostics(self) -> dict[str, Any]:
        task_states = Counter(ticket.state for ticket in self.tickets.values())
        actor_states = {
            str(index): {"day": actor.day, "zone": actor.zone, "role": actor.role,
                         "active_ticket": actor.active_ticket}
            for index, actor in sorted(self.actors.items())
        }
        return {
            "schema": SCHEMA,
            "strategy_parent": STRATEGY_PARENT,
            "mode": self.mode,
            "expert": self.expert,
            "committed": self.committed,
            "commit_step": self.commit_step,
            "first_shop": self.first_shop,
            "phase": self.phase,
            "route_scores": dict(sorted(self.route_scores.items())),
            "layout_lease_count": len(self.leases),
            "layout_assets": dict(sorted(Counter(lease.asset for lease in self.leases.values()).items())),
            "task_states": dict(sorted(task_states.items())),
            "actors": actor_states,
            "resource_ledger": {
                "shed": dict(sorted(self.resource_ledger.shed.items())),
                "seeds": dict(sorted(self.resource_ledger.seeds.items())),
                "carried": dict(sorted(self.resource_ledger.carried.items())),
                "reserved_seeds": dict(sorted(self.resource_ledger.reserved_seeds.items())),
                "pending": dict(sorted(self.resource_ledger.pending.items())),
            },
            "cash_ledger": asdict(self.cash_ledger),
            "pending_receipts": [asdict(receipt) for receipt in self.pending_receipts],
            "sell_states": dict(sorted(self.sell_states.items())),
            "audit": dict(sorted(self.audit.items())),
        }


def build_executor(params: Mapping[str, Any] | None = None,
                   mode: str = "router") -> EnterpriseQueueExecutor:
    return EnterpriseQueueExecutor(DEFAULT_PARAMS if params is None else params, mode)


_EXECUTOR: EnterpriseQueueExecutor | None = None


def agent(obs: Mapping[str, Any]) -> dict[str, Any]:
    global _EXECUTOR
    if _EXECUTOR is None or int(obs.get("step", 0) or 0) == 0:
        _EXECUTOR = build_executor(DEFAULT_PARAMS, "router")
    return _EXECUTOR.act(obs)


__all__ = [
    "ActorState", "CashLedger", "DEFAULT_PARAMS", "EnterpriseQueueExecutor",
    "EXPERTS", "LayoutLease", "MODES", "PendingReceipt", "ResourceLedger",
    "SCHEMA", "STRATEGY_PARENT", "TASK_STATES", "TaskTicket", "agent",
    "build_executor", "canonical_hash", "market_price", "validate_params",
]
