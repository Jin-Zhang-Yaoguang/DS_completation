"""Small dependency-free regression tree for delayed expert routing."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def router_features_from_encoded(encoded) -> np.ndarray:
    global_features = np.asarray(encoded["global"], dtype=np.float32).reshape(-1)
    board = np.asarray(encoded["board"], dtype=np.float32)
    units = np.asarray(encoded["units"], dtype=np.float32)
    unit_mask = np.asarray(encoded["unit_mask"], dtype=np.float32).reshape(-1)
    board_counts = board.sum(axis=(1, 2)).reshape(-1)
    unit_base = (units[:, :16] * unit_mask[:, None]).sum(axis=0)
    return np.concatenate((global_features, board_counts, unit_base)).astype(np.float32)


def _sse(y: np.ndarray) -> float:
    if len(y) == 0:
        return 0.0
    return float(np.square(y - y.mean(axis=0, keepdims=True)).sum())


def fit_regression_tree(
    x: np.ndarray, y: np.ndarray, max_depth: int = 3,
    min_leaf: int = 3, max_thresholds: int = 32,
):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
        raise ValueError("x and y must be aligned rank-2 arrays")
    if len(x) < min_leaf:
        raise ValueError("not enough rows for min_leaf")

    def build(indices: np.ndarray, depth: int):
        values = y[indices]
        leaf = {"type": "leaf", "n": int(len(indices)), "value": values.mean(axis=0).tolist()}
        if depth >= max_depth or len(indices) < 2 * min_leaf:
            return leaf
        parent_loss = _sse(values)
        best = None
        for feature in range(x.shape[1]):
            unique = np.unique(x[indices, feature])
            if len(unique) < 2:
                continue
            thresholds = (unique[:-1] + unique[1:]) / 2.0
            if len(thresholds) > max_thresholds:
                positions = np.linspace(0, len(thresholds) - 1, max_thresholds).round().astype(int)
                thresholds = thresholds[np.unique(positions)]
            for threshold in thresholds:
                left = indices[x[indices, feature] <= threshold]
                right = indices[x[indices, feature] > threshold]
                if len(left) < min_leaf or len(right) < min_leaf:
                    continue
                loss = _sse(y[left]) + _sse(y[right])
                gain = parent_loss - loss
                if best is None or gain > best[0] + 1e-9:
                    best = (gain, feature, float(threshold), left, right)
        if best is None or best[0] <= 1e-9:
            return leaf
        gain, feature, threshold, left, right = best
        return {
            "type": "split", "n": int(len(indices)), "feature": int(feature),
            "threshold": threshold, "gain": float(gain),
            "left": build(left, depth + 1), "right": build(right, depth + 1),
        }

    return build(np.arange(len(x)), 0)


def predict_tree(tree, features: np.ndarray) -> np.ndarray:
    node = tree
    features = np.asarray(features, dtype=np.float64).reshape(-1)
    while node["type"] == "split":
        node = node["left"] if features[node["feature"]] <= node["threshold"] else node["right"]
    return np.asarray(node["value"], dtype=np.float64)


def load_router(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
