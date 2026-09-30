from __future__ import annotations

from copy import deepcopy
import unittest

from kaggle_Kaggriculture.model.v11_iterative_league import (
    audit_fast_router_challenge as challenge,
)
from kaggle_Kaggriculture.model.v11_iterative_league import verify_fast_router as formal


def _row() -> dict:
    result = {
        "engine": "kaggle_environments.make(kaggriculture)",
        "closed_loop": True,
        "trace_agent": False,
        "rng_seed": 1,
        "statuses": ["DONE", "DONE"],
        "rewards": [1.0, 0.0],
        "action_sha256": "a" * 64,
        "calls": 719,
        "selected": "baseline_v1",
        "selection_reason": "default",
        "selection_eligible": list(formal.OPPONENTS),
        "prefix_complete": True,
        "prefix_match": {item: True for item in formal.OPPONENTS},
        "prefix_first_mismatch": {item: None for item in formal.OPPONENTS},
        "prefix_errors": {item: [] for item in formal.OPPONENTS},
        "selected_fallbacks": 0,
        "runtime_errors": [],
        "fast_shadow": False,
    }
    fast = deepcopy(result)
    fast["fast_shadow"] = True
    return {
        "schema": formal.SCHEMA,
        "task_id": "task",
        "run_fingerprint": "f" * 64,
        "router_id": "rule_router",
        "opponent_id": "baseline_v1",
        "source": {
            "date": "2026-08-18",
            "episode_id": "episode",
            "seed": 1,
            "split": "validation",
        },
        "router_seat": 0,
        "error": None,
        "action_equal": True,
        "field_equal": {key: True for key in formal.EXACT_FIELDS},
        "original": result,
        "fast": fast,
        "equivalent": True,
        "elapsed_seconds": 1.0,
        "semantic_sha256": "not-trusted-by-challenge",
    }


class FastRouterFreshChallengeTest(unittest.TestCase):
    def test_report_hash_derives_unique_deterministic_source_indices(self) -> None:
        first = challenge.challenge_source_indices("a" * 64, 100, 4)
        second = challenge.challenge_source_indices("a" * 64, 100, 4)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(len(set(first)), 4)
        self.assertTrue(all(0 <= value < 100 for value in first))
        self.assertNotEqual(
            first, challenge.challenge_source_indices("b" * 64, 100, 4)
        )

    def test_semantic_comparison_ignores_timing_but_detects_raw_change(self) -> None:
        stored = _row()
        fresh = deepcopy(stored)
        fresh["elapsed_seconds"] = 99.0
        fresh["semantic_sha256"] = "different-outer-hash"
        self.assertEqual(
            challenge._semantic_sha256(stored),
            challenge._semantic_sha256(fresh),
        )
        fresh["fast"]["rewards"] = [999.0, -999.0]
        self.assertNotEqual(
            challenge._semantic_sha256(stored),
            challenge._semantic_sha256(fresh),
        )

    def test_source_count_is_bounded_to_small_audit(self) -> None:
        with self.assertRaisesRegex(ValueError, "2-4"):
            challenge.challenge_source_indices("a" * 64, 100, 1)
        with self.assertRaisesRegex(ValueError, "2-4"):
            challenge.challenge_source_indices("a" * 64, 100, 5)


if __name__ == "__main__":
    unittest.main()
