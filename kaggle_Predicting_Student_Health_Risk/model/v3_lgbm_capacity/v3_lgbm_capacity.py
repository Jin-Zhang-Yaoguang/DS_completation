# -*- coding: utf-8 -*-
"""
方案 v2：LightGBM 加大容量 + 类别权重后处理
相对 baseline_lgbm 的改动：
1. 容量：lr 0.05→0.03，树数上限 2000→20000，early stopping 100→300
   （baseline 所有折都打满 2000 棵、ES 未触发，明确欠训练）；
2. 后处理：在 OOF 概率上搜索每类乘性决策权重，最大化 Balanced Accuracy
   （baseline 实验：argmax 0.93503 → 加权 0.94877，+0.0137）。
其余（特征、折、种子）与 baseline 完全一致，保证可对比。
"""

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score, confusion_matrix

# ---------------- 配置 ----------------
SEED = 42
N_FOLDS = 5
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

CAT_COLS = ["diet_type", "stress_level", "sleep_quality",
            "physical_activity_level", "smoking_alcohol", "gender"]
NUM_COLS = ["sleep_duration", "heart_rate", "bmi", "calorie_expenditure",
            "step_count", "exercise_duration", "water_intake"]
FEATURES = NUM_COLS + CAT_COLS
TARGET = "health_condition"

LGB_PARAMS = dict(
    objective="multiclass",
    num_class=3,
    learning_rate=0.03,        # baseline: 0.05
    num_leaves=63,
    max_depth=-1,
    min_child_samples=100,
    feature_fraction=0.9,
    bagging_fraction=0.9,
    bagging_freq=1,
    class_weight="balanced",
    n_estimators=20000,        # baseline: 2000（全部打满）
    random_state=SEED,
    n_jobs=-1,
    verbose=-1,
)
EARLY_STOP = 300               # baseline: 100


def search_weights(oof, y):
    """在 OOF 概率上搜索每类乘性权重（固定第 0 类 = 1），最大化 balanced accuracy。"""
    def _search(g1, g2, best):
        for w1, w2 in product(g1, g2):
            s = balanced_accuracy_score(y, (oof * np.array([1.0, w1, w2])).argmax(1))
            if s > best[0]:
                best = (s, w1, w2)
        return best

    best = (balanced_accuracy_score(y, oof.argmax(1)), 1.0, 1.0)
    print(f"argmax OOF: {best[0]:.5f}")
    best = _search(np.linspace(1, 12, 45), np.linspace(1, 12, 45), best)
    s, w1, w2 = _search(np.linspace(max(0.5, best[1] - 0.3), best[1] + 0.3, 25),
                        np.linspace(max(0.5, best[2] - 0.3), best[2] + 0.3, 25), best)
    print(f"加权 OOF: {s:.5f} (w_fit={w1:.3f}, w_unhealthy={w2:.3f})")
    return s, np.array([1.0, w1, w2])


def main():
    t0 = time.time()

    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")

    for c in CAT_COLS:
        cats = sorted(set(train[c].dropna()) | set(test[c].dropna()))
        train[c] = pd.Categorical(train[c], categories=cats)
        test[c] = pd.Categorical(test[c], categories=cats)

    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values
    X, X_test = train[FEATURES], test[FEATURES]

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros((len(train), len(classes)))
    test_pred = np.zeros((len(test), len(classes)))

    for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            X.iloc[tr_idx], y[tr_idx],
            eval_set=[(X.iloc[va_idx], y[va_idx])],
            eval_metric="multi_logloss",
            callbacks=[lgb.early_stopping(EARLY_STOP, verbose=False)],
        )
        oof[va_idx] = model.predict_proba(X.iloc[va_idx])
        test_pred += model.predict_proba(X_test) / N_FOLDS
        print(f"fold {fold}: balanced_acc = "
              f"{balanced_accuracy_score(y[va_idx], oof[va_idx].argmax(1)):.5f} "
              f"(best_iter={model.best_iteration_})", flush=True)

    # ---------------- OOF 评估 + 权重搜索 ----------------
    cv_weighted, w = search_weights(oof, y)
    oof_label = (oof * w).argmax(1)
    print("混淆矩阵（加权后，顺序 %s）:" % classes)
    print(confusion_matrix(y, oof_label))

    # ---------------- 生成提交（应用同一组权重） ----------------
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
