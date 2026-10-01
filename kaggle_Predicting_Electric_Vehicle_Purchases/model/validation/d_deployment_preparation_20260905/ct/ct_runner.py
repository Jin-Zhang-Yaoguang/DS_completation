"""PREPARATION_ONLY_NOT_AUTHORIZED. Library entry points; no real execution CLI.

A trusted future supervisor supplies immutable contract/auth SHA anchors and a live
lease. No fake backend can be passed to run_authorized(). No install/network/AUC.
"""
from __future__ import annotations
import contextlib
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parent
STATUS = 'PREPARATION_ONLY_NOT_AUTHORIZED'
FEATURE_SHA = '7cae5668f9c86938dc63635cfcfc7d4973059e48b754241cf8f88a5d220e2b14'
R01_CONFIG_SHA = '00a51bdb42fe1a88789059d45b7da5828f903474ddc4c611756d3ea88217afbc'
INPUT_SHA = {
    'train': 'eae9eaa4e6378df405e755f853771d7e26d212bd93258349fc797b771021946a',
    'test': '539263f6caabc40afd5e2f0bc0ab16b10a2d1177c565fc71b866f0181d836b34',
    'original': 'c271a380df51b18177d0a039d54525ca7c3d71500701dc7496714a091df16fae',
}
VERSIONS = {'numpy': '2.0.2', 'pandas': '2.3.3', 'scikit-learn': '1.6.1', 'ctboost': '0.1.58'}
WHEEL_SHA = {
    'cp310': 'c0a67a5e2d91d74c6f72566f79b3d4da4d8145c0a94b004c2603b0f41c94de79',
    'cp311': '3ee9a28777d1a3b7afdaadaeb7a46204164cdaffd8493bfcf9990a56bc815a61',
    'cp312': 'ff868712ac6b93f9038c646aedfe9fba0b9a9e7b95297ae0aa211157ee014a8b',
    'cp313': '36edbf6674a2cc6ce5fdf21caba40fa589e672712d20381dce88b70defd8faeb',
    'cp314': 'd334bba5296731800ff24f782c939e8631a0afecc585a95277987357e443136c',
}
PARAMS = dict(learning_rate=.039, max_depth=4, max_leaves=16, grow_policy='LeafWise',
              alpha=.5, lambda_l2=8., min_data_in_leaf=100, min_child_weight=.1,
              subsample=.85, bootstrap_type='Bernoulli', colsample_bytree=.3,
              feature_test='quadratic', feature_test_adjustment='none',
              feature_test_bins=8, max_bins=1024, leaf_estimation_iterations=3)
RECIPE = dict(folds=5, fold_seed=42, iterations=1426, model_seed=20260904,
              task_type='GPU', devices='0', eval_metric='AUC', verbose=False, params=PARAMS)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def atomic_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open('x') as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        return
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def array_sha(value):
    import numpy as np
    value = np.ascontiguousarray(value)
    return digest({'dtype': value.dtype.str, 'shape': list(value.shape),
                   'bytes': hashlib.sha256(value.tobytes()).hexdigest()})


def verify_ref(ref):
    need(set(ref) == {'path', 'sha256'}, 'invalid file reference')
    path = Path(ref['path']).resolve(strict=True)
    need(path.is_file() and sha(path) == ref['sha256'], 'file SHA mismatch: ' + str(path))
    return path


def authorize_contract(config_path, auth_path, expected_config_sha, expected_auth_sha):
    """Validate trusted parent anchors BEFORE importing numerical libraries or inputs.

    Caller obtains both expected SHAs out of band from the future supervisor; they
    must never be copied from the untrusted files being checked. No config emitted here.
    """
    return _authorize(config_path, auth_path, expected_config_sha, expected_auth_sha, verify_ref)


def _authorize(config_path, auth_path, expected_config_sha, expected_auth_sha, resolver):
    cfg_path = verify_ref({'path': str(config_path), 'sha256': expected_config_sha})
    auth_path = verify_ref({'path': str(auth_path), 'sha256': expected_auth_sha})
    cfg, auth = read(cfg_path), read(auth_path)
    need(cfg['status'] == 'FINAL_AUTHORIZED_CONTRACT' and cfg['schema_version'] == 1,
         'preparation is not a final contract')
    need(cfg['role'] == 'D_CT_GLOBAL_5FOLD' and cfg['recipe'] == RECIPE, 'recipe mismatch')
    need(type(cfg['cohort_id']) is str and len(cfg['cohort_id']) >= 16, 'missing cohort')
    need(auth['action'] == 'START_CT_GLOBAL5_D_ONCE' and auth['authorized_by'] == 'parent',
         'missing explicit parent START authorization')
    need(auth['config_sha256'] == expected_config_sha and auth['cohort_id'] == cfg['cohort_id'],
         'authorization not bound to this cohort/config')
    need(auth['preparation_only'] is False, 'synthetic authorization forbidden')
    for name in ('seconds', 'memory_bytes', 'threads'):
        need(type(cfg['budget'][name]) is int and cfg['budget'][name] > 0, 'invalid budget')
    need(cfg['budget']['seconds'] <= 7200 and cfg['budget']['memory_bytes'] <= 24 * 2**30
         and cfg['budget']['threads'] <= 4, 'budget exceeds verified R01 envelope')
    need(cfg['replay'] == {'rtol': 1e-7, 'atol': 1e-8, 'scope': 'ALL_H_AND_TEST'},
         'replay contract must match historical save/load check, expanded to all queries')
    need(set(cfg['inputs']) == set(INPUT_SHA), 'missing/extra input')
    for key, expected in INPUT_SHA.items():
        need(cfg['inputs'][key]['sha256'] == expected, 'not official input: ' + key)
    need(cfg['source_recipe']['sha256'] == R01_CONFIG_SHA, 'wrong CT R01 source')
    recipe = read(resolver(cfg['source_recipe']))
    need(recipe['params'] == PARAMS and recipe['inner_seed'] == 42
         and recipe['model_seed'] == 20260904 and recipe['iterations'] == 1426,
         'source recipe drift')
    expected_sources = {'ct_runner.py', 'ct_features.py', 'resource_guard.py'}
    need(set(cfg['worker_sources']) == expected_sources, 'incomplete worker source binding')
    for name in expected_sources:
        need(sha(ROOT / name) == cfg['worker_sources'][name], 'worker source drift')
    need(cfg['worker_sources']['ct_features.py'] == FEATURE_SHA, 'feature function drift')
    for ref in cfg['source_files'].values():
        resolver(ref)
    receipt_path = resolver(cfg['qualification_receipt'])
    receipt = read(receipt_path)
    need(receipt['status'] == 'VERIFIED_D_REBUILD_ELIGIBLE'
         and receipt['candidate_rebuild_eligible'] is True
         and receipt['selected_candidate'] == receipt['candidate'] == 'D'
         and receipt['baseline'] == 'C' and receipt['execution_authorized'] is False
         and receipt['allowed_for_submission'] is False, 'qualification receipt mismatch')
    need(bool(receipt['bound_sources']) and bool(receipt['terminal_artifacts'])
         and bool(receipt['readiness_gate_sha256']) and bool(receipt['checked_at_utc']),
         'qualification receipt incomplete')
    need(auth['qualification_receipt_sha256'] == cfg['qualification_receipt']['sha256'],
         'authorization receipt mismatch')
    need(cfg['runtime_versions'] == VERSIONS, 'runtime recipe drift')
    need(cfg['installation_wheel']['sha256'] in WHEEL_SHA.values(), 'not an audited CT wheel')
    remote = cfg['remote_execution']
    need(remote['provider'] == 'kaggle' and type(remote['kernel_ref']) is str
         and '/' in remote['kernel_ref'] and type(remote['kernel_version']) is int
         and remote['kernel_version'] >= 1, 'remote execution identity')
    need(Path(cfg['output_dir']).is_absolute(), 'output must be an absolute new directory')
    return {'config': cfg, 'config_sha256': expected_config_sha,
            'start_authorization_sha256': expected_auth_sha,
            'config_path': str(cfg_path), 'authorization_path': str(auth_path),
            'mode': 'LIVE_AUTHORIZED', 'artifact_root': cfg['output_dir']}


def _verify_archive_map(cfg, archive, config_sha, auth_sha):
    need(archive['status'] == 'VERIFIED_CT_DEPLOYMENT_ARCHIVE' and archive['schema_version'] == 1,
         'archive is not verified')
    need(archive['config_sha256'] == config_sha and archive['start_authorization_sha256'] == auth_sha
         and archive['cohort_id'] == cfg['cohort_id'] and archive['remote_output_dir'] == cfg['output_dir'],
         'archive original identity mismatch')
    execution = archive['remote_execution']
    need({k: execution[k] for k in ('provider', 'kernel_ref', 'kernel_version')} == cfg['remote_execution']
         and execution['status'] == 'COMPLETE'
         and execution['download_version_before'] == execution['download_version_after'] == execution['kernel_version'],
         'archive remote version mismatch')
    root = Path(archive['artifact_root']).resolve(strict=True)
    need(root.is_dir() and not Path(archive['artifact_root']).is_symlink(), 'archive root invalid')
    refs = [cfg['source_recipe'], cfg['qualification_receipt'], cfg['installation_wheel'],
            *cfg['source_files'].values(), *cfg['inputs'].values()]
    expected = {}
    for ref in refs:
        need(ref['path'] not in expected or expected[ref['path']] == ref['sha256'], 'conflicting original refs')
        expected[ref['path']] = ref['sha256']
    need(set(archive['path_map']) == set(expected), 'archive path-map whitelist mismatch')
    for original_path, local_ref in archive['path_map'].items():
        need(local_ref['sha256'] == expected[original_path], 'archive mapped source SHA differs')
        verify_ref(local_ref)
    actual_files = {}
    for path in root.rglob('*'):
        need(not path.is_symlink(), 'archive symlink forbidden')
        if path.is_file():
            actual_files[str(path.relative_to(root))] = sha(path)
    need(bool(actual_files) and actual_files == archive['files'], 'archive file tree mismatch')
    return root


def authorize_archived(config_path, auth_path, expected_config_sha, expected_auth_sha,
                       archive_map_path, expected_archive_map_sha):
    """Strictly read-only cross-host adapter; preserves original config/auth bytes.

    The independently verified archive map is another trusted parent SHA anchor,
    not a directory discovered or a map created by this function.
    """
    verify_ref({'path': str(config_path), 'sha256': expected_config_sha})
    verify_ref({'path': str(auth_path), 'sha256': expected_auth_sha})
    archive_path = verify_ref({'path': str(archive_map_path), 'sha256': expected_archive_map_sha})
    cfg, archive = read(config_path), read(archive_path)
    root = _verify_archive_map(cfg, archive, expected_config_sha, expected_auth_sha)
    def resolver(ref):
        mapped = archive['path_map'][ref['path']]
        need(mapped['sha256'] == ref['sha256'], 'archive source digest mismatch')
        return verify_ref(mapped)
    context = _authorize(config_path, auth_path, expected_config_sha, expected_auth_sha, resolver)
    context.update(mode='ARCHIVE_READ_ONLY', artifact_root=str(root), local_path_map=archive['path_map'],
                   archive_map_path=str(archive_path), archive_map_sha256=expected_archive_map_sha)
    return context


def _context_ref(context, ref):
    if context.get('mode') == 'ARCHIVE_READ_ONLY':
        mapped = context['local_path_map'][ref['path']]
        need(mapped['sha256'] == ref['sha256'], 'mapped input SHA mismatch')
        return verify_ref(mapped)
    return verify_ref(ref)


def _features():
    # Import exact frozen bytes even when a caller loaded ct_runner with importlib.
    path = ROOT / 'ct_features.py'
    need(sha(path) == FEATURE_SHA, 'feature code drift')
    name = '_d_ct_features_' + FEATURE_SHA
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return sys.modules[name]


def context_identity(context):
    cfg = context['config']
    return {'cohort_id': cfg['cohort_id'], 'config_sha256': context['config_sha256'],
            'start_authorization_sha256': context['start_authorization_sha256'],
            'input_sha256': {k: v['sha256'] for k, v in cfg['inputs'].items()},
            'recipe_sha256': digest(RECIPE), 'feature_source_sha256': FEATURE_SHA,
            'qualification_receipt_sha256': cfg['qualification_receipt']['sha256']}


def probability(value, rows, dtype):
    import numpy as np
    need(value.shape == (rows,) and value.dtype == np.dtype(dtype), 'probability shape/dtype')
    need(np.isfinite(value).all() and ((value >= 0) & (value <= 1)).all(), 'invalid probability')
    return value


def load_inputs(context):
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import StratifiedKFold
    binary_target = _features().binary_target
    paths = {key: verify_ref(ref) for key, ref in context['config']['inputs'].items()}
    frame, test, original = [pd.read_csv(paths[key]) for key in ('train', 'test', 'original')]
    need(len(frame) == 668665 and len(test) == 286571, 'official row count mismatch')
    need('Will_Buy_EV' not in test, 'test must not contain a target')
    y = binary_target(frame.pop('Will_Buy_EV'))
    for part in (frame, test):
        need(part.id.dtype == np.dtype('int64') and part.id.is_unique, 'official ID dtype/uniqueness')
    need(not np.intersect1d(frame.id, test.id).size, 'train/test ID overlap')
    folds = np.full(len(y), -1, dtype=np.int8)
    for fold, (_, hold) in enumerate(StratifiedKFold(5, shuffle=True, random_state=42).split(frame, y)):
        folds[hold] = fold
    return frame, y, test, original, folds


def runtime_evidence(context, output):
    """No installation. Archive supplied wheel and hash actual installed package files."""
    import ctboost
    cfg = context['config']
    versions = {name: importlib.metadata.version(name) for name in VERSIONS}
    need(versions == VERSIONS, 'installed runtime differs from recipe')
    loaded_modules = {}
    for distribution_name, module_name in [('numpy', 'numpy'), ('pandas', 'pandas'),
                                           ('scikit-learn', 'sklearn'), ('ctboost', 'ctboost')]:
        module = importlib.import_module(module_name)
        location = Path(module.__file__).resolve()
        need(module.__version__ == VERSIONS[distribution_name], 'loaded module version mismatch')
        expected = Path(importlib.metadata.distribution(distribution_name).locate_file(module_name + '/__init__.py')).resolve()
        need(location == expected, 'loaded module shadows distribution: ' + module_name)
        loaded_modules[module_name] = {'version': module.__version__, 'path': str(location), 'sha256': sha(location)}
    build = ctboost.build_info()
    need(build['cuda_enabled'] and build['version'] == build['package_version'] == '0.1.58',
         'not CTBoost 0.1.58 CUDA build')
    wheel = verify_ref(cfg['installation_wheel'])
    tag = f'cp{sys.version_info.major}{sys.version_info.minor}'
    need(sys.platform.startswith('linux') and WHEEL_SHA.get(tag) == sha(wheel), 'wheel/Python ABI mismatch')
    distribution = importlib.metadata.distribution('ctboost')
    # Prove actual installed package bytes match supplied wheel, not just its version.
    wheel_members = {}
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith(('ctboost/', 'ctboost.libs/')) and not name.endswith('/'):
                path = Path(distribution.locate_file(name)).resolve(strict=True)
                expected = hashlib.sha256(archive.read(name)).hexdigest()
                need(sha(path) == expected, 'installed package/wheel mismatch: ' + name)
                wheel_members[name] = {'path': str(path), 'sha256': expected}
    need(any(name.endswith('.so') for name in wheel_members), 'wheel has no recorded native library')
    need(Path(ctboost.__file__).resolve() == Path(distribution.locate_file('ctboost/__init__.py')).resolve(),
         'loaded CT module shadows installed distribution')
    files = {}
    for name in (*VERSIONS, 'scipy', 'joblib', 'threadpoolctl', 'psutil'):
        dist = importlib.metadata.distribution(name)
        files[name] = {str(f): sha(dist.locate_file(f)) for f in (dist.files or [])
                       if str(f).endswith(('.py', '.so', '.pyd', '.dylib')) and Path(dist.locate_file(f)).is_file()}
        need(bool(files[name]), 'no installed byte evidence: ' + name)
    gpu = subprocess.run(['nvidia-smi', '-q'], check=True, capture_output=True, text=True, timeout=30).stdout
    need('Product Name' in gpu and 'Driver Version' in gpu and 'CUDA Version' in gpu, 'GPU metadata incomplete')
    location = Path(output) / 'runtime'
    location.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(wheel, location / wheel.name)
    need(sha(location / wheel.name) == cfg['installation_wheel']['sha256'], 'archived wheel drift')
    result = {'status': 'ACTUAL_RUNTIME_CAPTURED', 'python': sys.version, 'platform': platform.platform(),
              'executable': sys.executable, 'executable_sha256': sha(sys.executable), 'versions': versions,
              'build_info': build, 'gpu_nvidia_smi': gpu, 'installed_file_sha256': files,
              'loaded_modules': loaded_modules,
              'installed_ct_wheel_members': wheel_members, 'wheel_file': 'runtime/' + wheel.name,
              'wheel_sha256': sha(wheel), 'threads': cfg['budget']['threads']}
    atomic_json(location / 'manifest.json', result, exclusive=True)
    return result


class GPUBackend:
    def fit(self, frame, y, original):
        import ctboost
        features, state = _features().fit_features(frame, y, original, seed=20260904)
        need(all(str(dtype) == 'float32' for dtype in features.dtypes), 'CT feature precision')
        model = ctboost.CTBoostClassifier(iterations=1426, task_type='GPU', devices='0',
                    random_seed=20260904, eval_metric='AUC', verbose=False, **PARAMS).fit(features, y)
        need(model.get_booster()._handle.export_state()['task_type'] == 'GPU', 'actual fit was not GPU')
        return model, state

    def predict(self, model, state, frame):
        import numpy as np
        return np.asarray(model.predict_proba(_features().transform_features(frame, state))[:, 1], dtype=np.float64)

    def save(self, model, state, directory):
        import joblib
        model.save_model(str(directory / 'model.json'))
        joblib.dump(state, directory / 'feature_state.joblib', compress=3)

    def load(self, directory):
        import ctboost
        import joblib
        return ctboost.CTBoostClassifier.load_model(str(directory / 'model.json')), joblib.load(directory / 'feature_state.joblib')


def _load_npz(path):
    import numpy as np
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def _verify_fold(directory, fold, ids, test_ids, folds, identity):
    import numpy as np
    expected_files = {'model.json', 'feature_state.joblib', 'predictions.npz', 'manifest.json'}
    need(directory.is_dir() and {p.name for p in directory.iterdir()} == expected_files, 'incomplete/extra fold files')
    record = read(directory / 'manifest.json')
    need(record['status'] == 'CT_GLOBAL_FOLD_COMPLETE_UNSCORED' and record['fold'] == fold
         and record['identity'] == identity, 'fold identity mismatch')
    need(set(record['file_sha256']) == expected_files - {'manifest.json'}, 'fold source set mismatch')
    for name, expected in record['file_sha256'].items():
        need(sha(directory / name) == expected, 'fold bytes drift')
    z = _load_npz(directory / 'predictions.npz')
    need(set(z) == {'fit_idx', 'hold_idx', 'fit_id', 'hold_id', 'test_id', 'oof_proba', 'test_proba'}, 'fold array keys')
    fit, hold = np.flatnonzero(folds != fold - 1), np.flatnonzero(folds == fold - 1)
    for key, expected in [('fit_idx', fit), ('hold_idx', hold), ('fit_id', ids[fit]),
                           ('hold_id', ids[hold]), ('test_id', test_ids)]:
        need(z[key].dtype == np.dtype('int64') and np.array_equal(z[key], expected), 'fold index/ID mismatch: ' + key)
    probability(z['oof_proba'], len(hold), 'float64')
    probability(z['test_proba'], len(test_ids), 'float64')
    need(record['feature_names'] and len(record['feature_names']) == len(set(record['feature_names'])), 'feature schema')
    need(record['feature_names_sha256'] == digest(record['feature_names']), 'feature schema SHA')
    need(record['hold_labels_used_in_fit'] is False and record['test_labels_available'] is False
         and record['allowed_for_submission'] is False, 'fold scope mismatch')
    replay = record['replay']
    need(replay['scope'] == 'ALL_H_AND_TEST' and replay['hold_rows'] == len(hold)
         and replay['test_rows'] == len(test_ids) and replay['passed'] is True, 'incomplete replay')
    need(all(type(replay[k]) in (int, float) and math.isfinite(replay[k]) and 0 <= replay[k] <= 1.1e-7
             for k in ('hold_max_abs', 'test_max_abs')), 'invalid replay error')
    return z, record


def _fit_five(x, y, test, original, folds, output, identity, backend, progress=lambda _: None):
    """Internal engine. Production selects GPUBackend; synthetic entry supplies generated frames only."""
    import numpy as np
    need('Will_Buy_EV' not in x and 'Will_Buy_EV' not in test, 'query/feature target forbidden')
    ids, test_ids = x.id.to_numpy(dtype=np.int64), test.id.to_numpy(dtype=np.int64)
    need(folds.shape == y.shape == (len(x),) and folds.dtype == np.dtype('int8')
         and set(np.unique(folds)) == set(range(5)), 'fold contract')
    need(len(np.unique(ids)) == len(ids) and len(np.unique(test_ids)) == len(test_ids)
         and not np.intersect1d(ids, test_ids).size, 'ID overlap/duplicate')
    output = Path(output)
    base = output / 'folds'
    base.mkdir(parents=True, exist_ok=True)
    need(all(p.name in {f'fold_{f:02d}' for f in range(1, 6)} for p in base.iterdir()), 'partial/unknown checkpoint')
    # Validate every existing checkpoint before any new fit, even noncontiguous ones.
    for fold in range(1, 6):
        directory = base / f'fold_{fold:02d}'
        if directory.exists():
            _verify_fold(directory, fold, ids, test_ids, folds, identity)
    for fold in range(1, 6):
        directory = base / f'fold_{fold:02d}'
        if directory.exists():
            continue
        temporary = base / f'fold_{fold:02d}.partial'
        temporary.mkdir()
        fit, hold = np.flatnonzero(folds != fold - 1), np.flatnonzero(folds == fold - 1)
        progress({'stage': 'BEFORE_FIT', 'fold': fold})
        model, state = backend.fit(x.iloc[fit], y[fit], original)
        a = probability(backend.predict(model, state, x.iloc[hold]), len(hold), 'float64')
        b = probability(backend.predict(model, state, test), len(test), 'float64')
        backend.save(model, state, temporary)
        feature_names = list(state['feature_names'])
        del model, state
        gc.collect()
        loaded_model, loaded_state = backend.load(temporary)
        ra = probability(backend.predict(loaded_model, loaded_state, x.iloc[hold]), len(hold), 'float64')
        rb = probability(backend.predict(loaded_model, loaded_state, test), len(test), 'float64')
        need(np.allclose(ra, a, rtol=1e-7, atol=1e-8) and np.allclose(rb, b, rtol=1e-7, atol=1e-8), 'saved model/state replay failed')
        np.savez_compressed(temporary / 'predictions.npz', fit_idx=fit, hold_idx=hold, fit_id=ids[fit],
                            hold_id=ids[hold], test_id=test_ids, oof_proba=a, test_proba=b)
        record = {'status': 'CT_GLOBAL_FOLD_COMPLETE_UNSCORED', 'fold': fold, 'identity': identity,
                  'file_sha256': {name: sha(temporary / name) for name in ('model.json', 'feature_state.joblib', 'predictions.npz')},
                  'feature_names': feature_names, 'feature_names_sha256': digest(feature_names),
                  'replay': {'scope': 'ALL_H_AND_TEST', 'hold_rows': len(hold), 'test_rows': len(test),
                             'hold_max_abs': float(np.max(np.abs(ra-a))), 'test_max_abs': float(np.max(np.abs(rb-b))), 'passed': True},
                  'hold_labels_used_in_fit': False, 'test_labels_available': False,
                  'allowed_for_submission': False}
        atomic_json(temporary / 'manifest.json', record, exclusive=True)
        os.rename(temporary, directory)
        _verify_fold(directory, fold, ids, test_ids, folds, identity)
        progress({'stage': 'FOLD_COMPLETE', 'fold': fold})
        del loaded_model, loaded_state, a, b, ra, rb
        gc.collect()
    oof = np.full(len(x), np.nan, dtype=np.float32)
    mean = np.zeros(len(test), dtype=np.float64)
    manifests = {}
    for fold in range(1, 6):
        directory = base / f'fold_{fold:02d}'
        z, _ = _verify_fold(directory, fold, ids, test_ids, folds, identity)
        oof[z['hold_idx']] = z['oof_proba']
        mean += z['test_proba'] / 5
        manifests[f'fold_{fold:02d}'] = sha(directory / 'manifest.json')
    probability(oof, len(x), 'float32')
    probability(mean, len(test), 'float64')
    temporary = output / 'cache.npz.tmp'
    with temporary.open('xb') as handle:
        np.savez_compressed(handle, train_id=ids, test_id=test_ids, oof_proba=oof,
                            test_proba_foldmean=mean, atom_fold=folds)
        handle.flush()
        os.fsync(handle.fileno())
    need(not (output / 'cache.npz').exists(), 'cache already exists')
    os.rename(temporary, output / 'cache.npz')
    summary = {'status': 'CT_GLOBAL5_CACHE_COMPLETE_UNSCORED', 'identity': identity,
               'cache_sha256': sha(output / 'cache.npz'), 'fold_manifest_sha256': manifests,
               'array_sha256': {k: array_sha(v) for k, v in _load_npz(output / 'cache.npz').items()},
               'aggregation': 'float64 zeros; fold01..05 mean += fold_test / 5',
               'allowed_for_submission': False, 'deployment_verified': False}
    atomic_json(output / 'cache_manifest.json', summary, exclusive=True)
    return summary


def check_cache(output, context):
    """Read-only full 5-fold artifact and exact OOF/test reconstruction. No target reads."""
    import numpy as np
    import pandas as pd
    output = Path(output).resolve()
    need(output == Path(context['artifact_root']).resolve(), 'wrong cohort output path')
    cfg = context['config']
    ids = pd.read_csv(_context_ref(context, cfg['inputs']['train']), usecols=['id']).id.to_numpy()
    test_ids = pd.read_csv(_context_ref(context, cfg['inputs']['test']), usecols=['id']).id.to_numpy()
    need(len(ids) == 668665 and len(test_ids) == 286571, 'official rows')
    identity = context_identity(context)
    runtime_path = output / 'runtime/manifest.json'
    runtime = read(runtime_path)
    need(runtime['status'] == 'ACTUAL_RUNTIME_CAPTURED' and runtime['versions'] == VERSIONS,
         'runtime evidence invalid')
    need(runtime['wheel_sha256'] == cfg['installation_wheel']['sha256']
         and sha(output / runtime['wheel_file']) == runtime['wheel_sha256'], 'runtime wheel drift')
    identity['runtime_manifest_sha256'] = sha(runtime_path)
    identity['split_sha256'] = sha(output / 'splits.npz')
    result = _check_cache_arrays(output, ids, test_ids, identity)
    result['files'].update({name: sha(output / name) for name in ('runtime/manifest.json', runtime['wheel_file'])})
    return result


def _check_cache_arrays(output, ids, test_ids, identity):
    import numpy as np
    output = Path(output)
    record = read(output / 'cache_manifest.json')
    need(record['status'] == 'CT_GLOBAL5_CACHE_COMPLETE_UNSCORED' and record['identity'] == identity,
         'cache source identity')
    need(record['cache_sha256'] == sha(output / 'cache.npz'), 'cache SHA')
    need(record['aggregation'] == 'float64 zeros; fold01..05 mean += fold_test / 5', 'wrong aggregation')
    z = _load_npz(output / 'cache.npz')
    need(set(z) == {'train_id', 'test_id', 'oof_proba', 'test_proba_foldmean', 'atom_fold'}, 'cache keys')
    need(z['train_id'].dtype == z['test_id'].dtype == np.dtype('int64')
         and np.array_equal(z['train_id'], ids) and np.array_equal(z['test_id'], test_ids), 'cache official IDs')
    folds = z['atom_fold']
    need(folds.shape == (len(ids),) and folds.dtype == np.dtype('int8')
         and set(np.unique(folds)) == set(range(5)), 'cache fold identity')
    # Frozen split was saved by worker before any fit; hash is bound in each fold identity.
    split = _load_npz(output / 'splits.npz')
    need(set(split) == {'train_id', 'test_id', 'atom_fold'} and all(np.array_equal(split[k], z[k])
         for k in split) and record['identity']['split_sha256'] == sha(output / 'splits.npz'), 'frozen split mismatch')
    probability(z['oof_proba'], len(ids), 'float32')
    probability(z['test_proba_foldmean'], len(test_ids), 'float64')
    need(record['array_sha256'] == {k: array_sha(v) for k, v in z.items()}, 'cache array hashes')
    expected_names = {f'fold_{fold:02d}' for fold in range(1, 6)}
    need(set(record['fold_manifest_sha256']) == expected_names
         and {p.name for p in (output / 'folds').iterdir()} == expected_names, 'not exactly five folds')
    oof, mean = np.full(len(ids), np.nan, dtype=np.float32), np.zeros(len(test_ids), dtype=np.float64)
    files = {str(name): sha(output / name) for name in ('cache.npz', 'cache_manifest.json', 'splits.npz')}
    for fold in range(1, 6):
        folder = output / 'folds' / f'fold_{fold:02d}'
        need(sha(folder / 'manifest.json') == record['fold_manifest_sha256'][folder.name], 'fold manifest SHA')
        part, _ = _verify_fold(folder, fold, ids, test_ids, folds, identity)
        oof[part['hold_idx']] = part['oof_proba']
        mean += part['test_proba'] / 5
        files.update({str(p.relative_to(output)): sha(p) for p in folder.iterdir()})
    need(np.array_equal(oof, z['oof_proba']) and np.array_equal(mean, z['test_proba_foldmean']),
         'same-cohort reconstruction mismatch')
    return {'status': 'CT_GLOBAL5_CACHE_REBUILT_UNSCORED', 'arrays': z, 'files': files,
            'identity': identity, 'allowed_for_submission': False}


def require_successful_completion(output, context):
    """Require final parent supervisor receipt BEFORE loading real prediction arrays."""
    output = Path(output).resolve()
    need(output == Path(context['artifact_root']).resolve(), 'wrong output')
    report = read(output / 'SUPERVISOR_RESULT.json')
    cfg = context['config']
    need(report['status'] == 'CT_DEPLOYMENT_SUPERVISOR_COMPLETE' and report['exit_code'] == 0,
         'parent supervision not complete')
    need(report['config_sha256'] == context['config_sha256']
         and report['start_authorization_sha256'] == context['start_authorization_sha256'], 'supervisor identity')
    for name, limit in [('seconds', cfg['budget']['seconds']), ('peak_process_tree_rss_bytes', cfg['budget']['memory_bytes'])]:
        need(type(report[name]) in (int, float) and math.isfinite(report[name])
             and 0 <= report[name] <= limit, 'parent final budget violation')
    need(report['phase'] == 'AFTER_EXIT_AND_CLEANUP' and report['completed_folds'] == 5,
         'incomplete parent lifecycle')
    required = {'WORKER_COMPLETE.json', 'RUN_STARTED.json', 'cache_manifest.json', 'runtime/manifest.json',
                'guard_report.json', 'worker.log'}
    need(set(report['file_sha256']) == required, 'supervisor missing source bindings')
    for name, expected in report['file_sha256'].items():
        need(sha(output / name) == expected, 'supervisor bound file drift')
    worker = read(output / 'WORKER_COMPLETE.json')
    need(worker['status'] == 'CT_GLOBAL5_WORKER_COMPLETE_UNSCORED'
         and worker['config_sha256'] == context['config_sha256'] and worker['completed_folds'] == 5
         and worker['start_authorization_sha256'] == context['start_authorization_sha256']
         and worker['cohort_id'] == cfg['cohort_id']
         and worker['cache_manifest_sha256'] == sha(output / 'cache_manifest.json'), 'worker completion mismatch')
    started = read(output / 'RUN_STARTED.json')
    need(started['status'] == 'CT_GLOBAL5_RUN_STARTED' and started['cohort_id'] == cfg['cohort_id']
         and started['config_sha256'] == context['config_sha256']
         and started['start_authorization_sha256'] == context['start_authorization_sha256'], 'STARTED identity')
    expected_instance = {'worker_pid': started['pid'], 'worker_created': started['worker_created'],
                         'parent_pid': started['lease']['parent_pid'],
                         'parent_created': started['lease']['parent_created']}
    need(report['instance'] == worker['instance'] == expected_instance, 'worker/supervisor instance mismatch')
    watched = read(output / 'guard_report.json')
    need(watched['status'] in {'MONITORING', 'WORKER_EXITED'} and watched['instance'] == expected_instance,
         'guard failed or wrong instance')
    need(type(watched['seconds']) in (int, float) and math.isfinite(watched['seconds'])
         and 0 <= watched['seconds'] <= report['seconds']
         and type(watched['peak_bytes']) is int
         and 0 <= watched['peak_bytes'] <= report['peak_process_tree_rss_bytes'], 'guard/final budget mismatch')
    result = check_cache(output, context)
    result['files'].update({name: sha(output / name) for name in required | {'SUPERVISOR_RESULT.json'}})
    result['status'] = 'CT_GLOBAL5_SUPERVISED_COMPLETE_UNSCORED'
    return result


@contextlib.contextmanager
def guard(context, output, lease):
    import psutil
    need(os.getpid() == os.getpgrp() and os.getppid() == lease['parent_pid'], 'worker must own child process group')
    need(psutil.Process(lease['parent_pid']).create_time() == lease['parent_created'], 'parent identity')
    need(lease['config_sha256'] == context['config_sha256']
         and lease['start_authorization_sha256'] == context['start_authorization_sha256'], 'lease identity')
    need(type(lease['prior_seconds']) in (float, int) and math.isfinite(lease['prior_seconds'])
         and 0 <= lease['prior_seconds'] < context['config']['budget']['seconds'], 'lease elapsed')
    need(type(lease['prior_peak_bytes']) is int and 0 <= lease['prior_peak_bytes']
         <= context['config']['budget']['memory_bytes'], 'lease peak memory')
    spec = {**context['config']['budget'], 'parent_pid': lease['parent_pid'],
            'parent_created': lease['parent_created'], 'worker_pid': os.getpid(),
            'worker_created': psutil.Process().create_time(), 'prior_seconds': lease['prior_seconds'],
            'prior_peak_bytes': lease['prior_peak_bytes'], 'report': str(output / 'guard_report.json'),
            'ready': str(output / 'guard_ready.json')}
    watcher = subprocess.Popen([sys.executable, str(ROOT / 'resource_guard.py'), json.dumps(spec)], start_new_session=True)
    try:
        until = time.monotonic() + 10
        while not (output / 'guard_ready.json').exists():
            need(watcher.poll() is None and time.monotonic() < until, 'resource guard failed to start')
            time.sleep(.02)
        ready = read(output / 'guard_ready.json')
        need(watcher.poll() is None and ready == {'status': 'GUARD_READY', 'worker_pid': os.getpid(),
             'worker_created': spec['worker_created'], 'parent_pid': lease['parent_pid'],
             'parent_created': lease['parent_created'], 'guard_pid': watcher.pid}, 'guard handshake identity')
        yield
    finally:
        watcher.terminate()
        try:
            watcher.wait(timeout=10)
        except subprocess.TimeoutExpired:
            watcher.kill()
            watcher.wait(timeout=10)


def run_authorized(config_path, auth_path, expected_config_sha, expected_auth_sha, lease):
    """Future parent-only production API. No fake backend parameter; no real CLI.

    Parent must start this call in a new process group, monitor the entire lifetime,
    capture worker.log, and finalize SUPERVISOR_RESULT only after exit and cleanup.
    Missing authorization fails before input labels, numerical imports, or training.
    """
    context = authorize_contract(config_path, auth_path, expected_config_sha, expected_auth_sha)
    import psutil
    cfg = context['config']
    output = Path(cfg['output_dir']).resolve()
    output.mkdir(parents=True, exist_ok=True)
    need(not any(output.iterdir()), 'real run requires a new empty output; no automatic resume')
    atomic_json(output / 'RUN_STARTED.json', {'status': 'CT_GLOBAL5_RUN_STARTED',
                'config_sha256': expected_config_sha, 'start_authorization_sha256': expected_auth_sha,
                'cohort_id': cfg['cohort_id'], 'pid': os.getpid(),
                'worker_created': psutil.Process().create_time(), 'lease': lease}, exclusive=True)
    # One-shot only: failed or killed calls retain STARTED and cannot silently resume.
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
        os.environ[key] = str(cfg['budget']['threads'])
    with guard(context, output, lease):
        from threadpoolctl import threadpool_limits
        with threadpool_limits(cfg['budget']['threads']):
            runtime_evidence(context, output)
            x, y, test, original, folds = load_inputs(context)
            import numpy as np
            np.savez_compressed(output / 'splits.npz', train_id=x.id.to_numpy(), test_id=test.id.to_numpy(), atom_fold=folds)
            identity = context_identity(context)
            identity.update(runtime_manifest_sha256=sha(output / 'runtime/manifest.json'), split_sha256=sha(output / 'splits.npz'))
            _fit_five(x, y, test, original, folds, output, identity, GPUBackend(),
                      progress=lambda record: print(json.dumps(record), flush=True))
            # Revalidate immutable byte anchors after all fits, no additional labels.
            authorize_contract(config_path, auth_path, expected_config_sha, expected_auth_sha)
            check_cache(output, context)
            atomic_json(output / 'WORKER_COMPLETE.json', {'status': 'CT_GLOBAL5_WORKER_COMPLETE_UNSCORED',
                        'config_sha256': expected_config_sha, 'completed_folds': 5,
                        'start_authorization_sha256': expected_auth_sha, 'cohort_id': cfg['cohort_id'],
                        'instance': {'worker_pid': os.getpid(), 'worker_created': psutil.Process().create_time(),
                                     'parent_pid': lease['parent_pid'], 'parent_created': lease['parent_created']},
                        'cache_manifest_sha256': sha(output / 'cache_manifest.json'),
                        'allowed_for_submission': False, 'deployment_verified': False}, exclusive=True)
    return {'status': 'CT_GLOBAL5_WORKER_COMPLETE_UNSCORED', 'awaiting_parent_supervisor': True}


if __name__ == '__main__':
    raise SystemExit('PREPARATION_ONLY_NOT_AUTHORIZED: no real execution CLI; parent contract required')
