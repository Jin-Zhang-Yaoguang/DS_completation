#!/usr/bin/env python3
"""Freeze the 200 train/validation seed identities used to fit the Router.

Only ``source`` identity metadata and collection fingerprints are consumed from
the completed 6,400-row grid.  Rewards, scores, actions and features are never
copied.  V11 league panels must exclude every listed seed.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
SCHEMA = "kaggriculture-v10-router-fit-source-exclusions-1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_payload(grid_path: Path) -> dict[str, Any]:
    grid_path = grid_path.expanduser().resolve()
    records: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    task_ids = set()
    collections = set()
    registries = set()
    rows = 0
    with grid_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            rows += 1
            task_id = str(row.get("task_id") or "")
            if not task_id or task_id in task_ids:
                raise ValueError(f"duplicate/missing grid task_id at line {line_number}")
            task_ids.add(task_id)
            if row.get("error") is not None or row.get("done") is not True:
                raise ValueError("Router fit grid is not fully successful")
            source = row.get("source") or {}
            record = {
                "date": str(source.get("date") or "")[:10],
                "episode_id": str(source.get("episode_id") or ""),
                "seed": int(source.get("seed") or 0),
                "split": "validation" if source.get("split") == "val" else str(source.get("split") or ""),
            }
            key = (record["date"], record["episode_id"], record["seed"], record["split"])
            records[key] = record
            collections.add(str(row.get("collection_fingerprint") or ""))
            registries.add(str(row.get("registry_sha256") or ""))
    if rows != 6400 or len(task_ids) != 6400:
        raise ValueError(f"expected exact 6,400-row formal grid, got {rows}")
    if len(collections) != 1 or "" in collections or len(registries) != 1 or "" in registries:
        raise ValueError("Router fit grid mixes collection/registry fingerprints")
    values = [records[key] for key in sorted(records, key=lambda item: (item[3], item[0], item[2], item[1]))]
    splits = Counter(row["split"] for row in values)
    dates = {
        split: dict(Counter(row["date"] for row in values if row["split"] == split))
        for split in ("train", "validation")
    }
    if len(values) != 200 or splits != Counter({"train": 100, "validation": 100}):
        raise ValueError(f"expected 100 train + 100 validation sources, got {splits}")
    expected_dates = {"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33}
    if any(dates[split] != expected_dates for split in dates):
        raise ValueError(f"unexpected Router fit date quotas: {dates}")
    if len({row["seed"] for row in values}) != 200:
        raise ValueError("Router fit sources contain a repeated seed")
    return {
        "schema": SCHEMA,
        "metadata_only": True,
        "outcomes_copied": False,
        "purpose": "Exclude Router fit seeds from all subsequent V11 league ranking panels.",
        "source_grid": str(grid_path),
        "source_grid_file_sha256": _sha256(grid_path),
        "collection_fingerprint": next(iter(collections)),
        "registry_and_code_sha256": next(iter(registries)),
        "records_count": len(values),
        "split_counts": dict(splits),
        "date_counts_by_split": dates,
        "records_sha256": _canonical_sha256(values),
        "records": values,
    }


def validate_payload(payload: Mapping[str, Any], grid_path: Path | None = None) -> set[int]:
    if payload.get("schema") != SCHEMA or payload.get("metadata_only") is not True:
        raise ValueError("invalid Router fit exclusion schema")
    rows = list(payload.get("records") or [])
    if len(rows) != 200 or int(payload.get("records_count") or 0) != 200:
        raise ValueError("Router fit exclusions must contain exactly 200 sources")
    if _canonical_sha256(rows) != payload.get("records_sha256"):
        raise ValueError("Router fit exclusion checksum mismatch")
    seeds = {int(row["seed"]) for row in rows}
    if len(seeds) != 200 or any(row.get("split") not in {"train", "validation"} for row in rows):
        raise ValueError("Router fit exclusions have invalid seed/split identities")
    if grid_path is not None and _sha256(grid_path.expanduser().resolve()) != payload.get("source_grid_file_sha256"):
        raise ValueError("Router fit exclusion source grid changed")
    return seeds


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, default=HERE / "router_grid_train_val.jsonl")
    parser.add_argument("--output", type=Path, default=HERE / "router_fit_source_exclusions.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_payload(args.grid)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    validate_payload(payload, args.grid)
    print(
        json.dumps(
            {
                "output": str(output),
                "records": payload["records_count"],
                "records_sha256": payload["records_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
