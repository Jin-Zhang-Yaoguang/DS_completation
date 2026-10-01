#!/usr/bin/env python3
"""Stage-gated CLI for periodic selective superblends.

Only ``audit-only`` is enabled in this infrastructure milestone.  Later stages
refuse to run until their experiment-specific pre-registration is implemented.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from superblend.lineage import build_lineage, freeze_lineage
    from superblend.registry import (
        RegistryError,
        audit_model_root,
        freeze_candidate_snapshot,
        load_candidate_snapshot,
        sources_manifest,
        write_json_exclusive,
    )
else:
    from .lineage import build_lineage, freeze_lineage
    from .registry import (
        RegistryError,
        audit_model_root,
        freeze_candidate_snapshot,
        load_candidate_snapshot,
        sources_manifest,
        write_json_exclusive,
    )


STAGES = ("audit-only", "meta-cv", "ablation", "final-fit")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate-config", type=Path)
    parser.add_argument("--candidate-snapshot", type=Path)
    parser.add_argument("--expected-oof-rows", type=int)
    parser.add_argument("--expected-test-rows", type=int)
    return parser


def run_audit_only(args: argparse.Namespace) -> dict[str, object]:
    if args.candidate_config is None:
        raise RegistryError("audit-only requires --candidate-config")
    if args.candidate_snapshot is not None:
        raise RegistryError("audit-only creates a snapshot and does not accept --candidate-snapshot")
    if not args.expected_oof_rows or not args.expected_test_rows:
        raise RegistryError("audit-only requires both expected row counts")
    repo_root = args.repo_root.resolve(strict=True)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=False)

    audit = audit_model_root(repo_root)
    write_json_exclusive(output_dir / "registry_audit.json", audit)
    envelope = freeze_candidate_snapshot(
        repo_root=repo_root,
        config_path=args.candidate_config,
        output_path=output_dir / "candidate_snapshot.json",
        expected_oof_rows=args.expected_oof_rows,
        expected_test_rows=args.expected_test_rows,
    )
    snapshot = load_candidate_snapshot(
        repo_root,
        output_dir / "candidate_snapshot.json",
        verify_sources=True,
    )
    lineage = build_lineage(repo_root, snapshot)
    freeze_lineage(output_dir / "lineage.json", lineage)
    write_json_exclusive(output_dir / "sources.json", sources_manifest(snapshot))
    summary = {
        "stage": "audit-only",
        "candidate_count": snapshot["candidate_count"],
        "candidate_snapshot_sha256": envelope["snapshot_sha256"],
        "output_dir": str(output_dir.resolve()),
        "next_stage_enabled": False,
    }
    write_json_exclusive(output_dir / "audit_summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.stage == "audit-only":
            summary = run_audit_only(args)
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
            return 0
        if args.candidate_snapshot is None:
            raise RegistryError(f"{args.stage} requires --candidate-snapshot")
        load_candidate_snapshot(args.repo_root.resolve(strict=True), args.candidate_snapshot)
        raise RegistryError(
            f"stage {args.stage!r} is intentionally disabled in the audit-only infrastructure; "
            "freeze an experiment-specific implementation before enabling it"
        )
    except (RegistryError, FileExistsError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

