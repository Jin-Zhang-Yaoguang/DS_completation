"""v110：精简成员的嵌套秩融合。

相对 v108 的改动（只动融合层）：
- 同族去冗余：10 折 v101 由 20 折 v105 取代；严格 v80 家族 6 个 40 折变体（v80/v81/v82/v87/v92/v96）先等权秩平均成一个成员；
- 补入现成的不同学习器成员：v77 CatBoost 双表示、v78 MLP；
- 爬山步长 0.02 → 0.01；可选 v109（20 折 donor 基底）替换 v107。
参照：已提交的 v104（嵌套留出逐折比较）。
用法：python v110_blend_compact.py [tag]   # tag 含 v109 / v113 / glm111 时加入对应成员，如 v109_v113_glm111
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.model_selection import StratifiedKFold

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
DATA = MODEL.parent / "data"
PUB = MODEL / "v104_blend_with_public_oof" / "public_inputs"
OLD = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/"
           "kaggle_Predicting_Electric_Vehicle_Purchases/model")
TAG = sys.argv[1] if len(sys.argv) > 1 else "base"
STEP = 0.01

train = pd.read_csv(DATA / "train.csv", usecols=["id", "Will_Buy_EV"])
train_ids = train["id"].to_numpy()
test_ids = pd.read_csv(DATA / "test.csv", usecols=["id"])["id"].to_numpy()
y = (train["Will_Buy_EV"] == "Yes").to_numpy().astype(np.int8)
ntr, nte = len(y), len(test_ids)


def fast_auc(yb, s):
    order = np.argsort(s, kind="stable")
    r = np.empty(len(s))
    r[order] = np.arange(1, len(s) + 1)
    n1 = yb.sum()
    return (r[yb == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(yb) - n1))


def rk(v):
    return rankdata(v) / len(v)


def hill(R, yb, names, step=STEP, iters=600):
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


def folds_member(d, n_folds, key="valid"):
    o, t = np.full(ntr, np.nan), np.zeros(nte)
    for k in range(n_folds):
        f = np.load(d / f"fold_{k}.npz")
        o[f["valid_rows"]] = f[key]
        t += rk(f["test"]) / n_folds
    assert np.isfinite(o).all()
    return o, t


def aligned(path, col, ids):
    df = pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)
    s = df.set_index("id")[col].reindex(ids)
    assert not s.isna().any()
    return s.to_numpy(np.float64)


OOF, TST = {}, {}
V105 = MODEL / "v105_glm_margin_gbdt_20f"
for m in ["glm", "lgbm", "xgb"]:
    OOF[f"v105_{m}"] = np.load(V105 / f"oof_v105_{m}.npy")
    TST[f"v105_{m}"] = np.load(V105 / f"test_v105_{m}.npy")
V109 = MODEL / "v109_donor_basis_xgb_glm_margin_20f" / "folds"
if "bag" in TAG:       # v113 与换种子的 v114 平均（外层划分与起点相同，逐行 logit 平均）
    o1, t1 = folds_member(MODEL / "v113_merged_basis_lgbm_glm_margin_20f" / "folds", 20)
    o2, t2 = folds_member(MODEL / "v114_merged_basis_lgbm_20f_seed2" / "folds", 20)
    OOF["v113_v114_bag"], TST["v113_v114_bag"] = (o1 + o2) / 2, (t1 + t2) / 2
if "v115" in TAG:      # 同两套特征、不设线性起点的 20 折 LGBM（独立视角）
    OOF["v115"], TST["v115"] = folds_member(MODEL / "v115_merged_basis_lgbm_no_margin_20f" / "folds", 20)
if "v113" in TAG:      # 同时看到两套特征的 20 折残差 LGBM
    OOF["v113"], TST["v113"] = folds_member(MODEL / "v113_merged_basis_lgbm_glm_margin_20f" / "folds", 20)
if "glm111" in TAG:    # 追加 donor 特征后的线性模型（10 折）
    OOF["v111_glm"] = np.load(MODEL / "v111_glm_donor_basis_10f" / "oof_v111_glm.npy")
    TST["v111_glm"] = np.load(MODEL / "v111_glm_donor_basis_10f" / "test_v111_glm.npy")
if "v109" in TAG and all((V109 / f"fold_{k}.npz").exists() for k in range(20)):
    OOF["v109"], TST["v109"] = folds_member(V109, 20)
else:
    OOF["v107"], TST["v107"] = folds_member(MODEL / "v107_donor_basis_xgb_glm_margin_10f" / "folds", 10)
fam = ["v80_strict_v61_outer104395303_40f", "v81_strict_v61_split7_40f", "v82_strict_v61_split2026_40f",
       "v87_strict_v80_commute_charging_burden_40f", "v92_strict_v80_vehicle_demand_affordability_40f",
       "v96_strict_v80_outer42_matched_control_40f"]
OOF["strict_family"] = np.mean([rk(np.load(OLD / d / "oof_proba.npy")) for d in fam], axis=0)
TST["strict_family"] = np.mean([rk(np.load(OLD / d / "test_proba.npy")) for d in fam], axis=0)
for n, d in {"v100": "v100_v90_ctboost_nested_cv_blend", "v85": "v85_naji_v74_40f",
             "v77_catboost": "v77_catboost_dual_40f", "v78_mlp": "v78_mlp_te_40f"}.items():
    OOF[n] = np.load(OLD / d / "oof_proba.npy")
    TST[n] = np.load(OLD / d / "test_proba.npy")
OWN = list(OOF)
PUBLIC = {
    "pub_heuljax_xgb": ("XGB_SAMPLE_OOF.parquet", "oof_pred", "XGB_SAMPLE_TEST.parquet", "test_pred"),
    "pub_blamerx_xgb": ("blamerx_oof.csv", "pred", "blamerx_test.csv", "Will_Buy_EV"),
    "pub_realmlp_3seed": ("oof_realmlp_g.csv", "G_realmlp_3seed", "test_realmlp_g.csv", "G_realmlp_3seed"),
    "pub_megayak_B": ("oof_six_views.csv", "B_xgb_on_A_features", "test_six_views.csv", "B_xgb_on_A_features"),
    "pub_megayak_D": ("oof_six_views.csv", "D_no_exact_key_ladder_windows", "test_six_views.csv", "D_no_exact_key_ladder_windows"),
}
for n, (fo, co, ft, ct) in PUBLIC.items():
    OOF[n] = aligned(PUB / fo, co, train_ids)
    TST[n] = aligned(PUB / ft, ct, test_ids)

names = list(OOF)
report = {"tag": TAG, "step": STEP, "members": {}}
for n in names:
    a = fast_auc(y, OOF[n])
    report["members"][n] = {"oof_auc": a, "spearman_vs_v105_lgbm": spearmanr(OOF[n], OOF["v105_lgbm"])[0]}
    print(f"{n:18s} OOF {a:.6f}  与 v105_lgbm 秩相关 {report['members'][n]['spearman_vs_v105_lgbm']:.4f}")
SPACE = os.getenv("V110_SPACE", "rank")    # rank：百分位秩相加；probit：秩先映射为正态分数 Φ⁻¹(rank) 再相加
if SPACE == "probit":
    from scipy.stats import norm
    tf = lambda v: norm.ppf(rankdata(v) / (len(v) + 1))
else:
    tf = rk
R = {n: tf(OOF[n]) for n in names}
T = {n: tf(TST[n]) for n in names}
import os
REF_NAME = os.getenv("V110_REF", "v104")     # 参照：v104 或已提交的 v110 v109 版
REF = rk(np.load(MODEL / ("v104_blend_with_public_oof" if REF_NAME == "v104" else "v110_blend_compact/v109") / "oof_proba.npy"))

ws, rows = [], []
for i, (a_idx, b_idx) in enumerate(StratifiedKFold(5, shuffle=True, random_state=0).split(np.zeros(ntr), y)):
    wi, _ = hill({n: R[n][a_idx] for n in names}, y[a_idx], names)
    ws.append(wi)
    held = fast_auc(y[b_idx], sum(wi[n] * R[n][b_idx] for n in names))
    ref = fast_auc(y[b_idx], REF[b_idx])
    rows.append({"fold": i, "stack": held, "ref_v104": ref})
    print(f"  嵌套折 {i}: {REF_NAME} {ref:.6f} -> 融合 {held:.6f} ({held - ref:+.6f})")
W = {n: float(np.mean([wi[n] for wi in ws])) for n in names}
oof = sum(W[n] * R[n] for n in names)
tst = sum(W[n] * T[n] for n in names)
gains = [r["stack"] - r["ref_v104"] for r in rows]
report.update(weights=W, oof_auc=fast_auc(y, oof), nested=rows, mean_gain_vs_v104=float(np.mean(gains)),
              positive_folds=int(sum(g > 0 for g in gains)), own_weight=float(sum(W[n] for n in OWN)))
print(f"融合 OOF {report['oof_auc']:.6f} | 嵌套留出均值对 {REF_NAME} {np.mean(gains):+.6f}，正向 {report['positive_folds']}/5 | "
      f"自训成员权重合计 {report['own_weight']:.3f}")
print("权重", {k: round(v, 3) for k, v in sorted(W.items(), key=lambda x: -x[1]) if v > 0.004})

out = HERE / (TAG + ("_probit" if SPACE == "probit" else ""))
out.mkdir(exist_ok=True)
sub = pd.DataFrame({"id": test_ids, "Will_Buy_EV": rankdata(tst) / nte})
assert len(sub) == 286571 and sub["id"].is_unique and sub["Will_Buy_EV"].between(0, 1).all()
sub.to_csv(out / "submission.csv", index=False)
np.save(out / "oof_proba.npy", oof)
np.save(out / "test_proba.npy", tst)
(out / "cv_results.json").write_text(json.dumps(report, indent=2, default=float))
print("已写出", out / "submission.csv")
