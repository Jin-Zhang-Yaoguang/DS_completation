"""PREPARATION_ONLY_NOT_AUTHORIZED: future single-run CT supervisor library."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
import psutil

ROOT = Path(__file__).resolve().parent
_watch_spec = importlib.util.spec_from_file_location('_d_ct_parent_watchdog', ROOT / 'watchdog.py')
_watch_module = importlib.util.module_from_spec(_watch_spec)
_watch_spec.loader.exec_module(_watch_module)
alive, identity, terminate_owned = _watch_module.alive, _watch_module.identity, _watch_module.terminate_owned
CT_ROOT = ROOT.parent / 'ct'
CT_SHA = '41f7cf4699520bf5ad7d721ae7db6b494d9cd88d96f68676bc247c63e2b4b98a'
SOURCES = ('parent_supervisor.py', 'worker_entry.py', 'watchdog.py')
FINAL_FILES = {'WORKER_COMPLETE.json', 'RUN_STARTED.json', 'cache_manifest.json',
               'runtime/manifest.json', 'guard_report.json', 'worker.log'}


def need(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path, tick=lambda: None):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            tick(); h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def once(path, value):
    path = Path(path)
    with path.open('x') as handle:
        json.dump(value, handle, allow_nan=False, indent=2)
        handle.flush(); os.fsync(handle.fileno())


def publish(path, value, tick=lambda: None):
    """Atomic no-replace publication on the same filesystem."""
    path = Path(path); temp = path.with_name(path.name + '.pending')
    once(temp, value)
    tick()
    os.link(temp, path)
    # Keep the payload hardlink: no fallible file operation after final publication.


def source_check(expected, tick=lambda: None):
    need(set(expected) == set(SOURCES), 'supervision source set mismatch')
    for name in SOURCES:
        need(sha(ROOT / name, tick) == expected[name], 'supervision source drift: ' + name)


def load_ct():
    path = CT_ROOT / 'ct_runner.py'
    need(sha(path) == CT_SHA, 'CT runner drift')
    spec = importlib.util.spec_from_file_location('_fixed_d_ct_supervised', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def prepare(config_path, auth_path, config_sha, auth_sha, expected_sources, started):
    source_check(expected_sources)
    need(sha(config_path) == config_sha and sha(auth_path) == auth_sha, 'contract/auth bytes mismatch')
    cfg, auth = read(config_path), read(auth_path)
    need(cfg['status'] == 'FINAL_AUTHORIZED_CONTRACT' and cfg['role'] == 'D_CT_GLOBAL_5FOLD', 'no final CT contract')
    need(auth['action'] == 'START_CT_GLOBAL5_D_ONCE' and auth['authorized_by'] == 'parent'
         and auth['config_sha256'] == config_sha and auth['cohort_id'] == cfg['cohort_id']
         and auth['preparation_only'] is False, 'no explicit bound start authorization')
    for name, limit in [('seconds', 7200), ('memory_bytes', 24 * 2**30), ('threads', 4)]:
        need(type(cfg['budget'][name]) is int and 0 < cfg['budget'][name] <= limit, 'invalid budget')
    refs = list(cfg['source_files'].values())
    for name in SOURCES:
        need(any(Path(r['path']).resolve() == (ROOT / name).resolve() and r['sha256'] == expected_sources[name]
                 for r in refs), 'CT contract omits supervisor source: ' + name)
    need(sha(CT_ROOT / 'ct_runner.py') == CT_SHA, 'CT worker source mismatch')
    output = Path(cfg['output_dir'])
    need(output.is_absolute() and not output.is_symlink(), 'output must be a new absolute directory')
    output = output.resolve()
    need(not output.exists() or (output.is_dir() and not any(output.iterdir())), 'CT output is not empty')
    attempt = output.parent / ('.' + output.name + '.supervision')
    return {'config_path': str(Path(config_path).resolve()), 'auth_path': str(Path(auth_path).resolve()),
            'config_sha': config_sha, 'auth_sha': auth_sha, 'supervision_sources': expected_sources,
            'budget': cfg['budget'], 'cohort_id': cfg['cohort_id'], 'output': str(output),
            'attempt': str(attempt), 'started_monotonic': started}


class Budget:
    def __init__(self, job):
        self.job = job; self.peak = 0; self.checks = []; self.watcher = None; self.known = {}

    def check(self, phase, record=False):
        own = psutil.Process()
        try:
            for ref in list(self.known.values()):
                if alive(ref):
                    for child in psutil.Process(ref['pid']).children(recursive=True):
                        self.known[child.pid] = identity(child.pid)
        except psutil.NoSuchProcess:
            pass
        rss = own.memory_info().rss
        for ref in self.known.values():
            if alive(ref):
                try: rss += psutil.Process(ref['pid']).memory_info().rss
                except psutil.NoSuchProcess: pass
        self.peak = max(self.peak, rss)
        elapsed = time.monotonic() - self.job['started_monotonic']
        need(elapsed < self.job['budget']['seconds'] and self.peak <= self.job['budget']['memory_bytes'], 'complete lifecycle budget exceeded')
        if self.watcher is not None:
            need(self.watcher.poll() is None, 'external watchdog unexpectedly exited')
        row = {'phase': phase, 'seconds': elapsed, 'peak_process_tree_rss_bytes': self.peak}
        if record: self.checks.append(row)
        return row


def archive_log(source, dest, budget):
    temp = Path(dest).with_name(Path(dest).name + '.pending')
    with Path(source).open('rb') as src, temp.open('xb') as dst:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            budget.check('LOG_ARCHIVE'); dst.write(chunk)
        dst.flush(); os.fsync(dst.fileno())
    os.link(temp, dest); temp.unlink()


def metadata(job, worker, budget):
    output = Path(job['output']); start = read(output / 'RUN_STARTED.json')
    done = read(output / 'WORKER_COMPLETE.json'); guard = read(output / 'guard_report.json')
    instance = {'worker_pid': worker['pid'], 'worker_created': worker['created'],
                'parent_pid': os.getpid(), 'parent_created': psutil.Process().create_time()}
    need(start['status'] == 'CT_GLOBAL5_RUN_STARTED' and start['pid'] == worker['pid']
         and start['worker_created'] == worker['created']
         and start['lease']['parent_pid'] == instance['parent_pid']
         and start['lease']['parent_created'] == instance['parent_created'], 'STARTED instance mismatch')
    for value in (start, done):
        need(value['config_sha256'] == job['config_sha'] and value['start_authorization_sha256'] == job['auth_sha']
             and value['cohort_id'] == job['cohort_id'], 'worker source identity mismatch')
    need(done['status'] == 'CT_GLOBAL5_WORKER_COMPLETE_UNSCORED' and done['completed_folds'] == 5
         and done['instance'] == instance and done['allowed_for_submission'] is False
         and done['deployment_verified'] is False, 'worker did not complete all folds')
    need(guard['status'] in ('MONITORING', 'WORKER_EXITED') and guard['instance'] == instance, 'inner guard failed')
    need(type(guard['seconds']) in (int, float) and math.isfinite(guard['seconds']) and guard['seconds'] >= 0
         and type(guard['peak_bytes']) is int and guard['peak_bytes'] >= 0, 'invalid inner guard budget')
    budget.peak = max(budget.peak, guard['peak_bytes'])
    need(guard['seconds'] <= budget.check('INNER_GUARD')['seconds'], 'inner guard exceeds actual lifecycle')
    files = {name: sha(output / name, lambda: budget.check('FINAL_HASH')) for name in FINAL_FILES}
    need(done['cache_manifest_sha256'] == files['cache_manifest.json'], 'cache completion hash mismatch')
    return instance, files


def _execute(job, command, validate):
    """Private process engine; production command and validator are fixed by supervise()."""
    attempt = Path(job['attempt']); attempt.mkdir(parents=True, exist_ok=False)
    output = Path(job['output']); budget = Budget(job); child = watcher = None
    worker = None; committed = False; previous_handler = signal.getsignal(signal.SIGTERM)
    alarm_handler = None
    def interrupted(signum, frame):
        if not committed:
            raise RuntimeError('supervisor interrupted by signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    launch = {**job, 'parent': identity(os.getpid()), 'token': uuid.uuid4().hex}
    try:
        budget.check('START', True)
        once(attempt / 'LAUNCH.json', launch)
        with (attempt / 'worker.log').open('xb') as log, (attempt / 'watchdog.log').open('xb') as guard_log:
            child = subprocess.Popen(command(attempt / 'LAUNCH.json'), stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            worker = identity(child.pid); budget.known[child.pid] = worker
            spec = {**launch, 'worker': worker, 'seconds': job['budget']['seconds'],
                    'memory_bytes': job['budget']['memory_bytes'], 'prior_peak': budget.peak}
            once(attempt / 'WATCH_SPEC.json', spec)
            watcher = subprocess.Popen([sys.executable, '-B', str(ROOT / 'watchdog.py'), str(attempt / 'WATCH_SPEC.json')],
                                       stdout=guard_log, stderr=subprocess.STDOUT, start_new_session=True)
            budget.known[watcher.pid] = identity(watcher.pid)
            budget.watcher = watcher
            while child.poll() is None:
                budget.check('WORKER'); time.sleep(.05)
            budget.check('AFTER_WORKER_EXIT', True)
            need(child.returncode == 0, 'worker failed with exit ' + str(child.returncode))
            # Known separate-session CT guard must also exit, not become an orphan.
            deadline = time.monotonic() + 3
            while any(alive(r) for pid, r in budget.known.items() if pid not in (watcher.pid, child.pid)):
                budget.check('CHILD_CLEANUP'); need(time.monotonic() < deadline, 'owned descendant survived worker')
                time.sleep(.02)
            log.flush(); os.fsync(log.fileno())
        budget.check('AFTER_LOG_CLOSE', True)
        output.mkdir(parents=True, exist_ok=True)
        archive_log(attempt / 'worker.log', output / 'worker.log', budget)
        instance, files = validate(job, worker, budget)
        budget.check('AFTER_FINAL_VALIDATION', True)
        # After the process watchdog closes, a kernel-default alarm still interrupts
        # blocked native finalization. This library requires a dedicated process.
        need(signal.getitimer(signal.ITIMER_REAL) == (0., 0.), 'existing process timer forbidden')
        alarm_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.setitimer(signal.ITIMER_REAL, max(.001, job['budget']['seconds'] - (time.monotonic() - job['started_monotonic'])))
        once(attempt / 'WATCHDOG_STOP.json', {'token': launch['token']})
        watcher.wait(timeout=3); budget.watcher = None
        need(watcher.returncode == 0, 'external watchdog shutdown failed')
        watched = read(attempt / 'WATCHDOG_REPORT.json')
        need(watched['status'] == 'CLEAN_STOP' and watched['token'] == launch['token']
             and watched['parent'] == launch['parent'] and watched['worker'] == worker, 'external watchdog did not close')
        budget.peak = max(budget.peak, watched['peak_bytes'])
        archive_log(attempt / 'WATCHDOG_REPORT.json', output / 'external_watchdog_report.json', budget)
        final = budget.check('AFTER_EXIT_AND_CLEANUP', True)
        need(watched['seconds'] <= final['seconds'], 'external guard time exceeds final time')
        result = {'status': 'CT_DEPLOYMENT_SUPERVISOR_COMPLETE', 'exit_code': 0,
                  'phase': 'AFTER_EXIT_AND_CLEANUP', 'completed_folds': 5,
                  'config_sha256': job['config_sha'], 'start_authorization_sha256': job['auth_sha'],
                  'instance': instance, 'seconds': final['seconds'], 'peak_process_tree_rss_bytes': budget.peak,
                  'file_sha256': files, 'resource_checks': budget.checks,
                  'external_watchdog_file': 'external_watchdog_report.json',
                  'external_watchdog_sha256': sha(output / 'external_watchdog_report.json'),
                  'allowed_for_submission': False, 'deployment_verified': False}
        blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        try:
            publish(output / 'SUPERVISOR_RESULT.json', result, lambda: budget.check('ATOMIC_COMMIT'))
            committed = True
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        return result
    except BaseException as error:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if worker is not None: terminate_owned(worker, {p: r for p, r in budget.known.items() if watcher is None or p != watcher.pid})
        if child is not None:
            try: child.wait(timeout=3)
            except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=3)
        if watcher is not None and watcher.poll() is None:
            watcher.terminate()
            try: watcher.wait(timeout=3)
            except subprocess.TimeoutExpired: watcher.kill(); watcher.wait(timeout=3)
        failure = {'status': 'CT_DEPLOYMENT_SUPERVISOR_FAILED', 'error_type': type(error).__name__,
                   'error': str(error), 'config_sha256': job['config_sha'], 'start_authorization_sha256': job['auth_sha'],
                   'seconds': time.monotonic() - job['started_monotonic'], 'peak_process_tree_rss_bytes': budget.peak,
                   'allowed_for_submission': False, 'deployment_verified': False}
        # Preserve the attempt even when output never existed; I/O errors never become COMPLETE.
        once(attempt / 'FAILURE.json', failure)
        raise
    finally:
        if alarm_handler is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, alarm_handler)
        signal.signal(signal.SIGTERM, previous_handler)


def supervise(config_path, auth_path, expected_config_sha, expected_auth_sha, expected_sources):
    started = time.monotonic()
    job = prepare(config_path, auth_path, expected_config_sha, expected_auth_sha, expected_sources, started)
    def validate(job, worker, budget):
        source_check(expected_sources, lambda: budget.check('SOURCE_RECHECK'))
        need(sha(config_path, lambda: budget.check('CONFIG_RECHECK')) == expected_config_sha
             and sha(auth_path, lambda: budget.check('AUTH_RECHECK')) == expected_auth_sha, 'final contract/auth drift')
        return metadata(job, worker, budget)
    return _execute(job, lambda path: [sys.executable, '-B', str(ROOT / 'worker_entry.py'), '_parent_worker', str(path)], validate)


if __name__ == '__main__':
    raise SystemExit('PREPARATION_ONLY_NOT_AUTHORIZED: library only; no real launch CLI')
