import unittest
from math import isclose
from types import SimpleNamespace

from event_aggregator import EventAggregator, EventType
from option_catalog import (
    BudgetTier,
    OPTION_CATALOG,
    OptionId,
    OptionState,
    RiskTier,
    smdp_duration_discount,
    transition_option,
)


class OptionEventContractTests(unittest.TestCase):
    def test_catalog_has_four_options_and_tiers_are_part_of_state(self):
        self.assertEqual(set(OPTION_CATALOG), set(OptionId))
        self.assertEqual(len(OPTION_CATALOG), 4)
        state = OptionState(budget_tier=BudgetTier.LEAN, risk_tier=RiskTier.SAFE)
        self.assertIs(state.budget_tier, BudgetTier.LEAN)
        self.assertIs(state.risk_tier, RiskTier.SAFE)

    def test_normal_switch_only_at_hour_zero_and_switch_is_debounced(self):
        aggregator = EventAggregator()
        initial = aggregator.advance(
            {"step": 0, "hour": 0, "cash": 1000},
            requested_option=OptionId.PRODUCTION_LOGISTICS,
        )
        self.assertIsNotNone(initial.transition)
        self.assertTrue(initial.transition.changed)

        mid_day = aggregator.advance(
            {"step": 3, "hour": 3, "cash": 1000},
            initial.state,
            requested_option=OptionId.MARKET_CASH,
        )
        self.assertIsNotNone(mid_day.transition)
        self.assertFalse(mid_day.transition.allowed)
        self.assertIs(mid_day.state.current_option, OptionId.PRODUCTION_LOGISTICS)

        next_day = aggregator.advance(
            {"step": 24, "hour": 0, "cash": 1000},
            mid_day.state,
            requested_option=OptionId.MARKET_CASH,
            budget_tier="LEAN",
            risk_tier="SAFE",
        )
        self.assertIn(EventType.DAY_BOUNDARY, next_day.snapshot.events)
        self.assertIsNotNone(next_day.transition)
        self.assertTrue(next_day.transition.changed)
        self.assertIs(next_day.state.current_option, OptionId.MARKET_CASH)
        self.assertIs(next_day.state.budget_tier, BudgetTier.LEAN)
        self.assertIs(next_day.state.risk_tier, RiskTier.SAFE)

    def test_cash_hysteresis_and_recovery_six_turn_minimum_and_cooldown(self):
        aggregator = EventAggregator(cash_enter_threshold=500, cash_exit_threshold=750)
        base = transition_option(
            OptionState(), OptionId.PRODUCTION_LOGISTICS, 0, day_boundary=True
        ).state

        entered = aggregator.advance({"step": 6, "hour": 6, "cash": 500}, base)
        self.assertIn(EventType.CASH_CRISIS_ENTERED, entered.snapshot.events)
        self.assertIs(entered.state.current_option, OptionId.RECOVERY)
        self.assertTrue(entered.state.cash_crisis)

        # Between thresholds the latch remains set and emits no repeated event.
        held = aggregator.advance({"step": 10, "hour": 10, "cash": 600}, entered.state)
        self.assertTrue(held.state.cash_crisis)
        self.assertNotIn(EventType.CASH_CRISIS_ENTERED, held.snapshot.events)

        too_early = aggregator.advance(
            {"step": 11, "hour": 11, "cash": 800},
            held.state,
            requested_option=OptionId.MARKET_CASH,
        )
        self.assertIn(EventType.CASH_CRISIS_EXITED, too_early.snapshot.events)
        self.assertIsNotNone(too_early.transition)
        self.assertFalse(too_early.transition.allowed)
        self.assertIn(
            too_early.transition.reason,
            {"switch_cooldown", "recovery_minimum_duration"},
        )

        released = aggregator.advance(
            {"step": 12, "hour": 12, "cash": 800},
            too_early.state,
            requested_option=OptionId.MARKET_CASH,
        )
        self.assertIsNotNone(released.transition)
        self.assertTrue(released.transition.changed)
        self.assertIs(released.state.current_option, OptionId.MARKET_CASH)
        self.assertFalse(released.state.cash_crisis)

    def test_cash_crisis_retries_recovery_after_cooldown(self):
        aggregator = EventAggregator(cash_enter_threshold=500, cash_exit_threshold=750)
        base = transition_option(
            OptionState(), OptionId.PRODUCTION_LOGISTICS, 0, day_boundary=True
        ).state

        blocked = aggregator.advance({"step": 2, "hour": 2, "cash": 400}, base)
        self.assertTrue(blocked.state.cash_crisis)
        self.assertIsNotNone(blocked.transition)
        self.assertFalse(blocked.transition.allowed)
        self.assertEqual(blocked.transition.reason, "switch_cooldown")

        retried = aggregator.advance(
            {"step": 6, "hour": 6, "cash": 450}, blocked.state
        )
        self.assertNotIn(EventType.CASH_CRISIS_ENTERED, retried.snapshot.events)
        self.assertIsNotNone(retried.transition)
        self.assertTrue(retried.transition.changed)
        self.assertIs(retried.state.current_option, OptionId.RECOVERY)

    def test_terminal_window_forces_one_absorbing_entry(self):
        aggregator = EventAggregator(terminal_window_turns=48)
        state = transition_option(
            OptionState(), OptionId.PRODUCTION_LOGISTICS, 648, day_boundary=True
        ).state

        terminal = aggregator.advance(
            SimpleNamespace(step=672, hour=0, cash=900, episodeSteps=720), state
        )
        self.assertIn(EventType.TERMINAL_WINDOW_ENTERED, terminal.snapshot.events)
        self.assertIs(
            terminal.state.current_option, OptionId.TERMINAL_LIQUIDATION
        )
        self.assertEqual(terminal.state.terminal_entry_step, 672)

        repeated = aggregator.advance(
            {
                "step": 673,
                "hour": 1,
                "cash": 900,
                "episodeSteps": 720,
                "seed": "must-not-be-used",
                "opponent_private": {"cash": -999999},
            },
            terminal.state,
            requested_option=OptionId.MARKET_CASH,
        )
        self.assertNotIn(
            EventType.TERMINAL_WINDOW_ENTERED, repeated.snapshot.events
        )
        self.assertIs(
            repeated.state.current_option, OptionId.TERMINAL_LIQUIDATION
        )
        self.assertEqual(repeated.state.terminal_entry_step, 672)
        self.assertIsNotNone(repeated.transition)
        self.assertFalse(repeated.transition.allowed)
        self.assertEqual(repeated.transition.reason, "terminal_is_absorbing")

    def test_smdp_duration_discount_uses_fractional_days(self):
        self.assertTrue(isclose(smdp_duration_discount(0.99, 0), 1.0))
        self.assertTrue(isclose(smdp_duration_discount(0.99, 6), 0.99**0.25))
        self.assertTrue(isclose(smdp_duration_discount(0.99, 24), 0.99))
        self.assertTrue(isclose(smdp_duration_discount(0.99, 48), 0.99**2))
        with self.assertRaises(ValueError):
            smdp_duration_discount(0.0, 24)
        with self.assertRaises(ValueError):
            smdp_duration_discount(0.99, -1)


if __name__ == "__main__":
    unittest.main()
