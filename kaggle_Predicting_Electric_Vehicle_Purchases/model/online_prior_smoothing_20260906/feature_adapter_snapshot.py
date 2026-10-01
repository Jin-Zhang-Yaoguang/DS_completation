"""Frozen feature recipes with explicit fit labels and label-free query rows."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder

PROJECT = Path(__file__).resolve().parents[3]
TARGET = "Will_Buy_EV"


def module_at(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_naji_static(raw_x, test_x, original):
    """V68 build_features, with synthetic targets removed from its interface.

    Numerical/static operations and column order are unchanged. The dummy target
    is excluded from every statistic and is never returned. Original labels are
    allowed only as the frozen external-source marginal prior.
    """
    train = raw_x.copy(); test = test_x.copy(); original = original.copy()
    train[TARGET] = 0
    original[TARGET] = original[TARGET].map({"Yes": 1, "No": 0})
    train["is_train"] = 1; test["is_train"] = 0; test[TARGET] = np.nan
    combined = pd.concat([train, test], ignore_index=True)
    combined.drop(columns=["Number_of_Cars_Owned"], inplace=True, errors="ignore")
    cat_cols = combined.select_dtypes(include=["object", "string"]).columns.tolist()
    num_cols = [col for col in combined if col not in cat_cols + ["id", "is_train", TARGET]]
    digits = []
    for col in list(num_cols):
        values = combined[col].fillna(0)
        for power in range(-4, 4):
            name = f"{col}_digit{power}"
            combined[name] = (values // (10**power) % 10).astype("int8")
            digits.append(name)
    num_cols.extend(digits)
    original_mean = float(original[TARGET].mean())
    for col in cat_cols + num_cols:
        if col in original:
            mapping = original.groupby(col, observed=False)[TARGET].mean()
            combined[f"{col}_org_mean"] = combined[col].map(mapping).fillna(original_mean).astype(float)
    as_cats = []
    for col in num_cols:
        name = f"{col}_cat"
        combined[name] = combined[col].fillna("NaN").astype(str)
        as_cats.append(name)
    for width in (10, 100):
        name = f"Annual_Income_USD_bin{width}_cat"
        combined[name] = ((combined["Annual_Income_USD"] // width).astype(np.int64).astype(str))
        as_cats.append(name)
    all_cats = cat_cols + as_cats
    for col in all_cats:
        frequency = combined[col].value_counts(normalize=True)
        combined[f"{col}_fe"] = combined[col].map(frequency).fillna(0).astype(float)
    combined["is_30k_spike"] = (combined.Annual_Income_USD == 30000.).astype("int8")
    combined["is_millionaire_cliff"] = (combined.Annual_Income_USD >= 170537.).astype("int8")
    combined["is_dead_zone"] = combined.Annual_Income_USD.between(38000., 42000.).astype("int8")
    combined["is_env_hater"] = (combined.Environmental_Concern_Level == 1).astype("int8")
    train_frame = combined[combined.is_train == 1].drop(columns=["is_train"])
    test_frame = combined[combined.is_train == 0].drop(columns=["is_train", TARGET])
    eval_cols = [c for c in train_frame if c not in ["id", TARGET] and pd.api.types.is_numeric_dtype(train_frame[c])]
    corr = train_frame[eval_cols].corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    drop_corr = [c for c in upper if (upper[c] == 1.).any()]
    drop_const = [c for c in train_frame if train_frame[c].nunique() == 1]
    drop_const += [c for c in test_frame if test_frame[c].nunique() == 1]
    drop = sorted(set(drop_corr).union(drop_const) - {"id", TARGET})
    train_frame = train_frame.drop(columns=drop, errors="ignore")
    test_frame = test_frame.drop(columns=drop, errors="ignore")
    te_cols = [c for c in all_cats if c not in drop]
    features = [c for c in test_frame if c != "id"]
    return train_frame[features].reset_index(drop=True), test_frame[features].reset_index(drop=True), te_cols


class Backend:
    def __init__(self, family, static, keys=None, te_columns=None, strict_encoder=None):
        self.family = family; self.static = static
        self.keys = keys or {}; self.te_columns = te_columns or []
        self.strict_encoder = strict_encoder

    def encode(self, fit_rows, fit_y, query_rows, seed):
        fit_rows = np.asarray(fit_rows, dtype=np.int64)
        query_rows = np.asarray(query_rows, dtype=np.int64)
        fit_y = np.asarray(fit_y, dtype=np.int8)
        if len(fit_rows) != len(fit_y) or np.intersect1d(fit_rows, query_rows).size:
            raise ValueError("fit/query scope invalid")
        if self.family == "v80":
            inner = list(StratifiedKFold(5, shuffle=True, random_state=seed).split(np.zeros(len(fit_y)), fit_y))
            fit_blocks = [self.static.iloc[fit_rows].to_numpy(np.float32)]
            query_blocks = [self.static.iloc[query_rows].to_numpy(np.float32)]
            names = list(self.static.columns)
            for key, codes in self.keys.items():
                a, _, c = self.strict_encoder(codes[fit_rows], codes[query_rows], fit_y, np.arange(len(fit_rows)), np.array([],dtype=np.int64), inner, (5.,15.,80.))
                fit_blocks.append(a); query_blocks.append(c)
                names += [f"te_{key}_m{s:g}" for s in (5.,15.,80.)]
        else:
            fit = self.static.iloc[fit_rows]; query = self.static.iloc[query_rows]
            numeric = [c for c in self.static if c not in self.te_columns]
            # Original V85 passes a mixed numeric DataFrame to LightGBM; its
            # static float64 columns must not be silently rounded to float32.
            fit_blocks = [fit[numeric].to_numpy(np.float64)]
            query_blocks = [query[numeric].to_numpy(np.float64)]
            names = list(numeric)
            for tag, smooth in (("auto","auto"),("10",10.)):
                encoder = TargetEncoder(cv=5, shuffle=True, smooth=smooth, random_state=seed)
                fit_blocks.append(encoder.fit_transform(fit[self.te_columns],fit_y).astype(np.float32))
                query_blocks.append(encoder.transform(query[self.te_columns]).astype(np.float32))
                names += [f"{c}_TE_{tag}" for c in self.te_columns]
        x_fit, x_query = np.column_stack(fit_blocks), np.column_stack(query_blocks)
        if not np.isfinite(x_fit).all() or not np.isfinite(x_query).all():
            raise ValueError("nonfinite encoded features")
        return x_fit, x_query, names


def load_backend(family):
    raw = pd.read_csv(PROJECT/"data/train.csv", usecols=lambda c: c != TARGET)
    test = pd.read_csv(PROJECT/"data/test.csv")
    if family == "v80":
        source = PROJECT/"model/v80_strict_v61_outer104395303_40f/v80_strict_v61_outer104395303_40f.py"
        v80 = module_at(source,"e2e_v80_recipe")
        v80.strict_prior_self_check()
        recipe = v80.load_recipe()
        static, _, keys, _ = recipe.base.build_static_features(raw,test)
        if static.shape[1] != 62 or len(keys) != 17:
            raise ValueError("V80 static feature schema mismatch")
        return Backend("v80",static,keys=keys,strict_encoder=v80.strict_encode_key)
    original = pd.read_csv(PROJECT/"data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        static, te_cols = build_naji_static(raw,test,original)
    return Backend("v85",static,te_columns=te_cols)
