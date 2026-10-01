from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from model.superblend.ablation import drop_one_ablation
from model.superblend.lineage import assert_no_lineage_overlap, build_lineage
from model.superblend.meta_cv import generate_meta_folds, load_meta_folds, save_meta_folds
from model.superblend.registry import (
    RegistryError,
    build_candidate_snapshot,
    load_candidate_snapshot,
    write_json_exclusive,
)
from model.superblend.run_superblend import main as superblend_main
from model.superblend.selectors import (
    correlation_clusters,
    family_equal_weights,
    fit_family_hierarchical,
    fit_nonnegative_ridge_simplex,
    greedy_forward_select,
)
from model.superblend.transforms import ECDFTransformer, MetaTransformer


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "model").mkdir()
        (self.root / "model" / "experiments.md").write_text("test", encoding="utf-8")
        self._candidate("m1", [0.1, 0.8, 0.2, 0.9], [0.3, 0.7])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _candidate(self, name: str, oof: list[float], test: list[float]) -> None:
        directory = self.root / "model" / name
        directory.mkdir()
        np.save(directory / "oof_proba.npy", np.asarray(oof, dtype=np.float32))
        np.save(directory / "test_proba.npy", np.asarray(test, dtype=np.float32))
        _write_json(directory / "cv_results.json", {"oof_auc": 0.75, "n_folds": 2})

    def _config(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "cycle_id": "C01",
            "candidates": [
                {
                    "id": "m1",
                    "experiment_dir": "model/m1",
                    "artifact_type": "atomic_model",
                    "family": "lightgbm",
                    "feature_mechanism": "synthetic",
                    "split_seed": 42,
                    "source_scope": "local",
                    "inclusion_reason": "unit test",
                    "row_order_evidence": {"oof": "fixture order", "test": "fixture order"},
                }
            ],
        }

    def test_snapshot_hash_and_source_mutation_are_rejected(self) -> None:
        envelope = build_candidate_snapshot(self.root, self._config(), 4, 2)
        snapshot_path = self.root / "run" / "candidate_snapshot.json"
        write_json_exclusive(snapshot_path, envelope)
        loaded = load_candidate_snapshot(self.root, snapshot_path)
        self.assertEqual(loaded["candidate_count"], 1)

        np.save(self.root / "model" / "m1" / "oof_proba.npy", np.full(4, 0.5, dtype=np.float32))
        with self.assertRaisesRegex(RegistryError, "source hash changed"):
            load_candidate_snapshot(self.root, snapshot_path)

    def test_snapshot_is_exclusive_and_requires_row_order_evidence(self) -> None:
        bad = self._config()
        del bad["candidates"][0]["row_order_evidence"]  # type: ignore[index]
        with self.assertRaisesRegex(RegistryError, "row_order_evidence"):
            build_candidate_snapshot(self.root, bad, 4, 2)
        path = self.root / "frozen.json"
        write_json_exclusive(path, {"once": True})
        with self.assertRaises(FileExistsError):
            write_json_exclusive(path, {"twice": True})

    def test_audit_only_cli_creates_complete_receipt_in_new_directory(self) -> None:
        config_path = self.root / "candidate-config.json"
        _write_json(config_path, self._config())
        output_dir = self.root / "audit-run"
        exit_code = superblend_main(
            [
                "--stage",
                "audit-only",
                "--repo-root",
                str(self.root),
                "--candidate-config",
                str(config_path),
                "--output-dir",
                str(output_dir),
                "--expected-oof-rows",
                "4",
                "--expected-test-rows",
                "2",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            {path.name for path in output_dir.iterdir()},
            {
                "audit_summary.json",
                "candidate_snapshot.json",
                "lineage.json",
                "registry_audit.json",
                "sources.json",
            },
        )


class LineageTests(unittest.TestCase):
    def test_lineage_overlap_is_rejected(self) -> None:
        with self.assertRaisesRegex(RegistryError, "parent/child"):
            assert_no_lineage_overlap(["atomic", "ensemble"], {"atomic": [], "ensemble": ["atomic"]})

    def test_sources_json_resolves_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("atomic", "ensemble"):
                (root / "model" / name).mkdir(parents=True)
            _write_json(
                root / "model" / "ensemble" / "sources.json",
                {"a": {"oof": "model/atomic/oof.npy", "test": "model/atomic/test.npy"}},
            )
            snapshot = {
                "candidates": [
                    {
                        "id": "atomic",
                        "experiment_dir": "model/atomic",
                        "declared_parents": [],
                        "oof": {"path": "model/atomic/oof.npy"},
                        "test": {"path": "model/atomic/test.npy"},
                    },
                    {
                        "id": "ensemble",
                        "experiment_dir": "model/ensemble",
                        "declared_parents": [],
                        "oof": {"path": "model/ensemble/oof.npy"},
                        "test": {"path": "model/ensemble/test.npy"},
                    },
                ]
            }
            lineage = build_lineage(root, snapshot)["lineage"]
            self.assertEqual(lineage["parents"]["ensemble"], ["atomic"])


class TransformTests(unittest.TestCase):
    def test_ecdf_uses_training_distribution_only(self) -> None:
        train = np.asarray([[0.0], [1.0], [2.0], [3.0]])
        valid = np.asarray([[-10.0], [10.0]])
        transformer = ECDFTransformer().fit(train)
        np.testing.assert_allclose(transformer.transform(valid).ravel(), [0.0, 1.0])
        np.testing.assert_allclose(transformer.transform(train).ravel(), [0.125, 0.375, 0.625, 0.875])

    def test_pipeline_is_frozen_after_fit(self) -> None:
        train = np.asarray([[0.1, 0.2], [0.4, 0.8], [0.9, 0.3]])
        transformer = MetaTransformer("ecdf_standardize").fit(train)
        before = transformer.transform(train)
        transformer.transform(np.full((20, 2), 1000.0))
        np.testing.assert_allclose(before, transformer.transform(train))


class MetaFoldTests(unittest.TestCase):
    def test_nested_folds_are_deterministic_disjoint_and_confirmation_locked(self) -> None:
        target = np.tile([0, 1], 30)
        manifest1, arrays1 = generate_meta_folds(
            target,
            outer_seeds=(42, 104743),
            confirmation_seed=104743,
            outer_splits=3,
            inner_splits=3,
        )
        manifest2, arrays2 = generate_meta_folds(
            target,
            outer_seeds=(42, 104743),
            confirmation_seed=104743,
            outer_splits=3,
            inner_splits=3,
        )
        self.assertEqual(manifest1["fold_definition_sha256"], manifest2["fold_definition_sha256"])
        for key in arrays1:
            np.testing.assert_array_equal(arrays1[key], arrays2[key])
        for record in manifest1["outer_folds"]:
            train = arrays1[record["train_key"]]
            valid = arrays1[record["valid_key"]]
            self.assertFalse(np.intersect1d(train, valid).size)
            self.assertEqual(len(np.union1d(train, valid)), len(target))
            for inner in record["inner_folds"]:
                inner_train = arrays1[inner["train_key"]]
                inner_valid = arrays1[inner["valid_key"]]
                self.assertFalse(np.intersect1d(inner_train, inner_valid).size)
                self.assertTrue(set(inner_train).issubset(set(train)))
                self.assertTrue(set(inner_valid).issubset(set(train)))

        with tempfile.TemporaryDirectory() as temp:
            manifest_path, _ = save_meta_folds(Path(temp), manifest1, arrays1)
            development, loaded = load_meta_folds(manifest_path)
            self.assertTrue(all(row["role"] == "development" for row in development["outer_folds"]))
            self.assertFalse(any("104743" in key for key in loaded))
            with self.assertRaisesRegex(RegistryError, "locked"):
                load_meta_folds(manifest_path, include_confirmation=True)


class SelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(123)
        self.target = rng.integers(0, 2, size=400)
        signal = self.target + rng.normal(0.0, 0.8, size=400)
        self.predictions = np.column_stack(
            [signal, signal + rng.normal(0.0, 0.01, size=400), rng.normal(size=400), self.target + rng.normal(0.0, 1.1, size=400)]
        )

    def test_basic_selectors_respect_constraints(self) -> None:
        greedy = greedy_forward_select(
            self.predictions,
            self.target,
            ["a", "b", "noise", "c"],
            min_delta=0.0,
        )
        self.assertLessEqual(len(greedy["selected_ids"]), 4)
        self.assertAlmostEqual(float(greedy["weights"].sum()), 1.0)

        fitted = fit_nonnegative_ridge_simplex(
            self.predictions,
            self.target,
            ridge_lambda=1e-3,
            weight_cap=0.5,
        )
        self.assertAlmostEqual(float(fitted["weights"].sum()), 1.0, places=8)
        self.assertTrue(np.all(fitted["weights"] >= 0.0))
        self.assertTrue(np.all(fitted["weights"] <= 0.5 + 1e-8))

    def test_family_and_cluster_tools(self) -> None:
        weights = family_equal_weights(["tree", "tree", "nn", "linear"])
        np.testing.assert_allclose(weights, [1 / 6, 1 / 6, 1 / 3, 1 / 3])
        metadata = [
            {"id": "a", "family": "tree", "feature_mechanism": "te", "split_seed": 42, "oof_auc": 0.8, "cycle_index": 1},
            {"id": "b", "family": "tree", "feature_mechanism": "te", "split_seed": 42, "oof_auc": 0.79, "cycle_index": 2},
            {"id": "noise", "family": "linear", "feature_mechanism": "raw", "split_seed": 42, "oof_auc": 0.5, "cycle_index": 1},
            {"id": "c", "family": "nn", "feature_mechanism": "embed", "split_seed": 42, "oof_auc": 0.7, "cycle_index": 1},
        ]
        clusters = correlation_clusters(self.predictions, metadata, threshold=0.99)
        self.assertTrue(any(set(cluster["member_ids"]) == {"a", "b"} for cluster in clusters))

        hierarchical = fit_family_hierarchical(
            self.predictions,
            self.target,
            ["tree", "tree", "nn", "linear"],
            ridge_lambda=1e-3,
            family_weight_cap=0.5,
        )
        self.assertAlmostEqual(float(hierarchical["weights"].sum()), 1.0, places=8)

    def test_drop_one_outputs_both_levels(self) -> None:
        result = drop_one_ablation(
            self.predictions,
            self.target,
            np.full(4, 0.25),
            ["a", "b", "noise", "c"],
            ["tree", "tree", "linear", "nn"],
        )
        self.assertEqual(len(result["drop_one_member"]), 4)
        self.assertEqual(len(result["drop_one_family"]), 3)


if __name__ == "__main__":
    unittest.main()
