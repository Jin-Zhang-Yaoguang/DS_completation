"""Standard-library tests for V114 residual quotas and safe execution."""

from __future__ import annotations

import copy
import unittest

from residual_action_space import (
    RESIDUAL_SPECS,
    DailyResidualQuota,
    ResidualChannel,
    ResidualRequest,
    ResidualType,
)
from safety_executor import SafetyExecutor, copy_kaggriculture_action


def base_action():
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"], ["MOVE", "N"]],
        "market": [
            ["BUY_PRODUCT", "WHEAT", 2],
            ["SELL", "MILK", 2],
        ],
    }


class ResidualActionSpaceTests(unittest.TestCase):
    def test_exactly_eight_non_keep_actions_and_channel_flags(self):
        non_keep = [kind for kind in ResidualType if kind is not ResidualType.KEEP]
        self.assertEqual(8, len(non_keep))
        self.assertEqual(ResidualChannel.MARKET, RESIDUAL_SPECS[ResidualType.MARKET_QTY_UP_1].channel)
        self.assertEqual(ResidualChannel.UNIT, RESIDUAL_SPECS[ResidualType.REASSIGN_ONE_IDLE_UNIT].channel)
        terminal = RESIDUAL_SPECS[ResidualType.TERMINAL_RETURN_OR_SELL]
        self.assertTrue(terminal.modifies_unit)
        self.assertTrue(terminal.modifies_market)

    def test_family_and_global_daily_quotas(self):
        quota = DailyResidualQuota()
        self.assertTrue(quota.consume(ResidualType.MARKET_QTY_UP_1, 3)[0])
        self.assertTrue(quota.consume(ResidualType.MARKET_QTY_DOWN_1, 3)[0])
        allowed, reason = quota.can_consume(ResidualType.MARKET_QTY_UP_1, 3)
        self.assertFalse(allowed)
        self.assertEqual("daily_market_qty_limit", reason)

        self.assertTrue(quota.consume(ResidualType.DEFER_ONE_MARKET_ORDER, 3)[0])
        self.assertTrue(quota.consume(ResidualType.REASSIGN_ONE_IDLE_UNIT, 3)[0])
        allowed, reason = quota.can_consume(ResidualType.ADVANCE_ONE_SELL, 3)
        self.assertFalse(allowed)
        self.assertEqual("daily_non_keep_limit", reason)

    def test_keep_is_unlimited_and_day_change_resets_all_counts(self):
        quota = DailyResidualQuota()
        for _ in range(20):
            self.assertTrue(quota.consume(ResidualType.KEEP, 7)[0])
        self.assertEqual(0, quota.non_keep_count)
        self.assertTrue(quota.consume(ResidualType.CASH_TIER_UP_1, 7)[0])
        self.assertFalse(quota.can_consume(ResidualType.CASH_TIER_DOWN_1, 7)[0])
        self.assertTrue(quota.can_consume(ResidualType.CASH_TIER_DOWN_1, 8)[0])
        self.assertEqual(0, quota.non_keep_count)
        self.assertEqual({}, quota.family_counts)

    def test_request_mapping_is_tolerant(self):
        request = ResidualRequest.from_value(
            {"type": "market-qty-up", "payload": {"order_index": "1", "step": "2"}}
        )
        self.assertEqual(ResidualType.MARKET_QTY_UP_1, request.kind)
        self.assertEqual(1, request.market_index)
        self.assertEqual(2, request.quantity_step)


class SafetyExecutorValidEditTests(unittest.TestCase):
    def test_market_quantity_up_and_down(self):
        up = SafetyExecutor().execute(
            base_action(),
            {"kind": "MARKET_QTY_UP_1", "market_index": 0},
            day=0,
            context={"available_budget": 100, "unit_prices": {"WHEAT": 2}, "inventory": {"MILK": 5}},
        )
        self.assertTrue(up.applied)
        self.assertEqual(3, up.action["market"][0][2])
        self.assertTrue(up.modifies_market)
        self.assertFalse(up.modifies_unit)

        down = SafetyExecutor().execute(
            base_action(),
            {"kind": "MARKET_QTY_DOWN_1", "market_index": 0},
            day=0,
            context={"inventory": {"MILK": 5}},
        )
        self.assertTrue(down.applied)
        self.assertEqual(1, down.action["market"][0][2])

    def test_defer_removes_one_nonurgent_market_order(self):
        result = SafetyExecutor().execute(
            base_action(),
            {"kind": "DEFER_ONE_MARKET_ORDER", "market_index": 0},
            day=0,
            context={"inventory": {"MILK": 5}},
        )
        self.assertTrue(result.applied)
        self.assertEqual([["SELL", "MILK", 2]], result.action["market"])

    def test_advance_moves_existing_sell_to_front(self):
        result = SafetyExecutor().execute(
            base_action(),
            {"kind": "ADVANCE_ONE_SELL", "market_index": 1},
            day=0,
            context={"available_budget": 100, "unit_prices": {"WHEAT": 2}, "inventory": {"MILK": 5}},
        )
        self.assertTrue(result.applied)
        self.assertEqual("SELL", result.action["market"][0][0])

    def test_both_cash_tier_directions_accept_same_network_market_candidate(self):
        base = base_action()
        candidate_up = copy.deepcopy(base)
        candidate_up["market"][0][2] = 1
        up = SafetyExecutor().execute(
            base,
            {"kind": "CASH_TIER_UP_1", "candidate_action": candidate_up},
            day=0,
            context={"available_budget": 10, "unit_prices": {"WHEAT": 2}, "inventory": {"MILK": 5}},
        )
        self.assertTrue(up.applied)

        candidate_down = copy.deepcopy(base)
        candidate_down["market"] = [["SELL", "MILK", 1]]
        down = SafetyExecutor().execute(
            base,
            {"kind": "CASH_TIER_DOWN_1", "candidate_action": candidate_down},
            day=1,
            context={"inventory": {"MILK": 5}},
        )
        self.assertTrue(down.applied)
        self.assertEqual(candidate_down, down.action)

    def test_reassign_only_idle_unit(self):
        result = SafetyExecutor().execute(
            base_action(),
            {"kind": "REASSIGN_ONE_IDLE_UNIT", "unit": "farmer", "unit_action": ["MOVE", "E"]},
            day=0,
            context={
                "inventory": {"MILK": 5},
                "legal_unit_actions": {"farmer": [["PASS"], ["MOVE", "E"]]},
            },
        )
        self.assertTrue(result.applied)
        self.assertEqual(["MOVE", "E"], result.action["farmer"])
        self.assertTrue(result.modifies_unit)
        self.assertFalse(result.modifies_market)

    def test_terminal_can_append_a_safe_sell(self):
        action = base_action()
        action["market"] = []
        result = SafetyExecutor().execute(
            action,
            {"kind": "TERMINAL_RETURN_OR_SELL", "market_order": ["SELL", "MILK", 3]},
            day=29,
            context={"option_id": "TERMINAL_LIQUIDATION", "inventory": {"MILK": 3}},
        )
        self.assertTrue(result.applied)
        self.assertEqual([["SELL", "MILK", 3]], result.action["market"])
        self.assertEqual(ResidualChannel.HYBRID, result.channel)


class SafetyExecutorFallbackTests(unittest.TestCase):
    def assert_falls_back(self, result, original, reason):
        self.assertFalse(result.applied)
        self.assertEqual(reason, result.reason)
        self.assertEqual(copy_kaggriculture_action(original), result.action)

    def test_illegal_edit_falls_back_and_does_not_consume_quota(self):
        action = base_action()
        executor = SafetyExecutor(legal_validator=lambda candidate: False)
        result = executor.execute(
            action,
            {"kind": "REASSIGN_ONE_IDLE_UNIT", "unit_index": -1, "replacement": ["MOVE", "E"]},
            day=0,
            context={"inventory": {"MILK": 5}},
        )
        self.assert_falls_back(result, action, "illegal_action")
        self.assertEqual(0, executor.quota.non_keep_count)

    def test_budget_failure_falls_back(self):
        action = base_action()
        result = SafetyExecutor().execute(
            action,
            {"kind": "MARKET_QTY_UP_1", "market_index": 0},
            day=0,
            context={"available_budget": 5, "unit_prices": {"WHEAT": 2}, "inventory": {"MILK": 5}},
        )
        self.assert_falls_back(result, action, "budget_exceeded")

    def test_inventory_failure_falls_back(self):
        action = base_action()
        result = SafetyExecutor().execute(
            action,
            {"kind": "MARKET_QTY_UP_1", "market_index": 1},
            day=0,
            context={"inventory": {"MILK": 2}},
        )
        self.assert_falls_back(result, action, "insufficient_inventory")

    def test_option_contract_failure_falls_back(self):
        action = base_action()
        result = SafetyExecutor().execute(
            action,
            {"kind": "DEFER_ONE_MARKET_ORDER", "market_index": 0},
            day=0,
            context={
                "inventory": {"MILK": 5},
                "option_contract": {"allow_market": False},
            },
        )
        self.assert_falls_back(result, action, "market_edit_forbidden_by_option")

    def test_terminal_edit_requires_terminal_option(self):
        action = base_action()
        result = SafetyExecutor().execute(
            action,
            {"kind": "TERMINAL_RETURN_OR_SELL", "market_order": ["SELL", "MILK", 1]},
            day=10,
            context={"option_id": "MARKET_CASH", "inventory": {"MILK": 5}},
        )
        self.assert_falls_back(result, action, "terminal_option_required")

    def test_global_quota_failure_returns_base_action(self):
        executor = SafetyExecutor()
        action = base_action()
        requests = [
            {"kind": "MARKET_QTY_UP_1", "market_index": 0},
            {"kind": "MARKET_QTY_DOWN_1", "market_index": 0},
            {"kind": "DEFER_ONE_MARKET_ORDER", "market_index": 0},
            {"kind": "REASSIGN_ONE_IDLE_UNIT", "unit_index": -1, "replacement": ["MOVE", "E"]},
        ]
        for request in requests:
            result = executor.execute(
                action,
                request,
                day=0,
                context={"available_budget": 100, "unit_prices": {"WHEAT": 1}, "inventory": {"MILK": 5}},
            )
            self.assertTrue(result.applied)
        blocked = executor.execute(
            action,
            {"kind": "ADVANCE_ONE_SELL", "market_index": 1},
            day=0,
            context={"inventory": {"MILK": 5}},
        )
        self.assert_falls_back(blocked, action, "daily_non_keep_limit")

    def test_inputs_and_candidate_payload_are_never_modified(self):
        action = base_action()
        action_before = copy.deepcopy(action)
        candidate = copy.deepcopy(action)
        candidate["market"][0][2] = 1
        candidate_before = copy.deepcopy(candidate)
        request = {"kind": "CASH_TIER_UP_1", "candidate_action": candidate}
        request_before = copy.deepcopy(request)

        result = SafetyExecutor().execute(
            action,
            request,
            day=0,
            context={"available_budget": 10, "unit_prices": {"WHEAT": 2}, "inventory": {"MILK": 5}},
        )
        result.action["market"][0][2] = 99
        self.assertEqual(action_before, action)
        self.assertEqual(candidate_before, candidate)
        self.assertEqual(request_before, request)

    def test_missing_fields_and_tuple_orders_are_tolerated(self):
        action = {"farmer": ("PASS",), "market": (("SELL", "MILK", 1),)}
        result = SafetyExecutor().execute(action, "KEEP", day=0)
        self.assertEqual(
            {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 1]]},
            result.action,
        )
        self.assertFalse(result.applied)
        self.assertEqual("keep", result.reason)


if __name__ == "__main__":
    unittest.main()
