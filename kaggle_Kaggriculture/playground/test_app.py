"""Integration tests for the local Kaggriculture playground."""

import unittest

from app import app


class PlaygroundTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_page_and_initial_state(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Kaggriculture 人机训练场", page.get_data(as_text=True))

        state = self.client.get("/api/state").get_json()
        self.assertEqual(state["bot"]["version"], "market-route-moe-v3-hinge")
        self.assertIn(state["game"]["humanPlayer"], (0, 1))
        self.assertIn("private", state)
        self.assertEqual(len(state["farms"]), 2)

    def test_human_can_step_against_latest_bot(self):
        created = self.client.post(
            "/api/new",
            json={"seed": 7, "days": 1, "humanPlayer": 0},
        ).get_json()
        self.assertEqual(created["game"]["step"], 0)

        stepped = self.client.post(
            "/api/step",
            json={
                "farmer": ["PASS"],
                "hands": [],
                "market": [["BUY_SEED", "WHEAT", 1]],
            },
        )
        self.assertEqual(stepped.status_code, 200)
        state = stepped.get_json()
        self.assertEqual(state["game"]["step"], 1)
        self.assertEqual(state["lastActions"]["human"]["market"], [["BUY_SEED", "WHEAT", 1]])
        self.assertTrue(state["lastActions"]["bot"]["farmer"])
        self.assertEqual(state["history"][-1]["step"], 1)

    def test_invalid_action_and_short_game(self):
        self.client.post("/api/new", json={"seed": 11, "days": 1, "humanPlayer": 1})
        invalid = self.client.post(
            "/api/step",
            json={"farmer": ["TELEPORT"], "hands": [], "market": []},
        )
        self.assertEqual(invalid.status_code, 400)

        state = self.client.post("/api/fast-forward", json={"turns": 24}).get_json()
        self.assertTrue(state["game"]["done"])
        self.assertIn(state["game"]["result"], {"win", "loss", "tie"})
        self.assertLessEqual(len(state["history"]), 12)


if __name__ == "__main__":
    unittest.main()
