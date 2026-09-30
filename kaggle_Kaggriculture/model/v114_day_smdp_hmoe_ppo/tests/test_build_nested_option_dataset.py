from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np

from build_nested_option_dataset import OPTION_IDS, build_nested_option_dataset


class BuildNestedOptionDatasetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "stage35.npz"
        self.output = self.root / "nested.npz"
        self.manifest = self.root / "nested.manifest.json"
        self.arrays = {
            "global": np.arange(24, dtype=np.float16).reshape(6, 4),
            "unit_expert": np.asarray([4, 2, 0, 1, 5, 4], dtype=np.int16),
            "market_expert": np.asarray([4, 4, 3, 4, 5, 3], dtype=np.int16),
            "teacher_family": np.asarray([
                "demand-timing-preemption",
                "procurement-slot-ordering",
                "production-route-router",
                "demand-timing-preemption",
                "production-route-router",
                "procurement-slot-ordering",
            ]),
            "episode": np.asarray([10, 10, 11, 11, 12, 12], dtype=np.int64),
        }
        np.savez_compressed(self.source, **self.arrays)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_adds_nested_options_and_preserves_every_source_array(self) -> None:
        report = build_nested_option_dataset(self.source, self.output, self.manifest)

        with np.load(self.output, allow_pickle=False) as written:
            self.assertEqual(set(written.files), set(self.arrays) | {"option_id"})
            for key, expected in self.arrays.items():
                np.testing.assert_array_equal(written[key], expected)
                self.assertEqual(written[key].dtype, expected.dtype)
            np.testing.assert_array_equal(
                written["option_id"],
                np.asarray([0, 1, 2, 0, 2, 1], dtype=np.int8),
            )

        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(payload, report)
        self.assertIsNone(payload["strategy_parent"])
        self.assertFalse(payload["inherits_v113_checkpoint"])
        self.assertIsNone(payload["source_checkpoint"])
        self.assertTrue(payload["functional_role_labels"]["preserved"])
        self.assertEqual(payload["option_contract"], OPTION_IDS)
        self.assertEqual(payload["option_counts"], {
            "demand-timing-preemption": 2,
            "procurement-slot-ordering": 2,
            "production-route-router": 2,
        })
        self.assertEqual(
            payload["source"]["sha256"],
            hashlib.sha256(self.source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            payload["output"]["sha256"],
            hashlib.sha256(self.output.read_bytes()).hexdigest(),
        )
        with zipfile.ZipFile(self.output) as archive:
            self.assertTrue(archive.infolist())
            self.assertTrue(all(row.compress_type == zipfile.ZIP_DEFLATED for row in archive.infolist()))

    def test_rejects_unknown_teacher_family_without_writing_artifacts(self) -> None:
        arrays = dict(self.arrays)
        arrays["teacher_family"] = arrays["teacher_family"].copy()
        arrays["teacher_family"][0] = "unknown-family"
        np.savez_compressed(self.source, **arrays)

        with self.assertRaisesRegex(ValueError, "unknown Stage35 teacher families"):
            build_nested_option_dataset(self.source, self.output, self.manifest)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())


if __name__ == "__main__":
    unittest.main()
