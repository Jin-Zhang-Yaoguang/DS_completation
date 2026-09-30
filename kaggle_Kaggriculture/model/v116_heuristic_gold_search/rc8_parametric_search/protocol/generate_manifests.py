#!/usr/bin/env python3
"""Generate deterministic, disjoint RC8 seed manifests.

The generator never inspects first-shop outcomes or candidate results.  It uses
SHA256 domain separation, rejects every registered historical exposure it can
discover, and explicitly excludes the exposed RC3--RC7 regression seeds
7100--7103.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "v116-rc8-parametric-seed-manifest-v1"
DOMAIN = "v116-rc8-parametric-seeds-v1"
MAX_ENGINE_SEED = 2_147_483_647
EXPLICIT_EXCLUSIONS = frozenset({7100, 7101, 7102, 7103})
SPLIT_COUNTS: tuple[tuple[str, int], ...] = (
    ("r1", 8),
    ("r2", 24),
    ("r3", 2),
    ("r4", 8),
    ("router-train", 8),
    ("router-val", 16),
    ("dev", 64),
    ("confirm", 128),
)
GOLD_VERSIONS = (
    "V19", "V20", "V21", "V32", "V33", "V34", "V37", "V46", "V51",
    "V52", "V53", "V54", "V66", "V70", "V71", "V72", "V73", "V76",
)
EXPOSURE_FILENAMES = frozenset({"exposure_inventory.json", "exposure_ledger.json",
                                "seed_ledger.json", "test_exposure_quarantine.json"})


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "kaggle_Kaggriculture").is_dir():
            return parent
    raise RuntimeError("could not locate repository root")


def _all_ints(value: Any) -> Iterable[int]:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _all_ints(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _all_ints(item)


def _is_seed_value_key(key: str) -> bool:
    normalized = key.lower()
    if "seed" not in normalized:
        return False
    excluded_tokens = ("count", "sha", "hash", "schema", "selection", "rule",
                       "split", "domain", "source", "path", "status")
    return not any(token in normalized for token in excluded_tokens)


def extract_registered_seeds(value: Any) -> set[int]:
    seeds: set[int] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if _is_seed_value_key(str(key)):
                seeds.update(seed for seed in _all_ints(child)
                             if 0 < seed < MAX_ENGINE_SEED)
            else:
                seeds.update(extract_registered_seeds(child))
    elif isinstance(value, list):
        for child in value:
            seeds.update(extract_registered_seeds(child))
    return seeds


def load_jsonish(path: Path) -> Any:
    if path.suffix == ".jsonl":
        records = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
        return records
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def default_exposure_paths(root: Path, output_dir: Path) -> list[Path]:
    paths: set[Path] = set()
    for base in (root / "kaggle_Kaggriculture" / "model",
                 root / "kaggle_Kaggriculture" / "model_data"):
        if not base.is_dir():
            continue
        for path in base.rglob("*.json"):
            if path.name not in EXPOSURE_FILENAMES and "exposure" not in path.name.lower():
                continue
            try:
                path.resolve().relative_to(output_dir.resolve())
                continue
            except ValueError:
                pass
            paths.add(path.resolve())
    return sorted(paths)


def collect_exposures(paths: Iterable[Path], root: Path) -> tuple[set[int], list[dict[str, Any]]]:
    combined = set(EXPLICIT_EXCLUSIONS)
    sources: list[dict[str, Any]] = []
    for path in sorted({item.resolve() for item in paths}):
        if not path.is_file():
            raise FileNotFoundError(f"exposure source does not exist: {path}")
        value = load_jsonish(path)
        seeds = extract_registered_seeds(value)
        combined.update(seeds)
        try:
            display_path = str(path.relative_to(root))
        except ValueError:
            display_path = str(path)
        sources.append({
            "path": display_path,
            "file_sha256": file_sha256(path),
            "extracted_seed_count": len(seeds),
            "extracted_seeds_sha256": sha256_bytes(canonical_bytes(sorted(seeds))),
        })
    return combined, sources


def derive_split(domain: str, split: str, count: int, unavailable: set[int]) -> tuple[list[int], int]:
    seeds: list[int] = []
    counter = 0
    while len(seeds) < count:
        payload = f"{domain}\0{split}\0{counter}".encode("utf-8")
        candidate = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % MAX_ENGINE_SEED
        counter += 1
        if candidate <= 0 or candidate in unavailable:
            continue
        seeds.append(candidate)
        unavailable.add(candidate)
    return seeds, counter


def validate_splits(splits: dict[str, list[int]], exclusions: set[int]) -> dict[str, Any]:
    expected = dict(SPLIT_COUNTS)
    errors: list[str] = []
    seen: dict[int, str] = {}
    for name, expected_count in expected.items():
        values = splits.get(name, [])
        if len(values) != expected_count:
            errors.append(f"{name}: expected {expected_count}, got {len(values)}")
        if len(values) != len(set(values)):
            errors.append(f"{name}: duplicate seeds inside split")
        overlap = sorted(set(values) & exclusions)
        if overlap:
            errors.append(f"{name}: {len(overlap)} historical exposure overlaps")
        for seed in values:
            if seed in seen:
                errors.append(f"cross-split overlap: {seed} in {seen[seed]} and {name}")
            else:
                seen[seed] = name
    if set(splits) != set(expected):
        errors.append("split names do not match frozen protocol")
    return {
        "pass": not errors,
        "errors": errors,
        "split_count": len(splits),
        "total_seed_count": sum(len(values) for values in splits.values()),
        "unique_seed_count": len(seen),
        "historical_overlap_count": sum(len(set(values) & exclusions)
                                        for values in splits.values()),
    }


def build_payload(domain: str, exposure_paths: list[Path], root: Path,
                  output_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    exclusions, exposure_sources = collect_exposures(exposure_paths, root)
    unavailable = set(exclusions)
    raw_splits: dict[str, list[int]] = {}
    attempts: dict[str, int] = {}
    for split, count in SPLIT_COUNTS:
        raw_splits[split], attempts[split] = derive_split(domain, split, count, unavailable)
    validation = validate_splits(raw_splits, exclusions)
    if not validation["pass"]:
        raise RuntimeError("; ".join(validation["errors"]))

    split_payload: dict[str, Any] = {}
    for split, count in SPLIT_COUNTS:
        seeds = raw_splits[split]
        split_payload[split] = {
            "count": count,
            "seeds": seeds,
            "seeds_sha256": sha256_bytes(canonical_bytes(seeds)),
            "derivation_attempts": attempts[split],
        }

    manifest_core: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREREGISTERED_NOT_RUN",
        "derivation": {
            "algorithm": "sha256(domain\\0split\\0counter)[:8] mod 2147483647",
            "domain": domain,
            "explicit_exclusions": sorted(EXPLICIT_EXCLUSIONS),
            "historical_excluded_seed_count": len(exclusions),
            "historical_excluded_seeds_sha256": sha256_bytes(canonical_bytes(sorted(exclusions))),
        },
        "gold_pool": {
            "versions": list(GOLD_VERSIONS),
            "version_count": len(GOLD_VERSIONS),
            "both_seats": True,
            "development_games_per_candidate": 64 * len(GOLD_VERSIONS) * 2,
            "confirmation_games_per_candidate": 128 * len(GOLD_VERSIONS) * 2,
        },
        "splits": split_payload,
        "selection_contract": {
            "common_random_numbers_within_round": True,
            "first_shop_usage": "post_hoc_stratified_reporting_only",
            "candidate_outcomes_may_select_seeds": False,
            "development_seed_count": 64,
            "confirmation_seed_count": 128,
        },
        "validation": validation,
    }
    manifest = dict(manifest_core)
    manifest["canonical_core_sha256"] = sha256_bytes(canonical_bytes(manifest_core))

    ledger_core: dict[str, Any] = {
        "schema": "v116-rc8-exposure-ledger-v1",
        "status": "PREREGISTERED_NOT_RUN",
        "explicit_exclusions": sorted(EXPLICIT_EXCLUSIONS),
        "historical_sources": exposure_sources,
        "historical_excluded_seed_count": len(exclusions),
        "historical_excluded_seeds": sorted(exclusions),
        "historical_excluded_seeds_sha256": sha256_bytes(canonical_bytes(sorted(exclusions))),
        "registered_splits": {
            split: {
                "status": "preregistered_not_run",
                "count": split_payload[split]["count"],
                "seeds": split_payload[split]["seeds"],
                "seeds_sha256": split_payload[split]["seeds_sha256"],
            }
            for split, _count in SPLIT_COUNTS
        },
        "rules": {
            "reuse_across_splits": False,
            "first_shop_is_generation_input": False,
            "candidate_outcome_is_generation_input": False,
            "result_files_must_not_overwrite_prior_runs": True,
        },
    }
    ledger = dict(ledger_core)
    ledger["canonical_core_sha256"] = sha256_bytes(canonical_bytes(ledger_core))
    return manifest, ledger


def pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def write_artifact(output_dir: Path, name: str, value: Any) -> tuple[str, str]:
    payload = pretty_bytes(value)
    digest = sha256_bytes(payload)
    json_path = output_dir / name
    hash_path = output_dir / f"{name.removesuffix('.json')}.sha256"
    json_path.write_bytes(payload)
    hash_path.write_text(f"{digest}  {name}\n", encoding="utf-8")
    return str(json_path), digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default=DOMAIN, help="frozen SHA256 domain")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--exposure", action="append", type=Path, default=[],
                        help="additional registered exposure JSON/JSONL; repeatable")
    parser.add_argument("--no-default-exposures", action="store_true",
                        help="disable repository exposure-ledger discovery")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and print hashes without writing files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    output_dir = args.output_dir.resolve()
    paths = [] if args.no_default_exposures else default_exposure_paths(root, output_dir)
    paths.extend(path.resolve() for path in args.exposure)
    manifest, ledger = build_payload(args.domain, sorted(set(paths)), root, output_dir)

    manifest_bytes = pretty_bytes(manifest)
    ledger_bytes = pretty_bytes(ledger)
    summary = {
        "dry_run": bool(args.dry_run),
        "validation": manifest["validation"],
        "exposure_source_count": len(ledger["historical_sources"]),
        "historical_excluded_seed_count": ledger["historical_excluded_seed_count"],
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "exposure_ledger_sha256": sha256_bytes(ledger_bytes),
        "split_counts": {name: manifest["splits"][name]["count"]
                         for name, _count in SPLIT_COUNTS},
    }
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_artifact(output_dir, "seed_manifest.json", manifest)
        write_artifact(output_dir, "exposure_ledger.json", ledger)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

