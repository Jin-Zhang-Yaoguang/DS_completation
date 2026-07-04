# -*- coding: utf-8 -*-
"""
方案 v3：规则特征 + 缺失指示 + 外部数据增强 + 类别权重后处理
基于逆向出的目标生成规则（外部数据上 100% 成立）：
    fit       ⟺ sleep_duration ≥ 7 且 stress_level = low 且 physical_activity_level = active
    unhealthy ⟺ sleep_duration < 6 且 stress_level = high
    at-risk   ⟸ 其余
改动（相对 baseline_lgbm）：
1. 规则特征（缺失感知三值逻辑：1/0/NaN）：各条件位 + 组合规则输出；
2. 缺失指示：规则 3 字段的缺失标志 + 全行缺失计数；
3. 外部数据增强：50k 干净样本并入每折训练集（验证集保持纯比赛数据，CV 口径不变）；
4. 模型参数回到 baseline 档位（v2 已证明加容量是负收益）；
5. 沿用类别权重后处理（#2 已线上验证有效）。
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
RAW_FEATURES = NUM_COLS + CAT_COLS
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
    class_weight="balanced",
    n_estimators=3000,
    random_state=SEED,
    n_jobs=-1,
    verbose=-1,
)
EARLY_STOP = 150


def tri_and(*conds):
    """三值逻辑 AND：任一为 0 → 0；全为 1 → 1；否则 NaN。conds 为 float(1/0/NaN) 数组。"""
    stacked = np.vstack(conds)
    out = np.full(stacked.shape[1], np.nan)
    out[(stacked == 0).any(axis=0)] = 0.0
    out[(stacked == 1).all(axis=0)] = 1.0
    return out


def add_features(df):
    """规则特征 + 缺失指示。全部缺失感知（组件缺失时传播 NaN，交给 LGBM 处理）。"""
    df = df.copy()
    sleep = df["sleep_duration"].values.astype(float)
    stress = df["stress_level"]
    act = df["physical_activity_level"]

    def cond_num(arr, mask):
        out = np.where(mask, 1.0, 0.0)
        out[np.isnan(arr)] = np.nan
        return out

    def cond_cat(s, value):
        out = np.where(s == value, 1.0, 0.0)
        out[s.isna().values] = np.nan
        return out

    df["f_sleep_ge7"] = cond_num(sleep, sleep >= 7)
    df["f_sleep_lt6"] = cond_num(sleep, sleep < 6)
    df["f_stress_low"] = cond_cat(stress, "low")
    df["f_stress_high"] = cond_cat(stress, "high")
    df["f_act_active"] = cond_cat(act, "active")

    df["f_rule_fit"] = tri_and(df["f_sleep_ge7"].values,
                               df["f_stress_low"].values,
                               df["f_act_active"].values)
    df["f_rule_unhealthy"] = tri_and(df["f_sleep_lt6"].values,
                                     df["f_stress_high"].values)
    # 规则综合输出：0=at-risk, 1=fit, 2=unhealthy, NaN=无法判定
    rule_pred = np.full(len(df), np.nan)
    rule_pred[(df["f_rule_fit"] == 0) & (df["f_rule_unhealthy"] == 0)] = 0.0
    rule_pred[df["f_rule_fit"] == 1] = 1.0
    rule_pred[df["f_rule_unhealthy"] == 1] = 2.0
    df["f_rule_pred"] = rule_pred

    # 缺失指示
    df["f_miss_sleep"] = df["sleep_duration"].isna().astype(int)
    df["f_miss_stress"] = df["stress_level"].isna().astype(int)
    df["f_miss_act"] = df["physical_activity_level"].isna().astype(int)
    df["f_n_missing"] = df[RAW_FEATURES].isna().sum(axis=1)
    return df


RULE_FEATURES = ["f_sleep_ge7", "f_sleep_lt6", "f_stress_low", "f_stress_high",
                 "f_act_active", "f_rule_fit", "f_rule_unhealthy", "f_rule_pred",
                 "f_miss_sleep", "f_miss_stress", "f_miss_act", "f_n_missing"]
FEATURES = RAW_FEATURES + RULE_FEATURES


def search_weights(oof, y):
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
    ext = pd.read_csv(DATA_DIR / "external/student_health_dataset_50k.csv") \
            .drop(columns=["student_id", "timestamp"])
    print(f"train {train.shape} | test {test.shape} | external {ext.shape}")

    # 特征工程（外部数据无缺失，规则特征全部可判定）
    train, test, ext = add_features(train), add_features(test), add_features(ext)

    # 类别列统一 category 编码（三份数据取值一致，已验证）
    for c in CAT_COLS:
        cats = sorted(set(train[c].dropna()) | set(test[c].dropna()) | set(ext[c].dropna()))
        for df in (train, test, ext):
            df[c] = pd.Categorical(df[c], categories=cats)

    classes = sorted(train[TARGET].unique())
    cls2id = {c: i for i, c in enumerate(classes)}
    y = train[TARGET].map(cls2id).values
    y_ext = ext[TARGET].map(cls2id).values
    X, X_test, X_ext = train[FEATURES], test[FEATURES], ext[FEATURES]

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof = np.zeros((len(train), len(classes)))
    test_pred = np.zeros((len(test), len(classes)))
    importances = np.zeros(len(FEATURES))

    for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
        # 外部干净数据并入训练折；验证折保持纯比赛数据
        X_tr = pd.concat([X.iloc[tr_idx], X_ext], axis=0)
        y_tr = np.concatenate([y[tr_idx], y_ext])

        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X.iloc[va_idx], y[va_idx])],
            eval_metric="multi_logloss",
            callbacks=[lgb.early_stopping(EARLY_STOP, verbose=False)],
        )
        oof[va_idx] = model.predict_proba(X.iloc[va_idx])
        test_pred += model.predict_proba(X_test) / N_FOLDS
        importances += model.feature_importances_ / N_FOLDS
        print(f"fold {fold}: balanced_acc = "
              f"{balanced_accuracy_score(y[va_idx], oof[va_idx].argmax(1)):.5f} "
              f"(best_iter={model.best_iteration_})", flush=True)

    # ---------------- 评估 + 后处理 ----------------
    cv_weighted, w = search_weights(oof, y)
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
    pd.DataFrame({"feature": FEATURES, "importance": importances}) \
        .sort_values("importance", ascending=False) \
        .to_csv(OUT_DIR / "feature_importance.csv", index=False)

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")
    print(f"CV (加权 OOF balanced accuracy): {cv_weighted:.5f}")


if __name__ == "__main__":
    main()
