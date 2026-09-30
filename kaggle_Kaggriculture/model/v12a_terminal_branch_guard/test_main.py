from __future__ import annotations

import unittest
from unittest.mock import patch

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import main


class FakeParent:
    def __init__(self, action, branch="baseline_v8"):
        self.action = action
        self.branch = branch

    def __call__(self, obs, configuration=None):
        del obs, configuration
        return self.action

    def diagnostics(self):
        return {"selected": self.branch}


def observation(*, step=240, day=10, shed=None, prices=None, shops=None):
    return {
        "step": step,
        "day": day,
        "player": 0,
        "private": {"shed": shed or {}},
        "market": {"prices": prices or {}},
        "town": {"unlocked_shops": shops or []},
    }


def action(*market, farmer=None, hands=None):
    return {
        "farmer": farmer or ["PASS"],
        "hands": hands or [["PASS"]],
        "market": [list(item) for item in market],
    }


class BranchGuardUnitTest(unittest.TestCase):
    def make(self, parent, **kwargs):
        with patch.object(main, "_load_learned_router", return_value=parent):
            return main.BranchGuardAgent(**kwargs)

    def test_v5_v8_branch_throttles_only_animal_sells(self):
        parent_action = action(
            ("SELL", "MILK", 10),
            ("SELL", "TOMATO", 9),
            farmer=["MOVE", "NORTH"],
            hands=[["HARVEST"]],
        )
        agent = self.make(FakeParent(parent_action, "baseline_v8"))
        result = agent(
            observation(
                shed={"MILK": 10, "TOMATO": 9}, shops=["PIZZA_SHOP"]
            )
        )
        self.assertEqual(result["market"], [["SELL", "MILK", 5], ["SELL", "TOMATO", 9]])
        self.assertEqual(result["farmer"], parent_action["farmer"])
        self.assertEqual(result["hands"], parent_action["hands"])

    def test_v1_v2_branches_are_not_throttled(self):
        parent_action = action(("SELL", "WOOL", 12))
        for branch in ("baseline_v1", "baseline_v2", None):
            with self.subTest(branch=branch):
                agent = self.make(FakeParent(parent_action, branch))
                self.assertEqual(
                    agent(observation(shed={"WOOL": 12})),
                    main._canonical_action(parent_action),
                )

    def test_shed_headroom_and_deposit_guards_fail_open_to_parent(self):
        parent_action = action(("SELL", "MILK", 4), ("SELL", "WOOL", 4))
        agent = self.make(FakeParent(parent_action))
        unsafe = observation(
            shed={"MILK": 4, "WOOL": 4, "WHEAT": 92},
            shops=["PIZZA_SHOP", "YARN_STORE"],
        )
        self.assertEqual(agent(unsafe), main._canonical_action(parent_action))
        dropping = action(("SELL", "MILK", 20), hands=[["DROP"]])
        agent = self.make(FakeParent(dropping))
        self.assertEqual(
            agent(observation(shed={"MILK": 20}, shops=["PIZZA_SHOP"])),
            main._canonical_action(dropping),
        )

    def test_guard_disabled_exactly_reproduces_r002_transform(self):
        parent_action = action(("SELL", "EGG", 3), ("SELL", "WOOL", 1))
        agent = self.make(
            FakeParent(parent_action, "baseline_v1"),
            enable_guard=False,
            enable_terminal=False,
        )
        result = agent(observation(shed={"EGG": 3, "WOOL": 1}))
        self.assertEqual(result["market"], [["SELL", "EGG", 2]])

    def test_terminal_fill_only_uses_empty_slots_and_available_stock(self):
        parent_action = action(("SELL", "MILK", 3), ("BUY_SEED", "WHEAT", 1))
        agent = self.make(FakeParent(parent_action, "baseline_v8"))
        obs = observation(
            step=718,
            day=29,
            shed={"MILK": 5, "WOOL": 4},
            prices={"MILK": 100, "WOOL": 200},
        )
        result = agent(obs)
        self.assertEqual(result["market"][-2:], [["SELL", "WOOL", 4], ["SELL", "MILK", 2]])
        self.assertEqual(len(result["market"]), 4)

    def test_terminal_fill_boundary_is_only_final_actionable_step(self):
        parent_action = action(("SELL", "MILK", 3))
        agent = self.make(FakeParent(parent_action, "baseline_v8"))
        before = observation(
            step=717,
            day=29,
            shed={"MILK": 5, "WOOL": 4},
            prices={"MILK": 100, "WOOL": 200},
        )
        self.assertEqual(agent(before), main._canonical_action(parent_action))
        final = observation(
            step=718,
            day=29,
            shed={"MILK": 5, "WOOL": 4},
            prices={"MILK": 100, "WOOL": 200},
        )
        self.assertEqual(
            agent(final)["market"],
            [["SELL", "MILK", 3], ["SELL", "WOOL", 4], ["SELL", "MILK", 2]],
        )

    def test_no_price_floor_path_exists(self):
        text = (main.HERE / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("premium_floor_guard", text)
        low_prices = {product: 1 for product in main.SELLABLE_PRODUCTS}
        parent_action = action(("SELL", "MILK", 10))
        agent = self.make(FakeParent(parent_action, "baseline_v8"))
        result = agent(
            observation(
                shed={"MILK": 10}, prices=low_prices, shops=["PIZZA_SHOP"]
            )
        )
        self.assertEqual(result["market"], [["SELL", "MILK", 5]])

    def test_actual_shop_mix_gates_each_animal_product(self):
        parent_action = action(
            ("SELL", "MILK", 10),
            ("SELL", "WOOL", 10),
            ("SELL", "EGG", 10),
        )
        agent = self.make(FakeParent(parent_action, "baseline_v8"))
        result = agent(
            observation(
                shed={"MILK": 10, "WOOL": 10, "EGG": 10},
                shops=["PIZZA_SHOP"],
            )
        )
        self.assertEqual(
            result["market"],
            [
                ["SELL", "MILK", 5],
                ["SELL", "WOOL", 10],
                ["SELL", "EGG", 10],
            ],
        )

    def test_no_animal_shop_demand_returns_parent_action(self):
        parent_action = action(("SELL", "WOOL", 10))
        agent = self.make(FakeParent(parent_action, "baseline_v8"))
        result = agent(
            observation(shed={"WOOL": 10}, shops=["FARMERS_MARKET"])
        )
        self.assertEqual(result, main._canonical_action(parent_action))


if __name__ == "__main__":
    unittest.main()
