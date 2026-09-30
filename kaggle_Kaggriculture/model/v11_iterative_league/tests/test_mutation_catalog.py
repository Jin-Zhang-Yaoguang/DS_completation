from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from mutation_catalog import (  # noqa: E402
    CATALOG,
    apply_mutation,
    mutation_signature,
    tried_mutations,
)


class MutationCatalogTests(unittest.TestCase):
    def setUp(self):
        self.action = {
            "farmer": ["MOVE", "UP"],
            "hands": [["WATER"], ["PASS"]],
            "market": [
                ["HIRE"],
                ["SELL", "WHEAT", 4],
                ["SELL", "MELON", 2],
            ],
        }
        self.obs = {
            "step": 100,
            "day": 4,
            "market": {
                "prices": {"WHEAT": 10, "MELON": 300},
                "inventory": {},
            },
            "private": {"shed": {"WHEAT": 9, "MELON": 3}},
        }

    def test_value_slot_changes_only_sell_order(self):
        result = apply_mutation("value_slot_priority", self.action, self.obs)
        self.assertEqual(result["farmer"], self.action["farmer"])
        self.assertEqual(result["hands"], self.action["hands"])
        before = Counter(tuple(order) for order in self.action["market"])
        after = Counter(tuple(order) for order in result["market"])
        self.assertEqual(before, after)
        self.assertEqual(result["market"][0], ["HIRE"])
        self.assertEqual(result["market"][1][1], "MELON")

    def test_market_mutations_never_change_production(self):
        for mutation in (
            "premium_floor_guard",
            "animal_batch_cap",
            "topday_animal_throttle",
            "terminal_clearance_fill",
            "terminal_value_priority",
        ):
            result = apply_mutation(mutation, self.action, self.obs)
            self.assertEqual(result["farmer"], self.action["farmer"], mutation)
            self.assertEqual(result["hands"], self.action["hands"], mutation)
            self.assertLessEqual(len(result["market"]), 10, mutation)

    def test_unknown_mutation_fails_closed(self):
        with self.assertRaises(ValueError):
            apply_mutation("invented_route", self.action, self.obs)

    def test_catalog_has_capacity_and_exact_parent_param_deduplication(self):
        self.assertGreaterEqual(len(CATALOG), 10)
        params = {"min_sell_orders": 2}
        registered = [
            {
                "id": "r001_baseline_v5_value_slot_priority",
                "parent_models": ["baseline_v5"],
                "mutation": "value_slot_priority",
                "factory_kwargs": {"mutation_params": params},
            }
        ]
        tried = tried_mutations(registered)
        self.assertIn(
            mutation_signature("baseline_v5", "value_slot_priority", params), tried
        )
        self.assertNotIn(
            mutation_signature("baseline_v1", "value_slot_priority", params), tried
        )
        self.assertNotIn(
            mutation_signature(
                "baseline_v5", "value_slot_priority", {"min_sell_orders": 3}
            ),
            tried,
        )


if __name__ == "__main__":
    unittest.main()
