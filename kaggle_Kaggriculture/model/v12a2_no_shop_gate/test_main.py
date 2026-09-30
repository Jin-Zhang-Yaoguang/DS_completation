from __future__ import annotations

import unittest

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main


class NoShopGateTest(unittest.TestCase):
    def test_only_shop_filter_is_disabled(self) -> None:
        agent = main.make_agent()
        self.assertFalse(agent.config["require_unlocked_shop_demand"])
        for key, value in main.base.DEFAULT_CONFIG.items():
            if key != "require_unlocked_shop_demand":
                self.assertEqual(agent.config[key], value)

    def test_diagnostics_identify_single_removed_component(self) -> None:
        agent = main.make_agent()
        diagnostics = agent.diagnostics()
        self.assertEqual(diagnostics["model_id"], "v12a2_no_shop_gate")
        self.assertEqual(
            diagnostics["removed_component"], "unlocked-shop product gate"
        )


if __name__ == "__main__":
    unittest.main()
