"""Small, auditable residuals used by the V10 complete-agent variants.

These functions never invent a production route.  They either reduce an
existing SELL quantity or reorder existing market orders without changing the
set or total quantity of goods sold.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping


ANIMAL_HALF_TOPDAYS = (10, 17, 24)
ANIMAL_PRODUCTS = frozenset({"EGG", "MILK", "WOOL"})
PREMIUM_PRODUCTS = frozenset({"STRAWBERRY", "MELON", "MILK", "WOOL"})
BASE_PRICES = {
    "WHEAT": 25.0,
    "CARROT": 35.0,
    "TOMATO": 60.0,
    "STRAWBERRY": 120.0,
    "MELON": 250.0,
    "EGG": 50.0,
    "MILK": 160.0,
    "WOOL": 200.0,
    "FERTILIZER": 100.0,
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def copy_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    """Return the canonical mutable Kaggriculture action structure."""
    source = copy.deepcopy(action or {})
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (source.get("hands") or [])],
        "market": [list(order) for order in (source.get("market") or [])],
    }


def observation_day(obs: Any) -> int:
    day = _get(obs, "day")
    if day is not None:
        return int(day or 0)
    return int(_get(obs, "step", 0) or 0) // 24


def animal_half_topdays(action: Mapping[str, Any], obs: Any) -> dict[str, list[Any]]:
    """Halve existing animal-product SELLs only on audited days 10/17/24.

    The schedule comes from the prior D1 counterfactual audit.  Zero-quantity
    orders are removed because the official parser treats them as malformed.
    """
    result = copy_action(action)
    if observation_day(obs) not in ANIMAL_HALF_TOPDAYS:
        return result
    market = []
    for raw in result["market"]:
        order = list(raw)
        if len(order) >= 3 and order[0] == "SELL" and str(order[1]) in ANIMAL_PRODUCTS:
            quantity = max(0, int(order[2] or 0))
            order[2] = max(0, int(round(quantity * 0.5)))
            if order[2] <= 0:
                continue
        market.append(order)
    result["market"] = market[:10]
    return result


def premium_price_slot(action: Mapping[str, Any], obs: Any) -> dict[str, list[Any]]:
    """Use earlier SELL slots for premium goods with the best live price ratio.

    Only the contents of already-existing SELL slots are permuted.  Non-SELL
    orders keep their indices and every SELL keeps its quantity, so this is a
    market-timing residual rather than a hidden production route.
    """
    result = copy_action(action)
    market = result["market"]
    indices = [
        index
        for index, order in enumerate(market)
        if len(order) >= 3 and order[0] == "SELL" and int(order[2] or 0) > 0
    ]
    if len(indices) < 2:
        return result
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    ranked = [(index, list(market[index])) for index in indices]
    ranked.sort(
        key=lambda row: (
            str(row[1][1]) in PREMIUM_PRODUCTS,
            float(_get(prices, str(row[1][1]), 0) or 0)
            / BASE_PRICES.get(str(row[1][1]), 1.0),
            -row[0],
        ),
        reverse=True,
    )
    for index, (_, order) in zip(indices, ranked):
        market[index] = order
    result["market"] = market[:10]
    return result


TRANSFORMS = {
    "animal_half_topdays": animal_half_topdays,
    "premium_price_slot": premium_price_slot,
}


def apply_transforms(
    action: Mapping[str, Any],
    obs: Any,
    names: tuple[str, ...],
) -> dict[str, list[Any]]:
    result = copy_action(action)
    for name in names:
        try:
            transform = TRANSFORMS[name]
        except KeyError as exc:
            raise ValueError(f"unknown action transform: {name}") from exc
        result = transform(result, obs)
    return result
