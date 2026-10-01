# -*- coding: utf-8 -*-
"""v55：五折验证稀疏分层加性逻辑模型，检验其独立误差是否可集成。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler


SEED = 15_485_863
ALPHAS = (3e-6, 3e-5)
OUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUT_DIR.parents[1] / "data"
V52_OOF = OUT_DIR.parent / "v52_robust_rank_ensemble_v51" / "oof_proba.npy"
V54_SOURCE = OUT_DIR.parent / "v54_sparse_additive_probe" / "v54_sparse_additive_probe.py"


def load_v54():
    spec = importlib.util.spec_from_file_location("v54_sparse_additive_probe", V54_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v54：{V54_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rank(values: np.ndarray) -> np.ndarray:
    return rankdata(np.asarray(values), method="average") / len(values)


def main() -> None:
    start = time.time()
    v54 = load_v54()
    train = pd.read_csv(DATA_DIR / "train.csv")
    y = (train["Will_Buy_EV"] == "Yes").to_numpy(np.int8)
    categorical = v54.make_categorical(train)
    encoder = OneHotEncoder(
        handle_unknown="ignore", min_frequency=2, dtype=np.float32, sparse_output=True
    )
    x_cat = encoder.fit_transform(categorical)
    spline_cols = [
        "Annual_Income_USD",
        "Daily_Commute_km",
        "Age",
        "Charging_Stations_Near_Home",
        "Charging_Stations_Near_Work",
    ]
    transformer = SplineTransformer(n_knots=20, degree=3, include_bias=False)
    x_spline = transformer.fit_transform(train[spline_cols]).astype(np.float32)
    x_spline = StandardScaler(with_mean=False).fit_transform(x_spline).astype(np.float32)
    x = sparse.hstack(
        [x_cat, sparse.csr_matrix(x_spline)], format="csr", dtype=np.float32
    )
    reference = np.load(V52_OOF)
    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y))
    predictions = {alpha: np.zeros(len(train), dtype=np.float64) for alpha in ALPHAS}
    rows: list[dict] = []
    print(f"matrix={x.shape} nnz={x.nnz} build_elapsed={time.time()-start:.1f}s", flush=True)

    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
        reference_auc = float(roc_auc_score(y[valid_idx], reference[valid_idx]))
        for alpha in ALPHAS:
            model = SGDClassifier(
                loss="log_loss",
                penalty="l2",
                alpha=alpha,
                max_iter=100,
                tol=1e-5,
                average=True,
                random_state=SEED + fold,
                n_jobs=8,
            )
            model.fit(x[fit_idx], y[fit_idx])
            pred = model.predict_proba(x[valid_idx])[:, 1]
            predictions[alpha][valid_idx] = pred
            auc = float(roc_auc_score(y[valid_idx], pred))
            blend_rows = []
            ref_rank = rank(reference[valid_idx])
            pred_rank = rank(pred)
            for weight in (0.01, 0.02, 0.03, 0.05, 0.08, 0.12):
                score = float(
                    roc_auc_score(
                        y[valid_idx], (1.0 - weight) * ref_rank + weight * pred_rank
                    )
                )
                blend_rows.append(
                    {"weight": weight, "auc": score, "delta": score - reference_auc}
                )
            best = max(blend_rows, key=lambda item: item["auc"])
            row = {
                "fold": fold,
                "alpha": alpha,
                "auc": auc,
                "reference_auc": reference_auc,
                "best_blend": best,
                "iterations": int(model.n_iter_),
                "elapsed_seconds": time.time() - start,
            }
            rows.append(row)
            print(json.dumps(row), flush=True)

    reference_auc = float(roc_auc_score(y, reference))
    summaries = {}
    reference_rank = rank(reference)
    for alpha, pred in predictions.items():
        np.save(OUT_DIR / f"oof_alpha_{alpha:g}.npy", pred)
        pred_rank = rank(pred)
        blends = []
        for weight in np.arange(0.0, 0.101, 0.005):
            score = float(
                roc_auc_score(y, (1.0 - weight) * reference_rank + weight * pred_rank)
            )
            blends.append(
                {"weight": float(weight), "auc": score, "delta": score - reference_auc}
            )
        per_fold = [row for row in rows if row["alpha"] == alpha]
        summaries[str(alpha)] = {
            "oof_auc": float(roc_auc_score(y, pred)),
            "spearman_vs_reference": float(spearmanr(pred, reference).statistic),
            "best_full_oof_blend": max(blends, key=lambda item: item["auc"]),
            "positive_probe_folds": int(
                sum(row["best_blend"]["delta"] > 0 for row in per_fold)
            ),
            "fold_rows": per_fold,
        }
    result = {
        "competition": "playground-series-s6e9",
        "model": "5-fold sparse hierarchical additive logistic SGD",
        "seed": SEED,
        "matrix_shape": list(x.shape),
        "matrix_nnz": int(x.nnz),
        "reference": "v52_robust_rank_ensemble_v51",
        "reference_oof_auc": reference_auc,
        "summaries": summaries,
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
