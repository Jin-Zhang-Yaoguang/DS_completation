from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from kaggle_Kaggriculture.model.v11_iterative_league import verify_fast_router as verify
from kaggle_Kaggriculture.model.v11_iterative_league import (
    audit_fast_router_challenge as challenge,
)
from kaggle_Kaggriculture.model.v11_iterative_league.materialize_fast_registry import (
    materialize,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import load_registry


V10 = Path(__file__).resolve().parents[2] / "v10_replay_lolo_router"


def _source() -> dict:
    return {
        "date": "2026-08-18",
        "episode_id": "episode-1",
        "seed": 123,
        "split": "validation",
        "source_path": "metadata-only",
        "lineage_fold": "v1",
    }


def _result(*, fast: bool) -> dict:
    return {
        "engine": "kaggle_environments.make(kaggriculture)",
        "closed_loop": True,
        "trace_agent": False,
        "rng_seed": 7,
        "statuses": ["DONE", "DONE"],
        "rewards": [1.0, 0.0],
        "action_sha256": "a" * 64,
        "calls": 719,
        "selected": "baseline_v1",
        "selection_reason": "default",
        "selection_eligible": list(verify.OPPONENTS),
        "prefix_complete": True,
        "prefix_match": {item: True for item in verify.OPPONENTS},
        "prefix_first_mismatch": {item: None for item in verify.OPPONENTS},
        "prefix_errors": {item: [] for item in verify.OPPONENTS},
        "selected_fallbacks": 0,
        "runtime_errors": [],
        "fast_shadow": fast,
    }


def _success(task: dict) -> dict:
    original = _result(fast=False)
    fast = _result(fast=True)
    row = {
        **{key: task[key] for key in (
            "schema", "task_id", "run_fingerprint", "router_id",
            "opponent_id", "source", "router_seat",
        )},
        "error": None,
        "action_equal": True,
        "field_equal": {key: True for key in verify.EXACT_FIELDS},
        "original": original,
        "fast": fast,
        "equivalent": True,
        "elapsed_seconds": 0.1,
    }
    semantic = {
        key: value for key, value in row.items() if key != "elapsed_seconds"
    }
    row["semantic_sha256"] = verify._canonical_sha256(semantic)
    return row


class FastRouterEquivalenceTest(unittest.TestCase):
    def test_task_ids_resume_and_conflicting_success_rejection(self) -> None:
        tasks = verify.build_tasks(Path("/tmp/registry.json"), "f" * 64, [_source()])
        self.assertEqual(len(tasks), 16)
        self.assertEqual(len({task["task_id"] for task in tasks}), 16)
        expected = {task["task_id"]: task for task in tasks}
        row = _success(tasks[0])
        with tempfile.TemporaryDirectory() as temporary:
            games = Path(temporary) / "games.jsonl"
            verify._append(games, row)
            successful, audit = verify._read_existing(games, "f" * 64, expected)
            self.assertEqual(set(successful), {tasks[0]["task_id"]})
            self.assertEqual(audit["successful_tasks"], 1)

            conflicting = deepcopy(row)
            conflicting["original"]["selected"] = "baseline_v2"
            conflicting["fast"]["selected"] = "baseline_v2"
            semantic = {
                key: value
                for key, value in conflicting.items()
                if key not in {"elapsed_seconds", "semantic_sha256"}
            }
            conflicting["semantic_sha256"] = verify._canonical_sha256(semantic)
            verify._append(games, conflicting)
            with self.assertRaisesRegex(ValueError, "conflicting successful"):
                verify._read_existing(games, "f" * 64, expected)

    def test_semantic_hash_tampering_is_rejected(self) -> None:
        task = verify.build_tasks(Path("/tmp/registry.json"), "f" * 64, [_source()])[0]
        row = _success(task)
        row["semantic_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            games = Path(temporary) / "games.jsonl"
            verify._append(games, row)
            with self.assertRaisesRegex(ValueError, "semantic hash mismatch"):
                verify._read_existing(games, "f" * 64, {task["task_id"]: task})

    def test_success_validation_recomputes_raw_evidence_and_health(self) -> None:
        task = verify.build_tasks(Path("/tmp/registry.json"), "f" * 64, [_source()])[0]
        valid = _success(task)
        verify._validate_success(valid)

        reward_forgery = deepcopy(valid)
        reward_forgery["fast"]["rewards"] = [999.0, -999.0]
        with self.assertRaisesRegex(ValueError, "exact-field"):
            verify._validate_success(reward_forgery)

        invalid_selected = deepcopy(valid)
        invalid_selected["original"]["selected"] = "not-an-expert"
        invalid_selected["fast"]["selected"] = "not-an-expert"
        with self.assertRaisesRegex(ValueError, "health"):
            verify._validate_success(invalid_selected)

        empty_prefix = deepcopy(valid)
        for side in ("original", "fast"):
            empty_prefix[side]["prefix_match"] = {}
            empty_prefix[side]["prefix_errors"] = {}
            empty_prefix[side]["prefix_first_mismatch"] = {}
        with self.assertRaisesRegex(ValueError, "health"):
            verify._validate_success(empty_prefix)

        bad_calls = deepcopy(valid)
        bad_calls["original"]["calls"] = 720
        bad_calls["fast"]["calls"] = 720
        with self.assertRaisesRegex(ValueError, "health"):
            verify._validate_success(bad_calls)

        non_finite_reward = deepcopy(valid)
        non_finite = [float("nan"), 0.0]
        non_finite_reward["original"]["rewards"] = non_finite
        non_finite_reward["fast"]["rewards"] = non_finite
        with self.assertRaisesRegex(ValueError, "health"):
            verify._validate_success(non_finite_reward)

        invalid_action_hash = deepcopy(valid)
        invalid_action_hash["original"]["action_sha256"] = "not-a-sha"
        invalid_action_hash["fast"]["action_sha256"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "health"):
            verify._validate_success(invalid_action_hash)

    def test_same_name_serving_replacement_fails_authoritative_final14_gate(self) -> None:
        payload = json.loads((V10 / "final_registry.json").read_text(encoding="utf-8"))
        models = {item["id"]: item for item in payload["models"]}
        replacement = deepcopy(models["baseline_v2"])
        replacement["id"] = "baseline_v1"
        payload["models"] = [
            replacement if item["id"] == "baseline_v1" else item
            for item in payload["models"]
        ]
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="tampered-final14-",
            dir=V10,
            encoding="utf-8",
        ) as handle:
            json.dump(payload, handle)
            handle.flush()
            registry = load_registry(Path(handle.name))
            with self.assertRaisesRegex(ValueError, "frozen final-14"):
                verify._validate_final14_audit(registry)

    def test_rng_is_reset_before_construction_make_and_run(self) -> None:
        class FakeRouter:
            def __call__(self, _obs, _configuration=None):
                return {"farmer": ["PASS"], "hands": [], "market": []}

            def diagnostics(self):
                return {
                    "selected": "baseline_v1",
                    "prefix_complete": True,
                    "prefix_match": {"baseline_v1": True},
                    "prefix_first_mismatch": {"baseline_v1": None},
                    "prefix_errors": {"baseline_v1": []},
                    "selected_fallbacks": 0,
                    "runtime_errors": [],
                }

        class FakeEnv:
            state = [
                SimpleNamespace(status="DONE", reward=1.0),
                SimpleNamespace(status="DONE", reward=0.0),
            ]

            def run(self, _agents):
                return None

        with (
            patch.object(verify, "create_agent", return_value=FakeRouter()),
            patch("kaggle_environments.make", return_value=FakeEnv()),
            patch.object(verify.random, "seed") as random_seed,
            patch.object(verify.np.random, "seed") as numpy_seed,
        ):
            result = verify._run(object(), FakeRouter, "baseline_v1", 17, 1)
        expected_seed = (17 * 104729 + 1009) % (2**32 - 1)
        self.assertEqual(random_seed.call_count, 3)
        self.assertEqual(numpy_seed.call_count, 3)
        self.assertEqual([call.args[0] for call in random_seed.call_args_list], [expected_seed] * 3)
        self.assertEqual([call.args[0] for call in numpy_seed.call_args_list], [expected_seed] * 3)
        self.assertEqual(result["statuses"], ["DONE", "DONE"])

    def test_materializer_rejects_unsealed_or_forged_formal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "final.json"
            source.write_text(
                json.dumps(
                    {
                        "schema": "kaggriculture-v10-final-registry-1",
                        "models": [{"id": "placeholder", "kind": "python"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "equivalence-report"):
                materialize(source, root / "fast.json")

            forged = root / "forged.json"
            forged.write_text(
                json.dumps(
                    {
                        "schema": verify.REPORT_SCHEMA,
                        "formal": True,
                        "formal_complete": True,
                        "all_equivalent": True,
                        "test_sources_accessed": False,
                        "environment_split": "validation",
                        "routers": list(verify.ROUTERS),
                        "opponents": list(verify.OPPONENTS),
                        "seats": [0, 1],
                        "source_count": 100,
                        "expected_comparisons": 1600,
                        "successful_comparisons": 1600,
                        "missing_comparisons": 0,
                        "missing_task_ids": [],
                        "exact_cell_coverage": True,
                        "sources": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source panel"):
                materialize(source, root / "fast.json", forged, forged)

    def test_missing_or_forged_fresh_challenge_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "final.json"
            source.write_text(
                json.dumps(
                    {
                        "schema": "kaggriculture-v10-final-registry-1",
                        "models": [{"id": "placeholder", "kind": "python"}],
                    }
                ),
                encoding="utf-8",
            )
            formal_report = root / "formal.json"
            formal_report.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "challenge-report"):
                materialize(source, root / "fast.json", formal_report)

            sources = [
                {
                    "date": (
                        "2026-08-18"
                        if index < 34
                        else "2026-08-19"
                        if index < 67
                        else "2026-08-20"
                    ),
                    "episode_id": f"episode-{index}",
                    "seed": index,
                    "split": "validation",
                }
                for index in range(100)
            ]
            games = root / "games.jsonl"
            games.write_text("", encoding="utf-8")
            formal_report.write_text(
                json.dumps(
                    {
                        "sources": sources,
                        "fit_exclusions": str(root / "fit.json"),
                        "source_final_registry": str(source),
                        "run_fingerprint": "f" * 64,
                        "games_jsonl": str(games),
                    }
                ),
                encoding="utf-8",
            )
            report_sha = challenge._sha256(formal_report)
            indices = challenge.challenge_source_indices(report_sha, 100, 4)
            forged = root / "challenge.json"
            forged.write_text(
                json.dumps(
                    {
                        "schema": challenge.SCHEMA,
                        "read_only_input_audit": True,
                        "formal_gate_revalidated": True,
                        "test_sources_accessed": False,
                        "environment_split": "validation",
                        "passed": True,
                        "source_count": 4,
                        "expected_comparisons": 64,
                        "fresh_comparisons": 64,
                        "environment_games": 128,
                        "exact_matches": 64,
                        "mismatches": 0,
                        "routers": list(verify.ROUTERS),
                        "opponents": list(verify.OPPONENTS),
                        "seats": [0, 1],
                        "challenge_implementation_sha256": challenge.implementation_fingerprint(),
                        "report": str(formal_report),
                        "report_file_sha256": report_sha,
                        "games_jsonl": str(games),
                        "games_jsonl_file_sha256": challenge._sha256(games),
                        "formal_seal": {},
                        "source_indices": indices,
                        "sources": [sources[index] for index in indices],
                        "comparisons": [],
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(challenge.formal, "validate_formal_report", return_value={}),
                patch.object(challenge.formal, "_source_rows", return_value=(sources, {})),
                patch.object(challenge.formal, "_read_existing", return_value=({}, {})),
            ):
                with self.assertRaisesRegex(ValueError, "incomplete/duplicated"):
                    challenge.validate_challenge_report(forged, formal_report)


if __name__ == "__main__":
    unittest.main()
