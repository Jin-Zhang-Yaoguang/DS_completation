"""Seal the V14 finalist while preserving the sealed auditor bytes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from common import HERE, file_sha256, load_json
import audit_dual_anchor as sealed_audit
from recover_audit_only import _exact_writer_lock_validator
import seal_finalist as sealed_finalist
from seal_candidates import CANDIDATE_SEAL, CANDIDATE_SLATE, CLEAN_REGISTRY


SCHEMA = "kaggriculture-v14-finalist-recovery-1"


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _screen_inputs(screen_root: Path, candidate: str) -> dict[str, str]:
    base = screen_root.resolve() / candidate
    return {
        "screen_games": file_sha256(base / "games.jsonl"),
        "screen_manifest": file_sha256(base / "run_manifest.json"),
        "screen_audit": file_sha256(base / "audit.json"),
        "screen_audit_recovery": file_sha256(base / "audit_recovery_provenance.json"),
        "screen_lock": file_sha256(
            HERE / "execution_state" / "screen" / f"{candidate}.json"
        ),
        "candidate_seal": file_sha256(CANDIDATE_SEAL),
        "candidate_slate": file_sha256(CANDIDATE_SLATE),
        "clean_registry": file_sha256(CLEAN_REGISTRY),
        "screen_panel": file_sha256(HERE / "screen_panel.json"),
        "confirmatory_panel": file_sha256(HERE / "confirmatory_panel.json"),
        "panel_seal": file_sha256(HERE / "panel_seal.json"),
        "evaluation_contract": file_sha256(HERE / "evaluation_contract.json"),
        "sealed_auditor": file_sha256(Path(sealed_audit.__file__).resolve()),
        "sealed_finalist": file_sha256(Path(sealed_finalist.__file__).resolve()),
        "writer_validator": file_sha256(
            Path(__file__).resolve().with_name("recover_audit_only.py")
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen-root", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", type=Path, default=HERE / "finalist_seal.json")
    parser.add_argument(
        "--provenance-output",
        type=Path,
        default=HERE / "finalist_seal_recovery_provenance.json",
    )
    args = parser.parse_args()
    screen_root = args.screen_root.resolve()
    output = args.output.resolve()
    provenance_output = args.provenance_output.resolve()
    confirm_lock = HERE / "execution_state" / "confirmatory_consumed.json"
    if output.exists() or provenance_output.exists() or confirm_lock.exists():
        raise FileExistsError("finalist or confirmatory artifacts already exist")

    base = screen_root / args.candidate
    recovery = load_json(base / "audit_recovery_provenance.json")
    if recovery.get("status") != "AUDIT_ONLY_RECOVERY_COMPLETE":
        raise ValueError("screen audit recovery provenance is not complete")
    if recovery.get("audit_output_sha256") != file_sha256(base / "audit.json"):
        raise ValueError("screen audit differs from recovery provenance")
    if recovery.get("recovery_script_sha256") != file_sha256(
        Path(__file__).resolve().with_name("recover_audit_only.py")
    ):
        raise ValueError("screen audit recovery implementation changed")

    before = _screen_inputs(screen_root, args.candidate)
    sealed_audit.panel_path = HERE / "screen_panel.json"
    sealed_audit._validate_consume_lock = _exact_writer_lock_validator
    # seal_finalist imported the same function object, whose globals are the
    # patched audit_dual_anchor module.  Assign explicitly to make that binding
    # visible and reviewable.
    sealed_finalist.audit = sealed_audit.audit
    payload = sealed_finalist.derive_payload(screen_root)
    if payload.get("status") != "sealed_screen_winner":
        raise ValueError("screen produced no eligible finalist")
    if payload.get("finalist") != args.candidate:
        raise ValueError("derived finalist differs from the expected sealed candidate")
    if payload.get("eligible_ranking") != [args.candidate]:
        raise ValueError("unexpected finalist ranking/cardinality")
    sealed_finalist.write_exclusive(output, payload)

    after = _screen_inputs(screen_root, args.candidate)
    if before != after:
        raise RuntimeError("an immutable screen/finalist input changed")
    provenance = {
        "schema": SCHEMA,
        "status": "FINALIST_SEALED_WITH_AUDIT_ONLY_RECOVERY",
        "candidate": args.candidate,
        "finalist": payload["finalist"],
        "patch_surface": ["audit_dual_anchor.panel_path", "audit_dual_anchor._validate_consume_lock"],
        "ranking_logic_replaced": False,
        "task_generation_replaced": False,
        "run_tasks_called": False,
        "confirmatory_lock_exists": False,
        "immutable_inputs_before_after_equal": True,
        "immutable_input_sha256": before,
        "wrapper_sha256": file_sha256(Path(__file__).resolve()),
        "finalist_seal": str(output),
        "finalist_seal_sha256": file_sha256(output),
    }
    _write_exclusive(provenance_output, provenance)
    print(
        json.dumps(
            {
                "finalist": payload["finalist"],
                "finalist_seal": str(output),
                "finalist_seal_sha256": provenance["finalist_seal_sha256"],
                "provenance": str(provenance_output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
