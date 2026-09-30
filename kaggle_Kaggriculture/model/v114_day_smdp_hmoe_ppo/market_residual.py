"""Canonical, target-product-only market residual action contract."""

from __future__ import annotations

from enum import IntEnum
import math
from typing import Any, Mapping, Sequence

from event_program import TERMINAL_START_STEP, observation_step


SHOPS: dict[str, tuple[str, ...]] = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}


class MarketResidualAction(IntEnum):
    KEEP_BASE = 0
    SKIP_EVENT = 1
    HALF_FRONT = 2
    HALF_BACK = 3
    ALL_BACK = 4


def scheduled_demand_quantity(
    observation: Mapping[str, Any], product: str, *, previous_step: bool = True
) -> int:
    """Return public scheduled town demand for a product at one visible step."""

    step = observation_step(observation) - int(bool(previous_step))
    if step < 0:
        return 0
    quantity = int(step % 24 == 0 and product != "FERTILIZER")
    if step % 4 != 0:
        return quantity
    town = observation.get("town", {}) or {}
    for shop_name in town.get("unlocked_shops", []) or []:
        products = SHOPS.get(str(shop_name), ())
        if product in products:
            quantity += 2 if len(products) == 1 else 1
    return quantity


def canonical_action_mask(
    *, available: int, base_market_queue: Sequence[Sequence[Any]], step: int
) -> tuple[bool, ...]:
    """Mask equivalent or unsafe actions before categorical sampling."""

    available = max(0, int(available))
    base_length = len(base_market_queue)
    if available <= 0:
        return (False,) * len(MarketResidualAction)
    if int(step) >= TERMINAL_START_STEP:
        return (base_length < 10, False, False, False, False)
    room = base_length < 10
    distinct_half = int(math.ceil(available * 0.5)) < available
    distinct_back = room and base_length > 0
    return (
        room,
        True,
        room and distinct_half,
        distinct_back and distinct_half,
        distinct_back,
    )


def apply_market_residual(
    *,
    base_market_queue: Sequence[Sequence[Any]],
    product: str,
    available: int,
    action: MarketResidualAction | int,
) -> list[list[Any]]:
    """Generate a queue while changing only the target-product SELL order."""

    parsed = MarketResidualAction(int(action))
    market = [
        list(order)
        for order in base_market_queue
        if not (
            order
            and len(order) >= 2
            and str(order[0]) == "SELL"
            and str(order[1]) == str(product)
        )
    ]
    if parsed is MarketResidualAction.SKIP_EVENT:
        return market
    quantity = max(0, int(available))
    if parsed in (MarketResidualAction.HALF_FRONT, MarketResidualAction.HALF_BACK):
        quantity = int(math.ceil(quantity * 0.5))
    if quantity <= 0 or len(market) >= 10:
        return market
    order = ["SELL", str(product), quantity]
    if parsed in (MarketResidualAction.KEEP_BASE, MarketResidualAction.HALF_FRONT):
        return [order, *market]
    return [*market, order]


def abstaining_action(
    probabilities: Sequence[float],
    q_gain_vs_keep: Sequence[float],
    mask: Sequence[bool],
    *,
    probability_min: float = 0.60,
    top_ratio_min: float = 2.0,
) -> MarketResidualAction:
    """Serve a residual only with probability and value separation from KEEP."""

    if not (len(probabilities) == len(q_gain_vs_keep) == len(mask) == len(MarketResidualAction)):
        raise ValueError("probabilities, q gains and mask must cover all actions")
    valid = [index for index, enabled in enumerate(mask) if enabled]
    if not valid or not mask[MarketResidualAction.KEEP_BASE]:
        return MarketResidualAction.KEEP_BASE
    non_keep = [index for index in valid if index != MarketResidualAction.KEEP_BASE]
    if not non_keep:
        return MarketResidualAction.KEEP_BASE
    ranked = sorted(non_keep, key=lambda index: float(probabilities[index]), reverse=True)
    best = ranked[0]
    second_probability = max(
        [float(probabilities[MarketResidualAction.KEEP_BASE])]
        + [float(probabilities[index]) for index in ranked[1:]]
    )
    best_probability = float(probabilities[best])
    ratio = best_probability / max(second_probability, 1e-12)
    if (
        best_probability < float(probability_min)
        or ratio < float(top_ratio_min)
        or float(q_gain_vs_keep[best]) <= 0.0
    ):
        return MarketResidualAction.KEEP_BASE
    return MarketResidualAction(best)


__all__ = [
    "MarketResidualAction",
    "SHOPS",
    "abstaining_action",
    "apply_market_residual",
    "canonical_action_mask",
    "scheduled_demand_quantity",
]
