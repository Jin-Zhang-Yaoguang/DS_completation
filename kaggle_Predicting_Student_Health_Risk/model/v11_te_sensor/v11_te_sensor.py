# -*- coding: utf-8 -*-
"""
方案 v11：v10 配方 + activity 传感器恢复（代理补全联合键 TE）

EDA 结论（data/EDA.html 第六节）：三个规则字段中只有 physical_activity_level
可以从其余特征恢复（预测精度 69% vs 多数类基线 34%）——信息藏在活动簇传感器
（step_count / exercise_duration / calorie_expenditure，两两 r≈0.4）里。
v10 的 rulecell 键在 activity 缺失行上写 'na'，TE 只能给出对全体 activity
边际化的先验；本方案把传感器信息显式补进联合键。

机制：
  1. 恢复器：HGBC 用其余 12 特征预测 activity 三档，在 train+test 合并的
     activity 非缺失行上拟合（不看目标 y，无泄漏，可全量拟合一次）；
  2. 代理补全键 k_cell_proxy = bucket(sleep) | stress | activity_completed，
     补全值带 '~' 后缀（如 'active~'）与实测值区分——代理精度 69%，
     其单元格条件概率被稀释，TE 分开估计才诚实（基数 ~4×4×6=96）；
  3. 其余与 v10 完全一致：13 单列 TE + k_cell + HGBC 慢/浅/重正则 +
     平衡样本权重 + 类别决策权重后处理，冻结 CV seed=42/5 折。
"""

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, accuracy_score
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
ACT = "physical_activity_level"

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
    v = pd.to_numeric(s, errors="coerce")
    out = pd.Series(np.where(v < 6, "lt6", np.where(v < 7, "6to7", "ge7")), index=s.index)
    out[v.isna()] = "na"
    return out


def recover_activity(train, test):
    """传感器恢复器：其余 12 特征 → activity 三档。返回补全列（缺失行带 '~' 后缀）。"""
    both = pd.concat([train[RAW], test[RAW]], ignore_index=True)
    feats = [c for c in RAW if c != ACT]
    X = both[feats].copy()
    for c in feats:
        if c in CAT_COLS:
            X[c] = X[c].astype("category")

    obs = both[ACT].notna().values
    y_act, act_levels = pd.factorize(both.loc[obs, ACT])
    print(f"恢复器训练集: {obs.sum():,} 行（activity 非缺失），预测 {(~obs).sum():,} 行", flush=True)

    # 90/10 持出评估恢复器精度（仅报告用）
    Xtr, Xva, ytr, yva = train_test_split(X[obs], y_act, test_size=0.1,
                                          random_state=SEED, stratify=y_act)
    imp = HistGradientBoostingClassifier(max_iter=200, categorical_features="from_dtype",
                                         random_state=SEED)
    imp.fit(Xtr, ytr)
    acc = accuracy_score(yva, imp.predict(Xva))
    base = np.bincount(yva).max() / len(yva)
    print(f"恢复器持出精度: {acc:.4f} (基线 {base:.4f}, 提升 {acc-base:+.4f})", flush=True)

    # 全量重训后预测缺失行
    imp_full = HistGradientBoostingClassifier(max_iter=200, categorical_features="from_dtype",
                                              random_state=SEED)
    imp_full.fit(X[obs], y_act)
    pred = imp_full.predict(X[~obs])

    completed = both[ACT].astype(str).copy()
    completed[~obs] = pd.Series(act_levels[pred]).values + "~"
    print("补全值分布:", completed[~obs].value_counts().to_dict(), flush=True)
    return completed[:len(train)].reset_index(drop=True), completed[len(train):].reset_index(drop=True)


def main():
    t0 = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    print(f"train {train.shape} | test {test.shape}", flush=True)

    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    # ---------- 传感器恢复 ----------
    act_tr, act_te = recover_activity(train, test)

    # ---------- 模型视图 ----------
    X, X_test = train[RAW].copy(), test[RAW].copy()
    for c in CAT_COLS:
        X[c] = X[c].astype("category")
        X_test[c] = X_test[c].astype("category").cat.set_categories(X[c].cat.categories)

    # ---------- TE 视图：13 单列 + k_cell（v10） + k_cell_proxy（v11 新增） ----------
    Xs = train[RAW].astype(str)
    Xs_test = test[RAW].astype(str)
    sb_tr = sleep_bucket(train["sleep_duration"])
    sb_te = sleep_bucket(test["sleep_duration"])
    Xs["k_cell"] = sb_tr + "|" + Xs["stress_level"] + "|" + Xs[ACT]
    Xs_test["k_cell"] = sb_te + "|" + Xs_test["stress_level"] + "|" + Xs_test[ACT]
    Xs["k_cell_proxy"] = sb_tr + "|" + Xs["stress_level"] + "|" + act_tr
    Xs_test["k_cell_proxy"] = sb_te + "|" + Xs_test["stress_level"] + "|" + act_te
    TE_COLS = RAW + ["k_cell", "k_cell_proxy"]
    print(f"k_cell 基数 {Xs['k_cell'].nunique()} | k_cell_proxy 基数 {Xs['k_cell_proxy'].nunique()}",
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

    # 与 v10 对比（同折）
    v10_oof = np.load(OUT_DIR.parent / "v10_te_joint/oof_proba.npy")
    v10_w = np.load(OUT_DIR.parent / "v10_te_joint/best_class_weights.npy")
    for fold, (_, va) in enumerate(skf.split(X, y)):
        s10 = balanced_accuracy_score(y[va], (v10_oof[va] * v10_w).argmax(1))
        s11 = balanced_accuracy_score(y[va], (oof[va] * w).argmax(1))
        print(f"fold {fold}: v10={s10:.5f} v11={s11:.5f} delta={s11-s10:+.5f}")

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
