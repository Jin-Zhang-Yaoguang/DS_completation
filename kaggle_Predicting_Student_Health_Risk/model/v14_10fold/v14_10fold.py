# -*- coding: utf-8 -*-
"""
方案 v14：v10 配方原样 + 5 折改 10 折（每模型多见 12.5% 数据，TE 查表统计噪声降 10%）

消融结论（见 ablation.py，5 配置 × 冻结 CV）：
  - rulecell（bucket(sleep)|stress|activity，基数 64）：+0.00021，4/5 折为正 ✓
  - rule3 精确值联合键（基数 10450）：-0.00017（每键仅 ~60 行，估计噪声反伤）
  - pairs 配对键：-0.00009

为什么 rulecell 有效而 rule3 无效：生成器对 sleep 的依赖只经过规则阈值
（fit 要求 ≥7，unhealthy 要求 <6），按阈值分桶后的三元组单元格是联合分布的
**无损压缩**——64 个键、每键平均 1 万行，TE 估计几乎零噪声；
精确值键信息更细但样本稀疏，噪声毁掉增益。

其余与 v6 完全一致：冻结 CV seed=42/5 折、逐折 TargetEncoder(cv=5)、
HGBC 慢/浅/重正则、平衡样本权重、类别决策权重后处理。
"""

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.preprocessing import TargetEncoder

SEED = 42
N_FOLDS = 10
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


def search_class_weights(proba, y):
    def _grid(g1, g2, best):
        for w1, w2 in product(g1, g2):
            s = balanced_accuracy_score(y, (proba * np.array([1.0, w1, w2])).argmax(1))
            if s > best[0]:
                best = (s, w1, w2)
        return best

    best = (balanced_accuracy_score(y, proba.argmax(1)), 1.0, 1.0)
    best = _grid(np.linspace(1, 12, 45), np.linspace(1, 12, 45), best)
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


def main():
    t0 = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    print(f"train {train.shape} | test {test.shape}", flush=True)

    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    # 模型视图：原生类别 + 原生 NaN
    X, X_test = train[RAW].copy(), test[RAW].copy()
    for c in CAT_COLS:
        X[c] = X[c].astype("category")
        X_test[c] = X_test[c].astype("category").cat.set_categories(X[c].cat.categories)

    # TE 视图：13 单列 + rulecell 联合键
    Xs = train[RAW].astype(str)
    Xs_test = test[RAW].astype(str)
    Xs["k_cell"] = (sleep_bucket(train["sleep_duration"]) + "|"
                    + Xs["stress_level"] + "|" + Xs["physical_activity_level"])
    Xs_test["k_cell"] = (sleep_bucket(test["sleep_duration"]) + "|"
                         + Xs_test["stress_level"] + "|" + Xs_test["physical_activity_level"])
    TE_COLS = RAW + ["k_cell"]
    print(f"k_cell 基数: train {Xs['k_cell'].nunique()} / test {Xs_test['k_cell'].nunique()}",
          flush=True)

    te_names = [f"te_{c}_{k}" for c in TE_COLS for k in range(3)]
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros((len(X), 3))
    test_pred = np.zeros((len(X_test), 3))

    for fold, (tr, va) in enumerate(skf.split(X, y)):
        ts = time.time()
        enc = TargetEncoder(cv=5, smooth="auto", shuffle=True, random_state=SEED)
        Z_tr = enc.fit_transform(Xs[TE_COLS].iloc[tr], y[tr])
        Z_va = enc.transform(Xs[TE_COLS].iloc[va])
        Z_te = enc.transform(Xs_test[TE_COLS])

        A_tr = pd.concat([X.iloc[tr].reset_index(drop=True),
                          pd.DataFrame(Z_tr, columns=te_names)], axis=1)
        A_va = pd.concat([X.iloc[va].reset_index(drop=True),
                          pd.DataFrame(Z_va, columns=te_names)], axis=1)
        A_te = pd.concat([X_test.reset_index(drop=True),
                          pd.DataFrame(Z_te, columns=te_names)], axis=1)

        model = HistGradientBoostingClassifier(**HGBC_CONFIG)
        model.fit(A_tr, y[tr], sample_weight=balanced_weights(y[tr]))
        oof[va] = model.predict_proba(A_va)
        test_pred += model.predict_proba(A_te) / N_FOLDS

        print(f"fold {fold}: balanced_acc = "
              f"{balanced_accuracy_score(y[va], oof[va].argmax(1)):.5f} "
              f"(iters {model.n_iter_}, {time.time() - ts:.0f}s)", flush=True)

    cv_raw = balanced_accuracy_score(y, oof.argmax(1))
    cv_weighted, w = search_class_weights(oof, y)
    print(f"\nargmax OOF: {cv_raw:.5f}")
    print(f"加权 OOF: {cv_weighted:.5f} (w={w.round(3)})")
    print("混淆矩阵（加权后，顺序 %s）:" % classes)
    print(confusion_matrix(y, (oof * w).argmax(1)))

    sub[TARGET] = [classes[i] for i in (test_pred * w).argmax(1)]
    sub.to_csv(OUT_DIR / "submission.csv", index=False)
    print("\n提交预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))

    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    np.save(OUT_DIR / "best_class_weights.npy", w)

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")
    print(f"CV (加权 OOF balanced accuracy): {cv_weighted:.5f}")


if __name__ == "__main__":
    main()
