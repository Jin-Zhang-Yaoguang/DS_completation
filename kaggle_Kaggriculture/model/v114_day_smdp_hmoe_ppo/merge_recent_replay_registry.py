#!/usr/bin/env python3
"""Merge qualified recent official and own-online replay evidence.

The merge is metadata-only: it never opens replay content, especially Blind
replays.  Own-online rows that failed identity checks remain in their source
registry for audit and are not copied into the eligible dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


HARD_OFFICIAL_MINIMUM = date(2026, 8, 25)
HARD_OWN_MINIMUM = date(2026, 8, 20)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-registry", type=Path, required=True)
    parser.add_argument("--own-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    official = read_json(args.official_registry)
    own = read_json(args.own_registry)
    if official.get("status") != "QUALIFIED":
        raise SystemExit("Official registry is not QUALIFIED")
    if date.fromisoformat(official["cutoff_date_inclusive"]) < HARD_OFFICIAL_MINIMUM:
        raise SystemExit("Official registry cutoff violates 2026-08-25 hard minimum")
    if date.fromisoformat(own["minimum_game_date_inclusive"]) < HARD_OWN_MINIMUM:
        raise SystemExit("Own-online registry cutoff violates 2026-08-20 hard minimum")

    official_dev_dates = set(official["date_split"]["dev"])
    official_blind_dates = set(official["date_split"]["blind"])
    if not official_blind_dates:
        raise SystemExit("Official registry has no Blind date")
    blind_start = min(date.fromisoformat(value) for value in official_blind_dates)

    entries: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    duplicates = 0
    conflicts: list[dict[str, Any]] = []

    def append(entry: dict[str, Any], source_registry: str) -> None:
        nonlocal duplicates
        key = entry["dedup_key"]
        episode_key = str(entry["episode_id"])
        if key in seen:
            duplicates += 1
            return
        prior = next((item for item in entries if str(item["episode_id"]) == episode_key), None)
        if prior is not None and prior["replay_sha256"] != entry["replay_sha256"]:
            conflicts.append({
                "episode_id": entry["episode_id"],
                "first_sha256": prior["replay_sha256"],
                "second_sha256": entry["replay_sha256"],
                "second_source": source_registry,
            })
            return
        seen[key] = source_registry
        entries.append(entry)

    for source in official["entries"]:
        game_day = date.fromisoformat(source["game_date"])
        if game_day < HARD_OFFICIAL_MINIMUM:
            raise SystemExit(f"Official row below hard minimum: {source['episode_id']}")
        entry = dict(source)
        entry["registry_source"] = "official_daily_index"
        entry["evidence_eligible"] = True
        append(entry, "official_daily_index")

    excluded_own = Counter()
    for source in own["entries"]:
        game_day = date.fromisoformat(source["game_date"])
        if game_day < HARD_OWN_MINIMUM:
            excluded_own["BELOW_OWN_MINIMUM"] += 1
            continue
        if not source.get("evidence_eligible"):
            excluded_own[source.get("exclusion_reason") or "SOURCE_INELIGIBLE"] += 1
            continue
        if game_day >= blind_start:
            split = "blind"
        elif source["game_date"] in official_dev_dates:
            split = "dev"
        else:
            split = "train"
        entry = dict(source)
        entry["source"] = "own_online_cli"
        entry["registry_source"] = "own_online_cli"
        entry["split"] = split
        entry["blind_content_accessed"] = False if split == "blind" else None
        append(entry, "own_online_cli")

    entries.sort(key=lambda row: (row["game_date"], int(row["episode_id"]), row["registry_source"]))
    split_counts = Counter(row["split"] for row in entries)
    source_counts = Counter(row["registry_source"] for row in entries)
    date_counts = Counter(row["game_date"] for row in entries)
    latest_date = max(date.fromisoformat(value) for value in date_counts)
    if not any(row["split"] == "blind" and date.fromisoformat(row["game_date"]) == latest_date for row in entries):
        raise SystemExit("Latest date is not reserved as Blind")

    payload = {
        "schema": "v114_recent_replay_registry_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "QUALIFIED_ELIGIBLE_SUBSET_WITH_FAIL_CLOSED_OWN_EXCLUSIONS" if excluded_own else "QUALIFIED",
        "hard_cutoffs": {
            "official_daily_index_minimum_partition_date_inclusive": HARD_OFFICIAL_MINIMUM.isoformat(),
            "own_online_actual_game_date_minimum_inclusive": HARD_OWN_MINIMUM.isoformat(),
        },
        "dedup_key": "episode_id + replay_sha256",
        "blind_policy": {
            "blind_start_date_inclusive": blind_start.isoformat(),
            "latest_observed_date": latest_date.isoformat(),
            "content_accessed_by_merge": False,
            "rule": "All dates from the frozen official Blind start onward remain Blind; no backward promotion.",
        },
        "source_registries": {
            "official": str(args.official_registry.resolve()),
            "official_sha256": sha256_file(args.official_registry),
            "own_online": str(args.own_registry.resolve()),
            "own_online_sha256": sha256_file(args.own_registry),
            "own_online_status": own.get("status"),
        },
        "counts": {
            "eligible_total": len(entries),
            "train": split_counts["train"],
            "dev": split_counts["dev"],
            "blind": split_counts["blind"],
            "official": source_counts["official_daily_index"],
            "own_online": source_counts["own_online_cli"],
            "source_duplicate_rows_removed": duplicates,
            "episode_sha_conflicts_excluded": len(conflicts),
            "own_online_rows_excluded_fail_closed": sum(excluded_own.values()),
        },
        "date_coverage": dict(sorted(date_counts.items())),
        "own_exclusion_reasons": dict(sorted(excluded_own.items())),
        "episode_sha_conflicts": conflicts,
        "entries": entries,
    }
    if conflicts:
        payload["status"] = "FAILED_EPISODE_SHA_CONFLICT"
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "counts": payload["counts"],
        "date_coverage": payload["date_coverage"],
        "registry": str(args.output.resolve()),
        "registry_sha256": sha256_file(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
