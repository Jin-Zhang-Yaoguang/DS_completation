#!/usr/bin/env python3
"""为每种单位语义目标训练目标格规则树。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.tree import DecisionTreeClassifier


HERE = Path(__file__).resolve().parent
DATA = HERE / "unit_goal_data"


def load(split: str):
    payload = np.load(DATA / f"{split}.npz")
    return payload["x"], payload["y"].astype(str), payload["meta"]


def distance(actual: np.ndarray, predicted: np.ndarray) -> float:
    def point(value: str) -> tuple[int, int]:
        x, y = value.split(","); return int(x), int(y)
    return float(np.mean([abs(point(a)[0]-point(p)[0]) + abs(point(a)[1]-point(p)[1]) for a, p in zip(actual, predicted)]))


def export_tree(model: DecisionTreeClassifier, names: list[str]) -> dict:
    tree, classes = model.tree_, [str(v) for v in model.classes_]
    def node(index: int) -> dict:
        if tree.children_left[index] == tree.children_right[index]:
            values = np.asarray(tree.value[index][0], dtype=float); values /= max(1e-12, values.sum())
            order = np.argsort(values)[::-1][:12]
            return {"leaf": classes[int(order[0])], "probabilities": {classes[int(i)]: float(values[i]) for i in order if values[i] > 0}}
        return {"feature": names[int(tree.feature[index])], "threshold": float(tree.threshold[index]),
                "left": node(int(tree.children_left[index])), "right": node(int(tree.children_right[index]))}
    return {"depth": int(tree.max_depth), "nodes": int(tree.node_count), "classes": classes, "root": node(0)}


def main() -> int:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8")); names = list(manifest["feature_names"])
    x_train, goal_train, meta_train = load("train"); x_dev, goal_dev, meta_dev = load("dev")
    routers, reports = {}, {}
    for goal in sorted(set(goal_train) - {"IDLE"}):
        train_mask, dev_mask = goal_train == goal, goal_dev == goal
        if train_mask.sum() < 80 or dev_mask.sum() < 30:
            reports[goal] = {"status": "insufficient", "train": int(train_mask.sum()), "dev": int(dev_mask.sum())}; continue
        y_train = np.asarray([f"{x},{y}" for x, y in meta_train[train_mask][:, 4:6]], dtype=str)
        y_dev = np.asarray([f"{x},{y}" for x, y in meta_dev[dev_mask][:, 4:6]], dtype=str)
        trials = []; best = None
        for depth in (10, 14, 18):
            for leaf in (10, 30, 80):
                model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, random_state=1224)
                model.fit(x_train[train_mask], y_train)
                prediction = model.predict(x_dev[dev_mask])
                row = {"depth": depth, "leaf": leaf, "accuracy": float(np.mean(prediction == y_dev)),
                       "mean_manhattan": distance(y_dev, prediction), "nodes": int(model.tree_.node_count)}
                row["score"] = row["accuracy"] - 0.025 * row["mean_manhattan"] - 0.000002 * row["nodes"]
                trials.append(row)
                if best is None or row["score"] > best[0]["score"]: best = (row, model)
        assert best is not None
        selected, model = best; routers[goal] = export_tree(model, names)
        reports[goal] = {"status": "trained", "train": int(train_mask.sum()), "dev": int(dev_mask.sum()), "locations": len(model.classes_), "selected": selected, "trials": trials}
        print(json.dumps({"goal": goal, **reports[goal]}, ensure_ascii=False), flush=True)
    payload = {"schema": "kaggriculture-goal-target-rule-trees-v1", "feature_names": names, "routers": routers,
               "contains_move_sequence": False, "status": "DEVELOPMENT_COMPONENT_ONLY_NOT_MODEL_VERSION"}
    (HERE / "goal_target_routers.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    report = {"schema": "kaggriculture-goal-target-training-report-v1", "goals_trained": len(routers), "reports": reports,
              "verdict": "DEVELOPMENT_COMPONENT_ONLY_NOT_MODEL_VERSION"}
    (HERE / "goal_target_training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
