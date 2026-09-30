#!/usr/bin/env python3
"""Read-only verifier for the terminal 16-model V11 sealed-test matrix.

The league must already have reached its registered terminal condition before
the test run: exactly 16 active models and all four original baselines absent.
This verifier never fits, tunes, mutates league state, or launches an
environment.  It reconstructs all 24,000 expected tasks from the sealed
registry, terminal state and pre-frozen 100-source clean test panel.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from .league import (
        TARGET_BASELINES,
        load_state,
        model_fingerprints,
    )
except ImportError:  # direct-file CLI compatibility
    from league import TARGET_BASELINES, load_state, model_fingerprints

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
    registry_fingerprint,
    resolve_path,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate import (
    SeedRecord,
    build_tasks,
    evaluation_fingerprint,
    implementation_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.report_frozen_test import (
    _read_jsonl,
    _sha256,
    _validate_complete_matrix,
    _validate_registry_seals,
)


SCHEMA = "kaggriculture-v11-terminal-frozen-test-report-1"
FINAL_REGISTRY_SCHEMA = "kaggriculture-v11-terminal-pool-registry-1"
PAIRWISE_SUMMARY_SCHEMA = "kaggriculture-v10-pairwise-summary-1"
MODEL_COUNT = 16
PAIR_COUNT = 120
SEEDS = 100
GAMES_PER_PAIR = 200
EXPECTED_GAMES = 24_000


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _terminal_state_gate(
    state: Mapping[str, Any],
    model_ids: Sequence[str],
    terminal_seal: Mapping[str, Any],
    state_file_sha256: str,
) -> dict[str, Any]:
    """Pure terminal-state gate, kept separately testable with synthetic data."""

    model_ids = [str(item) for item in model_ids]
    goal = state.get("goal") or {}
    absent = set(str(item) for item in TARGET_BASELINES)
    active = [str(item) for item in (state.get("active_models") or [])]
    if len(model_ids) != MODEL_COUNT or len(set(model_ids)) != MODEL_COUNT:
        raise ValueError("terminal registry must contain exactly 16 unique models")
    if active != model_ids:
        raise ValueError("terminal registry model order differs from league active pool")
    if set(active) & absent:
        raise ValueError("one or more original baselines remain in the terminal pool")
    if state.get("status") != "goal_achieved" or goal.get("achieved") is not True:
        raise ValueError("league state has not reached the registered terminal goal")
    if int(goal.get("required_pool_size") or -1) != MODEL_COUNT:
        raise ValueError("league terminal pool-size goal changed")
    if set(goal.get("required_absent_models") or []) != absent:
        raise ValueError("league terminal absent-model goal changed")
    if goal.get("achieved_after_round") is None:
        raise ValueError("league terminal state has no achieved round")
    if state.get("pending_candidate") or state.get("candidate_required"):
        raise ValueError("terminal league state still has a pending candidate")
    if terminal_seal.get("file_sha256") != state_file_sha256:
        raise ValueError("terminal registry is bound to a different league-state file")
    if terminal_seal.get("state_sha256") != state.get("state_sha256"):
        raise ValueError("terminal registry is bound to a different state checksum")
    if terminal_seal.get("active_models") != model_ids:
        raise ValueError("terminal registry seal contains a different active pool")
    if terminal_seal.get("achieved_after_round") != goal.get(
        "achieved_after_round"
    ):
        raise ValueError("terminal registry seal contains a different achieved round")
    return {
        "goal_achieved": True,
        "achieved_after_round": goal.get("achieved_after_round"),
        "active_models": model_ids,
        "required_absent_models": sorted(absent),
        "required_absent_models_present": [],
        "state_sha256": state.get("state_sha256"),
        "state_file_sha256": state_file_sha256,
    }


def _panel_from_summary(summary: Mapping[str, Any]) -> list[SeedRecord]:
    provenance = summary.get("provenance") or {}
    return [
        SeedRecord(
            date=str(item["date"]),
            seed=int(item["seed"]),
            episode_id=str(item["episode_id"]),
            split=str(item["split"]),
            source_path=str(item.get("source_path") or ""),
            lineage_fold=str(item.get("lineage_fold") or ""),
        )
        for item in (provenance.get("seed_panel") or [])
    ]


def _panel_sha256(panel: Sequence[SeedRecord]) -> str:
    return _canonical_sha256(
        [
            {
                "date": item.date,
                "seed": item.seed,
                "episode_id": item.episode_id,
                "split": item.split,
                "source_path": item.source_path,
                "lineage_fold": item.lineage_fold,
            }
            for item in panel
        ]
    )


def _standings(rows: Sequence[Mapping[str, Any]], model_ids: Sequence[str]) -> list[dict[str, Any]]:
    stats = {
        model_id: {
            "model_id": model_id,
            "games": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "points": 0.0,
            "margin_sum": 0.0,
        }
        for model_id in model_ids
    }
    for row in rows:
        a, b = str(row["model_a"]), str(row["model_b"])
        score_a = float(row["score_a"])
        margin_a = float(row["margin_a"])
        for model_id, score, margin in (
            (a, score_a, margin_a),
            (b, 1.0 - score_a, -margin_a),
        ):
            item = stats[model_id]
            item["games"] += 1
            item["points"] += score
            item["margin_sum"] += margin
            key = "wins" if score == 1.0 else "draws" if score == 0.5 else "losses"
            item[key] += 1
    result = []
    for item in stats.values():
        if item["games"] != (MODEL_COUNT - 1) * GAMES_PER_PAIR:
            raise ValueError(f"incomplete terminal schedule for {item['model_id']}")
        item["score_rate"] = float(item["points"]) / int(item["games"])
        item["mean_margin"] = float(item.pop("margin_sum")) / int(item["games"])
        result.append(item)
    result.sort(
        key=lambda item: (
            -float(item["points"]),
            -float(item["mean_margin"]),
            str(item["model_id"]),
        )
    )
    for rank, item in enumerate(result, 1):
        item["rank"] = rank
    return result


def _walk_diagnostics(value: Any):
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_diagnostics(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_diagnostics(nested)


def _router_ancestry(
    registry: Any,
    model_id: str,
    stack: tuple[tuple[str, str], ...] = (),
) -> dict[str, Any] | None:
    """Resolve a direct Router or a residual candidate's Router ancestor."""

    key = (str(registry.path), str(model_id))
    if key in stack:
        raise ValueError(f"recursive terminal model ancestry: {key}")
    spec = registry.require(model_id)
    if spec.get("kind") == "router":
        return {
            "experts": [str(item) for item in (spec.get("experts") or [])],
            "fast": False,
        }
    if spec.get("fast_shadow") is True:
        logical = ((spec.get("factory_kwargs") or {}).get("router_spec") or {})
        return {
            "experts": [str(item) for item in (logical.get("experts") or [])],
            "fast": True,
        }
    factory_kwargs = spec.get("factory_kwargs") or {}
    parent_value = (
        factory_kwargs.get("parent_registry")
        if isinstance(factory_kwargs, Mapping)
        else None
    )
    parent_id = (
        factory_kwargs.get("parent_id")
        if isinstance(factory_kwargs, Mapping)
        else None
    )
    if not parent_value or not parent_id:
        return None
    module_value = spec.get("path") or spec.get("module_path")
    module_path = (
        resolve_path(registry, str(module_value)) if module_value else registry.path
    )
    dependency = Path(str(parent_value)).expanduser()
    if not dependency.is_absolute():
        dependency = (module_path.parent / dependency).resolve()
    parent_registry = load_registry(dependency)
    return _router_ancestry(
        parent_registry,
        str(parent_id),
        (*stack, key),
    )


def _validate_game_semantics(
    rows: Sequence[Mapping[str, Any]],
    expected_tasks: Sequence[Mapping[str, Any]],
    registry: Any,
) -> dict[str, Any]:
    """Recompute every row field rather than trusting a matching task id."""

    expected = {str(task["task_id"]): task for task in expected_tasks}
    router_ancestry = {
        model_id: value
        for model_id in registry.models
        if (value := _router_ancestry(registry, model_id)) is not None
    }
    router_observations = Counter()
    for row in rows:
        task_id = str(row.get("task_id") or "")
        task = expected.get(task_id)
        if task is None:
            raise ValueError(f"unknown terminal task_id: {task_id}")
        for key in ("pair_id", "model_a", "model_b", "model_a_seat", "source"):
            if row.get(key) != task.get(key):
                raise ValueError(f"task_id/row semantic mismatch for {key}: {task_id}")
        a, b = str(task["model_a"]), str(task["model_b"])
        a_seat = int(task["model_a_seat"])
        expected_seat_models = [a, b] if a_seat == 0 else [b, a]
        if row.get("seat_models") != expected_seat_models:
            raise ValueError(f"seat_models disagree with model_a_seat: {task_id}")
        if (
            row.get("closed_loop") is not True
            or row.get("trace_agent") is not False
            or row.get("engine") != "kaggle_environments.make(kaggriculture)"
            or row.get("done") is not True
            or row.get("error") is not None
            or row.get("statuses") != ["DONE", "DONE"]
        ):
            raise ValueError(f"non-closed-loop/DONE terminal row: {task_id}")
        rewards = row.get("rewards")
        if (
            not isinstance(rewards, list)
            or len(rewards) != 2
            or not all(np.isfinite(float(value)) for value in rewards)
        ):
            raise ValueError(f"invalid terminal rewards: {task_id}")
        reward_a = float(row.get("reward_a"))
        reward_b = float(row.get("reward_b"))
        margin_a = float(row.get("margin_a"))
        score_a = float(row.get("score_a"))
        expected_reward_a = float(rewards[a_seat])
        expected_reward_b = float(rewards[1 - a_seat])
        expected_margin = expected_reward_a - expected_reward_b
        expected_score = 1.0 if expected_margin > 0 else 0.5 if expected_margin == 0 else 0.0
        if (
            not all(np.isfinite(value) for value in (reward_a, reward_b, margin_a, score_a))
            or reward_a != expected_reward_a
            or reward_b != expected_reward_b
            or margin_a != expected_margin
            or score_a not in {0.0, 0.5, 1.0}
            or score_a != expected_score
        ):
            raise ValueError(f"reward/margin/score semantic mismatch: {task_id}")
        diagnostics = row.get("seat_diagnostics")
        if not isinstance(diagnostics, list) or len(diagnostics) != 2:
            raise ValueError(f"missing seat diagnostics: {task_id}")
        for seat, model_id in enumerate(expected_seat_models):
            nodes = list(_walk_diagnostics(diagnostics[seat]))
            if any(node.get("diagnostic_error") for node in nodes):
                raise ValueError(f"agent diagnostic_error: {model_id}/{task_id}")
            if any(list(node.get("runtime_errors") or []) for node in nodes):
                raise ValueError(f"agent runtime_errors: {model_id}/{task_id}")
            router_nodes = [
                node
                for node in nodes
                if node.get("kind") == "shadow_full_expert_router"
            ]
            ancestry = router_ancestry.get(model_id)
            if ancestry is None:
                if router_nodes:
                    raise ValueError(
                        f"unexpected hidden Router diagnostics: {model_id}/{task_id}"
                    )
                continue
            if len(router_nodes) != 1:
                raise ValueError(
                    f"missing/ambiguous Router ancestry diagnostics: {model_id}/{task_id}"
                )
            diag = router_nodes[0]
            experts = list(ancestry["experts"])
            expert_set = set(experts)
            eligible_items = [
                str(item) for item in (diag.get("selection_eligible") or [])
            ]
            eligible = set(eligible_items)
            selected = str(diag.get("selected") or "")
            prefix_match = diag.get("prefix_match") or {}
            prefix_errors = diag.get("prefix_errors") or {}
            prefix_mismatches = diag.get("prefix_first_mismatch") or {}
            if (
                not diag
                or diag.get("kind") != "shadow_full_expert_router"
                or diag.get("prefix_complete") is not True
                or set(prefix_match) != set(experts)
                or set(prefix_errors) != set(experts)
                or set(prefix_mismatches) != set(experts)
                or not all(value is True for value in prefix_match.values())
                or any(value for value in prefix_errors.values())
                or any(value is not None for value in prefix_mismatches.values())
                or int(diag.get("selected_fallbacks") or 0) != 0
                or list(diag.get("runtime_errors") or [])
                or not eligible
                or len(eligible_items) != len(eligible)
                or not eligible <= expert_set
                or selected not in expert_set
                or selected not in eligible
                or (
                    ancestry["fast"] is True
                    and diag.get("fast_shadow") is not True
                )
            ):
                raise ValueError(f"Router runtime/prefix/fallback failure: {model_id}/{task_id}")
            router_observations[model_id] += 1
    expected_router_observations = (MODEL_COUNT - 1) * GAMES_PER_PAIR
    if any(
        router_observations[model_id] != expected_router_observations
        for model_id in router_ancestry
    ):
        raise ValueError(
            f"incomplete Router diagnostics: {dict(router_observations)}"
        )
    return {
        "rows": len(rows),
        "task_fields_recomputed": True,
        "reward_score_semantics_recomputed": True,
        "router_models": sorted(router_ancestry),
        "router_observations": dict(router_observations),
        "router_prefix_runtime_fallback_failures": 0,
    }


def build_report(
    *,
    rows: Sequence[Mapping[str, Any]],
    jsonl_audit: Mapping[str, Any],
    summary: Mapping[str, Any],
    registry_path: Path,
    state_path: Path,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    state = load_state(state_path)
    model_ids = [str(item) for item in registry.models]
    raw = registry.raw
    if raw.get("schema") != FINAL_REGISTRY_SCHEMA:
        raise ValueError("unexpected terminal 16-model registry schema")
    if (
        raw.get("sealed_before_final_test") is not True
        or raw.get("sealed_before_test") is not True
    ):
        raise ValueError("terminal registry was not sealed before final test")
    terminal_gate = _terminal_state_gate(
        state,
        model_ids,
        raw.get("league_terminal_state") or {},
        _sha256(state_path),
    )
    terminal_seal = raw.get("league_terminal_state") or {}
    seal_audit = _validate_registry_seals(registry)
    source_registry_path = Path(str(state["registry"])).expanduser()
    if not source_registry_path.is_absolute():
        source_registry_path = (state_path.parent / source_registry_path).resolve()
    source_registry = load_registry(source_registry_path)
    if terminal_seal.get("source_pool_registry_file_sha256") != _sha256(
        source_registry.path
    ):
        raise ValueError("terminal registry is bound to a different source pool file")
    if registry_fingerprint(source_registry) != state.get(
        "registry_and_code_sha256"
    ):
        raise ValueError("terminal state's source pool registry changed")
    if terminal_seal.get("source_pool_registry_and_code_sha256") != state.get(
        "registry_and_code_sha256"
    ):
        raise ValueError("terminal registry is bound to a different source pool registry")
    source_fingerprints = model_fingerprints(source_registry, model_ids)
    terminal_fingerprints = model_fingerprints(registry, model_ids)
    if source_fingerprints != terminal_fingerprints:
        raise ValueError("terminal registry changed one or more active serving policies")
    state_fingerprints = {
        model_id: str((state.get("model_entries") or {}).get(model_id, {}).get("serving_sha256") or "")
        for model_id in model_ids
    }
    if terminal_fingerprints != state_fingerprints:
        raise ValueError("terminal serving policies differ from league-state fingerprints")

    if summary.get("schema") != PAIRWISE_SUMMARY_SCHEMA:
        raise ValueError("unexpected pairwise summary schema")
    if summary.get("closed_loop") is not True or summary.get("trace_agent_used") is not False:
        raise ValueError("terminal test is not a real closed-loop/no-TraceAgent run")
    if [str(item) for item in (summary.get("models") or [])] != model_ids:
        raise ValueError("terminal test summary model order differs from sealed registry")
    expected_counts = {
        "expected_pairs": PAIR_COUNT,
        "games_per_pair": GAMES_PER_PAIR,
        "expected_tasks": EXPECTED_GAMES,
        "deduplicated_tasks": EXPECTED_GAMES,
    }
    if any(int(summary.get(key) or -1) != value for key, value in expected_counts.items()):
        raise ValueError("terminal test summary does not cover exact 120x200 tasks")
    if summary.get("include_self_play") or summary.get("formal_gate_complete") is not True:
        raise ValueError("terminal test summary is incomplete or contains self-play")
    if (
        int(jsonl_audit.get("deduplicated_records", -1)) != EXPECTED_GAMES
        or int(jsonl_audit.get("valid_done_records", -1)) != EXPECTED_GAMES
        or int(jsonl_audit.get("foreign_records", 0)) != 0
        or int(jsonl_audit.get("conflicting_success_records", 0)) != 0
    ):
        raise ValueError("terminal test JSONL audit is incomplete/foreign/conflicting")
    matrix_audit = _validate_complete_matrix(rows, model_ids, GAMES_PER_PAIR)
    if matrix_audit != {
        "pairs": PAIR_COUNT,
        "games": EXPECTED_GAMES,
        "unique_seed_clusters": SEEDS,
        "dual_seat_balanced": True,
        "common_seed_panel": True,
    }:
        raise ValueError("terminal test JSONL matrix is not exact")

    provenance = summary.get("provenance") or {}
    if provenance.get("split") != "test":
        raise ValueError("terminal test summary is not the sealed test split")
    if provenance.get("evaluation_implementation_sha256") != implementation_fingerprint():
        raise ValueError("pairwise evaluator/runtime changed after terminal test")
    if provenance.get("registry_sha256") != registry_fingerprint(registry):
        raise ValueError("terminal test registry/code fingerprint changed")
    if provenance.get("registry_file_sha256") != _sha256(registry_path):
        raise ValueError("terminal test registry file changed")
    panel = _panel_from_summary(summary)
    if len(panel) != SEEDS or len({int(item.seed) for item in panel}) != SEEDS:
        raise ValueError("terminal test provenance lacks exact 100 unique seeds")
    if Counter(item.date for item in panel) != Counter(
        {"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33}
    ):
        raise ValueError("terminal test panel date quota changed")
    if any(item.split != "test" for item in panel):
        raise ValueError("terminal test panel contains a non-test source")
    protocol = raw.get("test_protocol") or {}
    if (
        protocol.get("model_ids") != model_ids
        or protocol.get("unordered_pairs") != PAIR_COUNT
        or protocol.get("games_per_pair") != GAMES_PER_PAIR
        or protocol.get("expected_games") != EXPECTED_GAMES
        or _panel_sha256(panel) != protocol.get("frozen_panel_records_sha256")
    ):
        raise ValueError("terminal test provenance differs from sealed test protocol")
    sealed_run = provenance.get("sealed_test_protocol") or {}
    for key in (
        "source_manifest_sha256",
        "quarantine_file_sha256",
        "clean_pool_records_sha256",
        "frozen_panel_file_sha256",
        "frozen_panel_records_sha256",
        "salt",
    ):
        if sealed_run.get(key) != protocol.get(key):
            raise ValueError(f"terminal test runtime differs from registry seal: {key}")
    runtime_terminal = sealed_run.get("terminal_pool") or {}
    if (
        runtime_terminal.get("sealed_before_final_test") is not True
        or runtime_terminal.get("league_state_file_sha256")
        != terminal_gate["state_file_sha256"]
        or runtime_terminal.get("league_state_sha256")
        != terminal_gate["state_sha256"]
        or runtime_terminal.get("goal_achieved_after_round")
        != terminal_gate["achieved_after_round"]
        or runtime_terminal.get("original_baselines_absent") is not True
    ):
        raise ValueError("terminal test runtime lacks the goal-achieved preflight seal")

    run_fingerprint = str(summary.get("run_fingerprint") or "")
    expected_run_fingerprint = evaluation_fingerprint(
        registry, model_ids, panel, GAMES_PER_PAIR, False
    )
    if run_fingerprint != expected_run_fingerprint:
        raise ValueError("terminal test run fingerprint cannot be reproduced")
    expected_tasks = build_tasks(registry, model_ids, panel, run_fingerprint, False)
    if {str(row.get("task_id") or "") for row in rows} != {
        str(task["task_id"]) for task in expected_tasks
    }:
        raise ValueError("terminal test task IDs differ from the sealed manifest")
    semantic_audit = _validate_game_semantics(rows, expected_tasks, registry)

    return {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read_only_post_test_report": True,
        "fit_or_tuning_performed": False,
        "closed_loop": True,
        "trace_agent_used": False,
        "models": model_ids,
        "model_count": MODEL_COUNT,
        "original_baselines_absent": True,
        "games_per_pair": GAMES_PER_PAIR,
        "pairs": PAIR_COUNT,
        "games": EXPECTED_GAMES,
        "run_fingerprint": run_fingerprint,
        "league_terminal_state_audit": terminal_gate,
        "pretest_seal_audit": seal_audit,
        "jsonl_audit": dict(jsonl_audit),
        "matrix_audit": matrix_audit,
        "semantic_audit": semantic_audit,
        "standings": _standings(rows, model_ids),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, nargs="+", required=True)
    parser.add_argument("--pairwise-summary", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--league-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary_path = args.pairwise_summary.expanduser().resolve()
    registry_path = args.registry.expanduser().resolve()
    state_path = args.league_state.expanduser().resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run_fingerprint = str(summary.get("run_fingerprint") or "")
    rows, jsonl_audit = _read_jsonl(args.games, run_fingerprint)
    report = build_report(
        rows=rows,
        jsonl_audit=jsonl_audit,
        summary=summary,
        registry_path=registry_path,
        state_path=state_path,
    )
    report["provenance"] = {
        "pairwise_summary": str(summary_path),
        "pairwise_summary_sha256": _sha256(summary_path),
        "registry": str(registry_path),
        "registry_file_sha256": _sha256(registry_path),
        "league_state": str(state_path),
        "league_state_file_sha256": _sha256(state_path),
        "games": [str(path.expanduser().resolve()) for path in args.games],
        "games_sha256": {
            str(path.expanduser().resolve()): _sha256(path.expanduser().resolve())
            for path in args.games
        },
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(
        json.dumps(
            {
                "output": str(output),
                "models": report["model_count"],
                "pairs": report["pairs"],
                "games": report["games"],
                "original_baselines_absent": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
