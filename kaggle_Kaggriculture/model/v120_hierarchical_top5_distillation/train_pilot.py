#!/usr/bin/env python3
"""训练三层可解释 pilot；模型只用于验证分层信号，不用于提交。"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
MODEL_OUT = HERE / "pilot_model.json"
REPORT_OUT = HERE / "pilot_training_report.json"
# 三局覆盖全部五位 teacher，且所有 turn 严格跟随 episode 分组。
DEV_EPISODES = {104535318, 104543983, 104546522}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def feature_names(rows: list[dict]) -> list[str]:
    return sorted({key for row in rows for key in row["features"]})


def matrix(rows: list[dict], names: list[str], extras: list[dict[str, float]] | None = None) -> np.ndarray:
    values = []
    for index, row in enumerate(rows):
        feature = dict(row["features"])
        if extras is not None:
            feature.update(extras[index])
        values.append([float(feature.get(name, 0.0)) for name in names])
    return np.asarray(values, dtype=np.float64)


def normalize_fit(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-9] = 1.0
    return (x - mean) / scale, mean, scale


def centroid_fit(x: np.ndarray, labels: list[str]) -> tuple[list[str], np.ndarray]:
    classes = sorted(set(labels))
    centroids = np.stack([x[np.asarray(labels) == label].mean(axis=0) for label in classes])
    return classes, centroids


def centroid_predict(x: np.ndarray, classes: list[str], centroids: np.ndarray) -> list[str]:
    distance = ((x[:, None, :] - centroids[None, :, :]) ** 2).mean(axis=2)
    return [classes[index] for index in distance.argmin(axis=1)]


def classification_metrics(y: list[str], prediction: list[str], train_labels: list[str]) -> dict:
    majority = Counter(train_labels).most_common(1)[0][0]
    labels = sorted(set(y) | set(prediction))
    per_class = {}
    for label in labels:
        indices = [index for index, value in enumerate(y) if value == label]
        per_class[label] = sum(prediction[index] == label for index in indices) / len(indices) if indices else None
    present_recalls = [value for value in per_class.values() if value is not None]
    majority_per_class = []
    for label in labels:
        indices = [index for index, value in enumerate(y) if value == label]
        if indices:
            majority_per_class.append(float(label == majority))
    return {
        "rows": len(y),
        "accuracy": sum(a == b for a, b in zip(y, prediction)) / len(y),
        "majority_baseline_accuracy": sum(value == majority for value in y) / len(y),
        "majority_label": majority,
        "balanced_accuracy": sum(present_recalls) / len(present_recalls),
        "majority_balanced_accuracy": sum(majority_per_class) / len(majority_per_class),
        "per_class_recall": per_class,
    }


def split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    train = [row for row in rows if int(row["episode_id"]) not in DEV_EPISODES]
    dev = [row for row in rows if int(row["episode_id"]) in DEV_EPISODES]
    if {int(row["episode_id"]) for row in train} & {int(row["episode_id"]) for row in dev}:
        raise AssertionError("episode split 泄漏")
    return train, dev


def key(row: dict, cycle: bool = False) -> tuple:
    day = int(row["decision_day"])
    if cycle:
        day -= day % 3
    return int(row["episode_id"]), str(row["teacher"]), int(row["seat"]), day


def one_hot(label: str, labels: list[str], prefix: str) -> dict[str, float]:
    return {f"{prefix}_{value}": float(value == label) for value in labels}


def main() -> int:
    shop_rows = read_jsonl(DATA / "shop_refresh.jsonl")
    day_rows = read_jsonl(DATA / "daily_movement.jsonl")
    global_rows = read_jsonl(DATA / "global_strategy.jsonl")
    shop_train, shop_dev = split(shop_rows)
    day_train, day_dev = split(day_rows)
    global_train, global_dev = split(global_rows)

    # 第一层：72-turn 商店刷新 option。
    shop_names = feature_names(shop_rows)
    x_shop_train_raw = matrix(shop_train, shop_names)
    x_shop_train, shop_mean, shop_scale = normalize_fit(x_shop_train_raw)
    shop_classes, shop_centroids = centroid_fit(x_shop_train, [row["option"] for row in shop_train])
    x_shop_dev = (matrix(shop_dev, shop_names) - shop_mean) / shop_scale
    shop_dev_pred = centroid_predict(x_shop_dev, shop_classes, shop_centroids)
    shop_metrics = classification_metrics([row["option"] for row in shop_dev], shop_dev_pred, [row["option"] for row in shop_train])
    shop_train_option = {key(row): row["option"] for row in shop_train}
    shop_dev_option = {key(row): pred for row, pred in zip(shop_dev, shop_dev_pred)}

    # 第二层：日级移动 option；train 使用 teacher forcing，dev 只接第一层预测。
    day_train_extra = [one_hot(shop_train_option[key(row, cycle=True)], shop_classes, "parent_shop") for row in day_train]
    day_dev_extra = [one_hot(shop_dev_option[key(row, cycle=True)], shop_classes, "parent_shop") for row in day_dev]
    day_names = sorted(set(feature_names(day_rows)) | {name for item in day_train_extra for name in item})
    x_day_train_raw = matrix(day_train, day_names, day_train_extra)
    x_day_train, day_mean, day_scale = normalize_fit(x_day_train_raw)
    day_classes, day_centroids = centroid_fit(x_day_train, [row["option"] for row in day_train])
    x_day_dev = (matrix(day_dev, day_names, day_dev_extra) - day_mean) / day_scale
    day_dev_pred = centroid_predict(x_day_dev, day_classes, day_centroids)
    day_metrics = classification_metrics([row["option"] for row in day_dev], day_dev_pred, [row["option"] for row in day_train])
    day_train_option = {key(row): row["option"] for row in day_train}
    day_dev_option = {key(row): pred for row, pred in zip(day_dev, day_dev_pred)}

    # 第三层：组合前两层 option，预测提前卖出与对手下一日供给。
    global_target_names = sorted({name for row in global_rows for name in row["target"]})
    global_train_extra = []
    for row in global_train:
        extra = one_hot(shop_train_option[key(row, cycle=True)], shop_classes, "shop")
        extra.update(one_hot(day_train_option[key(row)], day_classes, "day"))
        global_train_extra.append(extra)
    global_dev_extra = []
    for row in global_dev:
        extra = one_hot(shop_dev_option[key(row, cycle=True)], shop_classes, "shop")
        extra.update(one_hot(day_dev_option[key(row)], day_classes, "day"))
        global_dev_extra.append(extra)
    global_names = sorted(set(feature_names(global_rows)) | {name for item in global_train_extra for name in item})
    x_global_train_raw = matrix(global_train, global_names, global_train_extra)
    x_global_train, global_mean, global_scale = normalize_fit(x_global_train_raw)
    y_global_train = np.asarray([[row["target"].get(name, 0.0) for name in global_target_names] for row in global_train])
    y_mean = y_global_train.mean(axis=0)
    design = np.column_stack([np.ones(len(x_global_train)), x_global_train])
    alpha = 10.0
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    weights = np.linalg.solve(design.T @ design + penalty, design.T @ y_global_train)
    x_global_dev = (matrix(global_dev, global_names, global_dev_extra) - global_mean) / global_scale
    prediction = np.column_stack([np.ones(len(x_global_dev)), x_global_dev]) @ weights
    y_global_dev = np.asarray([[row["target"].get(name, 0.0) for name in global_target_names] for row in global_dev])
    rmse = float(np.sqrt(np.mean((prediction - y_global_dev) ** 2)))
    mean_baseline_rmse = float(np.sqrt(np.mean((y_mean[None, :] - y_global_dev) ** 2)))

    model = {
        "schema": "kaggriculture-v120-three-layer-pilot-model-v1",
        "status": "NOT_DEPLOYABLE",
        "shop": {"features": shop_names, "mean": shop_mean.tolist(), "scale": shop_scale.tolist(), "classes": shop_classes, "centroids": shop_centroids.tolist()},
        "day": {"features": day_names, "mean": day_mean.tolist(), "scale": day_scale.tolist(), "classes": day_classes, "centroids": day_centroids.tolist()},
        "global": {"features": global_names, "mean": global_mean.tolist(), "scale": global_scale.tolist(), "targets": global_target_names, "ridge_alpha": alpha, "weights": weights.tolist()},
    }
    MODEL_OUT.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema": "kaggriculture-v120-three-layer-pilot-training-report-v1",
        "split": {"unit": "episode_id", "dev_episode_ids": sorted(DEV_EPISODES), "train_episode_ids": sorted({int(row["episode_id"]) for row in shop_train}), "leakage": False},
        "shop_refresh": shop_metrics,
        "daily_movement": day_metrics,
        "global_strategy": {"rows": len(global_dev), "rmse": rmse, "train_mean_baseline_rmse": mean_baseline_rmse, "beats_mean_baseline": rmse < mean_baseline_rmse},
        "gate": {
            "shop_macro_signal": shop_metrics["balanced_accuracy"] > shop_metrics["majority_balanced_accuracy"],
            "day_macro_signal": day_metrics["balanced_accuracy"] > day_metrics["majority_balanced_accuracy"],
            "global_beats_mean": rmse < mean_baseline_rmse,
        },
        "verdict": "PILOT_SIGNAL_ONLY_NOT_DEPLOYABLE",
    }
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
