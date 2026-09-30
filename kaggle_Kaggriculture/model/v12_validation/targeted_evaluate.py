"""Run only the 23 pre-registered formal pairs (4,600 closed-loop games)."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from kaggle_Kaggriculture.model.v12_validation.protocol import (
    expected_tasks,
    preflight,
    read_config,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10


HERE = Path(__file__).resolve().parent


def require_formal_execution_flag(execute_formal: bool) -> None:
    """Fail before preflight/task construction unless execution is deliberate."""

    if execute_formal is not True:
        raise PermissionError(
            "formal execution is locked; independent red-team review must finish, "
            "then pass --execute-formal explicitly"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=HERE / "frozen_v5" / "validation_config.json"
    )
    parser.add_argument(
        "--jsonl", type=Path, default=HERE / "runs_v5" / "formal" / "games.jsonl"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "runs_v5" / "formal" / "collection_summary.json",
    )
    parser.add_argument(
        "--execute-formal",
        action="store_true",
        help="required deliberate authorization after independent red-team review",
    )
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    require_formal_execution_flag(args.execute_formal)
    preflight_report = preflight(args.config)
    if preflight_report.get("passed") is not True:
        raise ValueError("formal preflight did not pass")
    config = read_config(args.config)

    fingerprint, tasks, panel = expected_tasks(config)
    rows = v10.run_tasks(tasks, args.jsonl, args.workers, args.resume)
    valid = [
        row
        for row in rows
        if row.get("run_fingerprint") == fingerprint
        and row.get("error") is None
        and row.get("done") is True
    ]
    payload = {
        "schema": "kaggriculture-v12-targeted-collection-summary-1",
        "config": str(args.config.resolve()),
        "run_fingerprint": fingerprint,
        "scheduled_tasks": len(tasks),
        "physical_rows": len(rows),
        "valid_rows_for_current_fingerprint": len(valid),
        "pairs": len({row["pair_id"] for row in tasks}),
        "panel_sources": len(panel),
        "status_counts": dict(
            Counter("/".join(str(value) for value in (row.get("statuses") or [])) for row in valid)
        ),
        "preflight": preflight_report,
        "formal_execution_flag": True,
        "old_screen_gate_dependency": False,
        "note": "effect claims require audit_results.py; this is collection status only",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
