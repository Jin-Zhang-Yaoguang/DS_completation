# -*- coding: utf-8 -*-
"""
方案 v12：缺失行显式边际化模型（生成式查表，差异化王牌）

原理：标签由生成器的条件概率 P(y | sleep, stress, activity) 采样而来。
判别式 GBDT 在缺失行上只能隐式边际化（受分箱/深度限制）；本方案显式计算

    P(y | x) = Σ_{b,s,a} P(y | b,s,a) · P(b|x) · P(s|x) · P(a|x)

其中 b/s/a 为睡眠桶/压力/活动，观测字段用点质量（one-hot），缺失字段用
软插补分布（HGBC 概率输出，只用特征不看 y，无泄漏）。

与 v11 的关键区别：v11 用 31% 错误率的**硬标签**污染 TE 键；本方案全程
**软概率积分**，插补不确定性被诚实地传播到输出。

组件：
  1. 概率表 P(y|cell)：9 睡眠桶（细分捕捉 6h/7h 附近平滑过渡）× 3 压力
     × 3 活动 = 81 格，逐折在训练折完整行上估计 + 拉普拉斯平滑；
  2. 三个软插补器（sleep 桶 9 类 / stress 3 类 / activity 3 类），
     train+test 合并的观测行上全量拟合一次；
  3. 评估：单模加权 OOF、与 v10 分歧率（分缺失模式）、按模式胜负分解、
     几何融合探测。冻结 CV seed=42/5 折。
"""

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import balanced_accuracy_score

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

SLEEP_EDGES = [-np.inf, 5, 5.5, 6, 6.5, 7, 7.5, 8, 9, np.inf]   # 9 桶
N_B = len(SLEEP_EDGES) - 1
STRESS_LEVELS = ["low", "medium", "high"]
ACT_LEVELS = ["sedentary", "moderate", "active"]
SMOOTH = 50.0   # 拉普拉斯平滑强度（向全局先验收缩）


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


def sleep_bin_idx(s):
    """精确睡眠值 → 桶号 (0..8)，缺失 → -1"""
    v = pd.to_numeric(s, errors="coerce").values
    idx = np.digitize(v, SLEEP_EDGES[1:-1])
    idx[np.isnan(v)] = -1
    return idx.astype(int)


def cat_idx(s, levels):
    m = {v: i for i, v in enumerate(levels)}
    return s.map(m).fillna(-1).astype(int).values


def fit_imputer(both_X, target_idx, n_classes, name):
    """软插补器：其余特征 → 该字段类别分布。返回全体行的 (n, n_classes) 概率。"""
    obs = target_idx >= 0
    m = HistGradientBoostingClassifier(max_iter=200, categorical_features="from_dtype",
                                       random_state=SEED)
    m.fit(both_X[obs], target_idx[obs])
    proba = np.zeros((len(both_X), n_classes))
    # 观测行 = 点质量；缺失行 = 模型分布
    proba[obs, target_idx[obs]] = 1.0
    if (~obs).sum():
        proba[~obs] = m.predict_proba(both_X[~obs])
    print(f"插补器 [{name}]: 观测 {obs.sum():,} / 缺失 {(~obs).sum():,}", flush=True)
    return proba


def main():
    t0 = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    n, nt = len(train), len(test)
    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values
    print(f"train {train.shape} | test {test.shape}", flush=True)

    both = pd.concat([train[RAW], test[RAW]], ignore_index=True)

    # ---------- 字段索引 ----------
    b_idx = sleep_bin_idx(both["sleep_duration"])
    s_idx = cat_idx(both["stress_level"], STRESS_LEVELS)
    a_idx = cat_idx(both["physical_activity_level"], ACT_LEVELS)

    # ---------- 三个软插补器（特征 = 其余 12 列，无 y，无泄漏） ----------
    dists = {}
    for name, tgt_idx, k, drop in [("sleep", b_idx, N_B, "sleep_duration"),
                                   ("stress", s_idx, 3, "stress_level"),
                                   ("act", a_idx, 3, "physical_activity_level")]:
        feats = [c for c in RAW if c != drop]
        Xf = both[feats].copy()
        for c in feats:
            if c in CAT_COLS:
                Xf[c] = Xf[c].astype("category")
        dists[name] = fit_imputer(Xf, tgt_idx, k, name)

    Pb, Ps, Pa = dists["sleep"], dists["stress"], dists["act"]

    # ---------- 联合单元格分布（n, 81） ----------
    # joint[i, b*9+s*3+a]  —— einsum 外积
    def joint_dist(idx):
        return np.einsum("ib,is,ia->ibsa", Pb[idx], Ps[idx], Pa[idx]).reshape(len(idx), -1)

    # 单元格 id（训练完整行用于估表）
    tr_b, tr_s, tr_a = b_idx[:n], s_idx[:n], a_idx[:n]
    complete = (tr_b >= 0) & (tr_s >= 0) & (tr_a >= 0)
    cell_id = np.where(complete, tr_b * 9 + tr_s * 3 + tr_a, -1)
    print(f"完整行: {complete.sum():,} ({complete.mean()*100:.1f}%)", flush=True)

    # ---------- 逐折：训练折完整行估表 → 验证行边际化 ----------
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    prior_global = np.bincount(y, minlength=3) / n
    oof = np.zeros((n, 3))
    test_pred = np.zeros((nt, 3))
    n_cells = N_B * 3 * 3

    test_joint = joint_dist(np.arange(n, n + nt))

    for fold, (tr, va) in enumerate(skf.split(train, y)):
        ts = time.time()
        # 概率表：训练折完整行 + 拉普拉斯平滑
        m = complete[tr]
        cid, yy = cell_id[tr][m], y[tr][m]
        table = np.zeros((n_cells, 3))
        np.add.at(table, (cid, yy), 1.0)
        table = (table + SMOOTH * prior_global) / (table.sum(1, keepdims=True) + SMOOTH)

        oof[va] = joint_dist(va) @ table
        test_pred += (test_joint @ table) / N_FOLDS
        print(f"fold {fold}: {time.time()-ts:.0f}s", flush=True)

    # ---------- 评估 ----------
    bacc = make_bacc(y)
    cv_raw = bacc(oof.argmax(1))
    cv_w, w = search_class_weights(oof, y)
    print(f"\n[边际化模型] argmax OOF: {cv_raw:.5f} | 加权 OOF: {cv_w:.5f} (w={w.round(3)})")

    # ---------- 与 v10 对比：分歧率 + 按缺失模式分解 ----------
    v10_oof = np.load(OUT_DIR.parent / "v10_te_joint/oof_proba.npy")
    v10_w = np.load(OUT_DIR.parent / "v10_te_joint/best_class_weights.npy")
    p10 = (v10_oof * v10_w).argmax(1)
    p12 = (oof * w).argmax(1)
    print(f"\n与 v10 总分歧率: {np.mean(p10 != p12)*100:.2f}%")

    pattern = ((tr_b < 0).astype(int) * 4 + (tr_s < 0).astype(int) * 2 + (tr_a < 0).astype(int))
    tags = {0: "全在", 1: "缺A", 2: "缺T", 3: "缺TA", 4: "缺S", 5: "缺SA", 6: "缺ST", 7: "缺STA"}
    n_k = np.bincount(y, minlength=3)

    def contrib(pred, mask):
        """该子集对全局 bacc 的贡献"""
        return sum((pred[mask & (y == k)] == k).sum() / n_k[k] for k in range(3)) / 3

    print(f"\n{'模式':<6} {'行数':>8} {'分歧%':>7} {'v10贡献':>9} {'v12贡献':>9} {'delta':>9}")
    for p in range(8):
        mask = pattern == p
        if mask.sum() == 0:
            continue
        d = np.mean(p10[mask] != p12[mask]) * 100
        c10, c12 = contrib(p10, mask), contrib(p12, mask)
        print(f"{tags[p]:<6} {mask.sum():>8,} {d:>7.2f} {c10:>9.5f} {c12:>9.5f} {c12-c10:>+9.5f}")

    # ---------- 融合探测（几何，α 粗扫） ----------
    print("\n=== v10 × v12 几何融合探测 ===")
    L10, L12 = np.log(v10_oof + 1e-9), np.log(oof + 1e-9)
    best = (0.0, 1.0, None)
    for alpha in np.linspace(0.5, 1.0, 26):
        blended = np.exp(alpha * L10 + (1 - alpha) * L12)
        s, cw = search_class_weights(blended, y)
        if s > best[0]:
            best = (s, alpha, cw)
    s10w, _ = search_class_weights(v10_oof, y)
    print(f"v10 单模: {s10w:.5f} | 最优融合 α(v10)={best[1]:.2f}: {best[0]:.5f} "
          f"(delta {best[0]-s10w:+.5f})")

    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    np.save(OUT_DIR / "best_class_weights.npy", w)

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
