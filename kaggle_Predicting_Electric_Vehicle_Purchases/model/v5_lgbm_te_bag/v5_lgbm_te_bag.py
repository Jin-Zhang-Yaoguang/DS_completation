# -*- coding: utf-8 -*-
"""
v5：v2 配方 + 通勤/年龄精确值 TE（消融 E4，+0.00012）+ 3 种子 bagging。

赛题：Predicting Electric Vehicle Purchases（Playground Series S6E9）
指标：ROC AUC

在 v2 基础上的改动：
- 新增折内 TE：Daily_Commute_km 精确值、Age 精确值（消融 E4：OOF +0.00012，4/5 折）；
- 3 个种子（模型随机性 + 内层 TE 划分）在同一外层折划分下 bagging，OOF/测试概率取平均；
- 已否定并移除：尾数指示、是否在原始集（v2 增益接近零）。

探索依据（见 model/experiments.md「收入伪影探索」）：
- 收入精确值的折外目标编码单特征 AUC 0.711，高于原值 0.670；
- 收入与 Subsidy / Environmental_Concern_Level 的联合键目标编码分别达 0.826 / 0.861；
- 收入 = 30,000 的单值占 9.2% 行，v1 在该子集 AUC 仅 0.915；
- 收入值 97.9% 落在原始数据集的取值集合内。

泄漏控制：
- 无标签特征（频次、是否在原始集、尾数）用 train+test 全量计算；
- 目标编码在外层每折内计算：训练折部分用内层 5 折 OOF，验证折与测试集用整个训练折统计；
- 对比基准 v1（同 seed 同折）。
"""

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
N_INNER = 5
TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"
INCOME = "Annual_Income_USD"
TE_SMOOTH = 10.0

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
ORIG_PATH = DATA_DIR / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv"
OUT_DIR = Path(__file__).resolve().parent
BASE_RESULTS = OUT_DIR.parent / "v2_income_artifact_lgbm" / "cv_results.json"

CAT_COLS = [
    "Gender",
    "City_Type",
    "Current_Car_Type",
    "Home_Charging_Possible",
    "Subsidy_Available",
    "Range_Anxiety_Level",
]

# 目标编码键：名称 -> 参与拼键的列
TE_KEYS = {
    "te_inc": [INCOME],
    "te_inc_bin100": ["_inc_bin100"],
    "te_inc_subsidy": [INCOME, "Subsidy_Available"],
    "te_inc_env": [INCOME, "Environmental_Concern_Level"],
    "te_commute": ["Daily_Commute_km"],
    "te_age": ["Age"],
}
BAG_SEEDS = [42, 2026, 7]

LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "n_estimators": 4000,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "max_depth": -1,
    "min_child_samples": 50,
    "subsample": 0.9,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "random_state": SEED,
    "bagging_seed": SEED,
    "feature_fraction_seed": SEED,
    "data_random_seed": SEED,
    "deterministic": True,
    "force_col_wise": True,
    "n_jobs": 8,
    "verbosity": -1,
}
EARLY_STOPPING_ROUNDS = 200


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if TARGET not in train or TARGET in test:
        raise ValueError("训练集/测试集目标列不符合预期")
    if train[ID_COL].duplicated().any() or test[ID_COL].duplicated().any():
        raise ValueError("发现重复 id")
    if set(train[TARGET].unique()) != {"No", "Yes"}:
        raise ValueError(f"目标列取值异常：{train[TARGET].unique()}")
    if not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("sample_submission.csv 的 id 顺序与 test.csv 不一致")
    if train.isna().any().any() or test.isna().any().any():
        raise ValueError("数据出现缺失值，与初始化核验不符")
    return train, test, sample


def build_static_features(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.Series], dict[str, pd.Series]]:
    """无标签特征 + 目标编码键。返回特征表与 train/test 的键序列。"""
    feat_cols = [c for c in test.columns if c != ID_COL]
    x_train = train[feat_cols].copy()
    x_test = test[feat_cols].copy()

    for col in CAT_COLS:
        categories = sorted(set(x_train[col].unique()) | set(x_test[col].unique()))
        dtype = pd.CategoricalDtype(categories=categories)
        x_train[col] = x_train[col].astype(dtype)
        x_test[col] = x_test[col].astype(dtype)

    inc_all = pd.concat([train[INCOME], test[INCOME]], ignore_index=True)
    freq = inc_all.value_counts()
    for source, output in ((train, x_train), (test, x_test)):
        inc = source[INCOME]
        output["inc_freq"] = inc.map(freq).astype(np.float32)

    keys_train: dict[str, pd.Series] = {}
    keys_test: dict[str, pd.Series] = {}
    for name, cols in TE_KEYS.items():
        parts_train, parts_test = [], []
        for col in cols:
            if col == "_inc_bin100":
                parts_train.append((train[INCOME] // 100).astype(np.int64).astype(str))
                parts_test.append((test[INCOME] // 100).astype(np.int64).astype(str))
            else:
                parts_train.append(train[col].astype(str))
                parts_test.append(test[col].astype(str))
        keys_train[name] = pd.Series(
            ["|".join(t) for t in zip(*parts_train)], index=train.index
        )
        keys_test[name] = pd.Series(
            ["|".join(t) for t in zip(*parts_test)], index=test.index
        )

    if list(x_train.columns) != list(x_test.columns):
        raise ValueError("训练集与测试集特征列不一致")
    return x_train, x_test, keys_train, keys_test


def smoothed_te(
    key_fit: pd.Series, y_fit: np.ndarray, key_apply: pd.Series, prior: float
) -> np.ndarray:
    stats = pd.DataFrame({"k": key_fit.to_numpy(), "y": y_fit}).groupby("k")["y"].agg(["sum", "count"])
    s = key_apply.map(stats["sum"]).fillna(0.0).to_numpy()
    c = key_apply.map(stats["count"]).fillna(0.0).to_numpy()
    return (s + prior * TE_SMOOTH) / (c + TE_SMOOTH)


def fold_target_encoding(
    key_tr: pd.Series,
    y_tr: np.ndarray,
    key_va: pd.Series,
    key_te: pd.Series,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """训练折：内层 OOF；验证折/测试：整个训练折统计。"""
    prior = float(y_tr.mean())
    key_tr = key_tr.reset_index(drop=True)
    tr_enc = np.zeros(len(key_tr), dtype=np.float64)
    inner = StratifiedKFold(n_splits=N_INNER, shuffle=True, random_state=seed)
    for a, b in inner.split(key_tr, y_tr):
        tr_enc[b] = smoothed_te(key_tr.iloc[a], y_tr[a], key_tr.iloc[b], prior)
    va_enc = smoothed_te(key_tr, y_tr, key_va, prior)
    te_enc = smoothed_te(key_tr, y_tr, key_te, prior)
    return tr_enc, va_enc, te_enc


def validate_submission(
    submission: pd.DataFrame, test: pd.DataFrame, sample: pd.DataFrame
) -> None:
    if submission.shape != sample.shape:
        raise ValueError(f"提交 shape 错误：{submission.shape} != {sample.shape}")
    if list(submission.columns) != [ID_COL, TARGET]:
        raise ValueError(f"提交列名错误：{submission.columns.tolist()}")
    if not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交 id 与测试集不一致")
    pred = submission[TARGET].to_numpy()
    if not np.isfinite(pred).all() or ((pred < 0.0) | (pred > 1.0)).any():
        raise ValueError("提交概率包含非法值")


def main() -> None:
    start = time.time()
    train, test, sample = load_data()
    x_train, x_test, keys_train, keys_test = build_static_features(train, test)
    y = (train[TARGET] == POS_LABEL).to_numpy(dtype=np.int8)
    te_names = list(TE_KEYS)
    all_feature_names = list(x_train.columns) + te_names

    print(f"train={train.shape}, test={test.shape}, features={len(all_feature_names)}")

    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros(len(train), dtype=np.float64)
    test_pred = np.zeros(len(test), dtype=np.float64)
    fold_scores: list[float] = []
    best_iters: list[int] = []
    importance_frames: list[pd.DataFrame] = []

    for fold, (train_idx, valid_idx) in enumerate(splitter.split(x_train, y), start=1):
        fold_start = time.time()
        x_tr = x_train.iloc[train_idx].reset_index(drop=True)
        x_va = x_train.iloc[valid_idx].reset_index(drop=True)
        x_te = x_test.copy()
        valid_pred = np.zeros(len(valid_idx), dtype=np.float64)
        fold_test = np.zeros(len(test), dtype=np.float64)
        fold_iters: list[int] = []
        for seed in BAG_SEEDS:
            for name in te_names:
                tr_enc, va_enc, te_enc = fold_target_encoding(
                    keys_train[name].iloc[train_idx],
                    y[train_idx],
                    keys_train[name].iloc[valid_idx],
                    keys_test[name],
                    seed=seed + fold,
                )
                x_tr[name] = tr_enc
                x_va[name] = va_enc
                x_te[name] = te_enc
            params = {**LGB_PARAMS, "random_state": seed, "bagging_seed": seed,
                      "feature_fraction_seed": seed, "data_random_seed": seed}
            model = lgb.LGBMClassifier(**params)
            model.fit(
                x_tr,
                y[train_idx],
                eval_set=[(x_va, y[valid_idx])],
                eval_metric="auc",
                categorical_feature=CAT_COLS,
                callbacks=[
                    lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            best_iter = int(model.best_iteration_ or LGB_PARAMS["n_estimators"])
            fold_iters.append(best_iter)
            valid_pred += model.predict_proba(x_va, num_iteration=best_iter)[:, 1] / len(BAG_SEEDS)
            fold_test += model.predict_proba(x_te, num_iteration=best_iter)[:, 1] / len(BAG_SEEDS)
            print(f"  fold={fold} seed={seed} auc={roc_auc_score(y[valid_idx], model.predict_proba(x_va, num_iteration=best_iter)[:, 1]):.6f} best_iter={best_iter}", flush=True)
        best_iters.append(int(np.mean(fold_iters)))
        oof[valid_idx] = valid_pred
        test_pred += fold_test / N_FOLDS

        fold_auc = float(roc_auc_score(y[valid_idx], valid_pred))
        fold_scores.append(fold_auc)
        importance_frames.append(
            pd.DataFrame(
                {
                    "feature": x_tr.columns,
                    "gain": model.booster_.feature_importance(importance_type="gain"),
                    "split": model.booster_.feature_importance(importance_type="split"),
                    "fold": fold,
                }
            )
        )
        print(
            f"fold={fold} auc={fold_auc:.6f} best_iter={best_iter} "
            f"elapsed={time.time() - fold_start:.1f}s",
            flush=True,
        )

    oof_auc = float(roc_auc_score(y, oof))
    elapsed = time.time() - start
    base = json.loads(BASE_RESULTS.read_text(encoding="utf-8"))
    base_fold = np.asarray(base["fold_auc"], dtype=float)
    fold_deltas = np.asarray(fold_scores) - base_fold
    oof_delta = oof_auc - float(base["oof_auc"])
    print(
        f"OOF AUC={oof_auc:.6f}, delta_vs_v2={oof_delta:+.6f}, "
        f"folds_won={(fold_deltas > 0).sum()}/{N_FOLDS}"
    )
    print("fold_deltas=" + ", ".join(f"{d:+.6f}" for d in fold_deltas))

    submission = sample.copy()
    submission[TARGET] = test_pred
    validate_submission(submission, test, sample)
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)

    importance = pd.concat(importance_frames, ignore_index=True)
    importance_summary = (
        importance.groupby("feature", as_index=False)
        .agg(gain_mean=("gain", "mean"), gain_std=("gain", "std"), split_mean=("split", "mean"))
        .sort_values("gain_mean", ascending=False)
    )
    importance_summary.to_csv(OUT_DIR / "feature_importance.csv", index=False)
    print(importance_summary.to_string(index=False))

    results = {
        "competition": "playground-series-s6e9",
        "model": "LightGBM + income/commute/age fold-wise TE, 3-seed bagging",
        "seed": SEED,
        "n_folds": N_FOLDS,
        "n_inner_folds": N_INNER,
        "te_smooth": TE_SMOOTH,
        "te_keys": TE_KEYS,
        "bag_seeds": BAG_SEEDS,
        "feature_count": len(all_feature_names),
        "features": all_feature_names,
        "fold_auc": fold_scores,
        "fold_auc_mean": float(np.mean(fold_scores)),
        "fold_auc_std": float(np.std(fold_scores)),
        "best_iterations": best_iters,
        "oof_auc": oof_auc,
        "base": "v2_income_artifact_lgbm",
        "base_oof_auc": float(base["oof_auc"]),
        "oof_delta_vs_base": oof_delta,
        "fold_delta_vs_base": fold_deltas.tolist(),
        "folds_won_vs_base": int((fold_deltas > 0).sum()),
        "prediction_min": float(test_pred.min()),
        "prediction_max": float(test_pred.max()),
        "prediction_mean": float(test_pred.mean()),
        "elapsed_seconds": elapsed,
        "lightgbm_version": lgb.__version__,
        "params": LGB_PARAMS,
        "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
    }
    (OUT_DIR / "cv_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"submission={OUT_DIR / 'submission.csv'}")
    print(f"elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
