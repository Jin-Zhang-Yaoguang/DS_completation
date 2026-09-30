import unittest

import action_space as space


def observation():
    tiles = [[None for _ in range(10)] for _ in range(10)]
    return {
        "player": 0,
        "farms": [
            {"money": 3000, "farmer": [4, 4], "hands": [], "hires_today": 0, "unlocked_quadrants": ["NW"], "tiles": tiles},
            {"money": 3000, "farmer": [4, 4], "hands": [], "hires_today": 0, "unlocked_quadrants": ["NW"], "tiles": tiles},
        ],
        "private": {
            "shed": {item: 0 for item in space.ITEMS},
            "seeds": {**{item: 0 for item in space.CROPS}, "WHEAT": 2},
            "inventories": [{}],
        },
        "market": {"prices": dict(space.BASE_PRICES), "inventory": {item: 10000 for item in space.PRODUCTS}},
        "town": {"unlocked_shops": []},
    }


class ActionSpaceTest(unittest.TestCase):
    def test_plant_roundtrip(self):
        obs = observation()
        source = {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": [["BUY_SEED", "WHEAT", 8]]}
        encoded = space.encode_action(obs, source)
        self.assertEqual(space.decode_action(obs, encoded), source)

    def test_illegal_unit_token_fails_to_pass(self):
        obs = observation()
        token = space.UNIT_INDEX["HARVEST"]
        self.assertEqual(space.decode_unit(obs, 0, token), ["PASS"])

    def test_market_shadow_respects_budget(self):
        obs = observation()
        shadow = space.market_shadow(obs)
        order = space.apply_market_token(shadow, space.MARKET_INDEX["BUY_ANIMAL:COW"], 100)
        self.assertEqual(order, ["BUY_ANIMAL", "COW", 7])
        self.assertEqual(shadow["money"], 200.0)

    def test_hire_is_masked_at_actor_unit_capacity(self):
        obs = observation()
        obs["farms"][0]["hands"] = [[4, 4] for _ in range(15)]
        obs["private"]["inventories"] = [{} for _ in range(16)]
        shadow = space.market_shadow(obs)
        self.assertFalse(space.market_legal_mask(shadow)[space.MARKET_INDEX["HIRE"]])

    def test_quantity_candidates_cover_every_executable_supervised_value(self):
        mask = space.quantity_candidate_mask(7)
        self.assertEqual([index for index, enabled in enumerate(mask) if enabled], [1, 2, 3, 4, 5, 6, 7])

    def test_same_turn_place_enables_sell(self):
        obs = observation()
        obs["private"]["inventories"][0]["FERTILIZER"] = 3
        source = {
            "farmer": ["PLACE", "FERTILIZER", 3],
            "hands": [],
            "market": [["SELL", "FERTILIZER", 3]],
        }
        encoded = space.encode_action(obs, source)
        self.assertEqual(space.decode_action(obs, encoded), source)


if __name__ == "__main__":
    unittest.main()
