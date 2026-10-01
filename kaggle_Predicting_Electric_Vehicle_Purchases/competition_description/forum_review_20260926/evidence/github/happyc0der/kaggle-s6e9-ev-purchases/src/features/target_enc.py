"""Nested out-of-fold target encoding. Keys are int64 arrays built from one or more columns."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold


def make_key(df: pd.DataFrame, cols, decimals=1) -> np.ndarray:
    key = np.zeros(len(df), dtype=np.int64)
    for c in cols:
        v = np.round(df[c].to_numpy(dtype=float) * 10**decimals).astype(np.int64)
        key = key * 10_000_000 + v
    return key


def te_fit_apply(key_fit, y_fit, key_apply, m: float, prior: float):
    u, inv = np.unique(key_fit, return_inverse=True)
    s = np.bincount(inv, weights=y_fit, minlength=len(u))
    c = np.bincount(inv, minlength=len(u)).astype(float)
    if m < 0:  # "auto": empirical-Bayes shrinkage (sklearn TargetEncoder smooth='auto')
        means = s / np.maximum(c, 1)
        ss = np.bincount(inv, weights=y_fit ** 2, minlength=len(u))
        within = np.sum(ss - c * means ** 2) / max(len(y_fit) - len(u), 1)
        between = max(np.var(means), 1e-12)
        m = within / between
    enc = (s + m * prior) / (c + m)
    idx = np.searchsorted(u, key_apply)
    idx_c = np.minimum(idx, len(u) - 1)
    found = u[idx_c] == key_apply
    return np.where(found, enc[idx_c], prior).astype(np.float32)


@dataclass
class TESpec:
    cols: tuple
    m: float = 10.0
    decimals: int = 1
    binwidth: float | None = None  # if set, first column is binned by this width
    name: str = ""
    inner: int = 5  # inner folds for the training-row encoding
    offset: float = 0.0  # shift applied before binning (half-width offset gives staggered bins)
    resid: bool = False  # encode mean(y - p_base) instead of mean(y); p_base supplied by the runner
    modulus: float | None = None  # if set, first column is replaced by (col mod modulus) before keying
    nbag: int = 1  # >1: average the training-row encoding over nbag different inner-fold seeds (variance reduction)

    def key(self, df: pd.DataFrame) -> np.ndarray:
        if self.modulus is not None:
            d = df[list(self.cols)].copy()
            d[self.cols[0]] = np.round(d[self.cols[0]]).astype(np.int64) % int(self.modulus)
            return make_key(d, self.cols, 0)
        if self.binwidth is None:
            return make_key(df, self.cols, self.decimals)
        d = df[list(self.cols)].copy()
        d[self.cols[0]] = np.floor((d[self.cols[0]] + self.offset) / self.binwidth)
        return make_key(d, self.cols, 0)

    @property
    def colname(self):
        if self.name:
            return self.name
        b = f"_b{self.binwidth:g}" if self.binwidth else ""
        i = f"_i{self.inner}" if self.inner != 5 else ""
        i += f"_o{self.offset:g}" if self.offset else ""
        i += "_r" if self.resid else ""
        i += f"_mod{self.modulus:g}" if self.modulus else ""
        i += f"_bag{self.nbag}" if self.nbag > 1 else ""
        return "te_" + "_".join(c[:6] for c in self.cols) + b + f"_m{self.m:g}" + i


def nested_te(spec: TESpec, df_tr: pd.DataFrame, y: np.ndarray, tr_idx, va_idx, df_te: pd.DataFrame,
              inner_folds=None, seed=0, p_base=None):
    """Returns (enc_train_rows[tr_idx order], enc_valid_rows, enc_test).

    p_base: optional (train_probs, test_probs) used when spec.resid is set; the encoded target becomes y - p_base."""
    inner_folds = inner_folds or spec.inner
    k_all = spec.key(df_tr)
    k_te = spec.key(df_te)
    y_strat = y[tr_idx]
    if spec.resid:
        assert p_base is not None, "resid TE needs p_base"
        y = y - p_base[0]
    prior = float(y[tr_idx].mean())
    k_tr, y_tr = k_all[tr_idx], y[tr_idx]
    enc_tr = np.zeros(len(tr_idx), dtype=np.float32)
    nbag = max(1, getattr(spec, "nbag", 1))
    for r in range(nbag):
        skf = StratifiedKFold(inner_folds, shuffle=True, random_state=seed + 1000 * r)
        for a, b in skf.split(np.zeros(len(tr_idx)), y_strat):
            enc_tr[b] += te_fit_apply(k_tr[a], y_tr[a], k_tr[b], spec.m, prior) / nbag
    enc_va = te_fit_apply(k_tr, y_tr, k_all[va_idx], spec.m, prior)
    enc_te = te_fit_apply(k_tr, y_tr, k_te, spec.m, prior)
    return enc_tr, enc_va, enc_te


@dataclass
class NTESpec:
    """Neighbourhood target statistics over equal-width bins of one numeric column (nested like TESpec).

    Emits per row: TE of own bin, kernel-smoothed TE, left-bin TE, right-bin TE, slope, curvature, log count."""
    col: str
    binwidth: float
    m: float = 10.0
    inner: int = 5
    sigma: float = 0.8

    @property
    def prefix(self):
        return f"nte_{self.col[:6]}_b{self.binwidth:g}"

    @property
    def colnames(self):
        return [f"{self.prefix}_{s}" for s in ("c", "sym", "l", "r", "slope", "curv", "logn")]

    def _codes(self, v):
        return np.floor(v / self.binwidth).astype(np.int64)

    def _stats(self, codes_fit, y_fit, lo, n_bins, prior):
        c = codes_fit - lo
        sums = np.bincount(c, weights=y_fit, minlength=n_bins).astype(np.float64)
        cnt = np.bincount(c, minlength=n_bins).astype(np.float64)
        m = self.m
        central = (sums + m * prior) / (cnt + m)
        ls, lc = np.r_[0.0, sums[:-1]], np.r_[0.0, cnt[:-1]]
        rs, rc = np.r_[sums[1:], 0.0], np.r_[cnt[1:], 0.0]
        left = (ls + m * prior) / (lc + m)
        right = (rs + m * prior) / (rc + m)
        kernel = np.exp(-0.5 * (np.arange(-2, 3) / self.sigma) ** 2)
        ns, nc = np.convolve(sums, kernel, mode="same"), np.convolve(cnt, kernel, mode="same")
        sym = (ns + m * kernel.sum() * prior) / (nc + m * kernel.sum())
        return np.column_stack([central, sym, left, right, right - left, central - 0.5 * (left + right), np.log1p(cnt)]).astype(np.float32)

    def nested(self, df_tr, y, tr_idx, va_idx, df_te, seed=0):
        v_all, v_te = df_tr[self.col].to_numpy(float), df_te[self.col].to_numpy(float)
        codes, codes_te = self._codes(v_all), self._codes(v_te)
        lo, hi = min(codes.min(), codes_te.min()), max(codes.max(), codes_te.max())
        n_bins = hi - lo + 1
        c_tr, y_tr = codes[tr_idx], y[tr_idx]
        prior = float(y_tr.mean())
        out_tr = np.zeros((len(tr_idx), 7), np.float32)
        skf = StratifiedKFold(self.inner, shuffle=True, random_state=seed)
        for a, b in skf.split(np.zeros(len(tr_idx)), y_tr):
            st = self._stats(c_tr[a], y_tr[a], lo, n_bins, float(y_tr[a].mean()))
            out_tr[b] = st[c_tr[b] - lo]
        st = self._stats(c_tr, y_tr, lo, n_bins, prior)
        return out_tr, st[codes[va_idx] - lo], st[codes_te - lo]
