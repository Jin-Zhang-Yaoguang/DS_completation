"""Replay-free product-level market controller for V116.

The module is deliberately pure: no episode memory, parent agent, replay,
per-step action table or hidden source state is read.  The planner consumes the
current observation, the shed after this turn's unit actions, one daily target,
and item reserves.

Kaggriculture 1.32.7 resolves a turn as unit actions -> market -> town demand.
Market orders are processed by slot and every unit receives a fresh quote.
Those two facts are the contract implemented below.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping, Sequence


PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
BUYABLE_PRODUCTS = ("WHEAT", "FERTILIZER")

PRICE_FLOOR = 1
MARKET_I0 = 10000
HINGE_GAIN = 8.0
MARKET_PARAMS = {
    "WHEAT":      (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT":     (35, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO":     (60, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON":      (250, 300, "log", 0.20, "sq", 3.60),
    "EGG":        (50, 332, "hinge", 0.40, "log", 0.20),
    "MILK":       (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL":       (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND_PRICES = (1000, 2000, 4000)

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


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError, OverflowError):
        return 0


def _int_or(value: Any, default: int) -> int:
    """Parse an integer without treating a legitimate zero as missing."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


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
    if name == "log10":
        return math.log10(1.0 + value)
    if name == "hinge":
        unit = value / target if target > 0 else value
        return unit + HINGE_GAIN * max(0.0, unit - 1.0) ** 2
    return value


def market_price(item: str, inventory: int) -> int:
    """Return the exact engine unit price for one product and inventory."""
    base, target, below_name, below_target, above_name, above_target = MARKET_PARAMS[item]
    if inventory < MARKET_I0:
        amplitude = below_target * base / _shape(below_name, target, target)
        value = base + amplitude * _shape(below_name, MARKET_I0 - inventory, target)
    else:
        amplitude = above_target * base / _shape(above_name, target, target)
        value = base - amplitude * _shape(above_name, inventory - MARKET_I0, target)
    # Python's round is half-to-even, matching the competition engine.
    return max(PRICE_FLOOR, int(round(value)))


def fibonacci_hire_cost(hires_today: int) -> int:
    """Cost of the next hire: 1, 1, 2, 3, 5, ..."""
    left, right = 1, 1
    for _ in range(_nonnegative_int(hires_today)):
        left, right = right, left + right
    return left


def _seat(observation: Any) -> int:
    return 1 if _nonnegative_int(_get(observation, "player", 0)) == 1 else 0


def _farm(observation: Any) -> Mapping[str, Any]:
    farms = list(_get(observation, "farms", []) or [])
    seat = _seat(observation)
    return farms[seat] if seat < len(farms) else {}


def _private(observation: Any) -> Mapping[str, Any]:
    return _get(observation, "private", {}) or {}


def _counts(source: Mapping[str, Any] | None, names: Iterable[str]) -> dict[str, int]:
    source = source or {}
    return {name: _nonnegative_int(_get(source, name, 0)) for name in names}


def _step(observation: Any, turns_per_day: int = 24) -> int:
    raw = _get(observation, "step", None)
    if raw is not None:
        return _nonnegative_int(raw)
    return _nonnegative_int(_get(observation, "day", 0)) * turns_per_day + _nonnegative_int(
        _get(observation, "hour", 0)
    )


def town_demand_after_market(
    observation: Any,
    *,
    shop_interval: int = 4,
    center_interval: int = 24,
) -> dict[str, int]:
    """Known demand applied *after* this turn's market queue.

    Shop instances are intentionally not deduplicated.  PET_CAFE and
    YARN_STORE are single-product shops and therefore consume two units.
    """
    demand = {item: 0 for item in PRODUCTS}
    step = _step(observation)
    if shop_interval > 0 and step % shop_interval == 0:
        town = _get(observation, "town", {}) or {}
        for raw_name in list(_get(town, "unlocked_shops", []) or []):
            products = SHOP_PRODUCTS.get(str(raw_name), ())
            multiplier = 2 if len(products) == 1 else 1
            for item in products:
                demand[item] += multiplier
    if center_interval > 0 and step % center_interval == 0:
        for item in PRODUCTS:
            if item != "FERTILIZER":
                demand[item] += 1
    return demand


@dataclass(frozen=True)
class ControllerPolicy:
    """Small, auditable policy surface.

    ``opponent_stress_units`` is the valuation haircut used for ordinary
    selling.  ``finance_stress_units`` is deliberately much stricter because
    a later purchase must not depend on optimistic SELL proceeds.
    """

    max_orders: int = 10
    shed_capacity: int = 100
    cash_buffer: int = 100
    opponent_stress_units: int = 12
    finance_stress_units: int = 100
    sale_floor_ratio: float = 0.25
    max_regular_sale_per_item: int = 24
    pressure_threshold: int = 88
    episode_steps: int = 720
    liquidation_start_step: int = 696
    turns_per_day: int = 24
    shop_interval: int = 4
    center_interval: int = 24
    max_units: int = 40


@dataclass(frozen=True)
class Ledger:
    money: int
    shed: dict[str, int]
    seeds: dict[str, int]
    market_inventory: dict[str, int]
    hands: int
    hires_today: int
    quadrants: int
    executed_orders: tuple[tuple[Any, ...], ...]


def simulate_own_orders(
    observation: Any,
    projected_shed: Mapping[str, Any],
    orders: Sequence[Sequence[Any]],
    *,
    opponent_stress_units: int = 0,
    shed_capacity: int = 100,
    cash_floor: int = 0,
    max_orders: int = 10,
    max_units: int = 40,
) -> Ledger:
    """Conservatively execute our queue with exact per-unit quotes.

    With ``opponent_stress_units=100``, SELL quotes assume that the opponent's
    full shed reached the same product first, while BUY_PRODUCT quotes assume
    that the opponent bought 100 units first.  Applying the full stress to
    every product is intentionally pessimistic, but makes fixed-price spending
    financed by prior SELL orders safe against any single legal opponent shed.
    The returned market inventory tracks only our own actions.
    """
    farm = _farm(observation)
    private = _private(observation)
    market = _get(observation, "market", {}) or {}
    money = _nonnegative_int(_get(farm, "money", 0))
    shed = _counts(projected_shed, (*PRODUCTS, *ANIMALS))
    seeds = _counts(_get(private, "seeds", {}) or {}, CROPS)
    inventory = {
        item: _int_or(_get(_get(market, "inventory", {}) or {}, item, MARKET_I0), MARKET_I0)
        for item in PRODUCTS
    }
    hands = len(list(_get(farm, "hands", []) or []))
    hires_today = _nonnegative_int(_get(farm, "hires_today", hands))
    quadrants = max(1, len(list(_get(farm, "unlocked_quadrants", []) or [])))
    stress = _nonnegative_int(opponent_stress_units)
    floor = _nonnegative_int(cash_floor)
    capacity = max(1, _nonnegative_int(shed_capacity))
    executed: list[tuple[Any, ...]] = []

    for raw in list(orders or [])[:max(0, int(max_orders))]:
        order = list(raw or [])
        if not order:
            continue
        operation = str(order[0])
        requested = _nonnegative_int(order[2]) if len(order) >= 3 else 1

        if operation == "SELL" and len(order) >= 3 and str(order[1]) in PRODUCTS:
            item = str(order[1])
            done = 0
            for _ in range(min(requested, shed[item])):
                quote = market_price(item, inventory[item] + stress)
                shed[item] -= 1
                money += quote
                if quote > PRICE_FLOOR:
                    inventory[item] += 1
                done += 1
            if done:
                executed.append(("SELL", item, done))
            continue

        if operation == "HIRE":
            cost = fibonacci_hire_cost(hires_today)
            if hands + 1 < max_units and money - cost >= floor:
                money -= cost
                hands += 1
                hires_today += 1
                executed.append(("HIRE",))
            continue

        if operation == "BUY_LAND":
            if quadrants <= len(LAND_PRICES):
                cost = LAND_PRICES[quadrants - 1]
                if money - cost >= floor:
                    money -= cost
                    quadrants += 1
                    executed.append(("BUY_LAND",))
            continue

        if operation == "BUY_SEED" and len(order) >= 3 and str(order[1]) in SEED_COST:
            item = str(order[1])
            done = 0
            for _ in range(requested):
                cost = SEED_COST[item]
                if money - cost < floor:
                    break
                money -= cost
                seeds[item] += 1
                done += 1
            if done:
                executed.append(("BUY_SEED", item, done))
            continue

        if operation == "BUY_ANIMAL" and len(order) >= 3 and str(order[1]) in ANIMAL_COST:
            item = str(order[1])
            done = 0
            for _ in range(requested):
                cost = ANIMAL_COST[item]
                if money - cost < floor or sum(shed.values()) >= capacity:
                    break
                money -= cost
                shed[item] += 1
                done += 1
            if done:
                executed.append(("BUY_ANIMAL", item, done))
            continue

        if operation == "BUY_PRODUCT" and len(order) >= 3 and str(order[1]) in BUYABLE_PRODUCTS:
            item = str(order[1])
            done = 0
            for _ in range(requested):
                # Engine quotes a buy at post-buy inventory.
                quote = market_price(item, inventory[item] - stress - 1)
                if money - quote < floor or sum(shed.values()) >= capacity:
                    break
                money -= quote
                shed[item] += 1
                inventory[item] -= 1
                done += 1
            if done:
                executed.append(("BUY_PRODUCT", item, done))

    return Ledger(
        money=money,
        shed=shed,
        seeds=seeds,
        market_inventory=inventory,
        hands=hands,
        hires_today=hires_today,
        quadrants=quadrants,
        executed_orders=tuple(executed),
    )


def _installed_animals(observation: Any) -> dict[str, int]:
    totals = {animal: 0 for animal in ANIMALS}
    for row in list(_get(_farm(observation), "tiles", []) or []):
        for tile in list(row or []):
            if isinstance(tile, Mapping):
                animal = str(tile.get("animal", ""))
                if animal in totals:
                    totals[animal] += 1
    return totals


def _target_map(target: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    for key in keys:
        value = _get(target, key, None)
        if isinstance(value, Mapping):
            return value
    return {}


def _purchase_blueprint(
    observation: Any,
    projected_shed: Mapping[str, Any],
    daily_target: Mapping[str, Any],
    reserves: Mapping[str, Any],
    policy: ControllerPolicy,
) -> list[list[Any]]:
    """Generate target gaps before cash and slot constraints are applied."""
    farm = _farm(observation)
    private = _private(observation)
    shed = _counts(projected_shed, (*PRODUCTS, *ANIMALS))
    installed = _installed_animals(observation)
    current_seeds = _counts(_get(private, "seeds", {}) or {}, CROPS)
    target_seeds = _target_map(daily_target, "seed_targets", "seeds")
    target_animals = _target_map(daily_target, "animal_targets", "animals")
    target_products = _target_map(daily_target, "product_targets", "products", "inputs")

    intents: list[tuple[int, list[Any]]] = []

    desired_hands = min(
        policy.max_units - 1,
        _nonnegative_int(_get(daily_target, "max_hands", _get(daily_target, "hands", 0))),
    )
    current_hands = len(list(_get(farm, "hands", []) or []))
    for _ in range(max(0, desired_hands - current_hands)):
        intents.append((92, ["HIRE"]))

    # Feed/fertilizer inputs are immediate operational dependencies.
    for item in BUYABLE_PRODUCTS:
        desired = max(
            _nonnegative_int(_get(target_products, item, 0)),
            _nonnegative_int(_get(reserves, item, 0)),
        )
        missing = max(0, desired - shed[item])
        if missing:
            intents.append((100, ["BUY_PRODUCT", item, missing]))

    # Animals already installed or waiting in the shed both satisfy the target.
    for item in ANIMALS:
        desired = _nonnegative_int(_get(target_animals, item, 0))
        missing = max(0, desired - installed[item] - shed[item])
        if missing:
            intents.append((88, ["BUY_ANIMAL", item, missing]))

    for item in CROPS:
        desired = _nonnegative_int(_get(target_seeds, item, 0))
        missing = max(0, desired - current_seeds[item])
        if missing:
            intents.append((80, ["BUY_SEED", item, missing]))

    desired_quadrants = min(4, max(1, _nonnegative_int(_get(daily_target, "quadrants", 1))))
    current_quadrants = max(1, len(list(_get(farm, "unlocked_quadrants", []) or [])))
    for _ in range(max(0, desired_quadrants - current_quadrants)):
        intents.append((70, ["BUY_LAND"]))

    # Python sort is stable, so same-priority target order remains deterministic.
    intents.sort(key=lambda entry: -entry[0])
    return [order for _, order in intents]


def _rough_purchase_cost(
    observation: Any,
    purchases: Sequence[Sequence[Any]],
    policy: ControllerPolicy,
) -> int:
    """Upper-bound selected purchases under the conservative quote model."""
    farm = _farm(observation)
    inventory = _get(_get(observation, "market", {}) or {}, "inventory", {}) or {}
    hires = _nonnegative_int(_get(farm, "hires_today", 0))
    quadrants = max(1, len(list(_get(farm, "unlocked_quadrants", []) or [])))
    cost = 0
    for raw in purchases:
        operation = str(raw[0])
        quantity = _nonnegative_int(raw[2]) if len(raw) >= 3 else 1
        if operation == "HIRE":
            cost += fibonacci_hire_cost(hires)
            hires += 1
        elif operation == "BUY_LAND" and quadrants <= len(LAND_PRICES):
            cost += LAND_PRICES[quadrants - 1]
            quadrants += 1
        elif operation == "BUY_SEED":
            cost += SEED_COST.get(str(raw[1]), 0) * quantity
        elif operation == "BUY_ANIMAL":
            cost += ANIMAL_COST.get(str(raw[1]), 0) * quantity
        elif operation == "BUY_PRODUCT" and str(raw[1]) in BUYABLE_PRODUCTS:
            item = str(raw[1])
            market_level = _int_or(_get(inventory, item, MARKET_I0), MARKET_I0)
            for offset in range(quantity):
                cost += market_price(item, market_level - policy.finance_stress_units - offset - 1)
    return cost


def _sale_quantities(
    observation: Any,
    projected_shed: Mapping[str, Any],
    reserves: Mapping[str, Any],
    cash_needed: int,
    policy: ControllerPolicy,
) -> dict[str, int]:
    """Choose financing first, then price-safe surplus liquidation."""
    shed = _counts(projected_shed, PRODUCTS)
    reserve = _counts(reserves, PRODUCTS)
    available = {item: max(0, shed[item] - reserve[item]) for item in PRODUCTS}
    inventory = {
        item: _int_or(
            _get(_get(_get(observation, "market", {}) or {}, "inventory", {}) or {}, item, MARKET_I0),
            MARKET_I0,
        )
        for item in PRODUCTS
    }
    selected = {item: 0 for item in PRODUCTS}
    remaining_need = max(0, int(cash_needed))

    # Financing is unit-greedy across products.  Quotes include the full
    # opponent stress; selected units update our own market state one by one.
    while remaining_need > 0:
        candidates: list[tuple[int, str]] = []
        for item in PRODUCTS:
            if selected[item] >= available[item]:
                continue
            quote = market_price(
                item,
                inventory[item] + policy.finance_stress_units + selected[item],
            )
            candidates.append((quote, item))
        if not candidates:
            break
        quote, item = max(candidates, key=lambda value: (value[0], -PRODUCTS.index(value[1])))
        selected[item] += 1
        remaining_need -= quote

    pressure = sum(shed.values()) >= policy.pressure_threshold
    demand = town_demand_after_market(
        observation,
        shop_interval=policy.shop_interval,
        center_interval=policy.center_interval,
    )
    for item in PRODUCTS:
        left = available[item] - selected[item]
        if left <= 0:
            continue
        # The visible demand tick happens after our queue.  Unless cash or
        # capacity is urgent, wait one turn and sell into the restored price.
        if demand[item] > 0 and not pressure:
            continue
        regular_cap = min(left, policy.max_regular_sale_per_item)
        for _ in range(regular_cap):
            own_offset = selected[item]
            quote = market_price(item, inventory[item] + policy.opponent_stress_units + own_offset)
            base = MARKET_PARAMS[item][0]
            if not pressure and quote < max(PRICE_FLOOR, int(base * policy.sale_floor_ratio)):
                break
            selected[item] += 1

    return {item: quantity for item, quantity in selected.items() if quantity > 0}


def _sale_order_key(
    observation: Any,
    item: str,
    policy: ControllerPolicy,
) -> tuple[int, int]:
    inventory = _int_or(
        _get(_get(_get(observation, "market", {}) or {}, "inventory", {}) or {}, item, MARKET_I0),
        MARKET_I0,
    )
    return (-market_price(item, inventory + policy.opponent_stress_units), PRODUCTS.index(item))


def market_orders(
    observation: Any,
    projected_shed: Mapping[str, Any],
    daily_target: Mapping[str, Any] | None,
    reserves: Mapping[str, Any] | None,
    *,
    policy: ControllerPolicy | None = None,
) -> list[list[Any]]:
    """Return at most ten executable market orders.

    This is the integration interface intended for V116's labor planner.  Its
    caller should compute ``projected_shed`` from same-turn DROP/PICKUP actions;
    using the observation shed instead would violate the engine phase order.
    """
    policy = policy or ControllerPolicy()
    daily_target = daily_target or {}
    reserves = reserves or {}
    projected = _counts(projected_shed, (*PRODUCTS, *ANIMALS))
    step = _step(observation, policy.turns_per_day)
    liquidation = step >= min(policy.liquidation_start_step, policy.episode_steps - 2)

    if liquidation:
        raw = [["SELL", item, projected[item]] for item in PRODUCTS if projected[item] > 0]
        ledger = simulate_own_orders(
            observation,
            projected,
            raw,
            opponent_stress_units=policy.finance_stress_units,
            shed_capacity=policy.shed_capacity,
            cash_floor=0,
            max_orders=policy.max_orders,
            max_units=policy.max_units,
        )
        return [list(order) for order in ledger.executed_orders]

    purchases = _purchase_blueprint(observation, projected, daily_target, reserves, policy)
    # Keep one slot for financing if there is anything legal to sell.
    has_saleable = any(projected[item] > _nonnegative_int(_get(reserves, item, 0)) for item in PRODUCTS)
    purchase_limit = max(0, policy.max_orders - int(has_saleable))
    selected_purchases = purchases[:purchase_limit]
    current_money = _nonnegative_int(_get(_farm(observation), "money", 0))
    cash_needed = max(
        0,
        _rough_purchase_cost(observation, selected_purchases, policy) + policy.cash_buffer - current_money,
    )
    quantities = _sale_quantities(observation, projected, reserves, cash_needed, policy)
    sales = [
        ["SELL", item, quantities[item]]
        for item in sorted(quantities, key=lambda value: _sale_order_key(observation, value, policy))
    ]

    # If ordinary liquidation uses several products, preserve target actions by
    # dropping the least valuable sale orders first.  Financing sales stay at
    # the front and every dependent spend therefore sees their cash.
    allowed_sales = max(0, policy.max_orders - len(selected_purchases))
    sales = sales[:allowed_sales]
    queue = [*sales, *selected_purchases]
    ledger = simulate_own_orders(
        observation,
        projected,
        queue,
        opponent_stress_units=policy.finance_stress_units,
        shed_capacity=policy.shed_capacity,
        cash_floor=policy.cash_buffer,
        max_orders=policy.max_orders,
        max_units=policy.max_units,
    )
    return [list(order) for order in ledger.executed_orders]


__all__ = [
    "ControllerPolicy",
    "Ledger",
    "market_orders",
    "market_price",
    "simulate_own_orders",
    "town_demand_after_market",
]
