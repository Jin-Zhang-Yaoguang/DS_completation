# -*- coding: utf-8 -*-
"""
v10 消融实验：联合键 TE 增量验证

动机：v6 的 39 列 TE 全是单列**边际**条件率 P(y|x_j)，但生成器的标签概率
依赖三个规则字段的**联合** P(y|sleep,stress,activity)。HGBC 要靠树分裂自己
重构联合分布（受 255 分箱与深度限制）。联合键 TE 直接查联合表递给模型。

键设计（全部在字符串视图上拼接，'nan' 字符串自动携带缺失模式信息）：
  rule3    : sleep|stress|activity（基数 ~1.1 万，均值每键 ~60 行，smooth='auto' 收缩护住稀键）
  pairs    : sleep|stress, sleep|activity, stress|activity 三个配对键
  rulecell : bucket(sleep)|stress|activity，bucket ∈ {lt6, 6to7, ge7, na}——
             生成规则的精确单元格（基数 ~80），低噪版联合键

消融配置（全部冻结 CV seed=42/5 折，与 v6 完全同协议）：
  base     = 13 单列 TE（复刻 v6，对照）
  +rule3   / +pairs / +rulecell / +all
"""

import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import TargetEncoder

SEED = 42
N_FOLDS = 5
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

CAT_COLS = ["diet_type", "stress_level", "sleep_quality",
            "physical_activity_level", "smoking_alcohol", "gender"]
NUM_COLS = ["sleep_duration", "heart_rate", "bmi", "calorie_expenditure",
            "step_count", "exercise_duration", "water_intake"]
RAW = NUM_COLS + CAT_COLS
TARGET = "health_condition"
RULE = ["sleep_duration", "stress_level", "physical_activity_level"]

HGBC_CONFIG = dict(
    learning_rate=0.0627037115235577,
    max_iter=300,
    max_leaf_nodes=33,
    min_samples_leaf=298,
    l2_regularization=0.028912644384523085,
    max_bins=237,
    max_features=0.820265066682815,
    early_stopping=True,
    categorical_features="from_dtype",
    random_state=0,
)


def balanced_weights(yy):
    counts = np.bincount(yy, minlength=3)
    return (len(yy) / (3 * counts))[yy]


def make_bacc(y):
    masks = [y == k for k in range(3)]
    counts = [m.sum() for m in masks]

    def bacc(pred):
        return np.mean([(pred[masks[k]] == k).mean() for k in range(3)])
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
    """按生成规则阈值分桶：<6 / [6,7) / ≥7 / 缺失"""
    v = pd.to_numeric(s, errors="coerce")
    out = pd.Series(np.where(v < 6, "lt6", np.where(v < 7, "6to7", "ge7")),
                    index=s.index)
    out[v.isna()] = "na"
    return out


def build_views(train, test):
    """返回 (模型视图 X/X_test, 字符串视图 Xs/Xs_test 含全部候选键)"""
    X, X_test = train[RAW].copy(), test[RAW].copy()
    for c in CAT_COLS:
        X[c] = X[c].astype("category")
        X_test[c] = X_test[c].astype("category").cat.set_categories(X[c].cat.categories)

    Xs = train[RAW].astype(str)
    Xs_test = test[RAW].astype(str)

    for df, src in [(Xs, train), (Xs_test, test)]:
        df["k_rule3"] = df[RULE[0]] + "|" + df[RULE[1]] + "|" + df[RULE[2]]
        df["k_sl_st"] = df[RULE[0]] + "|" + df[RULE[1]]
        df["k_sl_ac"] = df[RULE[0]] + "|" + df[RULE[2]]
        df["k_st_ac"] = df[RULE[1]] + "|" + df[RULE[2]]
        b = sleep_bucket(src["sleep_duration"])
        df["k_cell"] = b + "|" + df[RULE[1]] + "|" + df[RULE[2]]
    return X, X_test, Xs, Xs_test


CONFIGS = {
    "base":      [],
    "rule3":     ["k_rule3"],
    "pairs":     ["k_sl_st", "k_sl_ac", "k_st_ac"],
    "rulecell":  ["k_cell"],
    "all":       ["k_rule3", "k_sl_st", "k_sl_ac", "k_st_ac", "k_cell"],
}


def run_config(name, extra_keys, X, Xs, y, skf):
    te_cols = RAW + extra_keys
    te_names = [f"te_{c}_{k}" for c in te_cols for k in range(3)]
    oof = np.zeros((len(X), 3))
    t0 = time.time()

    for fold, (tr, va) in enumerate(skf.split(X, y)):
        enc = TargetEncoder(cv=5, smooth="auto", shuffle=True, random_state=SEED)
        Z_tr = enc.fit_transform(Xs[te_cols].iloc[tr], y[tr])
        Z_va = enc.transform(Xs[te_cols].iloc[va])

        A_tr = pd.concat([X.iloc[tr].reset_index(drop=True),
                          pd.DataFrame(Z_tr, columns=te_names)], axis=1)
        A_va = pd.concat([X.iloc[va].reset_index(drop=True),
                          pd.DataFrame(Z_va, columns=te_names)], axis=1)

        model = HistGradientBoostingClassifier(**HGBC_CONFIG)
        model.fit(A_tr, y[tr], sample_weight=balanced_weights(y[tr]))
        oof[va] = model.predict_proba(A_va)

    cv_raw = balanced_accuracy_score(y, oof.argmax(1))
    cv_w, w = search_class_weights(oof, y)
    print(f"[{name}] argmax={cv_raw:.5f} 加权={cv_w:.5f} (w={w[1]:.3f},{w[2]:.3f}) "
          f"| {time.time() - t0:.0f}s", flush=True)
    np.save(OUT_DIR / f"ablation_oof_{name}.npy", oof)
    return cv_w


def main():
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    X, X_test, Xs, Xs_test = build_views(train, test)
    for k in ["k_rule3", "k_sl_st", "k_sl_ac", "k_st_ac", "k_cell"]:
        print(f"键 {k}: 基数 {Xs[k].nunique()}", flush=True)

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    which = sys.argv[1:] if len(sys.argv) > 1 else list(CONFIGS)
    results = {}
    for name in which:
        results[name] = run_config(name, CONFIGS[name], X, Xs, y, skf)

    print("\n=== 消融汇总（加权 OOF） ===")
    base = results.get("base")
    for name, s in results.items():
        delta = f" ({s - base:+.5f})" if base and name != "base" else ""
        print(f"{name:>10}: {s:.5f}{delta}")


if __name__ == "__main__":
    main()
