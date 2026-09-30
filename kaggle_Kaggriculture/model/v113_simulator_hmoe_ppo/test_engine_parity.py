import unittest

import engine_parity


class EngineParityTest(unittest.TestCase):
    def test_select_samples_is_deterministic_and_unique(self):
        rows = [
            {"path": f"/{index}.json", "date": "2026-08-27", "episode_id": index, "module_version": "1.32.7"}
            for index in range(20)
        ]
        first = engine_parity.select_samples(rows, 8, 113)
        second = engine_parity.select_samples(list(reversed(rows)), 8, 113)
        self.assertEqual(first, second)
        self.assertEqual(len({row["episode_id"] for row in first}), 8)

    def test_clean_observation_removes_only_runtime_budget(self):
        source = {"step": 1, "remainingOverageTime": 60, "market": {"prices": {"WHEAT": 25}}}
        cleaned = engine_parity._clean_observation(source)
        self.assertEqual(cleaned, {"step": 1, "market": {"prices": {"WHEAT": 25}}})


if __name__ == "__main__":
    unittest.main()
