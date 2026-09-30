from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
    registry_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.collect_router_grid import (
    implementation_fingerprint as grid_implementation_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.router import FEATURE_DIM
from kaggle_Kaggriculture.model.v10_replay_lolo_router.train_router import (
    GRID_SCHEMA,
    _read_jsonl,
    grid_implementation_fingerprint,
    perspectives,
    train_and_report,
)


HERE = Path(__file__).resolve().parents[1]


class TrainRouterIntegrityTest(unittest.TestCase):
    def test_retry_success_supersedes_first_error(self) -> None:
        failed = {"task_id": "same", "done": False, "error": "failed"}
        succeeded = {"task_id": "same", "done": True, "error": None}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "grid.jsonl"
            path.write_text(
                json.dumps(failed) + "\n" + json.dumps(succeeded) + "\n",
                encoding="utf-8",
            )
            rows = _read_jsonl([path])
        self.assertEqual(rows, [succeeded])
        self.assertEqual(rows.audit["retry_success_replacements"], 1)

    def test_conflicting_successful_retry_is_audited(self) -> None:
        first = {
            "task_id": "same", "done": True, "error": None,
            "candidate_score": 0.0,
        }
        second = {
            "task_id": "same", "done": True, "error": None,
            "candidate_score": 1.0,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "grid.jsonl"
            path.write_text(
                json.dumps(first) + "\n" + json.dumps(second) + "\n",
                encoding="utf-8",
            )
            rows = _read_jsonl([path])
        self.assertEqual(rows, [second])
        self.assertEqual(rows.audit["conflicting_success_records"], 1)

    def test_grid_lineage_label_must_match_registry(self) -> None:
        registry = load_registry(HERE / "router_training_registry.json")
        row = {
            "schema": GRID_SCHEMA,
            "task_id": "bad-lineage",
            "done": True,
            "error": None,
            "candidate": "baseline_v1",
            "opponent": "baseline_v2",
            "candidate_root_lineage": "forged-lineage",
            "opponent_root_lineage": "baseline_v2",
            "candidate_score": 1.0,
            "candidate_margin": 1.0,
            "router_seat": 0,
            "switch_features": [0.0] * FEATURE_DIM,
            "switch_feature_sha256": "hash",
            "source": {
                "date": "2026-08-18",
                "episode_id": "episode",
                "seed": 1,
                "split": "train",
            },
        }
        with self.assertRaisesRegex(ValueError, "root-lineage labels"):
            perspectives([row], registry)

    def test_lolo_holds_out_opponent_lineage_but_keeps_all_candidates(self) -> None:
        registry = load_registry(HERE / "router_training_registry.json")
        fingerprint = registry_fingerprint(registry)
        candidates = ["baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8"]
        rows = []
        task = 0
        for split, seed_base in (("train", 100), ("validation", 200)):
            for opponent_index, opponent in enumerate(candidates):
                for seat in (0, 1):
                    seed = seed_base + opponent_index
                    context_hash = f"feature-{split}-{opponent}-{seat}"
                    vector = [0.0] * FEATURE_DIM
                    vector[0] = opponent_index / 3.0
                    vector[2] = float(seat)
                    for candidate_index, candidate in enumerate(candidates):
                        task += 1
                        score = float(candidate_index == (opponent_index + seat) % 4)
                        rows.append(
                            {
                                "schema": GRID_SCHEMA,
                                "task_id": f"task-{task}",
                                "collection_fingerprint": "synthetic-collection",
                                "collection_implementation_sha256": grid_implementation_fingerprint(),
                                "collection_implementation_sha256": grid_implementation_fingerprint(),
                                "registry_sha256": fingerprint,
                                "done": True,
                                "error": None,
                                "prefix_complete": True,
                                "prefix_match": True,
                                "candidate": candidate,
                                "opponent": opponent,
                                "candidate_root_lineage": candidate,
                                "opponent_root_lineage": opponent,
                                "candidate_score": score,
                                "candidate_margin": 100.0 if score else -100.0,
                                "router_seat": seat,
                                "switch_features": vector,
                                "switch_feature_sha256": context_hash,
                                "source": {
                                    "date": "2026-08-18",
                                    "episode_id": f"episode-{seed}",
                                    "seed": seed,
                                    "split": split,
                                },
                            }
                        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = train_and_report(
                rows,
                registry,
                candidates,
                root / "weights.npz",
                root / "report.json",
                ridge=1.0,
                min_support=1,
                rule_router_id=None,
            )
        for held, fold in report["leave_one_root_lineage_out"].items():
            self.assertEqual(set(fold["training_support"]), set(candidates))
            self.assertEqual(fold["excluded_candidate_classes"], [])
            self.assertTrue(fold["held_lineage_absent_from_training_opponents"])
            metrics = fold["comparison"]["policy_metrics"]
            self.assertIn("mean_margin", metrics["best_fixed"])
            self.assertEqual(len(metrics["learned_router"]["margin_ci95"]), 2)


if __name__ == "__main__":
    unittest.main()
