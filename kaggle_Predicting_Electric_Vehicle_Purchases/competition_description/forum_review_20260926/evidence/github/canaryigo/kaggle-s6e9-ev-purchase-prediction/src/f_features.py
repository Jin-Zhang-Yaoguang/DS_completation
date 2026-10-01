"""Frozen Pure F preprocessing. See reports/sources.md for attribution."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import TargetEncoder
from .old_features import NUM,CAT,features,transform_fold

NB_NUM = [n for n in NUM if n != 'Number_of_Cars_Owned']

NB_PARAMS = dict(n_estimators=20000, learning_rate=0.02, max_depth=5, num_leaves=32, min_child_samples=10, subsample=0.812763, colsample_bytree=0.30293, reg_alpha=0.07094, reg_lambda=2.03303, max_bin=1024, feature_pre_filter=False)

def nb_frame(df, spec):
    x = df.drop(columns=['id', 'Will_Buy_EV', 'Number_of_Cars_Owned'], errors='ignore').copy()
    nums = NB_NUM.copy()
    digits = {}
    if not spec.get('no_digits', False):
        for n in nums:
            for k in range(-4, 4):
                digits[f'{n}_digit{k}'] = (x[n].fillna(0) // 10 ** k % 10).astype('int8')
    x = pd.concat([x, pd.DataFrame(digits, index=x.index)], axis=1)
    nums += list(digits)
    keys = CAT + [n + '_cat' for n in nums]
    x = pd.concat([x, pd.DataFrame({n + '_cat': x[n].astype(str) for n in nums}, index=x.index)], axis=1)
    if not spec.get('no_flags', False):
        x['is_30k_spike'] = (x.Annual_Income_USD == 30000.0).astype('int8')
        x['is_millionaire_cliff'] = (x.Annual_Income_USD >= 170537.0).astype('int8')
        x['is_dead_zone'] = x.Annual_Income_USD.between(38000.0, 42000.0).astype('int8')
        x['is_env_hater'] = (x.Environmental_Concern_Level == 1).astype('int8')
    bins = []
    if not spec.get('no_bins', False):
        for name, col, scale in [('income_exact_int', 'Annual_Income_USD', 1), ('income100_floor', 'Annual_Income_USD', 100), ('income1000_floor', 'Annual_Income_USD', 1000), ('commute_integer', 'Daily_Commute_km', 1)]:
            x[name] = np.floor(x[col] / scale).astype(str)
            bins.append(name)
    return (x, keys, keys + bins)

def add_original(frames, orig):
    prior = float(orig.Will_Buy_EV.mean())
    maps = {}
    for n in CAT + NB_NUM:
        mapping = orig.groupby(n, observed=False).Will_Buy_EV.mean()
        maps[n] = mapping
        for z in frames:
            z[n + '_org_mean'] = z[n].map(mapping).astype(float).fillna(prior)
    return dict(prior=prior, maps=maps)

def prune(a, b, c):
    numeric = a.select_dtypes('number')
    corr = numeric.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    drop = [n for n in upper if (upper[n] == 1.0).any()]
    drop = list(dict.fromkeys(drop + [n for n in a if a[n].nunique() == 1]))
    return ([z.drop(columns=drop) for z in [a, b, c]], drop)

def prepare(train, test, y, tr, va, spec, fold, orig):
    fe = spec.get('fe', False)
    triple = spec.get('te', False)
    external = spec.get('external', False)
    aux = {}
    seed = 42 + fold - 1
    if fe:
        X, freqkeys, keys = nb_frame(train, spec)
        T, _, _ = nb_frame(test, spec)
        a, b, c = (X.iloc[tr].copy(), X.iloc[va].copy(), T.copy())
        if external:
            aux['original'] = add_original([a, b, c], orig)
        aux['frequency'] = {}
        for n in freqkeys:
            mapping = a[n].value_counts(normalize=True)
            aux['frequency'][n] = mapping
            for z in [a, b, c]:
                z[n + '_fe'] = z[n].map(mapping).fillna(0.0).astype(float)
        raw = [n for n in train if n not in ['id', 'Will_Buy_EV', 'Number_of_Cars_Owned']]
        digit_cols = [f'{n}_digit{k}' for n in NB_NUM for k in range(-4, 4) if f'{n}_digit{k}' in a]
        org_cols = [n + '_org_mean' for n in CAT + NB_NUM] if external else []
        numeric_cats = [n for n in freqkeys if n not in CAT]
        flag_cols = [n for n in a if n.startswith('is_')]
        bin_cols = [n for n in keys if n not in freqkeys]
        ordered = raw + digit_cols + org_cols + numeric_cats + [n + '_fe' for n in freqkeys] + flag_cols + bin_cols
        assert len(ordered) == len(a.columns) and set(ordered) == set(a.columns)
        a, b, c = [z[ordered] for z in [a, b, c]]
        (a, b, c), drop = prune(a, b, c)
        keys = [n for n in keys if n not in drop]
        aux['drop'] = drop
        if not triple:
            te = TargetEncoder(smooth=20.0, target_type='binary', cv=5, shuffle=True, random_state=seed)
            names = ['te_exact_' + n for n in NB_NUM]
            a[names] = te.fit_transform(a[NB_NUM].astype(str), y[tr])
            b[names] = te.transform(b[NB_NUM].astype(str))
            c[names] = te.transform(c[NB_NUM].astype(str))
            aux['baseline_te'] = te
    elif triple:
        X = features(train, ['digits'])
        T = features(test, ['digits'])
        a, b, c = (X.iloc[tr].copy(), X.iloc[va].copy(), T.copy())
        aux['frequency'] = {}
        for n in NUM:
            mapping = a[n].value_counts(normalize=True)
            aux['frequency'][n] = mapping
            for z in [a, b, c]:
                z['frequency_' + n] = z[n].map(mapping).fillna(0.0)
        numeric = X.select_dtypes('number').columns.tolist()
        keys = CAT + ['key_' + n for n in numeric]
        for z in [a, b, c]:
            for n in numeric:
                z['key_' + n] = z[n].astype(str)
        if external:
            aux['original'] = add_original([a, b, c], orig)
    else:
        X = features(train, ['identity_te', 'digits'])
        T = features(test, ['identity_te', 'digits'])
        a, b, c, _, base_enc = transform_fold(X, T, y, tr, va, 'lgbm', ['identity_te', 'digits'], seed)
        aux['baseline_encoders'] = base_enc
        if external:
            aux['original'] = add_original([a, b, c], orig)
        keys = []
    if triple:
        aux['target_keys'] = keys
        aux['target_encoders'] = {}
        smoothings = ['auto', 10.0] if spec.get('dual', False) else ['auto', 10.0, 100.0]
        pre_te_columns = list(a.columns)
        for smoothing in smoothings:
            te = TargetEncoder(smooth=smoothing, cv=5, shuffle=True, random_state=42)
            names = [n + '_TE_' + str(smoothing) for n in keys]
            a[names] = te.fit_transform(a[keys], y[tr]).astype('float32')
            b[names] = te.transform(b[keys]).astype('float32')
            c[names] = te.transform(c[keys]).astype('float32')
            aux['target_encoders'][str(smoothing)] = te
        ordered = [n for n in pre_te_columns if n not in keys] + [n + '_TE_' + str(v) for n in keys for v in smoothings]
        a, b, c = [z[ordered] for z in [a, b, c]]
    aux['categories'] = {}
    for n in a.select_dtypes(include=['object', 'string', 'category']):
        levels = sorted(a[n].astype(str).unique())
        aux['categories'][n] = levels
        for z in [a, b, c]:
            z[n] = z[n].astype(str).astype(pd.CategoricalDtype(levels))
    assert list(a) == list(b) == list(c) and 'id' not in a and ('Will_Buy_EV' not in a)
    assert np.array_equal(a.index, tr) and np.array_equal(b.index, va)
    return (a, b, c, aux)
