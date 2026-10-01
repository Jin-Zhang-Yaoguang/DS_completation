# -*- coding: utf-8 -*-
"""v72：40 折主家族与两种 Naji 20 折模型的稳健秩融合。"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
TARGET = "Will_Buy_EV"
ID_COL = "id"

V52_DIR = MODEL_DIR / "v52_robust_rank_ensemble_v51"
V59_DIR = MODEL_DIR / "v59_income_bin10_te_lgbm_40f_depth4"
V60_DIR = MODEL_DIR / "v60_income_bin10_te_lgbm_40f_depth4_seed86028121"
V61_DIR = MODEL_DIR / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
V63_DIR = MODEL_DIR / "v63_original_target_prior_lgbm_40f_depth4"
V64_DIR = MODEL_DIR / "v64_robust_40f_generator_ensemble"
V69_DIR = MODEL_DIR / "v69_naji_lgbm_20f"
V71_DIR = MODEL_DIR / "v71_naji_income_bin10_lgbm_20f"
PB_V35 = MODEL_DIR / "v35_pb_v34_smart" / "submission.csv"
ORIGINAL_DATA = DATA_DIR / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv"

THREE_SEED_WEIGHTS = {"v59": 0.25, "v60": 0.375, "v61": 0.375}
V63_WEIGHT = 0.05
FAMILY_WEIGHT = 0.45
V69_WEIGHT = 0.14
V71_WEIGHT = 0.15
ORIGINAL_INCOME_PRIOR_WEIGHT = 0.004
RULE_OFFSET = 0.1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile_rank(values: np.ndarray | pd.Series) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or not np.isfinite(array).all():
        raise ValueError("预测必须是一维有限数值")
    return rankdata(array, method="average") / len(array)


def load_local(directory: Path) -> tuple[np.ndarray, np.ndarray]:
    return (
        percentile_rank(np.load(directory / "oof_proba.npy")),
        percentile_rank(np.load(directory / "test_proba.npy")),
    )


def build_core(parts: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    three_seed = percentile_rank(
        THREE_SEED_WEIGHTS["v59"] * parts["v59"]
        + THREE_SEED_WEIGHTS["v60"] * parts["v60"]
        + THREE_SEED_WEIGHTS["v61"] * parts["v61"]
    )
    family = percentile_rank((1.0 - V63_WEIGHT) * three_seed + V63_WEIGHT * parts["v63"])
    core = percentile_rank((1.0 - FAMILY_WEIGHT) * parts["v52"] + FAMILY_WEIGHT * family)
    return core, {"three_seed_40f": three_seed, "depth4_family": family}


def original_income_prior(frame: pd.DataFrame, original: pd.DataFrame) -> np.ndarray:
    original_y = original[TARGET].eq("Yes").astype(np.float64)
    mapping = (
        pd.DataFrame(
            {"Annual_Income_USD": original["Annual_Income_USD"], "_target": original_y}
        )
        .groupby("Annual_Income_USD", dropna=False)["_target"]
        .mean()
    )
    values = frame["Annual_Income_USD"].map(mapping).fillna(float(original_y.mean()))
    return percentile_rank(values)


def generator_rule_offsets(frame: pd.DataFrame) -> np.ndarray:
    offset = np.zeros(len(frame), dtype=np.float64)
    offset[frame["Range_Anxiety_Level"].eq("High").to_numpy()] -= RULE_OFFSET
    offset[frame["Annual_Income_USD"].between(38_000, 42_000).to_numpy()] -= RULE_OFFSET
    offset[frame["Annual_Income_USD"].ge(170_537).to_numpy()] += RULE_OFFSET
    return offset


def diverse_blend(
    core: np.ndarray,
    v69: np.ndarray,
    v71: np.ndarray,
    v69_weight: float,
    v71_weight: float,
) -> np.ndarray:
    if v69_weight < 0 or v71_weight < 0 or v69_weight + v71_weight >= 1:
        raise ValueError("多样性权重非法")
    return percentile_rank(
        (1.0 - v69_weight - v71_weight) * core
        + v69_weight * v69
        + v71_weight * v71
    )


def apply_external_prior(
    prediction: np.ndarray, original_prior: np.ndarray, rule_offsets: np.ndarray
) -> np.ndarray:
    source_prior = percentile_rank(
        (1.0 - ORIGINAL_INCOME_PRIOR_WEIGHT) * prediction
        + ORIGINAL_INCOME_PRIOR_WEIGHT * original_prior
    )
    return percentile_rank(source_prior + rule_offsets)


def final_blend(
    core: np.ndarray,
    v69: np.ndarray,
    v71: np.ndarray,
    original_prior: np.ndarray,
    rule_offsets: np.ndarray,
    v69_weight: float = V69_WEIGHT,
    v71_weight: float = V71_WEIGHT,
) -> np.ndarray:
    diverse = diverse_blend(core, v69, v71, v69_weight, v71_weight)
    return apply_external_prior(diverse, original_prior, rule_offsets)


def outer_weight_validation(
    y: np.ndarray,
    core: np.ndarray,
    v69: np.ndarray,
    v71: np.ndarray,
    original_prior: np.ndarray,
    rule_offsets: np.ndarray,
) -> dict[str, object]:
    totals = (0.24, 0.27, 0.30, 0.33, 0.36)
    v71_shares = (0.35, 0.425, 0.50, 0.575, 0.65)
    grid = [
        (round(total * (1.0 - share), 6), round(total * share, 6))
        for total in totals
        for share in v71_shares
    ]
    predictions = np.vstack(
        [
            final_blend(core, v69, v71, original_prior, rule_offsets, w69, w71)
            for w69, w71 in grid
        ]
    ).astype(np.float32)
    base = apply_external_prior(core, original_prior, rule_offsets)
    splitter = StratifiedKFold(n_splits=10, shuffle=True, random_state=20260903)
    rows: list[dict[str, float | int]] = []
    choices: list[tuple[float, float]] = []
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(core, y), 1):
        fit_scores = [roc_auc_score(y[fit_idx], candidate[fit_idx]) for candidate in predictions]
        best_index = int(np.argmax(fit_scores))
        selected = predictions[best_index]
        w69, w71 = grid[best_index]
        choices.append((w69, w71))
        before = float(roc_auc_score(y[valid_idx], base[valid_idx]))
        after = float(roc_auc_score(y[valid_idx], selected[valid_idx]))
        rows.append(
            {
                "fold": fold,
                "selected_v69_weight": w69,
                "selected_v71_weight": w71,
                "fit_auc": float(fit_scores[best_index]),
                "base_auc": before,
                "auc": after,
                "delta": after - before,
            }
        )
    deltas = np.array([row["delta"] for row in rows], dtype=np.float64)
    counts = Counter(f"{w69:.6f},{w71:.6f}" for w69, w71 in choices)
    return {
        "grid": [{"v69_weight": w69, "v71_weight": w71} for w69, w71 in grid],
        "fold_count": len(rows),
        "positive_folds": int((deltas > 0).sum()),
        "mean_delta_vs_core_with_prior_rules": float(deltas.mean()),
        "median_delta_vs_core_with_prior_rules": float(np.median(deltas)),
        "min_delta_vs_core_with_prior_rules": float(deltas.min()),
        "max_delta_vs_core_with_prior_rules": float(deltas.max()),
        "selection_counts": dict(sorted(counts.items())),
        "fold_rows": rows,
    }


def repeated_validation(
    y: np.ndarray, prediction: np.ndarray, baselines: dict[str, np.ndarray]
) -> dict[str, object]:
    seeds = [42, 2026, 3407, 8119, 104729, 130363, 15485863, 271828, 314159, 161803]
    results: dict[str, object] = {}
    for name, baseline in baselines.items():
        rows: list[dict[str, float | int]] = []
        for seed in seeds:
            splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
            for fold, (_, valid_idx) in enumerate(splitter.split(prediction, y), 1):
                before = float(roc_auc_score(y[valid_idx], baseline[valid_idx]))
                after = float(roc_auc_score(y[valid_idx], prediction[valid_idx]))
                rows.append(
                    {
                        "seed": seed,
                        "fold": fold,
                        "base_auc": before,
                        "auc": after,
                        "delta": after - before,
                    }
                )
        deltas = np.array([row["delta"] for row in rows], dtype=np.float64)
        results[name] = {
            "fold_count": len(rows),
            "positive_folds": int((deltas > 0).sum()),
            "mean_delta": float(deltas.mean()),
            "median_delta": float(np.median(deltas)),
            "min_delta": float(deltas.min()),
            "max_delta": float(deltas.max()),
            "fold_rows": rows,
        }
    return results


def matched_naji_fold_validation(
    y: np.ndarray, v69: np.ndarray, v71: np.ndarray
) -> dict[str, object]:
    rows: list[dict[str, float | int]] = []
    splitter = StratifiedKFold(n_splits=20, shuffle=True, random_state=42)
    for fold, (_, valid_idx) in enumerate(splitter.split(v69, y), 1):
        before = float(roc_auc_score(y[valid_idx], v69[valid_idx]))
        after = float(roc_auc_score(y[valid_idx], v71[valid_idx]))
        rows.append(
            {
                "fold": fold,
                "v69_auc": before,
                "v71_auc": after,
                "delta": after - before,
            }
        )
    deltas = np.array([row["delta"] for row in rows], dtype=np.float64)
    return {
        "fold_count": len(rows),
        "positive_folds": int((deltas > 0).sum()),
        "mean_delta": float(deltas.mean()),
        "median_delta": float(np.median(deltas)),
        "min_delta": float(deltas.min()),
        "max_delta": float(deltas.max()),
        "fold_rows": rows,
    }


def validate_submission(
    submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame
) -> None:
    if submission.shape != sample.shape or list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError("提交 shape 或列名异常")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 顺序异常")
    prediction = submission[TARGET].to_numpy()
    if not np.isfinite(prediction).all() or ((prediction < 0) | (prediction > 1)).any():
        raise ValueError("提交概率非法")


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    original = pd.read_csv(ORIGINAL_DATA)
    y = train[TARGET].eq("Yes").to_numpy(np.int8)

    directories = {
        "v52": V52_DIR,
        "v59": V59_DIR,
        "v60": V60_DIR,
        "v61": V61_DIR,
        "v63": V63_DIR,
        "v69": V69_DIR,
        "v71": V71_DIR,
    }
    local = {name: load_local(directory) for name, directory in directories.items()}
    if any(len(pair[0]) != len(train) or len(pair[1]) != len(test) for pair in local.values()):
        raise ValueError("源预测长度异常")

    train_parts = {name: pair[0] for name, pair in local.items()}
    test_parts = {name: pair[1] for name, pair in local.items()}
    core_oof, core_stages = build_core(train_parts)
    core_test, _ = build_core(test_parts)
    original_oof = original_income_prior(train, original)
    original_test = original_income_prior(test, original)
    oof = final_blend(
        core_oof,
        local["v69"][0],
        local["v71"][0],
        original_oof,
        generator_rule_offsets(train),
    )
    test_prediction = final_blend(
        core_test,
        local["v69"][1],
        local["v71"][1],
        original_test,
        generator_rule_offsets(test),
    )

    submission = sample.copy()
    submission[TARGET] = test_prediction
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_prediction)

    v64_oof, v64_test = load_local(V64_DIR)
    core_with_prior_rules = apply_external_prior(
        core_oof, original_oof, generator_rule_offsets(train)
    )
    component_auc = {
        name: float(roc_auc_score(y, pair[0])) for name, pair in local.items()
    }
    component_auc.update(
        {name: float(roc_auc_score(y, values)) for name, values in core_stages.items()}
    )
    component_auc["core"] = float(roc_auc_score(y, core_oof))
    component_auc["core_with_prior_rules"] = float(
        roc_auc_score(y, core_with_prior_rules)
    )
    oof_auc = float(roc_auc_score(y, oof))

    test_correlations = {
        "v52": float(spearmanr(test_prediction, local["v52"][1]).statistic),
        "v64": float(spearmanr(test_prediction, v64_test).statistic),
        "v69": float(spearmanr(test_prediction, local["v69"][1]).statistic),
        "v71": float(spearmanr(test_prediction, local["v71"][1]).statistic),
        "v69_vs_v71": float(
            spearmanr(local["v69"][1], local["v71"][1]).statistic
        ),
    }
    if PB_V35.exists():
        pb = pd.read_csv(PB_V35).set_index(ID_COL).reindex(test[ID_COL])
        test_correlations["pb_v35"] = float(
            spearmanr(test_prediction, pb[TARGET].to_numpy()).statistic
        )

    baselines = {
        "v52": local["v52"][0],
        "core": core_oof,
        "core_with_prior_rules": core_with_prior_rules,
        "v64": v64_oof,
    }
    results = {
        "competition": "playground-series-s6e9",
        "model": "robust 40-fold core plus plain and income-bin10 Naji 20-fold rank bag",
        "hypothesis": (
            "income-bin10 improves the independent Naji lineage, while bagging it with the "
            "smoother unbinned Naji model preserves complementary ranking errors"
        ),
        "weights": {
            "three_seed_40f": THREE_SEED_WEIGHTS,
            "v63_within_family": V63_WEIGHT,
            "depth4_family": FAMILY_WEIGHT,
            "v69_plain_naji_20f": V69_WEIGHT,
            "v71_income_bin10_naji_20f": V71_WEIGHT,
            "original_income_prior": ORIGINAL_INCOME_PRIOR_WEIGHT,
        },
        "generator_rules": {
            "range_anxiety_high": -RULE_OFFSET,
            "income_38000_42000": -RULE_OFFSET,
            "income_ge_170537": RULE_OFFSET,
        },
        "component_oof_auc": component_auc,
        "oof_auc": oof_auc,
        "delta_vs_v52": oof_auc - float(roc_auc_score(y, local["v52"][0])),
        "delta_vs_core": oof_auc - float(roc_auc_score(y, core_oof)),
        "delta_vs_v64": oof_auc - float(roc_auc_score(y, v64_oof)),
        "matched_naji_fold_validation": matched_naji_fold_validation(
            y, local["v69"][0], local["v71"][0]
        ),
        "outer_weight_validation": outer_weight_validation(
            y,
            core_oof,
            local["v69"][0],
            local["v71"][0],
            original_oof,
            generator_rule_offsets(train),
        ),
        "fixed_weight_repeated_validation": repeated_validation(y, oof, baselines),
        "test_spearman": test_correlations,
        "prediction_min": float(test_prediction.min()),
        "prediction_max": float(test_prediction.max()),
        "prediction_mean": float(test_prediction.mean()),
    }
    results["sources"] = {
        name: {
            "oof_sha256": sha256(directory / "oof_proba.npy"),
            "test_sha256": sha256(directory / "test_proba.npy"),
        }
        for name, directory in directories.items()
    }
    with (OUT_DIR / "cv_results.json").open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    outer = results["outer_weight_validation"]
    repeated = results["fixed_weight_repeated_validation"]
    print(f"v72 OOF AUC: {oof_auc:.12f}")
    print(f"Delta vs v52: {results['delta_vs_v52']:+.12f}")
    print(f"Delta vs v64: {results['delta_vs_v64']:+.12f}")
    print(
        "Outer weight validation: "
        f"{outer['positive_folds']}/{outer['fold_count']} positive, "
        f"mean={outer['mean_delta_vs_core_with_prior_rules']:+.12f}, "
        f"min={outer['min_delta_vs_core_with_prior_rules']:+.12f}"
    )
    for name, audit in repeated.items():
        print(
            f"Fixed vs {name}: {audit['positive_folds']}/{audit['fold_count']} positive, "
            f"mean={audit['mean_delta']:+.12f}, min={audit['min_delta']:+.12f}"
        )
    print(f"Saved: {OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
