"""v104：自训成员（v101/v103 + V100/V85/V80）与公开 OOF 成员的嵌套秩融合。

公开成员（原样使用，未重训；文件在 public_inputs/）：
- heuljax：generator-aware ridge LR、XGB sample（notebook 输出）
- BlamerX：XGBoost + window encodings（notebook 输出）
- megayak：six-feature-views OOF library（A–F）与 RealMLP 3 种子
权重：百分位秩上贪心爬山（步长 0.02），5 折嵌套内拟合后取平均。
用法：python v104_blend_with_public_oof.py [own|all]   # own=只用自训成员（含 v103）
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.model_selection import StratifiedKFold

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
DATA = MODEL.parent / "data"
PUB = HERE / "public_inputs"
OLD = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/"
           "kaggle_Predicting_Electric_Vehicle_Purchases/model")
MODE = sys.argv[1] if len(sys.argv) > 1 else "all"

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


def aligned(path, col, ids):
    df = pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)
    s = df.set_index("id")[col].reindex(ids)
    assert not s.isna().any(), f"{path}: id 未对齐"
    return s.to_numpy(np.float64)


OOF, TST = {}, {}
V101 = MODEL / "v101_glm_margin_gbdt_10f"
for m in ["glm", "lgbm", "xgb"]:
    OOF[f"v101_{m}"] = np.load(V101 / f"oof_v101_{m}.npy")
    TST[f"v101_{m}"] = np.load(V101 / f"test_v101_{m}.npy")
V103 = MODEL / "v103_v85_features_glm_margin_10f" / "folds"
if all((V103 / f"fold_{k}.npz").exists() for k in range(10)):
    OOF["v103"], TST["v103"] = np.full(ntr, np.nan), np.zeros(nte)
    for k in range(10):
        f = np.load(V103 / f"fold_{k}.npz")
        OOF["v103"][f["valid_rows"]] = f["valid"]
        TST["v103"] += rk(f["test"]) / 10
    assert np.isfinite(OOF["v103"]).all()
for n, d in {"v100": "v100_v90_ctboost_nested_cv_blend", "v85": "v85_naji_v74_40f", "v80": "v80_strict_v61_outer104395303_40f"}.items():
    OOF[n] = np.load(OLD / d / "oof_proba.npy")
    TST[n] = np.load(OLD / d / "test_proba.npy")
OWN = list(OOF)
if MODE == "all":
    PUBLIC = {
        "pub_heuljax_lr": ("GENERATOR_AWARE_LOGREG_SAMPLE_OOF.parquet", "oof_pred", "GENERATOR_AWARE_LOGREG_SAMPLE_TEST.parquet", "test_pred"),
        "pub_heuljax_xgb": ("XGB_SAMPLE_OOF.parquet", "oof_pred", "XGB_SAMPLE_TEST.parquet", "test_pred"),
        "pub_blamerx_xgb": ("blamerx_oof.csv", "pred", "blamerx_test.csv", "Will_Buy_EV"),
        "pub_realmlp_3seed": ("oof_realmlp_g.csv", "G_realmlp_3seed", "test_realmlp_g.csv", "G_realmlp_3seed"),
    }
    for v in ["A_lgbm_triple_te_digits_3seed", "B_xgb_on_A_features", "C_no_digits_windows_lift_sm2_30_300",
              "D_no_exact_key_ladder_windows", "E_ladder25_250_2500_lift_sm5_50_500", "F_exact_rate_as_init_score"]:
        PUBLIC[f"pub_megayak_{v[0]}"] = ("oof_six_views.csv", v, "test_six_views.csv", v)
    for n, (fo, co, ft, ct) in PUBLIC.items():
        OOF[n] = aligned(PUB / fo, co, train_ids)
        TST[n] = aligned(PUB / ft, ct, test_ids)

names = list(OOF)
report = {"mode": MODE, "members": {}}
for n in names:
    assert len(OOF[n]) == ntr and len(TST[n]) == nte
    a = fast_auc(y, OOF[n])
    rho = spearmanr(OOF[n], OOF["v101_lgbm"])[0]
    report["members"][n] = {"oof_auc": a, "spearman_vs_v101_lgbm": rho}
    print(f"{n:20s} OOF {a:.6f}  与 v101_lgbm 秩相关 {rho:.4f}")
R = {n: rk(OOF[n]) for n in names}
T = {n: rk(TST[n]) for n in names}
REF = rk(np.load(MODEL / "v102_blend_v101_v100" / "oof_proba.npy"))     # 参照：已提交的 v102

ws, rows = [], []
for i, (a_idx, b_idx) in enumerate(StratifiedKFold(5, shuffle=True, random_state=0).split(np.zeros(ntr), y)):
    wi, _ = hill({n: R[n][a_idx] for n in names}, y[a_idx], names)
    ws.append(wi)
    held = fast_auc(y[b_idx], sum(wi[n] * R[n][b_idx] for n in names))
    ref = fast_auc(y[b_idx], REF[b_idx])
    rows.append({"fold": i, "stack": held, "v102": ref})
    print(f"  嵌套折 {i}: v102 {ref:.6f} -> 融合 {held:.6f} ({held - ref:+.6f})")
W = {n: float(np.mean([wi[n] for wi in ws])) for n in names}
oof = sum(W[n] * R[n] for n in names)
tst = sum(W[n] * T[n] for n in names)
gains = [r["stack"] - r["v102"] for r in rows]
report.update(weights=W, oof_auc=fast_auc(y, oof), nested=rows, mean_gain_vs_v102=float(np.mean(gains)),
              positive_folds=int(sum(g > 0 for g in gains)),
              own_weight=float(sum(W[n] for n in OWN)))
print(f"融合 OOF {report['oof_auc']:.6f} | 嵌套留出均值对 v102 {np.mean(gains):+.6f}，正向 {report['positive_folds']}/5 | 自训成员权重合计 {report['own_weight']:.3f}")
print("权重", {k: round(v, 3) for k, v in sorted(W.items(), key=lambda x: -x[1]) if v > 0.004})

out = HERE if MODE == "all" else MODEL / "v103_v85_features_glm_margin_10f"
sub = pd.DataFrame({"id": test_ids, "Will_Buy_EV": rankdata(tst) / nte})
assert len(sub) == 286571 and sub["id"].is_unique and sub["Will_Buy_EV"].between(0, 1).all()
sub.to_csv(out / "submission.csv", index=False)
np.save(out / "oof_proba.npy", oof)
np.save(out / "test_proba.npy", tst)
(out / "cv_results.json").write_text(json.dumps(report, indent=2, default=float))
print("已写出", out / "submission.csv")
