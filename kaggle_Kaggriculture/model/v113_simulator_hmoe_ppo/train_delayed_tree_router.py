"""Fit a shallow delayed Router from aligned counterfactual expert reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import numpy as np

from delayed_tree_router import fit_regression_tree, predict_tree, router_features_from_encoded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--combo", nargs="+", required=True, help="labels such as 3:2")
    parser.add_argument("--metric", choices=("candidate_reward", "margin"), required=True)
    parser.add_argument("--router-step", type=int, default=72)
    parser.add_argument("--reset-step", type=int)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--min-leaf", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.input) != len(args.combo):
        parser.error("--input and --combo must have equal length")
    combos = [tuple(int(part) for part in value.split(":")) for value in args.combo]
    if any(len(combo) != 2 for combo in combos):
        parser.error("each --combo must look like unit:market")

    snapshot_report = json.loads(args.snapshots.read_text(encoding="utf-8"))
    snapshot_rows = {
        (int(row["seed"]), int(row["seat"])): row for row in snapshot_report["rows"]
    }
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.input]
    indexed = [{
        (int(row["seed"]), int(row["seat"])): row for row in report["rows"]
    } for report in reports]
    keys = sorted(snapshot_rows)
    if any(set(rows) != set(keys) for rows in indexed):
        raise ValueError("counterfactual reports do not match snapshot seed/seat panel")
    if any(snapshot_rows[key].get("router_snapshot") is None for key in keys):
        raise ValueError("snapshot report is missing captured Router states")
    x = np.stack([
        router_features_from_encoded(snapshot_rows[key]["router_snapshot"])
        for key in keys
    ])
    y = np.stack([[float(rows[key][args.metric]) for rows in indexed] for key in keys])
    tree = fit_regression_tree(x, y, args.max_depth, args.min_leaf)
    predicted = np.stack([predict_tree(tree, row) for row in x])
    selected = predicted.argmax(axis=1)
    oracle = y.max(axis=1)
    achieved = y[np.arange(len(y)), selected]
    fixed_means = y.mean(axis=0)
    best_fixed = int(fixed_means.argmax())
    result = {
        "schema": "kaggriculture-v113-delayed-tree-router-v1",
        "router_step": args.router_step, "reset_step": args.reset_step,
        "base_combo": [3, 2],
        "combos": [list(combo) for combo in combos], "metric": args.metric,
        "feature_dimension": int(x.shape[1]), "rows": len(keys),
        "seed_seats": [list(key) for key in keys],
        "max_depth": args.max_depth, "min_leaf": args.min_leaf,
        "train_best_fixed_mean": float(fixed_means[best_fixed]),
        "train_router_mean": float(achieved.mean()),
        "train_oracle_mean": float(oracle.mean()),
        "train_router_gain_over_best_fixed": float((achieved - y[:, best_fixed]).mean()),
        "tree": tree,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as sink:
        json.dump(result, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps({key: result[key] for key in (
        "metric", "rows", "feature_dimension", "train_best_fixed_mean",
        "train_router_mean", "train_oracle_mean", "train_router_gain_over_best_fixed",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
