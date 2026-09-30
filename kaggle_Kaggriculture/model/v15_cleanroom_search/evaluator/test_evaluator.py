from __future__ import annotations

import json
import copy
from pathlib import Path
import tempfile
import unittest

from .inventory import build_payloads
from .protocol import atomic_create_json
from .run_evaluation import (
    _bind_candidate_stage,
    build_tasks,
    dry_run_payload,
    index_expected_tasks,
    validate_resume_file,
)
from .scorecard import (
    GAME_ENGINE,
    GAME_SCHEMA,
    TASK_BINDING_FIELDS,
    audit_and_score,
    read_jsonl,
    validate_public_feedback,
)
from .source_control import reserve_panel


def panel_records() -> list[dict]:
    rows = []
    counts = (("2026-08-18", 34), ("2026-08-19", 33), ("2026-08-20", 33))
    seed = 7_000_000_000
    for date, count in counts:
        for _ in range(count):
            seed += 1
            rows.append(
                {
                    "date": date,
                    "seed": seed,
                    "episode_id": str(seed),
                    "split": "train",
                    "source_path": "metadata-only",
                    "lineage_fold": "",
                }
            )
    return rows


def rewards_for(score: float, seat: int) -> list[float]:
    if score == 0.5:
        return [1.0, 1.0]
    own, other = ((2.0, 1.0) if score == 1.0 else (1.0, 2.0))
    return [own, other] if seat == 0 else [other, own]


def game_row(task: dict, score: float) -> dict:
    seat = task["model_a_seat"]
    policy = task["model_a"]
    opponent = task["model_b"]
    rewards = rewards_for(score, seat)
    own = rewards[seat]
    other = rewards[1 - seat]
    return {
        **{field: copy.deepcopy(task[field]) for field in TASK_BINDING_FIELDS},
        "schema": GAME_SCHEMA,
        "engine": GAME_ENGINE,
        "closed_loop": True,
        "trace_agent": False,
        "done": True,
        "statuses": ["DONE", "DONE"],
        "error": None,
        "rewards": rewards,
        "reward_a": own,
        "reward_b": other,
        "margin_a": own - other,
        "seat_models": [policy, opponent] if seat == 0 else [opponent, policy],
        "score_a": score,
    }


def expected_task_map(rows: list[dict]) -> dict[str, dict]:
    return {
        row["task_id"]: {field: copy.deepcopy(row[field]) for field in TASK_BINDING_FIELDS}
        for row in rows
    }


def synthetic_rows(panel: list[dict]) -> list[dict]:
    rows = []
    index = 0
    for policy in ("candidate", "parent"):
        for opponent in ("p1", "p2"):
            for source in panel:
                for seat in (0, 1):
                    index += 1
                    if policy == "candidate" and opponent == "p1":
                        score = 1.0
                    elif policy == "candidate" and opponent == "p2":
                        score = 1.0 if seat == 0 else 0.0
                    elif policy == "parent" and opponent == "p1":
                        score = 0.5
                    else:
                        score = 0.0
                    task = {
                        "task_id": f"task-{index}",
                        "run_fingerprint": "f" * 64,
                        "pair_id": f"{policy}__vs__{opponent}",
                        "model_a": policy,
                        "model_b": opponent,
                        "model_a_seat": seat,
                        "source": dict(source),
                    }
                    rows.append(game_row(task, score))
    return rows


class InventoryTests(unittest.TestCase):
    def test_exact_archive_and_lineage_deduplication(self) -> None:
        inventory, lineage, registry, audit = build_payloads(materialize=False)
        self.assertEqual(inventory["qualifying_submission_rows"], 12)
        self.assertEqual(inventory["local_archive_records"], 11)
        self.assertEqual(inventory["exact_serving_unique_records"], 11)
        self.assertEqual(lineage["development_lineages"], 7)
        self.assertEqual(lineage["development_models"], 7)
        self.assertEqual(lineage["hidden_lineages"], 7)
        self.assertEqual(lineage["hidden_models"], 11)
        self.assertEqual(len(lineage["lineages"]), 7)
        self.assertEqual(len(lineage["models"]), 11)
        self.assertEqual(len(registry["models"]), 11)
        self.assertEqual(
            sum(bool(row["development_representative"]) for row in lineage["models"]),
            7,
        )
        self.assertTrue(all(row["hidden_included"] for row in lineage["models"]))
        self.assertTrue(audit["parent_is_frozen_a2_archive"])
        self.assertTrue(audit["primary_anchor_is_parent"])


class ScorecardTests(unittest.TestCase):
    def test_equal_lineage_score_and_paired_uplift(self) -> None:
        panel = panel_records()
        rows = synthetic_rows(panel)
        feedback, private = audit_and_score(
            rows,
            attempt_id="attempt_001",
            candidate_id="candidate",
            parent_id="parent",
            panel_records=panel,
            pool_to_lineage={"p1": "l1", "p2": "l2"},
            expected_tasks=expected_task_map(rows),
            primary_anchor_id="p1",
            secondary_anchor_id="p2",
            integrity_passed=True,
            bootstrap_label="unit-test",
            rounds=200,
        )
        self.assertEqual(feedback["primary_anchor_pure_win_rate"], 1.0)
        self.assertEqual(feedback["secondary_anchor_pure_win_rate"], 0.5)
        self.assertEqual(feedback["lineage_equal_pool_score_rate"], 0.75)
        self.assertEqual(feedback["lineage_equal_pool_score_ci95_low"], 0.75)
        self.assertEqual(feedback["paired_uplift_rate"], 0.5)
        self.assertEqual(feedback["paired_uplift_ci95_low"], 0.5)
        self.assertTrue(feedback["overall_passed"])
        self.assertEqual(private["games_per_direct_anchor"], 200)

    def test_missing_row_is_rejected(self) -> None:
        panel = panel_records()
        rows = synthetic_rows(panel)
        with self.assertRaisesRegex(ValueError, "closure"):
            audit_and_score(
                rows[:-1],
                attempt_id="attempt_001",
                candidate_id="candidate",
                parent_id="parent",
                panel_records=panel,
                pool_to_lineage={"p1": "l1", "p2": "l2"},
                expected_tasks=expected_task_map(rows),
                primary_anchor_id="p1",
                secondary_anchor_id="p2",
                integrity_passed=True,
                bootstrap_label="unit-test",
                rounds=10,
            )

    def test_test_split_is_rejected(self) -> None:
        panel = panel_records()
        panel[0]["split"] = "test"
        with self.assertRaises(PermissionError):
            audit_and_score(
                [],
                attempt_id="attempt_001",
                candidate_id="candidate",
                parent_id="parent",
                panel_records=panel,
                pool_to_lineage={"p1": "l1", "p2": "l2"},
                expected_tasks={},
                primary_anchor_id="p1",
                secondary_anchor_id="p2",
                integrity_passed=True,
                bootstrap_label="unit-test",
                rounds=10,
            )

    def test_public_feedback_rejects_extra_detail(self) -> None:
        panel = panel_records()
        rows = synthetic_rows(panel)
        feedback, _ = audit_and_score(
            rows,
            attempt_id="attempt_001",
            candidate_id="candidate",
            parent_id="parent",
            panel_records=panel,
            pool_to_lineage={"p1": "l1", "p2": "l2"},
            expected_tasks=expected_task_map(rows),
            primary_anchor_id="p1",
            secondary_anchor_id="p2",
            integrity_passed=True,
            bootstrap_label="unit-test",
            rounds=10,
        )
        feedback["loss_reason"] = "forbidden"
        with self.assertRaises(ValueError):
            validate_public_feedback(feedback)

    def test_versions_are_equal_only_inside_their_lineage(self) -> None:
        panel = panel_records()
        rows: list[dict] = []
        index = 0
        scores = {
            ("candidate", "p1a"): 1.0,
            ("candidate", "p1b"): 0.0,
            ("candidate", "p2"): 1.0,
            ("parent", "p1a"): 0.0,
            ("parent", "p1b"): 0.0,
            ("parent", "p2"): 0.0,
        }
        for policy in ("candidate", "parent"):
            for opponent in ("p1a", "p1b", "p2"):
                for source in panel:
                    for seat in (0, 1):
                        index += 1
                        task = {
                            "task_id": f"weighted-{index}",
                            "run_fingerprint": "w" * 64,
                            "pair_id": f"{policy}__vs__{opponent}",
                            "model_a": policy,
                            "model_b": opponent,
                            "model_a_seat": seat,
                            "source": dict(source),
                        }
                        rows.append(game_row(task, scores[(policy, opponent)]))
        feedback, private = audit_and_score(
            rows,
            attempt_id="attempt_001",
            candidate_id="candidate",
            parent_id="parent",
            panel_records=panel,
            pool_to_lineage={"p1a": "l1", "p1b": "l1", "p2": "l2"},
            expected_tasks=expected_task_map(rows),
            primary_anchor_id="p1a",
            secondary_anchor_id="p2",
            integrity_passed=True,
            bootstrap_label="weighted-unit-test",
            rounds=50,
        )
        self.assertEqual(feedback["lineage_equal_pool_score_rate"], 0.75)
        self.assertEqual(feedback["paired_uplift_rate"], 0.75)
        self.assertEqual(private["models_evaluated"], 3)
        self.assertEqual(private["behaviour_lineages_equal_weighted"], 2)

    def test_raw_row_semantic_red_team(self) -> None:
        panel = panel_records()
        original = synthetic_rows(panel)
        expected = expected_task_map(original)
        mutations = (
            ("schema", "wrong", "schema"),
            ("engine", "wrong", "engine"),
            ("run_fingerprint", "wrong", "sealed task field"),
            ("reward_a", 999.0, "reward_a"),
            ("margin_a", 999.0, "margin_a"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                rows = copy.deepcopy(original)
                rows[0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    audit_and_score(
                        rows,
                        attempt_id="attempt_001",
                        candidate_id="candidate",
                        parent_id="parent",
                        panel_records=panel,
                        pool_to_lineage={"p1": "l1", "p2": "l2"},
                        expected_tasks=expected,
                        primary_anchor_id="p1",
                        secondary_anchor_id="p2",
                        integrity_passed=True,
                        bootstrap_label="red-team",
                        rounds=10,
                    )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v15-json-test-") as raw:
            path = Path(raw) / "games.jsonl"
            path.write_text('{"task_id":"a","task_id":"b"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed JSONL"):
                read_jsonl(path)


class SourceAndHiddenStateTests(unittest.TestCase):
    def test_attempt_panels_are_single_use_and_disjoint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="v15-source-test-") as raw:
            state = Path(raw)
            first = reserve_panel("attempt_001", "development", state_root=state)
            repeated = reserve_panel("attempt_001", "development", state_root=state)
            second = reserve_panel("attempt_002", "development", state_root=state)
            self.assertEqual(first, repeated)
            first_seeds = {row["seed"] for row in first["records"]}
            second_seeds = {row["seed"] for row in second["records"]}
            self.assertFalse(first_seeds & second_seeds)
            self.assertEqual(first["test_source_count"], 0)

    def test_hidden_rejects_post_development_mutation_and_second_draw(self) -> None:
        seal = {
            "candidate_serving_sha256": "a" * 64,
            "policy_sha256": "b" * 64,
        }
        closure = {"archive_sha256": "c" * 64, "serving_fingerprint": "d" * 64}
        with tempfile.TemporaryDirectory(prefix="v15-hidden-test-") as raw:
            state = Path(raw)
            _bind_candidate_stage(
                attempt_id="attempt_001",
                stage="development",
                seal=seal,
                candidate_closure=closure,
                state_root=state,
            )
            result = state / "attempts" / "attempt_001" / "development_result.private.json"
            atomic_create_json(result, {"feedback": {"overall_passed": True}})
            changed = {**closure, "archive_sha256": "e" * 64}
            with self.assertRaises(PermissionError):
                _bind_candidate_stage(
                    attempt_id="attempt_001",
                    stage="hidden",
                    seal=seal,
                    candidate_closure=changed,
                    state_root=state,
                )
            _bind_candidate_stage(
                attempt_id="attempt_001",
                stage="hidden",
                seal=seal,
                candidate_closure=closure,
                state_root=state,
            )
            with self.assertRaisesRegex(PermissionError, "already consumed"):
                _bind_candidate_stage(
                    attempt_id="attempt_001",
                    stage="hidden",
                    seal=seal,
                    candidate_closure=closure,
                    state_root=state,
                )
            _bind_candidate_stage(
                attempt_id="attempt_002",
                stage="development",
                seal=seal,
                candidate_closure=closure,
                state_root=state,
            )
            result2 = state / "attempts" / "attempt_002" / "development_result.private.json"
            atomic_create_json(result2, {"feedback": {"overall_passed": True}})
            with self.assertRaisesRegex(PermissionError, "already consumed"):
                _bind_candidate_stage(
                    attempt_id="attempt_002",
                    stage="hidden",
                    seal=seal,
                    candidate_closure=closure,
                    state_root=state,
                )

    def test_non_consuming_dry_run_closure(self) -> None:
        payload = dry_run_payload("attempt_001")
        self.assertFalse(payload["games_started"])
        self.assertFalse(payload["panels_reserved"])
        self.assertEqual(payload["development"]["models"], 7)
        self.assertEqual(payload["hidden"]["models"], 11)
        self.assertEqual(payload["development"]["total_tasks"], 2800)
        self.assertEqual(payload["hidden"]["total_tasks"], 4400)
        self.assertEqual(payload["test_sources_selected"], 0)

    def test_physical_task_builder_matches_dry_run_counts(self) -> None:
        panel = {"records": panel_records()}
        development = build_tasks(
            fingerprint="f" * 64,
            registry_path=Path("/private/registry.json"),
            pool_ids=[f"p{index}" for index in range(1, 8)],
            panel=panel,
        )
        hidden = build_tasks(
            fingerprint="e" * 64,
            registry_path=Path("/private/registry.json"),
            pool_ids=[f"p{index}" for index in range(1, 12)],
            panel=panel,
        )
        self.assertEqual(len(development), 2800)
        self.assertEqual(len(hidden), 4400)
        self.assertEqual(len({row["task_id"] for row in hidden}), 4400)

    def test_resume_rejects_duplicate_physical_row(self) -> None:
        panel = {"records": panel_records()}
        tasks = build_tasks(
            fingerprint="r" * 64,
            registry_path=Path("/private/registry.json"),
            pool_ids=["p1"],
            panel=panel,
        )
        row = game_row(tasks[0], 1.0)
        with tempfile.TemporaryDirectory(prefix="v15-resume-test-") as raw:
            path = Path(raw) / "games.jsonl"
            encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            path.write_text(encoded + "\n" + encoded + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate task id"):
                validate_resume_file(
                    path,
                    expected_tasks=index_expected_tasks(tasks),
                    pool_ids={"p1"},
                    panel_records=panel["records"],
                )


if __name__ == "__main__":
    unittest.main()
