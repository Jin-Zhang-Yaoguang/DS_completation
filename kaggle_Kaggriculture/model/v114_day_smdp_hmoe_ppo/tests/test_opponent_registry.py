from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from opponent_registry import (  # noqa: E402
    HARD_GOLD_MIN_TOTAL_RATIO,
    MAX_HISTORY_MILESTONES,
    MAX_MEMBER_RATIO,
    MAX_V76_RATIO,
    STAGE_WEIGHTS,
    build_schedule,
    expand_dual_seat,
    layer_quotas,
    load_registry,
    pfsp_components,
    pfsp_weights,
    validate_schedule,
)
from seed_ledger import DuplicateSeedError, SeedLedger  # noqa: E402


REGISTRY_PATH = HERE / "opponent_registry.json"


class OpponentRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry(REGISTRY_PATH)

    def test_exact_stage_contract_and_100_seed_quotas(self) -> None:
        self.assertEqual(self.registry["stage_weights"], STAGE_WEIGHTS)
        self.assertEqual(
            layer_quotas("survival", 100),
            {"gold_train": 15, "ppo_history": 35, "self_play": 10, "exploiter": 5, "anchor": 35},
        )
        self.assertEqual(
            layer_quotas("improvement", 100),
            {"gold_train": 30, "ppo_history": 35, "self_play": 15, "exploiter": 10, "anchor": 10},
        )
        self.assertEqual(
            layer_quotas("final", 100),
            {"gold_train": 40, "ppo_history": 30, "self_play": 15, "exploiter": 10, "anchor": 5},
        )

    def test_all_stages_respect_quotas_caps_and_hard_gold_floor(self) -> None:
        members = {member["id"]: member for member in self.registry["members"]}
        for stage in STAGE_WEIGHTS:
            with self.subTest(stage=stage):
                schedule = build_schedule(
                    self.registry, stage, seed_start=11400000, seed_blocks=200,
                    pool_seed=20260830, iteration=3,
                )
                report = validate_schedule(self.registry, stage, schedule)
                self.assertEqual(report["layer_counts"], layer_quotas(stage, 200))
                counts = Counter(row.opponent_id for row in schedule)
                self.assertLessEqual(max(counts.values()) / len(schedule), MAX_MEMBER_RATIO)
                v76 = sum(
                    count for member_id, count in counts.items() if members[member_id].get("is_v76")
                )
                self.assertLessEqual(v76 / len(schedule), MAX_V76_RATIO)
                hard_gold = sum(
                    count for member_id, count in counts.items() if members[member_id].get("hard_gold")
                )
                self.assertGreaterEqual(hard_gold / len(schedule), HARD_GOLD_MIN_TOTAL_RATIO)

    def test_schedule_is_reproducible_and_pool_seed_changes_order(self) -> None:
        kwargs = dict(
            registry=self.registry, stage="improvement", seed_start=11410000,
            seed_blocks=64, pool_seed=9917, iteration=2,
        )
        first = build_schedule(**kwargs)
        second = build_schedule(**kwargs)
        changed = build_schedule(**{**kwargs, "pool_seed": 9918})
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(
            Counter(row.opponent_id for row in first),
            Counter(row.opponent_id for row in changed),
        )

    def test_dual_seat_uses_same_seed_and_opponent(self) -> None:
        schedule = build_schedule(
            self.registry, "survival", seed_start=11420000,
            seed_blocks=64, pool_seed=17,
        )
        games = expand_dual_seat(schedule)
        self.assertEqual(len(games), 128)
        by_seed: dict[int, list] = {}
        for game in games:
            by_seed.setdefault(game.seed, []).append(game)
        for assignment in schedule:
            pair = by_seed[assignment.seed]
            self.assertEqual({game.candidate_seat for game in pair}, {0, 1})
            self.assertEqual({game.opponent_id for game in pair}, {assignment.opponent_id})
            self.assertEqual({game.opponent_sha256 for game in pair}, {assignment.opponent_sha256})

    def test_gold_dev_and_blind_are_never_sampled(self) -> None:
        forbidden = {
            member["id"] for member in self.registry["members"]
            if member.get("gold_split") in {"dev", "blind"}
        }
        for stage in STAGE_WEIGHTS:
            schedule = build_schedule(
                self.registry, stage, seed_start=11430000,
                seed_blocks=200, pool_seed=82,
            )
            self.assertTrue(forbidden.isdisjoint(row.opponent_id for row in schedule))

        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        leaked = next(member for member in raw["members"] if member.get("gold_split") == "dev")
        leaked["training_enabled"] = True
        leaked["training_layer"] = "gold_train"
        leaked["base_weight"] = 1.0
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "leaked.json"
            # Preserve path resolution while testing contract validation only.
            raw["path_base"] = str((HERE / "../../..").resolve())
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "may not be sampled"):
                load_registry(path, verify_artifacts=False)

    def test_history_is_bounded_and_identity_fields_are_auditable(self) -> None:
        history = [
            member for member in self.registry["members"]
            if member.get("training_layer") == "ppo_history"
        ]
        self.assertLessEqual(len(history), MAX_HISTORY_MILESTONES)
        for member in self.registry["members"]:
            self.assertTrue(member["role"])
            self.assertTrue(member["lineage"])
            self.assertRegex(member["sha256"], r"^[0-9a-f]{64}$")

    def test_foundation_l1_is_fixed_deduplicated_and_package_verified(self) -> None:
        contract = self.registry["foundation_l1"]
        self.assertEqual(len(contract["representative_ids"]), 4)
        self.assertEqual(contract["fresh_seed_blocks_total"], 32)
        self.assertEqual(contract["fresh_seed_blocks_per_representative"], 8)
        members = {member["id"]: member for member in self.registry["members"]}
        selected = [members[member_id] for member_id in contract["representative_ids"]]
        self.assertEqual(len({member["lineage"] for member in selected}), 4)
        self.assertAlmostEqual(sum(member["foundation_l1_weight"] for member in selected), 1.0)
        self.assertTrue(all(not member["training_enabled"] for member in selected))
        self.assertTrue(all(member["status"] == "FOUNDATION_L1_FIXED_OPPONENT" for member in selected))

    def test_pfsp_uses_smoothing_progress_and_novelty(self) -> None:
        gold = [
            member for member in self.registry["members"]
            if member.get("training_layer") == "gold_train"
        ]
        stats = {
            "members": {
                gold[0]["id"]: {
                    "wins": 16, "draws": 0, "losses": 16,
                    "previous_wins": 8, "previous_draws": 0, "previous_losses": 24,
                    "behavior_novelty": 1.0,
                }
            }
        }
        components = pfsp_components(gold[0], stats["members"][gold[0]["id"]])
        self.assertAlmostEqual(components["smoothed_score_rate"], 0.5)
        self.assertGreater(components["learning_progress"], 0.0)
        self.assertEqual(components["behavior_novelty"], 1.0)
        weights = pfsp_weights(gold, stats)
        self.assertAlmostEqual(sum(weights.values()), 1.0)
        self.assertGreater(weights[gold[0]["id"]], min(weights.values()))


class SeedLedgerTest(unittest.TestCase):
    def test_fresh_exposed_dev_blind_and_global_duplicate_prevention(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ledger.json"
            ledger = SeedLedger(path)
            ledger.reserve(
                7, split="train", campaign_id="train-a", opponent_id="anchor_starter",
                registry_sha256="a" * 64,
            )
            ledger.reserve(
                8, split="dev", campaign_id="dev-a", opponent_id="gold_dev_v54_terminal",
                registry_sha256="a" * 64,
            )
            ledger.reserve(
                9, split="blind", campaign_id="blind-a",
                opponent_id="gold_blind_v66_market_margin", registry_sha256="a" * 64,
            )
            self.assertEqual(ledger.snapshot()["indexes"]["fresh"], [7, 8, 9])
            self.assertEqual(ledger.snapshot()["indexes"]["dev"], [8])
            self.assertEqual(ledger.snapshot()["indexes"]["blind"], [9])
            ledger.mark_exposed(7, split="train", campaign_id="train-a")
            self.assertEqual(ledger.snapshot()["indexes"]["exposed"], [7])
            with self.assertRaises(DuplicateSeedError):
                ledger.reserve(
                    7, split="blind", campaign_id="blind-b",
                    opponent_id="gold_blind_v66_market_margin", registry_sha256="a" * 64,
                )
            with self.assertRaises(DuplicateSeedError):
                ledger.mark_exposed(7)

            reloaded = SeedLedger(path)
            self.assertEqual(reloaded.snapshot(), ledger.snapshot())
            self.assertEqual(reloaded.sha256(), ledger.sha256())

    def test_schedule_reservation_is_atomic_and_dual_seat(self) -> None:
        registry = load_registry(REGISTRY_PATH)
        schedule = build_schedule(
            registry, "survival", seed_start=11440000,
            seed_blocks=16, pool_seed=5,
        )
        ledger = SeedLedger()
        reserved = ledger.reserve_schedule(
            schedule, split="train", campaign_id="v4-0-test",
            registry_sha256=registry["registry_sha256"],
        )
        self.assertEqual(len(reserved), 16)
        self.assertTrue(all(row["seats"] == [0, 1] for row in reserved))
        with self.assertRaises(DuplicateSeedError):
            ledger.reserve_schedule(
                schedule, split="dev", campaign_id="reuse-test",
                registry_sha256=registry["registry_sha256"],
            )
        ledger.mark_schedule_exposed(schedule)
        self.assertEqual(len(ledger.snapshot()["indexes"]["exposed"]), 16)


if __name__ == "__main__":
    unittest.main()
