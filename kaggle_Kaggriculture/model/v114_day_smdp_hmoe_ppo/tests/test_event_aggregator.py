from __future__ import annotations

import unittest

from event_aggregator import (
    EventAggregator,
    EventInputs,
    EventType,
    HIGH_LEVEL_BOUNDARY_EVENTS,
)
from option_catalog import OptionState


def _tiles():
    return [[None for _ in range(10)] for _ in range(10)]


def _official_obs(
    *,
    step: int = 0,
    day: int = 0,
    hour: int = 0,
    player: int = 0,
    own_money: float = 3_000,
    opponent_money: float = 9_999,
    shed: int = 0,
    shops=(),
):
    own_tiles = _tiles()
    opponent_tiles = _tiles()
    farms = [
        {"money": own_money, "tiles": own_tiles, "hands": []},
        {"money": opponent_money, "tiles": opponent_tiles, "hands": []},
    ]
    if player == 1:
        farms.reverse()
    return {
        "step": step,
        "day": day,
        "hour": hour,
        "player": player,
        "farms": farms,
        "private": {"shed": {"WHEAT": shed}, "seeds": {}, "inventories": [{}]},
        "market": {"inventory": {}, "prices": {}},
        "town": {"unlocked_shops": list(shops)},
        "configuration": {"episodeSteps": 720, "shedCapacity": 100},
    }


class EventAggregatorOfficialContractTests(unittest.TestCase):
    def test_cash_uses_official_own_farm_and_keeps_legacy_fallbacks(self):
        aggregator = EventAggregator()
        obs = _official_obs(player=1, own_money=420, opponent_money=99_999)
        obs["cash"] = 8_888
        obs["private"]["money"] = 7_777
        _, snapshot = aggregator.observe(obs)
        self.assertEqual(snapshot.cash, 420)
        self.assertEqual(snapshot.boundary_event, EventType.CASH_CRISIS_ENTERED)

        _, legacy_top = EventAggregator().observe({"step": 1, "cash": 610})
        _, legacy_private = EventAggregator().observe(
            {"step": 1, "private": {"money": 620}}
        )
        self.assertEqual(legacy_top.cash, 610)
        self.assertEqual(legacy_private.cash, 620)

    def test_terminal_window_has_exact_remaining_action_boundary(self):
        aggregator = EventAggregator(terminal_window_turns=48)
        _, before = aggregator.observe(
            _official_obs(step=670, day=27, hour=22), OptionState()
        )
        self.assertEqual(before.actions_remaining, 49)
        self.assertFalse(before.terminal_window)

        _, entered = aggregator.observe(
            _official_obs(step=671, day=27, hour=23), OptionState()
        )
        self.assertEqual(entered.actions_remaining, 48)
        self.assertEqual(entered.remaining_turns, 48)
        self.assertTrue(entered.terminal_window)
        self.assertEqual(
            entered.boundary_event, EventType.TERMINAL_WINDOW_ENTERED
        )

    def test_done_accepts_explicit_status_done_and_observation_compatibility(self):
        obs = _official_obs(step=12, hour=12)
        _, by_status = EventAggregator().observe(obs, status="DONE")
        _, by_argument = EventAggregator().observe(obs, done=True)
        obs_with_done = dict(obs, done=True)
        _, by_observation = EventAggregator().observe(obs_with_done)
        obs_with_status = dict(obs, status="DONE")
        _, by_observation_status = EventAggregator().observe(obs_with_status)

        for snapshot in (
            by_status, by_argument, by_observation, by_observation_status
        ):
            self.assertTrue(snapshot.done)
            self.assertEqual(snapshot.boundary_event, EventType.EPISODE_DONE)

        _, explicit_false = EventAggregator().observe(
            obs_with_done, done=False, status="DONE"
        )
        self.assertFalse(explicit_false.done)

    def test_day_boundary_context_detects_shop_crop_and_new_production(self):
        aggregator = EventAggregator()
        previous = _official_obs(step=71, day=2, hour=23)
        previous["farms"][0]["tiles"][1][1] = {
            "kind": "PLANT",
            "crop": "WHEAT",
            "planted_day": 1,
            "yield_units": 1,
        }
        previous["farms"][0]["tiles"][2][2] = {
            "kind": "COOP",
            "animal": "CHICKEN",
            "yield_units": 0,
        }
        aggregator.observe(previous)

        current = _official_obs(
            step=72, day=3, hour=0, shops=("BAKERY",)
        )
        current["farms"][0]["tiles"][1][1] = {
            "kind": "PLANT",
            "crop": "WHEAT",
            "planted_day": 1,
            "yield_units": 1,
        }
        current["farms"][0]["tiles"][2][2] = {
            "kind": "COOP",
            "animal": "CHICKEN",
            "yield_units": 1,
        }
        _, snapshot = aggregator.observe(current)

        self.assertEqual(snapshot.boundary_event, EventType.DAY_BOUNDARY)
        self.assertIn(EventType.SHOP_UNLOCKED, snapshot.events)
        self.assertIn(EventType.CROP_BECAME_HARVESTABLE, snapshot.events)
        self.assertIn(EventType.NEW_PRODUCTION_READY, snapshot.events)

    def test_inventory_threshold_is_hysteretic_and_debounced(self):
        aggregator = EventAggregator()
        obs = _official_obs(step=1, hour=1)
        inputs = EventInputs(inventory_level=10, inventory_threshold=10)
        _, entered = aggregator.observe(obs, event_inputs=inputs)
        self.assertEqual(
            entered.boundary_event,
            EventType.SELL_INVENTORY_THRESHOLD_ENTERED,
        )

        _, held = aggregator.observe(
            _official_obs(step=2, hour=2),
            event_inputs={"inventory_level": 12, "inventory_threshold": 10},
        )
        self.assertNotIn(
            EventType.SELL_INVENTORY_THRESHOLD_ENTERED, held.events
        )

        _, released = aggregator.observe(
            _official_obs(step=3, hour=3),
            event_inputs={"inventory_level": 8, "inventory_threshold": 10},
        )
        self.assertIn(
            EventType.SELL_INVENTORY_THRESHOLD_EXITED, released.events
        )

        _, reentered = aggregator.observe(
            _official_obs(step=4, hour=4),
            event_inputs={"inventory_level": 11, "inventory_threshold": 10},
        )
        self.assertEqual(
            reentered.boundary_event,
            EventType.SELL_INVENTORY_THRESHOLD_ENTERED,
        )

    def test_shed_crisis_uses_own_private_only_and_has_hysteresis(self):
        aggregator = EventAggregator()
        obs = _official_obs(step=1, hour=1, shed=90)
        obs["farms"][1]["private"] = {"shed": {"WHEAT": 1_000_000}}
        _, entered = aggregator.observe(obs)
        self.assertEqual(entered.boundary_event, EventType.SHED_CAPACITY_CRISIS)

        held_obs = _official_obs(step=2, hour=2, shed=85)
        held_obs["seed"] = 123456
        held_obs["opponent_private"] = {"shed": {"WHEAT": -1}}
        _, held = aggregator.observe(held_obs)
        self.assertNotIn(EventType.SHED_CAPACITY_CRISIS, held.events)

        _, released = aggregator.observe(_official_obs(step=3, hour=3, shed=80))
        self.assertIn(EventType.SHED_CAPACITY_CRISIS_RESOLVED, released.events)

    def test_contract_failure_latches_until_explicitly_resolved(self):
        aggregator = EventAggregator()
        _, entered = aggregator.observe(
            _official_obs(step=1, hour=1),
            event_inputs=EventInputs(option_contract_failed=True),
        )
        self.assertEqual(entered.boundary_event, EventType.OPTION_CONTRACT_FAILED)

        _, held = aggregator.observe(
            _official_obs(step=2, hour=2),
            event_inputs={"option_contract_failed": True},
        )
        self.assertNotIn(EventType.OPTION_CONTRACT_FAILED, held.events)

        aggregator.observe(
            _official_obs(step=3, hour=3),
            event_inputs={"option_contract_failed": False},
        )
        _, reentered = aggregator.observe(
            _official_obs(step=4, hour=4),
            event_inputs={"option_contract_failed": True},
        )
        self.assertEqual(
            reentered.boundary_event, EventType.OPTION_CONTRACT_FAILED
        )

    def test_one_observation_has_at_most_one_boundary_with_fixed_priority(self):
        aggregator = EventAggregator()
        obs = _official_obs(
            step=671,
            day=27,
            hour=0,
            own_money=100,
            shed=100,
            shops=("BAKERY",),
        )
        _, snapshot = aggregator.observe(
            obs,
            status="DONE",
            event_inputs=EventInputs(
                inventory_level=100,
                inventory_threshold=10,
                option_contract_failed=True,
                shop_unlocked=True,
                crop_became_harvestable=True,
                new_production_ready=True,
            ),
        )
        boundaries = [event for event in snapshot.events if event in HIGH_LEVEL_BOUNDARY_EVENTS]
        self.assertEqual(boundaries, [EventType.EPISODE_DONE])
        self.assertEqual(snapshot.boundary_event, EventType.EPISODE_DONE)
        self.assertIn(EventType.SHOP_UNLOCKED, snapshot.events)


if __name__ == "__main__":
    unittest.main()
