# -*- coding: utf-8 -*-
"""v5：严格折外的层级查表/平滑模型。

每个原始字段建立两层经验贝叶斯估计：
- 数值字段：精确值 -> 分位数区间 -> 全局先验；
- 类别字段：精确类别 -> 全局先验。

训练行使用内层 5 折 OOF 统计，验证集和测试集只使用当前训练折的标签。
最终用正则化 LogisticRegression 组合各字段的 posterior logit、父层 logit、
频次以及不含标签的连续特征，保持模型为低方差的加性查表模型。
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
INNER_FOLDS = 5
TARGET = "addicted_label"
ID_COL = "id"
N_BINS = 128
BIN_ALPHA = 100.0
EXACT_ALPHA = 20.0

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
V3_RESULTS = OUT_DIR.parent / "v3_dual_catboost" / "cv_results.json"

COMPONENT_COLS = ["social_media_hours", "gaming_hours", "work_study_hours"]


def safe_logit(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 1e-5, 1.0 - 1e-5)
    return np.log(values / (1.0 - values)).astype(np.float32)


def exact_key(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(np.float64).fillna(-1e30)
    return series.fillna("__NA__").astype(str)


def numeric_bin_edges(series: pd.Series) -> np.ndarray:
    values = series.dropna().to_numpy(dtype=np.float64)
    if len(values) == 0:
        return np.array([], dtype=np.float64)
    edges = np.unique(np.quantile(values, np.linspace(0.0, 1.0, N_BINS + 1)))
    return edges[1:-1]


def assign_bins(series: pd.Series, edges: np.ndarray) -> np.ndarray:
    values = series.to_numpy(dtype=np.float64)
    bins = np.searchsorted(edges, values, side="right").astype(np.int32)
    bins[np.isnan(values)] = -1
    return bins


def grouped_sum_count(keys: pd.Series | np.ndarray, y: np.ndarray) -> pd.DataFrame:
    frame = pd.DataFrame({"key": keys, "target": y})
    return frame.groupby("key", sort=False, dropna=False)["target"].agg(["sum", "count"])


def map_stats(keys: pd.Series | np.ndarray, stats: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    key_series = pd.Series(keys, copy=False)
    sums = key_series.map(stats["sum"]).fillna(0.0).to_numpy(dtype=np.float64)
    counts = key_series.map(stats["count"]).fillna(0.0).to_numpy(dtype=np.float64)
    return sums, counts


def encode_column(
    fit_series: pd.Series,
    query_series: pd.Series,
    y_fit: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """返回 fit 的 LOO 编码和 query 的纯训练折编码，各含三列。"""
    global_mean = float(y_fit.mean())
    n_fit = len(y_fit)
    global_loo = (y_fit.sum() - y_fit) / max(n_fit - 1, 1)

    fit_exact = exact_key(fit_series).reset_index(drop=True)
    query_exact = exact_key(query_series).reset_index(drop=True)
    exact_stats = grouped_sum_count(fit_exact, y_fit)
    exact_sum_fit, exact_count_fit = map_stats(fit_exact, exact_stats)
    exact_sum_query, exact_count_query = map_stats(query_exact, exact_stats)

    if pd.api.types.is_numeric_dtype(fit_series):
        edges = numeric_bin_edges(fit_series)
        fit_parent_key = assign_bins(fit_series, edges)
        query_parent_key = assign_bins(query_series, edges)
        parent_stats = grouped_sum_count(fit_parent_key, y_fit)
        parent_sum_fit, parent_count_fit = map_stats(fit_parent_key, parent_stats)
        parent_sum_query, parent_count_query = map_stats(query_parent_key, parent_stats)
        parent_fit = (
            parent_sum_fit - y_fit + BIN_ALPHA * global_loo
        ) / (np.maximum(parent_count_fit - 1.0, 0.0) + BIN_ALPHA)
        parent_query = (
            parent_sum_query + BIN_ALPHA * global_mean
        ) / (parent_count_query + BIN_ALPHA)
    else:
        parent_fit = global_loo
        parent_query = np.full(len(query_series), global_mean, dtype=np.float64)

    exact_fit = (
        exact_sum_fit - y_fit + EXACT_ALPHA * parent_fit
    ) / (np.maximum(exact_count_fit - 1.0, 0.0) + EXACT_ALPHA)
    exact_query = (
        exact_sum_query + EXACT_ALPHA * parent_query
    ) / (exact_count_query + EXACT_ALPHA)

    fit_features = np.column_stack(
        [safe_logit(exact_fit), safe_logit(parent_fit), np.log1p(np.maximum(exact_count_fit - 1.0, 0.0))]
    ).astype(np.float32)
    query_features = np.column_stack(
        [safe_logit(exact_query), safe_logit(parent_query), np.log1p(exact_count_query)]
    ).astype(np.float32)
    return fit_features, query_features


def add_budget_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    parts = frame[COMPONENT_COLS]
    frame["component_sum_available"] = parts.fillna(0.0).sum(axis=1)
    frame["other_screen_available"] = frame["daily_screen_time_hours"] - frame["component_sum_available"]
    frame["n_components_observed"] = parts.notna().sum(axis=1).astype(np.float32)
    return frame


def base_features(
    fit: pd.DataFrame, query: pd.DataFrame, raw_cols: list[str]
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    fit_budget = add_budget_features(fit[raw_cols])
    query_budget = add_budget_features(query[raw_cols])
    numeric_cols = [c for c in fit_budget if pd.api.types.is_numeric_dtype(fit_budget[c])]
    fit_num = fit_budget[numeric_cols].to_numpy(dtype=np.float64)
    query_num = query_budget[numeric_cols].to_numpy(dtype=np.float64)
    medians = np.nanmedian(fit_num, axis=0)
    fit_num = np.where(np.isnan(fit_num), medians, fit_num)
    query_num = np.where(np.isnan(query_num), medians, query_num)
    means = fit_num.mean(axis=0)
    scales = fit_num.std(axis=0)
    scales[scales < 1e-8] = 1.0
    fit_scaled = (fit_num - means) / scales
    query_scaled = (query_num - means) / scales
    fit_out = np.column_stack([fit_scaled, np.sign(fit_scaled) * np.sqrt(np.abs(fit_scaled))]).astype(np.float32)
    query_out = np.column_stack([query_scaled, np.sign(query_scaled) * np.sqrt(np.abs(query_scaled))]).astype(np.float32)
    names = [f"raw_{c}" for c in numeric_cols] + [f"signed_sqrt_{c}" for c in numeric_cols]
    return fit_out, query_out, names


def make_fold_features(
    fit: pd.DataFrame,
    queries: list[pd.DataFrame],
    y_fit: np.ndarray,
    raw_cols: list[str],
) -> tuple[np.ndarray, list[np.ndarray], list[str]]:
    fit_parts: list[np.ndarray] = []
    query_parts: list[list[np.ndarray]] = [[] for _ in queries]
    names: list[str] = []
    inner_splitter = StratifiedKFold(
        n_splits=INNER_FOLDS, shuffle=True, random_state=SEED
    )
    inner_folds = list(inner_splitter.split(fit, y_fit))
    for col in raw_cols:
        encoded_fit = np.zeros((len(fit), 3), dtype=np.float32)
        for inner_fit_idx, inner_valid_idx in inner_folds:
            _, inner_valid_encoded = encode_column(
                fit[col].iloc[inner_fit_idx].reset_index(drop=True),
                fit[col].iloc[inner_valid_idx].reset_index(drop=True),
                y_fit[inner_fit_idx],
            )
            encoded_fit[inner_valid_idx] = inner_valid_encoded
        fit_parts.append(encoded_fit)
        for query_number, query in enumerate(queries):
            _, encoded_query = encode_column(
                fit[col].reset_index(drop=True),
                query[col].reset_index(drop=True),
                y_fit,
            )
            query_parts[query_number].append(encoded_query)
        names.extend([f"exact_logit_{col}", f"parent_logit_{col}", f"log_count_{col}"])
    base_fit, base_query, base_names = base_features(fit, queries[0], raw_cols)
    fit_parts.append(base_fit)
    query_parts[0].append(base_query)
    for query_number, query in enumerate(queries[1:], start=1):
        _, other_base_query, other_names = base_features(fit, query, raw_cols)
        if other_names != base_names:
            raise ValueError("基础特征列名不一致")
        query_parts[query_number].append(other_base_query)
    names.extend(base_names)
    return (
        np.column_stack(fit_parts),
        [np.column_stack(parts) for parts in query_parts],
        names,
    )


def validate_submission(submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame) -> None:
    if submission.shape != sample.shape or list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError("提交结构不符合 sample_submission")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与测试集不一致")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率包含非法值")


def main() -> None:
    start = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    raw_cols = [c for c in test.columns if c != ID_COL]
    y = train[TARGET].to_numpy(dtype=np.int8)
    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    coefficient_frames: list[pd.DataFrame] = []

    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(train, y), start=1):
        fold_start = time.time()
        fit_frame = train.iloc[fit_idx].reset_index(drop=True)
        valid_frame = train.iloc[valid_idx].reset_index(drop=True)
        y_fit = y[fit_idx]
        x_fit, (x_valid, x_test), names = make_fold_features(
            fit_frame,
            [valid_frame, test.reset_index(drop=True)],
            y_fit,
            raw_cols,
        )
        feature_means = x_fit.mean(axis=0, dtype=np.float64)
        feature_scales = x_fit.std(axis=0, dtype=np.float64)
        feature_scales[feature_scales < 1e-6] = 1.0
        x_fit = ((x_fit - feature_means) / feature_scales).astype(np.float32)
        x_valid = ((x_valid - feature_means) / feature_scales).astype(np.float32)
        x_test = ((x_test - feature_means) / feature_scales).astype(np.float32)
        model = LogisticRegression(C=0.2, solver="lbfgs", max_iter=300, tol=1e-6)
        model.fit(x_fit, y_fit)
        valid_pred = model.predict_proba(x_valid)[:, 1]
        oof[valid_idx] = valid_pred
        test_pred += model.predict_proba(x_test)[:, 1] / N_FOLDS
        score = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(score)
        coefficient_frames.append(pd.DataFrame({"feature": names, "coefficient": model.coef_[0], "fold": fold}))
        print(f"fold={fold} auc={score:.6f} features={len(names)} elapsed={time.time()-fold_start:.1f}s")

    oof_auc = float(roc_auc_score(y, oof))
    v3 = json.loads(V3_RESULTS.read_text(encoding="utf-8"))
    fold_deltas = np.asarray(fold_scores) - np.asarray(v3["fold_auc"], dtype=float)
    elapsed = time.time() - start

    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    coefficients = pd.concat(coefficient_frames, ignore_index=True)
    coefficients.groupby("feature", as_index=False).agg(
        coefficient_mean=("coefficient", "mean"), coefficient_std=("coefficient", "std")
    ).sort_values("coefficient_mean", key=lambda x: x.abs(), ascending=False).to_csv(
        OUT_DIR / "coefficients.csv", index=False
    )
    results = {
        "competition": "playground-series-s6e8",
        "model": "hierarchical exact-value/bin empirical-Bayes lookup + logistic",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "inner_folds": INNER_FOLDS,
        "n_bins": N_BINS,
        "bin_alpha": BIN_ALPHA,
        "exact_alpha": EXACT_ALPHA,
        "feature_count": len(names),
        "fold_auc": fold_scores,
        "oof_auc": oof_auc,
        "v3_oof_auc": float(v3["oof_auc"]),
        "oof_delta_vs_v3": oof_auc - float(v3["oof_auc"]),
        "fold_delta_vs_v3": fold_deltas.tolist(),
        "folds_won_vs_v3": int((fold_deltas > 0).sum()),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
    }
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
