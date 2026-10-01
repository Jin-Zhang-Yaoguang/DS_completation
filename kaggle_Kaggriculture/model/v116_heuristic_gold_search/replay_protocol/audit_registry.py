#!/usr/bin/env python3
"""Build a metadata-only registry for V116 Replay scenarios.

Safe default: no replay is fully hashed and no ``steps`` value is opened.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from .stream_whitelist import ReplayFormatError, read_replay_whitelist
except ImportError:  # direct-script execution
    from stream_whitelist import ReplayFormatError, read_replay_whitelist


SCHEMA = "v116-replay-metadata-registry-v1"
ACCOUNT_SNAPSHOT_SCHEMA = "v116-account-submission-snapshot-v1"
CUTOFF = "2026-08-20"
EXPECTED_MODULE = "1.32.7"
EXPECTED_CONFIGURATION: dict[str, Any] = {
    "actTimeout": 1,
    "boardSize": 10,
    "episodeSteps": 720,
    "farmHandCostMult": 1,
    "marketParams": {},
    "maxMarketOrdersPerTurn": 10,
    "runTimeout": 1200,
    "seed": None,
    "shedCapacity": 100,
    "startingMoney": 3000,
    "townCenterSellInterval": 24,
    "townShopSellInterval": 4,
    "townShopUnlockInterval": 3,
    "turnsPerDay": 24,
    "weedSpawnChance": 0.005,
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


EXPECTED_CONFIG_SHA256 = canonical_sha256(EXPECTED_CONFIGURATION)
MODEL_DATA_DEFAULT = Path(__file__).resolve().parents[3] / "model_data"


def _load_first_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        return json.JSONDecoder().raw_decode(text.lstrip())[0]
    except json.JSONDecodeError as exc:
        raise ValueError(f"cannot parse first JSON value in {path}: {exc}") from exc


def _valid_sha(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return value.lower()
    return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _load_account_submission_snapshot(
    path: str | Path | None,
) -> tuple[set[int], dict[str, Any]]:
    """Load the explicit current-account submission whitelist.

    ``None`` is intentionally not replaced by the bundled snapshot here.  A
    caller must explicitly opt into a concrete snapshot so that an old local
    directory name cannot silently become current-account provenance.
    """
    if path is None:
        return set(), {
            "status": "MISSING_FAIL_CLOSED",
            "snapshot_path": None,
            "snapshot_sha256": None,
            "verified_at": None,
            "verification_command": None,
            "whitelisted_submission_count": 0,
        }

    snapshot_path = Path(path).resolve()
    if not snapshot_path.is_file():
        raise ValueError(f"account submission snapshot does not exist: {snapshot_path}")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise ValueError("account submission snapshot must be a JSON object")
    if snapshot.get("schema") != ACCOUNT_SNAPSHOT_SCHEMA:
        raise ValueError("account submission snapshot has an unsupported schema")
    if snapshot.get("competition") != "kaggriculture":
        raise ValueError("account submission snapshot is for the wrong competition")
    verified_at = snapshot.get("verified_at")
    command = snapshot.get("verification_command")
    if not isinstance(verified_at, str) or not verified_at.strip():
        raise ValueError("account submission snapshot has no verified_at")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("account submission snapshot has no verification_command")
    raw_ids = snapshot.get("submission_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError("account submission snapshot has no submission_ids")
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in raw_ids):
        raise ValueError("account submission snapshot contains an invalid submission id")
    if len(raw_ids) != len(set(raw_ids)):
        raise ValueError("account submission snapshot contains duplicate submission ids")

    return set(raw_ids), {
        "status": "LOADED_EXPLICIT_SNAPSHOT",
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": _sha256_file(snapshot_path),
        "verified_at": verified_at,
        "verification_command": command,
        "whitelisted_submission_count": len(raw_ids),
    }


def _source_a(
    model_data: Path, cutoff: str, account_submission_ids: set[int] | None
) -> Iterable[dict[str, Any]]:
    for episodes_path in sorted(model_data.glob("*/episodes.json")):
        manifest_path = episodes_path.with_name("sync_manifest.json")
        if not manifest_path.exists():
            continue
        episodes = _load_first_json(episodes_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        replay_results = {
            int(row["episode_id"]): row
            for row in manifest.get("results", [])
            if row.get("kind") == "replay" and row.get("episode_id") is not None
        }
        submission_id_raw = manifest.get("submission_id")
        if isinstance(submission_id_raw, int) and not isinstance(submission_id_raw, bool):
            submission_id = submission_id_raw if submission_id_raw > 0 else None
        elif isinstance(submission_id_raw, str) and re.fullmatch(r"[1-9][0-9]*", submission_id_raw):
            submission_id = int(submission_id_raw)
        else:
            submission_id = None
        snapshot_provided = account_submission_ids is not None
        whitelisted = (
            submission_id in account_submission_ids
            if snapshot_provided and submission_id is not None
            else False
        )
        for episode in episodes:
            create_time = str(episode.get("createTime") or "")
            if create_time[:10] < cutoff:
                continue
            episode_id = int(episode["id"])
            result = replay_results.get(episode_id, {})
            replay_path = episodes_path.parent / "replays" / f"episode-{episode_id}-replay.json"
            yield {
                "source_class": "A_ACCOUNT_ONLINE",
                "source_name": episodes_path.parent.name,
                "submission_id": submission_id,
                "account_submission_snapshot_provided": snapshot_provided,
                "account_submission_whitelisted": whitelisted,
                "partition_date": create_time[:10],
                "date_basis": "createTime",
                "create_time": create_time or None,
                "end_time": episode.get("endTime"),
                "episode_id": episode_id,
                "replay_path": str(replay_path.resolve()),
                "download_status": result.get("status"),
                "manifest_sha256": _valid_sha(result.get("sha256")),
            }


def _source_b(model_data: Path, cutoff: str) -> Iterable[dict[str, Any]]:
    index_root = model_data / "kaggriculture_episodes_index"
    for date_dir in sorted(index_root.glob("date=20??-??-??")):
        partition_date = date_dir.name.removeprefix("date=")
        if partition_date < cutoff:
            continue
        manifest_path = date_dir / "data" / "manifest.csv"
        if not manifest_path.exists():
            continue
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                episode_id = int(row["episode_id"])
                replay_path = date_dir / "data" / f"{episode_id}.json"
                yield {
                    "source_class": "B_OFFICIAL_DAILY",
                    "source_name": f"kaggriculture-episodes-{partition_date}",
                    "submission_id": None,
                    "partition_date": partition_date,
                    "date_basis": "official_partition_create_time",
                    "create_time": row.get("create_time") or None,
                    "end_time": None,
                    "episode_id": episode_id,
                    "replay_path": str(replay_path.resolve()),
                    "download_status": "official_index",
                    "manifest_sha256": None,
                }


def _audit_record(raw: dict[str, Any]) -> dict[str, Any]:
    record = dict(raw)
    path = Path(record["replay_path"])
    record["file_exists"] = path.is_file()
    record["size_bytes"] = path.stat().st_size if path.is_file() else None
    record["manifest_sha256_claim"] = record.pop("manifest_sha256")
    record["replay_sha256"] = None
    record["sha_state"] = (
        "pending_manifest_claim" if record["manifest_sha256_claim"] else "pending_unhashed"
    )
    failures: list[str] = []
    if record["source_class"] == "A_ACCOUNT_ONLINE":
        if not record.get("account_submission_snapshot_provided"):
            failures.append("account_submission_snapshot_missing")
        elif record.get("submission_id") is None:
            failures.append("account_submission_id_missing_or_invalid")
        elif not record.get("account_submission_whitelisted"):
            failures.append("account_submission_not_whitelisted")
    if not path.is_file():
        failures.append("replay_missing")
        record.update(
            module_version=None,
            configuration=None,
            configuration_sha256=None,
            actual_seed=None,
            metadata_stopped_before_steps=None,
        )
    else:
        try:
            metadata = read_replay_whitelist(path, include_steps=False)
            config_sha = canonical_sha256(metadata.configuration)
            record.update(
                module_version=metadata.module_version,
                configuration=metadata.configuration,
                configuration_sha256=config_sha,
                actual_seed=metadata.seed,
                metadata_stopped_before_steps=metadata.stopped_before_steps,
            )
            if metadata.episode_id != record["episode_id"]:
                failures.append("episode_id_mismatch")
            if metadata.module_version != EXPECTED_MODULE:
                failures.append("module_version_mismatch")
            if config_sha != EXPECTED_CONFIG_SHA256:
                failures.append("configuration_mismatch")
            if not metadata.stopped_before_steps:
                failures.append("steps_boundary_not_seen")
        except (OSError, ReplayFormatError, ValueError) as exc:
            failures.append(f"metadata_error:{type(exc).__name__}")
            record.update(
                module_version=None,
                configuration=None,
                configuration_sha256=None,
                actual_seed=None,
                metadata_stopped_before_steps=False,
            )
    record["metadata_ready"] = not failures
    record["strict_ready"] = record["metadata_ready"] and record["sha_state"] == "recomputed"
    record["failures"] = failures
    record["record_id"] = f'{record["source_class"]}:{record["episode_id"]}'
    return record


def _deduplicate(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    by_episode: dict[int, dict[str, Any]] = {}
    by_pair: set[tuple[int, str]] = set()
    for record in records:
        episode_id = int(record["episode_id"])
        sha = record.get("replay_sha256") if record.get("sha_state") == "recomputed" else "PENDING"
        prior = by_episode.get(episode_id)
        if prior is not None:
            prior_sha = (
                prior.get("replay_sha256") if prior.get("sha_state") == "recomputed" else "PENDING"
            )
            if prior_sha != sha or sha == "PENDING":
                conflicts.append(
                    {
                        "kind": "episode_sha_collision_or_pending",
                        "episode_id": episode_id,
                        "left": prior["record_id"],
                        "right": record["record_id"],
                        "left_sha": prior_sha,
                        "right_sha": sha,
                    }
                )
                prior["metadata_ready"] = False
                prior["strict_ready"] = False
                prior["failures"].append("episode_sha_collision_or_pending")
                continue
        pair = (episode_id, sha)
        if pair in by_pair:
            continue
        by_episode[episode_id] = record
        by_pair.add(pair)
        kept.append(record)
    return kept, conflicts


def build_registry(
    model_data: str | Path,
    *,
    cutoff: str = CUTOFF,
    account_submissions_snapshot: str | Path | None = None,
    recompute_file_limit: int = 0,
    recompute_source: str = "none",
) -> dict[str, Any]:
    root = Path(model_data).resolve()
    account_submission_ids, account_snapshot = _load_account_submission_snapshot(
        account_submissions_snapshot
    )
    # ``None`` carries fail-closed provenance into each A record.  A loaded
    # empty whitelist is invalid and rejected by the loader above.
    source_a_whitelist = (
        account_submission_ids
        if account_snapshot["status"] == "LOADED_EXPLICIT_SNAPSHOT"
        else None
    )
    raw_records = list(_source_a(root, cutoff, source_a_whitelist)) + list(
        _source_b(root, cutoff)
    )
    records = [_audit_record(row) for row in raw_records]

    if recompute_file_limit < 0:
        raise ValueError("recompute_file_limit must be non-negative")
    if recompute_file_limit and recompute_source == "none":
        raise ValueError("explicit --recompute-source is required when hashing")
    source_map = {"A": "A_ACCOUNT_ONLINE", "B": "B_OFFICIAL_DAILY"}
    eligible_sources = (
        set(source_map.values()) if recompute_source == "both" else {source_map.get(recompute_source)}
    )
    hashed = 0
    for record in records:
        if hashed >= recompute_file_limit:
            break
        if record["source_class"] not in eligible_sources or not record["metadata_ready"]:
            continue
        actual = _sha256_file(Path(record["replay_path"]))
        claim = record.get("manifest_sha256_claim")
        if claim and claim != actual:
            record["failures"].append("manifest_sha_mismatch")
            record["metadata_ready"] = False
        record["replay_sha256"] = actual
        record["sha_state"] = "recomputed"
        record["strict_ready"] = record["metadata_ready"]
        hashed += 1

    records, conflicts = _deduplicate(records)
    source_counts = Counter(row["source_class"] for row in records)
    metadata_counts = Counter(row["source_class"] for row in records if row["metadata_ready"])
    strict_counts = Counter(row["source_class"] for row in records if row["strict_ready"])
    pending_counts = Counter(row["source_class"] for row in records if row["sha_state"] != "recomputed")
    return {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cutoff": cutoff,
        "date_contract": "createTime for A; official partition/create_time for B",
        "expected_module_version": EXPECTED_MODULE,
        "expected_configuration": EXPECTED_CONFIGURATION,
        "expected_configuration_sha256": EXPECTED_CONFIG_SHA256,
        "account_submission_provenance": account_snapshot,
        "steps_policy": "metadata scanner stops before the top-level steps value",
        "hash_policy": {
            "strict_ready_requires": "sha_state=recomputed",
            "manifest_claim_is_strict": False,
            "unrecomputed_sha_state_prefix": "pending_",
            "recomputed_this_run": hashed,
        },
        "summary": {
            "raw_records": len(raw_records),
            "deduplicated_records": len(records),
            "by_source": dict(source_counts),
            "metadata_ready_by_source": dict(metadata_counts),
            "strict_ready_by_source": dict(strict_counts),
            "sha_pending_or_claim_by_source": dict(pending_counts),
            "conflict_count": len(conflicts),
        },
        "conflicts": conflicts,
        "records": records,
    }


def atomic_json_dump(value: Any, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, output)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-data", type=Path, default=MODEL_DATA_DEFAULT)
    parser.add_argument("--cutoff", default=CUTOFF)
    parser.add_argument(
        "--account-submissions-snapshot",
        type=Path,
        help=(
            "Explicit current-account Kaggle submission snapshot. Omit only to "
            "audit fail-closed: every A_ACCOUNT_ONLINE record will be rejected."
        ),
    )
    parser.add_argument("--output", type=Path, help="Registry JSON path; omit for summary-only audit")
    parser.add_argument(
        "--recompute-file-limit",
        type=int,
        default=0,
        help="Safe default 0. Hash at most this many files; never use as an unbounded switch.",
    )
    parser.add_argument(
        "--recompute-source",
        choices=("none", "A", "B", "both"),
        default="none",
        help="Required explicit scope when --recompute-file-limit is non-zero.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = build_registry(
        args.model_data,
        cutoff=args.cutoff,
        account_submissions_snapshot=args.account_submissions_snapshot,
        recompute_file_limit=args.recompute_file_limit,
        recompute_source=args.recompute_source,
    )
    if args.output:
        atomic_json_dump(registry, args.output.resolve())
    print(json.dumps(registry["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if not registry["conflicts"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
