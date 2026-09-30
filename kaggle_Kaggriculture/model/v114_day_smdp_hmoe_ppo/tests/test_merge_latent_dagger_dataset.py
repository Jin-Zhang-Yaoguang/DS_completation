from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

import action_space as space
from build_latent_role_dataset import OPTION_IDS, build_latent_role_dataset
from merge_latent_dagger_dataset import (
    BASE_KEYS,
    CORE_KEYS,
    merge_latent_dagger_dataset,
)


TEACHERS = {
    "demand-timing-preemption": ("demand_teacher", "1" * 64),
    "procurement-slot-ordering": ("procurement_teacher", "2" * 64),
    "production-route-router": ("production_teacher", "3" * 64),
}


class MergeLatentDaggerDatasetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.base_raw = self.root / "base_raw.npz"
        self.base = self.root / "latent_base.npz"
        self.base_manifest = self.root / "latent_base.manifest.json"
        self.dagger0 = self.root / "dagger0.npz"
        self.dagger1 = self.root / "dagger1.npz"
        self.output = self.root / "merged.npz"
        self.manifest = self.root / "merged.manifest.json"

        base_arrays = self.make_core(episode_start=7, terminal=False)
        np.savez_compressed(self.base_raw, **base_arrays)
        build_latent_role_dataset(self.base_raw, self.base, self.base_manifest)
        np.savez_compressed(self.dagger0, **self.make_core(episode_start=7, terminal=True))
        np.savez_compressed(self.dagger1, **self.make_core(episode_start=7, terminal=False))

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_core(episode_start: int, terminal: bool) -> dict[str, np.ndarray]:
        families = np.asarray([
            "demand-timing-preemption", "demand-timing-preemption",
            "procurement-slot-ordering", "procurement-slot-ordering",
            "production-route-router", "production-route-router",
        ])
        teacher_ids = np.asarray([TEACHERS[family][0] for family in families])
        teacher_shas = np.asarray([TEACHERS[family][1] for family in families])
        episodes = np.asarray([
            episode_start, episode_start,
            episode_start + 1, episode_start + 1,
            episode_start + 2, episode_start + 2,
        ], dtype=np.int64)
        seats = np.asarray([0, 1, 0, 1, 0, 1], dtype=np.int8)
        stop = space.MARKET_INDEX["STOP"]
        hire = space.MARKET_INDEX["HIRE"]
        sell = space.MARKET_INDEX["SELL:WOOL"]
        market_tokens = np.full((6, 5), stop, dtype=np.int16)
        market_tokens[:, 0] = [hire, sell, hire, sell, hire, sell]
        market_mask = np.zeros((6, 5), dtype=np.uint8)
        market_mask[:, :2] = 1
        market_quantities = np.full((6, 5), 9, dtype=np.int16)
        unit_tokens = np.asarray([
            [space.UNIT_INDEX["PLANT:WHEAT"], space.UNIT_INDEX["PASS"], space.UNIT_INDEX["PASS"]],
            [space.UNIT_INDEX["CARE"], space.UNIT_INDEX["PASS"], space.UNIT_INDEX["PASS"]],
        ] * 3, dtype=np.int16)
        return {
            "global": np.zeros((6, 60), dtype=np.float16),
            "board": np.zeros((6, 2, 2, 2, 21), dtype=np.float16),
            "units": np.zeros((6, 3, 121), dtype=np.float16),
            "unit_mask": np.asarray([[1, 1, 0]] * 6, dtype=np.float32),
            "unit_tokens": unit_tokens,
            "unit_quantities": np.zeros((6, 3), dtype=np.int16),
            "market_tokens": market_tokens,
            "market_quantities": market_quantities,
            "market_mask": market_mask,
            "expert": np.zeros(6, dtype=np.int16),
            "value": np.linspace(-1, 1, 6, dtype=np.float32),
            "split": np.asarray([0, 0, 1, 1, 0, 0], dtype=np.int8),
            "episode": episodes,
            "step": np.full(6, 671 if terminal else 42, dtype=np.int16),
            "seat": seats,
            "unit_expert": np.zeros(6, dtype=np.int16),
            "market_expert": np.zeros(6, dtype=np.int16),
            "teacher_id": teacher_ids,
            "teacher_family": families,
            "teacher_sha256": teacher_shas,
        }

    def test_merges_raw_daggers_with_provenance_and_global_episode_groups(self) -> None:
        report = merge_latent_dagger_dataset(
            self.base, [self.dagger0, self.dagger1], self.output, self.manifest,
        )
        self.assertEqual(report["rows"], {"base": 6, "dagger": 12, "total": 18})
        self.assertEqual(report["counts"]["episodes"], 9)
        self.assertEqual(report["counts"]["by_family"], {family: 6 for family in OPTION_IDS})
        self.assertEqual(report["counts"]["by_option"], {"0": 6, "1": 6, "2": 6})
        self.assertEqual(report["counts"]["terminal"], {"rows": 6, "non_terminal_rows": 12})
        self.assertEqual(report["source_exposure"]["gold_dev"], {"accessed": False, "rows": 0})
        self.assertEqual(report["source_exposure"]["gold_blind"], {"accessed": False, "rows": 0})
        self.assertIsNone(report["strategy_parent"])
        self.assertFalse(report["inherits_v113_checkpoint"])
        self.assertIsNone(report["source_checkpoint"])

        with np.load(self.output, allow_pickle=False) as merged:
            self.assertEqual(set(merged.files), set(BASE_KEYS) | {"source_kind", "source_id", "source_episode"})
            np.testing.assert_array_equal(np.unique(merged["episode"]), np.arange(9, dtype=np.int32))
            np.testing.assert_array_equal(merged["source_id"], np.repeat([0, 1, 2], 6).astype(np.int16))
            np.testing.assert_array_equal(
                merged["source_kind"], np.asarray(["base"] * 6 + ["dagger"] * 12),
            )
            np.testing.assert_array_equal(
                merged["source_episode"],
                np.tile(np.asarray([7, 7, 8, 8, 9, 9], dtype=np.int64), 3),
            )
            for source_id, expected_range in enumerate((range(0, 3), range(3, 6), range(6, 9))):
                source_episodes = np.unique(merged["episode"][merged["source_id"] == source_id])
                np.testing.assert_array_equal(source_episodes, np.asarray(list(expected_range)))
            self.assertTrue(np.all(merged["market_mask"] == 1))
            stop = space.MARKET_INDEX["STOP"]
            self.assertTrue(np.all(merged["market_tokens"][:, 1:] == stop))
            self.assertTrue(np.all(merged["market_quantities"][:, 1:] == 0))
            self.assertTrue(np.all(merged["market_roles"][:, 1:] == 0))
            np.testing.assert_array_equal(
                merged["option_id"], np.tile(np.asarray([0, 0, 1, 1, 2, 2], dtype=np.int8), 3),
            )

        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(payload, report)
        self.assertEqual(payload["output"]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())
        self.assertEqual(payload["episode_grouping"]["global_unique_episodes"], 9)
        self.assertTrue(payload["episode_grouping"]["contiguous_zero_based"])
        self.assertEqual([item["rows"] for item in payload["inputs"]], [6, 6, 6])
        self.assertEqual([item["absorbing_stop_slots_added"] for item in payload["inputs"]], [0, 18, 18])

    def test_accepts_prederived_dagger_only_when_derived_contract_is_valid(self) -> None:
        dagger_latent = self.root / "dagger_latent.npz"
        dagger_manifest = self.root / "dagger_latent.manifest.json"
        build_latent_role_dataset(self.dagger0, dagger_latent, dagger_manifest)
        report = merge_latent_dagger_dataset(
            self.base, [dagger_latent], self.output, self.manifest,
        )
        self.assertEqual(report["rows"], {"base": 6, "dagger": 6, "total": 12})

        with np.load(dagger_latent, allow_pickle=False) as archive:
            arrays = {key: archive[key] for key in archive.files}
        arrays["terminal_flag"] = np.zeros(6, dtype=np.int8)
        np.savez_compressed(dagger_latent, **arrays)
        with self.assertRaisesRegex(ValueError, "terminal_flag conflicts"):
            merge_latent_dagger_dataset(self.base, [dagger_latent], self.output, self.manifest)

    def test_rejects_missing_extra_shape_and_dtype_schema_changes(self) -> None:
        with np.load(self.dagger0, allow_pickle=False) as archive:
            original = {key: archive[key] for key in archive.files}

        cases = []
        missing = dict(original)
        missing.pop("value")
        cases.append((missing, "array schema mismatch"))
        extra = dict(original)
        extra["unexpected"] = np.zeros(6, dtype=np.int8)
        cases.append((extra, "array schema mismatch"))
        shape = dict(original)
        shape["global"] = np.zeros((6, 59), dtype=np.float16)
        cases.append((shape, "trailing shape mismatch"))
        dtype = dict(original)
        dtype["value"] = original["value"].astype(np.float64)
        cases.append((dtype, "dtype mismatch"))

        for index, (arrays, message) in enumerate(cases):
            path = self.root / f"bad_schema_{index}.npz"
            np.savez_compressed(path, **arrays)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, message):
                merge_latent_dagger_dataset(self.base, [path], self.output, self.manifest)

    def test_rejects_option_family_and_teacher_sha_contract_violations(self) -> None:
        with np.load(self.dagger0, allow_pickle=False) as archive:
            original = {key: archive[key] for key in archive.files}

        unknown_family = dict(original)
        unknown_family["teacher_family"] = original["teacher_family"].copy()
        unknown_family["teacher_family"][0:2] = "unknown-family"
        cases = [(unknown_family, "unknown teacher families")]

        malformed_sha = dict(original)
        malformed_sha["teacher_sha256"] = original["teacher_sha256"].copy()
        malformed_sha["teacher_sha256"][0:2] = "not-a-sha"
        cases.append((malformed_sha, "invalid SHA256"))

        wrong_sha = dict(original)
        wrong_sha["teacher_sha256"] = original["teacher_sha256"].copy()
        wrong_sha["teacher_sha256"][0:2] = "f" * 64
        cases.append((wrong_sha, "family/SHA does not match base"))

        unknown_teacher = dict(original)
        unknown_teacher["teacher_id"] = original["teacher_id"].copy()
        unknown_teacher["teacher_id"][0:2] = "new_teacher"
        cases.append((unknown_teacher, "absent from the base teacher contract"))

        for index, (arrays, message) in enumerate(cases):
            path = self.root / f"bad_identity_{index}.npz"
            np.savez_compressed(path, **arrays)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, message):
                merge_latent_dagger_dataset(self.base, [path], self.output, self.manifest)

        latent = self.root / "bad_option.npz"
        build_latent_role_dataset(self.dagger0, latent, self.root / "bad_option_manifest.json")
        with np.load(latent, allow_pickle=False) as archive:
            arrays = {key: archive[key] for key in archive.files}
        arrays["option_id"] = arrays["option_id"].copy()
        arrays["option_id"][0] = 2
        np.savez_compressed(latent, **arrays)
        with self.assertRaisesRegex(ValueError, "option_id conflicts"):
            merge_latent_dagger_dataset(self.base, [latent], self.output, self.manifest)

    def test_rejects_episode_that_spans_split_or_teacher_identity(self) -> None:
        with np.load(self.dagger0, allow_pickle=False) as archive:
            original = {key: archive[key] for key in archive.files}
        split = dict(original)
        split["split"] = original["split"].copy()
        split["split"][1] = 1
        path = self.root / "split_leak.npz"
        np.savez_compressed(path, **split)
        with self.assertRaisesRegex(ValueError, "spans multiple split"):
            merge_latent_dagger_dataset(self.base, [path], self.output, self.manifest)

        identity = dict(original)
        identity["teacher_id"] = original["teacher_id"].copy()
        identity["teacher_id"][1] = TEACHERS["procurement-slot-ordering"][0]
        identity["teacher_family"] = original["teacher_family"].copy()
        identity["teacher_family"][1] = "procurement-slot-ordering"
        identity["teacher_sha256"] = original["teacher_sha256"].copy()
        identity["teacher_sha256"][1] = TEACHERS["procurement-slot-ordering"][1]
        path = self.root / "identity_leak.npz"
        np.savez_compressed(path, **identity)
        with self.assertRaisesRegex(ValueError, "spans multiple teacher_id"):
            merge_latent_dagger_dataset(self.base, [path], self.output, self.manifest)

    def test_rejects_duplicate_inputs_and_does_not_overwrite_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be unique"):
            merge_latent_dagger_dataset(
                self.base, [self.dagger0, self.dagger0], self.output, self.manifest,
            )
        with self.assertRaisesRegex(ValueError, "must differ"):
            merge_latent_dagger_dataset(
                self.base, [self.dagger0], self.dagger0, self.manifest,
            )
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
