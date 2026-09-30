#!/usr/bin/env python3
"""
Blend predictions from available v1~v13 prediction files and generate several
candidate submission files for Kaggle.

Usage:
  python model/v14_all_model_blend/blend_all_predictions.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "model"
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


def read_submission(path: Path, name: str) -> pd.Series:
    df = pd.read_csv(path)
    if not {"id", "addicted_label"}.issubset(df.columns):
        raise ValueError(f"{path} missing expected columns id / addicted_label")
    df = df.sort_values("id")
    pred = df["addicted_label"].astype(float).clip(0.0, 1.0).to_numpy()
    return pd.Series(pred, index=df["id"], name=name)


def rank_to_uniform(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    ranks = pd.Series(arr).rank(method="average").to_numpy()
    return (ranks - 1) / max(len(ranks) - 1, 1)


def write_submission(pred: np.ndarray, name: str, sample_df: pd.DataFrame) -> None:
    out = pd.DataFrame({
        "id": sample_df["id"].values,
        "addicted_label": pred.astype(float).clip(0.0, 1.0),
    })
    out.to_csv(OUT_DIR / name, index=False)


def main() -> None:
    # prediction sources discovered from current experiment history
    # (submission files可追溯到各自版本目录)
    candidates = {
        "v1_baseline_lgbm": MODEL_DIR / "v1_baseline_lgbm" / "submission.csv",
        "v2_budget_lgbm": MODEL_DIR / "v2_budget_lgbm" / "submission.csv",
        "v3_dual_catboost": MODEL_DIR / "v3_dual_catboost" / "submission.csv",
        "v5_hierarchical_lookup": MODEL_DIR / "v5_hierarchical_lookup" / "submission.csv",
        "v6_highres_lgbm": MODEL_DIR / "v6_highres_lgbm" / "submission.csv",
        "v7_catboost_bagging": MODEL_DIR / "v7_catboost_bagging" / "submission.csv",
        # v8 与 v10 的预测已完全一致，v10在这里只保留 v8 进行去重
        "v8_three_model_blend": MODEL_DIR / "v8_three_model_blend" / "submission.csv",
        "v9_catboost_engineered": MODEL_DIR / "v9_catboost_engineered" / "submission.csv",
        "v10_three_model_blend_plus_v9": MODEL_DIR / "v10_three_model_blend_plus_v9" / "submission.csv",
        "v11_xgboost_engineered": MODEL_DIR / "v11_xgboost_engineered" / "submission.csv",
        "v12_xgboost_prob_blend": MODEL_DIR / "v12_xgboost_rank_blend" / "submission.csv",
        "v12_xgboost_rank_blend": MODEL_DIR / "v12_xgboost_rank_blend" / "submission_rank.csv",
        "v13_lgbm": MODEL_DIR / "v13_fe_single_compare" / "submission_lgbm.csv",
        "v13_catboost": MODEL_DIR / "v13_fe_single_compare" / "submission_cat.csv",
        "v13_xgboost": MODEL_DIR / "v13_fe_single_compare" / "submission_xgb.csv",
    }

    predictions: Dict[str, pd.Series] = {}
    seen_hash = {}
    for name, path in candidates.items():
        if not path.exists():
            print(f"[WARN] {path} not found, skip {name}")
            continue
        s = read_submission(path, name)
        # 简单去重：若多份文件内容完全相同，则只保留第一份
        rounded = np.round(s.to_numpy(dtype=float), 8)
        key = pd.util.hash_pandas_object(pd.Series(rounded)).values.tobytes().hex()
        if key in seen_hash:
            print(f"[INFO] {name} 与 {seen_hash[key]} 预测完全一致，跳过重复")
            continue
        seen_hash[key] = name
        predictions[name] = s

    if not predictions:
        raise RuntimeError("未找到任何可用预测文件")

    # 对齐 ID
    ids = next(iter(predictions.values())).index
    pred_df = pd.concat(predictions.values(), axis=1)
    for c in pred_df.columns:
        if pred_df[c].isna().any():
            raise ValueError(f"预测列 {c} 存在缺失值，请检查对应 submission")

    # 将 index 显式转回 DataFrame
    pred_df = pred_df.reset_index().rename(columns={"index": "id"})
    pred_df["id"] = pred_df["id"].astype(int)

    # 等权平均
    prob_mean_all = pred_df[[*predictions.keys()]].mean(axis=1).values
    write_submission(prob_mean_all, "submission_blend_prob_all.csv", pred_df[["id"]])

    # 等权 rank 平均
    rank_cols = [rank_to_uniform(pred_df[col].values) for col in predictions]
    prob_rank_all = np.mean(np.column_stack(rank_cols), axis=1)
    write_submission(prob_rank_all, "submission_blend_rank_all.csv", pred_df[["id"]])

    # OOF 经验加权（用 oof_auc 作为权重，来自实验台账）
    oof_weights = {
        "v1_baseline_lgbm": 0.962633,
        "v2_budget_lgbm": 0.963559,
        "v3_dual_catboost": 0.967965,
        "v5_hierarchical_lookup": 0.958196,
        "v6_highres_lgbm": 0.967373,
        "v7_catboost_bagging": 0.968132,
        "v8_three_model_blend": 0.968358,
        "v9_catboost_engineered": 0.963478,
        "v11_xgboost_engineered": 0.964863,
        "v12_xgboost_prob_blend": 0.968366,
        "v12_xgboost_rank_blend": 0.968457,
        "v13_lgbm": 0.964841,
        "v13_catboost": 0.962842,
        "v13_xgboost": 0.966431,
    }
    w = []
    cols = []
    for c in pred_df.columns:
        if c in ("id",):
            continue
        if c in oof_weights:
            w.append(float(oof_weights[c]))
            cols.append(c)
    w = np.array(w, dtype=float)
    if (w <= 0).all():
        raise RuntimeError("未能匹配任何权重")
    w = w / w.sum()
    prob_w = np.dot(pred_df[cols].values, w)
    write_submission(prob_w, "submission_blend_oof_weight_all.csv", pred_df[["id"]])

    # 只保留前 8 个质量较高预测（剔除低分模型）
    top8 = [
        "v13_xgboost",
        "v12_xgboost_rank_blend",
        "v12_xgboost_prob_blend",
        "v7_catboost_bagging",
        "v8_three_model_blend",
        "v3_dual_catboost",
        "v6_highres_lgbm",
        "v11_xgboost_engineered",
    ]
    top8_cols = [c for c in top8 if c in pred_df.columns]
    if top8_cols:
        prob_top8 = pred_df[top8_cols].mean(axis=1).values
        write_submission(prob_top8, "submission_blend_top8_mean.csv", pred_df[["id"]])
        rank_top8 = np.mean(np.column_stack([rank_to_uniform(pred_df[c].values) for c in top8_cols]), axis=1)
        write_submission(rank_top8, "submission_blend_top8_rank.csv", pred_df[["id"]])

    # 输出用于复盘的 metadata
    meta = {
        "included_models": list(predictions.keys()),
        "included_model_count": len(predictions),
        "unique_hash_count": len(seen_hash),
        "blend_files": [
            "submission_blend_prob_all.csv",
            "submission_blend_rank_all.csv",
            "submission_blend_oof_weight_all.csv",
            "submission_blend_top8_mean.csv",
            "submission_blend_top8_rank.csv",
        ],
    }
    with open(OUT_DIR / "blend_record.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
