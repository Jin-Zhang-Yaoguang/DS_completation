"""OOF-based blending: weight optimisation (scipy) and hill climbing, on probabilities or ranks."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

from .cv import get_data, load_oof


def _rank(p):
    return rankdata(p) / len(p)


def collect(names, use_rank=False):
    _, _, _, _, y, _ = get_data()
    oofs, tests = zip(*[load_oof(n) for n in names])
    O = np.column_stack([_rank(o) if use_rank else o for o in oofs])
    T = np.column_stack([_rank(t) if use_rank else t for t in tests])
    return O, T, y


def optimize_weights(O, y, n_restarts=5, seed=0):
    k = O.shape[1]
    rng = np.random.default_rng(seed)
    best_w, best_auc = np.ones(k) / k, -1
    def neg(w):
        w = np.abs(w); w = w / w.sum()
        return -roc_auc_score(y, O @ w)
    for r in range(n_restarts):
        w0 = np.ones(k) / k if r == 0 else rng.dirichlet(np.ones(k))
        res = minimize(neg, w0, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-7, "maxiter": 2000})
        w = np.abs(res.x); w /= w.sum(); auc = -res.fun
        if auc > best_auc:
            best_w, best_auc = w, auc
    return best_w, best_auc


def hill_climb(O, y, names, iters=30, step=0.05):
    aucs = [roc_auc_score(y, O[:, i]) for i in range(O.shape[1])]
    w = np.zeros(O.shape[1]); w[int(np.argmax(aucs))] = 1.0
    cur = max(aucs)
    for _ in range(iters):
        best_i, best_auc = None, cur
        for i in range(O.shape[1]):
            w2 = w.copy(); w2[i] += step
            a = roc_auc_score(y, O @ (w2 / w2.sum()))
            if a > best_auc + 1e-7:
                best_i, best_auc = i, a
        if best_i is None:
            break
        w[best_i] += step; cur = best_auc
    w /= w.sum()
    return w, cur


def report(names, use_rank=False):
    O, T, y = collect(names, use_rank)
    for n, i in zip(names, range(O.shape[1])):
        print(f"  {n:32s} {roc_auc_score(y, O[:, i]):.6f}")
    C = np.corrcoef(O.T)
    print("  corr:\n", np.round(C, 4))
    w, a = optimize_weights(O, y)
    print(f"  optimized: {a:.6f} weights {np.round(w, 3)}")
    w2, a2 = hill_climb(O, y, names)
    print(f"  hillclimb: {a2:.6f} weights {np.round(w2, 3)}")
    return (w, a, T @ w) if a >= a2 else (w2, a2, T @ w2)
