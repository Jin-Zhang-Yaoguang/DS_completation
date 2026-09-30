#!/usr/bin/env python3
"""Audit the one-time frozen 14-model official-test matrix.

The real environments are executed by ``pairwise_evaluate.py --split test``.
This command is deliberately read-only: it loads that completed JSONL and its
summary, verifies the registry/training freeze, and reports paired seed-cluster
comparisons for the preselected best fixed expert, rule Router and learned
Router.  It never fits weights, changes a threshold, or reads replay actions.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from .agent_factory import load_registry, registry_fingerprint, resolve_path
    from .freeze_router_fit_sources import validate_payload as validate_fit_exclusions
    from .freeze_test_panel import validate_payload as validate_test_panel
    from .pairwise_evaluate import (
        SCHEMA as GAME_SCHEMA,
        SeedRecord,
        build_tasks as build_pairwise_tasks,
        evaluation_fingerprint,
        implementation_fingerprint,
    )
except ImportError:  # direct-file CLI compatibility
    from agent_factory import load_registry, registry_fingerprint, resolve_path
    from freeze_router_fit_sources import validate_payload as validate_fit_exclusions
    from freeze_test_panel import validate_payload as validate_test_panel
    from pairwise_evaluate import (
        SCHEMA as GAME_SCHEMA,
        SeedRecord,
        build_tasks as build_pairwise_tasks,
        evaluation_fingerprint,
        implementation_fingerprint,
    )


SCHEMA = "kaggriculture-v10-frozen-test-comparison-1"
TRAINING_SCHEMA = "kaggriculture-v10-learned-router-training-1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _result_digest(row: Mapping[str, Any]) -> str:
    keys = (
        "schema", "task_id", "run_fingerprint", "pair_id", "model_a",
        "model_b", "model_a_seat", "source", "statuses", "rewards",
        "score_a", "margin_a", "seat_diagnostics",
    )
    payload = {key: row.get(key) for key in keys}
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_jsonl(paths: Sequence[Path], run_fingerprint: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: dict[str, dict[str, Any]] = {}
    audit = Counter()
    for path in paths:
        with path.expanduser().resolve().open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                audit["input_records"] += 1
                row = json.loads(line)
                if row.get("schema") != GAME_SCHEMA or row.get("run_fingerprint") != run_fingerprint:
                    audit["foreign_records"] += 1
                    continue
                task_id = str(row.get("task_id") or f"{path}:{line_number}")
                previous = rows.get(task_id)
                success = row.get("error") is None and row.get("done") is True
                previous_success = (
                    previous is not None
                    and previous.get("error") is None
                    and previous.get("done") is True
                )
                if previous is not None:
                    audit["duplicate_records"] += 1
                if success and previous_success:
                    if _result_digest(row) != _result_digest(previous):
                        audit["conflicting_success_records"] += 1
                    else:
                        audit["identical_success_records"] += 1
                elif success and previous is not None:
                    audit["retry_success_replacements"] += 1
                elif previous_success:
                    audit["failure_after_success_ignored"] += 1
                if previous is None or success or not previous_success:
                    rows[task_id] = row
    audit["deduplicated_records"] = len(rows)
    audit["valid_done_records"] = sum(
        row.get("error") is None and row.get("done") is True for row in rows.values()
    )
    return list(rows.values()), dict(audit)


def _source_key(row: Mapping[str, Any]) -> tuple[str, str, int]:
    source = row.get("source") or {}
    return str(source.get("date") or ""), str(source.get("episode_id") or ""), int(source.get("seed") or 0)


def _oriented(row: Mapping[str, Any], model_id: str) -> dict[str, Any] | None:
    a, b = str(row.get("model_a")), str(row.get("model_b"))
    if a == b or model_id not in {a, b}:
        return None
    score_a = float(row["score_a"])
    margin_a = float(row["margin_a"])
    a_seat = int(row["model_a_seat"])
    if model_id == a:
        opponent, score, margin, seat = b, score_a, margin_a, a_seat
    else:
        opponent, score, margin, seat = a, 1.0 - score_a, -margin_a, 1 - a_seat
    return {
        "source": _source_key(row),
        "opponent": opponent,
        "seat": seat,
        "score": score,
        "margin": margin,
    }


def _seat_balanced(
    rows: Sequence[Mapping[str, Any]], model_id: str, opponents: set[str]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[tuple[str, str, int], str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row.get("error") is not None or not row.get("done") or row.get("score_a") is None:
            continue
        value = _oriented(row, model_id)
        if value is None or value["opponent"] not in opponents:
            continue
        grouped[(value["source"], value["opponent"])][value["seat"]] = value
    result = []
    for (source, opponent), seats in sorted(grouped.items()):
        if set(seats) != {0, 1}:
            continue
        result.append(
            {
                "source": source,
                "opponent": opponent,
                "score": float(np.mean([seats[0]["score"], seats[1]["score"]])),
                "margin": float(np.mean([seats[0]["margin"], seats[1]["margin"]])),
            }
        )
    return result


def _cluster(values: Sequence[Mapping[str, Any]], metric: str) -> dict[tuple[str, str, int], float]:
    grouped: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in values:
        grouped[tuple(row["source"])].append(float(row[metric]))
    return {key: float(np.mean(items)) for key, items in grouped.items()}


def _bootstrap(values: Sequence[float], seed: int, rounds: int = 4000) -> list[float | None]:
    array = np.asarray(values, dtype=np.float64)
    if not len(array):
        return [None, None]
    rng = np.random.default_rng(int(seed))
    samples = np.empty(rounds, dtype=np.float64)
    for start in range(0, rounds, 500):
        count = min(500, rounds - start)
        indices = rng.integers(0, len(array), size=(count, len(array)))
        samples[start : start + count] = array[indices].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def _stable_seed(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


def _metric(values: Sequence[Mapping[str, Any]], name: str) -> dict[str, Any]:
    clustered = _cluster(values, name)
    numbers = list(clustered.values())
    return {
        "contexts": len(values),
        "independent_seed_clusters": len(numbers),
        "mean": float(np.mean(numbers)) if numbers else None,
        "ci95": _bootstrap(numbers, _stable_seed(name)),
    }


def _difference(
    left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]], metric: str, label: str
) -> dict[str, Any]:
    left_context = {(tuple(row["source"]), row["opponent"]): float(row[metric]) for row in left}
    right_context = {(tuple(row["source"]), row["opponent"]): float(row[metric]) for row in right}
    keys = sorted(set(left_context) & set(right_context))
    by_seed: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for source, opponent in keys:
        by_seed[source].append(left_context[(source, opponent)] - right_context[(source, opponent)])
    numbers = [float(np.mean(items)) for items in by_seed.values()]
    return {
        "paired_contexts": len(keys),
        "independent_seed_clusters": len(numbers),
        "mean_difference": float(np.mean(numbers)) if numbers else None,
        "ci95": _bootstrap(numbers, _stable_seed(label)),
    }


def _router_diagnostics(rows: Sequence[Mapping[str, Any]], router_id: str) -> dict[str, Any]:
    selected = Counter()
    reasons = Counter()
    eligible_sizes = Counter()
    prefix_failures = 0
    selected_fallbacks = 0
    observations = 0
    for row in rows:
        if row.get("error") is not None or not row.get("done"):
            continue
        a, b = str(row.get("model_a")), str(row.get("model_b"))
        if router_id not in {a, b} or a == b:
            continue
        seat = int(row["model_a_seat"]) if router_id == a else 1 - int(row["model_a_seat"])
        seat_diagnostics = row.get("seat_diagnostics") or []
        if len(seat_diagnostics) != 2 or not isinstance(seat_diagnostics[seat], Mapping):
            continue
        wrapper = seat_diagnostics[seat]
        # pairwise_evaluate normally wraps AgentHandle diagnostics under
        # ``router``; direct AgentHandle captures expose the same payload at
        # top level.  Accept both without turning a valid selection into
        # ``<missing>``.
        diag = wrapper if wrapper.get("kind") == "shadow_full_expert_router" else (wrapper.get("router") or {})
        if not isinstance(diag, Mapping):
            continue
        observations += 1
        selected[str(diag.get("selected") or "<missing>")] += 1
        reasons[str(diag.get("selection_reason") or "<missing>")] += 1
        eligible_sizes[len(diag.get("selection_eligible") or [])] += 1
        if not diag.get("prefix_complete") or not all((diag.get("prefix_match") or {}).values()):
            prefix_failures += 1
        selected_fallbacks += int(diag.get("selected_fallbacks") or 0)
    total = max(1, observations)
    return {
        "observations": observations,
        "selection_counts": dict(selected),
        "selection_rates": {key: value / total for key, value in selected.items()},
        "reason_counts": dict(reasons),
        "reason_rates": {key: value / total for key, value in reasons.items()},
        "eligible_size_counts": {str(key): value for key, value in eligible_sizes.items()},
        "prefix_failures": prefix_failures,
        "selected_action_fallbacks": selected_fallbacks,
    }


def _validate_complete_matrix(
    rows: Sequence[Mapping[str, Any]], models: Sequence[str], games_per_pair: int
) -> dict[str, Any]:
    expected_pairs = {
        f"{left}__vs__{right}" for left, right in itertools.combinations(models, 2)
    }
    by_pair: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("error") is not None or row.get("done") is not True:
            raise ValueError("test JSONL contains a failed or non-DONE task")
        pair_id = str(row.get("pair_id") or "")
        if pair_id not in expected_pairs:
            raise ValueError(f"unexpected pair id in test JSONL: {pair_id}")
        if pair_id != f"{row.get('model_a')}__vs__{row.get('model_b')}":
            raise ValueError(f"pair id/model fields disagree: {pair_id}")
        by_pair[pair_id].append(row)
    if set(by_pair) != expected_pairs:
        raise ValueError("test JSONL pair set differs from the frozen 14-model matrix")

    canonical_sources: set[tuple[str, str, int]] | None = None
    for pair_id, pair_rows in by_pair.items():
        if len(pair_rows) != games_per_pair:
            raise ValueError(
                f"pair {pair_id} has {len(pair_rows)} rows, expected {games_per_pair}"
            )
        seats_by_source: dict[tuple[str, str, int], set[int]] = defaultdict(set)
        for row in pair_rows:
            seats_by_source[_source_key(row)].add(int(row.get("model_a_seat", -1)))
        if len(seats_by_source) != games_per_pair // 2 or any(
            seats != {0, 1} for seats in seats_by_source.values()
        ):
            raise ValueError(f"pair {pair_id} is not 100-seed, dual-seat balanced")
        source_set = set(seats_by_source)
        if canonical_sources is None:
            canonical_sources = source_set
        elif source_set != canonical_sources:
            raise ValueError(f"pair {pair_id} does not use the common frozen seed panel")
    return {
        "pairs": len(by_pair),
        "games": sum(len(value) for value in by_pair.values()),
        "unique_seed_clusters": len(canonical_sources or ()),
        "dual_seat_balanced": True,
        "common_seed_panel": True,
    }


def _serving_router_spec(registry: Any, model_id: str) -> dict[str, Any]:
    """Return the logical Router spec from V10 or a V11 fast proxy."""

    spec = dict(registry.require(model_id))
    if spec.get("kind") == "router":
        return spec
    if spec.get("fast_shadow") is True:
        nested = ((spec.get("factory_kwargs") or {}).get("router_spec") or {})
        if isinstance(nested, Mapping) and nested.get("kind") == "router":
            return dict(nested)
    raise ValueError(f"{model_id} is neither a V10 Router nor a sealed fast proxy")


def _serving_weights_path(registry: Any, model_id: str) -> Path:
    outer = registry.require(model_id)
    logical = _serving_router_spec(registry, model_id)
    value = logical.get("weights")
    if not value:
        raise ValueError(f"{model_id} has no learned weights")
    if outer.get("fast_shadow") is True:
        parent_value = str((outer.get("factory_kwargs") or {}).get("registry_parent") or "")
        if not parent_value:
            raise ValueError("fast Router has no source registry parent")
        parent = Path(parent_value).expanduser().resolve()
        path = Path(str(value)).expanduser()
        return path.resolve() if path.is_absolute() else (parent / path).resolve()
    return resolve_path(registry, str(value))


def _validate_registry_seals(registry: Any) -> dict[str, Any]:
    """Re-hash every metadata-only pre-test seal used by the report."""

    raw = registry.raw
    manifest = raw.get("source_manifest_seal") or {}
    manifest_path = Path(str(manifest.get("path") or "")).expanduser().resolve()
    if not manifest_path.is_file() or _sha256(manifest_path) != manifest.get(
        "file_sha256"
    ):
        raise ValueError("sealed evaluation seed manifest changed")
    if (
        manifest.get("records") != 2090
        or manifest.get("unique_seeds") != 2090
        or manifest.get("dates")
        != ["2026-08-18", "2026-08-19", "2026-08-20"]
        or manifest.get("split_counts")
        != {"test": 210, "train": 1670, "validation": 210}
    ):
        raise ValueError("sealed evaluation seed manifest summary changed")

    fit = raw.get("router_fit_source_exclusions") or {}
    fit_path = Path(str(fit.get("path") or "")).expanduser().resolve()
    if not fit_path.is_file() or _sha256(fit_path) != fit.get("file_sha256"):
        raise ValueError("Router-fit exclusion file changed")
    fit_payload = json.loads(fit_path.read_text(encoding="utf-8"))
    source_grid = Path(str(fit_payload.get("source_grid") or "")).expanduser().resolve()
    fit_seeds = validate_fit_exclusions(fit_payload, source_grid)
    if (
        len(fit_seeds) != 200
        or fit.get("records") != 200
        or fit.get("records_sha256") != fit_payload.get("records_sha256")
        or fit.get("source_grid_file_sha256")
        != fit_payload.get("source_grid_file_sha256")
    ):
        raise ValueError("Router-fit exclusion seal is inconsistent")

    test = raw.get("test_protocol") or {}
    panel_path = Path(str(test.get("frozen_panel") or "")).expanduser().resolve()
    quarantine_path = Path(str(test.get("quarantine") or "")).expanduser().resolve()
    if (
        not panel_path.is_file()
        or _sha256(panel_path) != test.get("frozen_panel_file_sha256")
        or not quarantine_path.is_file()
        or _sha256(quarantine_path) != test.get("quarantine_file_sha256")
    ):
        raise ValueError("frozen test panel/quarantine file changed")
    panel_payload = json.loads(panel_path.read_text(encoding="utf-8"))
    panel = validate_test_panel(panel_payload, manifest_path, quarantine_path)
    if (
        len(panel) != 100
        or panel_payload.get("records_sha256")
        != test.get("frozen_panel_records_sha256")
        or panel_payload.get("clean_pool_records_sha256")
        != test.get("clean_pool_records_sha256")
    ):
        raise ValueError("frozen test panel seal is inconsistent")
    return {
        "source_manifest_sha256": manifest.get("file_sha256"),
        "router_fit_exclusion_file_sha256": fit.get("file_sha256"),
        "router_fit_exclusion_records_sha256": fit.get("records_sha256"),
        "frozen_panel_file_sha256": test.get("frozen_panel_file_sha256"),
        "quarantine_file_sha256": test.get("quarantine_file_sha256"),
    }


def build_report(
    rows: Sequence[Mapping[str, Any]],
    pairwise_summary: Mapping[str, Any],
    training_report: Mapping[str, Any],
    registry_path: Path,
    jsonl_audit: Mapping[str, Any],
    rule_router_id: str = "rule_router",
    learned_router_id: str = "learned_router",
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    seal_audit = _validate_registry_seals(registry)
    if pairwise_summary.get("schema") != "kaggriculture-v10-pairwise-summary-1":
        raise ValueError("unexpected pairwise summary schema")
    if pairwise_summary.get("closed_loop") is not True or pairwise_summary.get("trace_agent_used") is not False:
        raise ValueError("pairwise summary is not a real closed-loop/no-TraceAgent run")
    models = [str(item) for item in (pairwise_summary.get("models") or [])]
    sealed_model_ids = list((registry.raw.get("test_protocol") or {}).get("model_ids") or [])
    if (
        len(models) != 14
        or models != list(registry.models)
        or models != sealed_model_ids
    ):
        raise ValueError("frozen test report requires the exact 14-model final registry")
    if not pairwise_summary.get("formal_gate_complete"):
        raise ValueError("pairwise test matrix is incomplete")
    if int(pairwise_summary.get("games_per_pair") or 0) != 200:
        raise ValueError("each sealed test pair needs exactly 200 balanced-seat games")
    if pairwise_summary.get("include_self_play"):
        raise ValueError("final 91-pair matrix must not include self-play")
    if int(pairwise_summary.get("expected_pairs") or -1) != 91:
        raise ValueError("14-model final matrix must contain exactly 91 unordered pairs")
    expected_tasks = 91 * int(pairwise_summary["games_per_pair"])
    if (
        int(pairwise_summary.get("expected_tasks") or -1) != expected_tasks
        or int(pairwise_summary.get("deduplicated_tasks") or -1) != expected_tasks
    ):
        raise ValueError("pairwise summary task counts are not the exact complete matrix")
    if (
        int(jsonl_audit.get("deduplicated_records", -1)) != expected_tasks
        or int(jsonl_audit.get("valid_done_records", -1)) != expected_tasks
    ):
        raise ValueError(
            "provided test JSONLs do not contain the exact complete 91-pair run"
        )
    if int(jsonl_audit.get("foreign_records", 0)):
        raise ValueError("provided test JSONLs contain foreign run records")
    if int(jsonl_audit.get("conflicting_success_records", 0)):
        raise ValueError("same test task_id has conflicting successful outcomes")
    matrix_audit = _validate_complete_matrix(
        rows, models, int(pairwise_summary["games_per_pair"])
    )
    provenance = pairwise_summary.get("provenance") or {}
    if provenance.get("split") != "test":
        raise ValueError("pairwise summary is not the sealed test split")
    if provenance.get("evaluation_implementation_sha256") != implementation_fingerprint():
        raise ValueError("pairwise evaluator/runtime implementation changed after test")
    if provenance.get("registry_sha256") != registry_fingerprint(registry):
        raise ValueError("pairwise summary registry/code hash differs from current final registry")
    sealed_provenance = provenance.get("sealed_test_protocol") or {}
    sealed_registry = registry.raw.get("test_protocol") or {}
    for key in (
        "source_manifest_sha256",
        "quarantine_file_sha256",
        "clean_pool_records_sha256",
        "frozen_panel_file_sha256",
        "frozen_panel_records_sha256",
        "salt",
    ):
        if sealed_provenance.get(key) != sealed_registry.get(key):
            raise ValueError(f"pairwise test provenance differs from registry seal: {key}")
    panel = [
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
    if len(panel) != int(pairwise_summary["games_per_pair"]) // 2:
        raise ValueError("pairwise provenance has the wrong frozen seed panel size")
    panel_records_hash = hashlib.sha256(
        json.dumps(
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
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if panel_records_hash != sealed_registry.get("frozen_panel_records_sha256"):
        raise ValueError("pairwise seed panel differs from the pre-test-frozen panel")
    if training_report.get("schema") != TRAINING_SCHEMA:
        raise ValueError("unexpected learned Router training-report schema")
    if list(training_report.get("fit_splits") or []) != ["train", "validation"]:
        raise ValueError("learned Router was not frozen from train+validation only")
    if training_report.get("test_used_for_fit") is not False:
        raise ValueError("training report used test for fit")
    if training_report.get("pre_selection_test_access") is not False:
        raise ValueError("training report accessed test before selection")
    if int((training_report.get("rows") or {}).get("test_seen", -1)) != 0:
        raise ValueError("training report contains test rows")
    if (training_report.get("formal_grid_audit") or {}).get("passed") is not True:
        raise ValueError("training report did not pass the formal Router grid gate")

    run_fingerprint = str(pairwise_summary.get("run_fingerprint") or "")
    expected_run_fingerprint = evaluation_fingerprint(
        registry, models, panel, int(pairwise_summary["games_per_pair"]), False
    )
    if run_fingerprint != expected_run_fingerprint:
        raise ValueError("pairwise run fingerprint cannot be reproduced from frozen inputs")
    if not run_fingerprint or any(row.get("run_fingerprint") != run_fingerprint for row in rows):
        raise ValueError("test JSONL mixes run fingerprints")
    if any((row.get("source") or {}).get("split") != "test" for row in rows):
        raise ValueError("test JSONL contains a non-test source")
    expected_tasks = build_pairwise_tasks(
        registry, models, panel, run_fingerprint, include_self_play=False
    )
    if {str(row.get("task_id") or "") for row in rows} != {
        str(task["task_id"]) for task in expected_tasks
    }:
        raise ValueError("test JSONL task IDs differ from the frozen task manifest")

    fixed_models = [
        model_id for model_id in models
        if model_id not in {rule_router_id, learned_router_id}
    ]
    if len(fixed_models) != 12:
        raise ValueError(f"expected 12 fixed experts, got {len(fixed_models)}")
    best_rank = [str(item) for item in (training_report.get("best_fixed_rank") or [])]
    if not best_rank or best_rank[0] not in fixed_models:
        raise ValueError("pre-test training report has no valid best fixed expert")
    best_fixed = best_rank[0]
    if registry.raw.get("sealed_before_test") is not True:
        raise ValueError("final registry was not marked sealed before test")
    if registry.raw.get("best_fixed_model") != best_fixed:
        raise ValueError("final registry best-fixed choice differs from training report")
    for router_id, kind in ((rule_router_id, "rule"), (learned_router_id, "learned")):
        spec = _serving_router_spec(registry, router_id)
        if spec.get("router_kind") != kind:
            raise ValueError(f"{router_id} is not the frozen {kind} Router")
        if [str(item) for item in (spec.get("experts") or [])] != [
            str(item) for item in (training_report.get("classes") or [])
        ]:
            raise ValueError(f"{router_id} expert action space differs from training")

    common_field = set(fixed_models) - {best_fixed}
    contenders = (best_fixed, rule_router_id, learned_router_id)
    policy_rows = {
        model_id: _seat_balanced(rows, model_id, common_field) for model_id in contenders
    }
    expected_contexts = len(common_field) * int(pairwise_summary["games_per_pair"]) // 2
    if any(len(values) != expected_contexts for values in policy_rows.values()):
        sizes = {key: len(value) for key, value in policy_rows.items()}
        raise ValueError(f"contender common-field contexts are incomplete: {sizes}")
    context_keys = {
        model_id: {(tuple(row["source"]), row["opponent"]) for row in values}
        for model_id, values in policy_rows.items()
    }
    if len({frozenset(value) for value in context_keys.values()}) != 1:
        raise ValueError("contenders do not share the exact same source/opponent contexts")

    policies = {
        model_id: {
            "score_rate": _metric(values, "score"),
            "mean_margin": _metric(values, "margin"),
        }
        for model_id, values in policy_rows.items()
    }
    comparisons = {}
    for left, right in (
        (learned_router_id, best_fixed),
        (learned_router_id, rule_router_id),
        (rule_router_id, best_fixed),
    ):
        comparisons[f"{left}_minus_{right}"] = {
            "score_rate": _difference(policy_rows[left], policy_rows[right], "score", f"{left}-{right}-score"),
            "mean_margin": _difference(policy_rows[left], policy_rows[right], "margin", f"{left}-{right}-margin"),
        }

    direct = {}
    for left, right in (
        (best_fixed, rule_router_id),
        (best_fixed, learned_router_id),
        (rule_router_id, learned_router_id),
    ):
        values = _seat_balanced(rows, left, {right})
        expected = int(pairwise_summary["games_per_pair"]) // 2
        if len(values) != expected:
            raise ValueError(f"direct matchup {left} vs {right} is incomplete")
        direct[f"{left}__vs__{right}"] = {
            "perspective": left,
            "score_rate": _metric(values, "score"),
            "mean_margin": _metric(values, "margin"),
        }

    router_diagnostics = {
        rule_router_id: _router_diagnostics(rows, rule_router_id),
        learned_router_id: _router_diagnostics(rows, learned_router_id),
    }
    expected_router_observations = (len(models) - 1) * int(
        pairwise_summary["games_per_pair"]
    )
    if any(
        value["observations"] != expected_router_observations
        for value in router_diagnostics.values()
    ):
        raise ValueError(
            "Router diagnostics are incomplete; expected every test-game selection"
        )
    if any(
        value["prefix_failures"] or value["selected_action_fallbacks"]
        or value["selection_counts"].get("<missing>", 0)
        for value in router_diagnostics.values()
    ):
        raise ValueError("Router serving diagnostics contain prefix/selection fallbacks")

    return {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read_only_post_test_report": True,
        "fit_or_tuning_performed": False,
        "test_used_for_fit": False,
        "pre_selection_test_access": False,
        "closed_loop": True,
        "trace_agent_used": False,
        "run_fingerprint": run_fingerprint,
        "registry_and_code_sha256": registry_fingerprint(registry),
        "models": models,
        "fixed_models": fixed_models,
        "preselected_best_fixed": best_fixed,
        "rule_router": rule_router_id,
        "learned_router": learned_router_id,
        "common_field_opponents": sorted(common_field),
        "games_per_pair": int(pairwise_summary["games_per_pair"]),
        "jsonl_audit": dict(jsonl_audit),
        "matrix_audit": matrix_audit,
        "pretest_seal_audit": seal_audit,
        "policy_vs_common_fixed_field": policies,
        "paired_common_field_differences": comparisons,
        "direct_head_to_head": direct,
        "router_diagnostics": router_diagnostics,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, nargs="+", required=True)
    parser.add_argument("--pairwise-summary", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--rule-router-id", default="rule_router")
    parser.add_argument("--learned-router-id", default="learned_router")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary_path = args.pairwise_summary.expanduser().resolve()
    training_path = args.training_report.expanduser().resolve()
    registry_path = args.registry.expanduser().resolve()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    training = json.loads(training_path.read_text(encoding="utf-8"))
    registry = load_registry(registry_path)
    _validate_registry_seals(registry)
    if registry.raw.get("training_report_sha256") != _sha256(training_path):
        raise ValueError("final registry is not frozen to this training report")
    if (_serving_router_spec(registry, args.rule_router_id).get("rule") or {}) != (
        (training.get("frozen_rule_spec") or {}).get("rule") or {}
    ):
        raise ValueError("final rule Router differs from the train/validation-frozen rule")
    learned_weights = _serving_weights_path(registry, args.learned_router_id)
    if registry.raw.get("learned_weights_sha256") != _sha256(learned_weights):
        raise ValueError("final learned Router weights differ from the sealed registry")
    run_fingerprint = str(summary.get("run_fingerprint") or "")
    rows, audit = _read_jsonl(args.games, run_fingerprint)
    report = build_report(
        rows, summary, training, registry_path, audit,
        args.rule_router_id, args.learned_router_id,
    )
    report["provenance"] = {
        "pairwise_summary": str(summary_path),
        "pairwise_summary_sha256": _sha256(summary_path),
        "training_report": str(training_path),
        "training_report_sha256": _sha256(training_path),
        "registry": str(registry_path),
        "games": [str(path.expanduser().resolve()) for path in args.games],
        "games_sha256": {
            str(path.expanduser().resolve()): _sha256(path.expanduser().resolve())
            for path in args.games
        },
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(
        json.dumps(
            {
                "output": str(output),
                "preselected_best_fixed": report["preselected_best_fixed"],
                "models": len(report["models"]),
                "fit_or_tuning_performed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
