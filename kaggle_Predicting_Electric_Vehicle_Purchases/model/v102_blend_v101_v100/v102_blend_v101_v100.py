"""v102：v101（线性模型 + 残差 GBDT）与既有严格线成员的嵌套秩融合。

成员全部转百分位秩；权重用 OOF AUC 贪心爬山（步长 0.02），在 5 折嵌套内拟合后取平均。
同时汇总 v101 各成员的 OOF/test，并写出 v101 残差 LGBM 的单模提交。
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.model_selection import StratifiedKFold

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
DATA = MODEL.parent / "data"
V101 = MODEL / "v101_glm_margin_gbdt_10f"
# 既有成员位于主线工作树（只读）
OLD = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/"
           "kaggle_Predicting_Electric_Vehicle_Purchases/model")
OLD_MEMBERS = {"v100": "v100_v90_ctboost_nested_cv_blend", "v85": "v85_naji_v74_40f",
               "v80": "v80_strict_v61_outer104395303_40f"}

train = pd.read_csv(DATA / "train.csv", usecols=["id", "Will_Buy_EV"])
test_ids = pd.read_csv(DATA / "test.csv", usecols=["id"])["id"].to_numpy()
y = (train["Will_Buy_EV"] == "Yes").to_numpy().astype(np.int8)
ntr, nte = len(y), len(test_ids)


def fast_auc(yb, s):
    order = np.argsort(s, kind="stable")
    r = np.empty(len(s))
    r[order] = np.arange(1, len(s) + 1)
    n1 = yb.sum()
    n0 = len(yb) - n1
    return (r[yb == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def rk(v):
    return rankdata(v) / len(v)


def hill(R, yb, names, step=0.02, iters=300):
    w = {n: 0.0 for n in names}
    best = max(names, key=lambda n: fast_auc(yb, R[n]))
    w[best] = 1.0
    vec, cur = R[best].copy(), fast_auc(yb, R[best])
    for _ in range(iters):
        a, n = max((fast_auc(yb, vec + step * R[n]), n) for n in names)
        if a <= cur + 1e-7:
            break
        w[n] += step
        vec = vec + step * R[n]
        cur = a
    s = sum(w.values())
    return {n: w[n] / s for n in names}, cur


# ---- v101 成员：由各折文件汇总
OOF, TST = {}, {}
for m in ["glm", "lgbm", "xgb"]:
    OOF[f"v101_{m}"] = np.full(ntr, np.nan)
    TST[f"v101_{m}"] = np.zeros(nte)
for k in range(10):
    f = np.load(V101 / "folds" / f"fold_{k}.npz")
    for m in ["glm", "lgbm", "xgb"]:
        OOF[f"v101_{m}"][f["valid_rows"]] = f[f"{m}_valid"]
        TST[f"v101_{m}"] += rk(f[f"{m}_test"]) / 10      # 各折起点不同，先转秩再平均
for n in list(OOF):
    assert np.isfinite(OOF[n]).all()
    np.save(V101 / f"oof_{n}.npy", OOF[n])
    np.save(V101 / f"test_{n}.npy", TST[n])
for n, d in OLD_MEMBERS.items():
    OOF[n] = np.load(OLD / d / "oof_proba.npy")
    TST[n] = np.load(OLD / d / "test_proba.npy")
    assert len(OOF[n]) == ntr and len(TST[n]) == nte

names = list(OOF)
report = {"members": {}}
for n in names:
    a = fast_auc(y, OOF[n])
    rho = spearmanr(OOF[n], OOF["v100"])[0]
    report["members"][n] = {"oof_auc": a, "spearman_vs_v100": rho}
    print(f"{n:10s} OOF {a:.6f}  与 v100 秩相关 {rho:.4f}")

R = {n: rk(OOF[n]) for n in names}
T = {n: rk(TST[n]) for n in names}


def nested(names, tag):
    ws, rows = [], []
    for i, (a_idx, b_idx) in enumerate(StratifiedKFold(5, shuffle=True, random_state=0).split(np.zeros(ntr), y)):
        wi, _ = hill({n: R[n][a_idx] for n in names}, y[a_idx], names)
        ws.append(wi)
        held = fast_auc(y[b_idx], sum(wi[n] * R[n][b_idx] for n in names))
        rows.append({"fold": i, "stack": held, "v100": fast_auc(y[b_idx], R["v100"][b_idx]),
                     "best_single": max(fast_auc(y[b_idx], R[n][b_idx]) for n in names)})
        print(f"  [{tag}] 嵌套折 {i}: v100 {rows[-1]['v100']:.6f} 最佳单成员 {rows[-1]['best_single']:.6f} -> 融合 {held:.6f} "
              f"(对 v100 {held - rows[-1]['v100']:+.6f})")
    W = {n: float(np.mean([wi[n] for wi in ws])) for n in names}
    oof = sum(W[n] * R[n] for n in names)
    tst = sum(W[n] * T[n] for n in names)
    auc = fast_auc(y, oof)
    gains = [r["stack"] - r["v100"] for r in rows]
    print(f"  [{tag}] 融合 OOF {auc:.6f} | 嵌套留出均值对 v100 {np.mean(gains):+.6f}，正向 {sum(g > 0 for g in gains)}/5 | 权重 "
          f"{ {k: round(v, 3) for k, v in sorted(W.items(), key=lambda x: -x[1]) if v > 0.004} }")
    return {"weights": W, "oof_auc": auc, "nested": rows, "mean_gain_vs_v100": float(np.mean(gains)),
            "positive_folds": int(sum(g > 0 for g in gains))}, oof, tst


def write_sub(path, score):
    sub = pd.DataFrame({"id": test_ids, "Will_Buy_EV": rankdata(score) / len(score)})
    assert len(sub) == 286571 and sub["Will_Buy_EV"].between(0, 1).all() and sub["id"].is_unique
    sub.to_csv(path, index=False)


report["v101_only"], oof_a, tst_a = nested(["v101_glm", "v101_lgbm", "v101_xgb"], "仅 v101")
report["all"], oof_b, tst_b = nested(names, "全部成员")
np.save(HERE / "oof_proba.npy", oof_b)
np.save(HERE / "test_proba.npy", tst_b)
write_sub(HERE / "submission.csv", tst_b)
write_sub(V101 / "submission.csv", tst_a)
(HERE / "cv_results.json").write_text(json.dumps(report, indent=2, default=float))
print("已写出 v102/submission.csv 与 v101/submission.csv")
