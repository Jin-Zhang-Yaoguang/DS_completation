# -*- coding: utf-8 -*-
"""P2-03：复用 v11 MLP 配方，升级为预注册 seed42 的 40 折、3 种子训练。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
BASE_DIR = MODEL_DIR / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
RECIPE_PATH = MODEL_DIR / "v11_mlp_te_10f" / "v11_mlp_te_10f.py"
TARGET = "Will_Buy_EV"
META_GRID = np.linspace(0.0, 1.0, 51)


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(np.asarray(values, dtype=np.float64), method="average") / len(values)


def load_recipe():
    spec = importlib.util.spec_from_file_location("v11_mlp_recipe", RECIPE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载配方：{RECIPE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.N_FOLDS = 40
    module.SEED = 42
    module.MODEL_SEEDS = [0, 1, 2]
    module.OUT_DIR = OUT_DIR
    module.BASE_RESULTS = BASE_DIR / "cv_results.json"
    return module


def crossfit_blend(
    y: np.ndarray, base: np.ndarray, candidate: np.ndarray
) -> dict[str, object]:
    base_rank = pct_rank(base)
    candidate_rank = pct_rank(candidate)
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    blend_oof = np.zeros(len(y), dtype=np.float64)
    rows: list[dict[str, float | int]] = []
    weights: list[float] = []
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(base_rank, y), 1):
        scores = []
        for weight in META_GRID:
            fit_prediction = (1.0 - weight) * base_rank[fit_idx] + weight * candidate_rank[fit_idx]
            scores.append(roc_auc_score(y[fit_idx], fit_prediction))
        best_index = int(np.argmax(scores))
        weight = float(META_GRID[best_index])
        weights.append(weight)
        blend_oof[valid_idx] = (
            (1.0 - weight) * base_rank[valid_idx] + weight * candidate_rank[valid_idx]
        )
        base_auc = float(roc_auc_score(y[valid_idx], base_rank[valid_idx]))
        blend_auc = float(roc_auc_score(y[valid_idx], blend_oof[valid_idx]))
        rows.append(
            {
                "fold": fold,
                "candidate_weight": weight,
                "fit_auc": float(scores[best_index]),
                "base_auc": base_auc,
                "blend_auc": blend_auc,
                "delta_vs_base": blend_auc - base_auc,
            }
        )
    base_auc = float(roc_auc_score(y, base_rank))
    blend_auc = float(roc_auc_score(y, blend_oof))
    return {
        "method": "5-fold seed42 cross-fitted nonnegative percentile-rank blend",
        "grid_step": float(META_GRID[1] - META_GRID[0]),
        "fold_rows": rows,
        "mean_candidate_weight": float(np.mean(weights)),
        "base_oof_auc": base_auc,
        "crossfit_oof_auc": blend_auc,
        "oof_delta_vs_base": blend_auc - base_auc,
        "folds_won_vs_base": int(sum(row["delta_vs_base"] > 0 for row in rows)),
        "passes_gate": bool(
            blend_auc >= base_auc + 0.0001
            and all(row["delta_vs_base"] > 0 for row in rows)
        ),
    }


def enrich_results() -> None:
    result_path = OUT_DIR / "cv_results.json"
    results = json.loads(result_path.read_text(encoding="utf-8"))
    train = pd.read_csv(PROJECT_DIR / "data" / "train.csv", usecols=[TARGET])
    y = train[TARGET].eq("Yes").to_numpy(np.int8)
    candidate = np.load(OUT_DIR / "oof_proba.npy")
    base = np.load(BASE_DIR / "oof_proba.npy")

    bucket_rows = []
    splitter = StratifiedKFold(n_splits=40, shuffle=True, random_state=42)
    for fold, (_, valid_idx) in enumerate(splitter.split(candidate, y), 1):
        candidate_auc = float(roc_auc_score(y[valid_idx], candidate[valid_idx]))
        base_auc = float(roc_auc_score(y[valid_idx], base[valid_idx]))
        bucket_rows.append(
            {
                "fold": fold,
                "candidate_auc": candidate_auc,
                "base_auc": base_auc,
                "delta_vs_base": candidate_auc - base_auc,
            }
        )

    member_delta = float(results["oof_auc"] - roc_auc_score(y, base))
    member_wins = int(sum(row["delta_vs_base"] > 0 for row in bucket_rows))
    blend = crossfit_blend(y, base, candidate)
    results.update(
        {
            "model": "MLP + value embeddings + nested fold-wise TE, 3-seed bagging, 40 outer folds",
            "n_folds": 40,
            "outer_split_seed": 42,
            "base": "v61_income_bin10_te_lgbm_40f_depth4_seed104395303",
            "base_oof_auc": float(roc_auc_score(y, base)),
            "oof_delta_vs_base": member_delta,
            "fold_delta_vs_base": bucket_rows,
            "folds_won_vs_base": member_wins,
            "params": results.pop("hyper"),
            "validation_boundary": (
                "候选按预注册 seed42 训练；v61 实际训练种子为 104395303，"
                "40 行桶差异仅用于共同样本分区诊断，并非相同训练折配对。"
            ),
            "member_gate": {
                "minimum_oof_auc": 0.9458,
                "minimum_delta_vs_v61": 0.0001,
                "minimum_positive_buckets": 24,
                "passes": bool(
                    results["oof_auc"] >= 0.9458
                    and member_delta >= 0.0001
                    and member_wins >= 24
                ),
            },
            "blend_with_v61": blend,
            "accepted_for_p2_06": bool(blend["passes_gate"]),
        }
    )
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"P2-03 member delta={member_delta:+.9f}, bucket_wins={member_wins}/40, "
        f"blend delta={blend['oof_delta_vs_base']:+.9f}, "
        f"blend_wins={blend['folds_won_vs_base']}/5, accepted={results['accepted_for_p2_06']}",
        flush=True,
    )


def main() -> None:
    recipe = load_recipe()
    recipe.main()
    enrich_results()


if __name__ == "__main__":
    main()
