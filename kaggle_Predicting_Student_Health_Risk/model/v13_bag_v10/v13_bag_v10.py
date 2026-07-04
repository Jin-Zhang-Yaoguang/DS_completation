# -*- coding: utf-8 -*-
"""
方案 v13：v10 配方 × 10 种子 bagging（纯方差缩减）

变化源：HGBC random_state（影响 max_features=0.82 的特征子采样与早停验证切分）
+ TargetEncoder shuffle 种子。CV 折划分保持冻结（seed 42），OOF 概率跨种子平均。
种子 0 = 精确复现 v10（HGBC rs=0, TE seed=42），故 bagging 曲线的第一个点
应等于 v10 的 0.95052，后续每加一个种子看边际增益。

预期：+0.0001~0.0003（方差缩减无假设风险）；输出累积 bagging 曲线以验证收敛。
"""

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import TargetEncoder

SEED = 42          # 冻结 CV 折划分，勿动
N_FOLDS = 5
N_SEEDS = 10
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

CAT_COLS = ["diet_type", "stress_level", "sleep_quality",
            "physical_activity_level", "smoking_alcohol", "gender"]
NUM_COLS = ["sleep_duration", "heart_rate", "bmi", "calorie_expenditure",
            "step_count", "exercise_duration", "water_intake"]
RAW = NUM_COLS + CAT_COLS
TARGET = "health_condition"

BASE_CONFIG = dict(
    learning_rate=0.0627037115235577,
    max_iter=300,
    max_leaf_nodes=33,
    min_samples_leaf=298,
    l2_regularization=0.028912644384523085,
    max_bins=237,
    max_features=0.820265066682815,
    early_stopping=True,
    categorical_features="from_dtype",
)


def balanced_weights(yy):
    counts = np.bincount(yy, minlength=3)
    return (len(yy) / (3 * counts))[yy]


def make_bacc(y):
    masks = [y == k for k in range(3)]

    def bacc(pred):
        return np.mean([(pred[m] == k).mean() for k, m in enumerate(masks)])
    return bacc


def search_class_weights(proba, y):
    bacc = make_bacc(y)

    def _grid(g1, g2, best):
        for w1, w2 in product(g1, g2):
            s = bacc((proba * np.array([1.0, w1, w2])).argmax(1))
            if s > best[0]:
                best = (s, w1, w2)
        return best

    best = _grid(np.linspace(1, 12, 45), np.linspace(1, 12, 45),
                 (bacc(proba.argmax(1)), 1.0, 1.0))
    s, w1, w2 = _grid(np.linspace(max(0.5, best[1] - 0.3), best[1] + 0.3, 25),
                      np.linspace(max(0.5, best[2] - 0.3), best[2] + 0.3, 25), best)
    return s, np.array([1.0, w1, w2])


def sleep_bucket(s):
    v = pd.to_numeric(s, errors="coerce")
    out = pd.Series(np.where(v < 6, "lt6", np.where(v < 7, "6to7", "ge7")), index=s.index)
    out[v.isna()] = "na"
    return out


def main():
    t0 = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    print(f"train {train.shape} | test {test.shape}", flush=True)

    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    X, X_test = train[RAW].copy(), test[RAW].copy()
    for c in CAT_COLS:
        X[c] = X[c].astype("category")
        X_test[c] = X_test[c].astype("category").cat.set_categories(X[c].cat.categories)

    Xs = train[RAW].astype(str)
    Xs_test = test[RAW].astype(str)
    Xs["k_cell"] = (sleep_bucket(train["sleep_duration"]) + "|"
                    + Xs["stress_level"] + "|" + Xs["physical_activity_level"])
    Xs_test["k_cell"] = (sleep_bucket(test["sleep_duration"]) + "|"
                         + Xs_test["stress_level"] + "|" + Xs_test["physical_activity_level"])
    TE_COLS = RAW + ["k_cell"]
    te_names = [f"te_{c}_{k}" for c in TE_COLS for k in range(3)]

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    folds = list(skf.split(X, y))

    oof_sum = np.zeros((len(X), 3))
    test_sum = np.zeros((len(X_test), 3))
    bacc = make_bacc(y)

    for seed in range(N_SEEDS):
        ts = time.time()
        te_seed = 42 + seed          # seed 0 → TE seed 42 = 复现 v10
        oof_s = np.zeros((len(X), 3))

        for fold, (tr, va) in enumerate(folds):
            enc = TargetEncoder(cv=5, smooth="auto", shuffle=True, random_state=te_seed)
            Z_tr = enc.fit_transform(Xs[TE_COLS].iloc[tr], y[tr])
            Z_va = enc.transform(Xs[TE_COLS].iloc[va])
            Z_te = enc.transform(Xs_test[TE_COLS])

            A_tr = pd.concat([X.iloc[tr].reset_index(drop=True),
                              pd.DataFrame(Z_tr, columns=te_names)], axis=1)
            A_va = pd.concat([X.iloc[va].reset_index(drop=True),
                              pd.DataFrame(Z_va, columns=te_names)], axis=1)
            A_te = pd.concat([X_test.reset_index(drop=True),
                              pd.DataFrame(Z_te, columns=te_names)], axis=1)

            model = HistGradientBoostingClassifier(**BASE_CONFIG, random_state=seed)
            model.fit(A_tr, y[tr], sample_weight=balanced_weights(y[tr]))
            oof_s[va] = model.predict_proba(A_va)
            test_sum += model.predict_proba(A_te) / (N_FOLDS * N_SEEDS)

        oof_sum += oof_s
        # 累积 bagging 曲线（每个种子后重搜权重）
        cum = oof_sum / (seed + 1)
        cv_w, w = search_class_weights(cum, y)
        print(f"seed {seed}: 单种子加权 {search_class_weights(oof_s, y)[0]:.5f} | "
              f"累积{seed+1}种子加权 {cv_w:.5f} (w={w[1]:.3f},{w[2]:.3f}) | {time.time()-ts:.0f}s",
              flush=True)

    oof = oof_sum / N_SEEDS
    cv_raw = bacc(oof.argmax(1))
    cv_weighted, w = search_class_weights(oof, y)
    print(f"\nargmax OOF: {cv_raw:.5f}")
    print(f"加权 OOF: {cv_weighted:.5f} (w={w.round(3)})")

    # 与 v10 逐折对比
    v10_oof = np.load(OUT_DIR.parent / "v10_te_joint/oof_proba.npy")
    v10_w = np.load(OUT_DIR.parent / "v10_te_joint/best_class_weights.npy")
    for fold, (_, va) in enumerate(folds):
        s10 = balanced_accuracy_score(y[va], (v10_oof[va] * v10_w).argmax(1))
        s13 = balanced_accuracy_score(y[va], (oof[va] * w).argmax(1))
        print(f"fold {fold}: v10={s10:.5f} v13={s13:.5f} delta={s13-s10:+.5f}")

    sub[TARGET] = [classes[i] for i in (test_sum * w).argmax(1)]
    sub.to_csv(OUT_DIR / "submission.csv", index=False)
    print("\n提交预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))

    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_sum)
    np.save(OUT_DIR / "best_class_weights.npy", w)

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")
    print(f"CV (加权 OOF balanced accuracy): {cv_weighted:.5f}")


if __name__ == "__main__":
    main()
