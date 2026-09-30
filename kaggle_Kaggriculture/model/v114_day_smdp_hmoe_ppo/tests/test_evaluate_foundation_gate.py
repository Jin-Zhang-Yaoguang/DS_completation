from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluate_foundation_gate import build_schedule, candidate_policy  # noqa: E402
from opponent_registry import load_registry  # noqa: E402


class FoundationGateTest(unittest.TestCase):
    def test_frozen_l1_schedule_is_32_blocks_and_balanced(self) -> None:
        registry = load_registry(ROOT / "opponent_registry.json")
        schedule = build_schedule("l1", 11509100, registry)
        self.assertEqual(len(schedule), 32)
        self.assertEqual(len({row["seed"] for row in schedule}), 32)
        counts = {}
        for row in schedule:
            counts[row["opponent_id"]] = counts.get(row["opponent_id"], 0) + 1
        self.assertEqual(set(counts.values()), {8})

    def test_l0_extension_uses_eight_starter_blocks(self) -> None:
        registry = load_registry(ROOT / "opponent_registry.json")
        schedule = build_schedule("l0_extension", 11509000, registry)
        self.assertEqual(len(schedule), 8)
        self.assertEqual({row["opponent_id"] for row in schedule}, {"builtin:starter"})

    def test_candidate_pool_has_three_distinct_responsibilities(self) -> None:
        self.assertEqual(candidate_policy("DAIRY_BERRY").profile.animal, "COW")
        self.assertEqual(candidate_policy("WOOL_MELON").profile.animal, "SHEEP")
        self.assertEqual(candidate_policy("EXPOSURE_ADAPTIVE_POULTRY").target_geese, 6)


if __name__ == "__main__":
    unittest.main()
