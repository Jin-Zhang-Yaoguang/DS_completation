#!/usr/bin/env python3
"""训练并导出单位语义目标规则树。"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.tree import DecisionTreeClassifier


HERE = Path(__file__).resolve().parent
DATA = HERE / "unit_goal_data"


def load(split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    payload = np.load(DATA / f"{split}.npz")
    return payload["x"], payload["y"].astype(str), payload["meta"]


def prior_weights(labels: np.ndarray, manifest: dict, split: str, exponent: float) -> np.ndarray:
    saved = Counter(labels.tolist()); seen = manifest["counts"][split]["seen"]
    weights = np.asarray([(float(seen[label]) / max(1, saved[label])) ** exponent for label in labels], dtype=np.float64)
    return weights / weights.mean()


def weighted_accuracy(actual: np.ndarray, predicted: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(actual == predicted, weights=weights))


def export_tree(model: DecisionTreeClassifier, names: list[str]) -> dict:
    tree, classes = model.tree_, [str(value) for value in model.classes_]
    def node(index: int) -> dict:
        if tree.children_left[index] == tree.children_right[index]:
            values = np.asarray(tree.value[index][0], dtype=float)
            probabilities = values / max(1e-12, values.sum())
            order = np.argsort(probabilities)[::-1][:5]
            return {"leaf": classes[int(order[0])], "probabilities": {classes[int(i)]: float(probabilities[i]) for i in order if probabilities[i] > 0}}
        return {"feature": names[int(tree.feature[index])], "threshold": float(tree.threshold[index]),
                "left": node(int(tree.children_left[index])), "right": node(int(tree.children_right[index]))}
    return {"schema": "kaggriculture-unit-goal-rule-tree-v1", "classes": classes,
            "depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def main() -> int:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    names = list(manifest["feature_names"])
    x_train, y_train, _ = load("train"); x_dev, y_dev, _ = load("dev")
    dev_population_weights = prior_weights(y_dev, manifest, "dev", 1.0)
    trials = []
    best = None
    for exponent in (0.0, 0.5, 1.0):
        weights = prior_weights(y_train, manifest, "train", exponent)
        for depth in (16, 20, 24):
            for leaf in (20, 60):
                model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, random_state=1223)
                model.fit(x_train, y_train, sample_weight=weights)
                prediction = model.predict(x_dev)
                row = {
                    "prior_exponent": exponent, "depth": depth, "leaf": leaf,
                    "population_accuracy": weighted_accuracy(y_dev, prediction, dev_population_weights),
                    "sample_accuracy": float(np.mean(y_dev == prediction)),
                    "balanced_accuracy": float(balanced_accuracy_score(y_dev, prediction)),
                    "nodes": int(model.tree_.node_count),
                }
                # 人口准确率为主，同时要求稀有语义不完全坍缩。
                row["selection_score"] = row["population_accuracy"] + 0.20 * row["balanced_accuracy"] - 0.000002 * row["nodes"]
                trials.append(row)
                if best is None or row["selection_score"] > best[0]["selection_score"]:
                    best = (row, model, prediction)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    assert best is not None
    selected, model, prediction = best
    labels = [str(v) for v in model.classes_]
    matrix = confusion_matrix(y_dev, prediction, labels=labels)
    per_class = {}
    for index, label in enumerate(labels):
        support = int(matrix[index].sum())
        per_class[label] = {"support": support, "recall": float(matrix[index, index] / support) if support else 0.0,
                            "top_confusion": labels[int(np.argmax(np.where(np.arange(len(labels)) == index, -1, matrix[index])))] if support else None}
    tree = export_tree(model, names)
    (HERE / "unit_goal_router.json").write_text(json.dumps(tree, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "schema": "kaggriculture-unit-goal-router-training-v1", "idea": "predict semantic goal, never primitive move direction",
        "data": {"train": len(y_train), "dev": len(y_dev), "features": len(names), "classes": len(labels), "split": "episode_id"},
        "selected": selected, "per_class": per_class, "trials": trials,
        "serving": {"format": "pure JSON rule tree", "contains_replay_action_sequence": False, "step_lookup": False},
        "verdict": "DEVELOPMENT_COMPONENT_ONLY_NOT_MODEL_VERSION",
    }
    (HERE / "unit_goal_training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected": selected, "per_class": per_class}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
