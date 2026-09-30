#!/usr/bin/env python3
"""Grouped OOF shallow-tree audit for V106 tail-risk state support."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np
from sklearn.metrics import balanced_accuracy_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.tree import DecisionTreeClassifier, export_text

HERE = Path(__file__).resolve().parent


def main():
    data = json.loads((HERE / "risk_probe_data.json").read_text())
    rows = data["rows"]
    reports = {}
    for checkpoint in data["checkpoints"]:
        snapshots = [row["snapshots"][str(checkpoint)] for row in rows]
        names = sorted(snapshots[0])
        x = np.asarray([[snapshot[name] for name in names] for snapshot in snapshots], dtype=float)
        y = np.asarray([int(row["catastrophic"]) for row in rows], dtype=int)
        groups = np.asarray([row["seed"] for row in rows])
        tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=24, class_weight="balanced", random_state=106)
        pred = cross_val_predict(tree, x, y, groups=groups, cv=GroupKFold(6), method="predict")
        tree.fit(x, y)
        report = {
            "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "predicted_positive_rate": float(pred.mean()),
            "positive_count": int(y.sum()),
            "tree": export_text(tree, feature_names=names),
            "feature_names": names,
        }
        report["passes_gate"] = report["balanced_accuracy"] >= 0.75 and report["precision"] >= 0.50 and report["recall"] >= 0.70
        reports[str(checkpoint)] = report
    qualified = [int(step) for step, report in reports.items() if report["passes_gate"]]
    payload = {"schema": "kaggriculture-v106-risk-learnability-v1", "status": "PASS_RISK_LEARNABILITY" if qualified else "REJECT_RISK_LEARNABILITY", "strategy_proof": False, "games": len(rows), "base_catastrophic_rate": statistics.mean(row["catastrophic"] for row in rows), "qualified_checkpoints": qualified, "reports": reports}
    (HERE / "risk_learnability_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
