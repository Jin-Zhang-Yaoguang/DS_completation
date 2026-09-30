import unittest

from collect_factorized_rollouts import relative_public_enterprise_potential


class OpponentImpactRewardTest(unittest.TestCase):
    def test_opponent_price_windfall_is_penalized_without_private_state(self):
        observation = {
            "player": 0,
            "farms": [
                {"money": 3000, "hands": [], "unlocked_quadrants": ["NW"], "tiles": [[None]]},
                {"money": 3000, "hands": [], "unlocked_quadrants": ["NW"], "tiles": [[{
                    "kind": "PLANT", "crop": "TOMATO", "yield_units": 5,
                }]]},
            ],
            "market": {"prices": {"TOMATO": 60}},
        }
        before = relative_public_enterprise_potential(observation, 1.0)
        observation["market"]["prices"]["TOMATO"] = 200
        after = relative_public_enterprise_potential(observation, 1.0)
        self.assertLess(after, before)

    def test_zero_weight_ignores_opponent_public_farm(self):
        observation = {
            "player": 0,
            "farms": [
                {"money": 3000, "hands": [], "unlocked_quadrants": ["NW"], "tiles": [[None]]},
                {"money": 3000, "hands": [], "unlocked_quadrants": ["NW"], "tiles": [[None]]},
            ],
            "market": {"prices": {}},
        }
        before = relative_public_enterprise_potential(observation, 0.0)
        observation["farms"][1]["money"] = 1_000_000
        after = relative_public_enterprise_potential(observation, 0.0)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
