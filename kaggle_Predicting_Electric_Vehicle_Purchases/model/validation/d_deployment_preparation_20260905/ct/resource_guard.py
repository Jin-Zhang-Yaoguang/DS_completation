"""PREPARATION_ONLY_NOT_AUTHORIZED: native-safe worker resource guard, no training."""
import json
import os
from pathlib import Path
import signal
import sys
import time
import psutil


def atomic(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, allow_nan=False))
    os.replace(temporary, path)


def same_process(pid, created):
    try:
        p = psutil.Process(pid)
        return p.create_time() == created and p.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def watch(spec):
    peak = spec['prior_peak_bytes']
    started = time.monotonic()
    path = Path(spec['report'])
    instance = {key: spec[key] for key in ('worker_pid', 'worker_created', 'parent_pid', 'parent_created')}
    atomic(spec['ready'], {'status': 'GUARD_READY', 'worker_pid': spec['worker_pid'],
                          'worker_created': spec['worker_created'], 'parent_pid': spec['parent_pid'],
                          'parent_created': spec['parent_created'], 'guard_pid': os.getpid()})
    while True:
        elapsed = spec['prior_seconds'] + time.monotonic() - started
        reason = None
        if not same_process(spec['parent_pid'], spec['parent_created']):
            reason = 'PARENT_DEAD'
        if not same_process(spec['worker_pid'], spec['worker_created']):
            atomic(path, {'status': 'WORKER_EXITED', 'seconds': elapsed, 'peak_bytes': peak, 'instance': instance})
            return
        try:
            worker = psutil.Process(spec['worker_pid'])
            members = [worker] + worker.children(recursive=True)
            peak = max(peak, sum(p.memory_info().rss for p in members if p.is_running()))
        except psutil.NoSuchProcess:
            continue
        except psutil.Error:
            reason = 'RESOURCE_INSPECTION_FAILED'
        if elapsed >= spec['seconds']:
            reason = 'TIME_BUDGET'
        if peak > spec['memory_bytes']:
            reason = 'MEMORY_BUDGET'
        if reason:
            atomic(path, {'status': 'STOPPED', 'reason': reason, 'seconds': elapsed,
                          'peak_bytes': peak, 'instance': instance})
            if same_process(spec['worker_pid'], spec['worker_created']):
                os.killpg(spec['worker_pid'], signal.SIGKILL)
            return
        atomic(path, {'status': 'MONITORING', 'seconds': elapsed, 'peak_bytes': peak, 'instance': instance})
        time.sleep(0.2)


def main(spec):
    # An I/O or inspection exception must never silently disable native supervision.
    try:
        watch(spec)
    except BaseException:
        if same_process(spec['worker_pid'], spec['worker_created']):
            try:
                os.killpg(spec['worker_pid'], signal.SIGKILL)
            except ProcessLookupError:
                pass
        raise


if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
