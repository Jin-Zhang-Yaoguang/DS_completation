# -*- coding: utf-8 -*-
"""
方案 v7：全成员概率融合（零训练，纯后处理）
汇集本项目所有冻结 CV（seed 42, 5 折）下的成员概率：
  - v6 TE-HGBC（LB 0.95057，当前最佳单模）
  - v5 三成员：CatBoost / HGBC / LGBM
  - v1 LGBM（锐化概率）、v4 LGBM+规则特征（锐化概率）
流程：
  1. 成员间不一致率矩阵（调研教训：多样性 > 单模强度，先看误差相关性）；
  2. 双路融合搜索：算术平均（概率空间） vs 几何平均（log 空间），
     Dirichlet 随机权重 + 坐标上升精化；
  3. 融合概率上再搜类别决策权重（本项目标配）；
  4. 取 OOF 最优组合生成提交。
"""

import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
TARGET = "health_condition"
EPS = 1e-9


def load_members():
    """返回 {名称: (oof, test)}，全部 (n,3) 概率，类别顺序 ['at-risk','fit','unhealthy']。"""
    members = {}
    members["v6_te_hgbc"] = (np.load(ROOT / "v6_te_hgbc/oof_proba.npy"),
                             np.load(ROOT / "v6_te_hgbc/test_proba.npy"))
    v5_oof = np.load(ROOT / "v5_stack_hgbc_catb_lgbm/oof_probs.npy")
    v5_test = np.load(ROOT / "v5_stack_hgbc_catb_lgbm/test_probs.npy")
    for i, name in enumerate(["hgbc", "lgbm", "catc"]):
        members[f"v5_{name}"] = (v5_oof[i], v5_test[i])
    members["v1_lgbm"] = (np.load(ROOT / "v1_baseline_lgbm/oof_proba.npy"),
                          np.load(ROOT / "v1_baseline_lgbm/test_proba.npy"))
    members["v4_lgbm_rule"] = (np.load(ROOT / "v4_lgbm_rule/oof_proba.npy"),
                               np.load(ROOT / "v4_lgbm_rule/test_proba.npy"))
    return members


def search_class_weights(proba, y, coarse=45):
    def _search(g1, g2, best):
        for w1, w2 in product(g1, g2):
            s = balanced_accuracy_score(y, (proba * np.array([1.0, w1, w2])).argmax(1))
            if s > best[0]:
                best = (s, w1, w2)
        return best

    best = (balanced_accuracy_score(y, proba.argmax(1)), 1.0, 1.0)
    best = _search(np.linspace(1, 12, coarse), np.linspace(1, 12, coarse), best)
    s, w1, w2 = _search(np.linspace(max(0.5, best[1] - 0.3), best[1] + 0.3, 25),
                        np.linspace(max(0.5, best[2] - 0.3), best[2] + 0.3, 25), best)
    return s, np.array([1.0, w1, w2])


def blend(oofs, w, mode):
    """按权重融合成员概率。mode: arith / geo。oofs: (m, n, 3)"""
    w = np.asarray(w) / np.sum(w)
    if mode == "arith":
        return np.tensordot(w, oofs, axes=(0, 0))
    return np.exp(np.tensordot(w, np.log(oofs + EPS), axes=(0, 0)))


def search_blend(oofs, y, mode, n_trials=3000, refine_rounds=3):
    """Dirichlet 随机搜索 + 坐标上升精化，目标 = 融合后 argmax balanced accuracy。"""
    m = oofs.shape[0]
    rng = np.random.default_rng(SEED)
    candidates = [np.ones(m) / m] + [np.eye(m)[i] for i in range(m)]
    candidates += list(rng.dirichlet(np.ones(m), size=n_trials))

    def score(w):
        return balanced_accuracy_score(y, blend(oofs, w, mode).argmax(1))

    best_s, best_w = -1, None
    for w in candidates:
        s = score(w)
        if s > best_s:
            best_s, best_w = s, np.asarray(w, dtype=float)

    # 坐标上升精化
    for _ in range(refine_rounds):
        improved = False
        for i in range(m):
            for delta in (0.05, -0.05, 0.15, -0.15):
                w = best_w.copy()
                w[i] = max(0.0, w[i] + delta)
                if w.sum() == 0:
                    continue
                s = score(w)
                if s > best_s + 1e-6:
                    best_s, best_w, improved = s, w / w.sum(), True
        if not improved:
            break
    return best_s, best_w / best_w.sum()


def main():
    t0 = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    members = load_members()
    names = list(members.keys())
    oofs = np.stack([members[n][0] for n in names])
    tests = np.stack([members[n][1] for n in names])
    print("成员:", names)

    # ---------- 1. 单模基准 + 不一致率矩阵 ----------
    print("\n=== 单模加权 OOF ===")
    preds = {}
    for i, n in enumerate(names):
        s, w = search_class_weights(oofs[i], y, coarse=23)
        preds[n] = (oofs[i] * w).argmax(1)
        print(f"{n}: {s:.5f}")

    print("\n=== 不一致率矩阵（加权预测间，%） ===")
    header = "            " + " ".join(f"{n[:10]:>11}" for n in names)
    print(header)
    for a in names:
        row = " ".join(f"{100 * np.mean(preds[a] != preds[b]):>11.2f}" for b in names)
        print(f"{a[:12]:<12} {row}")

    # ---------- 2. 双路融合搜索 ----------
    results = {}
    for mode in ["arith", "geo"]:
        bs, bw = search_blend(oofs, y, mode)
        # 融合概率上再搜类别权重
        bp = blend(oofs, bw, mode)
        cs, cw = search_class_weights(bp, y)
        results[mode] = (cs, bw, cw)
        print(f"\n[{mode}] 融合 argmax OOF = {bs:.5f} -> +类别权重 = {cs:.5f}")
        print(f"   成员权重: {dict(zip(names, bw.round(3)))}")
        print(f"   类别权重: {cw.round(3)}")

    # ---------- 3. 取最优生成提交 ----------
    best_mode = max(results, key=lambda k: results[k][0])
    cv_final, bw, cw = results[best_mode]
    print(f"\n>>> 最优: {best_mode}, OOF = {cv_final:.5f}")

    test_blend = blend(tests, bw, best_mode)
    sub[TARGET] = [classes[i] for i in (test_blend * cw).argmax(1)]
    sub.to_csv(OUT_DIR / "submission.csv", index=False)
    print("提交预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))

    np.save(OUT_DIR / "blend_weights.npy", bw)
    np.save(OUT_DIR / "class_weights.npy", cw)
    with open(OUT_DIR / "blend_config.txt", "w") as f:
        f.write(f"mode={best_mode}\nmembers={names}\nblend_w={bw.tolist()}\n"
                f"class_w={cw.tolist()}\ncv={cv_final:.5f}\n")

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")
    print(f"CV (融合+加权 OOF balanced accuracy): {cv_final:.5f}")


if __name__ == "__main__":
    main()
