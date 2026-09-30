#!/usr/bin/env python3
from __future__ import annotations

import unittest

import shop_demand_policy as policy


class ShopDemandPolicyTest(unittest.TestCase):
    def test_eight_experts_and_exact_route_prefix(self):
        self.assertEqual(set(policy.EXPERTS), set(policy.SHOP_PRODUCTS))
        self.assertEqual(len(policy.EXPERTS), 8)
        for actions in policy._ROUTES.values():
            self.assertEqual(len(actions), 719)
            self.assertEqual(actions[:policy.ROUTER_STEP], policy._PREFIX)

    def test_demand_targets_use_only_visible_shops(self):
        one = policy._target_quantities(["YARN_STORE"])
        two = policy._target_quantities(["YARN_STORE", "PIZZA_SHOP"])
        self.assertGreater(one["SHEEP"], 4)
        self.assertGreater(two["COW"], one["COW"])
        self.assertEqual(one["TOMATO_SEED"], 0)

    def test_updates_are_frozen_at_day6_and_day9(self):
        state = {"update_stage": 0}
        policy._update_demand_state(state, ["BAKERY"], 143)
        self.assertEqual(state["update_stage"], 0)
        policy._update_demand_state(state, ["BAKERY", "YARN_STORE"], 144)
        self.assertEqual(state["target_shops"], ("BAKERY", "YARN_STORE"))
        policy._update_demand_state(state, ["BAKERY", "YARN_STORE", "PET_CAFE"], 216)
        self.assertEqual(state["target_shops"], ("BAKERY", "YARN_STORE", "PET_CAFE"))

    def test_overlay_is_bounded_and_repaid_next_step(self):
        state = {
            "route": "default", "update_stage": 1,
            "target_shops": ("BAKERY", "YARN_STORE"),
            "due_step": -1, "due": {},
        }
        obs = {"private": {"shed": {"WOOL": 20}}, "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]}}
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WOOL", 10]]}
        deferred = policy._apply_demand_overlay(obs, action, state, 144)
        self.assertEqual(deferred["market"], [["SELL", "WOOL", 2]])
        self.assertEqual(state["due"], {"WOOL": 8})
        repaid = policy._apply_demand_overlay(obs, {"farmer": ["PASS"], "hands": [], "market": []}, state, 145)
        self.assertEqual(repaid["market"], [["SELL", "WOOL", 8]])
        self.assertEqual(state["due"], {})


if __name__ == "__main__":
    unittest.main()
