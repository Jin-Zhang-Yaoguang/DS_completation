"""V32-specialist supply-flood poultry expert for V114 Iteration 10."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from event_program import PRODUCTS, TERMINAL_START_STEP, _tiles, observation_step
from policy_exposure_adaptive_poultry import (
    ExposureAdaptivePoultryPolicy,
    _projected_shed,
)


class SupplyFloodPoultryPolicy(ExposureAdaptivePoultryPolicy):
    """Share safe logistics while owning an independent adversarial market program."""

    name = "SUPPLY_FLOOD_POULTRY"

    def __init__(self) -> None:
        super().__init__(target_geese=12, worker_cap=14)

    def _crop_map(self, observation: Mapping[str, Any]) -> dict[tuple[int, int], str]:
        tiles = _tiles(observation)
        reserved = set(self.coop_targets(len(tiles) or 10))
        coordinates = sorted(
            (
                (x, y)
                for y, row in enumerate(tiles)
                for x, tile in enumerate(row)
                if tile != "LOCKED" and (x, y) not in reserved
            ),
            key=lambda xy: (xy[1], xy[0]),
        )
        cash_crop = self._select_cash_crop(observation)
        wheat_quota = int(math.ceil(len(coordinates) * 0.55))
        result: dict[tuple[int, int], str] = {}
        wheat_assigned = 0
        for index, coordinate in enumerate(coordinates):
            remaining = len(coordinates) - index
            need = wheat_quota - wheat_assigned
            choose_wheat = need > 0 and (index % 2 == 0 or need >= remaining)
            result[coordinate] = "WHEAT" if choose_wheat else cash_crop
            wheat_assigned += int(choose_wheat)
        return result

    def _market(
        self,
        observation: Mapping[str, Any],
        unit_actions: Sequence[Sequence[Any]],
        terminal: bool,
    ) -> tuple[list[list[Any]], dict[str, Any]]:
        sale_units_before = dict(self.sale_units)
        previous_sales_before = dict(self.previous_own_sales)
        base_orders, audit = super()._market(observation, unit_actions, terminal)
        self.sale_units = sale_units_before
        self.previous_own_sales = previous_sales_before
        procurement = [order for order in base_orders if not order or order[0] != "SELL"]
        projected = _projected_shed(observation, unit_actions)
        geese = self._placed_geese(observation)
        feed_reserve = min(projected.get("WHEAT", 0), max(24, geese * 2))
        sells: list[list[Any]] = []
        for product in ("FERTILIZER", "WHEAT", "MELON", "CARROT", "TOMATO"):
            quantity = projected.get(product, 0)
            if product == "WHEAT" and not terminal:
                quantity -= feed_reserve
            if quantity > 0:
                sells.append(["SELL", product, quantity])
        if terminal or observation_step(observation) % 4 == 1:
            for product in ("EGG", "MILK", "WOOL", "STRAWBERRY"):
                quantity = projected.get(product, 0)
                if quantity > 0:
                    sells.append(["SELL", product, quantity])
        orders = (sells + procurement)[:10]
        for order in orders:
            if len(order) >= 3 and order[0] == "SELL" and order[1] in PRODUCTS:
                product, quantity = str(order[1]), int(order[2])
                self.sale_units[product] += quantity
                self.previous_own_sales[product] += quantity
        audit = dict(audit)
        audit.update({
            "market_role": "SUPPLY_FLOOD",
            "feed_reserve": feed_reserve,
            "actual_sells": sells,
        })
        return orders, audit


__all__ = ["SupplyFloodPoultryPolicy"]
