"""Training-block-only candidate compression and blend selectors."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score


RIDGE_GRID = (1e-4, 1e-3, 1e-2)
WEIGHT_CAP_GRID = (0.25, 0.50)
MAX_GREEDY_MEMBERS = 12
GREEDY_MIN_DELTA = 0.00002


def _validate_training_data(predictions: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.asarray(predictions, dtype=np.float64)
    labels = np.asarray(target)
    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("predictions must be a non-empty 2D matrix")
    if labels.ndim != 1 or len(labels) != len(matrix):
        raise ValueError("target must be one-dimensional and row-aligned")
    if not np.isfinite(matrix).all():
        raise ValueError("predictions contain NaN or Inf")
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("target must contain both binary classes")
    return matrix, labels


def spearman_correlation(predictions: np.ndarray) -> np.ndarray:
    matrix = np.asarray(predictions, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("predictions must be a non-empty 2D matrix")
    ranks = np.column_stack([rankdata(matrix[:, i], method="average") for i in range(matrix.shape[1])])
    if matrix.shape[1] == 1:
        return np.ones((1, 1), dtype=np.float64)
    correlation = np.corrcoef(ranks, rowvar=False)
    return np.nan_to_num(correlation, nan=0.0)


def correlation_clusters(
    predictions: np.ndarray,
    metadata: Sequence[Mapping[str, Any]],
    threshold: float = 0.999,
) -> list[dict[str, Any]]:
    """Cluster only within an identical family/mechanism/split lineage group."""

    matrix = np.asarray(predictions)
    if matrix.ndim != 2 or matrix.shape[1] != len(metadata):
        raise ValueError("metadata must have exactly one record per prediction column")
    correlation = spearman_correlation(matrix)
    groups: dict[tuple[Any, Any, Any], list[int]] = defaultdict(list)
    for index, item in enumerate(metadata):
        groups[(item.get("family"), item.get("feature_mechanism"), item.get("split_seed"))].append(index)

    clusters: list[dict[str, Any]] = []
    for group_key, indices in sorted(groups.items(), key=lambda item: str(item[0])):
        unseen = set(indices)
        while unseen:
            start = min(unseen)
            component = {start}
            pending = [start]
            unseen.remove(start)
            while pending:
                current = pending.pop()
                linked = {
                    other
                    for other in list(unseen)
                    if correlation[current, other] >= threshold
                }
                unseen.difference_update(linked)
                component.update(linked)
                pending.extend(linked)
            members = sorted(component)
            mean_corr = {
                index: float(np.mean([correlation[index, other] for other in members if other != index]))
                if len(members) > 1
                else 0.0
                for index in members
            }
            highest = max(members, key=lambda i: (float(metadata[i].get("oof_auc", -np.inf)), -i))
            diverse = min(members, key=lambda i: (mean_corr[i], i))
            latest = max(members, key=lambda i: (int(metadata[i].get("cycle_index") or -1), -i))
            representatives = []
            for index in (highest, diverse, latest):
                if index not in representatives:
                    representatives.append(index)
            clusters.append(
                {
                    "group": {
                        "family": group_key[0],
                        "feature_mechanism": group_key[1],
                        "split_seed": group_key[2],
                    },
                    "member_indices": members,
                    "member_ids": [str(metadata[index]["id"]) for index in members],
                    "representative_indices": representatives[:3],
                    "representative_ids": [str(metadata[index]["id"]) for index in representatives[:3]],
                }
            )
    return clusters


def equal_weights(n_members: int) -> np.ndarray:
    if n_members < 1:
        raise ValueError("at least one member is required")
    return np.full(n_members, 1.0 / n_members, dtype=np.float64)


def family_equal_weights(families: Sequence[str]) -> np.ndarray:
    if not families:
        raise ValueError("at least one family is required")
    groups: dict[str, list[int]] = defaultdict(list)
    for index, family in enumerate(families):
        groups[str(family)].append(index)
    weights = np.zeros(len(families), dtype=np.float64)
    family_share = 1.0 / len(groups)
    for indices in groups.values():
        weights[indices] = family_share / len(indices)
    return weights


def greedy_forward_select(
    predictions: np.ndarray,
    target: np.ndarray,
    member_ids: Sequence[str] | None = None,
    *,
    max_members: int = MAX_GREEDY_MEMBERS,
    min_delta: float = GREEDY_MIN_DELTA,
) -> dict[str, Any]:
    """Greedy equal-weight forward selection on one inner training block."""

    matrix, labels = _validate_training_data(predictions, target)
    if max_members < 1 or max_members > MAX_GREEDY_MEMBERS:
        raise ValueError(f"max_members must be in [1, {MAX_GREEDY_MEMBERS}]")
    ids = list(member_ids or [str(index) for index in range(matrix.shape[1])])
    if len(ids) != matrix.shape[1]:
        raise ValueError("member_ids must match prediction columns")
    individual = [float(roc_auc_score(labels, matrix[:, index])) for index in range(matrix.shape[1])]
    selected = [int(np.argmax(individual))]
    current_prediction = matrix[:, selected[0]].copy()
    current_auc = individual[selected[0]]
    history = [{"member": ids[selected[0]], "auc": current_auc, "delta": None}]

    while len(selected) < min(max_members, matrix.shape[1]):
        best: tuple[float, int, np.ndarray] | None = None
        for candidate in range(matrix.shape[1]):
            if candidate in selected:
                continue
            blended = (len(selected) * current_prediction + matrix[:, candidate]) / (len(selected) + 1)
            score = float(roc_auc_score(labels, blended))
            if best is None or score > best[0]:
                best = (score, candidate, blended)
        if best is None or best[0] - current_auc < min_delta:
            break
        score, candidate, blended = best
        delta = score - current_auc
        selected.append(candidate)
        current_auc = score
        current_prediction = blended
        history.append({"member": ids[candidate], "auc": score, "delta": delta})

    weights = np.zeros(matrix.shape[1], dtype=np.float64)
    weights[selected] = 1.0 / len(selected)
    return {
        "selected_indices": selected,
        "selected_ids": [ids[index] for index in selected],
        "weights": weights,
        "train_auc": current_auc,
        "history": history,
    }


def fit_nonnegative_ridge_simplex(
    predictions: np.ndarray,
    target: np.ndarray,
    *,
    ridge_lambda: float,
    weight_cap: float,
) -> dict[str, Any]:
    """Fit pre-registered non-negative, capped, sum-to-one ridge weights."""

    matrix, labels = _validate_training_data(predictions, target)
    if ridge_lambda not in RIDGE_GRID:
        raise ValueError(f"ridge_lambda must be in the pre-registered grid {RIDGE_GRID}")
    if weight_cap not in WEIGHT_CAP_GRID:
        raise ValueError(f"weight_cap must be in the pre-registered grid {WEIGHT_CAP_GRID}")
    n_members = matrix.shape[1]
    if weight_cap * n_members < 1.0 - 1e-12:
        raise ValueError("weight cap makes the simplex infeasible")
    initial = equal_weights(n_members)

    def objective(weights: np.ndarray) -> float:
        residual = matrix @ weights - labels
        return float(np.mean(residual * residual) + ridge_lambda * np.dot(weights, weights))

    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=[(0.0, weight_cap)] * n_members,
        constraints=[{"type": "eq", "fun": lambda weights: float(weights.sum() - 1.0)}],
        options={"ftol": 1e-12, "maxiter": 1000, "disp": False},
    )
    if not result.success:
        raise RuntimeError(f"constrained ridge did not converge: {result.message}")
    weights = np.clip(result.x, 0.0, weight_cap)
    weights /= weights.sum()
    return {
        "weights": weights,
        "ridge_lambda": ridge_lambda,
        "weight_cap": weight_cap,
        "objective": objective(weights),
        "train_auc": float(roc_auc_score(labels, matrix @ weights)),
    }


def fit_family_hierarchical(
    predictions: np.ndarray,
    target: np.ndarray,
    families: Sequence[str],
    *,
    ridge_lambda: float,
    family_weight_cap: float,
) -> dict[str, Any]:
    """Equal-bag within families, then fit constrained weights across families."""

    matrix, labels = _validate_training_data(predictions, target)
    if len(families) != matrix.shape[1]:
        raise ValueError("families must match prediction columns")
    groups: dict[str, list[int]] = defaultdict(list)
    for index, family in enumerate(families):
        groups[str(family)].append(index)
    family_names = sorted(groups)
    family_predictions = np.column_stack(
        [matrix[:, groups[family]].mean(axis=1) for family in family_names]
    )
    fitted = fit_nonnegative_ridge_simplex(
        family_predictions,
        labels,
        ridge_lambda=ridge_lambda,
        weight_cap=family_weight_cap,
    )
    member_weights = np.zeros(matrix.shape[1], dtype=np.float64)
    for family_index, family in enumerate(family_names):
        member_weights[groups[family]] = fitted["weights"][family_index] / len(groups[family])
    return {
        **fitted,
        "family_names": family_names,
        "family_weights": fitted["weights"],
        "weights": member_weights,
    }

