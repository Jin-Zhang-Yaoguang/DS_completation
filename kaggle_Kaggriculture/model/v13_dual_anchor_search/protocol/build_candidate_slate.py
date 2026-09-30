"""Build the immutable V13 candidate slate and clean-package registry."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any

from freeze_protocol import HERE, MODEL_ROOT, PROJECT_ROOT, canonical, file_sha256


CANDIDATE_ORDER = [
    "v13a_a2_no_wool_throttle",
    "v13c_a2_v8_no_wool_throttle",
    "v13d_a2_public_winrisk_gate",
]
ANCHOR_ORDER = ["v12_incumbent_r002", "v12a2_no_shop_gate"]
PACKAGE_IDS = [*ANCHOR_ORDER, *CANDIDATE_ORDER]
EXPECTED_SCREEN_RECORDS_SHA256 = (
    "cc3fdadc6c9eaf237484bfa60b54b26933957008eceffef763e7f78ad922a6fb"
)
EXPECTED_CONFIRMATORY_RECORDS_SHA256 = (
    "6b6ca237b99290ed1eecb5edb4d2a3350c9c018803153ca19e08c171e5965b55"
)
MECHANISMS = {
    "v13a_a2_no_wool_throttle": {
        "parent": "v12a2_no_shop_gate",
        "mechanism": "A2全部guard不变；所有V5/V8分支保留EGG/MILK节流，WOOL恢复A2父Router原出售量",
    },
    "v13c_a2_v8_no_wool_throttle": {
        "parent": "v12a2_no_shop_gate",
        "mechanism": "仅baseline_v8分支删除WOOL节流；baseline_v5完整保持A2",
    },
    "v13d_a2_public_winrisk_gate": {
        "parent": "v12a2_no_shop_gate",
        "mechanism": "A2节流本应触发时，仅在自己公开money严格领先且字段有效时跳过；缺失、平局、落后保持A2",
    },
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def safe_member_name(name: str) -> str:
    pure = PurePosixPath(name)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe archive member: {name!r}")
    return str(pure)


def package_paths(model_id: str) -> dict[str, Path]:
    root = MODEL_ROOT / model_id
    return {
        "root": root,
        "registry_entry": root / "registry_entry.json",
        "source_main": root / "main.py",
        "archive": root / "submission.tar.gz",
        "manifest": root / "submission_manifest.json",
        "package_qa": root / "package_qa_report.json",
    }


def extract_and_bind(model_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = package_paths(model_id)
    for name, path in paths.items():
        if name != "root" and not path.is_file():
            raise FileNotFoundError(path)
    entry = json.loads(paths["registry_entry"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    qa = json.loads(paths["package_qa"].read_text(encoding="utf-8"))
    if str(entry.get("id")) != model_id or str(manifest.get("model_id")) != model_id:
        raise ValueError(f"model ID mismatch for {model_id}")
    if qa.get("verdict") != "PASS" or not qa.get("checks") or not all(
        value is True for value in qa["checks"].values()
    ):
        raise ValueError(f"package QA is not an all-check PASS for {model_id}")
    archive_hash = file_sha256(paths["archive"])
    if archive_hash != manifest.get("archive_sha256"):
        raise ValueError(f"archive/manifest hash mismatch for {model_id}")
    qa_archive = qa.get("archive") or {}
    if qa_archive and qa_archive.get("sha256") not in {None, archive_hash}:
        raise ValueError(f"archive/QA hash mismatch for {model_id}")
    expected = {
        str(row["path"]): {
            "sha256": str(row["sha256"]),
            "size_bytes": int(row["size_bytes"]),
        }
        for row in manifest["files"]
    }
    if len(expected) != len(manifest["files"]) or "main.py" not in expected:
        raise ValueError(f"duplicate/missing manifest records for {model_id}")
    destination = HERE / "clean_submissions" / model_id
    destination.mkdir(parents=True, exist_ok=True)
    observed: dict[str, dict[str, Any]] = {}
    with tarfile.open(paths["archive"], "r:gz") as archive:
        members = archive.getmembers()
        names = [safe_member_name(member.name) for member in members]
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError(f"archive member closure mismatch for {model_id}")
        for member, name in zip(members, names):
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"non-regular archive member for {model_id}: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"unable to read archive member: {name}")
            data = stream.read()
            digest = sha256_bytes(data)
            if digest != expected[name]["sha256"] or len(data) != expected[name]["size_bytes"]:
                raise ValueError(f"archive member hash/size mismatch for {model_id}: {name}")
            target = destination.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if not target.is_file() or file_sha256(target) != digest or target.stat().st_size != len(data):
                    raise ValueError(f"existing clean member differs: {target}")
            else:
                with target.open("xb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            observed[name] = {
                "archive_path": name,
                "clean_path": str(target.resolve()),
                "sha256": digest,
                "size_bytes": len(data),
            }
    clean_records = [observed[name] for name in sorted(observed)]
    clean_closure_sha256 = sha256_bytes(
        canonical(
            [
                {"archive_path": row["archive_path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]}
                for row in clean_records
            ]
        )
    )
    source_main_hash = file_sha256(paths["source_main"])
    if source_main_hash != expected["main.py"]["sha256"]:
        raise ValueError(f"source main differs from packaged main for {model_id}")
    package = {
        "id": model_id,
        "registry_entry": {
            "path": relative(paths["registry_entry"]),
            "file_sha256": file_sha256(paths["registry_entry"]),
        },
        "source_main": {
            "path": relative(paths["source_main"]),
            "file_sha256": source_main_hash,
        },
        "archive": {
            "path": relative(paths["archive"]),
            "file_sha256": archive_hash,
            "size_bytes": paths["archive"].stat().st_size,
        },
        "submission_manifest": {
            "path": relative(paths["manifest"]),
            "file_sha256": file_sha256(paths["manifest"]),
            "schema": manifest.get("schema"),
        },
        "package_qa": {
            "path": relative(paths["package_qa"]),
            "file_sha256": file_sha256(paths["package_qa"]),
            "schema": qa.get("schema"),
            "verdict": qa.get("verdict"),
            "all_checks_true": all(value is True for value in qa["checks"].values()),
            "validation_or_new_panel_accessed": qa.get("validation_or_new_panel_accessed"),
        },
        "clean_submission": {
            "root": str(destination.resolve()),
            "main": str((destination / "main.py").resolve()),
            "member_count": len(clean_records),
            "closure_sha256": clean_closure_sha256,
            "members": clean_records,
        },
    }
    registry_spec = copy.deepcopy(entry)
    registry_spec.pop("factory", None)
    registry_spec["entrypoint"] = "agent"
    registry_spec["path"] = str((destination / "main.py").resolve())
    registry_spec["code_paths"] = [row["clean_path"] for row in clean_records]
    registry_spec["validation_runtime"] = "clean_current_go_submission_archive_raw_agent_entrypoint"
    registry_spec["source_archive_sha256"] = archive_hash
    registry_spec["clean_submission_closure_sha256"] = clean_closure_sha256
    registry_spec["submission_manifest_file_sha256"] = package["submission_manifest"]["file_sha256"]
    registry_spec["package_qa_file_sha256"] = package["package_qa"]["file_sha256"]
    return package, registry_spec


def invalidate_previous_seal() -> dict[str, Any]:
    previous_path = HERE / "protocol_seal.json"
    invalidated_path = HERE / "protocol_seal_v1_invalidated_before_games.json"
    if invalidated_path.exists():
        return json.loads(invalidated_path.read_text(encoding="utf-8"))
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    payload = {
        "schema": "kaggriculture-v13-invalidated-protocol-seal-1",
        "status": "invalidated_before_games",
        "reason": "initial seal did not bind an exact candidate slate or clean-package serving closure",
        "games_started_under_old_seal": False,
        "old_seal_file_sha256": file_sha256(previous_path),
        "old_seal": previous,
        "superseded_by": "protocol_seal.json",
    }
    write_json(invalidated_path, payload)
    return payload


def main() -> None:
    old = invalidate_previous_seal()
    screen = json.loads((HERE / "screen_panel.json").read_text(encoding="utf-8"))
    confirm = json.loads((HERE / "confirmatory_panel.json").read_text(encoding="utf-8"))
    if screen["records_sha256"] != EXPECTED_SCREEN_RECORDS_SHA256:
        raise ValueError("screen panel records changed before candidate slate")
    if confirm["records_sha256"] != EXPECTED_CONFIRMATORY_RECORDS_SHA256:
        raise ValueError("confirmatory panel records changed before candidate slate")

    packages: dict[str, dict[str, Any]] = {}
    registry_specs: dict[str, dict[str, Any]] = {}
    for model_id in PACKAGE_IDS:
        package, registry_spec = extract_and_bind(model_id)
        packages[model_id] = package
        registry_specs[model_id] = registry_spec

    rejected_root = MODEL_ROOT / "v13b_a2_terminal_clearance_716"
    rejected_files = [
        rejected_root / "rejected_registry_record.json",
        rejected_root / "mechanism_probe_report.json",
        rejected_root / "mechanism_probe.py",
        rejected_root / "README.md",
    ]
    rejected_record = json.loads(rejected_files[0].read_text(encoding="utf-8"))
    probe = json.loads(rejected_files[1].read_text(encoding="utf-8"))
    if (
        rejected_record.get("registrable") is not False
        or rejected_record.get("archive_built") is not False
        or probe.get("operationally_distinct_from_a2") is not False
        or int(probe.get("total_added_orders") or 0) != 0
        or int(probe.get("total_added_quantity") or 0) != 0
    ):
        raise ValueError("terminal716 rejection evidence changed")
    rejected = {
        "id": "v13b_a2_terminal_clearance_716",
        "parent": "v12a2_no_shop_gate",
        "mechanism": "从step716起仅填A2空闲market槽",
        "status": "rejected_before_screen",
        "reason": rejected_record["reason"],
        "zero_trigger_probe": {
            "games": len(probe["games"]),
            "steps_probed": probe["steps_probed"],
            "total_added_orders": probe["total_added_orders"],
            "total_added_quantity": probe["total_added_quantity"],
        },
        "artifacts": [
            {"path": relative(path), "file_sha256": file_sha256(path)}
            for path in rejected_files
        ],
        "registry_activated": False,
        "archive_built": False,
        "included_in_screen": False,
    }
    candidates = []
    for index, model_id in enumerate(CANDIDATE_ORDER, 1):
        candidates.append(
            {
                "selection_index": index,
                "id": model_id,
                "parent": MECHANISMS[model_id]["parent"],
                "mechanism": MECHANISMS[model_id]["mechanism"],
                "package": packages[model_id],
                "registry_spec_sha256": sha256_bytes(canonical(registry_specs[model_id])),
            }
        )
    anchor_packages = [packages[model_id] for model_id in ANCHOR_ORDER]
    selection = {
        "screen_execution_order": CANDIDATE_ORDER,
        "all_candidates_must_complete_exact_same_screen_panel_once": True,
        "hard_gate_before_ranking": "candidate must pass every pre-registered screen gate",
        "ranking_order": [
            "descending A2 competition score rate",
            "descending r002 competition score rate",
            "descending A2 mean margin",
            "ascending immutable selection_index",
        ],
        "maximum_confirmatory_finalists": 1,
        "confirmatory_requires_derived_finalist_seal": True,
    }
    slate_core = {
        "candidate_order": CANDIDATE_ORDER,
        "candidates": candidates,
        "anchors": anchor_packages,
        "rejected_before_screen": [rejected],
        "selection": selection,
        "screen_panel_records_sha256": screen["records_sha256"],
        "confirmatory_panel_records_sha256": confirm["records_sha256"],
    }
    slate = {
        "schema": "kaggriculture-v13-candidate-slate-1",
        "status": "sealed_before_any_screen_game",
        "test_access": False,
        "old_protocol_seal_invalidation_file_sha256": file_sha256(
            HERE / "protocol_seal_v1_invalidated_before_games.json"
        ),
        **slate_core,
        "slate_core_sha256": sha256_bytes(canonical(slate_core)),
    }
    write_json(HERE / "candidate_slate.json", slate)
    registry = {
        "schema": "kaggriculture-v13-clean-dual-anchor-registry-1",
        "purpose": "screen/confirmatory only; raw Kaggle agent entrypoint from safely extracted current GO archives",
        "test_sources_allowed": False,
        "candidate_slate_file_sha256": file_sha256(HERE / "candidate_slate.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "models": [registry_specs[model_id] for model_id in PACKAGE_IDS],
    }
    write_json(HERE / "clean_screen_registry.json", registry)
    print(
        json.dumps(
            {
                "candidate_slate": str(HERE / "candidate_slate.json"),
                "candidate_slate_file_sha256": file_sha256(HERE / "candidate_slate.json"),
                "candidate_order": CANDIDATE_ORDER,
                "clean_registry": str(HERE / "clean_screen_registry.json"),
                "clean_registry_file_sha256": file_sha256(HERE / "clean_screen_registry.json"),
                "old_seal_status": old["status"],
                "screen_records_sha256": screen["records_sha256"],
                "confirmatory_records_sha256": confirm["records_sha256"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
