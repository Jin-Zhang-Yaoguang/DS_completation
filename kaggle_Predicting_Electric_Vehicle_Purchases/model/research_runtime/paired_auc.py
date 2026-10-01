"""配对 AUC 比较；置信区间仅条件于现有预测，不代替训练与选择不确定性。"""
from __future__ import annotations

import math
import numpy as np

def validate_binary_predictions(y, prediction):
    y = np.asarray(y)
    prediction = np.asarray(prediction, dtype=np.float64)
    if y.ndim != 1 or prediction.shape != y.shape:
        raise ValueError("标签与预测必须为同行序一维向量")
    if not np.isin(y, [0, 1]).all() or np.unique(y).size != 2:
        raise ValueError("必须同时存在正负两类，标签只能为0/1")
    if not np.isfinite(prediction).all():
        raise ValueError("预测含非有限值")
    return y.astype(bool), prediction

def auc_components(y, prediction):
    y, prediction = validate_binary_predictions(y, prediction)
    positive = prediction[y]
    negative = prediction[~y]
    sorted_positive = np.sort(positive)
    sorted_negative = np.sort(negative)
    positive_concordance = (
        np.searchsorted(sorted_negative, positive, side="left")
        + np.searchsorted(sorted_negative, positive, side="right")
    ) / (2.0 * len(negative))
    negative_concordance = 1.0 - (
        np.searchsorted(sorted_positive, negative, side="left")
        + np.searchsorted(sorted_positive, negative, side="right")
    ) / (2.0 * len(positive))
    auc = float(positive_concordance.mean())
    if abs(auc - float(negative_concordance.mean())) > 1e-12:
        raise AssertionError("正负两种AUC分解不一致")
    return auc, positive_concordance, negative_concordance

def paired_auc(y, baseline, candidate, folds=None):
    y, baseline = validate_binary_predictions(y, baseline)
    _, candidate = validate_binary_predictions(y, candidate)
    base_auc, base_pos, base_neg = auc_components(y, baseline)
    candidate_auc, cand_pos, cand_neg = auc_components(y, candidate)
    pos_delta = cand_pos - base_pos
    neg_delta = cand_neg - base_neg
    delta = candidate_auc - base_auc
    variance = None
    se = None
    interval = None
    p_value = None
    if len(pos_delta) >= 2 and len(neg_delta) >= 2:
        variance = float(
            np.var(pos_delta, ddof=1) / len(pos_delta)
            + np.var(neg_delta, ddof=1) / len(neg_delta)
        )
        se = math.sqrt(max(variance, 0.0))
        interval = [delta - 1.959963984540054 * se, delta + 1.959963984540054 * se]
        p_value = math.erfc(abs(delta) / (math.sqrt(2.0) * se)) if se else (1.0 if delta == 0 else 0.0)
    report = {
        "n_rows": int(len(y)),
        "n_positive": int(y.sum()),
        "n_negative": int((~y).sum()),
        "baseline_auc": base_auc,
        "candidate_auc": candidate_auc,
        "delta": delta,
        "conditional_standard_error": se,
        "conditional_ci95": interval,
        "conditional_two_sided_p_value": p_value,
        "uncertainty_scope": (
            "配对正负样本影响函数近似；只描述条件于这些预测的样本不确定性。"
            "OOF训练集重叠、早停、选模、多重比较和历史开发影响均未纳入，"
            "不能据此声称独立盲测或整个学习流程的无偏置信区间。"
        ),
    }
    if folds is not None:
        folds = np.asarray(folds)
        if folds.shape != y.shape:
            raise ValueError("折ID与标签长度不一致")
        rows = []
        for fold in np.unique(folds):
            selected = folds == fold
            base = auc_components(y[selected], baseline[selected])[0]
            cand = auc_components(y[selected], candidate[selected])[0]
            rows.append({"fold": int(fold), "rows": int(selected.sum()), "baseline_auc": base, "candidate_auc": cand, "delta": cand-base})
        report["folds"] = rows
        report["positive_folds"] = sum(row["delta"] > 0 for row in rows)
        report["all_folds_positive"] = all(row["delta"] > 0 for row in rows)
    return report

