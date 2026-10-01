# -*- coding: utf-8 -*-
"""v64：三种子 40 折家族、公开多样性成员与生成器先验的稳健秩融合。"""

from __future__ import annotations

import hashlib
import json
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
NAJI_OOF = OUT_DIR / "public_inputs" / "oof_LIGHTGBM.csv"
NAJI_TEST = OUT_DIR / "public_inputs" / "test_LIGHTGBM.csv"
ORIGINAL_DATA = DATA_DIR / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv"
SMART = MODEL_DIR / "v13_pb_v7_smart" / "public_inputs" / "submission.csv"
PB_V35 = MODEL_DIR / "v35_pb_v34_smart" / "submission.csv"

THREE_SEED_WEIGHTS = {"v59": 0.25, "v60": 0.375, "v61": 0.375}
V63_WEIGHT = 0.05
FAMILY_WEIGHT = 0.45
NAJI_WEIGHT = 0.12
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
    oof = np.load(directory / "oof_proba.npy")
    test = np.load(directory / "test_proba.npy")
    return percentile_rank(oof), percentile_rank(test)


def original_income_prior(
    frame: pd.DataFrame, original: pd.DataFrame
) -> np.ndarray:
    original_y = original[TARGET].eq("Yes").astype(np.float64)
    mapping = (
        pd.DataFrame(
            {
                "Annual_Income_USD": original["Annual_Income_USD"],
                "_target": original_y,
            }
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


def blend(
    v52: np.ndarray,
    v59: np.ndarray,
    v60: np.ndarray,
    v61: np.ndarray,
    v63: np.ndarray,
    naji: np.ndarray,
    original_prior: np.ndarray,
    rule_offsets: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    three_seed = percentile_rank(
        THREE_SEED_WEIGHTS["v59"] * v59
        + THREE_SEED_WEIGHTS["v60"] * v60
        + THREE_SEED_WEIGHTS["v61"] * v61
    )
    family = percentile_rank((1.0 - V63_WEIGHT) * three_seed + V63_WEIGHT * v63)
    core = percentile_rank((1.0 - FAMILY_WEIGHT) * v52 + FAMILY_WEIGHT * family)
    diverse = percentile_rank((1.0 - NAJI_WEIGHT) * core + NAJI_WEIGHT * naji)
    source_prior = percentile_rank(
        (1.0 - ORIGINAL_INCOME_PRIOR_WEIGHT) * diverse
        + ORIGINAL_INCOME_PRIOR_WEIGHT * original_prior
    )
    final = percentile_rank(source_prior + rule_offsets)
    return final, {
        "three_seed_40f": three_seed,
        "depth4_family": family,
        "core": core,
        "diverse": diverse,
        "source_prior": source_prior,
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

    local = {
        "v52": load_local(V52_DIR),
        "v59": load_local(V59_DIR),
        "v60": load_local(V60_DIR),
        "v61": load_local(V61_DIR),
        "v63": load_local(V63_DIR),
    }
    for name, (oof, prediction) in local.items():
        if len(oof) != len(train) or len(prediction) != len(test):
            raise ValueError(f"{name} 预测长度异常")

    naji_oof_frame = pd.read_csv(NAJI_OOF)
    naji_test_frame = pd.read_csv(NAJI_TEST)
    if not naji_oof_frame[ID_COL].equals(train[ID_COL]):
        raise ValueError("Naji OOF id 顺序异常")
    if not naji_test_frame[ID_COL].equals(test[ID_COL]):
        raise ValueError("Naji test id 顺序异常")
    naji_oof = percentile_rank(naji_oof_frame["OOF_Pred"])
    naji_test = percentile_rank(naji_test_frame[TARGET])
    original_oof = original_income_prior(train, original)
    original_test = original_income_prior(test, original)

    oof, stages = blend(
        local["v52"][0],
        local["v59"][0],
        local["v60"][0],
        local["v61"][0],
        local["v63"][0],
        naji_oof,
        original_oof,
        generator_rule_offsets(train),
    )
    test_prediction, test_stages = blend(
        local["v52"][1],
        local["v59"][1],
        local["v60"][1],
        local["v61"][1],
        local["v63"][1],
        naji_test,
        original_test,
        generator_rule_offsets(test),
    )
    base_oof = local["v52"][0]
    base_auc = float(roc_auc_score(y, base_oof))
    oof_auc = float(roc_auc_score(y, oof))

    seeds = [42, 2026, 3407, 8119, 104729, 130363, 15485863, 271828, 314159, 161803]
    fold_deltas: list[dict[str, float | int]] = []
    for seed in seeds:
        splitter = StratifiedKFold(5, shuffle=True, random_state=seed)
        for fold, (_, valid_idx) in enumerate(splitter.split(oof, y), 1):
            before = float(roc_auc_score(y[valid_idx], base_oof[valid_idx]))
            after = float(roc_auc_score(y[valid_idx], oof[valid_idx]))
            fold_deltas.append(
                {
                    "seed": seed,
                    "fold": fold,
                    "base_auc": before,
                    "auc": after,
                    "delta": after - before,
                }
            )

    submission = sample.copy()
    submission[TARGET] = test_prediction
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_prediction)

    component_auc = {
        name: float(roc_auc_score(y, pair[0])) for name, pair in local.items()
    }
    component_auc["naji_public"] = float(roc_auc_score(y, naji_oof))
    component_auc.update(
        {name: float(roc_auc_score(y, value)) for name, value in stages.items()}
    )
    test_correlations = {}
    for name, path in (("smart", SMART), ("pb_v35", PB_V35)):
        if path.exists():
            frame = pd.read_csv(path).set_index(ID_COL).reindex(test[ID_COL])
            test_correlations[name] = float(
                spearmanr(test_prediction, frame[TARGET].to_numpy()).statistic
            )
    test_correlations["v52"] = float(
        spearmanr(test_prediction, local["v52"][1]).statistic
    )

    deltas = np.array([row["delta"] for row in fold_deltas])
    results = {
        "competition": "playground-series-s6e9",
        "model": "robust three-seed 40-fold generator-aware rank ensemble",
        "weights": {
            "three_seed_40f": THREE_SEED_WEIGHTS,
            "v63_within_family": V63_WEIGHT,
            "depth4_family": FAMILY_WEIGHT,
            "naji_public": NAJI_WEIGHT,
            "original_income_prior": ORIGINAL_INCOME_PRIOR_WEIGHT,
        },
        "generator_rules": {
            "range_anxiety_high": -RULE_OFFSET,
            "income_38000_42000": -RULE_OFFSET,
            "income_ge_170537": RULE_OFFSET,
        },
        "component_oof_auc": component_auc,
        "base_v52_oof_auc": base_auc,
        "oof_auc": oof_auc,
        "delta_vs_v52": oof_auc - base_auc,
        "repeated_validation_fold_count": len(fold_deltas),
        "repeated_validation_positive_folds": int((deltas > 0).sum()),
        "repeated_validation_mean_delta": float(deltas.mean()),
        "repeated_validation_median_delta": float(np.median(deltas)),
        "repeated_validation_min_delta": float(deltas.min()),
        "repeated_validation_max_delta": float(deltas.max()),
        "fold_deltas": fold_deltas,
        "meta_weight_validation": {
            "outer_folds": 10,
            "positive_folds": 10,
            "mean_delta_vs_v52": 3.3473787817217546e-05,
            "min_delta_vs_v52": 1.5705215808070605e-05,
            "note": "weights selected on each outer fit block and evaluated on its held-out block",
        },
        "test_spearman": test_correlations,
        "prediction_min": float(test_prediction.min()),
        "prediction_max": float(test_prediction.max()),
        "prediction_mean": float(test_prediction.mean()),
        "rejected_final_tweak": {
            "id_mod_13_best_delta": 1.8386718247942468e-06,
            "positive_repeated_folds": 34,
            "reason": "small and unstable; excluded from submission",
        },
    }
    sources = {}
    for name, directory in (
        ("v52", V52_DIR),
        ("v59", V59_DIR),
        ("v60", V60_DIR),
        ("v61", V61_DIR),
        ("v63", V63_DIR),
    ):
        oof_path = directory / "oof_proba.npy"
        test_path = directory / "test_proba.npy"
        sources[name] = {
            "oof": str(oof_path.relative_to(OUT_DIR.parents[1])),
            "oof_sha256": sha256(oof_path),
            "test": str(test_path.relative_to(OUT_DIR.parents[1])),
            "test_sha256": sha256(test_path),
        }
    sources["naji_public"] = {
        "kernel": "najiama/pure-lgbm-model-cv-0-94587-lb-0-94612",
        "kernel_url": "https://www.kaggle.com/code/najiama/pure-lgbm-model-cv-0-94587-lb-0-94612",
        "reported_public_lb": 0.94612,
        "oof": str(NAJI_OOF.relative_to(OUT_DIR.parents[1])),
        "oof_sha256": sha256(NAJI_OOF),
        "test": str(NAJI_TEST.relative_to(OUT_DIR.parents[1])),
        "test_sha256": sha256(NAJI_TEST),
    }
    sources["original_dataset"] = {
        "path": str(ORIGINAL_DATA.relative_to(OUT_DIR.parents[1])),
        "sha256": sha256(ORIGINAL_DATA),
        "usage": "exact-income target mean as a 0.4 percent rank prior",
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "sources.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {key: value for key, value in results.items() if key != "fold_deltas"}
    (OUT_DIR / "train_log.txt").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
