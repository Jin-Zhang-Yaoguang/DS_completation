"""V117 合法观测的标准化 schema；禁止 seed、Replay 与未来信息进入运行时。"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


VERSION = "v117-r2.1-b113-cow-care-strawberry-fertilizer"
ENGINE_VERSION = "1.32.7"
PASS = ["PASS"]
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
SHED_TILES = ((4, 4), (5, 4), (4, 5), (5, 5))
LAND_PRICES = (1000, 2000, 4000)
SHED_CAPACITY = 100
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
BASE_PRICE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
              "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
CROP_FACTS = {
    "WHEAT": {"first": 2, "mature": 4, "max_yield": 6, "ongoing": False},
    "CARROT": {"first": 2, "mature": 3, "max_yield": 4, "ongoing": False},
    "TOMATO": {"first": 8, "mature": 8, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"first": 10, "mature": 10, "max_yield": 4, "ongoing": True},
    "MELON": {"first": 10, "mature": 12, "max_yield": 6, "ongoing": False},
}
SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"), "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"), "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "YARN_STORE": ("WOOL",),
}
UNIT_NO_ARG = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP", "WATER", "HARVEST",
               "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE"}


def integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def distance(left: tuple[int, int], right: tuple[int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def toward(source: tuple[int, int], target: tuple[int, int], actor: int = 0) -> list[str]:
    dx, dy = target[0] - source[0], target[1] - source[1]
    horizontal = abs(dx) > abs(dy) or (abs(dx) == abs(dy) and actor % 2 == 0)
    if horizontal and dx:
        return ["EAST" if dx > 0 else "WEST"]
    if dy:
        return ["SOUTH" if dy > 0 else "NORTH"]
    if dx:
        return ["EAST" if dx > 0 else "WEST"]
    return PASS.copy()


def path_toward(grid: Sequence[Sequence[Any]], source: tuple[int, int], target: tuple[int, int],
                actor: int = 0) -> list[str]:
    """在当前已解锁网格上返回确定性最短路第一步。"""
    if source == target:
        return PASS.copy()
    directions = (("EAST", 1, 0), ("SOUTH", 0, 1), ("WEST", -1, 0), ("NORTH", 0, -1))
    if actor % 2:
        directions = (("SOUTH", 0, 1), ("EAST", 1, 0), ("NORTH", 0, -1), ("WEST", -1, 0))
    queue = deque([(source, None)])
    visited = {source}
    while queue:
        (x, y), first = queue.popleft()
        for verb, dx, dy in directions:
            nx, ny = x + dx, y + dy
            pos = (nx, ny)
            if pos in visited or ny < 0 or ny >= len(grid) or nx < 0 or nx >= len(grid[ny]):
                continue
            if grid[ny][nx] == "LOCKED":
                continue
            next_first = first or verb
            if pos == target:
                return [next_first]
            visited.add(pos)
            queue.append((pos, next_first))
    return PASS.copy()


def shed_gate(position: tuple[int, int]) -> tuple[int, int]:
    return min(SHED_TILES, key=lambda tile: (distance(position, tile), tile))


def quadrant(position: tuple[int, int]) -> int:
    return (2 if position[1] >= 5 else 0) + (1 if position[0] >= 5 else 0)


def fib(index: int) -> int:
    left, right = 1, 1
    for _ in range(max(0, index)):
        left, right = right, left + right
    return left


def animal_kind(tile: Any) -> str | None:
    if not isinstance(tile, Mapping) or not tile.get("animal"):
        return None
    animal = tile["animal"]
    return str(animal.get("kind")) if isinstance(animal, Mapping) else str(animal)


def farm_counts(grid: Sequence[Sequence[Any]]) -> tuple[Counter[str], Counter[str], Counter[str]]:
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    structures: Counter[str] = Counter()
    for row in grid:
        for tile in row:
            if not isinstance(tile, Mapping):
                continue
            kind = str(tile.get("kind") or "")
            if kind == "PLANT" and tile.get("crop") in CROPS:
                crops[str(tile["crop"])] += 1
            if kind in {"COOP", "PASTURE"}:
                structures[kind] += 1
            animal = animal_kind(tile)
            if animal in ANIMALS:
                animals[animal] += 1
    return crops, animals, structures


def inventory_total(inventories: Sequence[Mapping[str, Any]]) -> Counter[str]:
    total: Counter[str] = Counter()
    for inventory in inventories:
        for item, quantity in dict(inventory or {}).items():
            total[str(item)] += max(0, integer(quantity))
    return total


@dataclass(frozen=True)
class PublicFarmState:
    money: int
    positions: tuple[tuple[int, int], ...]
    lands: int
    crops: Mapping[str, int]
    animals: Mapping[str, int]
    structures: Mapping[str, int]


@dataclass(frozen=True)
class CanonicalState:
    seat: int
    step: int
    day: int
    hour: int
    money: int
    grid: tuple[tuple[Any, ...], ...]
    positions: tuple[tuple[int, int], ...]
    inventories: tuple[dict[str, int], ...]
    shed: dict[str, int]
    seeds: dict[str, int]
    shops: tuple[str, ...]
    new_shops: tuple[str, ...]
    prices: dict[str, int]
    price_delta: dict[str, int]
    market_inventory: dict[str, int]
    market_inventory_delta: dict[str, int]
    lands: int
    hires_today: int
    crops: Mapping[str, int]
    animals: Mapping[str, int]
    structures: Mapping[str, int]
    opponent: PublicFarmState
    shed_used: int
    remaining_steps: int
    return_distance: int
    active_contract_id: str | None = None
    active_expert_id: str | None = None
    contract_age_days: int = 0
    actor_tasks: tuple[str | None, ...] = ()
    actor_roles: tuple[int, ...] = ()
    pending_orders: tuple[tuple[Any, ...], ...] = ()


def _public_farm(raw: Mapping[str, Any]) -> PublicFarmState:
    positions = [raw.get("farmer") or [4, 4], *list(raw.get("hands") or [])]
    normalized = tuple((integer(pos[0], 4), integer(pos[1], 4)) for pos in positions)
    grid = tuple(tuple(row) for row in list(raw.get("tiles") or []))
    crops, animals, structures = farm_counts(grid)
    return PublicFarmState(
        money=max(0, integer(raw.get("money"))),
        positions=normalized,
        lands=max(1, len(list(raw.get("unlocked_quadrants") or []))),
        crops=dict(crops), animals=dict(animals), structures=dict(structures),
    )


def canonicalize(observation: Mapping[str, Any], previous: CanonicalState | None = None,
                 runtime: Mapping[str, Any] | None = None) -> CanonicalState:
    """只从合法公开/本方私有观测构造状态；未知字段不猜测。"""

    seat = 1 if integer(observation.get("player")) == 1 else 0
    farms = list(observation.get("farms") or [{}, {}])
    while len(farms) < 2:
        farms.append({})
    farm = dict(farms[seat] or {})
    rival = dict(farms[1 - seat] or {})
    own_public = _public_farm(farm)
    private = dict(observation.get("private") or {})
    raw_inventories = [dict(value or {}) for value in list(private.get("inventories") or [])]
    while len(raw_inventories) < len(own_public.positions):
        raw_inventories.append({})
    inventories = tuple({str(k): max(0, integer(v)) for k, v in raw.items()}
                        for raw in raw_inventories[:len(own_public.positions)])
    market = dict(observation.get("market") or {})
    town = dict(observation.get("town") or {})
    step = integer(observation.get("step"), integer(observation.get("day")) * 24 + integer(observation.get("hour")))
    shops = tuple(str(value) for value in list(town.get("unlocked_shops") or []))
    prices = {str(k): max(1, integer(v, 1)) for k, v in dict(market.get("prices") or {}).items()}
    market_inventory = {str(k): integer(v, 10000) for k, v in dict(market.get("inventory") or {}).items()}
    valid_previous = previous if previous is not None and previous.seat == seat and previous.step < step else None
    price_delta = {item: prices.get(item, 0) - valid_previous.prices.get(item, prices.get(item, 0))
                   for item in PRODUCTS} if valid_previous else {item: 0 for item in PRODUCTS}
    inventory_delta = {
        item: market_inventory.get(item, 0) - valid_previous.market_inventory.get(item, market_inventory.get(item, 0))
        for item in PRODUCTS
    } if valid_previous else {item: 0 for item in PRODUCTS}
    runtime = dict(runtime or {})
    return CanonicalState(
        seat=seat, step=step, day=min(29, max(0, integer(observation.get("day")))),
        hour=max(0, integer(observation.get("hour"))), money=own_public.money,
        grid=tuple(tuple(row) for row in list(farm.get("tiles") or [])), positions=own_public.positions,
        inventories=inventories,
        shed={str(k): max(0, integer(v)) for k, v in dict(private.get("shed") or {}).items()},
        seeds={str(k): max(0, integer(v)) for k, v in dict(private.get("seeds") or {}).items()},
        shops=shops, new_shops=tuple(shop for shop in shops if valid_previous is None or shop not in valid_previous.shops),
        prices=prices, price_delta=price_delta, market_inventory=market_inventory,
        market_inventory_delta=inventory_delta, lands=own_public.lands,
        hires_today=max(0, integer(farm.get("hires_today"))), crops=own_public.crops,
        animals=own_public.animals, structures=own_public.structures, opponent=_public_farm(rival),
        shed_used=sum(max(0, integer(v)) for v in dict(private.get("shed") or {}).values()),
        remaining_steps=max(0, 719 - step),
        return_distance=max((distance(pos, shed_gate(pos)) for pos in own_public.positions), default=0),
        active_contract_id=runtime.get("active_contract_id"), active_expert_id=runtime.get("active_expert_id"),
        contract_age_days=max(0, integer(runtime.get("contract_age_days"))),
        actor_tasks=tuple(runtime.get("actor_tasks") or ()), actor_roles=tuple(runtime.get("actor_roles") or ()),
        pending_orders=tuple(tuple(order) for order in runtime.get("pending_orders") or ()),
    )
