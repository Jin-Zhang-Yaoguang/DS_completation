from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

import action_space as space
from build_latent_role_dataset import (
    OPTION_IDS,
    TERMINAL_STEP,
    build_latent_role_dataset,
    unit_role,
)


class BuildLatentRoleDatasetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "teacher.npz"
        self.output = self.root / "v6.npz"
        self.manifest = self.root / "v6.manifest.json"
        stop = space.MARKET_INDEX["STOP"]
        hire = space.MARKET_INDEX["HIRE"]
        sell = space.MARKET_INDEX["SELL:WOOL"]
        plant = space.UNIT_INDEX["PLANT:WHEAT"]
        care = space.UNIT_INDEX["CARE"]
        pass_token = space.UNIT_INDEX["PASS"]
        families = list(OPTION_IDS)
        market_tokens = np.full((6, 5), stop, dtype=np.int16)
        market_quantities = np.full((6, 5), 9, dtype=np.int16)
        market_mask = np.zeros((6, 5), dtype=np.uint8)
        boundaries = [2, 1, 3, 2, 1, 3]
        for row, boundary in enumerate(boundaries):
            market_tokens[row, :boundary] = [hire, sell, hire][:boundary]
            market_tokens[row, boundary] = stop
            market_mask[row, :boundary + 1] = 1
        self.arrays = {
            "global": np.arange(24, dtype=np.float16).reshape(6, 4),
            "teacher_family": np.asarray(families * 2),
            "episode": np.asarray([10, 11, 12, 13, 14, 15], dtype=np.int64),
            "step": np.asarray([670, 671, 718, 0, 671, 42], dtype=np.int16),
            "unit_tokens": np.asarray([
                [plant, pass_token, pass_token],
                [care, pass_token, pass_token],
                [pass_token, pass_token, pass_token],
                [plant, care, pass_token],
                [care, care, pass_token],
                [plant, plant, pass_token],
            ], dtype=np.int16),
            "unit_mask": np.asarray([
                [1, 1, 0], [1, 1, 0], [1, 0, 0],
                [1, 1, 1], [1, 1, 0], [1, 1, 0],
            ], dtype=np.float32),
            "market_tokens": market_tokens,
            "market_quantities": market_quantities,
            "market_mask": market_mask,
        }
        np.savez_compressed(self.source, **self.arrays)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_builds_absorbing_stop_tail_and_complete_manifest(self) -> None:
        report = build_latent_role_dataset(self.source, self.output, self.manifest)
        stop = space.MARKET_INDEX["STOP"]
        original_active = int(np.count_nonzero(self.arrays["market_mask"]))

        with np.load(self.output, allow_pickle=False) as written:
            for key in ("global", "teacher_family", "episode", "step", "unit_tokens", "unit_mask"):
                np.testing.assert_array_equal(written[key], self.arrays[key])
            np.testing.assert_array_equal(written["option_id"], np.asarray([0, 1, 2, 0, 1, 2], dtype=np.int8))
            np.testing.assert_array_equal(
                written["terminal_flag"],
                (self.arrays["step"] >= TERMINAL_STEP).astype(np.int8),
            )
            self.assertTrue(np.all(written["market_mask"] == 1))
            for row in range(6):
                boundary = int(np.flatnonzero(
                    (self.arrays["market_mask"][row] != 0)
                    & (self.arrays["market_tokens"][row] == stop)
                )[0])
                np.testing.assert_array_equal(
                    written["market_tokens"][row, boundary:],
                    np.full(5 - boundary, stop, dtype=np.int16),
                )
                np.testing.assert_array_equal(
                    written["market_quantities"][row, boundary:],
                    np.zeros(5 - boundary, dtype=np.int16),
                )
                np.testing.assert_array_equal(
                    written["market_roles"][row, boundary:],
                    np.zeros(5 - boundary, dtype=np.int8),
                )
                np.testing.assert_array_equal(
                    written["market_tokens"][row, :boundary],
                    self.arrays["market_tokens"][row, :boundary],
                )
            expected_unit_roles = np.vectorize(unit_role, otypes=[np.int8])(self.arrays["unit_tokens"])
            expected_unit_roles[self.arrays["unit_mask"] == 0] = 0
            np.testing.assert_array_equal(written["unit_roles"], expected_unit_roles)

        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(payload, report)
        self.assertIsNone(payload["strategy_parent"])
        self.assertFalse(payload["inherits_v113_checkpoint"])
        self.assertIsNone(payload["source_checkpoint"])
        self.assertEqual(payload["checkpoint_inheritance"], "NONE_DATASET_TRANSFORMATION_ONLY")
        self.assertEqual(payload["market_absorbing_stop"]["original_mask_active"], original_active)
        self.assertEqual(payload["market_absorbing_stop"]["expanded_mask_active"], 30)
        self.assertEqual(payload["market_absorbing_stop"]["stop_tail_added_active"], 30 - original_active)
        self.assertEqual(
            sum(payload["market_absorbing_stop"]["stop_tail_added_by_family"].values()),
            30 - original_active,
        )
        self.assertTrue(payload["market_absorbing_stop"]["all_rows_fully_active_after_transform"])
        self.assertEqual(payload["family_balance"]["row_counts"], {family: 2 for family in OPTION_IDS})
        self.assertTrue(payload["family_balance"]["rows_exactly_balanced"])
        self.assertTrue(payload["family_balance"]["episodes_exactly_balanced"])
        self.assertEqual(payload["terminal"]["step_gte"], 671)
        self.assertEqual(payload["terminal"]["terminal_rows"], 3)
        self.assertEqual(payload["source"]["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(payload["output"]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_preserves_existing_option_and_unit_role_auxiliary_labels(self) -> None:
        arrays = dict(self.arrays)
        arrays["option_id"] = np.asarray([0, 1, 2, 0, 1, 2], dtype=np.int16)
        arrays["unit_roles"] = np.asarray([
            [3, 3, 3], [2, 2, 2], [1, 1, 1],
            [0, 0, 0], [3, 2, 1], [1, 2, 3],
        ], dtype=np.int16)
        np.savez_compressed(self.source, **arrays)

        report = build_latent_role_dataset(self.source, self.output, self.manifest)
        with np.load(self.output, allow_pickle=False) as written:
            np.testing.assert_array_equal(written["option_id"], arrays["option_id"])
            self.assertEqual(written["option_id"].dtype, arrays["option_id"].dtype)
            np.testing.assert_array_equal(written["unit_roles"], arrays["unit_roles"])
            self.assertEqual(written["unit_roles"].dtype, arrays["unit_roles"].dtype)
        self.assertTrue(report["unit_role_auxiliary_labels"]["preserved_from_source"])
        self.assertEqual(report["source"]["kind"], "per_slot")

    def test_rejects_partial_sequence_without_stop_or_actions_after_stop(self) -> None:
        arrays = dict(self.arrays)
        arrays["market_tokens"] = arrays["market_tokens"].copy()
        arrays["market_tokens"][0, 2] = space.MARKET_INDEX["HIRE"]
        np.savez_compressed(self.source, **arrays)
        with self.assertRaisesRegex(ValueError, "neither an active STOP boundary nor a full market sequence"):
            build_latent_role_dataset(self.source, self.output, self.manifest)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())

        arrays = dict(self.arrays)
        arrays["market_mask"] = arrays["market_mask"].copy()
        arrays["market_mask"][0, 3] = 1
        np.savez_compressed(self.source, **arrays)
        with self.assertRaisesRegex(ValueError, "active actions after its first STOP"):
            build_latent_role_dataset(self.source, self.output, self.manifest)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())

    def test_preserves_full_teacher_sequence_without_stop(self) -> None:
        arrays = dict(self.arrays)
        arrays["market_tokens"] = arrays["market_tokens"].copy()
        arrays["market_quantities"] = arrays["market_quantities"].copy()
        arrays["market_mask"] = arrays["market_mask"].copy()
        arrays["market_tokens"][0] = space.MARKET_INDEX["HIRE"]
        arrays["market_quantities"][0] = np.arange(5, dtype=np.int16)
        arrays["market_mask"][0] = 1
        np.savez_compressed(self.source, **arrays)

        report = build_latent_role_dataset(self.source, self.output, self.manifest)
        with np.load(self.output, allow_pickle=False) as written:
            np.testing.assert_array_equal(written["market_tokens"][0], arrays["market_tokens"][0])
            np.testing.assert_array_equal(
                written["market_quantities"][0], arrays["market_quantities"][0]
            )
            np.testing.assert_array_equal(written["market_mask"][0], arrays["market_mask"][0])
            np.testing.assert_array_equal(
                written["market_roles"][0], np.ones(5, dtype=np.int8)
            )
        self.assertEqual(report["market_absorbing_stop"]["full_sequences_without_stop"], 1)
        self.assertEqual(
            report["market_absorbing_stop"]["full_sequences_without_stop_by_family"]
            ["demand-timing-preemption"],
            1,
        )

    def test_rejects_conflicting_option_family_contract(self) -> None:
        arrays = dict(self.arrays)
        arrays["option_id"] = np.asarray([2, 1, 2, 0, 1, 2], dtype=np.int8)
        np.savez_compressed(self.source, **arrays)
        with self.assertRaisesRegex(ValueError, "option_id conflicts"):
            build_latent_role_dataset(self.source, self.output, self.manifest)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())


if __name__ == "__main__":
    unittest.main()
