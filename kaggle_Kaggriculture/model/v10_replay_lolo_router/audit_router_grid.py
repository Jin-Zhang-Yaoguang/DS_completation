#!/usr/bin/env python3
"""Read-only integrity audit for the formal V10 train/validation Router grid.

The auditor reconstructs the exact task manifest from the frozen collector
configuration, but never creates a Kaggle environment.  It can inspect an
in-progress append-only JSONL with ``--allow-incomplete``; without that flag it
hard-fails unless all 6,400 tasks and 1,600 four-candidate contexts are exact.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from . import collect_router_grid as grid
    from .agent_factory import load_registry, registry_fingerprint
except ImportError:  # direct-file CLI compatibility
    import collect_router_grid as grid
    from agent_factory import load_registry, registry_fingerprint


HERE = Path(__file__).resolve().parent
SCHEMA = "kaggriculture-v10-router-grid-audit-1"


def _digest_result(row: Mapping[str, Any]) -> str:
    keys = (
        "schema", "task_id", "context_id", "collection_fingerprint",
        "registry_sha256", "source", "candidate", "opponent", "router_seat",
        "statuses", "rewards", "done", "candidate_score", "candidate_margin",
        "prefix_complete", "prefix_match", "switch_feature_sha256",
        "switch_features", "error",
    )
    payload = {key: row.get(key) for key in keys}
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_snapshot(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    audit = Counter()
    conflict_ids = []
    bad_json = []
    with path.expanduser().resolve().open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            audit["physical_records"] += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                bad_json.append({"line": line_number, "error": str(exc)})
                continue
            task_id = str(row.get("task_id") or f"<missing:{line_number}>")
            previous = selected.get(task_id)
            success = row.get("error") is None and row.get("done") is True
            previous_success = (
                previous is not None
                and previous.get("error") is None
                and previous.get("done") is True
            )
            if previous is not None:
                audit["duplicate_records"] += 1
            if success and previous_success and _digest_result(row) != _digest_result(previous):
                audit["conflicting_success_records"] += 1
                conflict_ids.append(task_id)
            if previous is None or success or not previous_success:
                selected[task_id] = row
    audit["unique_task_ids"] = len(selected)
    return list(selected.values()), {
        **dict(audit),
        "bad_json": bad_json[:10],
        "conflicting_task_ids": conflict_ids[:10],
    }


def audit_grid(
    jsonl_path: Path,
    registry_path: Path,
    manifest_path: Path,
    summary_path: Path | None,
    seeds_per_split: int,
    splits: Sequence[str],
    dates: Sequence[str],
    random_seed: int,
    candidates: Sequence[str],
    opponents: Sequence[str],
    anchor: str,
    switch_step: int,
) -> dict[str, Any]:
    registry_path = registry_path.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    registry = load_registry(registry_path)
    sources = grid.load_seed_sources(manifest_path)
    panels = {
        grid._normalise_split(split): grid.stratified_panel(
            sources,
            grid._normalise_split(split),
            int(seeds_per_split),
            dates,
            int(random_seed),
        )
        for split in splits
    }
    tasks, expected_fingerprint = grid.build_tasks(
        registry_path,
        candidates,
        opponents,
        panels,
        anchor,
        int(switch_step),
    )
    expected = {str(task["task_id"]): task for task in tasks}
    rows, jsonl_audit = _read_snapshot(jsonl_path)
    observed = {str(row.get("task_id") or ""): row for row in rows}
    expected_ids, observed_ids = set(expected), set(observed)
    relevant = [observed[task_id] for task_id in sorted(expected_ids & observed_ids)]

    failures = Counter()
    examples: dict[str, list[str]] = defaultdict(list)

    def fail(name: str, task_id: str) -> None:
        failures[name] += 1
        if len(examples[name]) < 10:
            examples[name].append(task_id)

    current_registry_hash = registry_fingerprint(registry)
    current_implementation_hash = grid.implementation_fingerprint()
    context_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources_by_split: dict[str, set[tuple[str, str, int]]] = defaultdict(set)
    for row in relevant:
        task_id = str(row.get("task_id"))
        source = row.get("source") or {}
        if row.get("schema") != grid.GRID_SCHEMA:
            fail("schema", task_id)
        if row.get("collection_fingerprint") != expected_fingerprint:
            fail("collection_fingerprint", task_id)
        if row.get("registry_sha256") != current_registry_hash:
            fail("registry_fingerprint", task_id)
        if row.get("collection_implementation_sha256") != current_implementation_hash:
            fail("collector_implementation", task_id)
        if row.get("error") is not None:
            fail("error", task_id)
        if row.get("done") is not True or row.get("statuses") != ["DONE", "DONE"]:
            fail("not_done", task_id)
        if not row.get("prefix_complete") or not row.get("prefix_match"):
            fail("prefix", task_id)
        vector = row.get("switch_features")
        if not isinstance(vector, list) or len(vector) != grid.FEATURE_DIM:
            fail("feature_dim", task_id)
        else:
            array = np.asarray(vector, dtype=np.float32)
            if not np.all(np.isfinite(array)):
                fail("feature_nonfinite", task_id)
            digest = hashlib.sha256(
                array.astype("<f4", copy=False).tobytes()
            ).hexdigest()
            if digest != row.get("switch_feature_sha256"):
                fail("feature_hash", task_id)
        rewards = row.get("rewards")
        if (
            not isinstance(rewards, list)
            or len(rewards) != 2
            or not all(math.isfinite(float(value)) for value in rewards)
        ):
            fail("rewards", task_id)
        planned = expected[task_id]
        for key in (
            "context_id", "candidate", "candidate_root_lineage", "anchor",
            "opponent", "opponent_root_lineage", "router_seat", "switch_step",
        ):
            if row.get(key) != planned.get(key):
                fail(f"task_field.{key}", task_id)
        if source != planned.get("source"):
            fail("task_field.source", task_id)
        split = str(source.get("split") or "")
        sources_by_split[split].add(
            (str(source.get("date") or ""), str(source.get("episode_id") or ""), int(source.get("seed") or 0))
        )
        context_rows[str(row.get("context_id") or "")].append(row)

    complete_contexts = 0
    partial_contexts = 0
    feature_mismatched_contexts = 0
    duplicate_candidate_contexts = 0
    for context_id, values in context_rows.items():
        observed_candidates = [str(row.get("candidate")) for row in values]
        if len(observed_candidates) != len(set(observed_candidates)):
            duplicate_candidate_contexts += 1
        if set(observed_candidates) == set(candidates) and len(values) == len(candidates):
            complete_contexts += 1
            if len({row.get("switch_feature_sha256") for row in values}) != 1:
                feature_mismatched_contexts += 1
        else:
            partial_contexts += 1

    expected_sources_by_split = {
        split: {
            (item.date, item.episode_id, int(item.seed)) for item in values
        }
        for split, values in panels.items()
    }
    panel_audit = {
        split: {
            "expected_sources": len(expected_sources_by_split[split]),
            "observed_sources": len(sources_by_split.get(split, set())),
            "missing_sources": len(expected_sources_by_split[split] - sources_by_split.get(split, set())),
            "foreign_sources": len(sources_by_split.get(split, set()) - expected_sources_by_split[split]),
            "expected_by_date": dict(Counter(item.date for item in panels[split])),
            "observed_by_date": dict(Counter(item[0] for item in sources_by_split.get(split, set()))),
        }
        for split in panels
    }

    summary_audit: dict[str, Any] = {"present": False}
    if summary_path is not None and summary_path.expanduser().resolve().is_file():
        summary = json.loads(summary_path.expanduser().resolve().read_text(encoding="utf-8"))
        summary_audit = {
            "present": True,
            "schema": summary.get("schema"),
            "collection_fingerprint": summary.get("collection_fingerprint"),
            "scheduled_games": summary.get("scheduled_games"),
            "observed_games": summary.get("observed_games"),
            "valid_done_games": summary.get("valid_done_games"),
            "missing_games": summary.get("missing_games"),
            "errors": summary.get("errors"),
            "complete": summary.get("complete"),
            "matches_expected_fingerprint": summary.get("collection_fingerprint") == expected_fingerprint,
        }

    expected_contexts = sum(len(values) for values in panels.values()) * len(opponents) * 2
    strict_complete = (
        not jsonl_audit.get("bad_json")
        and int(jsonl_audit.get("duplicate_records", 0)) == 0
        and int(jsonl_audit.get("conflicting_success_records", 0)) == 0
        and not failures
        and not (observed_ids - expected_ids)
        and observed_ids == expected_ids
        and complete_contexts == expected_contexts
        and partial_contexts == 0
        and feature_mismatched_contexts == 0
        and duplicate_candidate_contexts == 0
        and all(
            value["missing_sources"] == 0 and value["foreign_sources"] == 0
            for value in panel_audit.values()
        )
        and summary_audit.get("present") is True
        and summary_audit.get("complete") is True
        and summary_audit.get("matches_expected_fingerprint") is True
    )
    return {
        "schema": SCHEMA,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "environment_games_started": False,
        "jsonl": str(jsonl_path.expanduser().resolve()),
        "expected": {
            "tasks": len(expected),
            "contexts": expected_contexts,
            "candidates_per_context": len(candidates),
            "collection_fingerprint": expected_fingerprint,
            "registry_and_code_sha256": current_registry_hash,
            "collector_implementation_sha256": current_implementation_hash,
            "splits": list(panels),
            "seeds_per_split": int(seeds_per_split),
            "candidates": list(candidates),
            "opponents": list(opponents),
            "anchor": anchor,
            "switch_step": int(switch_step),
        },
        "observed": {
            "relevant_tasks": len(relevant),
            "missing_tasks": len(expected_ids - observed_ids),
            "foreign_tasks": len(observed_ids - expected_ids),
            "complete_contexts": complete_contexts,
            "partial_contexts": partial_contexts,
            "feature_mismatched_contexts": feature_mismatched_contexts,
            "duplicate_candidate_contexts": duplicate_candidate_contexts,
        },
        "jsonl_audit": jsonl_audit,
        "row_failures": dict(failures),
        "failure_examples": dict(examples),
        "panel_audit": panel_audit,
        "summary_audit": summary_audit,
        "strict_complete": strict_complete,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=HERE / "router_grid_train_val.jsonl")
    parser.add_argument("--summary", type=Path, default=HERE / "router_grid_train_val_summary.json")
    parser.add_argument("--registry", type=Path, default=HERE / "router_training_registry.json")
    parser.add_argument("--manifest", type=Path, default=HERE / "evaluation_seed_manifest.jsonl")
    parser.add_argument("--splits", nargs="+", default=["train", "validation"])
    parser.add_argument("--dates", nargs="+", default=list(grid.DEFAULT_DATES))
    parser.add_argument("--seeds-per-split", type=int, default=100)
    parser.add_argument("--random-seed", type=int, default=20260822)
    parser.add_argument("--candidates", nargs="+", default=list(grid.DEFAULT_MODELS))
    parser.add_argument("--opponents", nargs="+", default=list(grid.DEFAULT_MODELS))
    parser.add_argument("--anchor", default="baseline_v1")
    parser.add_argument("--switch-step", type=int, default=72)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_grid(
        args.jsonl,
        args.registry,
        args.manifest,
        args.summary,
        args.seeds_per_split,
        args.splits,
        args.dates,
        args.random_seed,
        args.candidates,
        args.opponents,
        args.anchor,
        args.switch_step,
    )
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "strict_complete": report["strict_complete"],
                "relevant_tasks": report["observed"]["relevant_tasks"],
                "missing_tasks": report["observed"]["missing_tasks"],
                "foreign_tasks": report["observed"]["foreign_tasks"],
                "row_failures": report["row_failures"],
            },
            ensure_ascii=False,
        )
    )
    if report["strict_complete"] or args.allow_incomplete:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
