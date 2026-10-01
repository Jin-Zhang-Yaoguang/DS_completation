"""Meta-feature transforms that are fitted strictly on meta-training rows."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _matrix(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 1:
        array = array[:, None]
    if array.ndim != 2 or array.shape[0] == 0 or array.shape[1] == 0:
        raise ValueError("meta features must be a non-empty 2D matrix")
    if not np.isfinite(array).all():
        raise ValueError("meta features contain NaN or Inf")
    return array


@dataclass
class ECDFTransformer:
    """Column-wise empirical CDF fitted on a meta-training block only."""

    sorted_columns_: tuple[np.ndarray, ...] | None = None

    def fit(self, values: np.ndarray) -> "ECDFTransformer":
        matrix = _matrix(values)
        columns = []
        for column in range(matrix.shape[1]):
            sorted_values = np.sort(matrix[:, column], kind="mergesort")
            sorted_values.flags.writeable = False
            columns.append(sorted_values)
        self.sorted_columns_ = tuple(columns)
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.sorted_columns_ is None:
            raise RuntimeError("ECDFTransformer must be fitted before transform")
        matrix = _matrix(values)
        if matrix.shape[1] != len(self.sorted_columns_):
            raise ValueError("meta feature count differs from fitted ECDF")
        output = np.empty(matrix.shape, dtype=np.float32)
        for column, reference in enumerate(self.sorted_columns_):
            left = np.searchsorted(reference, matrix[:, column], side="left")
            right = np.searchsorted(reference, matrix[:, column], side="right")
            output[:, column] = (left + right) / (2.0 * len(reference))
        return output

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        return self.fit(values).transform(values)


@dataclass
class Standardizer:
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None

    def fit(self, values: np.ndarray) -> "Standardizer":
        matrix = _matrix(values)
        self.mean_ = matrix.mean(axis=0)
        scale = matrix.std(axis=0)
        self.scale_ = np.where(scale > 0.0, scale, 1.0)
        self.mean_.flags.writeable = False
        self.scale_.flags.writeable = False
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None:
            raise RuntimeError("Standardizer must be fitted before transform")
        matrix = _matrix(values)
        if matrix.shape[1] != len(self.mean_):
            raise ValueError("meta feature count differs from fitted standardizer")
        return ((matrix - self.mean_) / self.scale_).astype(np.float32)

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        return self.fit(values).transform(values)


class MetaTransformer:
    """Frozen transform pipeline; fitting accepts training rows only."""

    def __init__(self, method: str = "ecdf") -> None:
        if method not in {"identity", "ecdf", "standardize", "ecdf_standardize"}:
            raise ValueError(f"unsupported transform method: {method}")
        self.method = method
        self.ecdf: ECDFTransformer | None = None
        self.standardizer: Standardizer | None = None
        self.n_features_: int | None = None

    def fit(self, train_values: np.ndarray) -> "MetaTransformer":
        matrix = _matrix(train_values)
        self.n_features_ = matrix.shape[1]
        current = matrix
        if self.method in {"ecdf", "ecdf_standardize"}:
            self.ecdf = ECDFTransformer().fit(current)
            current = self.ecdf.transform(current)
        if self.method in {"standardize", "ecdf_standardize"}:
            self.standardizer = Standardizer().fit(current)
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.n_features_ is None:
            raise RuntimeError("MetaTransformer must be fitted before transform")
        current = _matrix(values)
        if current.shape[1] != self.n_features_:
            raise ValueError("meta feature count differs from fitted transform")
        if self.ecdf is not None:
            current = self.ecdf.transform(current)
        if self.standardizer is not None:
            current = self.standardizer.transform(current)
        return np.asarray(current, dtype=np.float32)

    def fit_transform(self, train_values: np.ndarray) -> np.ndarray:
        return self.fit(train_values).transform(train_values)

