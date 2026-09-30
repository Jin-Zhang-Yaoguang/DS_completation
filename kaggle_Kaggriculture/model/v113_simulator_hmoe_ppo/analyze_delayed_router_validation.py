"""Compare a learned delayed Router with aligned fixed expert schedules."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

import numpy as np

from analyze_expert_grid import bootstrap_ci


def wtl(values: np.ndarray) -> list[int]:
    return [int((values > 0).sum()), int((values == 0).sum()), int((values < 0).sum())]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--router", type=Path, required=True)
    parser.add_argument("--grid", type=Path, nargs="+", required=True)
    parser.add_argument("--label", nargs="+", required=True)
    parser.add_argument("--base-label", default="U3M2")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11323)
    args = parser.parse_args()
    if len(args.grid) != len(args.label):
        parser.error("--grid and --label must have equal length")
    router_report = json.loads(args.router.read_text(encoding="utf-8"))
    grid_reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.grid]
    router_rows = {
        (int(row["seed"]), int(row["seat"])): row for row in router_report["rows"]
    }
    grid_rows = [{
        (int(row["seed"]), int(row["seat"])): row for row in report["rows"]
    } for report in grid_reports]
    keys = sorted(router_rows)
    if any(set(rows) != set(keys) for rows in grid_rows):
        raise ValueError("Router and fixed reports do not share an identical panel")
    base_index = args.label.index(args.base_label)
    metrics = {}
    for metric_index, metric in enumerate(("candidate_reward", "margin")):
        router = np.asarray([float(router_rows[key][metric]) for key in keys])
        grid = np.asarray([
            [float(rows[key][metric]) for key in keys] for rows in grid_rows
        ])
        fixed_means = grid.mean(axis=1)
        best_index = int(fixed_means.argmax())
        oracle = grid.max(axis=0)
        versus_base = router - grid[base_index]
        versus_best = router - grid[best_index]
        metrics[metric] = {
            "router_mean": float(router.mean()),
            "fixed_mean": dict(zip(args.label, map(float, fixed_means))),
            "best_fixed": args.label[best_index],
            "best_fixed_mean": float(fixed_means[best_index]),
            "router_gain_vs_base_mean": float(versus_base.mean()),
            "router_gain_vs_base_ci95": bootstrap_ci(versus_base, args.seed + metric_index * 3),
            "router_gain_vs_base_wtl": wtl(versus_base),
            "router_gain_vs_best_fixed_mean": float(versus_best.mean()),
            "router_gain_vs_best_fixed_ci95": bootstrap_ci(versus_best, args.seed + metric_index * 3 + 1),
            "router_gain_vs_best_fixed_wtl": wtl(versus_best),
            "oracle_mean": float(oracle.mean()),
            "oracle_gap_from_router_mean": float((oracle - router).mean()),
        }
    result = {
        "schema": "kaggriculture-v113-delayed-router-validation-v1",
        "router": str(args.router), "rows": len(keys),
        "done_done": sum(
            row["error"] is None and row["statuses"] == ["DONE", "DONE"]
            for row in router_rows.values()
        ),
        "router_score_rate": float(np.mean([router_rows[key]["score"] for key in keys])),
        "selection_counts": dict(Counter(
            f"U{row['selected_combo'][0]}M{row['selected_combo'][1]}"
            for row in router_rows.values()
        )),
        "metrics": metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as sink:
        json.dump(result, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
