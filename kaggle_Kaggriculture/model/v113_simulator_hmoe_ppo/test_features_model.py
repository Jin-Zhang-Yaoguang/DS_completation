import json
from pathlib import Path
import unittest

import jax
import jax.numpy as jnp

import engine_parity
import features
from model import HMoEActorCritic, NUM_EXPERTS
import action_space as space


class FeaturesModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2] / "model_data" / "kaggriculture_episodes_index"
        row = engine_parity.discover(root, "1.32.7")[0]
        replay = json.loads(Path(row["path"]).read_text(encoding="utf-8"))
        cls.obs = replay["steps"][1][0]["observation"]

    def test_feature_shapes_and_private_boundary(self):
        encoded = features.encode_observation(self.obs)
        self.assertEqual(encoded["global"].shape, (features.GLOBAL_FEATURES,))
        self.assertEqual(encoded["board"].shape, (2, 10, 10, features.BOARD_CHANNELS))
        self.assertEqual(encoded["units"].shape, (features.MAX_UNITS, features.UNIT_FEATURES))
        self.assertEqual(int(encoded["unit_mask"].sum()), 1 + len(self.obs["farms"][0]["hands"]))

    def test_model_output_shapes(self):
        state = {key: jnp.asarray(value)[None] for key, value in features.encode_observation(self.obs).items()}
        model = HMoEActorCritic()
        variables = model.init(jax.random.key(113), state["global"], state["board"], state["units"], state["unit_mask"])
        output = model.apply(variables, state["global"], state["board"], state["units"], state["unit_mask"])
        self.assertEqual(output["router_logits"].shape, (1, NUM_EXPERTS))
        self.assertEqual(output["unit_logits"].shape, (1, NUM_EXPERTS, features.MAX_UNITS, len(space.UNIT_TOKENS)))
        self.assertEqual(output["market_logits"].shape, (1, NUM_EXPERTS, space.MAX_MARKET_SLOTS, len(space.MARKET_TOKENS)))
        self.assertEqual(output["value"].shape, (1,))


if __name__ == "__main__":
    unittest.main()
