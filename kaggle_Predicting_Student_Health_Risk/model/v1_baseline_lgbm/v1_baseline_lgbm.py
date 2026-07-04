# -*- coding: utf-8 -*-
"""
基线方案：LightGBM + 5 折分层交叉验证
赛题：Predicting Student Health Risk (Playground Series S6E7)
指标：Balanced Accuracy Score（各类 recall 宏平均）

思路：
- LightGBM 原生支持缺失值与类别特征，不做插补、不做特征工程，先端到端跑通；
- 类别严重不平衡（at-risk 85.9% / unhealthy 8.4% / fit 5.8%），
  用 class_weight='balanced' 让模型对齐 Balanced Accuracy；
- 5 折 StratifiedKFold，OOF 分数作为本地 CV，测试集取各折概率平均后 argmax。
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score, confusion_matrix

# ---------------- 配置 ----------------
SEED = 42
N_FOLDS = 5
DATA_DIR = Path(__file__).resolve().parents[2] / "data"   # 上级共享的 data/
OUT_DIR = Path(__file__).resolve().parent                  # 本方案文件夹

CAT_COLS = ["diet_type", "stress_level", "sleep_quality",
            "physical_activity_level", "smoking_alcohol", "gender"]
NUM_COLS = ["sleep_duration", "heart_rate", "bmi", "calorie_expenditure",
            "step_count", "exercise_duration", "water_intake"]
FEATURES = NUM_COLS + CAT_COLS
TARGET = "health_condition"

LGB_PARAMS = dict(
    objective="multiclass",
    num_class=3,
    learning_rate=0.05,
    num_leaves=63,
    max_depth=-1,
    min_child_samples=100,
    feature_fraction=0.9,
    bagging_fraction=0.9,
    bagging_freq=1,
    class_weight="balanced",   # 关键：对齐 Balanced Accuracy
    n_estimators=2000,
    random_state=SEED,
    n_jobs=-1,
    verbose=-1,
)


def main():
    t0 = time.time()

    # ---------------- 读数 ----------------
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    print(f"train {train.shape} | test {test.shape}")

    # 类别特征转 category（train/test 统一类别集合），LightGBM 原生处理
    for c in CAT_COLS:
        cats = sorted(set(train[c].dropna()) | set(test[c].dropna()))
        train[c] = pd.Categorical(train[c], categories=cats)
        test[c] = pd.Categorical(test[c], categories=cats)

    # 目标编码
    classes = sorted(train[TARGET].unique())          # ['at-risk', 'fit', 'unhealthy']
    cls2id = {c: i for i, c in enumerate(classes)}
    y = train[TARGET].map(cls2id).values
    X = train[FEATURES]
    X_test = test[FEATURES]
    print("类别映射:", cls2id)

    # ---------------- 交叉验证 ----------------
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros((len(train), len(classes)))
    test_pred = np.zeros((len(test), len(classes)))
    importances = np.zeros(len(FEATURES))

    for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            X.iloc[tr_idx], y[tr_idx],
            eval_set=[(X.iloc[va_idx], y[va_idx])],
            eval_metric="multi_logloss",
            callbacks=[lgb.early_stopping(100, verbose=False)],
        )
        oof[va_idx] = model.predict_proba(X.iloc[va_idx])
        test_pred += model.predict_proba(X_test) / N_FOLDS
        importances += model.feature_importances_ / N_FOLDS

        fold_score = balanced_accuracy_score(y[va_idx], oof[va_idx].argmax(1))
        print(f"fold {fold}: balanced_acc = {fold_score:.5f} "
              f"(best_iter={model.best_iteration_})")

    # ---------------- OOF 评估 ----------------
    oof_label = oof.argmax(1)
    cv_score = balanced_accuracy_score(y, oof_label)
    print(f"\n===== OOF Balanced Accuracy: {cv_score:.5f} =====")
    print("混淆矩阵（行=真实，列=预测，顺序 %s）:" % classes)
    print(confusion_matrix(y, oof_label))

    # ---------------- 生成提交 ----------------
    sub[TARGET] = [classes[i] for i in test_pred.argmax(1)]
    sub.to_csv(OUT_DIR / "submission.csv", index=False)
    print("\n提交文件预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))

    # ---------------- 过程产物 ----------------
    # OOF 概率留档，便于后续做阈值优化/融合
    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    pd.DataFrame({"feature": FEATURES, "importance": importances}) \
        .sort_values("importance", ascending=False) \
        .to_csv(OUT_DIR / "feature_importance.csv", index=False)

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")
    print(f"CV (OOF balanced accuracy): {cv_score:.5f}")


if __name__ == "__main__":
    main()
