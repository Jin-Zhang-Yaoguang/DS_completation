#!/usr/bin/env python3
"""Materialise the metadata-only, quarantine-clean V10 final test panel.

No environment is created and no historical reward/action field is consumed.
The only inputs are the compact seed manifest identity fields and the permanent
test-exposure quarantine.  The resulting ordered 100-source panel is immutable
input to the one-time final 14-model matrix.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .pairwise_evaluate import SeedRecord, load_seed_manifest, stratified_seed_panel
except ImportError:  # direct-file CLI compatibility
    from pairwise_evaluate import SeedRecord, load_seed_manifest, stratified_seed_panel


HERE = Path(__file__).resolve().parent
SCHEMA = "kaggriculture-v10-frozen-test-panel-1"
QUARANTINE_SCHEMA = "kaggriculture-v10-test-exposure-quarantine-1"
DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
SALT = 20260822


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identity(value: Mapping[str, Any] | SeedRecord) -> tuple[str, int, str]:
    if isinstance(value, SeedRecord):
        return value.date, int(value.seed), str(value.episode_id)
    return str(value["date"])[:10], int(value["seed"]), str(value["episode_id"])


def build_payload(
    manifest_path: Path,
    quarantine_path: Path,
    salt: int = SALT,
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    quarantine_path = quarantine_path.expanduser().resolve()
    quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
    if quarantine.get("schema") != QUARANTINE_SCHEMA:
        raise ValueError("unexpected test exposure quarantine schema")
    if quarantine.get("outcome_metrics_retained") is not False:
        raise ValueError("quarantine must be metadata-only")
    manifest_hash = file_sha256(manifest_path)
    if quarantine.get("canonical_seed_manifest_sha256") != manifest_hash:
        raise ValueError("quarantine is not bound to the canonical seed manifest")
    quarantined_rows = list(quarantine.get("quarantined_sources") or [])
    quarantined = {_identity(row) for row in quarantined_rows}
    if len(quarantined_rows) != 42 or len(quarantined) != 42:
        raise ValueError("authoritative quarantine must contain 42 unique test sources")

    records = load_seed_manifest(manifest_path)
    test_records = [row for row in records if row.split == "test"]
    test_identities = {_identity(row) for row in test_records}
    if len(test_records) != 210 or len(test_identities) != 210:
        raise ValueError("canonical test pool must contain 210 unique sources")
    if not quarantined <= test_identities:
        raise ValueError("quarantine contains a source outside canonical test")
    clean = [row for row in test_records if _identity(row) not in quarantined]
    if len(clean) != 168:
        raise ValueError(f"expected 168 clean test sources, got {len(clean)}")
    clean_by_date = Counter(row.date for row in clean)
    if clean_by_date != Counter({DATES[0]: 59, DATES[1]: 55, DATES[2]: 54}):
        raise ValueError(f"unexpected clean date distribution: {clean_by_date}")

    panel = stratified_seed_panel(
        clean,
        count=100,
        dates=DATES,
        split="test",
        random_seed=int(salt),
    )
    panel_ids = {_identity(row) for row in panel}
    if len(panel) != 100 or len(panel_ids) != 100 or panel_ids & quarantined:
        raise ValueError("frozen panel is not 100 unique quarantine-clean sources")
    panel_by_date = Counter(row.date for row in panel)
    if panel_by_date != Counter({DATES[0]: 34, DATES[1]: 33, DATES[2]: 33}):
        raise ValueError(f"unexpected panel date distribution: {panel_by_date}")

    clean_rows = [asdict(row) for row in clean]
    panel_rows = [asdict(row) for row in panel]
    return {
        "schema": SCHEMA,
        "frozen_before_final_test": True,
        "metadata_only": True,
        "historical_outcomes_accessed": False,
        "environment_games_started": False,
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": manifest_hash,
        "quarantine": str(quarantine_path),
        "quarantine_file_sha256": file_sha256(quarantine_path),
        "quarantine_schema": QUARANTINE_SCHEMA,
        "quarantined_sources": 42,
        "canonical_test_sources": 210,
        "clean_test_sources": 168,
        "clean_by_date": dict(sorted(clean_by_date.items())),
        "clean_pool_records_sha256": canonical_sha256(clean_rows),
        "selection": {
            "algorithm": "pairwise_evaluate.stratified_seed_panel",
            "salt": int(salt),
            "dates": list(DATES),
            "count": 100,
            "date_quota": dict(sorted(panel_by_date.items())),
        },
        "records_sha256": canonical_sha256(panel_rows),
        "records": panel_rows,
    }


def validate_payload(
    payload: Mapping[str, Any],
    manifest_path: Path | None = None,
    quarantine_path: Path | None = None,
) -> list[SeedRecord]:
    if payload.get("schema") != SCHEMA:
        raise ValueError("unexpected frozen test panel schema")
    if payload.get("frozen_before_final_test") is not True:
        raise ValueError("test panel is not marked frozen before final test")
    if payload.get("metadata_only") is not True or payload.get("historical_outcomes_accessed") is not False:
        raise ValueError("test panel is not metadata-only")
    raw = list(payload.get("records") or [])
    if canonical_sha256(raw) != payload.get("records_sha256"):
        raise ValueError("frozen test panel record checksum mismatch")
    records = [SeedRecord(**dict(row)) for row in raw]
    identities = {_identity(row) for row in records}
    if len(records) != 100 or len(identities) != 100:
        raise ValueError("frozen test panel must contain 100 unique sources")
    if any(row.split != "test" for row in records):
        raise ValueError("frozen test panel contains a non-test source")
    if Counter(row.date for row in records) != Counter({DATES[0]: 34, DATES[1]: 33, DATES[2]: 33}):
        raise ValueError("frozen test panel date quota mismatch")
    if int((payload.get("selection") or {}).get("salt", -1)) != SALT:
        raise ValueError("frozen test panel salt mismatch")
    if manifest_path is not None and file_sha256(manifest_path.expanduser().resolve()) != payload.get("source_manifest_sha256"):
        raise ValueError("current seed manifest differs from frozen panel")
    if quarantine_path is not None:
        quarantine_path = quarantine_path.expanduser().resolve()
        if file_sha256(quarantine_path) != payload.get("quarantine_file_sha256"):
            raise ValueError("current quarantine differs from frozen panel")
        quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
        blocked = {_identity(row) for row in quarantine.get("quarantined_sources") or []}
        if identities & blocked:
            raise ValueError("frozen test panel overlaps quarantine")
    return records


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "evaluation_seed_manifest.jsonl")
    parser.add_argument("--quarantine", type=Path, default=HERE / "test_exposure_quarantine.json")
    parser.add_argument("--salt", type=int, default=SALT)
    parser.add_argument("--output", type=Path, default=HERE / "final_test_panel.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_payload(args.manifest, args.quarantine, args.salt)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    validate_payload(payload, args.manifest, args.quarantine)
    print(
        json.dumps(
            {
                "output": str(output),
                "records": len(payload["records"]),
                "records_sha256": payload["records_sha256"],
                "clean_pool_records_sha256": payload["clean_pool_records_sha256"],
                "quarantine_file_sha256": payload["quarantine_file_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
