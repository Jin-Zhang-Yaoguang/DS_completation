# -*- coding: utf-8 -*-
"""v54：稀疏分层加性逻辑模型单折探针。"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import rankdata
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler


SEED = 15_485_863
OUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUT_DIR.parents[1] / "data"
V52_OOF = OUT_DIR.parent / "v52_robust_rank_ensemble_v51" / "oof_proba.npy"
ALPHAS = (3e-7, 1e-6, 3e-6, 1e-5, 3e-5)


def rank(values: np.ndarray) -> np.ndarray:
    return rankdata(np.asarray(values), method="average") / len(values)


def make_categorical(frame: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    raw = [
        "Age",
        "Daily_Commute_km",
        "Number_of_Cars_Owned",
        "Charging_Stations_Near_Home",
        "Charging_Stations_Near_Work",
        "Environmental_Concern_Level",
        "Gender",
        "City_Type",
        "Current_Car_Type",
        "Home_Charging_Possible",
        "Subsidy_Available",
        "Range_Anxiety_Level",
    ]
    for col in raw:
        out[col] = frame[col].astype("string")
    income = frame["Annual_Income_USD"].astype(np.int64)
    out["income_exact"] = income.astype("string")
    for width in (2, 5, 10, 20, 50, 100, 500, 1000):
        out[f"income_bin{width}"] = (income // width).astype("string")
    commute10 = np.rint(frame["Daily_Commute_km"].to_numpy() * 10).astype(np.int64)
    out["commute_exact"] = pd.Series(commute10, index=frame.index).astype("string")
    out["commute_bin1"] = pd.Series(commute10 // 10, index=frame.index).astype("string")
    out["commute_bin2"] = pd.Series(commute10 // 20, index=frame.index).astype("string")

    def interaction(name: str, *cols: str) -> None:
        value = out[cols[0]]
        for col in cols[1:]:
            value = value.str.cat(out[col], sep="|")
        out[name] = value

    interaction("income_env", "income_exact", "Environmental_Concern_Level")
    interaction("income_subsidy", "income_exact", "Subsidy_Available")
    interaction("income_range", "income_exact", "Range_Anxiety_Level")
    interaction("income_city", "income_exact", "City_Type")
    interaction("income_home", "income_exact", "Home_Charging_Possible")
    interaction("income_bin2_range", "income_bin2", "Range_Anxiety_Level")
    interaction("income_bin10_env", "income_bin10", "Environmental_Concern_Level")
    interaction("income_bin100_env", "income_bin100", "Environmental_Concern_Level")
    interaction("env_subsidy", "Environmental_Concern_Level", "Subsidy_Available")
    interaction("env_home", "Environmental_Concern_Level", "Home_Charging_Possible")
    interaction("env_range", "Environmental_Concern_Level", "Range_Anxiety_Level")
    interaction("subsidy_home", "Subsidy_Available", "Home_Charging_Possible")
    return out


def main() -> None:
    start = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    y = (train["Will_Buy_EV"] == "Yes").to_numpy(np.int8)
    categorical = make_categorical(train)
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
    spline = SplineTransformer(n_knots=20, degree=3, include_bias=False)
    x_spline = spline.fit_transform(train[spline_cols]).astype(np.float32)
    x_spline = StandardScaler().fit_transform(x_spline).astype(np.float32)
    x = sparse.hstack([x_cat, sparse.csr_matrix(x_spline)], format="csr", dtype=np.float32)
    fit_idx, valid_idx = next(
        StratifiedKFold(5, shuffle=True, random_state=SEED).split(x, y)
    )
    reference = np.load(V52_OOF)
    reference_auc = float(roc_auc_score(y[valid_idx], reference[valid_idx]))
    rows: list[dict] = []
    print(
        f"matrix={x.shape} nnz={x.nnz} reference_auc={reference_auc:.9f} "
        f"build_elapsed={time.time() - start:.1f}s",
        flush=True,
    )
    for alpha in ALPHAS:
        model = SGDClassifier(
            loss="log_loss",
            penalty="l2",
            alpha=alpha,
            max_iter=80,
            tol=1e-5,
            average=True,
            random_state=SEED,
            n_jobs=8,
        )
        model.fit(x[fit_idx], y[fit_idx])
        pred = model.predict_proba(x[valid_idx])[:, 1]
        auc = float(roc_auc_score(y[valid_idx], pred))
        blend_rows = []
        reference_rank = rank(reference[valid_idx])
        pred_rank = rank(pred)
        for weight in (0.02, 0.05, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30):
            score = float(
                roc_auc_score(
                    y[valid_idx], (1.0 - weight) * reference_rank + weight * pred_rank
                )
            )
            blend_rows.append({"weight": weight, "auc": score, "delta": score - reference_auc})
        best = max(blend_rows, key=lambda row: row["auc"])
        row = {
            "alpha": alpha,
            "auc": auc,
            "iterations": int(model.n_iter_),
            "best_blend": best,
            "elapsed_seconds": time.time() - start,
        }
        rows.append(row)
        print(json.dumps(row), flush=True)

    result = {
        "competition": "playground-series-s6e9",
        "model": "sparse hierarchical additive logistic SGD probe",
        "seed": SEED,
        "fold": 1,
        "matrix_shape": list(x.shape),
        "matrix_nnz": int(x.nnz),
        "categorical_field_count": int(categorical.shape[1]),
        "reference": "v52_robust_rank_ensemble_v51",
        "reference_fold_auc": reference_auc,
        "rows": rows,
        "elapsed_seconds": time.time() - start,
        "hypothesis": (
            "the synthetic generator is approximately additive in hierarchical income keys; "
            "a regularized sparse logit can estimate that structure with different errors from trees"
        ),
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
