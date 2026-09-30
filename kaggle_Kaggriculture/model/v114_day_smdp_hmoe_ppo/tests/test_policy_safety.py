import unittest

from policy_v114 import observation_step, reserve_shadow, with_observation_step


class TestPolicySafety(unittest.TestCase):
    def test_reserve_shadow_is_detached_and_clamped(self):
        source = {"money": 900.0, "shed": {"WHEAT": 3}}
        projected = reserve_shadow(source, 1000.0)
        self.assertEqual(projected["money"], 0.0)
        self.assertEqual(source["money"], 900.0)
        self.assertIsNot(projected, source)

    def test_reserve_shadow_keeps_spendable_cash(self):
        self.assertEqual(reserve_shadow({"money": 1500.0}, 750.0)["money"], 750.0)

    def test_official_day_hour_becomes_step(self):
        obs = {"day": 3, "hour": 7}
        self.assertEqual(observation_step(obs), 79)
        enriched = with_observation_step(obs)
        self.assertEqual(enriched["step"], 79)
        self.assertNotIn("step", obs)

    def test_explicit_step_is_preserved(self):
        obs = {"step": 11, "day": 9, "hour": 9}
        self.assertEqual(observation_step(obs), 11)
        self.assertIs(with_observation_step(obs), obs)


if __name__ == "__main__":
    unittest.main()
