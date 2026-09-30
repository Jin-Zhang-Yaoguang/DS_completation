#!/usr/bin/env python3
"""Parity and semantic tests for the evaluator-only accounting engine."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from typing import Any, Mapping
import unittest


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[3]
ORIGINAL_ROOT = (
    MODEL_ROOT
    / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
)
ORIGINAL_BUILDS = sorted((ORIGINAL_ROOT / "build").glob("lib.*/kagsim*.so"))
ACCOUNTING_BUILDS = sorted((HERE / "_module").glob("kagsim_accounting*.so"))


def normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    return value


def idle(observation: Mapping[str, Any]) -> dict[str, Any]:
    seat = int(observation.get("player", 0) or 0)
    farms = list(observation.get("farms", []) or [])
    farm = farms[seat]
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in list(farm.get("hands", []) or [])],
        "market": [],
    }


def fixed_legal_action(observation: Mapping[str, Any]) -> dict[str, Any]:
    action = idle(observation)
    step = int(observation.get("step", 0) or 0)
    if step == 0:
        action["market"] = [["HIRE"], ["BUY_SEED", "WHEAT", 1]]
    elif step == 1:
        action["farmer"] = ["PLANT", "WHEAT"]
    elif step == 2:
        action["farmer"] = ["WATER"]
    elif step == 3:
        action["market"] = [["BUY_PRODUCT", "WHEAT", 2]]
    elif step == 4:
        action["market"] = [["SELL", "WHEAT", 1]]
    elif step == 5:
        action["farmer"] = ["PICKUP", "WHEAT", 1]
    elif step == 6:
        action["farmer"] = ["DROP"]
    return action


def overflow_action(observation: Mapping[str, Any]) -> dict[str, Any]:
    action = idle(observation)
    step = int(observation.get("step", 0) or 0)
    if step == 0:
        action["market"] = [
            ["BUY_SEED", "WHEAT", 5],
            ["BUY_PRODUCT", "WHEAT", 100],
        ]
    script = {
        1: ["PLANT", "WHEAT"],
        2: ["WATER"],
        3: ["WEST"],
        4: ["PLANT", "WHEAT"],
        5: ["WATER"],
        6: ["NORTH"],
        7: ["PLANT", "WHEAT"],
        8: ["WATER"],
        9: ["EAST"],
        10: ["PLANT", "WHEAT"],
        11: ["WATER"],
        12: ["WEST"],
        13: ["WEST"],
        14: ["PLANT", "WHEAT"],
        15: ["WATER"],
        24: ["WATER"],
        25: ["WEST"],
        26: ["WATER"],
        27: ["NORTH"],
        28: ["WATER"],
        29: ["EAST"],
        30: ["WATER"],
        31: ["WEST"],
        32: ["WEST"],
        33: ["WATER"],
        48: ["WATER"],
        49: ["HARVEST"],
        50: ["WEST"],
        51: ["WATER"],
        52: ["HARVEST"],
        53: ["NORTH"],
        54: ["WATER"],
        55: ["HARVEST"],
        56: ["EAST"],
        57: ["WATER"],
        58: ["HARVEST"],
        59: ["WEST"],
        60: ["WEST"],
        61: ["WATER"],
        62: ["HARVEST"],
        63: ["EAST"],
        64: ["EAST"],
        65: ["SOUTH"],
        66: ["DROP"],
    }
    if step in script:
        action["farmer"] = script[step]
    return action


class AccountingEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not ORIGINAL_BUILDS:
            raise RuntimeError(f"validated original kagsim build not found under {ORIGINAL_ROOT}")
        if len(ACCOUNTING_BUILDS) != 1:
            raise RuntimeError(
                "build accounting module first with build_accounting_engine.py; "
                f"found {ACCOUNTING_BUILDS}"
            )
        sys.path.insert(0, str(ORIGINAL_BUILDS[-1].parent))
        sys.path.insert(0, str((HERE / "_module").resolve()))
        cls.original = importlib.import_module("kagsim")
        cls.accounting = importlib.import_module("kagsim_accounting")
        if str(cls.original.ENGINE_VERSION) != "1.32.7":
            raise RuntimeError(f"original engine drift: {cls.original.ENGINE_VERSION}")
        if str(cls.accounting.ENGINE_VERSION) != "1.32.7":
            raise RuntimeError(f"accounting engine drift: {cls.accounting.ENGINE_VERSION}")

    def test_stepwise_observation_and_reward_equivalence(self) -> None:
        original = self.original.Game(7100, steps=720)
        accounting = self.accounting.Game(7100, steps=720)
        expected_step = 0
        while not original.done:
            self.assertEqual(bool(original.done), bool(accounting.done))
            original_obs = [original.observe(0), original.observe(1)]
            accounting_obs = [accounting.observe(0), accounting.observe(1)]
            self.assertEqual(
                normalize(original_obs),
                normalize(accounting_obs),
                f"observation drift before step {expected_step}",
            )
            self.assertNotIn("accounting", normalize(accounting_obs[0]))
            actions = [fixed_legal_action(original_obs[0]), idle(original_obs[1])]
            original.step(actions[0], actions[1])
            accounting.step(actions[0], actions[1])
            self.assertEqual(float(original.reward(0)), float(accounting.reward(0)))
            self.assertEqual(float(original.reward(1)), float(accounting.reward(1)))
            expected_step += 1
        self.assertEqual(expected_step, 719)
        self.assertTrue(accounting.done)
        self.assertEqual(normalize(original.observe(0)), normalize(accounting.observe(0)))
        truth = normalize(accounting.accounting(0))
        self.assertEqual(truth["schema"], "kagsim-accounting-v1")
        self.assertEqual(truth["successful_hires"], 1)
        self.assertEqual(truth["sold_units"]["WHEAT"], 1)

    def test_bought_and_consumed_units_are_real(self) -> None:
        game = self.accounting.Game(31, steps=720)

        build_and_buy = idle(game.observe(0))
        build_and_buy["farmer"] = ["BUILD_COOP"]
        build_and_buy["market"] = [["BUY_ANIMAL", "GOOSE", 1]]
        game.step(build_and_buy, idle(game.observe(1)))

        pickup_goose = idle(game.observe(0))
        pickup_goose["farmer"] = ["PICKUP", "GOOSE", 1]
        game.step(pickup_goose, idle(game.observe(1)))

        place_goose = idle(game.observe(0))
        place_goose["farmer"] = ["PLACE", "GOOSE"]
        game.step(place_goose, idle(game.observe(1)))

        buy_wheat = idle(game.observe(0))
        buy_wheat["market"] = [["BUY_PRODUCT", "WHEAT", 1]]
        game.step(buy_wheat, idle(game.observe(1)))

        pickup_wheat = idle(game.observe(0))
        pickup_wheat["farmer"] = ["PICKUP", "WHEAT", 1]
        game.step(pickup_wheat, idle(game.observe(1)))

        feed = idle(game.observe(0))
        feed["farmer"] = ["FEED"]
        game.step(feed, idle(game.observe(1)))

        truth = normalize(game.accounting(0))
        self.assertEqual(truth["bought_units"]["GOOSE"], 1)
        self.assertEqual(truth["consumed_units"]["GOOSE"], 1)
        self.assertEqual(truth["total_inventory"]["GOOSE"], 0)
        self.assertEqual(truth["bought_units"]["WHEAT"], 1)
        self.assertEqual(truth["consumed_units"]["WHEAT"], 1)
        self.assertEqual(truth["total_inventory"]["WHEAT"], 0)

    def test_sell_request_is_not_a_sale(self) -> None:
        game = self.accounting.Game(11, steps=720)
        observation = game.observe(0)
        action = idle(observation)
        requested = 10
        action["market"] = [["SELL", "WHEAT", requested]]
        game.step(action, idle(game.observe(1)))
        truth = normalize(game.accounting(0))
        self.assertEqual(requested, 10)
        self.assertEqual(truth["sold_units"]["WHEAT"], 0)
        self.assertNotEqual(requested, truth["sold_units"]["WHEAT"])
        self.assertEqual(truth["sell_revenue"], 0.0)

    def test_hire_failure_is_not_a_success(self) -> None:
        game = self.accounting.Game(23, steps=720)
        own = idle(game.observe(0))
        own["market"] = [["BUY_LAND"], ["BUY_LAND"], ["HIRE"]]
        game.step(own, idle(game.observe(1)))
        truth = normalize(game.accounting(0))
        self.assertEqual(truth["total_spend"], 3000.0)
        self.assertEqual(truth["successful_hires"], 0)
        self.assertEqual(truth["hands"], 0)
        self.assertEqual(len(normalize(game.observe(0))["farms"][0]["hands"]), 0)

    def test_explicit_shed_overflow_and_conservation(self) -> None:
        game = self.accounting.Game(47, steps=720)
        before_drop: dict[str, Any] | None = None
        for step in range(67):
            own_obs = game.observe(0)
            if step == 66:
                before_drop = normalize(game.accounting(0))
            game.step(overflow_action(own_obs), idle(game.observe(1)))
        self.assertIsNotNone(before_drop)
        assert before_drop is not None
        combined_before = int(before_drop["total_inventory"]["WHEAT"])
        self.assertGreater(combined_before, 100)

        truth = normalize(game.accounting(0))
        discarded = int(truth["discarded"]["WHEAT"])
        explicit = int(truth["discarded_explicit"]["WHEAT"])
        eod = int(truth["discarded_end_of_day"]["WHEAT"])
        self.assertGreater(explicit, 0)
        self.assertEqual(eod, 0)
        self.assertEqual(discarded, explicit + eod)
        self.assertEqual(explicit, combined_before - 100)
        self.assertEqual(truth["carried"]["WHEAT"], 0)
        self.assertEqual(truth["shed"]["WHEAT"], 100)
        self.assertEqual(truth["bought_seed_units"]["WHEAT"], 5)
        self.assertEqual(truth["planted_seed_units"]["WHEAT"], 5)
        self.assertEqual(truth["produced"]["WHEAT"], 10)

        lhs = int(truth["produced"]["WHEAT"]) + int(truth["bought_units"]["WHEAT"])
        rhs = (
            int(truth["total_inventory"]["WHEAT"])
            + int(truth["sold_units"]["WHEAT"])
            + int(truth["consumed_units"]["WHEAT"])
            + discarded
        )
        self.assertEqual(lhs, rhs)

    def test_end_of_day_shed_overflow_is_separate(self) -> None:
        game = self.accounting.Game(47, steps=720)
        combined_before = 0
        for step in range(72):
            observation = game.observe(0)
            action = overflow_action(observation)
            if step == 66:
                action["farmer"] = ["PASS"]
            if step == 71:
                combined_before = int(
                    normalize(game.accounting(0))["total_inventory"]["WHEAT"]
                )
            game.step(action, idle(game.observe(1)))
        self.assertGreater(combined_before, 100)
        truth = normalize(game.accounting(0))
        self.assertEqual(truth["discarded_explicit"]["WHEAT"], 0)
        self.assertEqual(
            truth["discarded_end_of_day"]["WHEAT"], combined_before - 100
        )
        self.assertEqual(
            truth["discarded"]["WHEAT"], truth["discarded_end_of_day"]["WHEAT"]
        )
        self.assertEqual(truth["total_inventory"]["WHEAT"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
