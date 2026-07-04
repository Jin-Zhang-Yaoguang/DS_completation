# -*- coding: utf-8 -*-
"""
方案 v6：逐值目标编码（per-value TE）+ 慢/浅/重正则 HGBC
复刻调研确认的公开单模最优配方（survey §2.1，CV 0.95026 / LB 0.95034），
叠加本项目标配的类别决策权重后处理。

核心思想（为什么逐值 TE 有效）：
- 合成标签是从「依赖精确特征值的概率」中采样的；690k 行里每个不同取值重复上百次
  （如 sleep_duration 仅 701 个不同值），逐值标签率≈对生成器条件概率的直接查表估计；
- HGBC 自身把数值分箱到 ≤255 桶会损失逐值分辨率，TE 把逐值统计直接递给模型；
- 防泄漏：每折内 TargetEncoder(cv=5) 交叉拟合。

两个特征视图：
- 模型视图：原始 13 列（数值 float + 类别 category），NaN 原生路由；
- TE 视图：13 列全部 astype(str)（数值保留精确值），fillna('na')，逐折 TE → 39 列（3 类 × 13 列）。
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

# ---------------- 配置 ----------------
SEED = 42          # 冻结 CV（与本项目所有方案一致）
N_FOLDS = 5
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

CAT_COLS = ["diet_type", "stress_level", "sleep_quality",
            "physical_activity_level", "smoking_alcohol", "gender"]
NUM_COLS = ["sleep_duration", "heart_rate", "bmi", "calorie_expenditure",
            "step_count", "exercise_duration", "water_intake"]
RAW = NUM_COLS + CAT_COLS
TARGET = "health_condition"

# 慢/浅/重正则操作点（survey §2.1 原参数）
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
    """类别决策权重搜索（粗→细网格），本项目标配后处理。"""
    def _search(g1, g2, best):
        for w1, w2 in product(g1, g2):
            s = balanced_accuracy_score(y, (proba * np.array([1.0, w1, w2])).argmax(1))
            if s > best[0]:
                best = (s, w1, w2)
        return best

    best = (balanced_accuracy_score(y, proba.argmax(1)), 1.0, 1.0)
    best = _search(np.linspace(1, 12, 45), np.linspace(1, 12, 45), best)
    s, w1, w2 = _search(np.linspace(max(0.5, best[1] - 0.3), best[1] + 0.3, 25),
                        np.linspace(max(0.5, best[2] - 0.3), best[2] + 0.3, 25), best)
    return s, np.array([1.0, w1, w2])


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

    # TE 视图：全列字符串化（数值保留精确值）
    Xs = train[RAW].astype(str).fillna("na")
    Xs_test = test[RAW].astype(str).fillna("na")
    print("TE 基数:", dict(Xs.nunique().sort_values(ascending=False)), flush=True)

    te_names = [f"te_{c}_{k}" for c in RAW for k in range(3)]
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros((len(X), 3))
    test_pred = np.zeros((len(X_test), 3))

    for fold, (tr, va) in enumerate(skf.split(X, y)):
        ts = time.time()
        # 逐折防泄漏逐值 TE（内部 cv=5 交叉拟合）
        enc = TargetEncoder(cv=5, smooth="auto", shuffle=True, random_state=SEED)
        Z_tr = enc.fit_transform(Xs.iloc[tr], y[tr])
        Z_va = enc.transform(Xs.iloc[va])
        Z_te = enc.transform(Xs_test)

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

    # ---------------- 评估 + 后处理 ----------------
    cv_raw = balanced_accuracy_score(y, oof.argmax(1))
    cv_weighted, w = search_class_weights(oof, y)
    print(f"\nargmax OOF: {cv_raw:.5f}")
    print(f"加权 OOF: {cv_weighted:.5f} (w={w.round(3)})")
    print("混淆矩阵（加权后，顺序 %s）:" % classes)
    print(confusion_matrix(y, (oof * w).argmax(1)))

    # ---------------- 提交 ----------------
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
