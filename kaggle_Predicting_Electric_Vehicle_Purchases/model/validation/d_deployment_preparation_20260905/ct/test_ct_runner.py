"""Only generated tiny fixtures; production paths/targets and CT training forbidden."""
import copy
import gc
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import subprocess
import signal
import unittest
from unittest.mock import patch

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[key] = '2'
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
import ct_runner as ct

HERE = Path(__file__).resolve().parent
SYNTHETIC = HERE / '.synthetic_tests'


class FakeBackend:
    """No real model; records exact F labels and returns a simple bounded function."""
    def __init__(self, bad_replay=False, bad_probability=False):
        self.calls = []
        self.bad_replay = bad_replay
        self.bad_probability = bad_probability

    def fit(self, x, y, original):
        self.calls.append((x.id.to_numpy().copy(), y.copy()))
        return {'mean': float(y.mean()), 'loaded': False}, {'feature_names': ['signal'], 'offset': 0.01}

    def predict(self, model, state, frame):
        pred = np.full(len(frame), model['mean'], dtype=np.float64) + np.asarray(frame.signal) / 100
        if self.bad_replay and model['loaded']:
            pred += 1e-3
        if self.bad_probability:
            pred[:] = np.nan
        return pred.astype(np.float64)

    def save(self, model, state, directory):
        ct.atomic_json(directory / 'model.json', model, exclusive=True)
        ct.atomic_json(directory / 'feature_state.joblib', state, exclusive=True)

    def load(self, directory):
        model = ct.read(directory / 'model.json')
        model['loaded'] = True
        return model, ct.read(directory / 'feature_state.joblib')


def fixture(output):
    # No caller-supplied inputs or files. Negative synthetic IDs never official IDs.
    x = pd.DataFrame({'id': np.arange(-1000, -900, dtype=np.int64),
                      'signal': np.arange(100, dtype=np.float64) % 11})
    y = np.arange(100, dtype=np.int8) % 2
    test = pd.DataFrame({'id': np.arange(-2000, -1980, dtype=np.int64), 'signal': np.arange(20) % 7})
    original = pd.DataFrame({'synthetic': [True]})
    folds = np.full(len(y), -1, dtype=np.int8)
    for f, (_, h) in enumerate(StratifiedKFold(5, shuffle=True, random_state=42).split(x, y)):
        folds[h] = f
    np.savez_compressed(output / 'splits.npz', train_id=x.id.to_numpy(), test_id=test.id.to_numpy(), atom_fold=folds)
    identity = {'cohort_id': 'SYNTHETIC_ONLY_NOT_AUTHORIZED', 'config_sha256': 'fake',
                'split_sha256': ct.sha(output / 'splits.npz')}
    return x, y, test, original, folds, identity


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SYNTHETIC.mkdir(exist_ok=True)
        cls.root_context = tempfile.TemporaryDirectory(prefix='fixture_', dir=SYNTHETIC)
        cls.base = Path(cls.root_context.name)
        cls.x, cls.y, cls.test, cls.original, cls.folds, cls.identity = fixture(cls.base)
        backend = FakeBackend()
        ct._fit_five(cls.x, cls.y, cls.test, cls.original, cls.folds, cls.base, cls.identity, backend)
        cls.initial_calls = backend.calls

    @classmethod
    def tearDownClass(cls):
        cls.root_context.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='case_', dir=SYNTHETIC)
        self.out = Path(self.tmp.name)
        shutil.copytree(self.base, self.out, dirs_exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        return ct._check_cache_arrays(self.out, self.x.id.to_numpy(), self.test.id.to_numpy(), self.identity)

    def rewrite_npz(self, path, fn):
        z = ct._load_npz(path)
        fn(z)
        np.savez_compressed(path, **z)

    def update_fold_manifest(self, fold=1):
        folder = self.out / 'folds' / f'fold_{fold:02d}'
        r = ct.read(folder / 'manifest.json')
        r['file_sha256']['predictions.npz'] = ct.sha(folder / 'predictions.npz')
        ct.atomic_json(folder / 'manifest.json', r)
        summary = ct.read(self.out / 'cache_manifest.json')
        summary['fold_manifest_sha256'][folder.name] = ct.sha(folder / 'manifest.json')
        ct.atomic_json(self.out / 'cache_manifest.json', summary)

    def test_complete_exact_reconstruction(self):
        result = self.check()
        self.assertEqual(result['status'], 'CT_GLOBAL5_CACHE_REBUILT_UNSCORED')
        self.assertFalse(result['allowed_for_submission'])
        self.assertEqual(len(result['files']), 23)

    def test_fit_receives_only_its_F_labels(self):
        for f, (ids, labels) in enumerate(self.initial_calls):
            np.testing.assert_array_equal(ids, self.x.id.to_numpy()[self.folds != f])
            np.testing.assert_array_equal(labels, self.y[self.folds != f])

    def test_fixed_precision_and_sequential_mean(self):
        z = self.check()['arrays']
        self.assertEqual(z['oof_proba'].dtype, np.float32)
        mean = np.zeros(len(self.test), dtype=np.float64)
        for f in range(1, 6):
            mean += ct._load_npz(self.out / 'folds' / f'fold_{f:02d}' / 'predictions.npz')['test_proba'] / 5
        self.assertTrue(np.array_equal(mean, z['test_proba_foldmean']))

    def test_missing_fold(self):
        shutil.rmtree(self.out / 'folds/fold_05')
        with self.assertRaises(ValueError): self.check()

    def test_corrupted_model(self):
        (self.out / 'folds/fold_03/model.json').write_text('{}')
        with self.assertRaises(ValueError): self.check()

    def test_corrupted_state(self):
        (self.out / 'folds/fold_04/feature_state.joblib').write_text('{}')
        with self.assertRaises(ValueError): self.check()

    def test_wrong_test_ids_even_with_updated_hash(self):
        path = self.out / 'folds/fold_01/predictions.npz'
        self.rewrite_npz(path, lambda z: z.update(test_id=z['test_id'][::-1]))
        self.update_fold_manifest()
        with self.assertRaisesRegex(ValueError, 'index/ID'): self.check()

    def test_scalar_prediction_cannot_broadcast(self):
        path = self.out / 'folds/fold_01/predictions.npz'
        self.rewrite_npz(path, lambda z: z.update(oof_proba=np.array(.5)))
        self.update_fold_manifest()
        with self.assertRaisesRegex(ValueError, 'shape/dtype'): self.check()

    def test_wrong_fold_prediction_dtype(self):
        path = self.out / 'folds/fold_01/predictions.npz'
        self.rewrite_npz(path, lambda z: z.update(test_proba=z['test_proba'].astype(np.float32)))
        self.update_fold_manifest()
        with self.assertRaisesRegex(ValueError, 'shape/dtype'): self.check()

    def test_altered_prediction_breaks_cache_reconstruction(self):
        path = self.out / 'folds/fold_01/predictions.npz'
        self.rewrite_npz(path, lambda z: z.update(test_proba=z['test_proba'] + .001))
        self.update_fold_manifest()
        with self.assertRaisesRegex(ValueError, 'reconstruction'): self.check()

    def test_wrong_cohort(self):
        identity = {**self.identity, 'cohort_id': 'different'}
        with self.assertRaises(ValueError):
            ct._check_cache_arrays(self.out, self.x.id.to_numpy(), self.test.id.to_numpy(), identity)

    def test_changed_splits_rejected(self):
        path = self.out / 'splits.npz'
        self.rewrite_npz(path, lambda z: z.update(atom_fold=z['atom_fold'][::-1]))
        with self.assertRaises(ValueError): self.check()

    def test_partial_checkpoint_stops_before_new_fit(self):
        shutil.rmtree(self.out / 'folds/fold_01')
        (self.out / 'folds/fold_05/model.json').unlink()
        backend = FakeBackend()
        with self.assertRaises(ValueError):
            ct._fit_five(self.x, self.y, self.test, self.original, self.folds, self.out, self.identity, backend)
        self.assertEqual(backend.calls, [])

    def test_uncommitted_partial_directory_rejected(self):
        (self.out / 'folds/fold_01.partial').mkdir()
        with self.assertRaises(ValueError):
            ct._fit_five(self.x, self.y, self.test, self.original, self.folds, self.out, self.identity, FakeBackend())

    def test_existing_folds_rebuild_without_fit(self):
        (self.out / 'cache.npz').unlink()
        (self.out / 'cache_manifest.json').unlink()
        backend = FakeBackend()
        ct._fit_five(self.x, self.y, self.test, self.original, self.folds, self.out, self.identity, backend)
        self.assertEqual(backend.calls, [])
        self.check()

    def test_replay_failure_preserves_partial(self):
        new = self.out / 'replay_failure'
        new.mkdir()
        x, y, t, o, f, identity = fixture(new)
        with self.assertRaisesRegex(ValueError, 'replay'):
            ct._fit_five(x, y, t, o, f, new, identity, FakeBackend(bad_replay=True))
        self.assertTrue((new / 'folds/fold_01.partial').is_dir())
        self.assertFalse((new / 'cache.npz').exists())

    def test_nan_prediction_rejected(self):
        new = self.out / 'nan_failure'
        new.mkdir()
        x, y, t, o, f, identity = fixture(new)
        with self.assertRaisesRegex(ValueError, 'probability'):
            ct._fit_five(x, y, t, o, f, new, identity, FakeBackend(bad_probability=True))

    def test_target_column_forbidden(self):
        with self.assertRaisesRegex(ValueError, 'target'):
            ct._fit_five(self.x, self.y, self.test.assign(Will_Buy_EV=1), self.original,
                         self.folds, self.out, self.identity, FakeBackend())

    def test_missing_authorization_fails_before_input_loader(self):
        with patch.object(ct, 'load_inputs', side_effect=AssertionError('must not read labels')):
            with self.assertRaises(FileNotFoundError):
                ct.run_authorized(self.out / 'missing_config', self.out / 'missing_auth', 'x', 'y', {})

    def test_fake_config_cannot_unlock_real_paths(self):
        config, auth = self.out / 'fake_config.json', self.out / 'fake_auth.json'
        ct.atomic_json(config, {'status': 'SYNTHETIC', 'schema_version': 1}, exclusive=True)
        ct.atomic_json(auth, {}, exclusive=True)
        with patch.object(ct, 'load_inputs', side_effect=AssertionError('must not read labels')):
            with self.assertRaisesRegex(ValueError, 'not a final contract'):
                ct.run_authorized(config, auth, ct.sha(config), ct.sha(auth), {})

    def test_production_entry_has_no_backend_parameter(self):
        import inspect
        self.assertNotIn('backend', inspect.signature(ct.run_authorized).parameters)
        self.assertNotIn('factory', inspect.signature(ct.run_authorized).parameters)

    def test_supervisor_failed_blocks_array_loading(self):
        ct.atomic_json(self.out / 'SUPERVISOR_RESULT.json', {'status': 'FAILED', 'exit_code': 1})
        context = {'config': {'output_dir': str(self.out)}, 'artifact_root': str(self.out)}
        with patch.object(ct, 'check_cache', side_effect=AssertionError('must not load arrays')):
            with self.assertRaisesRegex(ValueError, 'not complete'):
                ct.require_successful_completion(self.out, context)

    def test_exclusive_started_cannot_overwrite(self):
        path = self.out / 'STARTED.json'
        ct.atomic_json(path, {'first': True}, exclusive=True)
        with self.assertRaises(FileExistsError): ct.atomic_json(path, {'second': True}, exclusive=True)
        self.assertEqual(ct.read(path), {'first': True})

    def test_verbatim_feature_source(self):
        self.assertEqual(ct.sha(HERE / 'ct_features.py'), ct.FEATURE_SHA)

    def test_recipe_matches_frozen_source(self):
        path = HERE.parents[1] / 'e2e_v100_20260905/gpu/revision_01/frozen_config.json'
        self.assertEqual(ct.sha(path), ct.R01_CONFIG_SHA)
        source = ct.read(path)
        self.assertEqual(ct.PARAMS, source['params'])
        self.assertEqual(ct.RECIPE['iterations'], source['iterations'])
        self.assertEqual(ct.RECIPE['model_seed'], source['model_seed'])
        self.assertEqual(ct.RECIPE['fold_seed'], source['inner_seed'])

    def archive_fixture(self):
        # Pure archive verifier fixture; never accepted by authorize/run production.
        mapped = self.out / 'local_input_stub.txt'
        mapped.write_text('SYNTHETIC_LOCAL_SOURCE')
        root = self.out / 'downloaded'
        root.mkdir()
        (root / 'artifact.txt').write_text('SYNTHETIC_ARTIFACT')
        ref = {'path': '/kaggle/remote/source', 'sha256': ct.sha(mapped)}
        cfg = {'cohort_id': 'synthetic_archive', 'output_dir': '/kaggle/working/ct',
               'source_recipe': ref, 'qualification_receipt': ref, 'installation_wheel': ref,
               'source_files': {'stub': ref}, 'inputs': {'train': ref},
               'remote_execution': {'provider': 'kaggle', 'kernel_ref': 'test/not-real', 'kernel_version': 1}}
        archive = {'status': 'VERIFIED_CT_DEPLOYMENT_ARCHIVE', 'schema_version': 1,
                   'config_sha256': 'synthetic_config', 'start_authorization_sha256': 'synthetic_auth',
                   'cohort_id': cfg['cohort_id'], 'remote_output_dir': cfg['output_dir'],
                   'artifact_root': str(root), 'files': {'artifact.txt': ct.sha(root / 'artifact.txt')},
                   'path_map': {ref['path']: {'path': str(mapped), 'sha256': ref['sha256']}},
                   'remote_execution': {**cfg['remote_execution'], 'status': 'COMPLETE',
                                        'download_version_before': 1, 'download_version_after': 1}}
        return cfg, archive, root

    def test_crosshost_archive_without_remote_paths(self):
        cfg, archive, root = self.archive_fixture()
        self.assertFalse(Path(cfg['output_dir']).exists())
        self.assertEqual(ct._verify_archive_map(cfg, archive, 'synthetic_config', 'synthetic_auth'), root)

    def test_archive_wrong_mapped_source(self):
        cfg, archive, root = self.archive_fixture()
        archive['path_map']['/kaggle/remote/source']['sha256'] = 'wrong'
        with self.assertRaises(ValueError): ct._verify_archive_map(cfg, archive, 'synthetic_config', 'synthetic_auth')

    def test_archive_wrong_version(self):
        cfg, archive, root = self.archive_fixture()
        archive['remote_execution']['download_version_after'] = 2
        with self.assertRaises(ValueError): ct._verify_archive_map(cfg, archive, 'synthetic_config', 'synthetic_auth')

    def test_archive_missing_file(self):
        cfg, archive, root = self.archive_fixture()
        archive['files'] = {}
        with self.assertRaises(ValueError): ct._verify_archive_map(cfg, archive, 'synthetic_config', 'synthetic_auth')

    def test_archive_extra_path_mapping(self):
        cfg, archive, root = self.archive_fixture()
        archive['path_map']['/escape/unexpected'] = next(iter(archive['path_map'].values()))
        with self.assertRaises(ValueError): ct._verify_archive_map(cfg, archive, 'synthetic_config', 'synthetic_auth')

    def test_archive_wrong_cohort(self):
        cfg, archive, root = self.archive_fixture()
        archive['cohort_id'] = 'other_cohort'
        with self.assertRaises(ValueError): ct._verify_archive_map(cfg, archive, 'synthetic_config', 'synthetic_auth')

    def test_archive_symlink_rejected(self):
        cfg, archive, root = self.archive_fixture()
        (root / 'link').symlink_to(root / 'artifact.txt')
        with self.assertRaises(ValueError): ct._verify_archive_map(cfg, archive, 'synthetic_config', 'synthetic_auth')

    def test_fake_archive_not_production_authorized(self):
        cfg, archive, root = self.archive_fixture()
        cfg.update(status='SYNTHETIC', schema_version=1)
        cp, ap, mp = self.out / 'config.json', self.out / 'auth.json', self.out / 'map.json'
        ct.atomic_json(cp, cfg); ct.atomic_json(ap, {})
        archive.update(config_sha256=ct.sha(cp), start_authorization_sha256=ct.sha(ap))
        ct.atomic_json(mp, archive)
        with self.assertRaisesRegex(ValueError, 'not a final contract'):
            ct.authorize_archived(cp, ap, ct.sha(cp), ct.sha(ap), mp, ct.sha(mp))

    def test_explicit_feature_import_ignores_ambiguous_module(self):
        with patch.dict(sys.modules, {'ct_features': object()}):
            self.assertTrue(callable(ct._features().fit_features))


class GuardTests(unittest.TestCase):
    def run_guard_case(self, cause):
        import psutil
        with tempfile.TemporaryDirectory(prefix='guard_', dir=SYNTHETIC) as directory:
            out = Path(directory)
            worker_code = '''import os,sys,time,ctypes,json,psutil
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import ct_runner as ct
out=Path(sys.argv[2]);cause=sys.argv[3]
budget={'seconds':1 if cause=='time' else 20,'memory_bytes':1024 if cause=='memory' else 256*2**20,'threads':2}
lease={'parent_pid':os.getppid(),'parent_created':psutil.Process(os.getppid()).create_time(),
       'config_sha256':'synthetic','start_authorization_sha256':'synthetic','prior_seconds':0,'prior_peak_bytes':0}
context={'config':{'budget':budget},'config_sha256':'synthetic','start_authorization_sha256':'synthetic'}
with ct.guard(context,out,lease):
    (out/'native_ready').write_text('yes')
    ctypes.PyDLL(None).sleep(30)
'''
            launcher_code = '''import subprocess,sys,time,json
from pathlib import Path
p=subprocess.Popen([sys.executable,'-B','-c',sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]],start_new_session=True)
Path(sys.argv[3],'worker_pid').write_text(str(p.pid))
time.sleep(30)
'''
            if cause == 'write_error':
                (out / 'guard_report.json').mkdir()
            log = (out / 'stderr.log').open('w')
            parent = subprocess.Popen([sys.executable, '-B', '-c', launcher_code, worker_code,
                        str(HERE), str(out), cause], start_new_session=True, stdout=log, stderr=log)
            worker_pid = None
            try:
                until = time.monotonic() + 8
                while not (out / 'worker_pid').exists():
                    self.assertLess(time.monotonic(), until)
                    time.sleep(.02)
                worker_pid = int((out / 'worker_pid').read_text())
                if cause in ('term', 'kill'):
                    while not (out / 'native_ready').exists():
                        self.assertLess(time.monotonic(), until)
                        time.sleep(.02)
                    parent.send_signal(signal.SIGTERM if cause == 'term' else signal.SIGKILL)
                    parent.wait(timeout=3)
                while True:
                    try:
                        alive = psutil.Process(worker_pid).status() != psutil.STATUS_ZOMBIE
                    except psutil.NoSuchProcess:
                        alive = False
                    if not alive:
                        break
                    self.assertLess(time.monotonic(), until, 'guard failed to stop native worker')
                    time.sleep(.02)
                if cause != 'write_error':
                    report = ct.read(out / 'guard_report.json')
                    expected = {'term':'PARENT_DEAD','kill':'PARENT_DEAD','time':'TIME_BUDGET','memory':'MEMORY_BUDGET'}[cause]
                    self.assertEqual(report['reason'], expected)
                else:
                    log.flush()
                    self.assertIn('IsADirectoryError', (out / 'stderr.log').read_text())
            finally:
                if parent.poll() is None:
                    parent.kill(); parent.wait(timeout=3)
                if worker_pid is not None:
                    try: os.killpg(worker_pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                log.close()

    def test_parent_term_during_native_GIL(self): self.run_guard_case('term')
    def test_parent_kill_during_native_GIL(self): self.run_guard_case('kill')
    def test_wallclock_budget_native(self): self.run_guard_case('time')
    def test_memory_budget_native(self): self.run_guard_case('memory')
    def test_guard_io_exception_kills_worker(self): self.run_guard_case('write_error')


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    started = time.monotonic()
    with threadpool_limits(2):
        suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(CoreTests),
                                  unittest.defaultTestLoader.loadTestsFromTestCase(GuardTests)])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin': peak *= 1024
    report = {'status': 'SYNTHETIC_TEST_PASS' if result.wasSuccessful() else 'SYNTHETIC_TEST_FAIL',
              'scope': 'PREPARATION_ONLY_NOT_AUTHORIZED', 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'seconds': time.monotonic() - started, 'peak_bytes': peak, 'threads': 2,
              'real_targets_read': False, 'real_training_performed': False, 'real_test_generated': False,
              'source_sha256': {name: ct.sha(HERE / name) for name in ('ct_runner.py', 'ct_features.py', 'resource_guard.py', 'test_ct_runner.py')}}
    ct.atomic_json(HERE / 'synthetic_test_results.json', report)
    need_budget = report['seconds'] <= 120 and report['peak_bytes'] <= 2 * 2**30
    raise SystemExit(0 if result.wasSuccessful() and need_budget else 1)
