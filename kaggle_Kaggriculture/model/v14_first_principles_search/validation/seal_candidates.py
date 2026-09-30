"""Seal 1--3 exact candidate archives plus the two immutable anchor archives.

Usage after the candidate packages and independent package QA reports exist::

    python seal_candidates.py \
      --candidate v14_candidate_a=/absolute/model/package/directory \
      --candidate v14_candidate_b=/absolute/model/package/directory

The package directory must contain ``submission.tar.gz``,
``submission_manifest.json``, ``package_qa_report.json``, ``registry_entry.json``
and ``main.py``.  Missing or inconsistent bytes fail before a candidate seal is
created.  No game can be dry-run or executed without that seal.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from typing import Any

from common import (
    ANCHORS,
    HERE,
    MODEL_ROOT,
    PROJECT_ROOT,
    canonical,
    file_sha256,
    load_json,
    relative,
    sha256_bytes,
    write_json,
)


SEALED_RUNTIME = HERE / "sealed_runtime"
CANDIDATE_SLATE = SEALED_RUNTIME / "candidate_slate.json"
CLEAN_REGISTRY = SEALED_RUNTIME / "clean_registry.json"
CANDIDATE_SEAL = SEALED_RUNTIME / "candidate_seal.json"
MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,95}$")
MAX_MEMBER_COUNT = 500
MAX_MEMBER_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024


def safe_member_name(name: str) -> str:
    pure = PurePosixPath(name)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe archive member: {name!r}")
    return str(pure)


def required_package_paths(root: Path) -> dict[str, Path]:
    return {
        "root": root.resolve(),
        "registry_entry": (root / "registry_entry.json").resolve(),
        "source_main": (root / "main.py").resolve(),
        "archive": (root / "submission.tar.gz").resolve(),
        "manifest": (root / "submission_manifest.json").resolve(),
        "package_qa": (root / "package_qa_report.json").resolve(),
    }


def validate_package_dir(model_id: str, root: Path) -> dict[str, Any]:
    if not MODEL_ID.fullmatch(model_id):
        raise ValueError(f"invalid model ID: {model_id!r}")
    paths = required_package_paths(root)
    missing = [str(path) for name, path in paths.items() if name != "root" and not path.is_file()]
    if missing:
        raise FileNotFoundError(f"candidate/anchor package is incomplete for {model_id}: {missing}")

    entry = load_json(paths["registry_entry"])
    manifest = load_json(paths["manifest"])
    qa = load_json(paths["package_qa"])
    if str(entry.get("id")) != model_id:
        raise ValueError(f"registry entry model ID mismatch for {model_id}")
    if str(manifest.get("model_id")) != model_id:
        raise ValueError(f"submission manifest model ID mismatch for {model_id}")
    checks = qa.get("checks")
    if qa.get("verdict") != "PASS" or not isinstance(checks, dict) or not checks:
        raise ValueError(f"package QA is not a populated PASS for {model_id}")
    if not all(value is True for value in checks.values()):
        raise ValueError(f"package QA does not have all checks true for {model_id}")
    qa_panel_access = qa.get("validation_or_new_panel_accessed")
    if qa_panel_access is not None and qa_panel_access is not False:
        raise ValueError(f"package QA accessed a validation/new panel for {model_id}")

    archive_hash = file_sha256(paths["archive"])
    if manifest.get("archive_sha256") != archive_hash:
        raise ValueError(f"archive/manifest hash mismatch for {model_id}")
    qa_archive = qa.get("archive")
    if isinstance(qa_archive, dict) and qa_archive.get("sha256") not in {None, archive_hash}:
        raise ValueError(f"archive/QA hash mismatch for {model_id}")

    file_rows = manifest.get("files")
    if not isinstance(file_rows, list) or not file_rows:
        raise ValueError(f"manifest file closure is absent for {model_id}")
    expected: dict[str, dict[str, Any]] = {}
    for row in file_rows:
        name = safe_member_name(str(row["path"]))
        if name in expected:
            raise ValueError(f"duplicate manifest member for {model_id}: {name}")
        expected[name] = {"sha256": str(row["sha256"]), "size_bytes": int(row["size_bytes"])}
    if "main.py" not in expected:
        raise ValueError(f"manifest has no main.py for {model_id}")

    member_bytes: dict[str, bytes] = {}
    with tarfile.open(paths["archive"], "r:gz") as archive:
        members = archive.getmembers()
        if len(members) > MAX_MEMBER_COUNT:
            raise ValueError(f"archive has too many members for {model_id}")
        names = [safe_member_name(member.name) for member in members]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError(f"archive member closure mismatch for {model_id}")
        total = 0
        for member, name in zip(members, names):
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"non-regular archive member for {model_id}: {name}")
            if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                raise ValueError(f"archive member size rejected for {model_id}: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot read archive member for {model_id}: {name}")
            data = stream.read(MAX_MEMBER_BYTES + 1)
            total += len(data)
            if len(data) > MAX_MEMBER_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError(f"archive expansion limit exceeded for {model_id}")
            if len(data) != expected[name]["size_bytes"] or sha256_bytes(data) != expected[name]["sha256"]:
                raise ValueError(f"archive member bytes differ from manifest for {model_id}: {name}")
            member_bytes[name] = data

    if file_sha256(paths["source_main"]) != expected["main.py"]["sha256"]:
        raise ValueError(f"source main differs from packaged main for {model_id}")
    return {
        "model_id": model_id,
        "paths": paths,
        "entry": entry,
        "manifest": manifest,
        "qa": qa,
        "archive_sha256": archive_hash,
        "member_bytes": member_bytes,
        "expected": expected,
    }


def _package_record(
    validated: dict[str, Any], final_clean_root: Path, selection_index: int | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    model_id = str(validated["model_id"])
    paths = validated["paths"]
    members = []
    for name in sorted(validated["member_bytes"]):
        spec = validated["expected"][name]
        members.append(
            {
                "archive_path": name,
                "clean_path": str(final_clean_root.joinpath(*PurePosixPath(name).parts)),
                "sha256": spec["sha256"],
                "size_bytes": spec["size_bytes"],
            }
        )
    closure = sha256_bytes(
        canonical(
            [
                {"archive_path": row["archive_path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]}
                for row in members
            ]
        )
    )
    package = {
        "id": model_id,
        "selection_index": selection_index,
        "source_package_root": str(paths["root"]),
        "registry_entry": {"path": relative(paths["registry_entry"]), "file_sha256": file_sha256(paths["registry_entry"])},
        "source_main": {"path": relative(paths["source_main"]), "file_sha256": file_sha256(paths["source_main"])},
        "archive": {"path": relative(paths["archive"]), "file_sha256": validated["archive_sha256"], "size_bytes": paths["archive"].stat().st_size},
        "submission_manifest": {"path": relative(paths["manifest"]), "file_sha256": file_sha256(paths["manifest"]), "schema": validated["manifest"].get("schema")},
        "package_qa": {
            "path": relative(paths["package_qa"]),
            "file_sha256": file_sha256(paths["package_qa"]),
            "schema": validated["qa"].get("schema"),
            "verdict": validated["qa"].get("verdict"),
            "all_checks_true": True,
            "validation_or_new_panel_accessed": validated["qa"].get("validation_or_new_panel_accessed"),
        },
        "clean_submission": {
            "root": str(final_clean_root),
            "main": str(final_clean_root / "main.py"),
            "member_count": len(members),
            "closure_sha256": closure,
            "members": members,
        },
    }
    registry_spec = copy.deepcopy(validated["entry"])
    registry_spec.pop("factory", None)
    registry_spec["entrypoint"] = "agent"
    registry_spec["path"] = str(final_clean_root / "main.py")
    registry_spec["code_paths"] = [row["clean_path"] for row in members]
    registry_spec["validation_runtime"] = "safe_exact_archive_raw_agent_entrypoint"
    registry_spec["source_archive_sha256"] = validated["archive_sha256"]
    registry_spec["clean_submission_closure_sha256"] = closure
    registry_spec["submission_manifest_file_sha256"] = package["submission_manifest"]["file_sha256"]
    registry_spec["package_qa_file_sha256"] = package["package_qa"]["file_sha256"]
    return package, registry_spec


def parse_candidate(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("candidate must be MODEL_ID=/absolute/package/directory")
    model_id, raw_path = value.split("=", 1)
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise argparse.ArgumentTypeError("candidate package directory must be absolute")
    return model_id, path.resolve()


def seal(candidate_args: list[tuple[str, Path]]) -> dict[str, Any]:
    from verify_protocol import verify

    panel_report = verify(require_candidates=False)
    if SEALED_RUNTIME.exists():
        raise FileExistsError(f"candidate runtime is already sealed or partially present: {SEALED_RUNTIME}")
    if (HERE / "execution_state").exists() or (HERE / "runs").exists():
        raise FileExistsError("execution artifacts exist before candidate seal")
    if not 1 <= len(candidate_args) <= 3:
        raise ValueError("seal requires 1 to 3 candidates")
    candidate_ids = [model_id for model_id, _ in candidate_args]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate IDs must be unique")
    if set(candidate_ids) & set(ANCHORS):
        raise ValueError("candidate ID collides with an anchor")

    package_args = [
        (model_id, MODEL_ROOT / model_id, None) for model_id in ANCHORS
    ] + [
        (model_id, root, index) for index, (model_id, root) in enumerate(candidate_args, 1)
    ]
    validated = [validate_package_dir(model_id, root) for model_id, root, _ in package_args]
    candidate_hashes = [row["archive_sha256"] for row in validated[len(ANCHORS) :]]
    if len(candidate_hashes) != len(set(candidate_hashes)):
        raise ValueError("two candidate IDs point to byte-identical archives")

    final_clean_base = SEALED_RUNTIME / "clean_submissions"
    package_records: dict[str, dict[str, Any]] = {}
    registry_specs: dict[str, dict[str, Any]] = {}
    for (_, _, selection_index), row in zip(package_args, validated):
        model_id = str(row["model_id"])
        package, spec = _package_record(row, final_clean_base / model_id, selection_index)
        package_records[model_id] = package
        registry_specs[model_id] = spec

    screen = load_json(HERE / "screen_panel.json")
    confirm = load_json(HERE / "confirmatory_panel.json")
    selection = {
        "screen_execution_order": candidate_ids,
        "all_candidates_must_complete_identical_screen_once": True,
        "hard_gate_before_ranking": "A2 pure win rate >= 0.65 and r002 pure win rate > 0.50",
        "ranking_order": [
            "descending A2 pure win rate",
            "descending r002 pure win rate",
            "descending A2 mean margin",
            "ascending immutable selection_index",
        ],
        "maximum_confirmatory_finalists": 1,
        "confirmatory_requires_derived_finalist_seal": True,
    }
    core = {
        "candidate_order": candidate_ids,
        "candidates": [package_records[model_id] for model_id in candidate_ids],
        "anchors": [package_records[model_id] for model_id in ANCHORS],
        "selection": selection,
        "panel_seal_file_sha256": file_sha256(HERE / "panel_seal.json"),
        "screen_panel_records_sha256": screen["records_sha256"],
        "confirmatory_panel_records_sha256": confirm["records_sha256"],
        "evaluation_contract_file_sha256": file_sha256(HERE / "evaluation_contract.json"),
    }
    slate = {
        "schema": "kaggriculture-v14-candidate-slate-1",
        "status": "sealed_before_any_screen_game",
        "test_access": False,
        **core,
        "slate_core_sha256": sha256_bytes(canonical(core)),
    }
    registry = {
        "schema": "kaggriculture-v14-clean-dual-anchor-registry-1",
        "purpose": "screen/confirmatory only; exact archives through raw agent entrypoint",
        "test_sources_allowed": False,
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "models": [registry_specs[model_id] for model_id in [*ANCHORS, *candidate_ids]],
    }

    stage = Path(tempfile.mkdtemp(prefix=".v14-sealed-runtime-", dir=HERE))
    try:
        for row in validated:
            model_id = str(row["model_id"])
            destination = stage / "clean_submissions" / model_id
            for name, data in row["member_bytes"].items():
                target = destination.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        write_json(stage / "candidate_slate.json", slate)
        write_json(stage / "clean_registry.json", registry)
        os.rename(stage, SEALED_RUNTIME)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise

    from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
        load_registry,
        registry_fingerprint,
    )

    loaded_registry = load_registry(CLEAN_REGISTRY)
    registry_code_hash = registry_fingerprint(loaded_registry)
    seal_core = {
        "status": "exact_candidate_and_anchor_archives_sealed_before_screen",
        "panel_verification_sha256": sha256_bytes(canonical(panel_report)),
        "panel_seal_file_sha256": file_sha256(HERE / "panel_seal.json"),
        "candidate_slate_file_sha256": file_sha256(CANDIDATE_SLATE),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "clean_registry_file_sha256": file_sha256(CLEAN_REGISTRY),
        "registry_and_serving_code_sha256": registry_code_hash,
        "candidate_order": candidate_ids,
        "anchor_order": list(ANCHORS),
        "candidate_archive_sha256": {
            model_id: package_records[model_id]["archive"]["file_sha256"] for model_id in candidate_ids
        },
        "screen_games_started": False,
        "confirmatory_games_started": False,
        "test_access": False,
    }
    candidate_seal = {
        "schema": "kaggriculture-v14-candidate-seal-1",
        **seal_core,
        "seal_core_sha256": sha256_bytes(canonical(seal_core)),
    }
    try:
        descriptor = os.open(CANDIDATE_SEAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(candidate_seal, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        # The runtime remains deliberately unusable without candidate_seal.json.
        raise
    return candidate_seal


def verify_candidate_seal() -> dict[str, Any]:
    from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
        load_registry,
        registry_fingerprint,
    )

    for path in (SEALED_RUNTIME, CANDIDATE_SLATE, CLEAN_REGISTRY, CANDIDATE_SEAL):
        if not path.exists():
            raise FileNotFoundError(f"candidate runtime is not fully sealed: {path}")
    slate = load_json(CANDIDATE_SLATE)
    registry_payload = load_json(CLEAN_REGISTRY)
    candidate_seal = load_json(CANDIDATE_SEAL)
    if slate.get("schema") != "kaggriculture-v14-candidate-slate-1" or slate.get("status") != "sealed_before_any_screen_game":
        raise ValueError("candidate slate schema/status mismatch")
    candidate_ids = list(slate.get("candidate_order") or [])
    if not 1 <= len(candidate_ids) <= 3 or len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("sealed candidate cardinality/uniqueness mismatch")
    if [row.get("id") for row in slate.get("anchors") or []] != list(ANCHORS):
        raise ValueError("sealed anchor order mismatch")
    if [row.get("id") for row in slate.get("candidates") or []] != candidate_ids:
        raise ValueError("sealed candidate order mismatch")

    core = {
        key: slate[key]
        for key in (
            "candidate_order",
            "candidates",
            "anchors",
            "selection",
            "panel_seal_file_sha256",
            "screen_panel_records_sha256",
            "confirmatory_panel_records_sha256",
            "evaluation_contract_file_sha256",
        )
    }
    if slate.get("slate_core_sha256") != sha256_bytes(canonical(core)):
        raise ValueError("candidate slate core hash mismatch")
    if slate["panel_seal_file_sha256"] != file_sha256(HERE / "panel_seal.json"):
        raise ValueError("candidate slate points to another panel seal")
    if slate["evaluation_contract_file_sha256"] != file_sha256(HERE / "evaluation_contract.json"):
        raise ValueError("candidate slate contract hash mismatch")

    all_packages = [*(slate.get("anchors") or []), *(slate.get("candidates") or [])]
    for package in all_packages:
        for artifact_name in (
            "registry_entry",
            "source_main",
            "submission_manifest",
            "package_qa",
        ):
            artifact = package[artifact_name]
            artifact_path = Path(str(artifact["path"]))
            if not artifact_path.is_absolute():
                artifact_path = PROJECT_ROOT / artifact_path
            if not artifact_path.is_file() or file_sha256(artifact_path) != artifact["file_sha256"]:
                raise ValueError(
                    f"sealed source artifact changed: {package.get('id')} {artifact_name}"
                )
        archive = PROJECT_ROOT / str(package["archive"]["path"])
        if not archive.is_file() or file_sha256(archive) != package["archive"]["file_sha256"]:
            raise ValueError(f"source archive changed: {package.get('id')}")
        members = package["clean_submission"]["members"]
        closure_rows = []
        for member in members:
            clean_path = Path(member["clean_path"])
            if not clean_path.is_file() or clean_path.stat().st_size != int(member["size_bytes"]):
                raise ValueError(f"clean member missing/size changed: {clean_path}")
            if file_sha256(clean_path) != member["sha256"]:
                raise ValueError(f"clean member hash changed: {clean_path}")
            closure_rows.append(
                {"archive_path": member["archive_path"], "sha256": member["sha256"], "size_bytes": member["size_bytes"]}
            )
        if sha256_bytes(canonical(closure_rows)) != package["clean_submission"]["closure_sha256"]:
            raise ValueError(f"clean member closure changed: {package.get('id')}")

    loaded = load_registry(CLEAN_REGISTRY)
    for model_id in [*ANCHORS, *candidate_ids]:
        loaded.require(model_id)
    registry_code_hash = registry_fingerprint(loaded)
    seal_core = {
        key: candidate_seal[key]
        for key in (
            "status",
            "panel_verification_sha256",
            "panel_seal_file_sha256",
            "candidate_slate_file_sha256",
            "candidate_slate_core_sha256",
            "clean_registry_file_sha256",
            "registry_and_serving_code_sha256",
            "candidate_order",
            "anchor_order",
            "candidate_archive_sha256",
            "screen_games_started",
            "confirmatory_games_started",
            "test_access",
        )
    }
    checks = {
        "candidate_seal_schema": candidate_seal.get("schema") == "kaggriculture-v14-candidate-seal-1",
        "candidate_seal_core": candidate_seal.get("seal_core_sha256") == sha256_bytes(canonical(seal_core)),
        "candidate_slate_file": candidate_seal.get("candidate_slate_file_sha256") == file_sha256(CANDIDATE_SLATE),
        "candidate_slate_core": candidate_seal.get("candidate_slate_core_sha256") == slate["slate_core_sha256"],
        "clean_registry_file": candidate_seal.get("clean_registry_file_sha256") == file_sha256(CLEAN_REGISTRY),
        "registry_and_code": candidate_seal.get("registry_and_serving_code_sha256") == registry_code_hash,
        "candidate_order": candidate_seal.get("candidate_order") == candidate_ids,
        "anchor_order": candidate_seal.get("anchor_order") == list(ANCHORS),
        "panel_seal_file": candidate_seal.get("panel_seal_file_sha256")
        == file_sha256(HERE / "panel_seal.json"),
        "candidate_archive_map": candidate_seal.get("candidate_archive_sha256")
        == {
            row["id"]: row["archive"]["file_sha256"]
            for row in slate["candidates"]
        },
        "test_access_false": candidate_seal.get("test_access") is False,
    }
    if not all(checks.values()):
        raise ValueError({name: ok for name, ok in checks.items() if not ok})
    return {
        "status": "SEALED",
        "candidate_order": candidate_ids,
        "candidate_seal_file_sha256": file_sha256(CANDIDATE_SEAL),
        "candidate_slate_file_sha256": file_sha256(CANDIDATE_SLATE),
        "clean_registry_file_sha256": file_sha256(CLEAN_REGISTRY),
        "registry_and_serving_code_sha256": registry_code_hash,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", type=parse_candidate, default=[])
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    payload = verify_candidate_seal() if args.verify else seal(args.candidate)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
