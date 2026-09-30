#!/usr/bin/env python3
"""
v18：用 11 个单模型产物做二层元学习（stacking）和 OOF 权重优化融合（blending）
并直接生成候选提交文件。

单模型清单：
- v1_baseline_lgbm
- v2_budget_lgbm
- v3_dual_catboost
- v5_hierarchical_lookup
- v6_highres_lgbm
- v7_catboost_bagging
- v9_catboost_engineered
- v11_xgboost_engineered
- v13_fe_single_compare（LGBM / CatBoost / XGBoost）
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "model"
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
N_FOLDS = 5
TARGET = "addicted_label"

SINGLE_MODELS = [
    ("v1_baseline_lgbm", "oof_proba.npy", "test_proba.npy"),
    ("v2_budget_lgbm", "oof_proba.npy", "test_proba.npy"),
    ("v3_dual_catboost", "oof_proba.npy", "test_proba.npy"),
    ("v5_hierarchical_lookup", "oof_proba.npy", "test_proba.npy"),
    ("v6_highres_lgbm", "oof_proba.npy", "test_proba.npy"),
    ("v7_catboost_bagging", "oof_proba.npy", "test_proba.npy"),
    ("v9_catboost_engineered", "oof_proba.npy", "test_proba.npy"),
    ("v11_xgboost_engineered", "oof_proba.npy", "test_proba.npy"),
    ("v13_lgbm", "lgbm_oof_proba.npy", "lgbm_test_proba.npy"),
    ("v13_cat", "cat_oof_proba.npy", "cat_test_proba.npy"),
    ("v13_xgb", "xgb_oof_proba.npy", "xgb_test_proba.npy"),
]


def load_and_align_data() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """读取原始数据和 11 个单模型 OOF/测试概率，按训练/测试顺序对齐。"""
    train = pd.read_csv(DATA_DIR / "train.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")

    if TARGET not in train.columns:
        raise ValueError("train.csv 缺少标签列 addicted_label")
    if train["id"].duplicated().any():
        raise ValueError("训练集 id 重复")

    y = train[TARGET].to_numpy(dtype=np.int8)
    test_ids = sample["id"].to_numpy(dtype=np.int64)

    oof_frames = {}
    test_frames = {}

    for model_name, oof_file, test_file in SINGLE_MODELS:
        src_dir = MODEL_DIR / (
            "v13_fe_single_compare"
            if model_name.startswith("v13_")
            else model_name
        )
        oof_path = src_dir / oof_file
        test_path = src_dir / test_file

        if not oof_path.exists():
            raise FileNotFoundError(f"缺少 OOF 文件: {oof_path}")
        if not test_path.exists():
            raise FileNotFoundError(f"缺少测试概率文件: {test_path}")

        oof_pred = np.load(oof_path)
        test_pred = np.load(test_path)

        if oof_pred.ndim != 1 or test_pred.ndim != 1:
            raise ValueError(f"{model_name} 概率不是 1-D")
        if len(oof_pred) != len(train):
            raise ValueError(f"{model_name} OOF 长度不一致: {len(oof_pred)} != {len(train)}")
        if len(test_pred) != len(sample):
            raise ValueError(
                f"{model_name} 测试长度不一致: {len(test_pred)} != {len(sample)}"
            )

        if np.isnan(oof_pred).any() or np.isinf(oof_pred).any():
            raise ValueError(f"{model_name} OOF 存在非法值")
        if np.isnan(test_pred).any() or np.isinf(test_pred).any():
            raise ValueError(f"{model_name} 测试概率存在非法值")

        oof_frames[model_name] = np.clip(oof_pred.astype(float), 0.0, 1.0)
        test_frames[model_name] = np.clip(test_pred.astype(float), 0.0, 1.0)

    X_train = pd.DataFrame(oof_frames)
    X_test = pd.DataFrame(test_frames)

    return train, X_train, X_test, test_ids, y


def optimize_weighted_blend(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    """在 simplex 上做 AUC 优化的线性融合权重。"""
    n_features = x.shape[1]
    init_w = np.full(n_features, 1.0 / n_features)

    def objective(w: np.ndarray) -> float:
        pred = x @ w
        return -roc_auc_score(y, pred)

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
    ]
    bounds = [(0.0, 1.0) for _ in range(n_features)]

    res = minimize(
        objective,
        x0=init_w,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 300, "ftol": 1e-10},
    )

    if not res.success:
        raise RuntimeError(f"OOF 融合优化未收敛: {res.message}")

    w = np.clip(res.x, 0.0, 1.0)
    w = w / w.sum()
    pred = x @ w
    oof_auc = float(roc_auc_score(y, pred))
    return w, oof_auc


def fit_stacking(
    X: np.ndarray, y: np.ndarray, model_seed: int = SEED
) -> tuple[np.ndarray, float, dict[str, float], float]:
    """用 5 折 OOF 输出二层堆叠 AUC。"""
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=model_seed)
    oof_pred = np.zeros(len(X), dtype=float)
    fold_scores: list[float] = []
    fold_models: list[tuple[np.ndarray, float]] = []

    for fold_id, (train_idx, valid_idx) in enumerate(skf.split(X, y), start=1):
        clf = LogisticRegression(
            C=1.2,
            penalty="l2",
            solver="liblinear",
            random_state=model_seed,
            max_iter=4000,
        )
        clf.fit(X[train_idx], y[train_idx])
        pred_valid = clf.predict_proba(X[valid_idx])[:, 1]
        oof_pred[valid_idx] = pred_valid
        auc = float(roc_auc_score(y[valid_idx], pred_valid))
        fold_models.append((clf.coef_[0], float(clf.intercept_[0])))
        fold_scores.append(auc)
        print(f"[stack] fold={fold_id} auc={auc:.6f} coef_norm={np.linalg.norm(clf.coef_):.4f}")

    oof_auc = float(roc_auc_score(y, oof_pred))
    meta = {
        "n_folds": N_FOLDS,
        "fold_auc": [float(x) for x in fold_scores],
        "oof_auc": oof_auc,
        "fit_seed": model_seed,
    }
    return oof_pred, oof_auc, meta, fold_models


def fit_stacking_test(x_train: np.ndarray, x_test: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """全量训练 stacking 头模型，分别返回测试概率与每折 OOF 预测。"""
    meta_oof_pred, meta_oof_auc, meta_report, _ = fit_stacking(x_train, y, model_seed=SEED)
    meta = LogisticRegression(
        C=1.2,
        penalty="l2",
        solver="liblinear",
        random_state=SEED,
        max_iter=4000,
    )
    meta.fit(x_train, y)
    test_pred = meta.predict_proba(x_test)[:, 1]
    meta_coef = meta.coef_[0].tolist()
    meta_intercept = float(meta.intercept_[0])
    return meta_oof_pred, meta_oof_auc, test_pred, meta_coef, meta_intercept, meta_report


def write_submission(pred: np.ndarray, ids: np.ndarray, file_name: str) -> Path:
    out_path = OUT_DIR / file_name
    pred = np.clip(pred, 0.0, 1.0)
    pd.DataFrame({"id": ids, "addicted_label": pred.astype(float)}).to_csv(
        out_path, index=False
    )
    print(f"[save] {out_path.name}")
    return out_path


def main() -> None:
    start = time.time()
    train, x_train_df, x_test_df, test_ids, y = load_and_align_data()

    x_train = x_train_df.to_numpy(dtype=float)
    x_test = x_test_df.to_numpy(dtype=float)
    print(f"加载单模型：{len(x_train_df.columns)} 个，train={x_train.shape}, test={x_test.shape}")
    print(f"单模型顺序: {list(x_train_df.columns)}")

    # 1) stacking：五折 OOF 与全量测试头模型预测
    stack_oof_pred, stack_oof_auc, stack_test_pred, stack_coef, stack_intercept, stack_meta = fit_stacking_test(
        x_train, x_test, y
    )
    stack_test_pred = np.clip(stack_test_pred, 0.0, 1.0)
    stack_auc = float(roc_auc_score(y, stack_oof_pred))
    print(f"[stack] OOF AUC={stack_auc:.6f}")

    # 2) OOF 线性权重优化：以最小化 OOF AUC 负值方式求权重
    blend_weights, blend_oof_auc = optimize_weighted_blend(x_train, y)
    blend_test_pred = x_test @ blend_weights

    print(f"[blend] OOF AUC={blend_oof_auc:.6f}")
    print("[blend] 权重 top10：")
    for name, w in sorted(
        zip(x_train_df.columns.tolist(), blend_weights),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"  {name}: {w:.6f}")

    # 3) 输出候选提交文件
    out_stack = write_submission(stack_test_pred, test_ids, "submission_stack_meta_lr.csv")
    out_blend = write_submission(blend_test_pred, test_ids, "submission_blend_auc_opt.csv")
    out_uniform = write_submission(np.mean(x_test, axis=1), test_ids, "submission_uniform_avg.csv")

    selected = "stack" if stack_auc >= blend_oof_auc else "blend"
    selected_file = out_stack if selected == "stack" else out_blend
    selected_auc = max(stack_auc, blend_oof_auc)

    # 简单 rank 融合后验测试（只做可追踪参考）
    from scipy.stats import rankdata

    rank_cols = np.column_stack([rankdata(x_train[:, i], method="average") for i in range(x_train.shape[1])])
    rank_blend_w = np.ones(x_train.shape[1], dtype=float) / x_train.shape[1]
    rank_test = np.dot(
        np.column_stack([rankdata(x_test[:, i], method="average") for i in range(x_test.shape[1])]),
        rank_blend_w,
    )
    rank_test = (rank_test - rank_test.min()) / max(1.0, (rank_test.max() - rank_test.min()))
    out_rank = write_submission(rank_test, test_ids, "submission_rank_uniform.csv")
    rank_oof = (rank_cols @ rank_blend_w)
    rank_oof = (rank_oof - rank_oof.min()) / max(1.0, (rank_oof.max() - rank_oof.min()))
    rank_oof_auc = float(roc_auc_score(y, rank_oof))

    # 4) 写入实验台账文件
    result = {
        "experiment": "v18_single_model_stacking",
        "competition": "playground-series-s6e8",
        "single_models": x_train_df.columns.tolist(),
        "train_size": int(len(train)),
        "test_size": int(len(test_ids)),
        "n_features": int(x_train.shape[1]),
        "seed": SEED,
        "stack": {
            "cv_folds": N_FOLDS,
            "oof_auc": stack_auc,
            "meta_coef": [float(x) for x in stack_coef],
            "meta_intercept": float(stack_intercept),
            "fold_scores": stack_meta["fold_auc"],
        },
        "blend": {
            "objective": "maximize AUC under non-negative simplex",
            "oof_auc": float(blend_oof_auc),
            "weights": {
                name: float(w)
                for name, w in zip(x_train_df.columns.tolist(), blend_weights)
            },
        },
        "rank_reference": {"uniform_rank_oof_auc": float(rank_oof_auc)},
        "outputs": {
            "stack_submission": out_stack.name,
            "blend_submission": out_blend.name,
            "uniform_submission": out_uniform.name,
            "rank_submission": out_rank.name,
        },
        "selection": {
            "selected": selected,
            "selected_submission": selected_file.name,
            "selected_oof_auc": float(selected_auc),
        },
        "runtime_seconds": float(time.time() - start),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with (OUT_DIR / "stack_blend_results.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"结果已写入: {OUT_DIR / 'stack_blend_results.json'}")
    print(f"选择提交策略: {selected}，OOF={selected_auc:.6f}")


if __name__ == "__main__":
    main()
