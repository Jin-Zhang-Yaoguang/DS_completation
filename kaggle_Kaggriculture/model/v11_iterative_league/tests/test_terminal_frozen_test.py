from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as pairwise
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    Registry,
    load_registry,
    registry_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate import (
    load_sealed_test_panel,
    validate_terminal_test_registry,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.report_frozen_test import (
    _validate_complete_matrix,
)
from kaggle_Kaggriculture.model.v11_iterative_league.report_frozen_league_test import (
    EXPECTED_GAMES,
    _validate_game_semantics,
    _standings,
    _terminal_state_gate,
    build_report,
)
from kaggle_Kaggriculture.model.v11_iterative_league import (
    report_frozen_league_test as terminal_report,
)
from kaggle_Kaggriculture.model.v11_iterative_league.league import (
    STATE_SCHEMA,
    model_fingerprints,
    save_state,
)


ROOT = Path(__file__).resolve().parents[2]
V10 = ROOT / "v10_replay_lolo_router"
BASELINES = {"baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _models() -> list[str]:
    return [f"candidate_{index:02d}" for index in range(16)]


def _terminal_state(models: list[str]) -> dict:
    return {
        "status": "goal_achieved",
        "active_models": models,
        "candidate_required": False,
        "pending_candidate": None,
        "state_sha256": "a" * 64,
        "goal": {
            "required_pool_size": 16,
            "required_absent_models": sorted(BASELINES),
            "achieved": True,
            "achieved_after_round": 23,
        },
    }


def _terminal_seal(models: list[str]) -> dict:
    return {
        "file_sha256": "b" * 64,
        "state_sha256": "a" * 64,
        "active_models": models,
        "achieved_after_round": 23,
    }


def _matrix_rows(models: list[str]) -> list[dict]:
    rows = []
    for left_index, left in enumerate(models):
        for right in models[left_index + 1 :]:
            for seed in range(100):
                for seat in (0, 1):
                    score = float((seed + seat) % 2)
                    rows.append(
                        {
                            "pair_id": f"{left}__vs__{right}",
                            "model_a": left,
                            "model_b": right,
                            "model_a_seat": seat,
                            "source": {
                                "date": "2026-08-18",
                                "episode_id": f"episode-{seed}",
                                "seed": seed,
                            },
                            "done": True,
                            "error": None,
                            "score_a": score,
                            "margin_a": 1.0 if score else -1.0,
                        }
                    )
    return rows


class TerminalFrozenTest(unittest.TestCase):
    @staticmethod
    def _semantic_row() -> tuple[dict, dict]:
        source = {
            "date": "2026-08-18",
            "seed": 7,
            "episode_id": "episode-7",
            "split": "test",
            "source_path": "",
            "lineage_fold": "",
        }
        task = {
            "task_id": "task-7",
            "pair_id": "a__vs__b",
            "model_a": "a",
            "model_b": "b",
            "model_a_seat": 1,
            "source": source,
        }
        row = {
            **task,
            "engine": "kaggle_environments.make(kaggriculture)",
            "closed_loop": True,
            "trace_agent": False,
            "seat_models": ["b", "a"],
            "statuses": ["DONE", "DONE"],
            "rewards": [10.0, 20.0],
            "done": True,
            "reward_a": 20.0,
            "reward_b": 10.0,
            "margin_a": 10.0,
            "score_a": 1.0,
            "seat_diagnostics": [{}, {}],
            "error": None,
        }
        return row, task

    def test_row_semantics_recompute_score_reward_source_and_seat(self) -> None:
        row, task = self._semantic_row()
        registry = Registry(
            path=V10 / "synthetic.json",
            models={"a": {"id": "a"}, "b": {"id": "b"}},
            raw={"models": []},
        )
        report = _validate_game_semantics([row], [task], registry)
        self.assertTrue(report["reward_score_semantics_recomputed"])
        bad = deepcopy(row)
        bad["score_a"] = 2.0
        with self.assertRaisesRegex(ValueError, "reward/margin/score"):
            _validate_game_semantics([bad], [task], registry)
        bad = deepcopy(row)
        bad["seat_models"] = ["a", "b"]
        with self.assertRaisesRegex(ValueError, "seat_models"):
            _validate_game_semantics([bad], [task], registry)

    def test_fast_router_runtime_error_is_a_hard_failure(self) -> None:
        row, task = self._semantic_row()
        row["model_a"] = task["model_a"] = "router"
        row["pair_id"] = task["pair_id"] = "router__vs__b"
        row["seat_models"] = ["b", "router"]
        row["seat_diagnostics"][1] = {
            "router": {
                "kind": "shadow_full_expert_router",
                "fast_shadow": True,
                "prefix_complete": True,
                "prefix_match": {"e1": True, "e2": True},
                "prefix_errors": {"e1": [], "e2": []},
                "prefix_first_mismatch": {"e1": None, "e2": None},
                "selected": "e1",
                "selection_eligible": ["e1", "e2"],
                "selected_fallbacks": 0,
                "runtime_errors": ["boom"],
            }
        }
        registry = Registry(
            path=V10 / "synthetic.json",
            models={
                "router": {
                    "id": "router",
                    "kind": "python",
                    "fast_shadow": True,
                    "factory_kwargs": {
                        "router_spec": {"experts": ["e1", "e2"]}
                    },
                },
                "b": {"id": "b"},
            },
            raw={"models": []},
        )
        with self.assertRaisesRegex(ValueError, "runtime"):
            _validate_game_semantics([row], [task], registry)

    def test_complete_24000_rows_reject_eligible_outside_sealed_experts(self) -> None:
        models = _models()
        router_id = models[0]
        experts = ["expert_a", "expert_b", "expert_c", "expert_d"]
        registry = Registry(
            path=V10 / "synthetic-terminal-evil-eligible.json",
            models={
                model_id: (
                    {
                        "id": model_id,
                        "kind": "router",
                        "experts": experts,
                    }
                    if model_id == router_id
                    else {"id": model_id, "kind": "python"}
                )
                for model_id in models
            },
            raw={"models": []},
        )
        panel = [
            pairwise.SeedRecord(
                date=(
                    "2026-08-18"
                    if index < 34
                    else "2026-08-19"
                    if index < 67
                    else "2026-08-20"
                ),
                seed=20_000 + index,
                episode_id=f"evil-{index:03d}",
                split="test",
            )
            for index in range(100)
        ]
        tasks = pairwise.build_tasks(registry, models, panel, "e" * 64, False)
        rows = []
        for task in tasks:
            a_seat = int(task["model_a_seat"])
            seat_models = (
                [task["model_a"], task["model_b"]]
                if a_seat == 0
                else [task["model_b"], task["model_a"]]
            )
            diagnostics = [{}, {}]
            if router_id in seat_models:
                router_seat = seat_models.index(router_id)
                diagnostics[router_seat] = {
                    "router": {
                        "kind": "shadow_full_expert_router",
                        "prefix_complete": True,
                        "prefix_match": {expert: True for expert in experts},
                        "prefix_errors": {expert: [] for expert in experts},
                        "prefix_first_mismatch": {
                            expert: None for expert in experts
                        },
                        "selected": "evil",
                        "selection_eligible": ["evil"],
                        "selected_fallbacks": 0,
                        "runtime_errors": [],
                    }
                }
            rewards = [0.0, 1.0]
            reward_a = rewards[a_seat]
            reward_b = rewards[1 - a_seat]
            margin = reward_a - reward_b
            rows.append(
                {
                    **task,
                    "engine": "kaggle_environments.make(kaggriculture)",
                    "closed_loop": True,
                    "trace_agent": False,
                    "seat_models": seat_models,
                    "statuses": ["DONE", "DONE"],
                    "rewards": rewards,
                    "done": True,
                    "reward_a": reward_a,
                    "reward_b": reward_b,
                    "margin_a": margin,
                    "score_a": 1.0 if margin > 0 else 0.0,
                    "seat_diagnostics": diagnostics,
                    "error": None,
                }
            )
        self.assertEqual(len(rows), EXPECTED_GAMES)
        with self.assertRaisesRegex(ValueError, "runtime/prefix/fallback"):
            _validate_game_semantics(rows, tasks, registry)

    def test_terminal_state_requires_exact_16_and_all_four_baselines_absent(self) -> None:
        models = _models()
        report = _terminal_state_gate(
            _terminal_state(models), models, _terminal_seal(models), "b" * 64
        )
        self.assertTrue(report["goal_achieved"])
        self.assertEqual(report["required_absent_models_present"], [])

        bad_models = deepcopy(models)
        bad_models[0] = "baseline_v1"
        with self.assertRaisesRegex(ValueError, "baselines remain"):
            _terminal_state_gate(
                _terminal_state(bad_models),
                bad_models,
                _terminal_seal(bad_models),
                "b" * 64,
            )

    def test_synthetic_16_model_matrix_is_exactly_120_pairs_and_24000_games(self) -> None:
        models = _models()
        rows = _matrix_rows(models)
        self.assertEqual(len(rows), EXPECTED_GAMES)
        self.assertEqual(
            _validate_complete_matrix(rows, models, 200),
            {
                "pairs": 120,
                "games": 24_000,
                "unique_seed_clusters": 100,
                "dual_seat_balanced": True,
                "common_seed_panel": True,
            },
        )
        standings = _standings(rows, models)
        self.assertEqual(len(standings), 16)
        self.assertTrue(all(item["games"] == 3000 for item in standings))
        with self.assertRaises(ValueError):
            _validate_complete_matrix(rows[:-1], models, 200)

    def test_pairwise_loader_requires_terminal_preflight_for_16_models(self) -> None:
        models = _models()
        panel_path = V10 / "final_test_panel.json"
        manifest_path = V10 / "evaluation_seed_manifest.jsonl"
        quarantine_path = V10 / "test_exposure_quarantine.json"
        panel = json.loads(panel_path.read_text(encoding="utf-8"))
        protocol = {
            "source_manifest_sha256": _sha256(manifest_path),
            "quarantine_file_sha256": _sha256(quarantine_path),
            "clean_pool_records_sha256": panel["clean_pool_records_sha256"],
            "frozen_panel_file_sha256": _sha256(panel_path),
            "frozen_panel_records_sha256": panel["records_sha256"],
            "panel_sources": 100,
            "games_per_pair": 200,
            "unordered_pairs": 120,
            "expected_games": 24_000,
            "salt": 20260822,
            "model_ids": models,
        }
        registry = Registry(
            path=V10 / "synthetic-terminal-registry.json",
            models={model_id: {"id": model_id} for model_id in models},
            raw={"sealed_before_test": True, "test_protocol": protocol},
        )
        # The terminal state gate must fail before even trying to open these
        # deliberately missing test metadata files.
        with self.assertRaisesRegex(ValueError, "terminal V11 registry"):
            load_sealed_test_panel(
                registry,
                models,
                V10 / "must-not-be-opened-panel.json",
                V10 / "must-not-be-opened-manifest.jsonl",
                V10 / "must-not-be-opened-quarantine.json",
            )
        with self.assertRaisesRegex(ValueError, "terminal V11 registry"):
            load_sealed_test_panel(
                registry, models, panel_path, manifest_path, quarantine_path
            )
        with patch.object(
            pairwise,
            "validate_terminal_test_registry",
            return_value={"sealed_before_final_test": True},
        ):
            records, provenance = load_sealed_test_panel(
                registry, models, panel_path, manifest_path, quarantine_path
            )
            self.assertEqual(len(records), 100)
            self.assertEqual(
                provenance["frozen_panel_records_sha256"], panel["records_sha256"]
            )
            registry.raw["test_protocol"]["expected_games"] = 18_200
            with self.assertRaisesRegex(ValueError, "sealed registry"):
                load_sealed_test_panel(
                    registry, models, panel_path, manifest_path, quarantine_path
                )

    def test_terminal_preflight_binds_state_and_serving_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            models = _models()
            source_path = tmp_path / "pool_registry.json"
            source_path.write_text(
                json.dumps({"models": [{"id": model_id} for model_id in models]}),
                encoding="utf-8",
            )
            source = load_registry(source_path)
            fingerprints = model_fingerprints(source, models)
            state_path = tmp_path / "pool_state.json"
            state = save_state(
                state_path,
                {
                    "schema": STATE_SCHEMA,
                    "status": "goal_achieved",
                    "active_models": models,
                    "candidate_required": False,
                    "pending_candidate": None,
                    "registry": str(source_path),
                    "registry_and_code_sha256": registry_fingerprint(source),
                    "model_entries": {
                        model_id: {"serving_sha256": fingerprints[model_id]}
                        for model_id in models
                    },
                    "goal": {
                        "required_pool_size": 16,
                        "required_absent_models": sorted(BASELINES),
                        "achieved": True,
                        "achieved_after_round": 23,
                    },
                },
            )
            terminal_path = tmp_path / "terminal_pool_registry.json"
            terminal_payload = {
                "schema": "kaggriculture-v11-terminal-pool-registry-1",
                "sealed_before_test": True,
                "sealed_before_final_test": True,
                "test_used_for_fit": False,
                "pre_selection_test_access": False,
                "evaluation_implementation_sha256": pairwise.implementation_fingerprint(),
                "league_terminal_state": {
                    "path": str(state_path),
                    "file_sha256": _sha256(state_path),
                    "state_sha256": state["state_sha256"],
                    "active_models": models,
                    "achieved_after_round": 23,
                    "source_pool_registry": str(source_path),
                    "source_pool_registry_file_sha256": _sha256(source_path),
                    "source_pool_registry_and_code_sha256": registry_fingerprint(source),
                    "serving_fingerprints": fingerprints,
                },
                "models": [source.require(model_id) for model_id in models],
            }
            terminal_path.write_text(json.dumps(terminal_payload), encoding="utf-8")
            terminal = load_registry(terminal_path)
            report = validate_terminal_test_registry(terminal, models)
            self.assertTrue(report["original_baselines_absent"])
            self.assertEqual(report["league_state_sha256"], state["state_sha256"])
            terminal.raw["league_terminal_state"]["file_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "state file/hash"):
                validate_terminal_test_registry(terminal, models)

    def test_complete_build_report_path_on_synthetic_24000_game_matrix(self) -> None:
        """Exercise the whole report builder without opening official test data."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            models = _models()
            model_specs = [{"id": model_id, "kind": "python"} for model_id in models]

            source_path = root / "source_pool.json"
            source_path.write_text(
                json.dumps({"models": model_specs}, sort_keys=True),
                encoding="utf-8",
            )
            source_registry = load_registry(source_path)
            serving = model_fingerprints(source_registry, models)

            state_path = root / "terminal_state.json"
            state = save_state(
                state_path,
                {
                    "schema": STATE_SCHEMA,
                    "status": "goal_achieved",
                    "active_models": models,
                    "candidate_required": False,
                    "pending_candidate": None,
                    "registry": str(source_path),
                    "registry_and_code_sha256": registry_fingerprint(source_registry),
                    "model_entries": {
                        model_id: {"serving_sha256": serving[model_id]}
                        for model_id in models
                    },
                    "goal": {
                        "required_pool_size": 16,
                        "required_absent_models": sorted(BASELINES),
                        "achieved": True,
                        "achieved_after_round": 23,
                    },
                },
            )

            panel = [
                pairwise.SeedRecord(
                    date=(
                        "2026-08-18"
                        if index < 34
                        else "2026-08-19"
                        if index < 67
                        else "2026-08-20"
                    ),
                    seed=10_000 + index,
                    episode_id=f"synthetic-{index:03d}",
                    split="test",
                )
                for index in range(100)
            ]
            panel_sha = terminal_report._panel_sha256(panel)
            protocol = {
                "model_ids": models,
                "unordered_pairs": 120,
                "games_per_pair": 200,
                "expected_games": 24_000,
                "frozen_panel_records_sha256": panel_sha,
                "source_manifest_sha256": "1" * 64,
                "quarantine_file_sha256": "2" * 64,
                "clean_pool_records_sha256": "3" * 64,
                "frozen_panel_file_sha256": "4" * 64,
                "salt": 20260822,
            }
            terminal_path = root / "terminal_registry.json"
            terminal_payload = {
                "schema": "kaggriculture-v11-terminal-pool-registry-1",
                "sealed_before_test": True,
                "sealed_before_final_test": True,
                "test_protocol": protocol,
                "league_terminal_state": {
                    "path": str(state_path),
                    "file_sha256": _sha256(state_path),
                    "state_sha256": state["state_sha256"],
                    "active_models": models,
                    "achieved_after_round": 23,
                    "source_pool_registry": str(source_path),
                    "source_pool_registry_file_sha256": _sha256(source_path),
                    "source_pool_registry_and_code_sha256": registry_fingerprint(
                        source_registry
                    ),
                    "serving_fingerprints": serving,
                },
                "models": model_specs,
            }
            terminal_path.write_text(
                json.dumps(terminal_payload, sort_keys=True), encoding="utf-8"
            )
            terminal_registry = load_registry(terminal_path)

            run_fingerprint = "f" * 64
            tasks = pairwise.build_tasks(
                terminal_registry, models, panel, run_fingerprint, False
            )
            rows = []
            for task in tasks:
                seat = int(task["model_a_seat"])
                rewards = [0.0, 1.0]
                reward_a = rewards[seat]
                reward_b = rewards[1 - seat]
                margin = reward_a - reward_b
                rows.append(
                    {
                        **task,
                        "engine": "kaggle_environments.make(kaggriculture)",
                        "closed_loop": True,
                        "trace_agent": False,
                        "seat_models": (
                            [task["model_a"], task["model_b"]]
                            if seat == 0
                            else [task["model_b"], task["model_a"]]
                        ),
                        "statuses": ["DONE", "DONE"],
                        "rewards": rewards,
                        "done": True,
                        "reward_a": reward_a,
                        "reward_b": reward_b,
                        "margin_a": margin,
                        "score_a": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
                        "seat_diagnostics": [{}, {}],
                        "error": None,
                    }
                )
            self.assertEqual(len(rows), EXPECTED_GAMES)

            sealed_runtime = {
                key: protocol[key]
                for key in (
                    "source_manifest_sha256",
                    "quarantine_file_sha256",
                    "clean_pool_records_sha256",
                    "frozen_panel_file_sha256",
                    "frozen_panel_records_sha256",
                    "salt",
                )
            }
            sealed_runtime["terminal_pool"] = {
                "sealed_before_final_test": True,
                "league_state_file_sha256": _sha256(state_path),
                "league_state_sha256": state["state_sha256"],
                "goal_achieved_after_round": 23,
                "original_baselines_absent": True,
            }
            summary = {
                "schema": "kaggriculture-v10-pairwise-summary-1",
                "closed_loop": True,
                "trace_agent_used": False,
                "models": models,
                "expected_pairs": 120,
                "games_per_pair": 200,
                "expected_tasks": 24_000,
                "deduplicated_tasks": 24_000,
                "include_self_play": False,
                "formal_gate_complete": True,
                "run_fingerprint": run_fingerprint,
                "provenance": {
                    "split": "test",
                    "evaluation_implementation_sha256": "i" * 64,
                    "registry_sha256": registry_fingerprint(terminal_registry),
                    "registry_file_sha256": _sha256(terminal_path),
                    "seed_panel": [
                        {
                            "date": item.date,
                            "seed": item.seed,
                            "episode_id": item.episode_id,
                            "split": item.split,
                            "source_path": item.source_path,
                            "lineage_fold": item.lineage_fold,
                        }
                        for item in panel
                    ],
                    "sealed_test_protocol": sealed_runtime,
                },
            }
            jsonl_audit = {
                "deduplicated_records": 24_000,
                "valid_done_records": 24_000,
                "foreign_records": 0,
                "conflicting_success_records": 0,
            }
            with (
                patch.object(
                    terminal_report,
                    "_validate_registry_seals",
                    return_value={"synthetic": True},
                ),
                patch.object(
                    terminal_report,
                    "implementation_fingerprint",
                    return_value="i" * 64,
                ),
                patch.object(
                    terminal_report,
                    "evaluation_fingerprint",
                    return_value=run_fingerprint,
                ),
            ):
                report = build_report(
                    rows=rows,
                    jsonl_audit=jsonl_audit,
                    summary=summary,
                    registry_path=terminal_path,
                    state_path=state_path,
                )
            self.assertEqual(report["games"], 24_000)
            self.assertEqual(report["matrix_audit"]["pairs"], 120)
            self.assertTrue(report["semantic_audit"]["task_fields_recomputed"])


if __name__ == "__main__":
    unittest.main()
