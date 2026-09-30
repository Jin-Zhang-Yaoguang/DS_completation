"""Run the single-use V14 confirmatory with an audit-lock compatibility patch.

Task generation, ProcessPool evaluation, consume-lock writing, finalist
validation, and result statistics remain the sealed implementations.  Only
the two deterministic metadata defects in the sealed audit lock checker are
replaced in memory for the lifetime of this parent process.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from common import HERE, file_sha256, load_json
import audit_dual_anchor as sealed_audit
from recover_audit_only import _exact_writer_lock_validator
import run_dual_anchor as sealed_runner
import seal_finalist as sealed_finalist
from seal_candidates import CANDIDATE_SEAL, CANDIDATE_SLATE, CLEAN_REGISTRY


SCHEMA = "kaggriculture-v14-confirmatory-recovery-1"


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _immutable_inputs(
    candidate: str, finalist_seal: Path, registry: Path, screen_root: Path
) -> dict[str, str]:
    screen = screen_root.resolve() / candidate
    paths = {
        "candidate_seal": CANDIDATE_SEAL,
        "candidate_slate": CANDIDATE_SLATE,
        "finalist_seal": finalist_seal,
        "finalist_recovery": HERE / "finalist_seal_recovery_provenance.json",
        "clean_registry": registry,
        "screen_games": screen / "games.jsonl",
        "screen_manifest": screen / "run_manifest.json",
        "screen_lock": HERE / "execution_state" / "screen" / f"{candidate}.json",
        "screen_audit": screen / "audit.json",
        "screen_audit_recovery": screen / "audit_recovery_provenance.json",
        "screen_panel": HERE / "screen_panel.json",
        "confirmatory_panel": HERE / "confirmatory_panel.json",
        "panel_seal": HERE / "panel_seal.json",
        "evaluation_contract": HERE / "evaluation_contract.json",
        "protocol_assets": HERE / "protocol_assets.sha256",
        "sealed_runner": Path(sealed_runner.__file__).resolve(),
        "sealed_auditor": Path(sealed_audit.__file__).resolve(),
        "sealed_finalist": Path(sealed_finalist.__file__).resolve(),
        "writer_validator": Path(__file__).resolve().with_name("recover_audit_only.py"),
    }
    return {name: file_sha256(path) for name, path in paths.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--screen-root", type=Path, required=True)
    parser.add_argument("--finalist-seal", type=Path, default=HERE / "finalist_seal.json")
    parser.add_argument("--registry", type=Path, default=CLEAN_REGISTRY)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--provenance-output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    finalist_seal = args.finalist_seal.resolve()
    registry = args.registry.resolve()
    games = args.jsonl.resolve()
    run_manifest = args.run_manifest.resolve()
    audit_output = args.audit_output.resolve()
    provenance_output = args.provenance_output.resolve()
    confirm_lock = HERE / "execution_state" / "confirmatory_consumed.json"
    for path in (games, run_manifest, audit_output, provenance_output, confirm_lock):
        if path.exists():
            raise FileExistsError(f"confirmatory output already exists: {path}")

    before = _immutable_inputs(
        args.candidate, finalist_seal, registry, args.screen_root.resolve()
    )
    sealed_audit.panel_path = HERE / "confirmatory_panel.json"
    sealed_audit._validate_consume_lock = _exact_writer_lock_validator
    sealed_finalist.audit = sealed_audit.audit
    finalist = sealed_finalist.validate_finalist_seal(finalist_seal)
    if finalist.get("finalist") != args.candidate:
        raise ValueError("confirmatory candidate differs from recovered finalist seal")
    if confirm_lock.exists():
        raise FileExistsError("confirmatory panel was consumed during preflight")

    runner_args = [
        str(Path(sealed_runner.__file__).resolve()),
        "--phase", "confirmatory",
        "--candidate", args.candidate,
        "--registry", str(registry),
        "--jsonl", str(games),
        "--run-manifest", str(run_manifest),
        "--audit-output", str(audit_output),
        "--workers", str(args.workers),
        "--execute-confirmatory",
        "--finalist-seal", str(finalist_seal),
    ]
    original_argv = sys.argv[:]
    try:
        sys.argv = runner_args
        sealed_runner.main()
    finally:
        sys.argv = original_argv

    if not all(path.is_file() for path in (games, run_manifest, audit_output, confirm_lock)):
        raise RuntimeError("sealed runner returned without a complete confirmatory artifact set")
    after = _immutable_inputs(
        args.candidate, finalist_seal, registry, args.screen_root.resolve()
    )
    if before != after:
        raise RuntimeError("an immutable pre-confirmatory input changed")
    report = load_json(audit_output)
    if report.get("phase") != "confirmatory" or report.get("candidate") != args.candidate:
        raise ValueError("confirmatory audit identity mismatch")
    if int(report.get("rows", -1)) != 400 or int(report.get("expected_rows", -1)) != 400:
        raise ValueError("confirmatory audit did not close exactly 400 tasks")

    provenance = {
        "schema": SCHEMA,
        "status": "CONFIRMATORY_COMPLETE_WITH_AUDIT_LOCK_RECOVERY",
        "candidate": args.candidate,
        "patch_surface": ["audit_dual_anchor.panel_path", "audit_dual_anchor._validate_consume_lock"],
        "task_generation_replaced": False,
        "run_tasks_replaced": False,
        "consume_lock_replaced": False,
        "finalist_validation_replaced": False,
        "resume": False,
        "dry_run": False,
        "execute_confirmatory": True,
        "immutable_inputs_before_after_equal": True,
        "immutable_input_sha256": before,
        "wrapper_sha256": file_sha256(Path(__file__).resolve()),
        "v10_evaluation_implementation_sha256": sealed_runner.v10.implementation_fingerprint(),
        "registry_and_serving_code_sha256": load_json(CANDIDATE_SEAL)[
            "registry_and_serving_code_sha256"
        ],
        "dynamic_output_sha256": {
            "run_manifest": file_sha256(run_manifest),
            "consume_lock": file_sha256(confirm_lock),
            "games": file_sha256(games),
            "audit": file_sha256(audit_output),
        },
        "run_fingerprint": report["run_fingerprint"],
        "rows": report["rows"],
        "passed": report["passed"],
    }
    _write_exclusive(provenance_output, provenance)
    print(
        json.dumps(
            {
                "audit": str(audit_output),
                "audit_sha256": provenance["dynamic_output_sha256"]["audit"],
                "games_sha256": provenance["dynamic_output_sha256"]["games"],
                "passed": report["passed"],
                "provenance": str(provenance_output),
                "rows": report["rows"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
