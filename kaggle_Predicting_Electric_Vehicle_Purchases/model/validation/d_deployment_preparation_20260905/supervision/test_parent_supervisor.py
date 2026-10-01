"""Generated temporary records and owned short processes only; no real CT/data."""
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import psutil
import parent_supervisor as sup
from watchdog import alive, identity

ROOT = Path(__file__).resolve().parent

FIXTURE = r'''
import ctypes,json,os,sys,time
from pathlib import Path
import psutil
launch=json.loads(Path(sys.argv[1]).read_text()); kind=sys.argv[2]
attempt=Path(launch['attempt']); output=Path(launch['output'])
parent=launch['parent']; deadline=time.monotonic()+5
while not (attempt/'WATCHDOG_READY.json').exists():
    try: good=psutil.Process(parent['pid']).create_time()==parent['created']
    except psutil.Error: good=False
    if not good or time.monotonic()>deadline: raise SystemExit(9)
    time.sleep(.01)
output.mkdir()
assert not (output/'worker.log').exists()
instance={'worker_pid':os.getpid(),'worker_created':psutil.Process().create_time(),
          'parent_pid':parent['pid'],'parent_created':parent['created']}
(attempt/'fixture_ready').write_text(json.dumps(instance))
print('synthetic worker log before output publication',flush=True)
if kind=='native': ctypes.PyDLL(None).sleep(30)
if kind=='failure': raise SystemExit(7)
if kind=='log_collision': (output/'worker.log').write_text('must preserve')
if kind=='bad_watchdog':
    path=attempt/'WATCHDOG_REPORT.json'
    path.unlink(missing_ok=True);path.mkdir();ctypes.PyDLL(None).sleep(30)
def put(name,value):
    path=output/name;path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(value))
base={'config_sha256':launch['config_sha'],'start_authorization_sha256':launch['auth_sha'],'cohort_id':launch['cohort_id']}
put('RUN_STARTED.json',dict(base,status='CT_GLOBAL5_RUN_STARTED',pid=os.getpid(),worker_created=instance['worker_created'],
                          lease={'parent_pid':parent['pid'],'parent_created':parent['created']}))
put('cache_manifest.json',{'synthetic':True})
import hashlib
cache_sha=hashlib.sha256((output/'cache_manifest.json').read_bytes()).hexdigest()
put('WORKER_COMPLETE.json',dict(base,status='CT_GLOBAL5_WORKER_COMPLETE_UNSCORED',completed_folds=4 if kind=='bad_metadata' else 5,
   instance=instance,allowed_for_submission=False,deployment_verified=False,cache_manifest_sha256=cache_sha))
put('guard_report.json',{'status':'STOPPED' if kind=='bad_guard' else 'MONITORING','instance':instance,
                        'seconds':time.monotonic()-launch['started_monotonic'],'peak_bytes':1})
put('runtime/manifest.json',{'synthetic':True})
'''


def job(root, seconds=10, memory=2 * 2**30):
    return {'output': str(root / 'output'), 'attempt': str(root / 'attempt'),
            'config_sha': 'SYNTHETIC', 'auth_sha': 'SYNTHETIC', 'cohort_id': 'SYNTHETIC_ONLY',
            'budget': {'seconds': seconds, 'memory_bytes': memory, 'threads': 2},
            'started_monotonic': time.monotonic()}


def execute(value, kind='success', validator=sup.metadata):
    return sup._execute(value, lambda path: [sys.executable, '-B', '-c', FIXTURE, str(path), kind], validator)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ct_supervision_synthetic_')
        self.root = Path(self.temporary.name)
    def tearDown(self): self.temporary.cleanup()

    def test_success_logs_outside_then_atomic_complete(self):
        value = job(self.root); result = execute(value)
        self.assertEqual(result['status'], 'CT_DEPLOYMENT_SUPERVISOR_COMPLETE')
        self.assertEqual(set(result['file_sha256']), sup.FINAL_FILES)
        self.assertEqual((self.root/'attempt/worker.log').read_bytes(), (self.root/'output/worker.log').read_bytes())
        self.assertEqual(sup.read(self.root/'attempt/WATCHDOG_REPORT.json')['status'], 'CLEAN_STOP')
        self.assertFalse(result['allowed_for_submission'])
        self.assertFalse(alive({'pid':result['instance']['worker_pid'],'created':result['instance']['worker_created']}))

    def test_receipt_matches_original_ct_metadata_consumer(self):
        value = job(self.root); execute(value)
        ct = sup.load_ct()
        context={'artifact_root':value['output'],'config':{'budget':value['budget'],'cohort_id':value['cohort_id']},
                 'config_sha256':value['config_sha'],'start_authorization_sha256':value['auth_sha']}
        with patch.object(ct, 'check_cache', return_value={'files':{}, 'allowed_for_submission':False}):
            result=ct.require_successful_completion(value['output'], context)
        self.assertEqual(result['status'], 'CT_GLOBAL5_SUPERVISED_COMPLETE_UNSCORED')

    def test_duplicate_closed_attempt_cannot_restart(self):
        value=job(self.root); execute(value)
        with patch.object(sup.subprocess, 'Popen', side_effect=AssertionError('no second child')):
            with self.assertRaises(FileExistsError): execute(value)

    def test_nonzero_exit_preserves_failure(self):
        with self.assertRaises(ValueError): execute(job(self.root), 'failure')
        self.assertTrue((self.root/'attempt/FAILURE.json').exists())
        self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())

    def test_bad_metadata_no_success(self):
        with self.assertRaisesRegex(ValueError, 'all folds'): execute(job(self.root), 'bad_metadata')
        self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())

    def test_inner_guard_stopped_no_success(self):
        with self.assertRaisesRegex(ValueError, 'inner guard'): execute(job(self.root), 'bad_guard')

    def test_log_collision_keeps_both_original_logs(self):
        with self.assertRaises(FileExistsError): execute(job(self.root), 'log_collision')
        self.assertEqual((self.root/'output/worker.log').read_text(), 'must preserve')
        self.assertTrue((self.root/'attempt/worker.log').stat().st_size)

    def test_total_time_includes_postworker_validation(self):
        def delayed(value, worker, budget):
            time.sleep(.6); return sup.metadata(value, worker, budget)
        with self.assertRaises((ValueError, RuntimeError)):
            execute(job(self.root, seconds=.5), validator=delayed)
        self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())

    def test_native_wall_budget(self):
        with self.assertRaises((ValueError, RuntimeError)): execute(job(self.root, seconds=.5), 'native')
        self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())

    def test_rss_includes_parent_and_children(self):
        with self.assertRaises((ValueError, RuntimeError)): execute(job(self.root, memory=1), 'native')
        self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())

    def test_guard_io_failure_kills_native_worker(self):
        with self.assertRaises((ValueError, RuntimeError)): execute(job(self.root), 'bad_watchdog')
        self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())

    def test_production_has_no_fake_or_command_parameter(self):
        self.assertEqual(list(inspect.signature(sup.supervise).parameters),
                         ['config_path','auth_path','expected_config_sha','expected_auth_sha','expected_sources'])

    def test_missing_auth_no_process(self):
        expected={name:sup.sha(ROOT/name) for name in sup.SOURCES}
        with patch.object(sup.subprocess, 'Popen', side_effect=AssertionError('no process')):
            with self.assertRaises(FileNotFoundError):
                sup.supervise(self.root/'absent',self.root/'auth','x','y',expected)

    def test_source_mismatch_rejected(self):
        with self.assertRaises(ValueError): sup.source_check({name:'wrong' for name in sup.SOURCES})

    def test_default_cli_is_preparation_only(self):
        result=subprocess.run([sys.executable,'-B',str(ROOT/'parent_supervisor.py')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PREPARATION_ONLY',result.stderr)

    def test_publish_refuses_existing_result(self):
        dest=self.root/'result.json';dest.write_text('original')
        with self.assertRaises(FileExistsError): sup.publish(dest, {'new':True})
        self.assertEqual(dest.read_text(),'original')

    def test_absolute_import_from_foreign_working_directory(self):
        code='import importlib.util,sys; s=importlib.util.spec_from_file_location("s",sys.argv[1]); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(m.CT_SHA)'
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'parent_supervisor.py')],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def native_parent_case(self, tail):
        code=r'''import ctypes,sys,signal
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import test_parent_supervisor as t
if sys.argv[3]=='tail':
    original=t.sup.once
    def slow(path,value):
        if Path(path).name=='SUPERVISOR_RESULT.json.pending': ctypes.PyDLL(None).sleep(30)
        return original(path,value)
    t.sup.once=slow
    t.execute(t.job(Path(sys.argv[2]),seconds=1))
else:
    def slow(job,worker,budget):
        # A native call that cannot cooperatively respond to TERM must still stop.
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        ctypes.PyDLL(None).sleep(30)
    t.execute(t.job(Path(sys.argv[2]),seconds=1),validator=slow)
'''
        process=subprocess.Popen([sys.executable,'-B','-c',code,str(ROOT),str(self.root),'tail' if tail else 'validation'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            process.wait(timeout=5)
            self.assertEqual(process.returncode,-signal.SIGALRM if tail else -signal.SIGKILL)
            self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())
        finally:
            if process.poll() is None: process.kill();process.wait(timeout=3)

    def test_parent_native_validation_is_hard_killed(self): self.native_parent_case(False)
    def test_final_publication_native_io_has_kernel_deadline(self): self.native_parent_case(True)

    def test_parent_term_during_native(self): self.parent_death(signal.SIGTERM)
    def test_parent_kill_during_native(self): self.parent_death(signal.SIGKILL)

    def parent_death(self, sig):
        code='import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import test_parent_supervisor as t;t.execute(t.job(Path(sys.argv[2])),"native")'
        parent=subprocess.Popen([sys.executable,'-B','-c',code,str(ROOT),str(self.root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        worker=None
        try:
            ready=self.root/'attempt/fixture_ready';deadline=time.monotonic()+5
            while not ready.exists():
                self.assertLess(time.monotonic(),deadline);time.sleep(.02)
            record=json.loads(ready.read_text());worker={'pid':record['worker_pid'],'created':record['worker_created']}
            parent.send_signal(sig);parent.wait(timeout=5)
            while alive(worker):
                self.assertLess(time.monotonic(),deadline+3);time.sleep(.02)
            self.assertFalse((self.root/'output/SUPERVISOR_RESULT.json').exists())
        finally:
            if parent.poll() is None: parent.kill();parent.wait(timeout=3)
            if worker and alive(worker): os.killpg(worker['pid'],signal.SIGKILL)

    def test_worker_checks_parent_before_watchdog_exists(self):
        # Real worker_entry only: parent disappears before a watchdog is launched.
        launch=self.root/'launch.json'
        code=r'''import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import parent_supervisor as s
root=Path(sys.argv[2]); value={'parent':s.identity(os.getpid()),'attempt':str(root),
 'supervision_sources':{n:s.sha(Path(sys.argv[1])/n) for n in s.SOURCES}}
(root/'launch.json').write_text(json.dumps(value))
p=subprocess.Popen([sys.executable,'-B',str(Path(sys.argv[1])/'worker_entry.py'),'_parent_worker',str(root/'launch.json')],start_new_session=True)
(root/'child.json').write_text(json.dumps(s.identity(p.pid)))
time.sleep(.1)
'''
        parent=subprocess.Popen([sys.executable,'-B','-c',code,str(ROOT),str(self.root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        parent.wait(timeout=3);worker=sup.read(self.root/'child.json');deadline=time.monotonic()+3
        try:
            while alive(worker):
                self.assertLess(time.monotonic(),deadline);time.sleep(.02)
        finally:
            if alive(worker): os.killpg(worker['pid'],signal.SIGKILL)


if __name__ == '__main__':
    started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    import resource
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform!='darwin': peak*=1024
    evidence={'status':'SYNTHETIC_TEST_PASS' if result.wasSuccessful() else 'SYNTHETIC_TEST_FAIL',
              'scope':'PREPARATION_ONLY_NOT_AUTHORIZED','tests_run':result.testsRun,
              'failures':len(result.failures),'errors':len(result.errors),'seconds':time.monotonic()-started,
              'peak_parent_rss_bytes':peak,'real_targets_read':False,'real_training_performed':False,
              'sources':{name:sup.sha(ROOT/name) for name in (*sup.SOURCES,'test_parent_supervisor.py')}}
    destination=Path(os.environ.get('SYNTHETIC_EVIDENCE_NAME','synthetic_test_results.json'))
    assert destination.parent==Path('.') and destination.name.startswith('synthetic_test_results')
    sup.publish(ROOT/destination,evidence)
    raise SystemExit(0 if result.wasSuccessful() and evidence['seconds']<120 and peak<2*2**30 else 1)
