"""Mechanism tests for the replay-free V116 product market controller."""

from __future__ import annotations

import unittest

from market_controller import (
    ControllerPolicy,
    market_orders,
    market_price,
    simulate_own_orders,
    town_demand_after_market,
)


PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)


def observation(
    *,
    step: int = 1,
    money: int = 3000,
    hands: int = 0,
    hires_today: int | None = None,
    quadrants: int = 1,
    shed: dict[str, int] | None = None,
    inventory: dict[str, int] | None = None,
    shops: list[str] | None = None,
) -> dict:
    day, hour = divmod(step, 24)
    market_inventory = {item: 10000 for item in PRODUCTS}
    market_inventory.update(inventory or {})
    private_shed = {item: 0 for item in PRODUCTS}
    private_shed.update({"GOOSE": 0, "COW": 0, "SHEEP": 0})
    private_shed.update(shed or {})
    farm = {
        "money": money,
        "farmer": [4, 4],
        "hands": [[4, 4] for _ in range(hands)],
        "hires_today": hands if hires_today is None else hires_today,
        "unlocked_quadrants": ["NW", "NE", "SW", "SE"][:quadrants],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }
    return {
        "step": step,
        "day": day,
        "hour": hour,
        "player": 0,
        "farms": [farm, dict(farm)],
        "private": {
            "shed": private_shed,
            "seeds": {crop: 0 for crop in PRODUCTS[:5]},
            "inventories": [{} for _ in range(hands + 1)],
        },
        "market": {
            "inventory": market_inventory,
            "prices": {item: market_price(item, value) for item, value in market_inventory.items()},
        },
        "town": {"unlocked_shops": list(shops or [])},
    }


class PriceAndLedgerTests(unittest.TestCase):
    def test_price_matches_engine_examples(self) -> None:
        self.assertEqual(market_price("WHEAT", 10000), 25)
        self.assertEqual(market_price("WHEAT", 9995), 27)
        self.assertEqual(market_price("MELON", 9999), 256)

    def test_sell_and_buy_product_are_priced_per_unit(self) -> None:
        obs = observation(money=100, shed={"WHEAT": 3})
        ledger = simulate_own_orders(
            obs,
            {"WHEAT": 3},
            [["SELL", "WHEAT", 2], ["BUY_PRODUCT", "WHEAT", 1]],
            opponent_stress_units=0,
        )
        expected_sale = market_price("WHEAT", 10000) + market_price("WHEAT", 10001)
        expected_buy = market_price("WHEAT", 10001)
        self.assertEqual(ledger.money, 100 + expected_sale - expected_buy)
        self.assertEqual(ledger.shed["WHEAT"], 2)
        self.assertEqual(ledger.market_inventory["WHEAT"], 10001)

    def test_zero_market_inventory_is_not_misread_as_missing(self) -> None:
        obs = observation(money=100000, inventory={"WHEAT": 0})
        ledger = simulate_own_orders(
            obs,
            {},
            [["BUY_PRODUCT", "WHEAT", 1]],
            opponent_stress_units=0,
        )
        self.assertEqual(ledger.market_inventory["WHEAT"], -1)
        self.assertEqual(ledger.money, 100000 - market_price("WHEAT", -1))

    def test_one_coin_sale_does_not_add_market_supply(self) -> None:
        obs = observation(money=0, shed={"STRAWBERRY": 2}, inventory={"STRAWBERRY": 10100})
        ledger = simulate_own_orders(
            obs,
            {"STRAWBERRY": 2},
            [["SELL", "STRAWBERRY", 2]],
            opponent_stress_units=0,
        )
        self.assertEqual(ledger.money, 2)
        self.assertEqual(ledger.market_inventory["STRAWBERRY"], 10100)

    def test_fixed_costs_use_fibonacci_hire_and_land_cashbook(self) -> None:
        obs = observation(money=1010, hands=2, hires_today=2)
        ledger = simulate_own_orders(
            obs,
            {},
            [["HIRE"], ["HIRE"], ["BUY_LAND"]],
            opponent_stress_units=0,
        )
        # Third and fourth hires cost 2 and 3; first land unlock costs 1000.
        self.assertEqual(ledger.money, 5)
        self.assertEqual(ledger.hands, 4)
        self.assertEqual(ledger.quadrants, 2)


class ControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        # No opponent stress in policy-behaviour tests; the conservative ledger
        # itself is tested separately and production defaults remain stricter.
        self.policy = ControllerPolicy(
            opponent_stress_units=0,
            finance_stress_units=0,
            cash_buffer=0,
        )

    def test_uses_projected_shed_and_sell_finances_later_seed_buy(self) -> None:
        obs = observation(money=0, shed={"WHEAT": 0})
        orders = market_orders(
            obs,
            {"WHEAT": 2},
            {"seeds": {"WHEAT": 2}},
            {},
            policy=self.policy,
        )
        self.assertEqual(orders[0][0], "SELL")
        self.assertIn(["BUY_SEED", "WHEAT", 2], orders)
        self.assertLess(
            next(i for i, order in enumerate(orders) if order[0] == "SELL"),
            next(i for i, order in enumerate(orders) if order[0] == "BUY_SEED"),
        )

    def test_reserve_is_never_sold_outside_terminal(self) -> None:
        obs = observation(step=5, shed={"WOOL": 9})
        orders = market_orders(obs, {"WOOL": 9}, {}, {"WOOL": 6}, policy=self.policy)
        sold = sum(order[2] for order in orders if order[:2] == ["SELL", "WOOL"])
        self.assertLessEqual(sold, 3)

    def test_default_valuation_stress_does_not_freeze_premium_sales(self) -> None:
        obs = observation(step=5, shed={"WOOL": 4})
        orders = market_orders(obs, {"WOOL": 4}, {}, {})
        self.assertIn(["SELL", "WOOL", 4], orders)

    def test_terminal_liquidates_every_product_and_ignores_reserve(self) -> None:
        obs = observation(step=718, shed={item: 2 for item in PRODUCTS})
        orders = market_orders(
            obs,
            {item: 2 for item in PRODUCTS},
            {},
            {item: 2 for item in PRODUCTS},
            policy=self.policy,
        )
        self.assertEqual(len(orders), 9)
        self.assertEqual({order[1] for order in orders}, set(PRODUCTS))
        self.assertTrue(all(order[0] == "SELL" and order[2] == 2 for order in orders))

    def test_current_demand_tick_is_after_market_so_nonurgent_sale_waits(self) -> None:
        obs = observation(step=4, shed={"EGG": 4}, shops=["BAKERY"])
        self.assertEqual(town_demand_after_market(obs)["EGG"], 1)
        at_tick = market_orders(obs, {"EGG": 4}, {}, {}, policy=self.policy)
        after_tick = market_orders(
            observation(step=5, shed={"EGG": 4}, inventory={"EGG": 9999}, shops=["BAKERY"]),
            {"EGG": 4},
            {},
            {},
            policy=self.policy,
        )
        self.assertFalse(any(order[:2] == ["SELL", "EGG"] for order in at_tick))
        self.assertTrue(any(order[:2] == ["SELL", "EGG"] for order in after_tick))

    def test_town_demand_counts_duplicate_single_product_shops(self) -> None:
        demand = town_demand_after_market(
            observation(step=24, shops=["YARN_STORE", "YARN_STORE"])
        )
        self.assertEqual(demand["WOOL"], 5)  # two shops * 2, plus town center
        self.assertEqual(demand["FERTILIZER"], 0)

    def test_capacity_and_cash_cap_animal_purchase(self) -> None:
        obs = observation(money=5000, shed={"WHEAT": 98})
        orders = market_orders(
            obs,
            {"WHEAT": 98},
            {"animals": {"COW": 10}},
            {"WHEAT": 98},
            policy=self.policy,
        )
        buys = [order for order in orders if order[:2] == ["BUY_ANIMAL", "COW"]]
        self.assertEqual(buys, [["BUY_ANIMAL", "COW", 2]])

    def test_order_limit_and_positive_quantities(self) -> None:
        obs = observation(step=5, money=100000, shed={item: 10 for item in PRODUCTS})
        orders = market_orders(
            obs,
            {item: 10 for item in PRODUCTS},
            {
                "max_hands": 20,
                "quadrants": 4,
                "seeds": {item: 20 for item in PRODUCTS[:5]},
                "animals": {"GOOSE": 4, "COW": 4, "SHEEP": 4},
            },
            {},
            policy=self.policy,
        )
        self.assertLessEqual(len(orders), 10)
        self.assertTrue(all(len(order) < 3 or isinstance(order[2], int) and order[2] > 0 for order in orders))


if __name__ == "__main__":
    unittest.main()
