import unittest

import jax
import jax.numpy as jnp

import action_space as space
import features
from model_factorized import FactorizedHMoEActorCritic, NUM_EXPERTS


class FactorizedModelTest(unittest.TestCase):
    def test_output_shapes_and_closed_opponent_gate(self):
        model = FactorizedHMoEActorCritic()
        inputs = {
            "global_state": jnp.zeros((2, features.GLOBAL_FEATURES)),
            "board": jnp.zeros((2, 2, features.BOARD_SIZE, features.BOARD_SIZE, features.BOARD_CHANNELS)),
            "units": jnp.zeros((2, features.MAX_UNITS, features.UNIT_FEATURES)),
            "unit_mask": jnp.ones((2, features.MAX_UNITS)),
        }
        variables = model.init(jax.random.key(7), **inputs)
        output = model.apply(variables, **inputs)
        self.assertEqual(output["unit_router_logits"].shape, (2, NUM_EXPERTS))
        self.assertEqual(output["market_router_logits"].shape, (2, NUM_EXPERTS))
        self.assertEqual(output["unit_logits"].shape, (2, NUM_EXPERTS, features.MAX_UNITS, len(space.UNIT_TOKENS)))
        self.assertEqual(output["market_logits"].shape, (2, NUM_EXPERTS, space.MAX_MARKET_SLOTS, len(space.MARKET_TOKENS)))
        self.assertTrue(bool(jnp.all(output["opponent_gate"] < 0.02)))


if __name__ == "__main__":
    unittest.main()
