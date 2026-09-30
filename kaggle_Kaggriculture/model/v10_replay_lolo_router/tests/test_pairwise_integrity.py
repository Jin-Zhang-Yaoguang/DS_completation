from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kaggle_Kaggriculture.model.v10_replay_lolo_router import collect_router_grid
from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
    registry_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate import (
    SCHEMA,
    SeedRecord,
    build_tasks,
    evaluation_fingerprint,
    stratified_seed_panel,
    summarise,
)


class PairwiseIntegrityTest(unittest.TestCase):
    def _registry(self, root: Path):
        agent = root / "agent.py"
        agent.write_text(
            "def agent(obs):\n return {'farmer':['PASS'],'hands':[],'market':[]}\n",
            encoding="utf-8",
        )
        registry = root / "registry.json"
        registry.write_text(
            json.dumps(
                {
                    "models": [
                        {"id": "a", "kind": "python", "path": "agent.py"},
                        {"id": "b", "kind": "python", "path": "agent.py"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        return load_registry(registry), agent

    def test_registry_fingerprint_includes_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry, agent = self._registry(Path(temporary))
            before = registry_fingerprint(registry)
            agent.write_text(
                "def agent(obs):\n return {'farmer':['NORTH'],'hands':[],'market':[]}\n",
                encoding="utf-8",
            )
            self.assertNotEqual(before, registry_fingerprint(registry))

    def test_registry_fingerprint_ignores_unlisted_trainer_but_marks_missing_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent = root / "agent.py"
            agent.write_text("def agent(obs): return {}\n", encoding="utf-8")
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "models": [
                            {
                                "id": "a",
                                "kind": "python",
                                "path": "agent.py",
                                "code_paths": ["missing_dependency.py"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            registry = load_registry(registry_path)
            missing_fingerprint = registry_fingerprint(registry)
            (root / "unlisted_trainer.py").write_text("version = 2\n", encoding="utf-8")
            self.assertEqual(missing_fingerprint, registry_fingerprint(registry))
            (root / "missing_dependency.py").write_text("version = 1\n", encoding="utf-8")
            self.assertNotEqual(missing_fingerprint, registry_fingerprint(registry))

    def test_registry_fingerprint_uses_declared_dependencies_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry, agent = self._registry(root)
            dependency = root / "serving_dependency.py"
            dependency.write_text("VALUE = 1\n", encoding="utf-8")
            registry.models["a"]["code_paths"] = ["serving_dependency.py"]
            registry.raw["models"][0]["code_paths"] = ["serving_dependency.py"]
            before = registry_fingerprint(registry)

            # Unrelated trainer/evaluator files must not invalidate reusable
            # serving results.
            (root / "train_router.py").write_text("VERSION = 2\n", encoding="utf-8")
            self.assertEqual(before, registry_fingerprint(registry))

            # Every explicitly declared serving dependency must invalidate it.
            dependency.write_text("VALUE = 2\n", encoding="utf-8")
            self.assertNotEqual(before, registry_fingerprint(registry))

    def test_summary_rejects_old_run_and_duplicate_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry, _ = self._registry(Path(temporary))
            panel = [SeedRecord("2026-08-18", 7, "episode-7", "test")]
            fingerprint = evaluation_fingerprint(registry, ["a", "b"], panel, 2)
            tasks = build_tasks(registry, ["a", "b"], panel, fingerprint)
            rows = []
            for task in tasks:
                row = {
                    **task,
                    "schema": SCHEMA,
                    "done": True,
                    "error": None,
                    "score_a": 1.0,
                    "margin_a": 10.0,
                }
                rows.append(row)
            # A failed retry record with the same id cannot inflate counts or
            # replace an already successful task.
            rows.append({**rows[0], "done": False, "error": "old failure"})
            # A row from a different code/panel run is ignored even if its
            # remaining fields look valid.
            rows.append({**rows[0], "task_id": "foreign", "run_fingerprint": "old"})
            report = summarise(
                rows,
                ["a", "b"],
                2,
                {task["task_id"] for task in tasks},
                fingerprint,
            )
            self.assertTrue(report["formal_gate_complete"])
            self.assertEqual(report["deduplicated_tasks"], 2)
            pair = report["pairs"]["a__vs__b"]
            self.assertEqual(pair["observed_games"], 2)
            self.assertEqual(pair["valid_games"], 2)
            self.assertEqual(pair["paired_seeds"], 1)

    def test_small_panel_does_not_fill_zero_quota_dates(self) -> None:
        records = [
            SeedRecord(date, seed, f"episode-{seed}", "test")
            for date, offset in (
                ("2026-08-18", 0),
                ("2026-08-19", 100),
                ("2026-08-20", 200),
            )
            for seed in range(offset, offset + 3)
        ]
        panel = stratified_seed_panel(
            records,
            count=1,
            dates=("2026-08-18", "2026-08-19", "2026-08-20"),
            split="test",
            random_seed=7,
        )
        self.assertEqual(len(panel), 1)
        self.assertEqual(panel[0].date, "2026-08-18")

    def test_run_fingerprints_bind_evaluator_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry, _ = self._registry(Path(temporary))
            panel = [SeedRecord("2026-08-18", 7, "episode-7", "test")]
            with patch.object(pairwise_evaluate, "implementation_fingerprint", return_value="implementation-a"):
                first = evaluation_fingerprint(registry, ["a", "b"], panel, 2)
            with patch.object(pairwise_evaluate, "implementation_fingerprint", return_value="implementation-b"):
                second = evaluation_fingerprint(registry, ["a", "b"], panel, 2)
            self.assertNotEqual(first, second)

    def test_collection_fingerprint_binds_collector_implementation(self) -> None:
        registry_path = Path(__file__).resolve().parents[1] / "router_training_registry.json"
        source = collect_router_grid.SeedSource(
            "2026-08-18", 7, "episode-7", "train", "source.json"
        )
        arguments = (
            registry_path,
            ["baseline_v1", "baseline_v2"],
            ["baseline_v5"],
            {"train": [source]},
            "baseline_v1",
            72,
        )
        with patch.object(collect_router_grid, "implementation_fingerprint", return_value="implementation-a"):
            _, first = collect_router_grid.build_tasks(*arguments)
        with patch.object(collect_router_grid, "implementation_fingerprint", return_value="implementation-b"):
            _, second = collect_router_grid.build_tasks(*arguments)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
