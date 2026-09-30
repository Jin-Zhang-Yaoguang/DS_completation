"""Build and verify the de-duplicated historical model pool.

This module never imports a historical model.  It hashes exact submitted
archives, performs safe extraction for all exact-serving-unique versions, and
emits an evaluator-private opaque registry plus frozen lineage membership.
"""

from __future__ import annotations

from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any

from .catalog import (
    MODELS,
    PARENT_CATALOG_KEY,
    PRIMARY_ANCHOR_CATALOG_KEY,
    SECONDARY_ANCHOR_CATALOG_KEY,
    SNAPSHOT,
    HistoricalModel,
)
from .protocol import HERE, PROJECT_ROOT, atomic_create_json, canonical, file_sha256


INVENTORY = HERE / "model_pool_inventory.private.json"
LINEAGE_SEAL = HERE / "lineage_seal.private.json"
REGISTRY = HERE / "pool_registry.private.json"
AUDIT = HERE / "model_pool_audit.json"
SEALED_MODELS = HERE / "sealed_models"

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_MEMBER_BYTES = 32 * 1024 * 1024


def resolve_archive(model: HistoricalModel) -> Path:
    path = (PROJECT_ROOT / model.archive).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"archive escapes project root: {path}") from exc
    return path


def safe_member_name(name: str) -> str:
    value = PurePosixPath(name)
    if value.is_absolute() or not value.parts or any(part in {"", ".", ".."} for part in value.parts):
        raise ValueError(f"unsafe archive member: {name!r}")
    return value.as_posix()


def archive_closure(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError(f"missing/oversized archive: {path}")
    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            name = safe_member_name(member.name)
            if name in seen:
                raise ValueError(f"duplicate archive member: {name}")
            seen.add(name)
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"only regular archive files are allowed: {name}")
            if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"invalid archive member size: {name} {member.size}")
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"unable to read archive member: {name}")
            data = handle.read()
            if len(data) != member.size:
                raise ValueError(f"archive member size mismatch: {name}")
            members.append(
                {
                    "path": name,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    if not any(row["path"] == "main.py" for row in members):
        raise ValueError(f"submitted archive has no root main.py: {path}")
    members.sort(key=lambda row: row["path"])
    serving = hashlib.sha256(canonical(members)).hexdigest()
    code_rows = [row for row in members if str(row["path"]).endswith(".py")]
    code = hashlib.sha256(canonical(code_rows)).hexdigest()
    return {
        "archive_sha256": file_sha256(path),
        "archive_size_bytes": path.stat().st_size,
        "serving_fingerprint": serving,
        "code_fingerprint": code,
        "members": members,
    }


def extract_closure(path: Path, closure: dict[str, Any], destination: Path) -> None:
    expected = {row["path"]: row for row in closure["members"]}
    closure_path = destination / "closure.json"
    if destination.exists():
        if not closure_path.is_file():
            raise FileExistsError(f"unsealed runtime already exists: {destination}")
        observed = json.loads(closure_path.read_text(encoding="utf-8"))
        if observed != closure:
            raise FileExistsError(f"sealed runtime closure differs: {destination}")
        for name, row in expected.items():
            target = destination / name
            if not target.is_file() or file_sha256(target) != row["sha256"]:
                raise ValueError(f"sealed runtime member changed: {target}")
        return

    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            name = safe_member_name(member.name)
            if name not in expected or not member.isfile():
                raise ValueError(f"archive changed during extraction: {name}")
            data = archive.extractfile(member).read()  # type: ignore[union-attr]
            if hashlib.sha256(data).hexdigest() != expected[name]["sha256"]:
                raise ValueError(f"member changed during extraction: {name}")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    closure_path.write_text(
        json.dumps(closure, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_payloads(*, materialize: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model in MODELS:
        if model.peak_public_score <= 2000:
            raise ValueError(f"catalog contains a non-qualifier: {model.catalog_key}")
        path = resolve_archive(model)
        closure = archive_closure(path)
        if closure["archive_sha256"] != model.expected_archive_sha256:
            raise ValueError(f"historical archive SHA mismatch: {model.catalog_key}")
        rows.append(
            {
                **asdict(model),
                "archive": str(path),
                "peak_public_score": model.peak_public_score,
                **closure,
            }
        )

    # Exact serving duplicates are collapsed before behaviour-lineage selection.
    exact_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        exact_groups.setdefault(row["serving_fingerprint"], []).append(row)
    exact_unique: list[dict[str, Any]] = []
    exact_dropped: list[dict[str, Any]] = []
    for fingerprint, group in sorted(exact_groups.items()):
        ordered = sorted(group, key=lambda row: (-float(row["peak_public_score"]), row["catalog_key"]))
        exact_unique.append(ordered[0])
        for dropped in ordered[1:]:
            exact_dropped.append(
                {
                    "catalog_key": dropped["catalog_key"],
                    "kept_catalog_key": ordered[0]["catalog_key"],
                    "reason": "identical_serving_fingerprint",
                    "serving_fingerprint": fingerprint,
                }
            )

    by_lineage: dict[str, list[dict[str, Any]]] = {}
    for row in exact_unique:
        by_lineage.setdefault(row["behaviour_lineage"], []).append(row)
    development_representative: dict[str, str] = {}
    development_nonrepresentatives: list[dict[str, Any]] = []
    for lineage, group in sorted(by_lineage.items()):
        ordered = sorted(group, key=lambda row: (-float(row["peak_public_score"]), row["catalog_key"]))
        development_representative[lineage] = str(ordered[0]["catalog_key"])
        for deferred in ordered[1:]:
            development_nonrepresentatives.append(
                {
                    "catalog_key": deferred["catalog_key"],
                    "development_representative_catalog_key": ordered[0]["catalog_key"],
                    "reason": "development_uses_one_representative_hidden_keeps_all_versions",
                    "behaviour_lineage": lineage,
                }
            )

    # Every exact-serving-unique model remains in the hidden pool.  Ordering is
    # private and deterministic; it does not influence lineage-equal weights.
    exact_unique.sort(
        key=lambda row: (
            row["behaviour_lineage"],
            -float(row["peak_public_score"]),
            row["catalog_key"],
        )
    )
    pool_models: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    catalog_to_pool: dict[str, str] = {}
    lineage_index = {lineage: index for index, lineage in enumerate(sorted(by_lineage), 1)}
    for index, row in enumerate(exact_unique, 1):
        pool_id = f"pool_{index:02d}"
        catalog_to_pool[row["catalog_key"]] = pool_id
        runtime = SEALED_MODELS / row["serving_fingerprint"][:20]
        if materialize:
            extract_closure(Path(row["archive"]), {
                key: row[key]
                for key in ("archive_sha256", "archive_size_bytes", "serving_fingerprint", "code_fingerprint", "members")
            }, runtime)
        code_paths = [str((runtime / member["path"]).resolve()) for member in row["members"]]
        pool_models.append(
            {
                "id": pool_id,
                "kind": "python",
                "path": str((runtime / "main.py").resolve()),
                "entrypoint": "agent",
                "family": f"opaque_model_{index:02d}",
                "lineage": f"opaque_lineage_{lineage_index[row['behaviour_lineage']]:02d}",
                "code_paths": code_paths,
                "tags": ["sealed-historical-submission", "opaque-to-generator"],
            }
        )
        model_rows.append(
            {
                "opaque_pool_id": pool_id,
                "behaviour_lineage": row["behaviour_lineage"],
                "catalog_key": row["catalog_key"],
                "display_name": row["display_name"],
                "peak_public_score": row["peak_public_score"],
                "serving_fingerprint": row["serving_fingerprint"],
                "code_fingerprint": row["code_fingerprint"],
                "development_representative": (
                    development_representative[row["behaviour_lineage"]] == row["catalog_key"]
                ),
                "hidden_included": True,
            }
        )

    def pool_id_for_catalog(key: str) -> str:
        try:
            return catalog_to_pool[key]
        except KeyError as exc:
            raise ValueError(f"anchor/parent was removed by exact-serving de-duplication: {key}") from exc

    lineage_rows: list[dict[str, Any]] = []
    for lineage in sorted(by_lineage):
        members = [row for row in model_rows if row["behaviour_lineage"] == lineage]
        representatives = [row for row in members if row["development_representative"]]
        if len(representatives) != 1:
            raise ValueError(f"development representative closure failed: {lineage}")
        lineage_rows.append(
            {
                "behaviour_lineage": lineage,
                "development_representative_pool_id": representatives[0]["opaque_pool_id"],
                "hidden_member_pool_ids": [row["opaque_pool_id"] for row in members],
                "hidden_member_count": len(members),
            }
        )

    inventory = {
        "schema": "kaggriculture-v15-model-pool-inventory-1",
        "snapshot": SNAPSHOT,
        "qualifying_submission_rows": sum(len(row["qualifying_submissions"]) for row in rows),
        "local_archive_records": len(rows),
        "exact_serving_unique_records": len(exact_unique),
        "behaviour_lineages": len(lineage_rows),
        "records": rows,
        "exact_serving_dropped": exact_dropped,
        "development_nonrepresentatives": development_nonrepresentatives,
        "hidden_preserves_all_exact_serving_unique_models": True,
    }
    lineage_seal = {
        "schema": "kaggriculture-v15-lineage-seal-1",
        "development_selection_rule": "one highest historical publicScore representative per lineage",
        "hidden_selection_rule": "all exact-serving-unique models with publicScore > 2000",
        "lineage_weighting": "models equal within lineage; lineages equal in final pool score",
        "development_lineages": len(lineage_rows),
        "development_models": len(lineage_rows),
        "hidden_lineages": len(lineage_rows),
        "hidden_models": len(model_rows),
        "lineages": lineage_rows,
        "models": model_rows,
        "parent_mapping": {
            "public_alias": "P0",
            "catalog_key": PARENT_CATALOG_KEY,
            "opaque_pool_id": pool_id_for_catalog(PARENT_CATALOG_KEY),
            "serving_fingerprint": next(row["serving_fingerprint"] for row in rows if row["catalog_key"] == PARENT_CATALOG_KEY),
        },
        "direct_anchor_mapping": {
            "primary": pool_id_for_catalog(PRIMARY_ANCHOR_CATALOG_KEY),
            "secondary": pool_id_for_catalog(SECONDARY_ANCHOR_CATALOG_KEY),
        },
    }
    lineage_seal["seal_sha256"] = hashlib.sha256(canonical(lineage_seal)).hexdigest()
    registry = {
        "schema": "kaggriculture-v15-opaque-pool-registry-1",
        "models": pool_models,
        "lineage_seal_sha256": lineage_seal["seal_sha256"],
        "test_sources_allowed": False,
    }
    audit = {
        "schema": "kaggriculture-v15-model-pool-audit-1",
        "cli_snapshot": SNAPSHOT,
        "qualifying_submission_rows": inventory["qualifying_submission_rows"],
        "local_archives_verified": len(rows),
        "exact_serving_unique_models": len(exact_unique),
        "development_representatives": lineage_seal["development_models"],
        "hidden_models": lineage_seal["hidden_models"],
        "development_lineages": lineage_seal["development_lineages"],
        "hidden_lineages": lineage_seal["hidden_lineages"],
        "all_scores_strictly_above_2000": all(float(row["peak_public_score"]) > 2000 for row in rows),
        "all_archive_sha256_verified": True,
        "all_exact_serving_unique_models_in_hidden": len(pool_models) == len(exact_unique),
        "development_has_one_model_per_lineage": len(lineage_rows) == len(by_lineage),
        "parent_is_frozen_a2_archive": PARENT_CATALOG_KEY == "a2_fixed",
        "primary_anchor_is_parent": PRIMARY_ANCHOR_CATALOG_KEY == PARENT_CATALOG_KEY,
        "secondary_anchor_is_r002": SECONDARY_ANCHOR_CATALOG_KEY == "r002_fixed",
        "games_started": False,
    }
    return inventory, lineage_seal, registry, audit


def build(*, materialize: bool = True) -> dict[str, Any]:
    inventory, lineage_seal, registry, audit = build_payloads(materialize=materialize)
    for path, payload in (
        (INVENTORY, inventory),
        (LINEAGE_SEAL, lineage_seal),
        (REGISTRY, registry),
        (AUDIT, audit),
    ):
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true", help="hash archives without extracting runtimes")
    args = parser.parse_args()
    print(json.dumps(build(materialize=not args.audit_only), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
