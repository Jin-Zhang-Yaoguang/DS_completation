from __future__ import annotations

import argparse
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
import collect_latent_self_imitation as collector  # noqa: E402
import merge_latent_dagger_dataset as merger  # noqa: E402


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
            "source": "candidate-raw",
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
        self.steps = []
        self.done = False
        self.step_index = 0
        return self.state

    def step(self, actions):
        type(self).executed.append(actions)
        self.steps.append(actions)
        self.step_index += 1
        if self.step_index == 2:
            self.done = True
            self.state = [
                SimpleNamespace(reward=4500.0, status="DONE"),
                SimpleNamespace(reward=2500.0, status="DONE"),
            ]


def _fake_observations(env: _FakeEnv):
    return [
        {"player": seat, "step": env.step_index}
        for seat in (0, 1)
    ]


def _fake_labelled_row(obs, action, expert, seed, seat):
    assert action["source"] == "candidate-canonical"
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


class TestLatentSelfImitationCollector(unittest.TestCase):
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
            "dataset_sha256": "a" * 64,
            "inherits_v113_checkpoint": False,
            "online_historical_agent_fallback": False,
            "teacher_role_conditions_action_decoder": False,
            "params": {},
        }
        payload.update(overrides)
        path.write_bytes(serialization.msgpack_serialize(payload))
        return path

    def _registry(self) -> Path:
        agent = self.root / "train-agent.py"
        agent.write_text("# train only\n", encoding="utf-8")
        members = [
            {
                "id": "anchor_starter",
                "kind": "builtin",
                "spec": "builtin:starter",
                "sha256": collector.builtin_sha256("builtin:starter"),
                "training_enabled": True,
                "training_layer": "anchor",
                "gold_split": None,
            },
            {
                "id": "gold_train_agent",
                "kind": "agent",
                "path": agent.name,
                "sha256": collector.sha256_file(agent),
                "training_enabled": True,
                "training_layer": "gold_train",
                "gold_split": "train",
            },
            # Missing artifacts are deliberate. Selecting either forbidden
            # member must fail before path resolution or hashing.
            {
                "id": "gold_dev_trap",
                "kind": "agent",
                "path": "missing-dev.py",
                "sha256": "1" * 64,
                "training_enabled": False,
                "training_layer": None,
                "gold_split": "dev",
            },
            {
                "id": "gold_blind_trap",
                "kind": "agent",
                "path": "missing-blind.py",
                "sha256": "2" * 64,
                "training_enabled": False,
                "training_layer": None,
                "gold_split": "blind",
            },
        ]
        path = self.root / "registry.json"
        path.write_text(json.dumps({
            "schema": collector.REGISTRY_SCHEMA,
            "path_base": ".",
            "members": members,
        }), encoding="utf-8")
        return path

    def test_checkpoint_and_terminal_value_contract(self):
        metadata = collector.checkpoint_metadata(self._checkpoint())
        self.assertTrue(metadata["frozen"])
        self.assertGreater(collector.terminal_value(1000.0), 1.0)
        self.assertLess(collector.terminal_value(-1000.0), -1.0)
        self.assertEqual(collector.terminal_value(0.0), 0.0)
        with self.assertRaisesRegex(ValueError, "inherit"):
            collector.checkpoint_metadata(
                self._checkpoint(inherits_v113_checkpoint=True)
            )

    def test_registry_loads_only_selected_training_members_and_forbids_dev_blind(self):
        metadata, selected = collector.load_training_opponents(
            self._registry(), ["anchor_starter", "gold_train_agent"]
        )
        self.assertEqual(set(selected), {"anchor_starter", "gold_train_agent"})
        self.assertFalse(metadata["gold_dev_artifacts_accessed"])
        self.assertFalse(metadata["gold_blind_artifacts_accessed"])
        for forbidden in ("gold_dev_trap", "gold_blind_trap"):
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(ValueError, "forbidden"):
                    collector.load_training_opponents(
                        self._registry(), [forbidden]
                    )

    def test_repeated_opponents_rotate_by_seed_and_keep_layer(self):
        members = {
            "a": {"training_layer": "anchor", "sha256": "a" * 64},
            "b": {"training_layer": "ppo_history", "sha256": "b" * 64},
        }
        schedule = collector.build_seed_schedule(20, 4, ["a", "b"], members)
        self.assertEqual(
            [(row.seed, row.opponent_id, row.layer) for row in schedule],
            [
                (20, "a", "anchor"),
                (21, "b", "ppo_history"),
                (22, "a", "anchor"),
                (23, "b", "ppo_history"),
            ],
        )
        parsed = collector.parser().parse_args([
            "--registry", "r.json", "--checkpoint", "c.msgpack",
            "--seed-start", "20", "--seeds", "2",
            "--opponent", "a", "--opponent", "b",
            "--campaign", "test", "--ledger", "ledger.json",
            "--output", "out.npz",
        ])
        self.assertEqual(parsed.opponent, ["a", "b"])

    def test_collect_executes_candidate_and_encodes_its_canonical_action(self):
        checkpoint = self._checkpoint()
        registry = self._registry()
        args = argparse.Namespace(
            checkpoint=checkpoint,
            registry=registry,
            seed_start=11493000,
            seeds=1,
            opponent=["anchor_starter", "gold_train_agent"],
            campaign="unit-test-self-imitation",
            ledger=self.root / "seed-ledger.json",
        )
        checkpoint_meta = collector.checkpoint_metadata(checkpoint)
        registry_meta, opponents = collector.load_training_opponents(
            registry, args.opponent
        )
        _FakePolicy.calls = []
        _FakeEnv.executed = []
        built_opponents = []
        canonical_sources = []

        def fake_build(member, unique_name):
            built_opponents.append(member)
            return lambda obs, configuration=None: {
                "source": "opponent",
                "step": int(obs["step"]),
            }

        def fake_canonical(obs, raw):
            canonical_sources.append(raw["source"])
            self.assertEqual(raw["source"], "candidate-raw")
            return {
                **raw,
                "source": "candidate-canonical",
            }, {
                "raw_unit_unknown": 0,
                "raw_market_unknown": 0,
                "canonical_unit_unknown": 0,
                "canonical_market_unknown": 0,
                "changed": 1,
            }

        patches = (
            mock.patch.object(
                collector, "checkpoint_metadata", return_value=checkpoint_meta
            ),
            mock.patch.object(
                collector, "load_training_opponents",
                return_value=(registry_meta, opponents),
            ),
            mock.patch.object(collector, "LatentRoleOptionPolicy", _FakePolicy),
            mock.patch.object(
                collector, "build_selected_opponent", side_effect=fake_build
            ),
            mock.patch.object(
                collector, "make",
                side_effect=lambda name, configuration, debug: _FakeEnv(
                    configuration["seed"]
                ),
            ),
            mock.patch.object(
                collector, "agent_observations", _fake_observations
            ),
            mock.patch.object(
                collector, "call_opponent",
                side_effect=lambda agent, obs, configuration: agent(
                    obs, configuration
                ),
            ),
            mock.patch.object(
                collector, "canonical_action", side_effect=fake_canonical
            ),
            mock.patch.object(
                collector, "labelled_row", side_effect=_fake_labelled_row
            ),
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

        self.assertEqual(len(_FakePolicy.calls), 4)
        self.assertEqual([call["option_id"] for call in _FakePolicy.calls], [1, 1, 2, 2])
        for call in _FakePolicy.calls:
            self.assertEqual(call["worker_cap"], 4)
            self.assertEqual(call["cash_reserve"], 0.0)
            self.assertEqual(call["terminal_buy_cutoff"], 671)
        self.assertEqual(len(built_opponents), 4)
        self.assertEqual(len(canonical_sources), 8)

        executed_sources = [
            action["source"]
            for pair in _FakeEnv.executed
            for action in pair
        ]
        self.assertIn("candidate-raw", executed_sources)
        self.assertNotIn("candidate-canonical", executed_sources)
        self.assertFalse(any("teacher" in source for source in executed_sources))

        self.assertEqual(set(arrays), set(collector.OUTPUT_KEYS))
        self.assertTrue(collector.V6_SOURCE_KEYS.issubset(arrays))
        self.assertEqual(arrays["global"].dtype, np.float16)
        self.assertEqual(arrays["value"].dtype, np.float32)
        self.assertEqual(arrays["episode_return"].dtype, np.float32)
        self.assertEqual(len(arrays["value"]), 8)
        self.assertTrue(np.array_equal(arrays["value"], arrays["episode_return"]))
        self.assertEqual(set(arrays["result"].tolist()), {"win", "loss"})
        self.assertEqual(set(arrays["source_kind"].tolist()), {
            collector.SOURCE_KIND,
        })
        self.assertEqual(set(arrays["candidate_reward"].tolist()), {2500.0, 4500.0})
        self.assertEqual(set(arrays["margin"].tolist()), {-2000.0, 2000.0})
        self.assertTrue(np.all(arrays["market_mask"] == 1))
        self.assertTrue(np.all(
            arrays["market_tokens"] == space.MARKET_INDEX["STOP"]
        ))
        self.assertFalse(any(array.dtype == object for array in arrays.values()))

        # The V6 core remains structurally consumable after the explicitly
        # requested terminal provenance fields are projected away.
        core = {key: arrays[key] for key in collector.V6_SOURCE_KEYS}
        normalised, added = merger._normalise_source(
            core, "unit-test-self-imitation", require_derived=True
        )
        self.assertEqual(added, 0)
        self.assertEqual(len(normalised["episode"]), 8)

        overall = report["candidate_summary"]["overall"]
        self.assertEqual(overall["wdl"], {
            "wins": 2, "draws": 0, "losses": 2,
        })
        self.assertEqual(overall["catastrophe_games"], 2)
        self.assertIn("anchor", report["candidate_summary"]["by_opponent_layer"])
        self.assertEqual(report["execution_contract"]["teacher_policy_calls"], 0)
        self.assertFalse(report["execution_contract"]["teacher_labels"])
        self.assertTrue(
            report["execution_contract"][
                "candidate_checkpoint_unchanged_during_rollout"
            ]
        )
        self.assertFalse(report["isolation_contract"]["gold_dev_used"])
        self.assertFalse(report["isolation_contract"]["gold_blind_used"])
        self.assertFalse(report["execution_contract"]["kaggle_submission"])
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        self.assertEqual(
            ledger["records"][str(args.seed_start)]["status"], "exposed"
        )

    def test_bad_schedule_inputs_fail_closed(self):
        members = {
            "a": {"training_layer": "anchor", "sha256": "a" * 64},
        }
        with self.assertRaisesRegex(ValueError, "positive"):
            collector.build_seed_schedule(10, 0, ["a"], members)
        with self.assertRaisesRegex(ValueError, "verified"):
            collector.build_seed_schedule(10, 1, ["missing"], members)


if __name__ == "__main__":
    unittest.main()
