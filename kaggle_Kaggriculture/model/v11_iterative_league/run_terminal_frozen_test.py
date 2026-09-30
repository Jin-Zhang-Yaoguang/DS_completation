#!/usr/bin/env python3
"""Preflight and, only with ``--execute``, run the V11 terminal sealed test."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Sequence

try:
    from .league import HERE, _atomic_json
except ImportError:  # direct-file CLI compatibility
    from league import HERE, _atomic_json

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
    registry_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate import (
    implementation_fingerprint,
    load_sealed_test_panel,
)


V10 = HERE.parent / "v10_replay_lolo_router"
SCHEMA = "kaggriculture-v11-terminal-test-preflight-1"


def preflight(
    registry_path: Path,
    state_path: Path,
    manifest_path: Path,
    panel_path: Path,
    quarantine_path: Path,
) -> dict:
    registry_path = registry_path.expanduser().resolve()
    state_path = state_path.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    panel_path = panel_path.expanduser().resolve()
    quarantine_path = quarantine_path.expanduser().resolve()
    registry = load_registry(registry_path)
    model_ids = list(registry.models)
    if len(model_ids) != 16:
        raise ValueError("terminal runner requires exactly 16 sealed models")
    panel, provenance = load_sealed_test_panel(
        registry, model_ids, panel_path, manifest_path, quarantine_path
    )
    terminal = provenance.get("terminal_pool") or {}
    if Path(str(terminal.get("league_state") or "")).resolve() != state_path:
        raise ValueError("runner league-state path differs from terminal registry seal")
    return {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "preflight_only": True,
        "environment_games_started": False,
        "registry": str(registry_path),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "evaluation_implementation_sha256": implementation_fingerprint(),
        "league_state": str(state_path),
        "models": model_ids,
        "model_count": len(model_ids),
        "panel_sources": len(panel),
        "pairs": 120,
        "games_per_pair": 200,
        "expected_games": 24_000,
        "sealed_test_protocol": provenance,
        "passed": True,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--league-state", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, default=V10 / "evaluation_seed_manifest.jsonl")
    parser.add_argument("--frozen-panel", type=Path, default=V10 / "final_test_panel.json")
    parser.add_argument("--quarantine", type=Path, default=V10 / "test_exposure_quarantine.json")
    parser.add_argument("--jsonl", type=Path, default=HERE / "terminal_test_games.jsonl")
    parser.add_argument("--summary", type=Path, default=HERE / "terminal_test_pairwise_summary.json")
    parser.add_argument("--preflight-report", type=Path, default=HERE / "terminal_test_preflight.json")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="after preflight, start/resume the one-time 24,000-game test matrix",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = preflight(
        args.registry,
        args.league_state,
        args.seed_manifest,
        args.frozen_panel,
        args.quarantine,
    )
    _atomic_json(args.preflight_report.expanduser().resolve(), report)
    if not args.execute:
        print(
            json.dumps(
                {
                    "preflight_report": str(args.preflight_report.expanduser().resolve()),
                    "passed": True,
                    "environment_games_started": False,
                    "next_step": "rerun with --execute only after explicit final-test authorization",
                },
                ensure_ascii=False,
            )
        )
        return 0
    command = [
        sys.executable,
        "-m",
        "kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate",
        "--registry",
        str(args.registry.expanduser().resolve()),
        "--seed-manifest",
        str(args.seed_manifest.expanduser().resolve()),
        "--models",
        *report["models"],
        "--split",
        "test",
        "--games-per-pair",
        "200",
        "--random-seed",
        "20260822",
        "--workers",
        str(int(args.workers)),
        "--jsonl",
        str(args.jsonl.expanduser().resolve()),
        "--output",
        str(args.summary.expanduser().resolve()),
        "--frozen-panel",
        str(args.frozen_panel.expanduser().resolve()),
        "--quarantine",
        str(args.quarantine.expanduser().resolve()),
        "--resume",
    ]
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
