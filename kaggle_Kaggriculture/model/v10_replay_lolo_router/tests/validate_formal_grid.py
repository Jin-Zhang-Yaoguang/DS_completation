#!/usr/bin/env python3
"""Independent integrity audit for a V10 formal Router outcome grid.

This validator deliberately does not call ``collect_router_grid.build_tasks``
or ``summarise_grid``.  It reconstructs the deterministic seed panels, task
IDs and collection fingerprint independently, then checks every stored game.
It is safe to run with ``--allow-incomplete`` while collection is in progress.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parents[1]
GRID_SCHEMA = "kaggriculture-v10-router-outcome-grid-1"
GRID_SUMMARY_SCHEMA = "kaggriculture-v10-router-grid-summary-1"
FEATURE_SCHEMA = "kaggriculture-v10-public-step72-1"
FEATURE_DIM = 61
DEFAULT_MODELS = ("baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8")
DEFAULT_DATES = ("2026-08-18", "2026-08-19", "2026-08-20")


class AuditFailure(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_int(text: str, modulo: int = 2**31 - 1) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big") % modulo


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditFailure(f"invalid JSONL at line {number}: {exc}") from exc
            if not isinstance(value, dict):
                raise AuditFailure(f"line {number} is not a JSON object")
            rows.append(value)
    return rows


def normalise_split(value: Any) -> str:
    text = str(value or "").strip().lower()
    return "validation" if text in {"val", "valid", "validation"} else text


def load_sources(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        raw = load_jsonl(path)
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            raw = payload
        elif isinstance(payload, Mapping) and isinstance(payload.get("splits"), Mapping):
            raw = []
            for split, block in payload["splits"].items():
                raw.extend({"split": split, **row} for row in block.get("records", []))
        elif isinstance(payload, Mapping):
            raw = list(payload.get("records", []))
        else:
            raw = []
    unique: dict[tuple[str, int], dict[str, Any]] = {}
    for row in raw:
        date = str(row.get("date") or row.get("source_date") or "")[:10]
        split = normalise_split(row.get("split"))
        if not date or row.get("seed") is None or row.get("episode_id") is None or not split:
            continue
        source = {
            "date": date,
            "seed": int(row["seed"]),
            "episode_id": str(row["episode_id"]),
            "split": split,
            "source_relpath": str(row.get("source_relpath") or row.get("source_path") or ""),
        }
        unique.setdefault((date, source["seed"]), source)
    return sorted(unique.values(), key=lambda row: (row["split"], row["date"], row["seed"]))


def panel(
    sources: Sequence[dict[str, Any]],
    split: str,
    count: int,
    dates: Sequence[str],
    random_seed: int,
) -> list[dict[str, Any]]:
    split = normalise_split(split)
    quotas = {date: count // len(dates) for date in dates}
    for date in dates[: count % len(dates)]:
        quotas[date] += 1
    selected: list[dict[str, Any]] = []
    for date in dates:
        values = [row for row in sources if row["split"] == split and row["date"] == date]
        rng = random.Random(int(random_seed) + stable_int(f"{split}|{date}"))
        rng.shuffle(values)
        if len(values) < quotas[date]:
            raise AuditFailure(
                f"not enough manifest seeds for {split}/{date}: "
                f"need {quotas[date]}, have {len(values)}"
            )
        selected.extend(values[: quotas[date]])
    random.Random(int(random_seed) + stable_int(split)).shuffle(selected)
    return selected


def load_registry(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    source = raw.get("models", raw.get("agents", {})) if isinstance(raw, dict) else raw
    if isinstance(source, list):
        models = {str(row["id"]): dict(row) for row in source}
    elif isinstance(source, Mapping):
        models = {str(key): {"id": str(key), **dict(value)} for key, value in source.items()}
    else:
        raise AuditFailure("invalid registry")
    return raw if isinstance(raw, dict) else {"models": raw}, models


def resolve(registry_path: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (registry_path.parent / path).resolve()


def registry_fingerprint(path: Path, raw: Mapping[str, Any], models: Mapping[str, Mapping[str, Any]]) -> str:
    digest = hashlib.sha256(canonical(raw).encode("utf-8"))
    paths: set[Path] = set()
    for spec in models.values():
        module = spec.get("path") or spec.get("module_path")
        if module:
            paths.add(resolve(path, module))
        source = spec.get("source")
        if source:
            candidates = [
                (path.parent / str(source)).resolve(),
                (path.parent.parent / str(source)).resolve(),
            ]
            for candidate in candidates:
                if candidate.is_file():
                    paths.add(candidate)
                    break
        for value in spec.get("code_paths") or []:
            paths.add(resolve(path, value))
        if spec.get("weights"):
            paths.add(resolve(path, spec["weights"]))
    for dependency in sorted(paths):
        digest.update(str(dependency).encode("utf-8"))
        if not dependency.is_file():
            digest.update(b"<missing>")
        else:
            with dependency.open("rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
    return digest.hexdigest()


def implementation_fingerprint() -> tuple[str, dict[str, str]]:
    import kaggle_environments

    files = (HERE / "collect_router_grid.py", HERE / "agent_factory.py", HERE / "router.py")
    runtime = {
        "python": list(sys.version_info[:2]),
        "kaggle_environments": getattr(kaggle_environments, "__version__", "unknown"),
        "numpy": np.__version__,
    }
    digest = hashlib.sha256(canonical(runtime).encode("utf-8"))
    file_hashes: dict[str, str] = {}
    for path in files:
        file_hashes[path.name] = file_sha256(path)
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest(), file_hashes


def root_lineage(spec: Mapping[str, Any], fallback: str) -> str:
    if spec.get("root_lineage"):
        return str(spec["root_lineage"])
    lineage = spec.get("lineage")
    if isinstance(lineage, (list, tuple)) and lineage:
        return str(lineage[0])
    return str(lineage or fallback)


def expected_tasks(args: argparse.Namespace) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    registry_path = args.registry.expanduser().resolve()
    manifest_path = args.seed_manifest.expanduser().resolve()
    raw_registry, models = load_registry(registry_path)
    requested = [*args.candidates, *args.opponents, args.anchor]
    missing = [model for model in requested if model not in models]
    if missing:
        raise AuditFailure(f"registry missing models: {missing}")
    registry_hash = registry_fingerprint(registry_path, raw_registry, models)
    implementation_hash, collector_file_hashes = implementation_fingerprint()
    sources = load_sources(manifest_path)
    panels = {
        split: panel(sources, split, args.seeds_per_split, args.dates, args.random_seed)
        for split in args.splits
    }
    config = {
        "schema": GRID_SCHEMA,
        "collection_implementation_sha256": implementation_hash,
        "registry_sha256": registry_hash,
        "candidates": list(args.candidates),
        "opponents": list(args.opponents),
        "anchor": args.anchor,
        "switch_step": args.switch_step,
        "collector_implementation_sha256": collector_file_hashes,
        "panels": {split: values for split, values in sorted(panels.items())},
    }
    collection_hash = hashlib.sha256(canonical(config).encode("utf-8")).hexdigest()
    tasks: dict[str, dict[str, Any]] = {}
    for split, values in sorted(panels.items()):
        for source in values:
            for opponent in args.opponents:
                opponent_root = root_lineage(models[opponent], opponent)
                for seat in (0, 1):
                    context_payload = {
                        "collection": collection_hash,
                        "date": source["date"],
                        "split": source["split"],
                        "seed": source["seed"],
                        "episode_id": source["episode_id"],
                        "router_seat": seat,
                        "opponent_root_lineage": opponent_root,
                    }
                    context_id = "context-" + hashlib.sha256(
                        canonical(context_payload).encode("utf-8")
                    ).hexdigest()[:24]
                    for candidate in args.candidates:
                        key = f"{context_id}|candidate:{candidate}|opponent:{opponent}"
                        task_id = "grid-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
                        tasks[task_id] = {
                            "task_id": task_id,
                            "context_id": context_id,
                            "source": source,
                            "candidate": candidate,
                            "candidate_root_lineage": root_lineage(models[candidate], candidate),
                            "opponent": opponent,
                            "opponent_root_lineage": opponent_root,
                            "router_seat": seat,
                        }
    metadata = {
        "registry_sha256": registry_hash,
        "collection_implementation_sha256": implementation_hash,
        "collector_file_sha256": collector_file_hashes,
        "collection_fingerprint": collection_hash,
        "panels": panels,
        "models": models,
    }
    return tasks, metadata


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    expected, metadata = expected_tasks(args)
    rows = load_jsonl(args.grid.expanduser().resolve())
    errors: list[str] = []
    by_task: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for row in rows:
        task_id = str(row.get("task_id") or "")
        if task_id in by_task:
            duplicate_ids.append(task_id)
        by_task[task_id] = row
    require(not duplicate_ids, f"duplicate task IDs: {len(duplicate_ids)}", errors)
    observed_ids = set(by_task)
    expected_ids = set(expected)
    foreign = sorted(observed_ids - expected_ids)
    missing = sorted(expected_ids - observed_ids)
    require(not foreign, f"foreign tasks: {len(foreign)}", errors)
    if not args.allow_incomplete:
        require(not missing, f"missing tasks: {len(missing)}", errors)

    context_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    macro_rows: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    split_counts: Counter[str] = Counter()
    date_counts: Counter[tuple[str, str]] = Counter()
    seen_sources: set[tuple[str, int, str]] = set()
    row_errors: list[str] = []
    for task_id in sorted(observed_ids & expected_ids):
        row = by_task[task_id]
        task = expected[task_id]
        label = task_id
        require(row.get("schema") == GRID_SCHEMA, f"{label}: schema", row_errors)
        require(row.get("collection_fingerprint") == metadata["collection_fingerprint"], f"{label}: collection fingerprint", row_errors)
        require(row.get("collection_implementation_sha256") == metadata["collection_implementation_sha256"], f"{label}: implementation fingerprint", row_errors)
        require(row.get("registry_sha256") == metadata["registry_sha256"], f"{label}: registry fingerprint", row_errors)
        for field in (
            "context_id", "source", "candidate", "candidate_root_lineage",
            "opponent", "opponent_root_lineage", "router_seat",
        ):
            require(row.get(field) == task[field], f"{label}: {field}", row_errors)
        require(row.get("anchor") == args.anchor, f"{label}: anchor", row_errors)
        require(row.get("switch_step") == args.switch_step, f"{label}: switch step", row_errors)
        require(row.get("closed_loop") is True, f"{label}: not closed loop", row_errors)
        require(row.get("trace_agent") is False, f"{label}: TraceAgent used", row_errors)
        require(row.get("error") is None, f"{label}: error={row.get('error')}", row_errors)
        require(row.get("done") is True, f"{label}: not done", row_errors)
        require(row.get("statuses") == ["DONE", "DONE"], f"{label}: statuses", row_errors)
        require(row.get("prefix_complete") is True, f"{label}: incomplete prefix", row_errors)
        require(row.get("prefix_match") is True, f"{label}: prefix mismatch", row_errors)
        require(row.get("first_prefix_mismatch") is None, f"{label}: mismatch marker", row_errors)
        require(row.get("anchor_prefix_sha256") == row.get("candidate_prefix_sha256"), f"{label}: prefix hashes", row_errors)
        vector = np.asarray(row.get("switch_features"), dtype=np.float32)
        require(vector.shape == (FEATURE_DIM,), f"{label}: feature shape {vector.shape}", row_errors)
        if vector.shape == (FEATURE_DIM,):
            require(bool(np.all(np.isfinite(vector))), f"{label}: non-finite feature", row_errors)
            actual_hash = hashlib.sha256(vector.astype("<f4", copy=False).tobytes()).hexdigest()
            require(row.get("switch_feature_sha256") == actual_hash, f"{label}: feature hash", row_errors)
        require(row.get("switch_feature_schema") == FEATURE_SCHEMA, f"{label}: feature schema", row_errors)
        require(row.get("switch_feature_dim") == FEATURE_DIM, f"{label}: feature dim", row_errors)
        rewards = row.get("rewards") or []
        seat = int(task["router_seat"])
        if len(rewards) == 2 and all(isinstance(value, (int, float)) and math.isfinite(value) for value in rewards):
            own = float(rewards[seat])
            other = float(rewards[1 - seat])
            margin = own - other
            score = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
            require(float(row.get("candidate_reward")) == own, f"{label}: candidate reward", row_errors)
            require(float(row.get("opponent_reward")) == other, f"{label}: opponent reward", row_errors)
            require(float(row.get("candidate_margin")) == margin, f"{label}: margin", row_errors)
            require(float(row.get("candidate_score")) == score, f"{label}: score", row_errors)
        else:
            row_errors.append(f"{label}: invalid rewards")
        elapsed = row.get("elapsed_seconds")
        require(isinstance(elapsed, (int, float)) and math.isfinite(elapsed) and elapsed >= 0, f"{label}: elapsed", row_errors)
        context_rows[str(row.get("context_id"))].append(row)
        source = task["source"]
        macro_rows[(source["split"], source["seed"], seat)].append(row)
        seen_sources.add((source["split"], source["seed"], source["episode_id"]))

    errors.extend(row_errors[:100])
    if len(row_errors) > 100:
        errors.append(f"additional row failures suppressed: {len(row_errors) - 100}")

    for context_id, values in context_rows.items():
        candidates = [str(row.get("candidate")) for row in values]
        require(len(candidates) == len(set(candidates)), f"{context_id}: duplicate candidates", errors)
        require(set(candidates) <= set(args.candidates), f"{context_id}: foreign candidate", errors)
        if not args.allow_incomplete:
            require(len(values) == len(args.candidates), f"{context_id}: {len(values)} rows", errors)
            require(set(candidates) == set(args.candidates), f"{context_id}: candidate grid", errors)
        feature_hashes = {row.get("switch_feature_sha256") for row in values}
        require(len(feature_hashes) == 1 and None not in feature_hashes, f"{context_id}: feature mismatch", errors)
        anchor_hashes = {row.get("anchor_prefix_sha256") for row in values}
        require(len(anchor_hashes) == 1 and None not in anchor_hashes, f"{context_id}: anchor prefix mismatch", errors)

    for macro_id, values in macro_rows.items():
        pairs = {(str(row.get("candidate")), str(row.get("opponent"))) for row in values}
        expected_pairs = {(candidate, opponent) for candidate in args.candidates for opponent in args.opponents}
        require(len(values) == len(pairs), f"macro context {macro_id}: duplicate pairs", errors)
        require(pairs <= expected_pairs, f"macro context {macro_id}: foreign pair", errors)
        if not args.allow_incomplete:
            require(len(values) == len(expected_pairs), f"macro context {macro_id}: {len(values)} rows", errors)
            require(pairs == expected_pairs, f"macro context {macro_id}: incomplete 4x4 grid", errors)

    # Source coverage counts each seed only once, independent of game rows.
    for split, seed, episode_id in seen_sources:
        split_counts[split] += 1
        source = next(
            source for source in metadata["panels"][split]
            if source["seed"] == seed and source["episode_id"] == episode_id
        )
        date_counts[(split, source["date"])] += 1
    expected_seen = sum(len(values) for values in metadata["panels"].values())
    if not args.allow_incomplete:
        require(len(seen_sources) == expected_seen, f"source seeds: {len(seen_sources)} != {expected_seen}", errors)
        for split, values in metadata["panels"].items():
            require(split_counts[split] == len(values), f"{split}: source coverage", errors)
            expected_dates = Counter(source["date"] for source in values)
            for date, count in expected_dates.items():
                require(date_counts[(split, date)] == count, f"{split}/{date}: source coverage", errors)

    expected_macro = sum(len(values) for values in metadata["panels"].values()) * 2
    expected_contexts = expected_macro * len(args.opponents)
    if not args.allow_incomplete:
        require(len(macro_rows) == expected_macro, f"macro contexts: {len(macro_rows)} != {expected_macro}", errors)
        require(len(context_rows) == expected_contexts, f"context IDs: {len(context_rows)} != {expected_contexts}", errors)

    summary_payload = None
    if args.summary and args.summary.is_file():
        summary_payload = json.loads(args.summary.read_text(encoding="utf-8"))
        require(summary_payload.get("schema") == GRID_SUMMARY_SCHEMA, "summary schema", errors)
        require(summary_payload.get("collection_fingerprint") == metadata["collection_fingerprint"], "summary collection fingerprint", errors)
        provenance = summary_payload.get("provenance") or {}
        require(provenance.get("registry_sha256") == metadata["registry_sha256"], "summary registry fingerprint", errors)
        require(provenance.get("collection_implementation_sha256") == metadata["collection_implementation_sha256"], "summary implementation fingerprint", errors)
        if not args.allow_incomplete:
            require(summary_payload.get("scheduled_games") == len(expected), "summary scheduled games", errors)
            require(summary_payload.get("observed_games") == len(expected), "summary observed games", errors)
            require(summary_payload.get("valid_done_games") == len(expected), "summary valid games", errors)
            require(summary_payload.get("missing_games") == 0, "summary missing games", errors)
            require(summary_payload.get("errors") == 0, "summary errors", errors)
            require(summary_payload.get("not_done") == 0, "summary not_done", errors)
            require(summary_payload.get("contexts") == expected_contexts, "summary contexts", errors)
            require(summary_payload.get("complete") is True, "summary not complete", errors)
            audit_block = summary_payload.get("context_audit") or {}
            require(audit_block.get("complete_candidate_grid") == expected_contexts, "summary candidate grids", errors)
            require(audit_block.get("feature_matched") == expected_contexts, "summary feature matches", errors)
            require(audit_block.get("all_prefix_compatible") == expected_contexts, "summary prefix compatibility", errors)
    elif not args.allow_incomplete:
        errors.append("formal summary file is missing")

    report = {
        "passed": not errors,
        "allow_incomplete": bool(args.allow_incomplete),
        "raw_rows": len(rows),
        "unique_tasks": len(by_task),
        "expected_tasks": len(expected),
        "missing_tasks": len(missing),
        "foreign_tasks": len(foreign),
        "duplicate_tasks": len(duplicate_ids),
        "valid_rows_checked": len(observed_ids & expected_ids),
        "source_seeds_seen": len(seen_sources),
        "macro_contexts_seen": len(macro_rows),
        "candidate_contexts_seen": len(context_rows),
        "expected_macro_contexts": expected_macro,
        "expected_candidate_contexts": expected_contexts,
        "split_seed_counts": dict(split_counts),
        "split_date_seed_counts": {f"{key[0]}|{key[1]}": value for key, value in sorted(date_counts.items())},
        "registry_sha256": metadata["registry_sha256"],
        "collection_implementation_sha256": metadata["collection_implementation_sha256"],
        "collection_fingerprint": metadata["collection_fingerprint"],
        "summary_present": summary_payload is not None,
        "errors": errors,
    }
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--registry", type=Path, default=HERE / "router_training_registry.json")
    parser.add_argument("--seed-manifest", type=Path, default=HERE / "evaluation_seed_manifest.jsonl")
    parser.add_argument("--splits", nargs="+", default=["train", "validation"])
    parser.add_argument("--dates", nargs="+", default=list(DEFAULT_DATES))
    parser.add_argument("--seeds-per-split", type=int, default=100)
    parser.add_argument("--candidates", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--opponents", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--anchor", default="baseline_v1")
    parser.add_argument("--switch-step", type=int, default=72)
    parser.add_argument("--random-seed", type=int, default=20260822)
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    report = audit(parse_args(argv))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
