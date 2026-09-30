from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
import tempfile
import unittest

from flax import serialization
import jax
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collect_event_program_warmstart import (  # noqa: E402
    DATASET_SCHEMA,
    QUALIFIED_LINES,
    action_indices,
    atomic_npz,
    build_dataset_arrays,
    qualified_decision_specs,
    validate_decision_specs,
)
from event_program import MacroDecision  # noqa: E402
from event_program_features import DECISION_HEAD_VALUES, MANAGER_FEATURE_DIM  # noqa: E402
from model_event_program_ppo import validate_checkpoint_metadata  # noqa: E402
from policy_random_event_program import RandomEventProgramPolicy  # noqa: E402
from train_event_program_manager_bc import (  # noqa: E402
    create_train_state,
    load_dataset,
    make_batch,
    seed_block_split,
    train_bc,
    train_one_step,
    validate_dataset,
)


def synthetic_rows(seeds=(9100, 9101, 9102, 9103)):
    samples = []
    games = []
    for seed in seeds:
        for spec in qualified_decision_specs():
            decision = MacroDecision(**spec["decision"])
            actions = action_indices(decision)
            line = decision.production_line.value
            for seat in (0, 1):
                reward = float(5000 + 100 * QUALIFIED_LINES.index(line) + seat)
                masks = {
                    name: np.ones((len(values),), dtype=np.bool_)
                    for name, values in DECISION_HEAD_VALUES.items()
                }
                features = np.zeros((MANAGER_FEATURE_DIM,), dtype=np.float32)
                features[0] = float(seed % 17) / 17.0
                features[1] = float(seat)
                features[2 + QUALIFIED_LINES.index(line)] = 1.0
                samples.append({
                    "features": features,
                    "masks": masks,
                    "actions": actions,
                    "day": 0,
                    "step": 0,
                    "target_legal": True,
                    "seed": seed,
                    "seat": seat,
                    "line": line,
                    "opponent_id": "builtin:starter",
                    "candidate_reward": reward,
                    "opponent_reward": 4000.0,
                    "margin": reward - 4000.0,
                    "catastrophe": False,
                    "error": "",
                })
                games.append({
                    "line": line,
                    "decision_name": spec["name"],
                    "seed": seed,
                    "seat": seat,
                    "opponent_id": "builtin:starter",
                    "candidate_reward": reward,
                    "opponent_reward": 4000.0,
                    "margin": reward - 4000.0,
                    "catastrophe": False,
                    "error": "",
                    "statuses": ["DONE", "DONE"],
                    "action_steps": 719,
                    "contract_violations": 0,
                    "terminal_procurement_count": 0,
                    "decision_rows": 1,
                })
    return samples, games


class EventProgramManagerBCTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        samples, games = synthetic_rows()
        self.dataset_path = self.root / "warmstart.npz"
        atomic_npz(self.dataset_path, build_dataset_arrays(samples, games))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dataset_schema_is_complete_and_carrot_is_forbidden(self) -> None:
        data = load_dataset(self.dataset_path)
        contract = validate_dataset(data)
        self.assertEqual(str(data["schema"].item()), DATASET_SCHEMA)
        self.assertEqual(data["features"].shape[1], 427)
        self.assertEqual(contract["line_counts"], {line: 8 for line in QUALIFIED_LINES})
        self.assertEqual(len(data["game_error"]), 32)

        forbidden = copy.deepcopy(qualified_decision_specs())
        forbidden[0]["decision"]["production_line"] = "CARROT"
        with self.assertRaisesRegex(ValueError, "CARROT"):
            validate_decision_specs(forbidden)

        corrupted = dict(data)
        corrupted["line"] = data["line"].copy()
        corrupted["line"][0] = "CARROT"
        with self.assertRaisesRegex(ValueError, "CARROT"):
            validate_dataset(corrupted)

    def test_seed_block_split_has_no_leakage_and_stays_balanced(self) -> None:
        data = load_dataset(self.dataset_path)
        train, validation, train_seeds, validation_seeds = seed_block_split(
            data, seed=42, validation_fraction=0.25
        )
        self.assertFalse(set(train_seeds.tolist()) & set(validation_seeds.tolist()))
        self.assertEqual(
            set(np.asarray(data["seed"])[train].tolist()), set(train_seeds.tolist())
        )
        self.assertEqual(
            set(np.asarray(data["seed"])[validation].tolist()),
            set(validation_seeds.tolist()),
        )
        for indices in (train, validation):
            counts = {
                line: int(np.sum(np.asarray(data["line"])[indices] == line))
                for line in QUALIFIED_LINES
            }
            self.assertEqual(len(set(counts.values())), 1)

    def test_masked_ce_can_update_random_manager_once(self) -> None:
        data = load_dataset(self.dataset_path)
        batch = make_batch(
            data,
            np.arange(8),
            reward_center=0.0,
            reward_scale=30000.0,
        )
        state = create_train_state(seed=114920, learning_rate=3.0e-4)
        before = jax.tree_util.tree_map(np.asarray, state.params)
        updated, metrics = train_one_step(state, batch)
        self.assertTrue(np.isfinite(float(metrics["loss"])))
        deltas = jax.tree_util.tree_leaves(
            jax.tree_util.tree_map(
                lambda left, right: np.max(np.abs(np.asarray(left) - np.asarray(right))),
                before,
                updated.params,
            )
        )
        self.assertGreater(max(float(value) for value in deltas), 0.0)

    def test_checkpoint_is_independent_and_loadable_by_random_policy(self) -> None:
        checkpoint = self.root / "manager_bc.msgpack"
        report_path = self.root / "training_report.json"
        args = argparse.Namespace(
            dataset=self.dataset_path,
            output=checkpoint,
            report=report_path,
            epochs=1,
            batch_size=16,
            learning_rate=3.0e-4,
            validation_fraction=0.25,
            patience=1,
            min_delta=0.0,
            value_coefficient=0.1,
            constraint_coefficient=0.1,
            reward_center=0.0,
            reward_scale=30000.0,
            seed=114920,
            policy_seed=114921,
        )
        report = train_bc(args)
        payload = serialization.msgpack_restore(checkpoint.read_bytes())
        validate_checkpoint_metadata(payload)
        policy = RandomEventProgramPolicy(checkpoint)

        self.assertEqual(report["status"], "COMPLETE")
        self.assertIsNone(payload["strategy_parent"])
        self.assertFalse(payload["loads_historical_policy_parameters"])
        self.assertEqual(payload["teacher_programs"], list(QUALIFIED_LINES))
        self.assertIsNotNone(policy.params)
        self.assertTrue(report_path.is_file())


if __name__ == "__main__":
    unittest.main()
