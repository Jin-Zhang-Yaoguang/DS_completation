from __future__ import annotations

import json
import hashlib
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate import (
    SCHEMA as GAME_SCHEMA,
    SeedRecord,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as pairwise
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent as create_registry_agent,
    load_registry,
    registry_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.router import (
    RuleSelector,
    ShadowRouter,
)
from kaggle_Kaggriculture.model.v11_iterative_league.fast_router import FastShadowRouter
from kaggle_Kaggriculture.model.v11_iterative_league.league import (
    AUTHORITATIVE_V10_FINAL14_SHA256,
    _attempt_state,
    _lowest_model,
    _pending_retry_tasks,
    _validate_candidate_parent,
    _validate_candidate_wrapper,
    _validate_formal_fast_evidence,
    add_candidate,
    build_failure_audit,
    build_league_summary,
    initialise_state,
    load_exclusion_metadata,
    load_state,
    model_fingerprint,
    render_round_report,
    round_salt,
    save_state,
    select_round_panel,
)
from kaggle_Kaggriculture.model.v11_iterative_league.materialize_fast_registry import materialize
from kaggle_Kaggriculture.model.v11_iterative_league import admission_verifier
from kaggle_Kaggriculture.model.v11_iterative_league.strategy_optimizer import (
    _write_registry_payload,
)


def _agent_source(path: Path) -> None:
    path.write_text(
        "def agent(obs):\n"
        " return {'farmer':['PASS'],'hands':[],'market':[]}\n",
        encoding="utf-8",
    )


def _formal_row(
    model_a: str,
    model_b: str,
    source: SeedRecord,
    seat: int,
    score_a: float,
    run: str,
) -> dict:
    reward_a = 101.0 if score_a == 1.0 else 99.0 if score_a == 0.0 else 100.0
    reward_b = 100.0
    rewards = [reward_a, reward_b] if seat == 0 else [reward_b, reward_a]
    pair_id = f"{model_a}__vs__{model_b}"
    return {
        "schema": GAME_SCHEMA,
        "engine": "kaggle_environments.make(kaggriculture)",
        "closed_loop": True,
        "trace_agent": False,
        "task_id": pairwise._task_id(run, pair_id, source, seat),
        "run_fingerprint": run,
        "pair_id": pair_id,
        "model_a": model_a,
        "model_b": model_b,
        "model_a_seat": seat,
        "source": asdict(source),
        "seat_models": [model_a, model_b] if seat == 0 else [model_b, model_a],
        "statuses": ["DONE", "DONE"],
        "rewards": rewards,
        "done": True,
        "error": None,
        "reward_a": reward_a,
        "reward_b": reward_b,
        "score_a": score_a,
        "margin_a": reward_a - reward_b,
        "model_meta": {},
        "agent_diagnostics": {},
        "seat_diagnostics": [{}, {}],
    }


class LeagueTest(unittest.TestCase):
    def test_authoritative_v10_final14_runtime_fingerprint_is_frozen(self) -> None:
        final_registry = (
            Path(__file__).resolve().parents[2]
            / "v10_replay_lolo_router"
            / "final_registry.json"
        )
        registry = load_registry(final_registry)
        self.assertEqual(
            registry_fingerprint(registry), AUTHORITATIVE_V10_FINAL14_SHA256
        )

    def test_formal_init_rejects_missing_or_forged_fast_evidence(self) -> None:
        source_path = (
            Path(__file__).resolve().parents[2]
            / "v10_replay_lolo_router"
            / "final_registry.json"
        )
        source = load_registry(source_path)
        with self.assertRaisesRegex(ValueError, "equivalence report path"):
            _validate_formal_fast_evidence({}, source)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            equivalence_report = root / "equivalence.json"
            equivalence_report.write_text("{}\n", encoding="utf-8")
            equivalence = {
                "report": str(equivalence_report.resolve()),
                "report_file_sha256": hashlib.sha256(
                    equivalence_report.read_bytes()
                ).hexdigest(),
            }
            forged_equivalence = {
                **equivalence,
                "report_file_sha256": "0" * 64,
            }
            with self.assertRaisesRegex(ValueError, "equivalence report file/hash"):
                _validate_formal_fast_evidence(
                    {"formal_fast_router_equivalence": forged_equivalence}, source
                )
            with patch(
                "kaggle_Kaggriculture.model.v11_iterative_league.verify_fast_router.validate_formal_report",
                return_value=equivalence,
            ):
                with self.assertRaisesRegex(ValueError, "fresh challenge path"):
                    _validate_formal_fast_evidence(
                        {"formal_fast_router_equivalence": equivalence}, source
                    )
                challenge_report = root / "challenge.json"
                challenge_report.write_text("{}\n", encoding="utf-8")
                forged_challenge = {
                    "report": str(challenge_report.resolve()),
                    "report_file_sha256": "f" * 64,
                }
                with self.assertRaisesRegex(ValueError, "challenge file/hash"):
                    _validate_formal_fast_evidence(
                        {
                            "formal_fast_router_equivalence": equivalence,
                            "formal_fast_router_fresh_challenge": forged_challenge,
                        },
                        source,
                    )

    def test_candidate_wrapper_rejects_malicious_module_and_stale_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent_agent = root / "parent.py"
            _agent_source(parent_agent)
            parent_registry_path = root / "parent_registry.json"
            parent_registry_path.write_text(
                json.dumps(
                    {"models": [{"id": "leader", "kind": "python", "path": "parent.py"}]}
                ),
                encoding="utf-8",
            )
            parent_registry = load_registry(parent_registry_path)
            expected_parent = model_fingerprint(parent_registry, "leader")
            v11 = Path(__file__).resolve().parents[1]
            entry = {
                "id": "candidate",
                "kind": "python",
                "path": str(v11 / "candidate_agent.py"),
                "factory": "create_agent",
                "factory_kwargs": {
                    "parent_registry": str(parent_registry_path),
                    "parent_id": "leader",
                    "mutation_name": "value_slot_priority",
                    "mutation_params": {},
                    "candidate_id": "candidate",
                },
                "code_paths": [
                    str(v11 / "candidate_agent.py"),
                    str(v11 / "mutation_catalog.py"),
                ],
            }
            admitted_path = root / "admitted.json"
            admitted_path.write_text(
                json.dumps(
                    {
                        "models": [
                            {"id": "leader", "kind": "python", "path": "parent.py"},
                            entry,
                        ]
                    }
                ),
                encoding="utf-8",
            )
            admitted = load_registry(admitted_path)
            _validate_candidate_wrapper(
                admitted, entry, "candidate", "leader", expected_parent
            )
            malicious = dict(entry)
            malicious["path"] = str(parent_agent)
            with self.assertRaisesRegex(ValueError, "path/factory"):
                _validate_candidate_wrapper(
                    admitted, malicious, "candidate", "leader", expected_parent
                )
            stale_agent = root / "stale.py"
            stale_agent.write_text(
                "def agent(obs):\n return {'farmer':['NORTH'],'hands':[],'market':[]}\n",
                encoding="utf-8",
            )
            stale_registry = root / "stale_registry.json"
            stale_registry.write_text(
                json.dumps(
                    {"models": [{"id": "leader", "kind": "python", "path": "stale.py"}]}
                ),
                encoding="utf-8",
            )
            stale = json.loads(json.dumps(entry))
            stale["factory_kwargs"]["parent_registry"] = str(stale_registry)
            with self.assertRaisesRegex(ValueError, "stale or substituted"):
                _validate_candidate_wrapper(
                    admitted, stale, "candidate", "leader", expected_parent
                )

    def test_candidate_parent_must_be_active_round_leader(self) -> None:
        state = {"active_models": ["leader", "runner_up"]}
        summary = {
            "standings": [
                {"model_id": "leader", "rank": 1},
                {"model_id": "runner_up", "rank": 2},
            ]
        }
        _validate_candidate_parent("leader", state, summary)
        with self.assertRaisesRegex(ValueError, "round leader"):
            _validate_candidate_parent("runner_up", state, summary)
        with self.assertRaisesRegex(ValueError, "not active"):
            _validate_candidate_parent("retired", state, summary)

    def test_candidate_registry_preserves_seals_across_two_generations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent = root / "agent.py"
            _agent_source(agent)
            immutable = {
                "sealed_before_test": True,
                "test_used_for_fit": False,
                "pre_selection_test_access": False,
                "source_manifest_seal": {"file_sha256": "1" * 64, "records": 2090},
                "router_fit_source_exclusions": {
                    "file_sha256": "2" * 64,
                    "records_sha256": "3" * 64,
                    "records": 200,
                },
                "formal_fast_router_equivalence": {
                    "all_equivalent": True,
                    "report_file_sha256": "4" * 64,
                },
                "test_protocol": {"expected_games": 18200},
            }
            source = root / "source.json"
            source.write_text(
                json.dumps(
                    {
                        **immutable,
                        "schema": "kaggriculture-v11-fast-router-registry-1",
                        "models": [{"id": "a", "kind": "python", "path": "agent.py"}],
                    }
                ),
                encoding="utf-8",
            )
            first = root / "one" / "registry.json"
            first.parent.mkdir()
            first_entry = {"id": "c1", "kind": "python", "path": "../agent.py"}
            first.write_text(
                json.dumps(_write_registry_payload(source, first, first_entry)),
                encoding="utf-8",
            )
            second = root / "two" / "registry.json"
            second.parent.mkdir()
            second_entry = {"id": "c2", "kind": "python", "path": "../agent.py"}
            second.write_text(
                json.dumps(_write_registry_payload(first, second, second_entry)),
                encoding="utf-8",
            )
            for path in (first, second):
                payload = json.loads(path.read_text(encoding="utf-8"))
                for key, value in immutable.items():
                    self.assertEqual(payload[key], value)
            self.assertEqual(
                [item["id"] for item in json.loads(second.read_text())["models"]],
                ["a", "c1", "c2"],
            )

    def test_retry_budget_is_cumulative_across_resume(self) -> None:
        source = SeedRecord("2026-08-18", 1, "e1", "train")
        pair_id = "a__vs__b"
        task = {
            "task_id": pairwise._task_id("retry-run", pair_id, source, 0),
            "run_fingerprint": "retry-run",
            "pair_id": pair_id,
            "model_a": "a",
            "model_b": "b",
            "model_a_seat": 0,
            "source": asdict(source),
        }
        failure = {
            **task,
            "schema": GAME_SCHEMA,
            "done": False,
            "error": "Timeout",
            "statuses": [],
            "score_a": None,
        }
        successes, counts, _ = _attempt_state(
            [failure, failure], [task], ["a", "b"], [source], "retry-run"
        )
        self.assertEqual(counts[task["task_id"]], 2)
        self.assertEqual(len(_pending_retry_tasks([task], successes, counts)), 1)
        # A later process resume observes the third JSONL row and cannot gain a
        # fresh three-attempt allowance.
        successes, counts, _ = _attempt_state(
            [failure, failure, failure], [task], ["a", "b"], [source], "retry-run"
        )
        self.assertEqual(counts[task["task_id"]], 3)
        self.assertEqual(_pending_retry_tasks([task], successes, counts), [])
        with self.assertRaisesRegex(ValueError, "exceeds the cumulative"):
            _attempt_state(
                [failure] * 4, [task], ["a", "b"], [source], "retry-run"
            )
        late_success = _formal_row("a", "b", source, 0, 1.0, "retry-run")
        with self.assertRaisesRegex(ValueError, "exceeds the cumulative"):
            _attempt_state(
                [failure] * 4 + [late_success],
                [task],
                ["a", "b"],
                [source],
                "retry-run",
            )

    def test_independent_admission_rejects_a_renamed_action_clone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent = root / "agent.py"
            _agent_source(agent)
            registry = root / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "models": [
                            {"id": "parent", "kind": "python", "path": "agent.py"},
                            {"id": "clone", "kind": "python", "path": "agent.py"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            sources = [
                {
                    "date": f"2026-08-{18 + index % 3:02d}",
                    "episode_id": str(index + 1),
                    "seed": index + 1,
                    "split": "train",
                }
                for index in range(6)
            ]
            trajectory = {
                "statuses": ["DONE", "DONE"],
                "steps": 720,
                "actions": [{"farmer": ["PASS"], "hands": [], "market": []}] * 719,
                "stderr": "",
            }
            with patch.object(
                admission_verifier, "_trajectory", return_value=trajectory
            ):
                report = admission_verifier.verify_candidate(
                    registry, "clone", "parent", sources, workers=1
                )
            self.assertFalse(report["passed"])
            self.assertFalse(report["real_action_difference"])
            self.assertEqual(report["changed_games"], 0)

    def test_router_fit_metadata_is_excluded_without_reading_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clean = root / "clean.json"
            clean.write_text(
                json.dumps(
                    {
                        "schema": "kaggriculture-v11-router-fit-exclusion-1",
                        "records": [
                            {"date": "2026-08-18", "seed": 11, "episode_id": "e11", "split": "train"},
                            {"date": "2026-08-19", "seed": 12, "episode_id": "e12", "split": "validation"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rows = load_exclusion_metadata(clean)
            self.assertEqual({row["seed"] for row in rows}, {11, 12})
            contaminated = root / "contaminated.json"
            contaminated.write_text(
                json.dumps(
                    {
                        "records": [
                            {"date": "2026-08-18", "seed": 11, "split": "train", "candidate_score": 1.0}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "forbidden outcome field"):
                load_exclusion_metadata(contaminated)

    def test_round_panel_is_unique_balanced_auditable_and_round_specific(self) -> None:
        records = []
        for date_index, date in enumerate(("2026-08-18", "2026-08-19", "2026-08-20")):
            for offset in range(120):
                split = "train" if offset % 2 else "validation"
                seed = date_index * 10_000 + offset
                records.append(SeedRecord(date, seed, f"e-{seed}", split))
            records.append(SeedRecord(date, 999_999, f"test-{date}", "test"))
        state = {"root_seed": 7, "manifest_sha256": "a" * 64}
        salt1, _ = round_salt(state, 1)
        salt2, _ = round_salt(state, 2)
        first = select_round_panel(records, 100, 1, salt1)
        repeated = select_round_panel(records, 100, 1, salt1)
        second = select_round_panel(
            records, 100, 2, salt2, exclude_seeds={item.seed for item in first}
        )
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, second)
        self.assertFalse({item.seed for item in first} & {item.seed for item in second})
        self.assertEqual(len({item.seed for item in first}), 100)
        self.assertNotIn("test", {item.split for item in first})
        counts = {date: sum(row.date == date for row in first) for date in {row.date for row in first}}
        self.assertEqual(sorted(counts.values()), [33, 33, 34])
        self.assertEqual(counts["2026-08-18"], 34)

    def test_first_cycle_is_no_replacement_then_second_cycle_may_reuse(self) -> None:
        dates = ("2026-08-18", "2026-08-19", "2026-08-20")
        date_sizes = (627, 627, 626)
        records = [
            SeedRecord(date, date_index * 10_000 + offset, f"e-{date_index}-{offset}", "train")
            for date_index, date in enumerate(dates)
            for offset in range(date_sizes[date_index])
        ]
        exclusions = {
            item.seed
            for date_index, quota in enumerate((67, 67, 66))
            for item in records
            if item.date == dates[date_index] and item.seed % 10_000 < quota
        }
        self.assertEqual(len(exclusions), 200)
        cycle_used = set()
        panel_hashes = set()
        usage = {}
        last_design_seeds = set()
        for cycle_round in range(1, 17):
            salt = hashlib.sha256(f"cycle-one-{cycle_round}".encode()).hexdigest()
            panel = select_round_panel(
                records,
                100,
                cycle_round,
                salt,
                exclude_seeds=exclusions | cycle_used,
            )
            seeds = {item.seed for item in panel}
            self.assertFalse(seeds & exclusions)
            self.assertFalse(seeds & cycle_used)
            cycle_used.update(seeds)
            for seed in seeds:
                usage[seed] = usage.get(seed, 0) + 1
            panel_hashes.add(tuple(sorted(seeds)))
            last_design_seeds = seeds
        self.assertEqual(len(cycle_used), 1600)
        second_cycle = select_round_panel(
            records,
            100,
            1,
            hashlib.sha256(b"cycle-two-1").hexdigest(),
            exclude_seeds=exclusions | last_design_seeds,
            usage_counts=usage,
        )
        second_seeds = {item.seed for item in second_cycle}
        self.assertFalse(second_seeds & last_design_seeds)
        # The 80 never-used seeds are exhausted before any once-used source is
        # eligible; the previous cycle's last panel can be separately excluded
        # by run_round when a pending candidate is activated.
        self.assertEqual(len(second_seeds - cycle_used), 80)
        self.assertEqual(len(second_seeds & cycle_used), 20)
        self.assertNotIn(tuple(sorted(second_seeds)), panel_hashes)
        for seed in second_seeds:
            usage[seed] = usage.get(seed, 0) + 1
        self.assertLessEqual(max(usage.values()) - min(usage.values()), 1)

    def test_summary_scores_wdl_matrix_and_markdown(self) -> None:
        models = ["a", "b", "c"]
        run = "run-1"
        rows = []
        task_ids = set()
        outcomes = {
            ("a", "b"): [1.0] * 120 + [0.5] * 20 + [0.0] * 60,
            ("a", "c"): [1.0] * 100 + [0.0] * 100,
            ("b", "c"): [1.0] * 80 + [0.5] * 40 + [0.0] * 80,
        }
        counter = 0
        panel = [SeedRecord("2026-08-18", index, str(index), "train") for index in range(100)]
        for (a, b), scores in outcomes.items():
            for pair_game_index, score in enumerate(scores):
                counter += 1
                source = panel[pair_game_index // 2]
                row = _formal_row(
                    a, b, source, pair_game_index % 2, score, run
                )
                task_id = row["task_id"]
                task_ids.add(task_id)
                rows.append(row)
        summary = build_league_summary(rows, models, task_ids, run, 1, panel)
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["valid_games"], 600)
        self.assertEqual(summary["matrix"]["a"]["b"]["wins"], 120)
        self.assertEqual(summary["matrix"]["b"]["a"]["losses"], 120)
        self.assertEqual(summary["matrix"]["a"]["b"]["points"], 130.0)
        by_model = {row["model_id"]: row for row in summary["standings"]}
        self.assertEqual(by_model["a"]["points"], 230.0)
        self.assertEqual(by_model["b"]["points"], 170.0)
        self.assertEqual(by_model["c"]["points"], 200.0)
        self.assertEqual(summary["standings"][0]["model_id"], "a")
        report = render_round_report(summary)
        self.assertTrue(report.startswith("# 第 1 轮迭代\n"))
        self.assertIn("## 3×3 对战矩阵", report)
        self.assertIn("120-20-60 / 130.0", report)

        identical_retry = dict(rows[0])
        repeated = build_league_summary(
            [*rows, identical_retry], models, task_ids, run, 1, panel
        )
        self.assertTrue(repeated["complete"])
        self.assertEqual(
            repeated["retry_audit"]["identical_success_duplicates"], 1
        )

        wrong_panel_rows = [dict(item) for item in rows]
        wrong_panel_rows[0] = dict(wrong_panel_rows[0])
        wrong_panel_rows[0]["source"] = dict(wrong_panel_rows[2]["source"])
        with self.assertRaisesRegex(ValueError, "task_id does not match"):
            build_league_summary(
                wrong_panel_rows, models, task_ids, run, 1, panel
            )

    def test_conflicting_success_duplicate_is_rejected(self) -> None:
        panel = [SeedRecord("2026-08-18", index, str(index), "train") for index in range(100)]
        rows = []
        task_ids = set()
        for seat_index in range(200):
            row = _formal_row(
                "a",
                "b",
                panel[seat_index // 2],
                seat_index % 2,
                1.0,
                "run",
            )
            task_id = row["task_id"]
            task_ids.add(task_id)
            rows.append(row)
        conflict = dict(rows[0])
        conflict["score_a"] = 0.0
        conflict["margin_a"] = -1.0
        conflict["reward_a"] = 99.0
        conflict["rewards"] = [99.0, 100.0]
        with self.assertRaisesRegex(ValueError, "conflicting successful results"):
            build_league_summary(
                [*rows, conflict], ["a", "b"], task_ids, "run", 1, panel
            )

    def test_malicious_score_status_task_and_seat_rows_are_rejected(self) -> None:
        panel = [SeedRecord("2026-08-18", index, str(index), "train") for index in range(100)]
        base = _formal_row("a", "b", panel[0], 0, 1.0, "strict-run")
        mutations = []
        score_two = dict(base)
        score_two["score_a"] = 2.0
        mutations.append(score_two)
        non_finite = dict(base)
        non_finite["margin_a"] = float("nan")
        mutations.append(non_finite)
        bad_status = dict(base)
        bad_status["statuses"] = ["DONE", "ERROR"]
        mutations.append(bad_status)
        bad_task = dict(base)
        bad_task["task_id"] = "forged-task"
        mutations.append(bad_task)
        bad_seat_models = dict(base)
        bad_seat_models["seat_models"] = ["b", "a"]
        mutations.append(bad_seat_models)
        wrong_schema = dict(base)
        wrong_schema["schema"] = "legacy-trace-agent"
        mutations.append(wrong_schema)
        not_closed_loop = dict(base)
        not_closed_loop["closed_loop"] = False
        mutations.append(not_closed_loop)
        trace_agent = dict(base)
        trace_agent["trace_agent"] = True
        mutations.append(trace_agent)
        wrong_engine = dict(base)
        wrong_engine["engine"] = "replay-player"
        mutations.append(wrong_engine)
        for row in mutations:
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    build_league_summary(
                        [row],
                        ["a", "b"],
                        {str(row["task_id"])},
                        "strict-run",
                        1,
                        panel,
                    )

    def test_candidate_wrapped_router_diagnostics_are_recursively_gated(self) -> None:
        panel = [SeedRecord("2026-08-18", index, str(index), "train") for index in range(100)]
        row = _formal_row("candidate", "b", panel[0], 0, 1.0, "router-run")
        experts = ["e1", "e2", "e3", "e4"]
        ancestry = {
            "candidate": {
                "router_model_id": "rule_router",
                "experts": experts,
                "fast_shadow_required": True,
            },
            "b": None,
        }
        router = {
            "kind": "shadow_full_expert_router",
            "fast_shadow": True,
            "prefix_complete": True,
            "prefix_match": {item: True for item in experts},
            "prefix_errors": {item: [] for item in experts},
            "prefix_first_mismatch": {item: None for item in experts},
            "runtime_errors": [],
            "selected_fallbacks": 0,
            "selected": "e1",
            "selection_eligible": list(experts),
            "selection_reason": "rule",
        }
        row["seat_diagnostics"][0] = {
            "underlying": {
                "kind": "v11_complete_parent_market_residual",
                "parent_diagnostics": {"router": router},
            }
        }
        # A valid nested Router is accepted (the round remains incomplete only
        # because this fixture intentionally contains one of 200 tasks).
        summary = build_league_summary(
            [row],
            ["candidate", "b"],
            {row["task_id"]},
            "router-run",
            1,
            panel,
            ancestry,
        )
        self.assertFalse(summary["complete"])
        broken = json.loads(json.dumps(row))
        broken["seat_diagnostics"][0]["underlying"]["parent_diagnostics"]["router"][
            "runtime_errors"
        ] = ["boom"]
        with self.assertRaisesRegex(ValueError, "runtime failure"):
            build_league_summary(
                [broken],
                ["candidate", "b"],
                {row["task_id"]},
                "router-run",
                1,
                panel,
                ancestry,
            )
        missing = json.loads(json.dumps(row))
        missing["seat_diagnostics"][0] = {
            "underlying": {
                "kind": "v11_complete_parent_market_residual",
                "parent_diagnostics": {},
            }
        }
        with self.assertRaisesRegex(ValueError, "exactly one Router diagnostic"):
            build_league_summary(
                [missing],
                ["candidate", "b"],
                {row["task_id"]},
                "router-run",
                1,
                panel,
                ancestry,
            )
        ineligible = json.loads(json.dumps(row))
        ineligible_router = ineligible["seat_diagnostics"][0]["underlying"][
            "parent_diagnostics"
        ]["router"]
        ineligible_router["selection_eligible"] = ["e2"]
        with self.assertRaisesRegex(ValueError, "do not cover its four experts"):
            build_league_summary(
                [ineligible],
                ["candidate", "b"],
                {row["task_id"]},
                "router-run",
                1,
                panel,
                ancestry,
            )

    def test_complete_round_rejects_a_foreign_resume_row(self) -> None:
        panel = [
            SeedRecord("2026-08-18", index, str(index), "train")
            for index in range(100)
        ]
        rows = [
            _formal_row("a", "b", source, seat, 1.0, "round-run")
            for source in panel
            for seat in (0, 1)
        ]
        expected = {str(row["task_id"]) for row in rows}
        foreign = dict(rows[0])
        foreign["run_fingerprint"] = "foreign-run"
        foreign["task_id"] = "foreign-task"
        rows.append(foreign)
        with self.assertRaisesRegex(ValueError, "foreign task/run"):
            build_league_summary(
                rows,
                ["a", "b"],
                expected,
                "round-run",
                1,
                panel,
            )

    def test_worst_opponent_score_rate_is_a_registered_tie_break(self) -> None:
        models = ["a", "b", "c", "d"]
        rates = {
            ("a", "b"): 0.5,
            ("a", "c"): 0.8,
            ("a", "d"): 0.4,
            ("b", "c"): 0.6,
            ("b", "d"): 0.6,
            ("c", "d"): 0.5,
        }
        rows, task_ids = [], set()
        counter = 0
        panel = [SeedRecord("2026-08-18", index, str(index), "train") for index in range(100)]
        for (left, right), rate in rates.items():
            left_wins = int(rate * 200)
            scores = [1.0] * left_wins + [0.0] * (200 - left_wins)
            for pair_index, score in enumerate(scores):
                counter += 1
                row = _formal_row(
                    left,
                    right,
                    panel[pair_index // 2],
                    pair_index % 2,
                    score,
                    "tie-run",
                )
                task_id = row["task_id"]
                task_ids.add(task_id)
                rows.append(row)
        summary = build_league_summary(
            rows, models, task_ids, "tie-run", 1, panel
        )
        by_model = {row["model_id"]: row for row in summary["standings"]}
        self.assertEqual(by_model["a"]["points"], by_model["b"]["points"])
        self.assertEqual(
            by_model["a"]["head_to_head_points"],
            by_model["b"]["head_to_head_points"],
        )
        self.assertEqual(by_model["a"]["mean_margin"], by_model["b"]["mean_margin"])
        self.assertLess(
            by_model["a"]["worst_opponent_score_rate"],
            by_model["b"]["worst_opponent_score_rate"],
        )
        self.assertLess(by_model["b"]["rank"], by_model["a"]["rank"])

    def test_failure_audit_never_turns_technical_failure_into_loss(self) -> None:
        tasks = [
            {
                "task_id": "ok",
                "pair_id": "a__vs__b",
                "model_a": "a",
                "model_b": "b",
                "model_a_seat": 0,
                "source": {"date": "2026-08-18", "episode_id": "1", "seed": 1},
            },
            {
                "task_id": "bad",
                "pair_id": "a__vs__b",
                "model_a": "a",
                "model_b": "b",
                "model_a_seat": 1,
                "source": {"date": "2026-08-18", "episode_id": "1", "seed": 1},
            },
        ]
        rows = [
            {"task_id": "ok", "run_fingerprint": "r", "done": True, "error": None},
            {"task_id": "bad", "run_fingerprint": "r", "done": False, "error": "boom-1", "statuses": []},
            {"task_id": "bad", "run_fingerprint": "r", "done": False, "error": "boom-2", "statuses": []},
        ]
        audit = build_failure_audit(rows, tasks, "r", attempts=3)
        self.assertEqual(audit["unresolved_tasks"], 1)
        self.assertEqual(audit["unresolved"][0]["last_error"], "boom-2")
        self.assertEqual(audit["policy"], "hard_fail_no_imputation_no_loss_assignment")

    def test_candidate_is_pending_and_does_not_reuse_design_round_for_elimination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent = root / "agent.py"
            _agent_source(agent)
            manifest = root / "manifest.jsonl"
            manifest.write_text('{"date":"2026-08-18","seed":1,"split":"train"}\n', encoding="utf-8")
            registry1 = root / "registry1.json"
            specs = [
                {"id": item, "kind": "python", "path": "agent.py"}
                for item in ("a", "b")
            ]
            registry1.write_text(json.dumps({"models": specs}), encoding="utf-8")
            state_path = root / "pool_state.json"
            initialise_state(
                registry1,
                manifest,
                state_path,
                ["a", "b"],
                pool_cap=2,
                require_initial_14=False,
            )
            summary = {
                "complete": True,
                "round": 1,
                "model_ids": ["a", "b"],
                "standings": [
                    {"model_id": "a", "rank": 1, "points": 120.0, "wins": 120, "draws": 0, "losses": 80, "games": 200, "mean_margin": 1.0, "worst_opponent_score_rate": 0.6, "error_count": 0, "head_to_head_points": 120.0},
                    {"model_id": "b", "rank": 2, "points": 80.0, "wins": 80, "draws": 0, "losses": 120, "games": 200, "mean_margin": -1.0, "worst_opponent_score_rate": 0.4, "error_count": 0, "head_to_head_points": 80.0},
                ],
                "matrix": {
                    "a": {"a": None, "b": {"wins": 120, "draws": 0, "losses": 80, "points": 120.0, "games": 200}},
                    "b": {"a": {"wins": 80, "draws": 0, "losses": 120, "points": 80.0, "games": 200}, "b": None},
                },
                "model_count": 2,
                "expected_pairs": 1,
                "scheduled_games": 200,
                "valid_games": 200,
                "panel": {"date_counts": {}, "count": 100},
                "tie_break": [],
            }
            summary_path = root / "league_summary.json"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            report_path = root / "report.md"
            report_path.write_text("# old\n", encoding="utf-8")
            state = load_state(state_path)
            state["status"] = "awaiting_candidate"
            state["candidate_required"] = True
            state["next_round"] = 2
            state["history"] = [
                {
                    "round": 1,
                    "directory": str(root),
                    "panel_sha256": "design-panel",
                    "league_summary": str(summary_path),
                    "report": str(report_path),
                    "activated_model": None,
                    "eliminated_model": None,
                }
            ]
            save_state(state_path, state)

            next_dir = root / "next"
            next_dir.mkdir()
            registry2 = next_dir / "registry2.json"
            v11 = Path(__file__).resolve().parents[1]
            candidate_spec = {
                "id": "c",
                "kind": "python",
                "path": str(v11 / "candidate_agent.py"),
                "factory": "create_agent",
                "factory_kwargs": {
                    "parent_registry": str(registry1),
                    "parent_id": "a",
                    "mutation_name": "value_slot_priority",
                    "mutation_params": {"min_sell_orders": 2},
                    "candidate_id": "c",
                },
                "code_paths": [
                    str(v11 / "candidate_agent.py"),
                    str(v11 / "mutation_catalog.py"),
                ],
                "family": "a+value_slot_priority",
                "lineage": ["a", "c"],
                "parent_models": ["a"],
                "mutation": "value_slot_priority",
                "change_scope": "test",
                "tags": ["pending"],
                "source_round": 1,
                "first_evaluation_round": 2,
            }
            rebased_specs = [
                {"id": item, "kind": "python", "path": "../agent.py"}
                for item in ("a", "b")
            ]
            registry2.write_text(
                json.dumps({"models": [*rebased_specs, candidate_spec]}), encoding="utf-8"
            )
            self.assertEqual(
                model_fingerprint(load_registry(registry1), "a"),
                model_fingerprint(load_registry(registry2), "a"),
            )
            admitted_registry = load_registry(registry2)
            sources = [
                {
                    "date": f"2026-08-{18 + index % 3:02d}",
                    "episode_id": str(100 + index),
                    "seed": 100 + index,
                    "split": "train" if index % 2 else "validation",
                }
                for index in range(6)
            ]
            formal_panel_sources = [
                {**item, "source_path": f"daily/{item['episode_id']}.json", "lineage_fold": "f0"}
                for item in sources
            ]
            panel_records_sha = hashlib.sha256(
                json.dumps(
                    formal_panel_sources,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            (root / "panel.json").write_text(
                json.dumps(
                    {"records": formal_panel_sources, "records_sha256": panel_records_sha}
                ),
                encoding="utf-8",
            )
            state = load_state(state_path)
            state["history"][0]["panel_sha256"] = panel_records_sha
            save_state(state_path, state)
            source_sha = hashlib.sha256(
                json.dumps(
                    sources,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            smoke = {
                "schema": "kaggriculture-v11-candidate-admission-smoke-1",
                "candidate_id": "c",
                "parent_id": "a",
                "mutation_name": "value_slot_priority",
                "mutation_params": {"min_sell_orders": 2},
                "development_sources": sources,
                "development_sources_sha256": source_sha,
                "done": True,
                "statuses": ["DONE", "DONE"],
                "steps": 720,
                "source_round": 1,
                "first_evaluation_round": 2,
                "passed": True,
                "functionality_only": True,
                "performance_evidence": False,
                "source_panel_reused_only_for_smoke": True,
                "seeds": 6,
                "candidate_games": 12,
                "parent_control_games": 12,
                "all_done": True,
                "all_720_steps": True,
                "zero_stderr": True,
                "real_action_difference": True,
                "changed_games": 12,
                "action_difference_steps": 12,
                "admitted_registry": str(registry2.resolve()),
                "admitted_registry_file_sha256": hashlib.sha256(registry2.read_bytes()).hexdigest(),
                "admitted_registry_and_code_sha256": registry_fingerprint(admitted_registry),
                "candidate_serving_sha256": model_fingerprint(admitted_registry, "c"),
                "parent_serving_sha256": model_fingerprint(admitted_registry, "a"),
            }
            smoke_path = root / "candidate_smoke.json"
            smoke_path.write_text(json.dumps(smoke), encoding="utf-8")
            proposal = {
                "model_id": "c",
                "source_round": 1,
                "first_evaluation_round": 2,
                "same_panel_performance_claim": False,
                "registry_entry": candidate_spec,
                "parent_models": ["a"],
                "hypothesis": "test",
                "change_scope": "test",
                "code_paths": candidate_spec["code_paths"],
                "mutation": {
                    "name": "value_slot_priority",
                    "params": {"min_sell_orders": 2},
                },
                "smoke_evidence": {
                    **smoke,
                    "path": str(smoke_path),
                    "sha256": hashlib.sha256(smoke_path.read_bytes()).hexdigest(),
                },
                "registry_path": str(registry2),
            }
            proposal_path = root / "proposal.json"
            proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
            independent = {
                "passed": True,
                "candidate_games": 12,
                "parent_control_games": 12,
                "all_done": True,
                "all_720_steps": True,
                "zero_stderr": True,
                "changed_games": 12,
                "changed_steps": 12,
            }
            with patch(
                "kaggle_Kaggriculture.model.v11_iterative_league.admission_verifier.verify_candidate",
                return_value=independent,
            ):
                admitted = add_candidate(state_path, proposal_path)
            self.assertEqual(admitted["active_models"], ["a", "b"])
            self.assertEqual(admitted["pending_candidate"]["model_id"], "c")
            self.assertEqual(admitted["retired_models"], [])
            self.assertFalse(admitted["candidate_required"])
            self.assertEqual(_lowest_model(summary, {"a", "b"}), "b")


class _CountingExpert:
    def __init__(self, name: str):
        self.name = name
        self.calls = []

    def __call__(self, obs, configuration=None):
        step = int(obs["step"])
        self.calls.append(step)
        direction = "NORTH" if self.name == "a" else "SOUTH"
        if step < 3:
            direction = "PASS"
        return {"farmer": [direction], "hands": [], "market": []}


def _obs(step: int):
    farm = {"money": 1000, "hands": [], "tiles": [], "unlocked_quadrants": []}
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, dict(farm)],
        "market": {"prices": {}, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


class FastRouterTest(unittest.TestCase):
    def test_fast_router_matches_actions_and_stops_unselected_after_boundary(self) -> None:
        specs = {"a": {"tags": []}, "b": {"tags": []}}
        router_spec = {"rule": {"default_priority": ["b", "a"]}}
        original_experts = {"a": _CountingExpert("a"), "b": _CountingExpert("b")}
        fast_experts = {"a": _CountingExpert("a"), "b": _CountingExpert("b")}
        original = ShadowRouter(
            "original",
            original_experts,
            specs,
            "a",
            RuleSelector(router_spec, specs, "a"),
            3,
        )
        fast = FastShadowRouter(
            "fast",
            fast_experts,
            specs,
            "a",
            RuleSelector(router_spec, specs, "a"),
            3,
        )
        original_actions, fast_actions = [], []
        for step in range(9):
            original_actions.append(original(_obs(step)))
            fast_actions.append(fast(_obs(step)))
        self.assertEqual(original_actions, fast_actions)
        self.assertEqual(original.diagnostics()["selected"], fast.diagnostics()["selected"])
        self.assertEqual(original_experts["a"].calls, list(range(9)))
        self.assertEqual(fast_experts["a"].calls, [0, 1, 2, 3])
        self.assertEqual(fast_experts["b"].calls, list(range(9)))
        self.assertEqual(fast.diagnostics()["runtime_errors"], [])

    def test_materialized_router_proxy_is_loadable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent = root / "agent.py"
            _agent_source(agent)
            source = root / "source.json"
            source.write_text(
                json.dumps(
                    {
                        "models": [
                            {"id": "a", "kind": "python", "path": "agent.py"},
                            {"id": "b", "kind": "python", "path": "agent.py"},
                            {
                                "id": "r",
                                "kind": "router",
                                "router_kind": "rule",
                                "experts": ["a", "b"],
                                "anchor": "a",
                                "switch_step": 1,
                                "rule": {"default_priority": ["b", "a"]},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            output = root / "fast.json"
            payload = materialize(source, output)
            self.assertEqual(payload["converted_routers"], ["r"])
            registry = load_registry(output)
            self.assertTrue(registry.require("r")["fast_shadow"])
            router = create_registry_agent(registry, "r")
            router(_obs(0))
            router(_obs(1))
            router(_obs(2))
            diagnostics = router.diagnostics()
            # AgentHandle nests the underlying FastShadow diagnostics.
            self.assertTrue(diagnostics["fast_shadow"])
            self.assertEqual(diagnostics["selected"], "b")


if __name__ == "__main__":
    unittest.main()
