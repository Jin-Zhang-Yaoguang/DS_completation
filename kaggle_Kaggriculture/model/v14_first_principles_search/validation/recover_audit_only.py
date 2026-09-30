"""Recover a V14 audit after the sealed runner's audit-only lock bug.

This script never creates environments and never resumes tasks.  It preserves
the sealed auditor byte-for-byte, replaces only its broken lock checker with
the exact payload written by ``run_dual_anchor.consume_lock``, then delegates
all row/task/statistical validation to the original auditor.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from common import HERE, file_sha256, load_json
import audit_dual_anchor as sealed_audit
import run_dual_anchor as sealed_runner
import verify_protocol as sealed_protocol_verifier
from seal_candidates import CANDIDATE_SEAL, CANDIDATE_SLATE, CLEAN_REGISTRY


SCHEMA = "kaggriculture-v14-audit-recovery-1"


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _exact_writer_lock_validator(
    phase: str,
    candidate: str,
    fingerprint: str,
    games: Path,
    run_manifest: Path,
    registry: Any,
) -> Path:
    lock_path = (
        HERE / "execution_state" / "screen" / f"{candidate}.json"
        if phase == "screen"
        else HERE / "execution_state" / "confirmatory_consumed.json"
    )
    observed = load_json(lock_path)
    panel = HERE / ("screen_panel.json" if phase == "screen" else "confirmatory_panel.json")
    expected = {
        "schema": "kaggriculture-v14-panel-consume-lock-1",
        "phase": phase,
        "candidate": candidate,
        "run_fingerprint": fingerprint,
        "jsonl": str(games.resolve()),
        "run_manifest": str(run_manifest.resolve()),
        "run_manifest_file_sha256": file_sha256(run_manifest),
        "registry_and_code_sha256": sealed_audit.registry_fingerprint(registry),
        "panel_file_sha256": file_sha256(panel),
        "candidate_seal_file_sha256": file_sha256(CANDIDATE_SEAL),
    }
    if observed != expected:
        raise ValueError("consume lock differs from the exact writer payload")
    return lock_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "confirmatory"), required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=CLEAN_REGISTRY)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--provenance-output", type=Path, required=True)
    args = parser.parse_args()

    games = args.games.resolve()
    run_manifest = args.run_manifest.resolve()
    registry = args.registry.resolve()
    audit_output = args.audit_output.resolve()
    provenance_output = args.provenance_output.resolve()
    if audit_output.exists() or provenance_output.exists():
        raise FileExistsError("recovery outputs must not already exist")

    panel_path = HERE / (
        "screen_panel.json" if args.phase == "screen" else "confirmatory_panel.json"
    )
    lock_path = (
        HERE / "execution_state" / "screen" / f"{args.candidate}.json"
        if args.phase == "screen"
        else HERE / "execution_state" / "confirmatory_consumed.json"
    )
    immutable_inputs = {
        "games": file_sha256(games),
        "run_manifest": file_sha256(run_manifest),
        "consume_lock": file_sha256(lock_path),
        "panel": file_sha256(panel_path),
        "candidate_seal": file_sha256(CANDIDATE_SEAL),
        "candidate_slate": file_sha256(CANDIDATE_SLATE),
        "clean_registry": file_sha256(registry),
        "panel_seal": file_sha256(HERE / "panel_seal.json"),
        "evaluation_contract": file_sha256(HERE / "evaluation_contract.json"),
        "sealed_runner": file_sha256(Path(sealed_runner.__file__).resolve()),
        "sealed_auditor": file_sha256(Path(sealed_audit.__file__).resolve()),
        "sealed_protocol_verifier": file_sha256(
            Path(sealed_protocol_verifier.__file__).resolve()
        ),
    }

    # The first assignment satisfies the sealed function's otherwise undefined
    # global.  The second replaces that function because its expected payload
    # contains two fields never written by the sealed runner.  No other audit
    # function is changed.
    sealed_audit.panel_path = panel_path
    sealed_audit._validate_consume_lock = _exact_writer_lock_validator
    report = sealed_audit.audit(
        args.phase, args.candidate, games, run_manifest, registry
    )
    _write_exclusive(audit_output, report)

    after_inputs = {
        "games": file_sha256(games),
        "run_manifest": file_sha256(run_manifest),
        "consume_lock": file_sha256(lock_path),
        "panel": file_sha256(panel_path),
        "candidate_seal": file_sha256(CANDIDATE_SEAL),
        "candidate_slate": file_sha256(CANDIDATE_SLATE),
        "clean_registry": file_sha256(registry),
        "panel_seal": file_sha256(HERE / "panel_seal.json"),
        "evaluation_contract": file_sha256(HERE / "evaluation_contract.json"),
        "sealed_runner": file_sha256(Path(sealed_runner.__file__).resolve()),
        "sealed_auditor": file_sha256(Path(sealed_audit.__file__).resolve()),
        "sealed_protocol_verifier": file_sha256(
            Path(sealed_protocol_verifier.__file__).resolve()
        ),
    }
    if immutable_inputs != after_inputs:
        raise RuntimeError("an immutable audit input changed during recovery")
    provenance = {
        "schema": SCHEMA,
        "status": "AUDIT_ONLY_RECOVERY_COMPLETE",
        "phase": args.phase,
        "candidate": args.candidate,
        "reason": [
            "sealed auditor referenced undefined panel_path",
            "sealed auditor lock expectation contained registry/panel fields absent from writer",
        ],
        "patched_surface": "runtime replacement of _validate_consume_lock only",
        "run_tasks_called": False,
        "games_replayed": False,
        "immutable_inputs_before_after_equal": True,
        "immutable_input_sha256": immutable_inputs,
        "recovery_script_sha256": file_sha256(Path(__file__).resolve()),
        "audit_output": str(audit_output),
        "audit_output_sha256": file_sha256(audit_output),
    }
    _write_exclusive(provenance_output, provenance)
    print(
        json.dumps(
            {
                "audit_output": str(audit_output),
                "audit_output_sha256": provenance["audit_output_sha256"],
                "provenance_output": str(provenance_output),
                "passed": report["passed"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
