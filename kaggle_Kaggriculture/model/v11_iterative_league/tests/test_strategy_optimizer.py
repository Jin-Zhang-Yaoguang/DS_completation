from __future__ import annotations

import json
import hashlib
import inspect
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import strategy_optimizer as optimizer  # noqa: E402
import candidate_agent  # noqa: E402


def game(task: str, a: str, b: str, seat: int, score: float, margin: float, date: str, seed: int):
    return {
        "schema": "kaggriculture-v10-pairwise-closed-loop-1",
        "task_id": task,
        "pair_id": f"{a}__vs__{b}",
        "model_a": a,
        "model_b": b,
        "model_a_seat": seat,
        "source": {
            "date": date,
            "episode_id": str(seed),
            "seed": seed,
            "split": "train",
        },
        "done": True,
        "error": None,
        "score_a": score,
        "margin_a": margin,
        "reward_a": 1000 + margin,
        "reward_b": 1000,
    }


class StrategyOptimizerTests(unittest.TestCase):
    def test_recorded_real_closed_loop_smoke_is_current(self):
        evidence = json.loads(
            (HERE / "tests" / "real_closed_loop_smoke.json").read_text(encoding="utf-8")
        )
        self.assertTrue(evidence["passed"])
        self.assertFalse(evidence["sealed_test_used"])
        self.assertEqual(evidence["seeds"], 6)
        self.assertEqual(evidence["candidate_games"], 12)
        self.assertEqual(evidence["parent_control_games"], 12)
        self.assertEqual(
            {item["date"] for item in evidence["development_sources"]},
            {"2026-08-18", "2026-08-19", "2026-08-20"},
        )
        self.assertGreater(evidence["changed_games"], 0)
        self.assertGreater(evidence["changed_steps"], 0)
        independent = evidence["independent_admission"]
        self.assertTrue(independent["passed"])
        self.assertEqual(independent["candidate_games"], 12)
        self.assertEqual(independent["parent_control_games"], 12)
        self.assertTrue(independent["all_done"])
        self.assertTrue(independent["all_720_steps"])
        self.assertTrue(independent["zero_stderr"])
        source_hash = hashlib.sha256(
            inspect.getsource(optimizer.run_admission_smoke).encode()
        ).hexdigest()
        self.assertEqual(source_hash, evidence["run_admission_smoke_source_sha256"])
        for filename in ("candidate_agent.py", "mutation_catalog.py", "admission_smoke.py"):
            actual = hashlib.sha256((HERE / filename).read_bytes()).hexdigest()
            self.assertEqual(actual, evidence["code_sha256"][filename])

    def test_ranking_and_slices(self):
        rows = [
            game("1", "a", "b", 0, 1.0, 100, "2026-08-18", 1),
            game("2", "a", "b", 1, 0.5, 0, "2026-08-19", 2),
            game("3", "a", "c", 0, 0.0, -20, "2026-08-20", 3),
        ]
        result = optimizer.compute_diagnostics(rows)
        self.assertEqual(result["leader"], "a")
        self.assertEqual(result["models"]["a"]["overall"]["wins"], 1)
        self.assertEqual(result["models"]["a"]["overall"]["draws"], 1)
        self.assertEqual(result["models"]["a"]["overall"]["losses"], 1)
        self.assertEqual(result["models"]["a"]["by_seat"]["0"]["games"], 2)

    def test_sealed_test_is_rejected(self):
        row = game("1", "a", "b", 0, 1.0, 1, "2026-08-18", 1)
        row["source"]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "sealed test"):
            optimizer.assert_no_sealed_test([row], {})
        with self.assertRaisesRegex(ValueError, "sealed test"):
            optimizer.assert_no_sealed_test([], {"provenance": {"split": "test"}})

    def test_unknown_or_missing_split_is_rejected(self):
        row = game("1", "a", "b", 0, 1.0, 1, "2026-08-18", 1)
        row["source"]["split"] = "unknown"
        with self.assertRaisesRegex(ValueError, "explicit development split"):
            optimizer.assert_no_sealed_test([row], {})
        row["source"].pop("split")
        with self.assertRaisesRegex(ValueError, "explicit development split"):
            optimizer.assert_no_sealed_test([row], {})

    def test_formal_input_validation_deduplicates_retries(self):
        rows = []
        dates = ("2026-08-18", "2026-08-19", "2026-08-20")
        for source_index in range(100):
            for seat in (0, 1):
                row = game(
                    f"task-{source_index}-{seat}",
                    "a",
                    "b",
                    seat,
                    1.0,
                    10.0,
                    dates[source_index % 3],
                    1000 + source_index,
                )
                row["run_fingerprint"] = "run-1"
                rows.append(row)
        summary = {
            "round": 1,
            "complete": True,
            "run_fingerprint": "run-1",
            "model_ids": ["a", "b"],
            "panel": {
                "count": 100,
                "unique_seeds": 100,
                "date_counts": {date: 1 for date in dates},
                "splits": ["train", "validation"],
            },
            "scheduled_games": 200,
            "valid_games": 200,
            "expected_pairs": 1,
            "complete_pairs": 1,
            "panel_integrity": {"all_pairs_share_exact_panel": True},
        }
        # One byte-identical successful retry and one failed historical attempt
        # must not inflate the diagnostic sample.
        rows.append(dict(rows[0]))
        failed = dict(rows[1])
        failed["done"] = False
        failed["error"] = "Timeout"
        rows.append(failed)
        valid, audit = optimizer.validate_league_round(rows, summary, 1)
        self.assertEqual(len(valid), 200)
        self.assertEqual(audit["identical_success_duplicates"], 1)
        self.assertEqual(audit["ignored_failed_attempts"], 1)

    def test_representative_losses_cover_categories(self):
        rows = [
            game(str(index), "a", "b" if index < 3 else "c", index % 2, 0.0, -index, f"2026-08-{18 + index % 3:02d}", index + 10)
            for index in range(1, 7)
        ]
        result = optimizer.compute_diagnostics(rows)
        selected = optimizer.select_representative_losses(result, "a", 3)
        self.assertEqual(len(selected), 3)
        self.assertIn("惨败", {item["category"] for item in selected})

    def test_completed_parent_games_blacklist_catastrophe_and_rank_transfer(self):
        def model(opponent, score_rate, mean_margin):
            wins = int(round(score_rate * 200))
            return {
                "overall": {"games": 200, "score_rate": score_rate},
                "by_opponent": {
                    opponent: {
                        "games": 200,
                        "valid_games": 200,
                        "wins": wins,
                        "draws": 0,
                        "losses": 200 - wins,
                        "score_rate": score_rate,
                        "mean_margin": mean_margin,
                    }
                },
            }

        diagnosis = {
            "models": {
                "baseline_v1": {"overall": {"games": 200, "score_rate": 0.4}},
                "baseline_v2": {"overall": {"games": 200, "score_rate": 0.4}},
                "learned_router": {"overall": {"games": 200, "score_rate": 0.7}},
                "v1_topdays": model("baseline_v1", 0.65, 1000),
                "v2_topdays": model("baseline_v2", 0.60, 800),
                "r001_floor": model("learned_router", 0.04, -30000),
            }
        }
        registry = [
            {
                "id": "v1_topdays",
                "lineage": ["baseline_v1", "v1_topdays"],
                "family": "v1+topdays",
            },
            {
                "id": "v2_topdays",
                "lineage": ["baseline_v2", "v2_topdays"],
                "family": "v2+topdays",
            },
            {
                "id": "r001_floor",
                "parent_models": ["learned_router"],
                "mutation": "premium_floor_guard",
            },
        ]
        evidence = optimizer.registered_mutation_evidence(diagnosis, registry)
        self.assertEqual(evidence["excluded_mutations"], ["premium_floor_guard"])
        self.assertEqual(evidence["strong_transfer_priority"], ["topday_animal_throttle"])
        topday = next(
            item
            for item in evidence["mechanism_groups"]
            if item["mutation"] == "topday_animal_throttle"
        )
        self.assertEqual(topday["lineage_count"], 2)
        self.assertTrue(topday["strong_transfer_evidence"])

        candidates = optimizer.build_parameter_candidates(
            "learned_router",
            "premium_floor_guard",
            {"minimum_price_ratio": 0.45, "release_step": 696},
            registry,
            evidence,
        )
        self.assertTrue(candidates)
        self.assertEqual(candidates[0][0], "topday_animal_throttle")
        self.assertNotIn("premium_floor_guard", {name for name, _ in candidates})

    def test_transfer_priority_is_mechanism_agnostic(self):
        diagnosis = {
            "models": {
                "baseline_v1": {"overall": {}},
                "baseline_v2": {"overall": {}},
                "cap_v1": {
                    "by_opponent": {
                        "baseline_v1": {
                            "games": 200,
                            "valid_games": 200,
                            "wins": 130,
                            "draws": 0,
                            "losses": 70,
                            "score_rate": 0.65,
                            "mean_margin": 500,
                        }
                    }
                },
                "cap_v2": {
                    "by_opponent": {
                        "baseline_v2": {
                            "games": 200,
                            "valid_games": 200,
                            "wins": 120,
                            "draws": 0,
                            "losses": 80,
                            "score_rate": 0.60,
                            "mean_margin": 300,
                        }
                    }
                },
            }
        }
        registry = [
            {
                "id": "cap_v1",
                "parent_models": ["baseline_v1"],
                "mutation": "general_batch_cap",
            },
            {
                "id": "cap_v2",
                "parent_models": ["baseline_v2"],
                "mutation": "general_batch_cap",
            },
        ]
        evidence = optimizer.registered_mutation_evidence(diagnosis, registry)
        self.assertEqual(evidence["strong_transfer_priority"], ["general_batch_cap"])

    def test_unambiguous_legacy_alias_can_blacklist_a_catastrophic_family(self):
        diagnosis = {
            "models": {
                "baseline_v5": {"overall": {}},
                "v5_price_slot": {
                    "by_opponent": {
                        "baseline_v5": {
                            "games": 200,
                            "valid_games": 200,
                            "wins": 9,
                            "draws": 0,
                            "losses": 191,
                            "score_rate": 0.045,
                            "mean_margin": -5082.02,
                        }
                    }
                },
            }
        }
        registry = [
            {
                "id": "v5_price_slot",
                "family": "v5_rule_hybrid+price_slot",
                "lineage": ["baseline_v5", "v5_price_slot"],
            }
        ]
        evidence = optimizer.registered_mutation_evidence(diagnosis, registry)
        self.assertEqual(evidence["excluded_mutations"], ["value_slot_priority"])
        self.assertEqual(
            evidence["catastrophic_evidence"][0]["mapping_source"],
            "inferred_alias",
        )

    def test_smoke_requires_real_component_difference(self):
        registry = ROOT / "model" / "v10_replay_lolo_router" / "fixed_registry.json"
        sources = [
            {
                "date": f"2026-08-{18 + index % 3:02d}",
                "episode_id": str(100 + index),
                "seed": 100 + index,
                "split": "train",
            }
            for index in range(6)
        ]

        def fake_run(_registry, target_id, _opponent, _seat, _seed):
            action = {
                "farmer": ["PASS"],
                "hands": [],
                "market": [["SELL", "WHEAT", 1]] if target_id.startswith("r001_") else [],
            }
            return {
                "statuses": ["DONE", "DONE"],
                "steps": 720,
                "actions": [action] * 719,
                "stderr": "",
            }

        with tempfile.TemporaryDirectory() as temporary:
            smoke_registry = Path(temporary) / "smoke.json"
            with patch.object(optimizer, "_run_target_trajectory", side_effect=fake_run):
                report = optimizer.run_admission_smoke(
                    registry,
                    smoke_registry,
                    "r001_baseline_v1_value_slot_priority",
                    "baseline_v1",
                    "value_slot_priority",
                    {},
                    sources,
                    1,
                    workers=1,
                )
        self.assertTrue(report["passed"])
        self.assertEqual(report["changed_games"], 12)
        self.assertGreater(report["market_changed_steps"], 0)
        self.assertEqual(report["farmer_changed_steps"], 0)
        self.assertEqual(report["hands_changed_steps"], 0)

    def test_candidate_can_wrap_a_router_parent(self):
        source_path = ROOT / "model" / "v10_replay_lolo_router" / "fixed_registry.json"
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        for spec in payload["models"]:
            for key in ("path", "module_path", "weights"):
                if spec.get(key):
                    spec[key] = str((source_path.parent / spec[key]).resolve())
            spec["code_paths"] = [
                str((source_path.parent / value).resolve())
                for value in (spec.get("code_paths") or [])
            ]
        payload["models"].append(
            {
                "id": "test_rule_router",
                "kind": "router",
                "router_kind": "rule",
                "experts": ["baseline_v1", "baseline_v2"],
                "anchor": "baseline_v1",
                "switch_step": 72,
                "rule": {"default_priority": ["baseline_v1", "baseline_v2"]},
                "code_paths": [
                    str(
                        (
                            ROOT
                            / "model"
                            / "v10_replay_lolo_router"
                            / "router.py"
                        ).resolve()
                    )
                ],
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / "router_registry.json"
            registry.write_text(json.dumps(payload), encoding="utf-8")
            wrapped = candidate_agent.create_agent(
                registry,
                "test_rule_router",
                "value_slot_priority",
                {"min_sell_orders": 2},
                "router_child",
            )
        self.assertEqual(wrapped.parent_id, "test_rule_router")


if __name__ == "__main__":
    unittest.main()
