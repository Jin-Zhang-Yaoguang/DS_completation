"""Small, deterministic drop-one ablation primitives."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import roc_auc_score


def _normalise_weights(weights: np.ndarray) -> np.ndarray:
    array = np.asarray(weights, dtype=np.float64)
    if array.ndim != 1 or np.any(array < 0.0) or not np.isfinite(array).all():
        raise ValueError("weights must be a finite non-negative vector")
    total = array.sum()
    if total <= 0.0:
        raise ValueError("at least one positive weight is required")
    return array / total


def drop_one_ablation(
    predictions: np.ndarray,
    target: np.ndarray,
    weights: np.ndarray,
    member_ids: Sequence[str],
    families: Sequence[str],
) -> dict[str, Any]:
    matrix = np.asarray(predictions, dtype=np.float64)
    labels = np.asarray(target)
    normalised = _normalise_weights(weights)
    if matrix.ndim != 2 or matrix.shape != (len(labels), len(normalised)):
        raise ValueError("prediction matrix, target and weights are not aligned")
    if len(member_ids) != matrix.shape[1] or len(families) != matrix.shape[1]:
        raise ValueError("member metadata is not aligned")
    baseline = float(roc_auc_score(labels, matrix @ normalised))

    member_rows = []
    for index, member_id in enumerate(member_ids):
        reduced = normalised.copy()
        reduced[index] = 0.0
        if reduced.sum() == 0.0:
            continue
        reduced /= reduced.sum()
        score = float(roc_auc_score(labels, matrix @ reduced))
        member_rows.append({"member": member_id, "auc": score, "delta_vs_full": score - baseline})

    groups: dict[str, list[int]] = defaultdict(list)
    for index, family in enumerate(families):
        groups[str(family)].append(index)
    family_rows = []
    for family, indices in sorted(groups.items()):
        reduced = normalised.copy()
        reduced[indices] = 0.0
        if reduced.sum() == 0.0:
            continue
        reduced /= reduced.sum()
        score = float(roc_auc_score(labels, matrix @ reduced))
        family_rows.append({"family": family, "auc": score, "delta_vs_full": score - baseline})
    return {"full_auc": baseline, "drop_one_member": member_rows, "drop_one_family": family_rows}

