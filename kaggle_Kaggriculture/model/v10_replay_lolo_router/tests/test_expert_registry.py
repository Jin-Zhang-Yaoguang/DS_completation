from __future__ import annotations

import copy
import unittest

from kaggle_Kaggriculture.model.v10_replay_lolo_router.expert_registry import (
    BASELINE_SPECS,
    EXPERT_SPECS,
    VARIANT_SPECS,
    create_agent,
    registry_records,
    resolve_spec,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.variants import (
    animal_half_topdays,
    premium_price_slot,
)


def minimal_obs(step: int = 0, player: int = 0) -> dict:
    farm = {
        "money": 100,
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": [],
        "tiles": [["EMPTY" for _ in range(10)] for _ in range(10)],
    }
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": player,
        "farms": [copy.deepcopy(farm), copy.deepcopy(farm)],
        "private": {"shed": {}, "inventories": [{}]},
        "market": {"prices": {}, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


def assert_action_structure(action: dict, expected_hands: int) -> None:
    assert set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list) and action["farmer"]
    assert isinstance(action["hands"], list) and len(action["hands"]) == expected_hands
    assert all(isinstance(order, list) and order for order in action["hands"])
    assert isinstance(action["market"], list) and len(action["market"]) <= 10
    assert all(isinstance(order, list) and order for order in action["market"])
    for order in action["market"]:
        if order[0] in {"SELL", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}:
            assert len(order) >= 3 and int(order[2]) > 0


class RegistryTest(unittest.TestCase):
    def test_registry_has_four_baselines_and_exactly_eight_variants(self) -> None:
        self.assertEqual(len(BASELINE_SPECS), 4)
        self.assertEqual(len(VARIANT_SPECS), 8)
        self.assertEqual(len(EXPERT_SPECS), 12)
        for spec in VARIANT_SPECS.values():
            self.assertIn(spec.parent, BASELINE_SPECS)
            self.assertTrue(spec.model_id)
            self.assertTrue(spec.lineage)
            self.assertEqual(spec.lineage[-1], spec.model_id)
            self.assertEqual(spec.change_scope, "仅市场wrapper")
            self.assertTrue(spec.family)
            self.assertTrue(spec.mechanism)
            self.assertTrue(spec.expected_effect)
            self.assertEqual(spec.tag, "待评测")
            self.assertTrue(spec.is_variant)
            self.assertTrue(callable(spec.factory))

        records = registry_records()
        self.assertEqual(len(records), 12)
        self.assertEqual({row["id"] for row in records}, set(EXPERT_SPECS))
        for row in records:
            self.assertEqual(row["model_id"], row["id"])
            self.assertEqual(row["factory"], "create_agent")
            self.assertEqual(row["factory_args"], [row["model_id"]])
            self.assertEqual(row["tags"], [row["tag"]])

    def test_alias_and_unambiguous_prefix_compatibility(self) -> None:
        self.assertEqual(resolve_spec("v1").model_id, "baseline_v1")
        self.assertEqual(resolve_spec("baseline_v8").model_id, "baseline_v8")
        self.assertEqual(resolve_spec("v8_cons").model_id, "v8_conservative")
        with self.assertRaises(ValueError):
            resolve_spec("v8_")
        with self.assertRaises(KeyError):
            resolve_spec("does_not_exist")

    def test_each_create_is_module_isolated_and_step_zero_resets(self) -> None:
        left = create_agent("v1")
        right = create_agent("v1")
        self.assertIsNot(left.module, right.module)
        first = left(minimal_obs(0))
        left(minimal_obs(1))
        reset = left(minimal_obs(0))
        independent = right(minimal_obs(0))
        self.assertEqual(first, reset)
        self.assertEqual(reset, independent)

    def test_deterministic_prefix_and_episode_reset(self) -> None:
        for model_id in sorted(EXPERT_SPECS):
            with self.subTest(model_id=model_id):
                left = create_agent(model_id)
                right = create_agent(model_id)
                prefix_left = [left(minimal_obs(step)) for step in range(72)]
                prefix_right = [right(minimal_obs(step)) for step in range(72)]
                self.assertEqual(prefix_left, prefix_right)
                reset_prefix = [left(minimal_obs(step)) for step in range(72)]
                self.assertEqual(prefix_left, reset_prefix)

    def test_registered_agents_return_legal_action_structure(self) -> None:
        for model_id in sorted(EXPERT_SPECS):
            with self.subTest(model_id=model_id):
                agent = create_agent(model_id)
                action = agent(minimal_obs(0), configuration={})
                assert_action_structure(action, expected_hands=0)

    def test_topdays_residual_is_bounded_and_does_not_mutate_input(self) -> None:
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "MILK", 9],
                ["SELL", "WOOL", 1],
                ["SELL", "CARROT", 7],
                ["HIRE"],
            ],
        }
        original = copy.deepcopy(action)
        transformed = animal_half_topdays(action, minimal_obs(10 * 24))
        self.assertEqual(action, original)
        self.assertEqual(transformed["market"], [
            ["SELL", "MILK", 4],
            ["SELL", "CARROT", 7],
            ["HIRE"],
        ])
        self.assertEqual(animal_half_topdays(action, minimal_obs(11 * 24)), action)

    def test_price_slot_only_permutes_existing_sells(self) -> None:
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "CARROT", 5],
                ["HIRE"],
                ["SELL", "MILK", 3],
                ["SELL", "WOOL", 4],
            ],
        }
        obs = minimal_obs(200)
        obs["market"]["prices"] = {"CARROT": 50, "MILK": 120, "WOOL": 300}
        result = premium_price_slot(action, obs)
        self.assertEqual(result["market"][1], ["HIRE"])
        self.assertEqual(result["market"][0], ["SELL", "WOOL", 4])
        self.assertEqual(result["market"][2], ["SELL", "MILK", 3])
        self.assertEqual(
            sorted(tuple(order) for order in result["market"] if order[0] == "SELL"),
            sorted(tuple(order) for order in action["market"] if order[0] == "SELL"),
        )


if __name__ == "__main__":
    unittest.main()
