#!/usr/bin/env python3
"""Run the standalone V11 6-seed x 2-seat candidate admission gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .strategy_optimizer import run_admission_smoke
except ImportError:
    from strategy_optimizer import run_admission_smoke


def _sources(path: Path, count: int = 6) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            split = str(row.get("split", "")).lower()
            split = "validation" if split == "val" else split
            if split not in {"train", "validation"}:
                continue
            date = str(row.get("date") or row.get("source_date") or "")[:10]
            by_date.setdefault(date, []).append(dict(row))
    dates = ("2026-08-18", "2026-08-19", "2026-08-20")
    rows = []
    base, extra = divmod(int(count), len(dates))
    for index, date in enumerate(dates):
        quota = base + int(index < extra)
        rows.extend(by_date.get(date, [])[:quota])
    if len(rows) < count:
        raise ValueError(f"need {count} date-stratified non-test source rows")
    return rows


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--parent", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--mutation", required=True)
    parser.add_argument("--params-json", default="{}")
    parser.add_argument("--round", type=int, required=True, dest="source_round")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = run_admission_smoke(
        input_registry=args.registry.expanduser().resolve(),
        smoke_registry=args.output.with_name(args.output.stem + "_registry.json").resolve(),
        candidate_id=args.candidate_id,
        parent_id=args.parent,
        mutation_name=args.mutation,
        mutation_params=json.loads(args.params_json),
        sources=_sources(args.source_manifest.expanduser().resolve()),
        source_round=args.source_round,
        workers=args.workers,
    )
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "passed": report["passed"],
                "changed_games": report["changed_games"],
                "changed_steps": report["action_difference_steps"],
                "market": report["market_changed_steps"],
                "farmer": report["farmer_changed_steps"],
                "hands": report["hands_changed_steps"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
