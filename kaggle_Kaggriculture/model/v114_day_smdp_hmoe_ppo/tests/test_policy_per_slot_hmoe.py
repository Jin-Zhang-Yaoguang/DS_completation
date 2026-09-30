import tempfile
import unittest
from pathlib import Path
from unittest import mock

from flax import serialization
import numpy as np

import policy_per_slot_hmoe as policy_module


space = policy_module.space


class _FakeModel:
    def __init__(self, timed=False):
        self.timed = timed

    def apply(self, *args, **kwargs):  # pragma: no cover - inference is stubbed below.
        raise AssertionError("test should replace _conditioned")


def _observation(*, day=0, hour=0, money=3000, hands=0):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    positions = [[4, 4] for _ in range(hands)]
    return {
        "day": day,
        "hour": hour,
        "player": 0,
        "farms": [
            {
                "money": money, "farmer": [4, 4], "hands": positions,
                "hires_today": 0, "unlocked_quadrants": ["NW"], "tiles": tiles,
            },
            {
                "money": 3000, "farmer": [4, 4], "hands": [],
                "hires_today": 0, "unlocked_quadrants": ["NW"], "tiles": tiles,
            },
        ],
        "private": {
            "shed": {item: 0 for item in space.ITEMS},
            "seeds": {**{item: 0 for item in space.CROPS}, "WHEAT": 2},
            "inventories": [{} for _ in range(1 + hands)],
        },
        "market": {
            "prices": dict(space.BASE_PRICES),
            "inventory": {item: 10000 for item in space.PRODUCTS},
        },
        "town": {"unlocked_shops": []},
    }


def _model_output():
    unit_roles = np.zeros((3, policy_module.features.MAX_UNITS, 4), dtype=np.float32)
    market_roles = np.zeros((3, space.MAX_MARKET_SLOTS, 3), dtype=np.float32)
    unit_logits = np.full(
        (3, policy_module.features.MAX_UNITS, len(space.UNIT_TOKENS)),
        -20.0, dtype=np.float32,
    )
    unit_quantities = np.zeros(
        (3, policy_module.features.MAX_UNITS, space.QUANTITY_DIM),
        dtype=np.float32,
    )
    market_logits = np.full(
        (3, space.MAX_MARKET_SLOTS, len(space.MARKET_TOKENS)),
        -20.0, dtype=np.float32,
    )
    market_quantities = np.zeros(
        (3, space.MAX_MARKET_SLOTS, space.QUANTITY_DIM),
        dtype=np.float32,
    )
    market_logits[..., space.MARKET_INDEX["STOP"]] = 0.0
    return {
        "unit_role_logits": unit_roles,
        "market_role_logits": market_roles,
        "unit_logits": unit_logits,
        "unit_quantity_logits": unit_quantities,
        "market_logits": market_logits,
        "market_quantity_logits": market_quantities,
    }


class TestPerSlotOptionRolePolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.checkpoint = Path(self.temp.name) / "v114.msgpack"
        self._write_checkpoint("v114_per_slot_hmoe_bc_v1", False)

    def tearDown(self):
        self.temp.cleanup()

    def _write_checkpoint(self, model_id, inherits):
        self.checkpoint.write_bytes(serialization.msgpack_serialize({
            "model_id": model_id,
            "inherits_v113_checkpoint": inherits,
            "params": {},
        }))

    def _policy(self, **kwargs):
        with mock.patch.object(policy_module, "PerSlotOptionRoleHMoE", _FakeModel):
            return policy_module.PerSlotOptionRolePolicy(
                self.checkpoint, option_id=2, **kwargs
            )

    def test_checkpoint_must_be_v114_and_not_inherit_v113(self):
        self._write_checkpoint("v113_old_model", False)
        with self.assertRaisesRegex(ValueError, "V114"):
            policy_module.PerSlotOptionRolePolicy(self.checkpoint, 0)
        self._write_checkpoint("v114_per_slot_hmoe_bc_v1", True)
        with self.assertRaisesRegex(ValueError, "inherit"):
            policy_module.PerSlotOptionRolePolicy(self.checkpoint, 0)

    def test_fixed_option_uses_independent_role_per_unit_slot(self):
        policy = self._policy()
        output = _model_output()
        output["unit_role_logits"][2, 0, 1] = 8.0
        output["unit_role_logits"][2, 1, 2] = 8.0
        output["unit_logits"][2, 0, space.UNIT_INDEX["PLANT:WHEAT"]] = 9.0
        output["unit_logits"][2, 1, space.UNIT_INDEX["NORTH"]] = 9.0
        prefixes = []

        def conditioned(obs, unit_tokens, unit_quantities, *market_prefix):
            prefixes.append(np.asarray(unit_tokens).copy())
            return output

        policy._conditioned = conditioned
        action = policy.act(_observation(hands=1))
        self.assertEqual(action["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(action["hands"], [["NORTH"]])
        self.assertEqual(policy.unit_role_usage, {1: 1, 2: 1})
        self.assertEqual(prefixes[0][0], space.UNIT_INDEX["PASS"])
        self.assertEqual(prefixes[1][0], space.UNIT_INDEX["PLANT:WHEAT"])

    def test_illegal_high_logit_is_masked(self):
        policy = self._policy()
        output = _model_output()
        output["unit_role_logits"][2, 0, 1] = 8.0
        output["unit_logits"][2, 0, space.UNIT_INDEX["HARVEST"]] = 100.0
        output["unit_logits"][2, 0, space.UNIT_INDEX["PLANT:WHEAT"]] = 9.0
        policy._conditioned = lambda *args: output
        self.assertEqual(policy.act(_observation())["farmer"], ["PLANT", "WHEAT"])

    def test_day_hour_terminal_cutoff_blocks_buy(self):
        policy = self._policy(terminal_buy_cutoff=671)
        output = _model_output()
        output["market_role_logits"][2, 0, 2] = 8.0
        output["market_logits"][2, 0, space.MARKET_INDEX["BUY_SEED:WHEAT"]] = 9.0
        policy._conditioned = lambda *args: output
        action = policy.act(_observation(day=27, hour=23))
        self.assertEqual(action["market"], [])
        self.assertEqual(policy.last_step, 27 * 24 + 23)

    def test_cash_reserve_and_worker_cap_mask_spending(self):
        policy = self._policy(cash_reserve=6.0, worker_cap=0)
        obs = policy_module.with_observation_step(_observation(money=15, hour=0))
        legal = policy._market_legal_mask(obs, space.market_shadow(obs))
        self.assertFalse(legal[space.MARKET_INDEX["BUY_SEED:WHEAT"]])
        self.assertFalse(legal[space.MARKET_INDEX["HIRE"]])
        self.assertTrue(legal[space.MARKET_INDEX["STOP"]])

    def test_role_first_router_and_slot_action_tensor_are_supported(self):
        output = _model_output()
        output["unit_role_logits"] = output["unit_role_logits"].transpose(0, 2, 1)
        role_logits = policy_module._role_logits_for_slot(output, "unit", 1, 3)
        action_logits = policy_module._action_logits_for_slot(
            output, "unit", 1, 2, 3
        )
        self.assertEqual(role_logits.shape, (4,))
        self.assertEqual(action_logits.shape, (len(space.UNIT_TOKENS),))


if __name__ == "__main__":
    unittest.main()
