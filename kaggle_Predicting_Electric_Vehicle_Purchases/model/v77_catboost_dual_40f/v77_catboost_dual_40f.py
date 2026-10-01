# -*- coding: utf-8 -*-
"""P2-02：v10 CatBoost 双表示配方，40 折、两个模型种子，支持逐折续跑。"""

from __future__ import annotations

import gc
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool, __version__ as catboost_version
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
CHECKPOINT_DIR = OUT_DIR / "checkpoints"
MODEL_DIR = OUT_DIR.parent
PROJECT_DIR = OUT_DIR.parents[1]
RECIPE_PATH = MODEL_DIR / "v10_catboost_bag_10f" / "v10_catboost_bag_10f.py"
BASE_DIR = MODEL_DIR / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
OLD_LINEAGE_DIR = MODEL_DIR / "v10_catboost_bag_10f"
N_FOLDS = 40
OUTER_SEED = 42
META_GRID = np.linspace(0.0, 1.0, 101)


def load_recipe():
    spec = importlib.util.spec_from_file_location("v10_catboost_recipe", RECIPE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载配方：{RECIPE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(np.asarray(values, dtype=np.float64), method="average") / len(values)


def save_checkpoint(
    path: Path,
    valid_idx: np.ndarray,
    valid_pred: np.ndarray,
    test_pred: np.ndarray,
    best_iterations: list[int],
    importance: np.ndarray,
) -> None:
    temporary = path.with_suffix(".tmp.npz")
    np.savez_compressed(
        temporary,
        valid_idx=valid_idx,
        valid_pred=valid_pred,
        test_pred=test_pred,
        best_iterations=np.asarray(best_iterations, dtype=np.int32),
        importance=importance,
    )
    temporary.replace(path)


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
        fit_scores = np.array(
            [
                roc_auc_score(
                    y[fit_idx],
                    (1.0 - weight) * base_rank[fit_idx]
                    + weight * candidate_rank[fit_idx],
                )
                for weight in META_GRID
            ]
        )
        best_index = int(np.argmax(fit_scores))
        weight = float(META_GRID[best_index])
        weights.append(weight)
        blend_oof[valid_idx] = (
            (1.0 - weight) * base_rank[valid_idx]
            + weight * candidate_rank[valid_idx]
        )
        base_auc = float(roc_auc_score(y[valid_idx], base_rank[valid_idx]))
        blend_auc = float(roc_auc_score(y[valid_idx], blend_oof[valid_idx]))
        rows.append(
            {
                "fold": fold,
                "candidate_weight": weight,
                "fit_auc": float(fit_scores[best_index]),
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


def main() -> None:
    started = time.time()
    recipe = load_recipe()
    train, test, sample = recipe.load_data()
    x_train, x_test, categorical_cols = recipe.build_features(train, test)
    y = train[recipe.TARGET].eq(recipe.POS_LABEL).to_numpy(np.int8)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"train={train.shape}, test={test.shape}, features={x_train.shape[1]}, "
        f"categorical={len(categorical_cols)}, folds={N_FOLDS}, "
        f"bag_seeds={recipe.BAG_SEEDS}",
        flush=True,
    )

    oof = np.zeros(len(train), dtype=np.float64)
    test_prediction = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iterations: list[list[int]] = []
    importance_rows: list[np.ndarray] = []
    test_pool = Pool(x_test, cat_features=categorical_cols)
    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=OUTER_SEED)
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(x_train, y), 1):
        checkpoint = CHECKPOINT_DIR / f"fold_{fold:02d}.npz"
        if checkpoint.exists():
            saved = np.load(checkpoint)
            if not np.array_equal(saved["valid_idx"], valid_idx):
                raise ValueError(f"fold {fold} checkpoint 的行索引不匹配")
            valid_pred = saved["valid_pred"]
            fold_test = saved["test_pred"]
            fold_iterations = saved["best_iterations"].astype(int).tolist()
            fold_importance = saved["importance"]
            print(f"fold={fold} resumed from {checkpoint.name}", flush=True)
        else:
            fold_started = time.time()
            train_pool = Pool(
                x_train.iloc[fit_idx], y[fit_idx], cat_features=categorical_cols
            )
            valid_pool = Pool(
                x_train.iloc[valid_idx], y[valid_idx], cat_features=categorical_cols
            )
            valid_pred = np.zeros(len(valid_idx), dtype=np.float64)
            fold_test = np.zeros(len(test), dtype=np.float64)
            fold_iterations = []
            fold_importance = np.zeros(x_train.shape[1], dtype=np.float64)
            for seed in recipe.BAG_SEEDS:
                params = {**recipe.CAT_PARAMS, "random_seed": seed}
                model = CatBoostClassifier(**params)
                model.fit(train_pool, eval_set=valid_pool, use_best_model=True)
                one_valid = model.predict_proba(valid_pool)[:, 1]
                valid_pred += one_valid / len(recipe.BAG_SEEDS)
                fold_test += model.predict_proba(test_pool)[:, 1] / len(recipe.BAG_SEEDS)
                iteration = int(model.get_best_iteration() + 1)
                fold_iterations.append(iteration)
                fold_importance += model.get_feature_importance() / len(recipe.BAG_SEEDS)
                print(
                    f"  fold={fold} seed={seed} "
                    f"auc={roc_auc_score(y[valid_idx], one_valid):.6f} "
                    f"best_iteration={iteration}",
                    flush=True,
                )
            save_checkpoint(
                checkpoint,
                valid_idx,
                valid_pred,
                fold_test,
                fold_iterations,
                fold_importance,
            )
            print(
                f"fold={fold} checkpointed elapsed={time.time() - fold_started:.1f}s",
                flush=True,
            )
            del train_pool, valid_pool, model
            gc.collect()

        oof[valid_idx] = valid_pred
        test_prediction += fold_test / N_FOLDS
        score = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(score)
        best_iterations.append(fold_iterations)
        importance_rows.append(fold_importance)
        print(
            f"fold={fold}/{N_FOLDS} auc={score:.6f} "
            f"elapsed_total={time.time() - started:.1f}s",
            flush=True,
        )

    candidate_auc = float(roc_auc_score(y, oof))
    base = np.load(BASE_DIR / "oof_proba.npy")
    base_auc = float(roc_auc_score(y, base))
    bucket_rows = []
    comparison_splitter = StratifiedKFold(
        n_splits=40, shuffle=True, random_state=OUTER_SEED
    )
    for fold, (_, valid_idx) in enumerate(comparison_splitter.split(oof, y), 1):
        before = float(roc_auc_score(y[valid_idx], base[valid_idx]))
        after = float(roc_auc_score(y[valid_idx], oof[valid_idx]))
        bucket_rows.append(
            {
                "fold": fold,
                "candidate_auc": after,
                "base_auc": before,
                "delta_vs_base": after - before,
            }
        )
    blend = crossfit_blend(y, base, oof)
    old_lineage_auc = json.loads(
        (OLD_LINEAGE_DIR / "cv_results.json").read_text(encoding="utf-8")
    )["oof_auc"]
    single_gate = candidate_auc >= 0.9458
    accepted = bool(single_gate and blend["passes_gate"])

    submission = sample.copy()
    submission[recipe.TARGET] = test_prediction
    recipe.validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_prediction)
    importance = pd.DataFrame(
        {
            "feature": x_train.columns,
            "importance_mean": np.mean(importance_rows, axis=0),
            "importance_std": np.std(importance_rows, axis=0, ddof=1),
        }
    ).sort_values("importance_mean", ascending=False)
    importance.to_csv(OUT_DIR / "feature_importance.csv", index=False)

    results = {
        "competition": "playground-series-s6e9",
        "model": "CatBoost dual representation, 2-seed bagging, 40 outer folds",
        "n_folds": N_FOLDS,
        "outer_split_seed": OUTER_SEED,
        "fold_auc": fold_scores,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iterations,
        "oof_auc": candidate_auc,
        "base": "v61_income_bin10_te_lgbm_40f_depth4_seed104395303",
        "base_oof_auc": base_auc,
        "oof_delta_vs_base": candidate_auc - base_auc,
        "fold_delta_vs_base": bucket_rows,
        "folds_won_vs_base": int(
            sum(row["delta_vs_base"] > 0 for row in bucket_rows)
        ),
        "params": recipe.CAT_PARAMS,
        "bag_seeds": recipe.BAG_SEEDS,
        "lineage_base": "v10_catboost_bag_10f",
        "lineage_base_oof_auc": old_lineage_auc,
        "oof_delta_vs_lineage_base": candidate_auc - old_lineage_auc,
        "single_model_gate": {
            "minimum_oof_auc": 0.9458,
            "passes": bool(single_gate),
        },
        "blend_with_v61": blend,
        "accepted_for_p2_06": accepted,
        "validation_boundary": (
            "候选按预注册 seed42 训练；v61 实际训练种子为 104395303，"
            "40 行桶差异仅用于共同样本分区诊断，并非相同训练折配对。"
        ),
        "feature_count": int(x_train.shape[1]),
        "categorical_feature_count": len(categorical_cols),
        "prediction_min": float(test_prediction.min()),
        "prediction_max": float(test_prediction.max()),
        "prediction_mean": float(test_prediction.mean()),
        "elapsed_seconds": float(time.time() - started),
        "catboost_version": catboost_version,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"P2-02 OOF={candidate_auc:.9f}, delta_vs_v61={candidate_auc-base_auc:+.9f}, "
        f"blend_delta={blend['oof_delta_vs_base']:+.9f}, "
        f"blend_wins={blend['folds_won_vs_base']}/5, accepted={accepted}",
        flush=True,
    )
    print(f"submission={OUT_DIR / 'submission.csv'}", flush=True)


if __name__ == "__main__":
    main()
