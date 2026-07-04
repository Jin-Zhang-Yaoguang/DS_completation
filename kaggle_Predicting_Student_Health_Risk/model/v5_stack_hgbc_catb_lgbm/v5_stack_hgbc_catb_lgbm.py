# -*- coding: utf-8 -*-
"""
方案：三模型异构融合（HGBC + LGBM + CatBoost）
参考 kaggle notebook kospintr/health-stacked-hgbc-catb-xgb-lgbm-baseline 的设计思路：
- 三个异构 GBDT 各自 5 折 CV，全部类别平衡；
- OOF 概率上做 Dirichlet 随机权重搜索融合（修正原 notebook 的 bug：
  其 test 融合误用循环末权重而非最优权重）；
- HGBC 早停 scoring 直接用 balanced_accuracy。
叠加本项目已验证的改进：
- 规则特征 + 缺失指示（目标生成规则逆向，见 overview.md）；
- 外部数据 50k 并入训练折（验证折保持纯比赛数据）；
- 融合概率上再做类别决策权重后处理（#2 线上验证 +0.0147）。
"""

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
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

RULE_FEATURES = ["f_sleep_ge7", "f_sleep_lt6", "f_stress_low", "f_stress_high",
                 "f_act_active", "f_rule_fit", "f_rule_unhealthy", "f_rule_pred",
                 "f_miss_sleep", "f_miss_stress", "f_miss_act", "f_n_missing"]
FEATURES = RAW_FEATURES + RULE_FEATURES


# ---------------- 特征工程（与 lgbm_v3_rule 一致） ----------------
def tri_and(*conds):
    """三值逻辑 AND：任一为 0 → 0；全为 1 → 1；否则 NaN。"""
    stacked = np.vstack(conds)
    out = np.full(stacked.shape[1], np.nan)
    out[(stacked == 0).any(axis=0)] = 0.0
    out[(stacked == 1).all(axis=0)] = 1.0
    return out


def add_features(df):
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
    rule_pred = np.full(len(df), np.nan)
    rule_pred[(df["f_rule_fit"] == 0) & (df["f_rule_unhealthy"] == 0)] = 0.0
    rule_pred[df["f_rule_fit"] == 1] = 1.0
    rule_pred[df["f_rule_unhealthy"] == 1] = 2.0
    df["f_rule_pred"] = rule_pred

    df["f_miss_sleep"] = df["sleep_duration"].isna().astype(int)
    df["f_miss_stress"] = df["stress_level"].isna().astype(int)
    df["f_miss_act"] = df["physical_activity_level"].isna().astype(int)
    df["f_n_missing"] = df[RAW_FEATURES].isna().sum(axis=1)
    return df


# ---------------- 模型定义 ----------------
def make_models():
    """返回 {名称: (模型实例, 是否支持早停)}。类别特征统一 category dtype。"""
    hgbc = HistGradientBoostingClassifier(
        class_weight="balanced",
        scoring="balanced_accuracy",       # 早停指标直接对齐赛题（notebook 思路）
        learning_rate=0.05,
        max_leaf_nodes=23,
        min_samples_leaf=20,
        max_iter=10000,
        n_iter_no_change=10,
        validation_fraction=0.1,
        categorical_features="from_dtype",
        random_state=SEED,
    )
    lgbm = lgb.LGBMClassifier(
        objective="multiclass", num_class=3,
        learning_rate=0.05, num_leaves=63, max_depth=-1,
        min_child_samples=100, feature_fraction=0.9,
        bagging_fraction=0.9, bagging_freq=1,
        class_weight="balanced", n_estimators=2000,
        random_state=SEED, n_jobs=-1, verbose=-1,
    )
    catc = CatBoostClassifier(
        loss_function="MultiClass",
        auto_class_weights="Balanced",
        learning_rate=0.05, depth=6,
        iterations=3000, early_stopping_rounds=150,
        l2_leaf_reg=9, max_bin=254,
        random_seed=SEED, verbose=False, allow_writing_files=False,
    )
    return {"hgbc": hgbc, "lgbm": lgbm, "catc": catc}


# ---------------- 融合与后处理 ----------------
def dirichlet_blend(oof_probs, y, n_trials=1000):
    """OOF 概率上搜索模型融合权重（含均匀权重与单模型解，修正 notebook 的 bug）。"""
    n_est = oof_probs.shape[0]
    rng = np.random.default_rng(SEED)
    candidates = [np.ones(n_est) / n_est]
    candidates += [np.eye(n_est)[i] for i in range(n_est)]
    candidates += list(rng.dirichlet(np.ones(n_est), size=n_trials))

    best_score, best_w = -1.0, None
    for w in candidates:
        s = balanced_accuracy_score(y, np.tensordot(w, oof_probs, axes=(0, 0)).argmax(1))
        if s > best_score:
            best_score, best_w = s, np.asarray(w)
    return best_score, best_w


def search_class_weights(proba, y):
    """类别决策权重搜索（粗→细网格）。"""
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
    ext = pd.read_csv(DATA_DIR / "external/student_health_dataset_50k.csv") \
            .drop(columns=["student_id", "timestamp"])
    print(f"train {train.shape} | test {test.shape} | external {ext.shape}", flush=True)

    train, test, ext = add_features(train), add_features(test), add_features(ext)

    # 类别列：填充 'NA' 后统一 category（CatBoost 不接受类别列 NaN；HGBC 用 from_dtype）
    for c in CAT_COLS:
        for df in (train, test, ext):
            df[c] = df[c].fillna("NA")
        cats = sorted(set(train[c]) | set(test[c]) | set(ext[c]))
        for df in (train, test, ext):
            df[c] = pd.Categorical(df[c], categories=cats)

    classes = sorted(train[TARGET].unique())
    cls2id = {c: i for i, c in enumerate(classes)}
    y = train[TARGET].map(cls2id).values
    y_ext = ext[TARGET].map(cls2id).values
    X, X_test, X_ext = train[FEATURES], test[FEATURES], ext[FEATURES]

    model_names = list(make_models().keys())
    n_est = len(model_names)
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof_probs = np.zeros((n_est, len(train), 3))
    test_probs = np.zeros((n_est, len(test), 3))

    for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
        X_tr = pd.concat([X.iloc[tr_idx], X_ext], axis=0)
        y_tr = np.concatenate([y[tr_idx], y_ext])
        X_va, y_va = X.iloc[va_idx], y[va_idx]

        models = make_models()
        for mi, (name, model) in enumerate(models.items()):
            ts = time.time()
            if name == "lgbm":
                model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)],
                          eval_metric="multi_logloss",
                          callbacks=[lgb.early_stopping(100, verbose=False)])
            elif name == "catc":
                model.fit(X_tr, y_tr, eval_set=(X_va, y_va),
                          cat_features=CAT_COLS)
            else:   # hgbc：内部自带验证早停
                model.fit(X_tr, y_tr)
            oof_probs[mi, va_idx] = model.predict_proba(X_va)
            test_probs[mi] += model.predict_proba(X_test) / N_FOLDS
            print(f"fold {fold} {name}: balanced_acc = "
                  f"{balanced_accuracy_score(y_va, oof_probs[mi, va_idx].argmax(1)):.5f} "
                  f"({time.time() - ts:.0f}s)", flush=True)

    # ---------------- 单模 OOF 分数 ----------------
    print("\n=== 单模 OOF（argmax / 类别加权后） ===")
    for mi, name in enumerate(model_names):
        s_raw = balanced_accuracy_score(y, oof_probs[mi].argmax(1))
        s_w, _ = search_class_weights(oof_probs[mi], y)
        print(f"{name}: argmax={s_raw:.5f} | 加权={s_w:.5f}")

    # ---------------- 融合 + 类别权重后处理 ----------------
    blend_score, blend_w = dirichlet_blend(oof_probs, y)
    print(f"\n融合权重 {dict(zip(model_names, blend_w.round(3)))} | 融合 argmax OOF = {blend_score:.5f}")

    oof_blend = np.tensordot(blend_w, oof_probs, axes=(0, 0))
    test_blend = np.tensordot(blend_w, test_probs, axes=(0, 0))   # 修正 bug：用最优权重
    cv_final, cw = search_class_weights(oof_blend, y)
    print(f"融合+类别加权 OOF = {cv_final:.5f} (w={cw.round(3)})")
    print("混淆矩阵（顺序 %s）:" % classes)
    print(confusion_matrix(y, (oof_blend * cw).argmax(1)))

    # ---------------- 提交 ----------------
    sub[TARGET] = [classes[i] for i in (test_blend * cw).argmax(1)]
    sub.to_csv(OUT_DIR / "submission.csv", index=False)
    print("\n提交预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))

    np.save(OUT_DIR / "oof_probs.npy", oof_probs)
    np.save(OUT_DIR / "test_probs.npy", test_probs)
    np.save(OUT_DIR / "blend_weights.npy", blend_w)
    np.save(OUT_DIR / "class_weights.npy", cw)

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")
    print(f"CV (融合+加权 OOF balanced accuracy): {cv_final:.5f}")


if __name__ == "__main__":
    main()
