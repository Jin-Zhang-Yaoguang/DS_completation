from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from replay_inspector import compact_action, compress_records, farm_summary  # noqa: E402


class ReplayInspectorTests(unittest.TestCase):
    def test_compact_action_omits_passes(self):
        result = compact_action(
            {
                "farmer": ["PASS"],
                "hands": [["PASS"], ["WATER"]],
                "market": [["SELL", "MILK", 3]],
            }
        )
        self.assertNotIn("farmer", result)
        self.assertEqual(result["hands"], [{"hand": 1, "action": ["WATER"]}])

    def test_farm_summary_is_aggregate_not_raw_tiles(self):
        result = farm_summary(
            {
                "farms": [
                    {
                        "money": 10,
                        "hands": [[1, 1]],
                        "tiles": [[None, "LOCKED", {"kind": "PASTURE", "animal": "COW"}]],
                    }
                ]
            }
        )
        self.assertEqual(result[0]["tiles"]["ANIMAL:COW"], 1)
        self.assertNotIn("raw_tiles", result[0])

    def test_trace_compression_records_deltas(self):
        base = {
            "day": 0,
            "hour": 0,
            "action": {},
            "action_sha16": "a",
            "farms": [{"money": 10, "tiles": {}}, {"money": 10, "tiles": {}}],
            "private": {"shed": {}, "seeds": {}, "carried": {}, "shed_total": 0},
            "market": {"prices": {"WHEAT": 25}, "inventory": {"WHEAT": 1}},
        }
        later = {
            **base,
            "step": 1,
            "hour": 1,
            "action": {"market": [["SELL", "WHEAT", 1]]},
            "action_sha16": "b",
            "farms": [{"money": 35, "tiles": {}}, {"money": 10, "tiles": {}}],
            "market": {"prices": {"WHEAT": 24}, "inventory": {"WHEAT": 2}},
        }
        first = {**base, "step": 0}
        traces = [
            SimpleNamespace(seat=0, records=[first, later]),
            SimpleNamespace(seat=1, records=[first, first]),
        ]
        report = compress_records(traces)
        self.assertTrue(report["farm_events"])
        self.assertTrue(report["market_events"])
        self.assertTrue(report["action_events"])


if __name__ == "__main__":
    unittest.main()

