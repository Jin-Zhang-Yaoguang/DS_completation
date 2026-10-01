"""Reproduce the final five-model system; run from the repository root."""
import argparse
import gc
import hashlib
import io
import json
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits

from .f_features import NB_PARAMS, NB_NUM, prepare
from .old_features import CAT, TARGET, features, transform_fold

REPO = Path(__file__).resolve().parents[1]
SPEC = dict(id='F', fe=True, te=True, external=True, params='notebook')
MODELS = ('xgb', 'lgbm', 'catboost', 'F', 'constrained_F')


def config():
    return json.loads((REPO / 'configs/final.json').read_text())


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_data(data, seed):
    cfg = config()
    for name, digest in cfg['input_sha256'].items():
        if sha(data / name) != digest:
            raise ValueError(f'{name}: not the recorded competition data version')
    train, test = (pd.read_csv(data / name) for name in ('train.csv', 'test.csv'))
    y = train[TARGET].map({'No': 0, 'Yes': 1}).to_numpy()
    assert np.isfinite(y).all() and set(y) == {0, 1}
    folds = np.zeros(len(y), dtype=np.int8)
    for k, (_, valid) in enumerate(StratifiedKFold(5, shuffle=True, random_state=seed).split(train, y), 1):
        folds[valid] = k
    stream = io.BytesIO()
    np.save(stream, folds)
    assert hashlib.sha256(stream.getvalue()).hexdigest() == cfg['fold_sha256'][str(seed)]
    return train, test, y, folds


def origin(name):
    for n in sorted(CAT + NB_NUM, key=len, reverse=True):
        if name == n or name.startswith(n + '_'):
            return n
    if name.startswith('income') or name in ['commute_integer', 'is_30k_spike', 'is_millionaire_cliff', 'is_dead_zone', 'is_env_hater']:
        return 'Daily_Commute_km' if name.startswith('commute') else 'Environmental_Concern_Level' if name == 'is_env_hater' else 'Annual_Income_USD'
    if name.startswith('commute_integer'):
        return 'Daily_Commute_km'
    raise ValueError('Unmapped feature ' + name)


def make_model(name, fold, columns, old_specs):
    if name in ('F', 'constrained_F'):
        params = NB_PARAMS.copy()
        if name == 'constrained_F':
            origins = [origin(n) for n in columns]
            groups = [[i for i, o in enumerate(origins) if o == n] for n in CAT + NB_NUM]
            params.update(max_bin_by_feature=[1024] * len(columns), interaction_constraints=[g for g in groups if g])
        return lgb.LGBMClassifier(objective='binary', metric='auc', n_jobs=8, verbosity=-1, random_state=42, **params)
    spec = old_specs[name]
    if name == 'xgb':
        from xgboost import XGBClassifier
        return XGBClassifier(objective='binary:logistic', eval_metric='auc', enable_categorical=True,
                             tree_method='hist', n_jobs=spec['threads'], random_state=42 + fold - 1,
                             early_stopping_rounds=120, **spec['params'])
    if name == 'lgbm':
        return lgb.LGBMClassifier(objective='binary', metric='auc', n_jobs=8, verbosity=-1,
                                 random_state=42 + fold - 1, **spec['params'])
    from catboost import CatBoostClassifier
    return CatBoostClassifier(loss_function='Logloss', eval_metric='AUC', thread_count=8,
                              random_seed=42 + fold - 1, allow_writing_files=False, **spec['params'])


def train_model(args):
    train, test, y, folds = load_data(args.data_dir, args.seed)
    specs = {s['model']: s for s in json.loads((REPO / 'configs/old_models.json').read_text())}
    # Refuse to overwrite previous runs; use a fresh --output directory to rerun.
    dest = args.output / str(args.seed) / args.model
    dest.mkdir(parents=True, exist_ok=False)
    original = None
    if args.model in ('F', 'constrained_F'):
        path = args.data_dir / 'external/EV_Adoption_and_Range_Anxiety_Dataset.csv'
        assert sha(path) == config()['original_sha256'], 'Original dataset version mismatch'
        original = pd.read_csv(path)
        original[TARGET] = original[TARGET].map({'No': 0, 'Yes': 1})
    else:
        X = features(train, specs[args.model]['groups'])
        T = features(test, specs[args.model]['groups'])
    oof = np.full(len(y), np.nan)
    predicted_test = np.zeros(len(test))
    covered = np.zeros(len(y), dtype=np.int8)
    details = []
    for k in range(1, 6):
        start = time.perf_counter()
        tr, va = np.flatnonzero(folds != k), np.flatnonzero(folds == k)
        if args.model in ('F', 'constrained_F'):
            a, b, c, enc = prepare(train, test, y, tr, va, SPEC, k, original)
            cats = []
        else:
            a, b, c, cats, enc = transform_fold(X, T, y, tr, va, args.model, specs[args.model]['groups'], 42 + k - 1)
        model = make_model(args.model, k, list(a), specs)
        save_json(dest / f'config_{k}.json', dict(parameters=model.get_params(), features=list(a)))
        np.savez_compressed(dest / f'membership_{k}.npz', train_indices=tr, valid_indices=va)
        if args.model == 'xgb':
            model.fit(a, y[tr], eval_set=[(b, y[va])], verbose=500)
        elif args.model == 'catboost':
            model.fit(a, y[tr], cat_features=cats, eval_set=(b, y[va]), early_stopping_rounds=120, use_best_model=True, verbose=500)
        else:
            stop = 500 if args.model in ('F', 'constrained_F') else 120
            model.fit(a, y[tr], eval_set=[(b, y[va])], eval_metric='auc',
                      callbacks=[lgb.early_stopping(stop, first_metric_only=True, verbose=False), lgb.log_evaluation(1000)])
        with threadpool_limits(limits=8):
            pv, pt = model.predict_proba(b)[:, 1], model.predict_proba(c)[:, 1]
        oof[va] = pv
        predicted_test += pt / 5
        covered[va] += 1
        np.savez_compressed(dest / f'fold_{k}.npz', valid=pv, test=pt, valid_indices=va)
        joblib.dump(dict(model=model, encoders=enc, features=list(a)), dest / f'model_{k}.joblib', compress=3)
        details.append(dict(fold=k, auc=float(roc_auc_score(y[va], pv)), seconds=time.perf_counter() - start))
        print(args.model, details[-1], flush=True)
        del a, b, c, enc, model
        gc.collect()
    assert (covered == 1).all() and np.isfinite(oof).all() and np.isfinite(predicted_test).all()
    for name, values in [('oof', oof), ('test', predicted_test), ('folds', folds)]:
        np.save(dest / f'{name}.npy', values)
    save_json(dest / 'metrics.json', dict(oof_auc=float(roc_auc_score(y, oof)), folds=details, split_seed=args.seed))


def rank(values):
    return rankdata(values, method='average') / len(values)


def final_blend(predictions):
    old = np.mean([rank(predictions[n]) for n in ('xgb', 'lgbm', 'catboost')], axis=0)
    hybrid = .5 * rank(predictions['F']) + .5 * rank(predictions['constrained_F'])
    return (1 - .8) * rank(old) + .8 * rank(hybrid)


def blend(args):
    _, test, y, folds = load_data(args.data_dir, args.seed)
    dest = args.output / str(args.seed) / 'final'
    dest.mkdir(parents=True, exist_ok=False)
    outputs = {}
    for kind in ('oof', 'test'):
        predictions = {}
        for model in MODELS:
            folder = args.output / str(args.seed) / model
            assert np.array_equal(np.load(folder / 'folds.npy'), folds)
            values = np.load(folder / f'{kind}.npy')
            assert values.shape == (len(y) if kind == 'oof' else len(test),) and np.isfinite(values).all()
            predictions[model] = values
        outputs[kind] = final_blend(predictions)
        np.save(dest / f'{kind}.npy', outputs[kind])
    save_json(dest / 'metrics.json', dict(oof_auc=float(roc_auc_score(y, outputs['oof'])),
              fold_auc=[float(roc_auc_score(y[folds == k], outputs['oof'][folds == k])) for k in range(1, 6)]))
    sample = pd.read_csv(args.data_dir / 'sample_submission.csv')
    assert list(sample) == ['id', TARGET] and len(sample) == len(test) and np.array_equal(sample.id, test.id)
    assert np.isfinite(outputs['test']).all() and ((outputs['test'] >= 0) & (outputs['test'] <= 1)).all()
    sample[TARGET] = outputs['test']
    sample.to_csv(dest / 'submission_hybrid.csv', index=False)
    loaded = pd.read_csv(dest / 'submission_hybrid.csv', float_precision='round_trip')
    assert np.array_equal(loaded[TARGET], outputs['test']) and np.array_equal(loaded.id, test.id)
    save_json(dest / 'export_validation.json', dict(rows=len(sample), csv_roundtrip_exact=True,
              min=float(outputs['test'].min()), max=float(outputs['test'].max()), sha256=sha(dest / 'submission_hybrid.csv')))
    print('Saved local predictions and CSV. No Kaggle upload performed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('validate', 'train', 'blend'))
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('outputs'))
    parser.add_argument('--seed', type=int, choices=(42, 20260918), default=20260918)
    parser.add_argument('--model', choices=MODELS)
    args = parser.parse_args()
    if args.action == 'validate':
        _, _, y, _ = load_data(args.data_dir, args.seed)
        print('Data hashes and five-fold split verified:', len(y), 'training rows')
    elif args.action == 'train':
        if args.model is None:
            parser.error('train requires --model')
        train_model(args)
    else:
        blend(args)


if __name__ == '__main__':
    main()
