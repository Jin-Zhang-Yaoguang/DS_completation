"""Freeze and verify the V13 dual-anchor development panels.

This script never opens historical replay payloads.  It reads only the V10
seed manifest plus development artifacts that may already expose an official
environment seed.  Every seed seen by Router fitting, V11, or any V12
development/QA/ablation artifact is quarantined before panel selection.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[1]
PROJECT_ROOT = MODEL_ROOT.parents[1]
SOURCE_MANIFEST = MODEL_ROOT / "v10_replay_lolo_router" / "evaluation_seed_manifest.jsonl"
DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
ALLOWED_SPLITS = {"train", "validation"}
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".py", ".sh", ".csv"}
INTEGER_TOKEN = re.compile(rb"(?<![A-Za-z0-9_.])-?[0-9]{1,10}(?![A-Za-z0-9_.])")
SCREEN_SALT = "kaggriculture-v13-dual-anchor-screen-20260823-v1"
CONFIRM_SALT = "kaggriculture-v13-dual-anchor-confirmatory-20260823-v1"
SCREEN_QUOTAS = {
    ("2026-08-18", "train"): 10,
    ("2026-08-18", "validation"): 2,
    ("2026-08-19", "train"): 10,
    ("2026-08-19", "validation"): 2,
    ("2026-08-20", "train"): 10,
    ("2026-08-20", "validation"): 2,
}
CONFIRM_QUOTAS = {
    ("2026-08-18", "train"): 30,
    ("2026-08-18", "validation"): 4,
    ("2026-08-19", "train"): 29,
    ("2026-08-19", "validation"): 4,
    ("2026-08-20", "train"): 29,
    ("2026-08-20", "validation"): 4,
}
SEALED_CANDIDATE_ORDER = [
    "v13a_a2_no_wool_throttle",
    "v13c_a2_v8_no_wool_throttle",
    "v13d_a2_public_winrisk_gate",
]
SEALED_ANCHORS = ["v12_incumbent_r002", "v12a2_no_shop_gate"]
EXPECTED_SCREEN_RECORDS_SHA256 = (
    "cc3fdadc6c9eaf237484bfa60b54b26933957008eceffef763e7f78ad922a6fb"
)
EXPECTED_CONFIRMATORY_RECORDS_SHA256 = (
    "6b6ca237b99290ed1eecb5edb4d2a3350c9c018803153ca19e08c171e5965b55"
)


@dataclass(frozen=True)
class Source:
    date: str
    seed: int
    episode_id: str
    split: str
    source_path: str
    lineage_fold: str = ""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def normalise_split(value: Any) -> str:
    split = str(value or "").lower()
    return "validation" if split == "val" else split


def load_sources() -> list[Source]:
    rows: list[Source] = []
    with SOURCE_MANIFEST.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            payload = json.loads(line)
            split = normalise_split(payload.get("split"))
            date = str(payload.get("date") or "")[:10]
            if date not in DATES:
                continue
            rows.append(
                Source(
                    date=date,
                    seed=int(payload["seed"]),
                    episode_id=str(payload.get("episode_id") or ""),
                    split=split,
                    source_path=str(payload.get("source_path") or ""),
                    lineage_fold=str(payload.get("lineage_fold") or ""),
                )
            )
    if not rows:
        raise ValueError("official seed manifest is empty")
    by_seed: dict[int, Source] = {}
    duplicates: list[tuple[Source, Source]] = []
    for row in rows:
        previous = by_seed.setdefault(row.seed, row)
        if previous != row:
            duplicates.append((previous, row))
    if duplicates:
        raise ValueError(f"environment seeds are not globally unique: {duplicates[:3]}")
    return sorted(rows, key=lambda row: (row.date, row.seed, row.episode_id))


def scan_roots() -> list[Path]:
    paths = [
        MODEL_ROOT / "v10_replay_lolo_router" / "router_fit_source_exclusions.json",
        MODEL_ROOT / "v11_iterative_league",
    ]
    paths.extend(sorted(path for path in MODEL_ROOT.glob("v12*") if path.is_dir()))
    paths.extend(
        MODEL_ROOT / name
        for name in (
            "v13a_a2_no_wool_throttle",
            "v13b_a2_terminal_clearance_716",
            "v13c_a2_v8_no_wool_throttle",
            "v13d_a2_public_winrisk_gate",
        )
    )
    return paths


def iter_scan_files() -> Iterable[Path]:
    seen: set[Path] = set()
    for root in scan_roots():
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield resolved


def official_seed_tokens(path: Path, official_seeds: set[int]) -> set[int]:
    matches: set[int] = set()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            # Adjacent chunks overlap so a seed split at a MiB boundary is not lost.
            data = getattr(official_seed_tokens, "_tail", b"") + block
            for token in INTEGER_TOKEN.findall(data):
                value = int(token)
                if value in official_seeds:
                    matches.add(value)
            official_seed_tokens._tail = data[-32:]  # type: ignore[attr-defined]
    official_seed_tokens._tail = b""  # type: ignore[attr-defined]
    return matches


def build_exposure_inventory(sources: list[Source]) -> dict[str, Any]:
    official_allowed = {
        row.seed for row in sources if row.split in ALLOWED_SPLITS
    }
    evidence: list[dict[str, Any]] = []
    union: set[int] = set()
    roots: dict[str, set[int]] = defaultdict(set)
    errors: list[dict[str, str]] = []
    for path in iter_scan_files():
        try:
            matches = official_seed_tokens(path, official_allowed)
        except OSError as exc:
            errors.append({"path": relative(path), "error": repr(exc)})
            continue
        if not matches:
            continue
        rel = relative(path)
        if "/v10_replay_lolo_router/" in f"/{rel}":
            category = "router_fit"
        elif "/v11_iterative_league/" in f"/{rel}":
            category = "v11_all_exposures"
        elif re.search(r"/v13[abcd]_", f"/{rel}"):
            category = "v13_candidate_qa_probe_packaging_exposures"
        else:
            category = "v12_all_exposures"
        roots[category].update(matches)
        union.update(matches)
        evidence.append(
            {
                "path": rel,
                "file_sha256": file_sha256(path),
                "matched_official_allowed_seed_count": len(matches),
                "matched_official_allowed_seeds_sha256": sha256_bytes(
                    canonical(sorted(matches))
                ),
                "matched_official_allowed_seeds": sorted(matches),
            }
        )
    if errors:
        raise OSError(f"exposure scan was incomplete: {errors[:3]}")
    by_seed = {row.seed: row for row in sources}
    records = [asdict(by_seed[seed]) for seed in sorted(union)]
    evidence.sort(key=lambda row: row["path"])
    evidence_fingerprint = sha256_bytes(canonical(evidence))
    return {
        "schema": "kaggriculture-v13-exposure-inventory-1",
        "policy": (
            "Conservative token intersection: every official train/validation "
            "environment seed appearing in Router-fit, any V11 text artifact, "
            "or any V12 text artifact is quarantined. Historical replay outcomes "
            "are never opened by this script."
        ),
        "source_manifest": relative(SOURCE_MANIFEST),
        "source_manifest_file_sha256": file_sha256(SOURCE_MANIFEST),
        "dates": list(DATES),
        "allowed_splits": sorted(ALLOWED_SPLITS),
        "test_scanned_for_selection": False,
        "test_selected": False,
        "scan_roots": [relative(path) for path in scan_roots()],
        "evidence_file_count": len(evidence),
        "evidence_fingerprint": evidence_fingerprint,
        "categories": {
            name: {
                "unique_seed_count": len(values),
                "seeds_sha256": sha256_bytes(canonical(sorted(values))),
            }
            for name, values in sorted(roots.items())
        },
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
    for stratum, count in sorted(quotas.items()):
        date, split = stratum
        pool = sorted(
            [row for row in available if row.date == date and row.split == split],
            key=lambda row: stable_rank(row, salt),
        )
        if len(pool) < count:
            raise ValueError(f"insufficient unexposed sources in {stratum}: {len(pool)} < {count}")
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
        "schema": "kaggriculture-v13-frozen-development-panel-1",
        "kind": kind,
        "frozen_before_candidate_games": True,
        "metadata_only": True,
        "historical_outcomes_accessed": False,
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


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def validate_panels(
    inventory: dict[str, Any], screen: dict[str, Any], confirm: dict[str, Any]
) -> dict[str, bool]:
    exposed = {int(row["seed"]) for row in inventory["records"]}
    screen_seeds = {int(row["seed"]) for row in screen["records"]}
    confirm_seeds = {int(row["seed"]) for row in confirm["records"]}
    checks = {
        "screen_count_36": len(screen_seeds) == 36 == int(screen["count"]),
        "confirmatory_count_100": len(confirm_seeds) == 100 == int(confirm["count"]),
        "screen_confirmatory_disjoint": not (screen_seeds & confirm_seeds),
        "screen_unexposed": not (screen_seeds & exposed),
        "confirmatory_unexposed": not (confirm_seeds & exposed),
        "screen_no_test": int(screen["test_source_count"]) == 0,
        "confirmatory_no_test": int(confirm["test_source_count"]) == 0,
        "screen_unique": screen["all_environment_seeds_unique"] is True,
        "confirmatory_unique": confirm["all_environment_seeds_unique"] is True,
        "screen_records_hash": screen["records_sha256"]
        == sha256_bytes(canonical(screen["records"])),
        "confirmatory_records_hash": confirm["records_sha256"]
        == sha256_bytes(canonical(confirm["records"])),
    }
    return checks


def validate_candidate_slate() -> dict[str, Any]:
    slate_path = HERE / "candidate_slate.json"
    registry_path = HERE / "clean_screen_registry.json"
    if not slate_path.is_file() or not registry_path.is_file():
        raise FileNotFoundError("candidate slate/clean registry missing")
    slate = json.loads(slate_path.read_text(encoding="utf-8"))
    if slate.get("status") != "sealed_before_any_screen_game":
        raise ValueError("candidate slate is not pre-screen sealed")
    if slate.get("candidate_order") != SEALED_CANDIDATE_ORDER:
        raise ValueError("candidate slate order changed")
    candidates = list(slate.get("candidates") or [])
    if [row.get("id") for row in candidates] != SEALED_CANDIDATE_ORDER:
        raise ValueError("candidate records do not close to sealed order")
    anchors = list(slate.get("anchors") or [])
    if [row.get("id") for row in anchors] != SEALED_ANCHORS:
        raise ValueError("anchor package closure changed")
    selection = dict(slate.get("selection") or {})
    if (
        selection.get("screen_execution_order") != SEALED_CANDIDATE_ORDER
        or selection.get("maximum_confirmatory_finalists") != 1
        or selection.get("all_candidates_must_complete_exact_same_screen_panel_once") is not True
        or selection.get("confirmatory_requires_derived_finalist_seal") is not True
    ):
        raise ValueError("candidate selection contract changed")
    slate_core = {
        "candidate_order": slate["candidate_order"],
        "candidates": slate["candidates"],
        "anchors": slate["anchors"],
        "rejected_before_screen": slate["rejected_before_screen"],
        "selection": slate["selection"],
        "screen_panel_records_sha256": slate["screen_panel_records_sha256"],
        "confirmatory_panel_records_sha256": slate["confirmatory_panel_records_sha256"],
    }
    if sha256_bytes(canonical(slate_core)) != slate.get("slate_core_sha256"):
        raise ValueError("candidate slate core hash mismatch")
    if (
        slate["screen_panel_records_sha256"] != EXPECTED_SCREEN_RECORDS_SHA256
        or slate["confirmatory_panel_records_sha256"]
        != EXPECTED_CONFIRMATORY_RECORDS_SHA256
    ):
        raise ValueError("candidate slate binds different panel records")

    packages = [*(row["package"] for row in candidates), *anchors]
    package_checks: dict[str, bool] = {}
    clean_by_id: dict[str, dict[str, Any]] = {}
    for package in packages:
        model_id = str(package["id"])
        for field in ("registry_entry", "source_main", "archive", "submission_manifest", "package_qa"):
            item = package[field]
            path = PROJECT_ROOT / str(item["path"])
            package_checks[f"{model_id}:{field}"] = path.is_file() and file_sha256(path) == item["file_sha256"]
        if package["package_qa"].get("verdict") != "PASS" or package["package_qa"].get("all_checks_true") is not True:
            raise ValueError(f"slate package QA is not PASS: {model_id}")
        clean = package["clean_submission"]
        members = list(clean["members"])
        for member in members:
            path = Path(member["clean_path"])
            package_checks[f"{model_id}:clean:{member['archive_path']}"] = (
                path.is_file()
                and path.stat().st_size == int(member["size_bytes"])
                and file_sha256(path) == member["sha256"]
            )
        closure = [
            {
                "archive_path": row["archive_path"],
                "sha256": row["sha256"],
                "size_bytes": int(row["size_bytes"]),
            }
            for row in members
        ]
        if sha256_bytes(canonical(closure)) != clean["closure_sha256"]:
            raise ValueError(f"clean closure hash mismatch: {model_id}")
        clean_by_id[model_id] = clean
    if not all(package_checks.values()):
        failed = [key for key, value in package_checks.items() if not value]
        raise ValueError(f"candidate/anchor package artifacts changed: {failed[:5]}")
    for rejected in slate.get("rejected_before_screen") or []:
        if rejected.get("id") != "v13b_a2_terminal_clearance_716" or rejected.get("included_in_screen") is not False:
            raise ValueError("terminal716 rejection record changed")
        for item in rejected["artifacts"]:
            path = PROJECT_ROOT / item["path"]
            if not path.is_file() or file_sha256(path) != item["file_sha256"]:
                raise ValueError(f"rejected-candidate artifact changed: {path}")

    v10_path = MODEL_ROOT / "v10_replay_lolo_router"
    for value in (str(PROJECT_ROOT), str(v10_path)):
        if value not in sys.path:
            sys.path.insert(0, value)
    from agent_factory import load_registry, registry_fingerprint

    registry = load_registry(registry_path)
    expected_models = [*SEALED_ANCHORS, *SEALED_CANDIDATE_ORDER]
    if list(registry.models) != expected_models:
        raise ValueError("clean registry model order/set changed")
    if registry.raw.get("candidate_slate_file_sha256") != file_sha256(slate_path):
        raise ValueError("clean registry does not bind candidate slate file")
    for model_id in expected_models:
        spec = registry.require(model_id)
        clean = clean_by_id[model_id]
        expected_paths = [row["clean_path"] for row in clean["members"]]
        if (
            spec.get("factory") is not None
            or spec.get("entrypoint") != "agent"
            or str(Path(spec["path"]).resolve()) != str(Path(clean["main"]).resolve())
            or list(spec.get("code_paths") or []) != expected_paths
            or spec.get("clean_submission_closure_sha256") != clean["closure_sha256"]
        ):
            raise ValueError(f"clean raw-agent registry closure changed: {model_id}")
    return {
        "candidate_order": SEALED_CANDIDATE_ORDER,
        "candidate_slate_file_sha256": file_sha256(slate_path),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "clean_registry_file_sha256": file_sha256(registry_path),
        "clean_registry_and_code_sha256": registry_fingerprint(registry),
        "package_artifact_checks": len(package_checks),
        "maximum_confirmatory_finalists": 1,
        "passed": True,
    }


def freeze() -> dict[str, Any]:
    sources = load_sources()
    inventory = build_exposure_inventory(sources)
    exposed = {int(row["seed"]) for row in inventory["records"]}
    if (HERE / "candidate_slate.json").is_file():
        screen = json.loads((HERE / "screen_panel.json").read_text(encoding="utf-8"))
        confirm = json.loads((HERE / "confirmatory_panel.json").read_text(encoding="utf-8"))
        if (
            screen.get("records_sha256") != EXPECTED_SCREEN_RECORDS_SHA256
            or confirm.get("records_sha256") != EXPECTED_CONFIRMATORY_RECORDS_SHA256
        ):
            raise ValueError("pre-slate panel records changed; reselection is forbidden")
    else:
        available = [
            row for row in sources if row.split in ALLOWED_SPLITS and row.seed not in exposed
        ]
        screen_rows = select_panel(available, SCREEN_QUOTAS, SCREEN_SALT)
        screen_seeds = {row.seed for row in screen_rows}
        confirm_rows = select_panel(
            [row for row in available if row.seed not in screen_seeds],
            CONFIRM_QUOTAS,
            CONFIRM_SALT,
        )
        screen = panel_payload(
            "screen", screen_rows, SCREEN_SALT, SCREEN_QUOTAS, inventory["union_seeds_sha256"]
        )
        confirm = panel_payload(
            "confirmatory",
            confirm_rows,
            CONFIRM_SALT,
            CONFIRM_QUOTAS,
            inventory["union_seeds_sha256"],
        )
    checks = validate_panels(inventory, screen, confirm)
    if not all(checks.values()):
        raise ValueError(f"panel validation failed: {checks}")
    write_json(HERE / "exposure_inventory.json", inventory)
    # Records are frozen before the slate. Never rewrite panel files here once
    # the slate exists; only the exposure inventory and enclosing seal change.
    if not (HERE / "candidate_slate.json").is_file():
        write_json(HERE / "screen_panel.json", screen)
        write_json(HERE / "confirmatory_panel.json", confirm)
    write_jsonl(HERE / "screen_seed_manifest.jsonl", screen["records"])
    write_jsonl(HERE / "confirmatory_seed_manifest.jsonl", confirm["records"])
    assets = [
        "freeze_protocol.py",
        "build_candidate_slate.py",
        "README.md",
        "evaluation_contract.json",
        "audit_dual_anchor.py",
        "run_dual_anchor.py",
        "seal_finalist.py",
        "test_protocol_security.py",
        "candidate_slate.json",
        "clean_screen_registry.json",
        "protocol_seal_v1_invalidated_before_games.json",
        "exposure_inventory.json",
        "screen_panel.json",
        "confirmatory_panel.json",
        "screen_seed_manifest.jsonl",
        "confirmatory_seed_manifest.jsonl",
    ]
    missing = [name for name in assets if not (HERE / name).is_file()]
    if missing:
        raise FileNotFoundError(f"protocol assets missing before seal: {missing}")
    slate_validation = validate_candidate_slate()
    seal = {
        "schema": "kaggriculture-v13-dual-anchor-protocol-seal-1",
        "status": "sealed_candidate_slate_before_screen_games",
        "anchors": ["v12_incumbent_r002", "v12a2_no_shop_gate"],
        "candidate_order": SEALED_CANDIDATE_ORDER,
        "candidate_slate": slate_validation,
        "old_seal_status": "invalidated_before_games",
        "old_seal_file_sha256": file_sha256(
            HERE / "protocol_seal_v1_invalidated_before_games.json"
        ),
        "test_access": False,
        "historical_outcomes_accessed_by_freezer": False,
        "screen_sources": 36,
        "confirmatory_sources": 100,
        "screen_expected_games_per_candidate": 144,
        "confirmatory_expected_games_for_one_finalist": 400,
        "exposure_union_seed_count": inventory["union_seed_count"],
        "exposure_union_seeds_sha256": inventory["union_seeds_sha256"],
        "checks": checks,
        "asset_sha256": {name: file_sha256(HERE / name) for name in assets},
    }
    write_json(HERE / "protocol_seal.json", seal)
    (HERE / "protocol_assets.sha256").write_text(
        "".join(
            f"{file_sha256(HERE / name)}  {name}\n"
            for name in [*assets, "protocol_seal.json"]
        ),
        encoding="utf-8",
    )
    return seal


def verify() -> dict[str, Any]:
    seal = json.loads((HERE / "protocol_seal.json").read_text(encoding="utf-8"))
    inventory = json.loads((HERE / "exposure_inventory.json").read_text(encoding="utf-8"))
    screen = json.loads((HERE / "screen_panel.json").read_text(encoding="utf-8"))
    confirm = json.loads((HERE / "confirmatory_panel.json").read_text(encoding="utf-8"))
    checks = validate_panels(inventory, screen, confirm)
    checks["source_manifest_unchanged"] = (
        file_sha256(SOURCE_MANIFEST) == inventory["source_manifest_file_sha256"]
    )
    current_inventory = build_exposure_inventory(load_sources())
    checks["exposure_scan_unchanged"] = (
        current_inventory["evidence_fingerprint"] == inventory["evidence_fingerprint"]
        and current_inventory["union_seeds_sha256"] == inventory["union_seeds_sha256"]
    )
    for name, digest in seal["asset_sha256"].items():
        checks[f"sealed_asset:{name}"] = (HERE / name).is_file() and file_sha256(
            HERE / name
        ) == digest
    slate_validation = validate_candidate_slate()
    checks["candidate_slate_file_hash"] = (
        slate_validation["candidate_slate_file_sha256"]
        == seal["candidate_slate"]["candidate_slate_file_sha256"]
    )
    checks["clean_registry_and_code_hash"] = (
        slate_validation["clean_registry_and_code_sha256"]
        == seal["candidate_slate"]["clean_registry_and_code_sha256"]
    )
    checks["candidate_order_exact"] = (
        slate_validation["candidate_order"] == seal["candidate_order"] == SEALED_CANDIDATE_ORDER
    )
    passed = all(checks.values())
    report = {
        "schema": "kaggriculture-v13-dual-anchor-protocol-verification-1",
        "passed": passed,
        "checks": checks,
        "test_access": False,
    }
    if not passed:
        raise ValueError(f"sealed protocol verification failed: {checks}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    payload = verify() if args.verify else freeze()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
