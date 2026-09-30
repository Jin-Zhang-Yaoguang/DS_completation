"""V114 V4-0 model contract tests using only unittest."""

from __future__ import annotations

import unittest

import numpy as np

from critics import (
    ManagerCritic,
    OptionCritic,
    ResidualCritic,
    deserialize_parameters,
    serialize_parameters,
)
from model_experts import IndependentExpertAdapters
from model_manager import DaySMDPManager
from model_residual import (
    MARKET_RESIDUAL_ACTIONS,
    UNIT_RESIDUAL_ACTIONS,
    BoundedResidualActorCritic,
)


def assert_tree_equal(
    case: unittest.TestCase, expected: dict, actual: dict
) -> None:
    case.assertEqual(set(expected), set(actual))
    for key in expected:
        if isinstance(expected[key], dict):
            assert_tree_equal(case, expected[key], actual[key])
        else:
            np.testing.assert_array_equal(expected[key], actual[key])


def assert_all_finite(case: unittest.TestCase, *arrays: np.ndarray) -> None:
    for array in arrays:
        case.assertTrue(np.isfinite(array).all())


class CriticContractTest(unittest.TestCase):
    def test_three_independent_critics_return_value_and_catastrophe(self) -> None:
        inputs = np.linspace(-2.0, 2.0, 21, dtype=np.float32).reshape(3, 7)
        critics = (
            ManagerCritic(7, seed=10),
            OptionCritic(7, seed=20),
            ResidualCritic(7, seed=30),
        )
        self.assertEqual(
            [critic.scope for critic in critics],
            ["V_manager", "V_option", "V_residual"],
        )
        for critic in critics:
            output = critic(inputs)
            self.assertEqual(output.value.shape, (3,))
            self.assertEqual(output.catastrophe_logit.shape, (3,))
            self.assertEqual(output.catastrophe_probability.shape, (3,))
            assert_all_finite(self, *output)
            self.assertTrue((output.catastrophe_probability >= 0.0).all())
            self.assertTrue((output.catastrophe_probability <= 1.0).all())
            self.assertGreater(critic.value_coef, 0.0)

        manager_weight = critics[0].parameters["trunk"]["layer_0"]["weight"]
        option_weight = critics[1].parameters["trunk"]["layer_0"]["weight"]
        residual_weight = critics[2].parameters["trunk"]["layer_0"]["weight"]
        self.assertFalse(np.shares_memory(manager_weight, option_weight))
        self.assertFalse(np.shares_memory(manager_weight, residual_weight))
        option_before = option_weight.copy()
        manager_weight[0, 0] += 1.0
        np.testing.assert_array_equal(option_weight, option_before)

    def test_value_loss_cannot_be_disabled(self) -> None:
        for critic_type in (ManagerCritic, OptionCritic, ResidualCritic):
            with self.subTest(critic=critic_type.__name__):
                with self.assertRaises(ValueError):
                    critic_type(7, value_coef=0.0)


class ModelContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = 3
        self.units = 5
        self.market_slots = 4
        self.input_dim = 7
        self.unit_feature_dim = 6
        self.market_feature_dim = 8
        rng = np.random.default_rng(114)
        self.state_features = rng.normal(
            size=(self.batch, self.input_dim)
        ).astype(np.float32)
        self.unit_features = rng.normal(
            size=(self.batch, self.units, self.unit_feature_dim)
        ).astype(np.float32)
        self.market_features = rng.normal(
            size=(self.batch, self.market_slots, self.market_feature_dim)
        ).astype(np.float32)

    def test_manager_shapes_and_serialization_round_trip(self) -> None:
        manager = DaySMDPManager(self.input_dim, seed=1)
        output = manager(self.state_features)
        self.assertEqual(output.option_logits.shape, (self.batch, 4))
        self.assertEqual(output.budget_logits.shape, (self.batch, 3))
        self.assertEqual(output.risk_logits.shape, (self.batch, 3))
        self.assertEqual(output.value.shape, (self.batch,))
        self.assertEqual(output.catastrophe_probability.shape, (self.batch,))
        assert_all_finite(self, *output)
        self.assertIn("V_manager", manager.parameters)
        self.assertGreater(manager.value_coef, 0.0)

        saved = manager.state_dict()
        restored = deserialize_parameters(serialize_parameters(saved))
        assert_tree_equal(self, saved, restored)
        reloaded = DaySMDPManager(self.input_dim, seed=999)
        reloaded.load_state_dict(restored)
        reloaded_output = reloaded(self.state_features)
        for expected, actual in zip(output, reloaded_output):
            np.testing.assert_array_equal(expected, actual)

        with self.assertRaises(ValueError):
            DaySMDPManager(self.input_dim, value_coef=0.0)

    def test_two_experts_have_independent_parameters_state_and_critics(self) -> None:
        experts = IndependentExpertAdapters(
            self.input_dim,
            self.unit_feature_dim,
            self.market_feature_dim,
            num_unit_actions=11,
            num_market_actions=9,
            state_dim=12,
            seed=2,
        )
        states = experts.initial_states(self.batch)
        self.assertFalse(
            np.shares_memory(
                states["production_logistics"].memory,
                states["market_cash"].memory,
            )
        )
        outputs = experts(
            self.state_features,
            self.unit_features,
            self.market_features,
            states,
        )
        for name, output in outputs.items():
            with self.subTest(expert=name):
                self.assertEqual(output.unit_logits.shape, (self.batch, self.units, 11))
                self.assertEqual(
                    output.market_logits.shape,
                    (self.batch, self.market_slots, 9),
                )
                self.assertEqual(output.next_state.memory.shape, (self.batch, 12))
                self.assertEqual(output.value.shape, (self.batch,))
                self.assertEqual(
                    output.catastrophe_probability.shape, (self.batch,)
                )
                assert_all_finite(
                    self,
                    output.unit_logits,
                    output.market_logits,
                    output.next_state.memory,
                    output.value,
                    output.catastrophe_logit,
                    output.catastrophe_probability,
                )

        production = experts.production_logistics.parameters
        market = experts.market_cash.parameters
        self.assertIn("V_option", production)
        self.assertIn("V_option", market)
        production_weight = production["observation_encoder"]["layer_0"]["weight"]
        market_weight = market["observation_encoder"]["layer_0"]["weight"]
        self.assertFalse(np.shares_memory(production_weight, market_weight))
        market_before = market_weight.copy()
        production_weight[0, 0] += 5.0
        np.testing.assert_array_equal(market_weight, market_before)

        production_critic = production["V_option"]["value_head"]["layer_0"]["weight"]
        market_critic = market["V_option"]["value_head"]["layer_0"]["weight"]
        self.assertFalse(np.shares_memory(production_critic, market_critic))

        saved = experts.state_dict()
        restored = deserialize_parameters(serialize_parameters(saved))
        assert_tree_equal(self, saved, restored)
        expected_after_mutation = experts(
            self.state_features,
            self.unit_features,
            self.market_features,
            states,
        )
        reloaded = IndependentExpertAdapters(
            self.input_dim,
            self.unit_feature_dim,
            self.market_feature_dim,
            num_unit_actions=11,
            num_market_actions=9,
            state_dim=12,
            seed=999,
        )
        reloaded.load_state_dict(restored)
        reloaded_outputs = reloaded(
            self.state_features,
            self.unit_features,
            self.market_features,
            reloaded.initial_states(self.batch),
        )
        for name in expected_after_mutation:
            for expected, actual in zip(
                expected_after_mutation[name], reloaded_outputs[name]
            ):
                if hasattr(expected, "memory"):
                    np.testing.assert_array_equal(expected.memory, actual.memory)
                else:
                    np.testing.assert_array_equal(expected, actual)

        with self.assertRaises(ValueError):
            IndependentExpertAdapters(
                self.input_dim,
                self.unit_feature_dim,
                self.market_feature_dim,
                11,
                9,
                value_coef=0.0,
            )

    def test_residual_has_split_unit_and_market_heads(self) -> None:
        residual = BoundedResidualActorCritic(
            self.input_dim,
            self.unit_feature_dim,
            self.market_feature_dim,
            seed=3,
        )
        output = residual(
            self.state_features, self.unit_features, self.market_features
        )
        self.assertEqual(
            output.unit_logits.shape,
            (self.batch, self.units, len(UNIT_RESIDUAL_ACTIONS)),
        )
        self.assertEqual(
            output.market_logits.shape,
            (self.batch, self.market_slots, len(MARKET_RESIDUAL_ACTIONS)),
        )
        self.assertEqual(output.value.shape, (self.batch,))
        self.assertEqual(output.catastrophe_probability.shape, (self.batch,))
        assert_all_finite(self, *output)
        self.assertIn("V_residual", residual.parameters)
        self.assertIsNot(
            residual.parameters["unit_branch"],
            residual.parameters["market_branch"],
        )
        self.assertGreater(residual.value_coef, 0.0)

        saved = residual.state_dict()
        restored = deserialize_parameters(serialize_parameters(saved))
        assert_tree_equal(self, saved, restored)
        reloaded = BoundedResidualActorCritic(
            self.input_dim,
            self.unit_feature_dim,
            self.market_feature_dim,
            seed=999,
        )
        reloaded.load_state_dict(restored)
        reloaded_output = reloaded(
            self.state_features, self.unit_features, self.market_features
        )
        for expected, actual in zip(output, reloaded_output):
            np.testing.assert_array_equal(expected, actual)

        with self.assertRaises(ValueError):
            BoundedResidualActorCritic(
                self.input_dim,
                self.unit_feature_dim,
                self.market_feature_dim,
                value_coef=0.0,
            )


if __name__ == "__main__":
    unittest.main()
