import tempfile
import unittest
from pathlib import Path
from unittest import mock

from flax import serialization
import numpy as np

import evaluate_latent_role_options as evaluator
import policy_latent_role_hmoe as policy_module


space = policy_module.space


class _FakeModel:
    def __init__(self, timed=False):
        self.timed = timed

    def apply(self, *args, **kwargs):  # pragma: no cover - replaced per test.
        raise AssertionError("test must replace _apply_conditioned")


def _observation(*, day=0, hour=0, money=3000, hands=0):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    positions = [[4, 4] for _ in range(hands)]
    return {
        "day": day,
        "hour": hour,
        "player": 0,
        "farms": [
            {
                "money": money,
                "farmer": [4, 4],
                "hands": positions,
                "hires_today": 0,
                "unlocked_quadrants": ["NW"],
                "tiles": tiles,
            },
            {
                "money": 3000,
                "farmer": [4, 4],
                "hands": [],
                "hires_today": 0,
                "unlocked_quadrants": ["NW"],
                "tiles": tiles,
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
    unit_roles = np.zeros(
        (3, policy_module.features.MAX_UNITS, 4), dtype=np.float32
    )
    market_roles = np.zeros(
        (3, space.MAX_MARKET_SLOTS, 3), dtype=np.float32
    )
    unit_logits = np.full(
        (3, policy_module.features.MAX_UNITS, len(space.UNIT_TOKENS)),
        -20.0,
        dtype=np.float32,
    )
    unit_quantities = np.zeros(
        (3, policy_module.features.MAX_UNITS, space.QUANTITY_DIM),
        dtype=np.float32,
    )
    market_logits = np.full(
        (3, space.MAX_MARKET_SLOTS, len(space.MARKET_TOKENS)),
        -20.0,
        dtype=np.float32,
    )
    market_quantities = np.zeros(
        (3, space.MAX_MARKET_SLOTS, space.QUANTITY_DIM),
        dtype=np.float32,
    )
    unit_logits[..., space.UNIT_INDEX["PASS"]] = 0.0
    market_logits[..., space.MARKET_INDEX["STOP"]] = 0.0
    return {
        "unit_role_logits": unit_roles,
        "market_role_logits": market_roles,
        "unit_logits": unit_logits,
        "unit_quantity_logits": unit_quantities,
        "market_logits": market_logits,
        "market_quantity_logits": market_quantities,
    }


def _batched(output):
    return {key: value[None] for key, value in output.items()}


class TestLatentRoleOptionPolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.checkpoint = Path(self.temp.name) / "latent.msgpack"
        self._write_checkpoint()

    def tearDown(self):
        self.temp.cleanup()

    def _write_checkpoint(self, **overrides):
        payload = {
            "model_id": "v114_day_smdp_hmoe_ppo_latent_role_bc_v1",
            "inherits_v113_checkpoint": False,
            "online_historical_agent_fallback": False,
            "teacher_role_conditions_action_decoder": False,
            "params": {},
        }
        payload.update(overrides)
        self.checkpoint.write_bytes(serialization.msgpack_serialize(payload))

    def _policy(self, option_id=2, **kwargs):
        with mock.patch.object(policy_module, "LatentRoleHMoE", _FakeModel):
            return policy_module.LatentRoleOptionPolicy(
                self.checkpoint, option_id=option_id, **kwargs
            )

    def test_checkpoint_contract_rejects_inheritance_fallback_and_teacher_role(self):
        cases = (
            ({"model_id": "v114_other_model"}, "latent-role"),
            ({"inherits_v113_checkpoint": True}, "inherit"),
            ({"online_historical_agent_fallback": True}, "fallback"),
            ({"teacher_role_conditions_action_decoder": True}, "teacher roles"),
        )
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                self._write_checkpoint(**overrides)
                with self.assertRaisesRegex(ValueError, message):
                    policy_module.LatentRoleOptionPolicy(self.checkpoint, 0)

    def test_conditioned_call_never_passes_teacher_roles(self):
        policy = self._policy(option_id=1)
        calls = []

        def apply_without_roles(*args):
            calls.append(args)
            return _batched(_model_output())

        policy._apply_conditioned = apply_without_roles
        unit_tokens = np.full(
            policy_module.features.MAX_UNITS,
            space.UNIT_INDEX["PASS"],
            dtype=np.int16,
        )
        unit_quantities = np.zeros_like(unit_tokens)
        output = policy._conditioned(
            _observation(), unit_tokens, unit_quantities
        )
        # params + four encoded tensors + four action-prefix tensors.  There
        # are no unit_teacher_roles or market_teacher_roles arguments.
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 9)
        self.assertEqual(output["unit_logits"].shape[0], 3)

    def test_fixed_option_reforwards_executed_prefix_and_counts_latent_roles(self):
        policy = self._policy(option_id=2)
        output = _model_output()
        output["unit_role_logits"][2, 0, 1] = 9.0
        output["unit_role_logits"][2, 1, 3] = 9.0
        output["unit_logits"][2, 0, space.UNIT_INDEX["PLANT:WHEAT"]] = 10.0
        output["unit_logits"][2, 1, space.UNIT_INDEX["NORTH"]] = 10.0
        output["market_role_logits"][2, 0, 2] = 9.0
        prefixes = []

        def conditioned(obs, unit_tokens, unit_quantities, *market_prefix):
            prefixes.append((
                np.asarray(unit_tokens).copy(),
                tuple(np.asarray(value).copy() for value in market_prefix),
            ))
            return output

        policy._conditioned = conditioned
        action = policy.act(_observation(hands=1))
        self.assertEqual(action["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(action["hands"], [["NORTH"]])
        self.assertEqual(action["market"], [])
        self.assertEqual(policy.option_usage, {2: 1})
        self.assertEqual(policy.unit_role_usage, {1: 1, 3: 1})
        self.assertEqual(policy.market_role_usage, {2: 1})
        self.assertEqual(prefixes[0][0][0], space.UNIT_INDEX["PASS"])
        self.assertEqual(prefixes[1][0][0], space.UNIT_INDEX["PLANT:WHEAT"])

    def test_market_prefix_is_legal_and_stop_never_enters_tail(self):
        policy = self._policy(option_id=0)
        seen_market_prefixes = []

        def conditioned(obs, unit_tokens, unit_quantities, *market_prefix):
            output = _model_output()
            if not market_prefix:
                return output
            market_tokens = np.asarray(market_prefix[0])
            seen_market_prefixes.append(market_tokens.copy())
            if len(seen_market_prefixes) == 1:
                output["market_logits"][
                    0, 0, space.MARKET_INDEX["BUY_SEED:WHEAT"]
                ] = 10.0
            return output

        policy._conditioned = conditioned
        action = policy.act(_observation(money=3000))
        self.assertEqual(action["market"], [["BUY_SEED", "WHEAT", 1]])
        self.assertEqual(len(seen_market_prefixes), 2)
        self.assertEqual(
            seen_market_prefixes[1][0], space.MARKET_INDEX["BUY_SEED:WHEAT"]
        )
        self.assertEqual(policy.market_turns, 1)
        self.assertEqual(policy.ten_slot_market_turns, 0)
        self.assertEqual(policy.market_sequence_lengths, {1: 1})

    def test_ten_slot_counter_counts_only_successfully_applied_orders(self):
        policy = self._policy(option_id=1)
        output = _model_output()
        output["market_logits"][
            1, :, space.MARKET_INDEX["BUY_SEED:WHEAT"]
        ] = 10.0
        policy._conditioned = lambda *args: output
        action = policy.act(_observation(money=1_000_000))
        self.assertEqual(len(action["market"]), space.MAX_MARKET_SLOTS)
        self.assertEqual(policy.market_turns, 1)
        self.assertEqual(policy.ten_slot_market_turns, 1)
        self.assertEqual(policy.ten_slot_rate, 1.0)

    def test_official_masks_keep_reserve_worker_cap_and_terminal_cutoff(self):
        policy = self._policy(
            cash_reserve=6.0, worker_cap=0, terminal_buy_cutoff=671
        )
        early = policy_module.with_observation_step(
            _observation(money=15, hour=0)
        )
        legal = policy._market_legal_mask(early, space.market_shadow(early))
        self.assertFalse(legal[space.MARKET_INDEX["BUY_SEED:WHEAT"]])
        self.assertFalse(legal[space.MARKET_INDEX["HIRE"]])
        self.assertTrue(legal[space.MARKET_INDEX["STOP"]])

        terminal = policy_module.with_observation_step(
            _observation(day=27, hour=23, money=3000)
        )
        legal = policy._market_legal_mask(
            terminal, space.market_shadow(terminal)
        )
        self.assertFalse(legal[space.MARKET_INDEX["BUY_SEED:WHEAT"]])
        self.assertFalse(legal[space.MARKET_INDEX["BUY_LAND"]])
        self.assertTrue(legal[space.MARKET_INDEX["STOP"]])

    def test_option_summary_reports_wdl_reward_p10_catastrophe_and_ten_slot_rate(self):
        rows = [
            {
                "option_id": 1,
                "error": None,
                "statuses": ["DONE", "DONE"],
                "score": 1.0,
                "candidate_reward": 5000.0,
                "opponent_reward": 4000.0,
                "margin": 1000.0,
                "catastrophe": False,
                "market_turns": 100,
                "ten_slot_market_turns": 4,
            },
            {
                "option_id": 1,
                "error": None,
                "statuses": ["DONE", "DONE"],
                "score": 0.0,
                "candidate_reward": 2000.0,
                "opponent_reward": 3000.0,
                "margin": -1000.0,
                "catastrophe": True,
                "market_turns": 100,
                "ten_slot_market_turns": 6,
            },
        ]
        summary = evaluator.summarize_option(rows, 1)
        self.assertEqual(summary["wdl"], {"wins": 1, "draws": 0, "losses": 1})
        self.assertEqual(summary["mean_candidate_reward"], 3500.0)
        self.assertEqual(summary["p10_candidate_reward"], 2000.0)
        self.assertEqual(summary["catastrophe_games"], 1)
        self.assertEqual(summary["ten_slot_rate"], 0.05)


if __name__ == "__main__":
    unittest.main()
