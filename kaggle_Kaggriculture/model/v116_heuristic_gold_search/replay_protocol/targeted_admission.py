#!/usr/bin/env python3
"""Strictly admit every replay selected by a provisional split.

The default command is a plan-only dry run: it validates registry/split
references but does not open replay files.  ``--execute`` requires an exact
``--max-files`` bound and hashes only the files named by split assignments.

Replay ``steps`` are never parsed by this module.  During execution approved
metadata is re-read with the streaming whitelist (which stops before the
top-level ``steps`` value), then the whole file is consumed only as opaque
bytes for SHA256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .audit_registry import (
        CUTOFF,
        EXPECTED_CONFIG_SHA256,
        EXPECTED_MODULE,
        atomic_json_dump,
        canonical_sha256,
    )
    from .split_protocol import SOURCES
    from .stream_whitelist import read_replay_whitelist
except ImportError:  # direct-script execution
    from audit_registry import (
        CUTOFF,
        EXPECTED_CONFIG_SHA256,
        EXPECTED_MODULE,
        atomic_json_dump,
        canonical_sha256,
    )
    from split_protocol import SOURCES
    from stream_whitelist import read_replay_whitelist


SCHEMA = "v116-targeted-replay-admission-v1"
SHA_RE = re.compile(r"[0-9a-f]{64}")
SPLITS = ("dev", "frozen")


class AdmissionError(ValueError):
    """The provisional panel cannot be finalized without re-registration."""


def _valid_lower_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _record_key(row: dict[str, Any]) -> tuple[str, int]:
    try:
        source = str(row["source_class"])
        episode_id = int(row["episode_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AdmissionError("record/assignment has no valid source_class + episode_id") from exc
    return source, episode_id


def _index_selected(
    registry: dict[str, Any], split_manifest: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    assignments = split_manifest.get("assignments")
    records = registry.get("records")
    if not isinstance(assignments, list) or not assignments:
        raise AdmissionError("provisional split has no assignments")
    if not isinstance(records, list):
        raise AdmissionError("registry records must be a list")

    records_by_id: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        record_id = record.get("record_id")
        if isinstance(record_id, str):
            records_by_id[record_id].append(record)

    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen_record_ids: set[str] = set()
    seen_assignment_keys: set[tuple[str, int]] = set()
    actual_counts: Counter[str] = Counter()
    for assignment in assignments:
        if not isinstance(assignment, dict):
            raise AdmissionError("every split assignment must be an object")
        source, episode_id = _record_key(assignment)
        if source not in SOURCES:
            raise AdmissionError(f"unsupported assignment source: {source}")
        split = assignment.get("split")
        if split not in SPLITS:
            raise AdmissionError(f"assignment {(source, episode_id)} has invalid split {split!r}")
        record_id = assignment.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise AdmissionError(f"assignment {(source, episode_id)} has no record_id")
        if record_id in seen_record_ids:
            raise AdmissionError(f"duplicate assignment record_id: {record_id}")
        seen_record_ids.add(record_id)
        assignment_key = (source, episode_id)
        if assignment_key in seen_assignment_keys:
            raise AdmissionError(f"duplicate assignment source/episode: {assignment_key}")
        seen_assignment_keys.add(assignment_key)

        matches = records_by_id.get(record_id, [])
        if len(matches) != 1:
            raise AdmissionError(
                f"assignment {record_id!r} resolves to {len(matches)} registry records"
            )
        record = matches[0]
        if _record_key(record) != assignment_key:
            raise AdmissionError(f"assignment identity differs from registry record {record_id}")
        if not record.get("metadata_ready"):
            raise AdmissionError(f"assignment {record_id} is not metadata-ready")
        if record.get("failures"):
            raise AdmissionError(f"assignment {record_id} has registry failures")
        if not record.get("metadata_stopped_before_steps"):
            raise AdmissionError(f"assignment {record_id} lacks the steps-boundary proof")
        if record.get("module_version") != EXPECTED_MODULE:
            raise AdmissionError(f"assignment {record_id} has the wrong module version")
        if record.get("configuration_sha256") != EXPECTED_CONFIG_SHA256:
            raise AdmissionError(f"assignment {record_id} has the wrong configuration hash")
        configuration = record.get("configuration")
        if canonical_sha256(configuration) != EXPECTED_CONFIG_SHA256:
            raise AdmissionError(f"assignment {record_id} configuration payload changed")
        if str(record.get("partition_date") or "") < CUTOFF:
            raise AdmissionError(f"assignment {record_id} predates {CUTOFF}")
        seed = record.get("actual_seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise AdmissionError(f"assignment {record_id} has no integer actual_seed")
        if int(assignment.get("actual_seed", seed)) != seed:
            raise AdmissionError(f"assignment {record_id} seed differs from registry")
        replay_path = record.get("replay_path")
        if not isinstance(replay_path, str) or not replay_path:
            raise AdmissionError(f"assignment {record_id} has no replay path")

        actual_counts[f"{source}:{split}"] += 1
        selected.append((assignment, record))

    declared_counts = split_manifest.get("counts")
    if declared_counts is not None:
        if not isinstance(declared_counts, dict):
            raise AdmissionError("split counts must be an object")
        expected_keys = {f"{source}:{split}" for source in SOURCES for split in SPLITS}
        for key in expected_keys:
            try:
                declared = int(declared_counts.get(key, 0))
            except (TypeError, ValueError) as exc:
                raise AdmissionError(f"invalid declared count for {key}") from exc
            if declared != actual_counts[key]:
                raise AdmissionError(
                    f"split count mismatch for {key}: declared {declared}, actual {actual_counts[key]}"
                )
        unexpected_positive = [
            key for key, value in declared_counts.items() if key not in expected_keys and int(value) != 0
        ]
        if unexpected_positive:
            raise AdmissionError(f"unexpected positive split counts: {unexpected_positive}")

    registry_expected_module = registry.get("expected_module_version", EXPECTED_MODULE)
    registry_expected_config = registry.get(
        "expected_configuration_sha256", EXPECTED_CONFIG_SHA256
    )
    if registry_expected_module != EXPECTED_MODULE:
        raise AdmissionError("registry expected module version differs from the frozen contract")
    if registry_expected_config != EXPECTED_CONFIG_SHA256:
        raise AdmissionError("registry expected configuration differs from the frozen contract")
    return selected


def _seed_preflight(selected: list[tuple[dict[str, Any], dict[str, Any]]]) -> None:
    by_seed: defaultdict[int, list[str]] = defaultdict(list)
    for _, record in selected:
        by_seed[int(record["actual_seed"])].append(str(record["record_id"]))
    conflicts = {seed: ids for seed, ids in by_seed.items() if len(ids) > 1}
    if conflicts:
        rendered = "; ".join(f"{seed}:{sorted(ids)}" for seed, ids in sorted(conflicts.items()))
        raise AdmissionError(f"global seed collision: {rendered}")


def plan_admission(registry: dict[str, Any], split_manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate references without opening or hashing any Replay file."""
    selected = _index_selected(registry, split_manifest)
    _seed_preflight(selected)
    counts = Counter(
        (assignment["source_class"], assignment["split"]) for assignment, _ in selected
    )
    missing_paths = [
        str(record["record_id"])
        for _, record in selected
        if not Path(record["replay_path"]).is_file()
    ]
    return {
        "schema": SCHEMA,
        "status": "PLAN_ONLY_NOT_FINALIZED",
        "files_opened": 0,
        "files_hashed": 0,
        "steps_parsed": False,
        "assignment_count": len(selected),
        "required_max_files": len(selected),
        "missing_path_count": len(missing_paths),
        "missing_record_ids": missing_paths,
        "counts": {
            f"{source}:{split}": counts[(source, split)]
            for source in SOURCES
            for split in SPLITS
        },
    }


def _recheck_and_hash(record: dict[str, Any]) -> str:
    record_id = str(record["record_id"])
    path = Path(record["replay_path"])
    if not path.is_file():
        raise AdmissionError(f"assignment {record_id} replay file is missing")
    before = path.stat()

    # The whitelist returns as soon as it sees the top-level steps key.  It
    # never enters that value in this admission pass.
    metadata = read_replay_whitelist(path, include_steps=False)
    if not metadata.stopped_before_steps:
        raise AdmissionError(f"assignment {record_id} did not stop before steps")
    if metadata.episode_id != int(record["episode_id"]):
        raise AdmissionError(f"assignment {record_id} episode id changed")
    if metadata.seed != int(record["actual_seed"]):
        raise AdmissionError(f"assignment {record_id} seed changed")
    if metadata.module_version != EXPECTED_MODULE:
        raise AdmissionError(f"assignment {record_id} module version changed")
    if canonical_sha256(metadata.configuration) != EXPECTED_CONFIG_SHA256:
        raise AdmissionError(f"assignment {record_id} configuration changed")

    actual_sha = _sha256_file(path)
    after = path.stat()
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise AdmissionError(f"assignment {record_id} changed while it was being admitted")
    claimed_sha = record.get("manifest_sha256_claim")
    if claimed_sha is not None:
        if not _valid_lower_sha(claimed_sha):
            raise AdmissionError(f"assignment {record_id} has an invalid manifest SHA claim")
        if claimed_sha != actual_sha:
            raise AdmissionError(f"assignment {record_id} manifest SHA claim mismatch")
    return actual_sha


def _check_episode_sha_pairs(
    selected: list[tuple[dict[str, Any], dict[str, Any]]], sha_by_record_id: dict[str, str]
) -> None:
    by_episode: defaultdict[int, list[tuple[str, str]]] = defaultdict(list)
    pair_counts: Counter[tuple[int, str]] = Counter()
    for _, record in selected:
        record_id = str(record["record_id"])
        episode_id = int(record["episode_id"])
        sha = sha_by_record_id[record_id]
        by_episode[episode_id].append((record_id, sha))
        pair_counts[(episode_id, sha)] += 1

    duplicate_pairs = [pair for pair, count in pair_counts.items() if count > 1]
    if duplicate_pairs:
        raise AdmissionError(
            "duplicate episode_id + replay_sha256 pair would double-count the panel; "
            "re-preregister after exact deduplication: " + repr(sorted(duplicate_pairs))
        )
    for episode_id, rows in sorted(by_episode.items()):
        hashes = {sha for _, sha in rows}
        if len(hashes) > 1:
            raise AdmissionError(
                f"same episode id has different replay SHA256 values: {episode_id}, {rows}"
            )


def _refresh_registry_summary(registry: dict[str, Any]) -> None:
    records = registry.get("records", [])
    summary = dict(registry.get("summary") or {})
    summary["strict_ready_by_source"] = dict(
        Counter(row["source_class"] for row in records if row.get("strict_ready"))
    )
    summary["sha_pending_or_claim_by_source"] = dict(
        Counter(row["source_class"] for row in records if row.get("sha_state") != "recomputed")
    )
    registry["summary"] = summary


def _validate_finalized(
    registry: dict[str, Any], split_manifest: dict[str, Any], assignment_count: int
) -> None:
    selected = _index_selected(registry, split_manifest)
    if len(selected) != assignment_count:
        raise AdmissionError("finalized assignment count changed")
    _seed_preflight(selected)
    seen_pairs: set[tuple[int, str]] = set()
    by_episode: dict[int, str] = {}
    for assignment, record in selected:
        sha = record.get("replay_sha256")
        if not _valid_lower_sha(sha):
            raise AdmissionError(f"finalized record {record['record_id']} has no valid SHA256")
        if record.get("sha_state") != "recomputed" or record.get("strict_ready") is not True:
            raise AdmissionError(f"finalized record {record['record_id']} is not strict-ready")
        if assignment.get("replay_sha256") != sha:
            raise AdmissionError(f"finalized split SHA differs for {record['record_id']}")
        if assignment.get("sha_state") != "recomputed" or assignment.get("strict_ready") is not True:
            raise AdmissionError(f"finalized split assignment {record['record_id']} is not strict-ready")
        episode_id = int(record["episode_id"])
        pair = (episode_id, sha)
        if pair in seen_pairs:
            raise AdmissionError(f"finalized split contains duplicate episode/SHA pair: {pair}")
        seen_pairs.add(pair)
        previous = by_episode.setdefault(episode_id, sha)
        if previous != sha:
            raise AdmissionError(f"finalized split has an episode/SHA conflict: {episode_id}")


def finalize_admission(
    registry: dict[str, Any], split_manifest: dict[str, Any], *, max_files: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Hash and admit exactly the assignments in the provisional split."""
    selected = _index_selected(registry, split_manifest)
    _seed_preflight(selected)
    required = len(selected)
    if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files <= 0:
        raise AdmissionError("--max-files must be a positive integer")
    if max_files != required:
        raise AdmissionError(
            f"--max-files must equal the full assignment count: got {max_files}, required {required}"
        )

    sha_by_record_id: dict[str, str] = {}
    for _, record in selected:
        sha_by_record_id[str(record["record_id"])] = _recheck_and_hash(record)
    if len(sha_by_record_id) != required:
        raise AdmissionError("not every assignment received a recomputed SHA256")
    _check_episode_sha_pairs(selected, sha_by_record_id)

    admitted_at = datetime.now(timezone.utc).isoformat()
    admitted_registry = _copy_json(registry)
    admitted_split = _copy_json(split_manifest)
    selected_ids = set(sha_by_record_id)
    for record in admitted_registry["records"]:
        record_id = record.get("record_id")
        if record_id not in selected_ids:
            continue
        record["replay_sha256"] = sha_by_record_id[record_id]
        record["sha_state"] = "recomputed"
        record["strict_ready"] = True
        record["targeted_admitted_at"] = admitted_at
    for assignment in admitted_split["assignments"]:
        record_id = assignment["record_id"]
        assignment["replay_sha256"] = sha_by_record_id[record_id]
        assignment["sha_state"] = "recomputed"
        assignment["strict_ready"] = True
        assignment["targeted_admitted_at"] = admitted_at

    admission = {
        "schema": SCHEMA,
        "status": "FINALIZED_ALL_ASSIGNMENTS_STRICT_READY",
        "admitted_at": admitted_at,
        "assignment_count": required,
        "files_hashed": required,
        "max_files": max_files,
        "all_assignments_strict_ready": True,
        "dedup_key": "episode_id + replay_sha256",
        "steps_parsed": False,
        "metadata_reader": "stream whitelist stopped before top-level steps value",
        "hash_reader": "opaque raw bytes only",
        "input_registry_canonical_sha256": canonical_sha256(registry),
        "input_split_canonical_sha256": canonical_sha256(split_manifest),
    }
    admitted_registry["targeted_admission"] = admission
    admitted_split["targeted_admission"] = admission
    _refresh_registry_summary(admitted_registry)
    _validate_finalized(admitted_registry, admitted_split, required)
    return admitted_registry, admitted_split, admission


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually hash assignments. Omit for a no-open, no-hash plan.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Exact assignment count; mandatory with --execute and never an unbounded switch.",
    )
    parser.add_argument("--admitted-registry-output", type=Path)
    parser.add_argument("--admitted-split-output", type=Path)
    return parser.parse_args()


def _validate_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.admitted_registry_output is None or args.admitted_split_output is None:
        raise AdmissionError("--execute requires both admitted output paths")
    registry_input = args.registry.resolve()
    split_input = args.split_manifest.resolve()
    registry_output = args.admitted_registry_output.resolve()
    split_output = args.admitted_split_output.resolve()
    if registry_output == split_output:
        raise AdmissionError("admitted registry and split outputs must be different files")
    if registry_output in (registry_input, split_input) or split_output in (registry_input, split_input):
        raise AdmissionError("admission outputs must not overwrite provisional inputs")
    return registry_output, split_output


def main() -> int:
    args = parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    split_manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    if not args.execute:
        if args.admitted_registry_output or args.admitted_split_output:
            raise AdmissionError("plan-only mode does not write admitted outputs")
        plan = plan_admission(registry, split_manifest)
        if args.max_files is not None:
            plan["provided_max_files"] = args.max_files
            plan["max_files_exact"] = args.max_files == plan["required_max_files"]
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
        return 0

    if args.max_files is None:
        raise AdmissionError("--execute requires explicit --max-files")
    registry_output, split_output = _validate_output_paths(args)
    admitted_registry, admitted_split, admission = finalize_admission(
        registry, split_manifest, max_files=args.max_files
    )
    # Both complete documents are constructed and validated before either path
    # is touched.  Each replacement is atomic; provisional inputs are immutable.
    atomic_json_dump(admitted_registry, registry_output)
    atomic_json_dump(admitted_split, split_output)
    print(json.dumps(admission, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
