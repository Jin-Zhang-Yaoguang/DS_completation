#!/usr/bin/env python3
"""Pre-register source-separated dev/frozen Replay scenario panels."""

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
    from .audit_registry import atomic_json_dump
except ImportError:  # direct-script execution
    from audit_registry import atomic_json_dump


SCHEMA = "v116-replay-split-manifest-v1"
SOURCES = ("A_ACCOUNT_ONLINE", "B_OFFICIAL_DAILY")


def _rank(salt: str, source: str, partition_date: str, episode_id: int) -> str:
    return hashlib.sha256(
        f"{salt}\0{source}\0{partition_date}\0{episode_id}".encode("utf-8")
    ).hexdigest()


def _collision_audit(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exclusions: list[dict[str, Any]] = []
    by_episode: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    by_seed: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_episode[int(record["episode_id"])].append(record)
        by_seed[int(record["actual_seed"])].append(record)

    blocked_ids: set[str] = set()
    for episode_id, rows in by_episode.items():
        if len(rows) > 1:
            for row in rows:
                blocked_ids.add(row["record_id"])
            exclusions.append(
                {
                    "kind": "episode_collision",
                    "episode_id": episode_id,
                    "record_ids": sorted(row["record_id"] for row in rows),
                }
            )
    for seed, rows in by_seed.items():
        if len(rows) > 1:
            for row in rows:
                blocked_ids.add(row["record_id"])
            exclusions.append(
                {
                    "kind": "seed_collision",
                    "actual_seed": seed,
                    "record_ids": sorted(row["record_id"] for row in rows),
                }
            )
    return [row for row in records if row["record_id"] not in blocked_ids], exclusions


def preregister(
    registry: dict[str, Any], *, salt: str, dev_per_source: int = 64, frozen_per_source: int = 128
) -> dict[str, Any]:
    if dev_per_source <= 0 or frozen_per_source <= 0:
        raise ValueError("panel targets must be positive")
    candidates = [
        row
        for row in registry.get("records", [])
        if row.get("metadata_ready")
        and row.get("source_class") in SOURCES
        and row.get("actual_seed") is not None
    ]
    candidates, exclusions = _collision_audit(candidates)
    assignments: list[dict[str, Any]] = []
    for source in SOURCES:
        source_rows = [row for row in candidates if row["source_class"] == source]
        source_rows.sort(
            key=lambda row: (
                _rank(salt, source, str(row["partition_date"]), int(row["episode_id"])),
                str(row["partition_date"]),
                int(row["episode_id"]),
            )
        )
        needed = dev_per_source + frozen_per_source
        if len(source_rows) < needed:
            raise ValueError(f"{source} has {len(source_rows)} collision-free records; {needed} required")
        for index, row in enumerate(source_rows[:needed]):
            split = "dev" if index < dev_per_source else "frozen"
            assignments.append(
                {
                    "record_id": row["record_id"],
                    "source_class": source,
                    "episode_id": int(row["episode_id"]),
                    "partition_date": row["partition_date"],
                    "actual_seed": int(row["actual_seed"]),
                    "replay_sha256": row.get("replay_sha256"),
                    "sha_state": row.get("sha_state"),
                    "strict_ready_at_preregistration": bool(row.get("strict_ready")),
                    "split": split,
                    "rank_sha256": _rank(
                        salt, source, str(row["partition_date"]), int(row["episode_id"])
                    ),
                    "scenario_sha256": None,
                }
            )

    counts = Counter((row["source_class"], row["split"]) for row in assignments)
    return {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "registry_schema": registry.get("schema"),
        "registry_expected_configuration_sha256": registry.get("expected_configuration_sha256"),
        "selection": {
            "algorithm": "sha256(salt\\0source\\0partition_date\\0episode_id), ascending",
            "salt": salt,
            "outcomes_used": False,
            "steps_opened": False,
            "dev_per_source": dev_per_source,
            "frozen_per_source": frozen_per_source,
        },
        "collision_policy": {
            "episode": "exclude every colliding record",
            "seed": "exclude every globally colliding record",
            "scenario_sha256": "fail closed during extracted-scenario validation",
        },
        "frozen_lock": {"status": "UNLOCKED", "candidate_sha256": None, "locked_at": None},
        "panel_gate": {
            "A_ACCOUNT_ONLINE_min_win_rate": 0.75,
            "B_OFFICIAL_DAILY_min_win_rate": 0.75,
            "both_required": True,
            "denominator": "planned games; errors count as non-wins",
        },
        "counts": {f"{source}:{split}": counts[(source, split)] for source in SOURCES for split in ("dev", "frozen")},
        "exclusions": exclusions,
        "assignments": assignments,
    }


def lock_candidate(manifest: dict[str, Any], candidate_sha256: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_sha256):
        raise ValueError("candidate SHA256 must be 64 lowercase hex characters")
    lock = manifest.get("frozen_lock") or {}
    if lock.get("status") == "LOCKED" and lock.get("candidate_sha256") != candidate_sha256:
        raise ValueError("manifest is already locked to a different candidate")
    result = json.loads(json.dumps(manifest))
    result["frozen_lock"] = {
        "status": "LOCKED",
        "candidate_sha256": candidate_sha256,
        "locked_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def validate_extracted_scenarios(manifest: dict[str, Any], scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    assignments = {
        (row["source_class"], int(row["episode_id"])): row for row in manifest.get("assignments", [])
    }
    seen_hash: dict[str, tuple[str, int]] = {}
    seen_episode: set[tuple[str, int]] = set()
    seen_seed: set[int] = set()
    validated = 0
    for scenario in scenarios:
        key = (scenario["source_class"], int(scenario["episode_id"]))
        assignment = assignments.get(key)
        if assignment is None:
            raise ValueError(f"scenario {key} is not pre-registered")
        if key in seen_episode:
            raise ValueError(f"episode collision: {key}")
        seen_episode.add(key)
        seed_key = int(scenario["actual_seed"])
        if seed_key in seen_seed:
            raise ValueError(f"seed collision: {seed_key}")
        seen_seed.add(seed_key)
        scenario_hash = scenario.get("scenario_sha256")
        if not isinstance(scenario_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", scenario_hash):
            raise ValueError(f"invalid scenario SHA256 for {key}")
        if scenario_hash in seen_hash:
            raise ValueError(f"scenario hash collision: {seen_hash[scenario_hash]} and {key}")
        seen_hash[scenario_hash] = key
        validated += 1
    return {"valid": True, "validated": validated, "scenario_hashes_unique": len(seen_hash)}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preregister", help="Select panels from metadata; never opens replay steps")
    pre.add_argument("--registry", type=Path, required=True)
    pre.add_argument("--output", type=Path, required=True)
    pre.add_argument("--salt", default="v116-replay-panels-v1")
    pre.add_argument("--dev-per-source", type=int, default=64)
    pre.add_argument("--frozen-per-source", type=int, default=128)

    lock = sub.add_parser("lock-candidate", help="Commit a candidate SHA before frozen extraction")
    lock.add_argument("--manifest", type=Path, required=True)
    lock.add_argument("--output", type=Path, required=True)
    group = lock.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidate-path", type=Path)
    group.add_argument("--candidate-sha256")

    validate = sub.add_parser("validate-scenarios", help="Fail closed on extracted scenario collisions")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--scenario", type=Path, action="append", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "preregister":
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        result = preregister(
            registry,
            salt=args.salt,
            dev_per_source=args.dev_per_source,
            frozen_per_source=args.frozen_per_source,
        )
        atomic_json_dump(result, args.output.resolve())
        print(json.dumps(result["counts"], sort_keys=True))
        return 0
    if args.command == "lock-candidate":
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        candidate_sha = args.candidate_sha256 or _sha256_file(args.candidate_path)
        result = lock_candidate(manifest, candidate_sha)
        atomic_json_dump(result, args.output.resolve())
        print(json.dumps(result["frozen_lock"], sort_keys=True))
        return 0
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    scenarios = [json.loads(path.read_text(encoding="utf-8")) for path in args.scenario]
    result = validate_extracted_scenarios(manifest, scenarios)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
