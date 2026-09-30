from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest

from kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate import (
    load_seed_manifest,
    stratified_seed_panel,
)


HERE = Path(__file__).resolve().parents[1]


def _source_key(row):
    return str(row["date"])[:10], int(row["seed"]), str(row["episode_id"])


class TestExposureQuarantineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.quarantine_path = HERE / "test_exposure_quarantine.json"
        self.manifest_path = HERE / "evaluation_seed_manifest.jsonl"
        self.quarantine = json.loads(self.quarantine_path.read_text(encoding="utf-8"))

    def test_quarantine_is_metadata_only_and_matches_canonical_test_pool(self) -> None:
        data = self.quarantine
        self.assertEqual(data["schema"], "kaggriculture-v10-test-exposure-quarantine-1")
        self.assertFalse(data["outcome_metrics_retained"])
        self.assertEqual(
            data["canonical_seed_manifest_sha256"],
            hashlib.sha256(self.manifest_path.read_bytes()).hexdigest(),
        )
        quarantined = {_source_key(row) for row in data["quarantined_sources"]}
        self.assertEqual(len(quarantined), 42)
        self.assertEqual(len(data["quarantined_sources"]), 42)
        self.assertEqual(
            Counter(date for date, _, _ in quarantined),
            Counter({"2026-08-18": 11, "2026-08-19": 15, "2026-08-20": 16}),
        )
        manifest = load_seed_manifest(self.manifest_path)
        test_sources = {
            (row.date, int(row.seed), str(row.episode_id))
            for row in manifest
            if row.split == "test"
        }
        self.assertEqual(len(test_sources), 210)
        self.assertLessEqual(quarantined, test_sources)
        clean = test_sources - quarantined
        self.assertEqual(len(clean), 168)
        self.assertEqual(
            Counter(date for date, _, _ in clean),
            Counter({"2026-08-18": 59, "2026-08-19": 55, "2026-08-20": 54}),
        )

    def test_final_deterministic_panel_has_zero_quarantine_overlap(self) -> None:
        quarantined = {_source_key(row) for row in self.quarantine["quarantined_sources"]}
        clean_manifest = [
            row
            for row in load_seed_manifest(self.manifest_path)
            if (row.date, int(row.seed), str(row.episode_id)) not in quarantined
        ]
        panel = stratified_seed_panel(
            clean_manifest,
            count=100,
            dates=("2026-08-18", "2026-08-19", "2026-08-20"),
            split="test",
            random_seed=20260822,
        )
        panel_keys = {(row.date, int(row.seed), str(row.episode_id)) for row in panel}
        self.assertEqual(len(panel_keys), 100)
        self.assertFalse(panel_keys & quarantined)
        self.assertEqual(
            Counter(row.date for row in panel),
            Counter({"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33}),
        )

    def test_present_exposure_artifacts_reproduce_the_union(self) -> None:
        """When ephemeral files remain, hashes and source union must be exact."""

        artifacts = self.quarantine["source_artifacts"]
        present = [Path(row["path"]) for row in artifacts if Path(row["path"]).is_file()]
        if not present:
            self.skipTest("ephemeral exposure artifacts have been removed")
        self.assertEqual(len(present), len(artifacts), "only part of the incident artifacts remains")
        union = set()
        total_records = 0
        for expected, path in zip(artifacts, present):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected["sha256"])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), int(expected["records"]))
            total_records += len(rows)
            sources = {
                (
                    str((row.get("source") or {}).get("date") or "")[:10],
                    int((row.get("source") or {})["seed"]),
                    str((row.get("source") or {}).get("episode_id") or ""),
                )
                for row in rows
            }
            self.assertEqual(len(sources), int(expected["unique_test_sources"]))
            union.update(sources)
        quarantined = {_source_key(row) for row in self.quarantine["quarantined_sources"]}
        self.assertEqual(total_records, 148)
        self.assertEqual(union, quarantined)


if __name__ == "__main__":
    unittest.main()
