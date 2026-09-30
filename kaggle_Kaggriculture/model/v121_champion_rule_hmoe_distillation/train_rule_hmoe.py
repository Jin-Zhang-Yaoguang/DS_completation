#!/usr/bin/env python3
"""训练可导出为纯规则节点的三层 HMoE；不保存任何教师动作。"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score, mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
MODEL_PATH = HERE / "rule_hmoe_model.json"
REPORT_PATH = HERE / "training_report.json"
EXPERTS = ("CAPACITY", "CROP", "LIVESTOCK", "LIQUIDATE")
FORBIDDEN = {"episode_id", "replay_sha256", "teacher", "submission_id", "seat", "seed", "future_shop"}
PROTOTYPE_KEYS = (
    "market_HIRE", "market_BUY_LAND", "market_BUY_SEED", "market_BUY_ANIMAL",
    "market_SELL", "unit_PLANT", "unit_WATER", "unit_FERTILIZE", "unit_BUILD_PASTURE",
    "unit_BUILD_COOP", "unit_FEED", "unit_CARE", "unit_HARVEST", "unit_PICKUP",
    "unit_PLACE", "mean_task_distance", "productive_per_move", "center_task_share",
    "center_livestock_share", "top_two_row_plant_share",
)


def read_jsonl(name: str) -> list[dict]:
    path = DATA / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def names(rows: list[dict]) -> list[str]:
    result = sorted({key for row in rows for key in row["features"]})
    bad = FORBIDDEN.intersection(result)
    if bad:
        raise ValueError(f"非法运行时特征: {sorted(bad)}")
    return result


def matrix(rows: list[dict], feature_names: list[str], extras: list[dict[str, float]] | None = None) -> np.ndarray:
    output = []
    for index, row in enumerate(rows):
        feature = dict(row["features"])
        if extras is not None:
            feature.update(extras[index])
        output.append([float(feature.get(key, 0.0)) for key in feature_names])
    return np.asarray(output, dtype=np.float64)


def sample_weights(rows: list[dict], labels: list[str]) -> np.ndarray:
    class_count = Counter(labels)
    teacher_count = Counter(str(row["teacher"]) for row in rows)
    n = len(rows)
    return np.asarray([
        n / (len(class_count) * class_count[label])
        * n / (len(teacher_count) * teacher_count[str(row["teacher"])])
        for row, label in zip(rows, labels)
    ], dtype=np.float64)


def classifier_oof(rows: list[dict], feature_names: list[str], depth: int, leaf: int,
                   extras: list[dict[str, float]] | None = None) -> tuple[float, list[str]]:
    x = matrix(rows, feature_names, extras)
    y = np.asarray([row["expert"] for row in rows])
    groups = np.asarray([int(row["episode_id"]) for row in rows])
    prediction = np.empty(len(rows), dtype=object)
    splitter = GroupKFold(n_splits=5)
    for train, valid in splitter.split(x, y, groups):
        model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, random_state=121, class_weight="balanced")
        model.fit(x[train], y[train], sample_weight=sample_weights([rows[i] for i in train], list(y[train])))
        prediction[valid] = model.predict(x[valid])
    return float(balanced_accuracy_score(y, prediction)), [str(value) for value in prediction]


def select_classifier(rows: list[dict], feature_names: list[str],
                      extras: list[dict[str, float]] | None = None) -> tuple[dict, list[str]]:
    candidates = []
    for depth in (2, 3, 4, 5, 6):
        for leaf in (4, 8, 12, 20):
            score, prediction = classifier_oof(rows, feature_names, depth, leaf, extras)
            candidates.append({"depth": depth, "leaf": leaf, "balanced_accuracy": score, "prediction": prediction})
    best = max(candidates, key=lambda item: (item["balanced_accuracy"], -item["depth"], item["leaf"]))
    compact = [{key: value for key, value in item.items() if key != "prediction"} for item in candidates]
    return {**{key: value for key, value in best.items() if key != "prediction"}, "candidates": compact}, best["prediction"]


def export_classifier(model: DecisionTreeClassifier, feature_names: list[str]) -> dict:
    tree = model.tree_
    classes = [str(value) for value in model.classes_]

    def node(index: int) -> dict:
        if tree.children_left[index] == tree.children_right[index]:
            counts = tree.value[index][0]
            return {"leaf": classes[int(np.argmax(counts))], "distribution": {classes[i]: float(value) for i, value in enumerate(counts)}}
        return {
            "feature": feature_names[int(tree.feature[index])],
            "threshold": float(tree.threshold[index]),
            "left": node(int(tree.children_left[index])),
            "right": node(int(tree.children_right[index])),
        }

    return {"kind": "classification_tree", "classes": classes, "depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def export_regressor(model: DecisionTreeRegressor, feature_names: list[str], targets: list[str]) -> dict:
    tree = model.tree_

    def node(index: int) -> dict:
        if tree.children_left[index] == tree.children_right[index]:
            values = np.asarray(tree.value[index]).reshape(-1)
            return {"value": {target: max(0.0, float(values[i])) for i, target in enumerate(targets)}}
        return {
            "feature": feature_names[int(tree.feature[index])],
            "threshold": float(tree.threshold[index]),
            "left": node(int(tree.children_left[index])),
            "right": node(int(tree.children_right[index])),
        }

    return {"kind": "regression_tree", "targets": targets, "depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def macro_mapping(rows: list[dict], prediction: list[str]) -> dict[tuple, str]:
    return {
        (int(row["episode_id"]), str(row["teacher"]), int(row["seat"]), int(row["decision_day"])): label
        for row, label in zip(rows, prediction)
    }


def parent_extras(daily: list[dict], mapping: dict[tuple, str]) -> list[dict[str, float]]:
    output = []
    for row in daily:
        key = (int(row["episode_id"]), str(row["teacher"]), int(row["seat"]), int(row["cycle_day"]))
        label = mapping[key]
        output.append({f"macro_{expert}": float(label == expert) for expert in EXPERTS})
    return output


def regression_oof(rows: list[dict], feature_names: list[str], targets: list[str], depth: int, leaf: int) -> dict:
    x = matrix(rows, feature_names)
    y = np.asarray([[float(row["target"].get(target, 0.0)) for target in targets] for row in rows], dtype=np.float64)
    groups = np.asarray([int(row["episode_id"]) for row in rows])
    prediction = np.zeros_like(y)
    baseline = np.zeros_like(y)
    splitter = GroupKFold(n_splits=5)
    for train, valid in splitter.split(x, y, groups):
        model = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=leaf, random_state=121, criterion="squared_error")
        model.fit(x[train], y[train])
        prediction[valid] = model.predict(x[valid])
        baseline[valid] = y[train].mean(axis=0)
    return {
        "depth": depth,
        "leaf": leaf,
        "rmse": float(mean_squared_error(y, prediction) ** 0.5),
        "mean_baseline_rmse": float(mean_squared_error(y, baseline) ** 0.5),
    }


def prototypes(rows: list[dict]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["expert"])].append(row["target"])
    output = {}
    for expert, targets in sorted(grouped.items()):
        output[expert] = {
            key: float(np.median([float(target.get(key, 0.0)) for target in targets]))
            for key in PROTOTYPE_KEYS
        }
    return output


def main() -> int:
    macro = read_jsonl("macro_3day.jsonl")
    daily = read_jsonl("daily_contract.jsonl")
    global_rows = read_jsonl("global_market.jsonl")

    macro_names = names(macro)
    macro_selection, macro_oof = select_classifier(macro, macro_names)
    macro_map = macro_mapping(macro, macro_oof)
    daily_extra = parent_extras(daily, macro_map)
    daily_names = sorted(set(names(daily)) | {f"macro_{expert}" for expert in EXPERTS})
    daily_selection, daily_oof = select_classifier(daily, daily_names, daily_extra)

    macro_y = [str(row["expert"]) for row in macro]
    macro_model = DecisionTreeClassifier(
        max_depth=int(macro_selection["depth"]), min_samples_leaf=int(macro_selection["leaf"]),
        random_state=121, class_weight="balanced",
    ).fit(matrix(macro, macro_names), macro_y, sample_weight=sample_weights(macro, macro_y))
    daily_y = [str(row["expert"]) for row in daily]
    daily_model = DecisionTreeClassifier(
        max_depth=int(daily_selection["depth"]), min_samples_leaf=int(daily_selection["leaf"]),
        random_state=121, class_weight="balanced",
    ).fit(matrix(daily, daily_names, daily_extra), daily_y, sample_weight=sample_weights(daily, daily_y))

    global_names = names(global_rows)
    global_targets = sorted({key for row in global_rows for key in row["target"]})
    reg_candidates = [
        regression_oof(global_rows, global_names, global_targets, depth, leaf)
        for depth in (2, 3, 4, 5) for leaf in (8, 16, 24)
    ]
    reg_best = min(reg_candidates, key=lambda item: (item["rmse"], item["depth"], -item["leaf"]))
    x_global = matrix(global_rows, global_names)
    y_global = np.asarray([[float(row["target"].get(target, 0.0)) for target in global_targets] for row in global_rows])
    global_model = DecisionTreeRegressor(
        max_depth=int(reg_best["depth"]), min_samples_leaf=int(reg_best["leaf"]), random_state=121,
    ).fit(x_global, y_global)

    model = {
        "schema": "kaggriculture-v121-rule-hmoe-v1",
        "status": "RESEARCH_ONLY_NOT_DEPLOYABLE",
        "runtime_contract": {
            "forbidden_fields": sorted(FORBIDDEN),
            "tape": False,
            "step_action_lookup": False,
            "primary_action_source": "learned_state_contract",
        },
        "macro_router": export_classifier(macro_model, macro_names),
        "daily_router": export_classifier(daily_model, daily_names),
        "global_market": export_regressor(global_model, global_names, global_targets),
        "expert_contract_prototypes": prototypes(daily),
    }
    MODEL_PATH.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "schema": "kaggriculture-v121-rule-hmoe-training-report-v1",
        "data": {"episodes": len({row["episode_id"] for row in daily}), "teacher_trajectories": len(daily) // 30, "group_split": "5-fold episode_id"},
        "macro_router": {"selected": {key: value for key, value in macro_selection.items() if key != "candidates"}, "majority_accuracy": max(Counter(macro_y).values()) / len(macro_y), "tree_depth": int(macro_model.tree_.max_depth), "tree_nodes": int(macro_model.tree_.node_count)},
        "daily_router": {"selected": {key: value for key, value in daily_selection.items() if key != "candidates"}, "majority_accuracy": max(Counter(daily_y).values()) / len(daily_y), "tree_depth": int(daily_model.tree_.max_depth), "tree_nodes": int(daily_model.tree_.node_count), "parent_signal": "OOF macro prediction"},
        "global_market": {"selected": reg_best, "beats_group_mean": reg_best["rmse"] < reg_best["mean_baseline_rmse"], "tree_depth": int(global_model.tree_.max_depth), "tree_nodes": int(global_model.tree_.node_count)},
        "tape_audit_required": True,
        "promotion_gate": {
            "macro_balanced_accuracy_min": 0.55,
            "daily_balanced_accuracy_min": 0.55,
            "global_beats_group_mean": True,
            "offline_signal_pass": bool(macro_selection["balanced_accuracy"] >= 0.55 and daily_selection["balanced_accuracy"] >= 0.55 and reg_best["rmse"] < reg_best["mean_baseline_rmse"]),
            "closed_loop_required": True,
        },
        "verdict": "RESEARCH_SIGNAL_ONLY_NOT_PROMOTABLE",
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

