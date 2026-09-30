from __future__ import annotations

import unittest

from kaggle_Kaggriculture.model.v10_replay_lolo_router.collect_router_grid import (
    collector_implementation_fingerprint,
    main,
)


class RouterGridIntegrityTest(unittest.TestCase):
    def test_collection_fingerprint_covers_implementation_files(self) -> None:
        fingerprints = collector_implementation_fingerprint()
        self.assertEqual(
            set(fingerprints),
            {"collect_router_grid.py", "agent_factory.py", "router.py"},
        )
        self.assertTrue(all(len(value) == 64 for value in fingerprints.values()))

    def test_collector_refuses_sealed_test_split(self) -> None:
        with self.assertRaisesRegex(ValueError, "sealed official test split"):
            main(["--seeds-per-split", "1", "--splits", "test", "--smoke"])


if __name__ == "__main__":
    unittest.main()
