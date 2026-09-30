from __future__ import annotations

import unittest

import numpy as np

from kaggle_Kaggriculture.model.v10_replay_lolo_router.router import (
    ShadowRouter,
    public_features,
)


def observation(step: int, private_marker: str = "secret") -> dict:
    empty_tiles = [[None for _ in range(10)] for _ in range(10)]
    farms = [
        {
            "money": 1000,
            "hands": [],
            "hires_today": 0,
            "unlocked_quadrants": [0],
            "tiles": empty_tiles,
        },
        {
            "money": 900,
            "hands": [],
            "hires_today": 0,
            "unlocked_quadrants": [0],
            "tiles": empty_tiles,
        },
    ]
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": farms,
        "market": {"prices": {}, "inventory": {}},
        "town": {"unlocked_shops": []},
        "private": {"marker": private_marker},
    }


class FakeExpert:
    def __init__(self, label: str, mismatch_step: int | None = None):
        self.label = label
        self.mismatch_step = mismatch_step
        self.calls: list[int] = []

    def __call__(self, obs, configuration=None):
        step = int(obs["step"])
        self.calls.append(step)
        label = "mismatch" if step == self.mismatch_step else "same"
        if step >= 72:
            label = self.label
        return {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1, label]]}


class ChooseLast:
    last_reason = "test_choose_last"

    def choose(self, obs, eligible):
        return eligible[-1]


class RouterBoundaryTest(unittest.TestCase):
    def test_private_fields_never_change_public_features(self) -> None:
        left = public_features(observation(72, "left"))
        right = public_features(observation(72, "right"))
        np.testing.assert_array_equal(left, right)

    def test_step_72_is_first_selected_action_and_selection_is_sticky(self) -> None:
        anchor = FakeExpert("anchor")
        other = FakeExpert("other")
        router = ShadowRouter(
            "router",
            {"anchor": anchor, "other": other},
            {"anchor": {}, "other": {}},
            "anchor",
            ChooseLast(),
            switch_step=72,
        )
        for step in range(72):
            action = router(observation(step))
            self.assertEqual(action["market"][0][3], "same")
        selected = router(observation(72))
        self.assertEqual(selected["market"][0][3], "other")
        self.assertEqual(router.diagnostics()["selected"], "other")
        self.assertTrue(router.diagnostics()["prefix_complete"])
        self.assertEqual(anchor.calls, list(range(73)))
        self.assertEqual(other.calls, list(range(73)))

    def test_prefix_mismatch_excludes_complete_expert(self) -> None:
        anchor = FakeExpert("anchor")
        other = FakeExpert("other", mismatch_step=5)
        router = ShadowRouter(
            "router",
            {"anchor": anchor, "other": other},
            {"anchor": {}, "other": {}},
            "anchor",
            ChooseLast(),
            switch_step=72,
        )
        for step in range(73):
            result = router(observation(step))
        self.assertEqual(result["market"][0][3], "anchor")
        diagnostics = router.diagnostics()
        self.assertEqual(diagnostics["selection_eligible"], ["anchor"])
        self.assertEqual(diagnostics["prefix_first_mismatch"]["other"], 5)


if __name__ == "__main__":
    unittest.main()
