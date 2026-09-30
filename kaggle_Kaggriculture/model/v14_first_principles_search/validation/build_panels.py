"""Freeze fresh V14 screen and single-use confirmatory source panels.

The builder inherits the already audited V10/V11/V12 exposure union from V13,
then conservatively scans every V13 text artifact and every pre-validation V14
text artifact for official train/validation seed tokens.  It never opens daily
replay payloads and never selects a test source.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

from common import (
    ALLOWED_SPLITS,
    CONFIRMATORY_QUOTAS,
    CONFIRMATORY_SALT,
    DATES,
    HERE,
    MODEL_ROOT,
    PROJECT_ROOT,
    SCREEN_QUOTAS,
    SCREEN_SALT,
    SOURCE_MANIFEST,
    V13_EXPOSURE_INVENTORY,
    Source,
    canonical,
    file_sha256,
    load_json,
    load_sources,
    relative,
    sha256_bytes,
)


TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".py", ".sh", ".csv"}
INTEGER_TOKEN = re.compile(rb"(?<![A-Za-z0-9_.])-?[0-9]{1,10}(?![A-Za-z0-9_.])")

SCREEN_PANEL = HERE / "screen_panel.json"
SCREEN_MANIFEST = HERE / "screen_seed_manifest.jsonl"
CONFIRMATORY_PANEL = HERE / "confirmatory_panel.json"
CONFIRMATORY_MANIFEST = HERE / "confirmatory_seed_manifest.jsonl"
EXPOSURE_INVENTORY = HERE / "exposure_inventory.json"
PANEL_SEAL = HERE / "panel_seal.json"
ASSET_SUMS = HERE / "protocol_assets.sha256"

PROTOCOL_CODE_ASSETS = (
    "README.md",
    "__init__.py",
    "common.py",
    "evaluation_contract.json",
    "build_panels.py",
    "verify_protocol.py",
    "seal_candidates.py",
    "run_dual_anchor.py",
    "audit_dual_anchor.py",
    "seal_finalist.py",
    "test_protocol_security.py",
)


def incremental_scan_roots() -> list[Path]:
    roots = sorted(path for path in MODEL_ROOT.glob("v13*") if path.is_dir())
    roots.append(MODEL_ROOT / "v14_first_principles_search")
    return roots


def iter_incremental_files() -> Iterable[Path]:
    seen: set[Path] = set()
    validation_root = HERE.resolve()
    for root in incremental_scan_roots():
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            resolved = path.resolve()
            if resolved == validation_root or validation_root in resolved.parents:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            yield resolved


def official_seed_tokens(path: Path, official_seeds: set[int]) -> set[int]:
    matches: set[int] = set()
    tail = b""
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            data = tail + block
            for token in INTEGER_TOKEN.findall(data):
                value = int(token)
                if value in official_seeds:
                    matches.add(value)
            tail = data[-32:]
    return matches


def _validate_inherited_inventory(
    payload: dict[str, Any], sources_by_seed: dict[int, Source]
) -> set[int]:
    if payload.get("schema") != "kaggriculture-v13-exposure-inventory-1":
        raise ValueError("unexpected inherited V13 exposure schema")
    if payload.get("scan_errors") != []:
        raise ValueError("inherited exposure inventory contains scan errors")
    if payload.get("source_manifest_file_sha256") != file_sha256(SOURCE_MANIFEST):
        raise ValueError("official source manifest differs from inherited exposure audit")
    seeds = [int(row["seed"]) for row in payload.get("records") or []]
    if len(seeds) != len(set(seeds)) or len(seeds) != int(payload.get("union_seed_count", -1)):
        raise ValueError("inherited exposure seed closure is inconsistent")
    if not set(seeds).issubset(sources_by_seed):
        raise ValueError("inherited exposure contains an unknown/non-allowed source")
    if sha256_bytes(canonical(sorted(seeds))) != payload.get("union_seeds_sha256"):
        raise ValueError("inherited exposure seed hash mismatch")
    return set(seeds)


def build_exposure_inventory(sources: list[Source]) -> dict[str, Any]:
    sources_by_seed = {row.seed: row for row in sources}
    official = set(sources_by_seed)
    inherited = load_json(V13_EXPOSURE_INVENTORY)
    inherited_seeds = _validate_inherited_inventory(inherited, sources_by_seed)

    evidence: list[dict[str, Any]] = []
    incremental_union: set[int] = set()
    categories: dict[str, set[int]] = defaultdict(set)
    errors: list[dict[str, str]] = []
    for path in iter_incremental_files():
        try:
            matches = official_seed_tokens(path, official)
        except OSError as exc:
            errors.append({"path": relative(path), "error": repr(exc)})
            continue
        if not matches:
            continue
        rel = relative(path)
        category = "v14_existing_dev_oracle_alternatives" if "/v14_" in f"/{rel}" else "v13_all_screen_confirm_package_qa"
        categories[category].update(matches)
        incremental_union.update(matches)
        evidence.append(
            {
                "path": rel,
                "file_sha256": file_sha256(path),
                "matched_seed_count": len(matches),
                "matched_seeds_sha256": sha256_bytes(canonical(sorted(matches))),
                "matched_seeds": sorted(matches),
            }
        )
    if errors:
        raise OSError(f"incremental exposure scan incomplete: {errors[:3]}")

    union = inherited_seeds | incremental_union
    records = [asdict(sources_by_seed[seed]) for seed in sorted(union)]
    evidence.sort(key=lambda row: row["path"])
    return {
        "schema": "kaggriculture-v14-exposure-inventory-1",
        "policy": (
            "Inherit and hash-bind the audited V13 V10-Router-fit/V11/V12 union; "
            "then conservatively token-scan all V13 artifacts and all existing V14 "
            "artifacts outside this validation directory. Daily replay payloads and "
            "test outcomes are never opened."
        ),
        "source_manifest": relative(SOURCE_MANIFEST),
        "source_manifest_file_sha256": file_sha256(SOURCE_MANIFEST),
        "dates": list(DATES),
        "allowed_splits": sorted(ALLOWED_SPLITS),
        "test_outcomes_accessed": False,
        "test_selected": False,
        "inherited_v13_inventory": {
            "path": relative(V13_EXPOSURE_INVENTORY),
            "file_sha256": file_sha256(V13_EXPOSURE_INVENTORY),
            "union_seed_count": len(inherited_seeds),
            "union_seeds_sha256": inherited["union_seeds_sha256"],
            "category_counts": inherited.get("categories"),
        },
        "incremental_scan_roots": [relative(path) for path in incremental_scan_roots()],
        "incremental_evidence_file_count": len(evidence),
        "incremental_evidence_sha256": sha256_bytes(canonical(evidence)),
        "incremental_categories": {
            name: {
                "unique_seed_count": len(seeds),
                "seeds_sha256": sha256_bytes(canonical(sorted(seeds))),
            }
            for name, seeds in sorted(categories.items())
        },
        "incremental_union_seed_count": len(incremental_union),
        "incremental_union_seeds_sha256": sha256_bytes(canonical(sorted(incremental_union))),
        "union_seed_count": len(union),
        "union_seeds_sha256": sha256_bytes(canonical(sorted(union))),
        "records": records,
        "evidence": evidence,
        "scan_errors": [],
    }


def stable_rank(row: Source, salt: str) -> str:
    return sha256_bytes(
        f"{salt}:{row.date}:{row.split}:{row.seed}:{row.episode_id}".encode("utf-8")
    )


def select_panel(
    available: list[Source], quotas: dict[tuple[str, str], int], salt: str
) -> list[Source]:
    selected: list[Source] = []
    for (date, split), count in sorted(quotas.items()):
        pool = sorted(
            [row for row in available if row.date == date and row.split == split],
            key=lambda row: stable_rank(row, salt),
        )
        if len(pool) < count:
            raise ValueError(f"insufficient unexposed sources for {(date, split)}: {len(pool)} < {count}")
        selected.extend(pool[:count])
    return sorted(selected, key=lambda row: stable_rank(row, salt + ":shuffle"))


def panel_payload(
    kind: str,
    records: list[Source],
    salt: str,
    quotas: dict[tuple[str, str], int],
    excluded_sha256: str,
) -> dict[str, Any]:
    rows = [asdict(row) for row in records]
    return {
        "schema": "kaggriculture-v14-frozen-development-panel-1",
        "kind": kind,
        "status": "frozen_before_candidate_archive_seal_and_games",
        "metadata_only": True,
        "historical_replay_payloads_accessed": False,
        "test_outcomes_accessed": False,
        "environment_games_started": False,
        "dates": list(DATES),
        "allowed_splits": sorted(ALLOWED_SPLITS),
        "test_source_count": sum(row.split == "test" for row in records),
        "selection_salt": salt,
        "selection_salt_sha256": sha256_bytes(salt.encode("utf-8")),
        "stratum_quotas": {
            f"{date}|{split}": count for (date, split), count in sorted(quotas.items())
        },
        "count": len(rows),
        "date_counts": dict(Counter(row.date for row in records)),
        "split_counts": dict(Counter(row.split for row in records)),
        "all_environment_seeds_unique": len({row.seed for row in records}) == len(rows),
        "exposure_union_seeds_sha256": excluded_sha256,
        "records_sha256": sha256_bytes(canonical(rows)),
        "records": rows,
    }


def build_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    sources = load_sources()
    inventory = build_exposure_inventory(sources)
    exposed = {int(row["seed"]) for row in inventory["records"]}
    available = [row for row in sources if row.seed not in exposed]
    screen_rows = select_panel(available, SCREEN_QUOTAS, SCREEN_SALT)
    screen_seeds = {row.seed for row in screen_rows}
    confirm_rows = select_panel(
        [row for row in available if row.seed not in screen_seeds],
        CONFIRMATORY_QUOTAS,
        CONFIRMATORY_SALT,
    )
    screen = panel_payload(
        "screen36", screen_rows, SCREEN_SALT, SCREEN_QUOTAS, inventory["union_seeds_sha256"]
    )
    confirm = panel_payload(
        "confirmatory100_single_use",
        confirm_rows,
        CONFIRMATORY_SALT,
        CONFIRMATORY_QUOTAS,
        inventory["union_seeds_sha256"],
    )
    checks = validate_panels(inventory, screen, confirm)
    if not all(checks.values()):
        raise ValueError({name: ok for name, ok in checks.items() if not ok})
    return inventory, screen, confirm


def validate_panels(
    inventory: dict[str, Any], screen: dict[str, Any], confirm: dict[str, Any]
) -> dict[str, bool]:
    exposed = {int(row["seed"]) for row in inventory["records"]}
    screen_seeds = {int(row["seed"]) for row in screen["records"]}
    confirm_seeds = {int(row["seed"]) for row in confirm["records"]}
    return {
        "screen_count_36": len(screen_seeds) == 36 == int(screen["count"]),
        "confirmatory_count_100": len(confirm_seeds) == 100 == int(confirm["count"]),
        "screen_dates_12_12_12": screen["date_counts"]
        == {"2026-08-18": 12, "2026-08-19": 12, "2026-08-20": 12},
        "confirmatory_dates_34_33_33": confirm["date_counts"]
        == {"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33},
        "screen_confirmatory_disjoint": not (screen_seeds & confirm_seeds),
        "screen_unexposed": not (screen_seeds & exposed),
        "confirmatory_unexposed": not (confirm_seeds & exposed),
        "screen_no_test": int(screen["test_source_count"]) == 0,
        "confirmatory_no_test": int(confirm["test_source_count"]) == 0,
        "screen_allowed_splits": {str(row["split"]) for row in screen["records"]}
        <= ALLOWED_SPLITS,
        "confirmatory_allowed_splits": {str(row["split"]) for row in confirm["records"]}
        <= ALLOWED_SPLITS,
        "screen_unique": screen["all_environment_seeds_unique"] is True,
        "confirmatory_unique": confirm["all_environment_seeds_unique"] is True,
        "screen_records_hash": screen["records_sha256"]
        == sha256_bytes(canonical(screen["records"])),
        "confirmatory_records_hash": confirm["records_sha256"]
        == sha256_bytes(canonical(confirm["records"])),
    }


def _exclusive_text(path: Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _jsonl_text(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)


def freeze() -> dict[str, Any]:
    required = [HERE / name for name in PROTOCOL_CODE_ASSETS]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"protocol implementation incomplete: {missing}")
    generated = [
        EXPOSURE_INVENTORY,
        SCREEN_PANEL,
        SCREEN_MANIFEST,
        CONFIRMATORY_PANEL,
        CONFIRMATORY_MANIFEST,
        PANEL_SEAL,
        ASSET_SUMS,
    ]
    existing = [str(path) for path in generated if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite frozen protocol artifacts: {existing}")

    inventory, screen, confirm = build_payloads()
    _exclusive_text(EXPOSURE_INVENTORY, _json_text(inventory))
    _exclusive_text(SCREEN_PANEL, _json_text(screen))
    _exclusive_text(SCREEN_MANIFEST, _jsonl_text(screen["records"]))
    _exclusive_text(CONFIRMATORY_PANEL, _json_text(confirm))
    _exclusive_text(CONFIRMATORY_MANIFEST, _jsonl_text(confirm["records"]))

    bound_assets = [
        *required,
        EXPOSURE_INVENTORY,
        SCREEN_PANEL,
        SCREEN_MANIFEST,
        CONFIRMATORY_PANEL,
        CONFIRMATORY_MANIFEST,
    ]
    assets = [
        {"path": relative(path), "file_sha256": file_sha256(path), "size_bytes": path.stat().st_size}
        for path in bound_assets
    ]
    seal_core = {
        "status": "frozen_metadata_only_before_candidate_archive_seal_and_games",
        "test_access": False,
        "daily_replay_payloads_accessed": False,
        "candidate_archives_sealed": False,
        "environment_games_started": False,
        "source_manifest_file_sha256": file_sha256(SOURCE_MANIFEST),
        "exposure_union_seed_count": inventory["union_seed_count"],
        "exposure_union_seeds_sha256": inventory["union_seeds_sha256"],
        "screen_records_sha256": screen["records_sha256"],
        "confirmatory_records_sha256": confirm["records_sha256"],
        "screen_confirmatory_disjoint": True,
        "screen_test_source_count": 0,
        "confirmatory_test_source_count": 0,
        "assets": assets,
    }
    seal = {
        "schema": "kaggriculture-v14-panel-seal-1",
        **seal_core,
        "seal_core_sha256": sha256_bytes(canonical(seal_core)),
    }
    _exclusive_text(PANEL_SEAL, _json_text(seal))
    sums = "".join(
        f"{file_sha256(path)}  {relative(path)}\n" for path in [*bound_assets, PANEL_SEAL]
    )
    _exclusive_text(ASSET_SUMS, sums)
    return seal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        from verify_protocol import verify

        payload = verify(require_candidates=False)
    else:
        payload = freeze()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
