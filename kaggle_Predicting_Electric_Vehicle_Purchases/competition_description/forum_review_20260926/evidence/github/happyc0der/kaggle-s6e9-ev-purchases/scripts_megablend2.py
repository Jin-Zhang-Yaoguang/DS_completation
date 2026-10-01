"""Second pass: our members + every public OOF-backed member found so far. Rank-space hill-climb, nested check."""
import glob, json, os, numpy as np, pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from src.cv import get_data, load_oof
from src.postprocess import hard_edges
from src.submit import write_submission
tr, te, orig, static, y, folds = get_data("v2")
P = "data/public"; rk = lambda v: rankdata(v) / len(v)
O, T, names = [], [], []
def add(name, oof, test):
    oof, test = np.asarray(oof, float), np.asarray(test, float)
    if len(oof) != len(tr) or len(test) != len(te) or not (np.isfinite(oof).all() and np.isfinite(test).all()):
        print(f"  skip {name}: shape/nan"); return
    a = roc_auc_score(y, oof)
    if a < 0.94: print(f"  skip {name}: OOF {a:.4f}"); return
    O.append(rk(oof)); T.append(rk(test)); names.append(name); print(f"  {name:34s} OOF {a:.6f}")
def csv_col(path, col=None):
    d = pd.read_csv(path).set_index("id"); c = col or [c for c in d.columns if c not in ("Will_Buy_EV_true", "fold", "split_bin")][-1]
    return d[c]
def csv_pair(name, oof_path, test_path, oof_col=None, test_col=None):
    add(name, csv_col(oof_path, oof_col).reindex(tr.id).to_numpy(), csv_col(test_path, test_col).reindex(te.id).to_numpy())
for n in ["lgb_final_bag10", "cb_final_bag8", "nn_final_bag15"]:
    o, t = load_oof(n); add("ours_" + n, o, t)
so, st = pd.read_csv(f"{P}/sixviews/oof_six_views.csv").set_index("id"), pd.read_csv(f"{P}/sixviews/test_six_views.csv").set_index("id")
for c in [c for c in so.columns if c[0] in "ABCDEF" and "_" in c]:
    add("six_" + c[:22], so[c].reindex(tr.id).to_numpy(), st[c].reindex(te.id).to_numpy())
csv_pair("realmlp_G_3seed", f"{P}/sixviews/oof_realmlp_g.csv", f"{P}/sixviews/test_realmlp_g.csv", "G_realmlp_3seed", "G_realmlp_3seed")
csv_pair("yekenot_realmlp", f"{P}/realmlp/oof_preds.csv", f"{P}/realmlp/submission.csv")
for stem, oc, tc in [("Sergey_LGBM", "Will_Buy_EV", "Will_Buy_EV"), ("Pure LGBM_V3", "OOF_Pred", "Will_Buy_EV"), ("Pure LGBM_V1", "OOF_Pred", "Will_Buy_EV"),
                     ("XGBoost_Triple_TE_10folds", "OOF_Pred", "Will_Buy_EV"), ("XGBoost_Triple_TE_5folds", "OOF_Pred", "Will_Buy_EV")]:
    tp = f"{P}/naji_oof/{stem}_submission.csv" if os.path.exists(f"{P}/naji_oof/{stem}_submission.csv") else f"{P}/naji_oof/{stem}_test.csv"
    csv_pair("naji_" + stem.replace(" ", "_"), f"{P}/naji_oof/{stem}_oof.csv", tp, oc, tc)
csv_pair("naji_01_blend", f"{P}/naji_oof/01_blend_oof.csv", f"{P}/naji_oof/01_submission.csv")
for stem in ["jaz", "yek", "v19"]:
    csv_pair("rs_" + stem, f"{P}/s6e9-residual-stack-oof/{stem}_oof.csv", f"{P}/s6e9-residual-stack-oof/{stem}_test.csv", "pred", "pred")
add("hybrid_lgbm_3seed", np.load(f"{P}/s6e9-hybrid-lgbm-oof/oof_hybrid_3seed.npy"), np.load(f"{P}/s6e9-hybrid-lgbm-oof/test_hybrid_3seed.npy"))
fo, ft = pd.read_csv(f"{P}/s6e9-four-feature-views-one-ensemble-oof/oof_four_views.csv").set_index("id"), pd.read_csv(f"{P}/s6e9-four-feature-views-one-ensemble-oof/test_four_views.csv").set_index("id")
for c in [c for c in fo.columns if c[0] in "ABCD" and "_" in c]:
    add("four_" + c[:22], fo[c].reindex(tr.id).to_numpy(), ft[c].reindex(te.id).to_numpy())
for m in ["lgb", "xgb", "cat"]:
    add("digitleak_" + m, np.load(f"{P}/s6e9-digit-leak-oof/oof_{m}.npy"), np.load(f"{P}/s6e9-digit-leak-oof/test_{m}.npy"))
for f in sorted(glob.glob(f"{P}/hirge/oof_*.npy")):
    n = f.split("oof_")[-1][:-4]; tf = f"{P}/hirge/test_{n}.npy"
    if os.path.exists(tf):
        o, t = np.load(f), np.load(tf)
        if o.ndim == 1 and t.ndim == 1: add("hirge_" + n, o, t)
G = f"{P}/s6e9-golem-oof-library"
for f in sorted(glob.glob(f"{G}/oof_*_*.npy")):  # named members only (oof_a_lgbm.npy etc.)
    n = os.path.basename(f)[4:-4]; tf = f"{G}/test_{n}.npy"
    if os.path.exists(tf):
        add("golem_" + n, np.load(f), np.load(tf))
O, T = np.column_stack(O), np.column_stack(T); print("\nmembers:", len(names))
pos = y == 1
def auc_of(score, mask):
    s = score[mask]; yy = pos[mask]; r = rankdata(s); n1 = yy.sum(); n0 = len(yy) - n1
    return (r[yy].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
def hill_climb(mask, steps=60):
    k = O.shape[1]; counts = np.zeros(k, int)
    i0 = max(range(k), key=lambda i: auc_of(O[:, i], mask)); counts[i0] = 1; cur = O[:, i0].copy(); cur_auc = auc_of(cur, mask)
    for _ in range(steps - 1):
        tot = counts.sum()
        a, i = max((auc_of((cur * tot + O[:, i]) / (tot + 1), mask), i) for i in range(k))
        if a <= cur_auc + 1e-9: break
        counts[i] += 1; cur = (cur * tot + O[:, i]) / (tot + 1); cur_auc = a
    return counts / counts.sum()
gains = []
for f in range(10):
    trm, vam = folds != f, folds == f
    w = hill_climb(trm); gains.append(auc_of(O @ w, vam) - max(auc_of(O[:, i], vam) for i in range(O.shape[1])))
print(f"nested gain over best single: mean {np.mean(gains)*1e5:+.2f}e-5, positive in {(np.array(gains) > 0).sum()}/10")
W = hill_climb(np.ones(len(y), bool))
print("weights:", {n: round(w, 3) for n, w in zip(names, W) if w > 0})
ob, tb = O @ W, T @ W
auc = roc_auc_score(y, hard_edges(ob, tr)); print(f"blend OOF {roc_auc_score(y, ob):.6f} | hard edges {auc:.6f}")
np.save("experiments/megablend3_oof.npy", ob); np.save("experiments/megablend3_test.npy", tb)
json.dump(dict(names=names, weights=W.tolist()), open("experiments/megablend3_weights.json", "w"))
print("wrote", write_submission(hard_edges(tb, te), f"mega5_{auc:.5f}", cv=float(auc)))
