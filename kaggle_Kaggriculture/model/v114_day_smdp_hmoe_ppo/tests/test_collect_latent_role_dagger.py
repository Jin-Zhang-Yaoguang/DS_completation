from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from flax import serialization
import numpy as np


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import action_space as space  # noqa: E402
import collect_latent_role_dagger as collector  # noqa: E402
import merge_latent_dagger_dataset as merger  # noqa: E402


def _sha(path: Path) -> str:
    return collector.sha256_file(path)


class _FakePolicy:
    calls: list[dict] = []

    def __init__(self, checkpoint, option_id, **kwargs):
        self.option_id = int(option_id)
        type(self).calls.append({
            "checkpoint": str(checkpoint),
            "option_id": self.option_id,
            **kwargs,
        })

    def __call__(self, obs, configuration=None):
        return {
            "source": "candidate",
            "option_id": self.option_id,
            "step": int(obs["step"]),
        }


class _FakeEnv:
    executed: list[list[dict]] = []

    def __init__(self, seed: int):
        self.configuration = {"seed": int(seed), "episodeSteps": 3}
        self.steps = []
        self.done = False
        self.step_index = 0
        self.state = [
            SimpleNamespace(reward=0.0, status="ACTIVE"),
            SimpleNamespace(reward=0.0, status="ACTIVE"),
        ]

    def reset(self, agents):
        self.done = False
        self.step_index = 0
        self.steps = []
        return self.state

    def step(self, actions):
        type(self).executed.append(actions)
        self.steps.append(actions)
        self.step_index += 1
        if self.step_index == 2:
            self.done = True
            self.state = [
                SimpleNamespace(reward=4000.0, status="DONE"),
                SimpleNamespace(reward=2000.0, status="DONE"),
            ]


def _fake_observations(env: _FakeEnv):
    return [
        {"player": seat, "step": env.step_index}
        for seat in (0, 1)
    ]


def _fake_labelled_row(obs, action, expert, seed, seat):
    assert action["source"].startswith("teacher:")
    return {
        "global": np.asarray([obs["step"], seat], dtype=np.float32),
        "board": np.asarray([seed % 7, obs["step"]], dtype=np.float32),
        "units": np.asarray([seat, 1], dtype=np.float32),
        "unit_mask": np.asarray([1, 0], dtype=np.uint8),
        "unit_tokens": np.asarray(
            [space.UNIT_INDEX["PASS"], space.UNIT_INDEX["PASS"]],
            dtype=np.int16,
        ),
        "unit_quantities": np.zeros(2, dtype=np.int16),
        "market_tokens": np.asarray(
            [space.MARKET_INDEX["STOP"]] * 3, dtype=np.int16
        ),
        "market_quantities": np.zeros(3, dtype=np.int16),
        "market_mask": np.asarray([1, 0, 0], dtype=np.uint8),
        "expert": np.int16(expert),
        "value": np.float32(0.0),
        "split": np.int8(0),
        "episode": np.int64(seed),
        "step": np.int16(obs["step"]),
        "seat": np.int8(seat),
    }, False


class TestLatentRoleDaggerCollector(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _checkpoint(self, **overrides) -> Path:
        path = self.root / "candidate.msgpack"
        payload = {
            "model_id": "v114_day_smdp_hmoe_ppo_latent_role_bc_v6",
            "architecture": "latent-role-hmoe-v1",
            "inherits_v113_checkpoint": False,
            "online_historical_agent_fallback": False,
            "teacher_role_conditions_action_decoder": False,
            "params": {},
        }
        payload.update(overrides)
        path.write_bytes(serialization.msgpack_serialize(payload))
        return path

    def _registry(self, *, corrupt_v76_sha=False) -> Path:
        members = []
        definitions = (
            (
                "gold_v76_adjacent_buy",
                "procurement-slot-ordering",
                "v76.py",
            ),
            (
                "gold_v19_route_hmoe",
                "production-route-switching",
                "v19.py",
            ),
            (
                "gold_v21_top_meta",
                "first-shop-meta-routing",
                "v21.py",
            ),
        )
        for member_id, family, filename in definitions:
            artifact = self.root / filename
            artifact.write_text(f"# {member_id}\n", encoding="utf-8")
            members.append({
                "id": member_id,
                "kind": "agent",
                "path": filename,
                "sha256": (
                    "0" * 64
                    if corrupt_v76_sha and member_id == "gold_v76_adjacent_buy"
                    else _sha(artifact)
                ),
                "training_enabled": True,
                "training_layer": "gold_train",
                "gold_split": "train",
                "behavior_family": family,
            })
        # Deliberately missing files: an implementation that touches either
        # forbidden split will fail this test.
        members.extend([
            {
                "id": "gold_dev_trap",
                "kind": "agent",
                "path": "missing-dev.py",
                "sha256": "1" * 64,
                "training_enabled": False,
                "training_layer": None,
                "gold_split": "dev",
                "behavior_family": "terminal",
            },
            {
                "id": "gold_blind_trap",
                "kind": "agent",
                "path": "missing-blind.py",
                "sha256": "2" * 64,
                "training_enabled": False,
                "training_layer": None,
                "gold_split": "blind",
                "behavior_family": "market",
            },
        ])
        path = self.root / "registry.json"
        path.write_text(json.dumps({
            "schema": collector.REGISTRY_SCHEMA,
            "path_base": ".",
            "members": members,
        }), encoding="utf-8")
        return path

    def test_checkpoint_contract_is_v114_latent_frozen_and_fallback_free(self):
        metadata = collector.checkpoint_metadata(self._checkpoint())
        self.assertTrue(metadata["frozen"])
        self.assertFalse(metadata["inherits_v113_checkpoint"])
        self.assertFalse(metadata["online_historical_agent_fallback"])
        cases = (
            ({"model_id": "v114_other"}, "latent-role"),
            ({"inherits_v113_checkpoint": True}, "inherit"),
            ({"online_historical_agent_fallback": True}, "fallback"),
            ({"teacher_role_conditions_action_decoder": True}, "teacher roles"),
        )
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, message):
                    collector.checkpoint_metadata(self._checkpoint(**overrides))

    def test_registry_exact_allowlist_verifies_sha_without_touching_dev_blind(self):
        metadata, teachers = collector.load_required_gold_train_teachers(
            self._registry()
        )
        self.assertEqual(set(teachers), collector.REQUIRED_TEACHER_IDS)
        self.assertEqual(metadata["selected_gold_split"], "train")
        self.assertFalse(metadata["dev_blind_selected"])
        self.assertTrue(all(row["gold_split"] == "train" for row in teachers.values()))
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            collector.load_required_gold_train_teachers(
                self._registry(corrupt_v76_sha=True)
            )

    def test_teacher_assignment_is_fixed_for_option1_and_seed_balanced_for_option2(self):
        seeds = list(range(11490000, 11490008))
        self.assertEqual(
            {collector.teacher_id_for(1, seed) for seed in seeds},
            {"gold_v76_adjacent_buy"},
        )
        counts = Counter(collector.teacher_id_for(2, seed) for seed in seeds)
        self.assertEqual(counts["gold_v19_route_hmoe"], 4)
        self.assertEqual(counts["gold_v21_top_meta"], 4)
        with self.assertRaisesRegex(ValueError, "option_id"):
            collector.teacher_id_for(0, seeds[0])

    def test_collect_executes_candidate_only_and_emits_v6_compatible_rows(self):
        checkpoint = self._checkpoint()
        registry_path = self._registry()
        _, teachers = collector.load_required_gold_train_teachers(registry_path)
        args = argparse.Namespace(
            checkpoint=checkpoint,
            registry=registry_path,
            seed_start=11490000,
            seeds=1,
            opponent=["builtin:starter", "builtin:pass"],
            campaign="unit-test-candidate-state-dagger",
            ledger=self.root / "seed-ledger.json",
        )
        _FakePolicy.calls = []
        _FakeEnv.executed = []
        built_teachers = []
        resolved_opponents = []

        def fake_build(assignment, unique_name):
            built_teachers.append(assignment.member_id)
            return lambda obs, configuration=None: {
                "source": f"teacher:{assignment.member_id}",
                "step": int(obs["step"]),
            }

        def fake_resolve(opponent_id, unique_name):
            resolved_opponents.append(opponent_id)
            return lambda obs, configuration=None: {
                "source": f"opponent:{opponent_id}",
                "step": int(obs["step"]),
            }

        def fake_canonical(obs, raw):
            self.assertTrue(raw["source"].startswith("teacher:"))
            return raw, {
                "raw_unit_unknown": 0,
                "raw_market_unknown": 0,
                "canonical_unit_unknown": 0,
                "canonical_market_unknown": 0,
                "changed": 0,
            }

        patches = (
            mock.patch.object(collector, "checkpoint_metadata", return_value={
                "path": str(checkpoint),
                "sha256": _sha(checkpoint),
                "model_id": "v114_latent_role_test",
                "frozen": True,
                "inherits_v113_checkpoint": False,
                "online_historical_agent_fallback": False,
                "teacher_role_conditions_action_decoder": False,
            }),
            mock.patch.object(
                collector,
                "load_required_gold_train_teachers",
                return_value=(
                    {
                        "path": str(registry_path),
                        "sha256": _sha(registry_path),
                        "schema": collector.REGISTRY_SCHEMA,
                        "selected_gold_split": "train",
                        "selected_teacher_ids": sorted(teachers),
                        "dev_blind_selected": False,
                    },
                    teachers,
                ),
            ),
            mock.patch.object(collector, "LatentRoleOptionPolicy", _FakePolicy),
            mock.patch.object(collector, "build_opponent", side_effect=fake_build),
            mock.patch.object(collector, "resolve_opponent", side_effect=fake_resolve),
            mock.patch.object(
                collector,
                "make",
                side_effect=lambda name, configuration, debug: _FakeEnv(
                    configuration["seed"]
                ),
            ),
            mock.patch.object(collector, "agent_observations", _fake_observations),
            mock.patch.object(
                collector,
                "call_opponent",
                side_effect=lambda agent, obs, configuration: agent(obs, configuration),
            ),
            mock.patch.object(collector, "canonical_action", side_effect=fake_canonical),
            mock.patch.object(collector, "labelled_row", side_effect=_fake_labelled_row),
            mock.patch.object(
                collector.space, "functional_unit_expert_label", return_value=1
            ),
            mock.patch.object(
                collector.space, "functional_market_expert_label", return_value=2
            ),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                patches[5], patches[6], patches[7], patches[8], patches[9], \
                patches[10]:
            arrays, report = collector.collect(args)

        # One seed, options 1/2, both seats: four independently reloaded games.
        self.assertEqual(len(_FakePolicy.calls), 4)
        self.assertEqual(len(built_teachers), 4)
        self.assertEqual(len(resolved_opponents), 4)
        self.assertEqual([row["option_id"] for row in _FakePolicy.calls], [1, 1, 2, 2])
        for call in _FakePolicy.calls:
            self.assertEqual(call["worker_cap"], 4)
            self.assertEqual(call["cash_reserve"], 0.0)
            self.assertEqual(call["terminal_buy_cutoff"], 671)
        self.assertEqual(set(resolved_opponents), {"builtin:starter"})
        self.assertEqual(built_teachers[:2], ["gold_v76_adjacent_buy"] * 2)
        self.assertEqual(
            built_teachers[2:],
            [collector.teacher_id_for(2, args.seed_start)] * 2,
        )

        # The environment sees candidate and opponent actions only.
        self.assertEqual(len(_FakeEnv.executed), 8)
        executed_sources = [
            action["source"]
            for pair in _FakeEnv.executed
            for action in pair
        ]
        self.assertFalse(any(source.startswith("teacher:") for source in executed_sources))
        self.assertTrue(any(source == "candidate" for source in executed_sources))

        required = {
            "global", "board", "units", "unit_mask",
            "unit_tokens", "unit_quantities", "market_tokens",
            "market_quantities", "market_mask", "value",
            "teacher_family", "teacher_sha256", "option_id",
            "unit_roles", "market_roles", "terminal_flag",
        }
        self.assertTrue(required.issubset(arrays))
        self.assertEqual(set(arrays), set(collector.V6_SOURCE_KEYS))
        self.assertEqual(arrays["global"].dtype, np.float16)
        self.assertEqual(len(arrays["option_id"]), 8)
        self.assertEqual(set(arrays["option_id"].tolist()), {1, 2})
        self.assertEqual(
            set(arrays["episode"].tolist()),
            {
                collector.episode_group_id(args.seed_start, 1),
                collector.episode_group_id(args.seed_start, 2),
            },
        )
        self.assertTrue(np.all(arrays["market_mask"] == 1))
        self.assertTrue(
            np.all(arrays["market_tokens"] == space.MARKET_INDEX["STOP"])
        )
        self.assertTrue(np.all(arrays["market_quantities"] == 0))
        self.assertFalse(any(array.dtype == object for array in arrays.values()))
        self.assertEqual(set(arrays), set(merger.BASE_KEYS))
        normalised, added = merger._normalise_source(
            arrays, "unit-test-dagger", require_derived=True
        )
        self.assertEqual(added, 0)
        self.assertEqual(len(normalised["episode"]), len(arrays["episode"]))

        self.assertEqual(report["games"], 4)
        self.assertEqual(report["rows"], 8)
        self.assertEqual(
            report["candidate_summary"]["overall"]["wdl"],
            {"wins": 2, "draws": 0, "losses": 2},
        )
        self.assertEqual(
            report["candidate_summary"]["overall"]["catastrophe_games"], 2
        )
        self.assertTrue(
            report["execution_contract"]["dual_seat_same_seed_same_opponent"]
        )
        self.assertEqual(report["execution_contract"]["teacher_execution"],
                         "never; canonical supervision query only")
        self.assertFalse(report["execution_contract"]["historical_agent_fallback"])
        self.assertFalse(report["isolation_contract"]["gold_dev_used"])
        self.assertFalse(report["isolation_contract"]["gold_blind_used"])
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        self.assertEqual(ledger["records"][str(args.seed_start)]["status"], "exposed")

    def test_schedule_keeps_one_opponent_for_both_seats_and_rejects_bad_input(self):
        schedule = collector.build_seed_schedule(10, 3, ["a", "b"])
        self.assertEqual(
            [(row.seed, row.opponent_id) for row in schedule],
            [(10, "a"), (11, "b"), (12, "a")],
        )
        with self.assertRaisesRegex(ValueError, "positive"):
            collector.build_seed_schedule(10, 0, ["a"])
        with self.assertRaisesRegex(ValueError, "opponent"):
            collector.build_seed_schedule(10, 1, [])


if __name__ == "__main__":
    unittest.main()
