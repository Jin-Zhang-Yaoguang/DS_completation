"""Unit tests for V12B's observable state gates and safety invariants."""

from __future__ import annotations

import copy
import unittest

import main


def tile(animal: str = "") -> dict[str, str]:
    return {"kind": "PASTURE", "animal": animal}


def observation(
    *,
    step: int,
    price: float = 144,
    inventory: int = 10010,
    own_cows: int = 1,
    opponent_cows: int = 3,
    shed: int = 20,
    own_money: int = 0,
    opponent_money: int = 0,
) -> dict:
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"tiles": [[tile("COW") for _ in range(own_cows)]], "hands": [], "money": own_money},
            {"tiles": [[tile("COW") for _ in range(opponent_cows)]], "hands": [], "money": opponent_money},
        ],
        "market": {
            "prices": {"EGG": 50, "MILK": price, "WOOL": 200},
            "inventory": {"EGG": 10000, "MILK": inventory, "WOOL": 10000},
        },
        "town": {"unlocked_shops": ["PIZZA_SHOP"]},
        "private": {"shed": {"MILK": shed}, "inventories": []},
    }


ACTION = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 12]]}


def transition(obs: dict, own_sale: int = 0) -> dict:
    action = {"market": [["SELL", "MILK", own_sale]]} if own_sale else {"market": []}
    return main._transition_context(obs, action)


class FeedbackDecisionTest(unittest.TestCase):
    def test_first_observation_never_triggers(self):
        decision = main.feedback_decision(observation(step=100), "MILK", 12, None)
        self.assertFalse(decision["triggered"])
        self.assertEqual(decision["reason"], "no_lagged_observation")

    def test_visible_supply_shock_reduces_existing_sell(self):
        previous = transition(observation(step=100, price=150, inventory=10005))
        decision = main.feedback_decision(
            observation(step=101, price=112, inventory=10100), "MILK", 12, previous
        )
        self.assertTrue(decision["triggered"])
        self.assertEqual(decision["severity"], "severe")
        self.assertEqual(decision["new_quantity"], 6)
        self.assertEqual(decision["reason"], "observable_collision_pressure")

    def test_warehouse_pressure_bypasses_throttle(self):
        previous = transition(observation(step=100, price=150, inventory=10005))
        decision = main.feedback_decision(
            observation(step=101, price=112, inventory=10100, shed=75),
            "MILK",
            12,
            previous,
        )
        self.assertFalse(decision["triggered"])
        self.assertEqual(decision["reason"], "warehouse_pressure_bypass")

    def test_terminal_phase_bypasses_throttle(self):
        previous = transition(observation(step=671, price=150, inventory=10005))
        decision = main.feedback_decision(
            observation(step=672, price=112, inventory=10100), "MILK", 12, previous
        )
        self.assertFalse(decision["triggered"])
        self.assertEqual(decision["reason"], "terminal_bypass")

    def test_no_rival_capacity_no_throttle(self):
        previous = transition(observation(step=100, price=150, inventory=10005))
        decision = main.feedback_decision(
            observation(step=101, price=112, inventory=10100, opponent_cows=0),
            "MILK",
            12,
            previous,
        )
        self.assertFalse(decision["triggered"])
        self.assertEqual(decision["reason"], "no_visible_rival_supply")

    def test_own_planned_sale_is_removed_from_opponent_lower_bound(self):
        previous = transition(
            observation(step=100, price=150, inventory=10005), own_sale=100
        )
        decision = main.feedback_decision(
            observation(step=101, price=112, inventory=10100), "MILK", 12, previous
        )
        self.assertFalse(decision["triggered"])
        self.assertLess(decision["opponent_supply_lower_bound"], 0)
        self.assertEqual(decision["reason"], "no_positive_opponent_supply_lower_bound")

    def test_floor_risk_is_uncertainty_bypass(self):
        previous = transition(observation(step=100, price=1, inventory=10100))
        decision = main.feedback_decision(
            observation(step=101, price=1, inventory=10150), "MILK", 12, previous
        )
        self.assertFalse(decision["triggered"])
        self.assertEqual(decision["reason"], "floor_risk_uncertainty_bypass")

    def test_public_lead_protection_uses_semantic_zero_boundary(self):
        previous = transition(observation(step=100, price=150, inventory=10005))
        decision = main.feedback_decision(
            observation(
                step=101,
                price=112,
                inventory=10100,
                own_money=1001,
                opponent_money=1000,
            ),
            "MILK",
            12,
            previous,
        )
        self.assertFalse(decision["triggered"])
        self.assertEqual(decision["public_bank_margin"], 1)
        self.assertEqual(decision["reason"], "public_lead_protection_bypass")

    def test_tied_public_bank_keeps_feedback_available(self):
        previous = transition(observation(step=100, price=150, inventory=10005))
        decision = main.feedback_decision(
            observation(
                step=101,
                price=112,
                inventory=10100,
                own_money=1000,
                opponent_money=1000,
            ),
            "MILK",
            12,
            previous,
        )
        self.assertTrue(decision["triggered"])
        self.assertEqual(decision["public_bank_state"], "tied")


class PolicyInvariantTest(unittest.TestCase):
    def test_only_eligible_sell_quantity_changes(self):
        action = {
            "farmer": ["MOVE", "N"],
            "hands": [["PASS"]],
            "market": [["BUY", "WHEAT_SEED", 2], ["SELL", "TOMATO", 9], ["SELL", "MILK", 12]],
        }
        parent = lambda obs, configuration=None: copy.deepcopy(action)
        policy = main.MarketFeedbackPolicy(parent)
        policy(observation(step=100, price=150, inventory=10005))
        result = policy(observation(step=101, price=112, inventory=10100))
        self.assertEqual(result["farmer"], action["farmer"])
        self.assertEqual(result["hands"], action["hands"])
        self.assertEqual(result["market"][:2], action["market"][:2])
        self.assertEqual(result["market"][2], ["SELL", "MILK", 6])
        self.assertEqual(policy.diagnostics()["trigger_count"], 1)
        self.assertEqual(policy.diagnostics()["trigger_history"][0]["item"], "MILK")
        self.assertEqual(policy.diagnostics()["trigger_history"][0]["pre_money_gap"], 0)

    def test_step_zero_resets_lagged_state(self):
        parent = lambda obs, configuration=None: copy.deepcopy(ACTION)
        policy = main.MarketFeedbackPolicy(parent)
        policy(observation(step=100, price=150, inventory=10005))
        policy(observation(step=101, price=112, inventory=10100))
        result = policy(observation(step=0, price=112, inventory=10100))
        self.assertEqual(result, ACTION)
        self.assertEqual(policy.last_events[0]["reason"], "no_lagged_observation")


if __name__ == "__main__":
    unittest.main()
