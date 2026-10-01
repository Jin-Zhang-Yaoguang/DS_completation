"""Preparation: supervises only an explicitly identified, newly started process tree."""
import json
import os
from pathlib import Path
import signal
import sys
import time
import psutil


def identity(pid):
    return {'pid': pid, 'created': psutil.Process(pid).create_time()}


def alive(ref):
    try:
        p = psutil.Process(ref['pid'])
        return p.create_time() == ref['created'] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, allow_nan=False)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def sample(parent, known):
    # Retain identities after reparenting, including the CT guard's separate session.
    for ref in list(known.values()):
        if alive(ref):
            try:
                for child in psutil.Process(ref['pid']).children(recursive=True):
                    if child.pid != os.getpid():
                        known[child.pid] = identity(child.pid)
            except psutil.NoSuchProcess:
                pass
    total = 0
    refs = {parent['pid']: parent, os.getpid(): identity(os.getpid()), **known}
    for ref in refs.values():
        if alive(ref):
            try:
                total += psutil.Process(ref['pid']).memory_info().rss
            except psutil.NoSuchProcess:
                pass
    return total


def terminate_owned(worker, known):
    if alive(worker):
        try:
            if os.getpgid(worker['pid']) == worker['pid']:
                os.killpg(worker['pid'], signal.SIGKILL)
        except ProcessLookupError:
            pass
    for ref in reversed(list(known.values())):
        if ref['pid'] != os.getpid() and alive(ref):
            try:
                os.kill(ref['pid'], signal.SIGKILL)
            except ProcessLookupError:
                pass


def stop_parent(parent):
    if alive(parent):
        os.kill(parent['pid'], signal.SIGTERM)
        time.sleep(.3)
        if alive(parent):
            os.kill(parent['pid'], signal.SIGKILL)


def watch(spec):
    parent, worker = spec['parent'], spec['worker']
    known = {worker['pid']: worker}
    root = Path(spec['attempt'])
    peak = spec['prior_peak']
    record = {'token': spec['token'], 'parent': parent, 'worker': worker,
              'watchdog': identity(os.getpid())}
    try:
        if not alive(parent) or not alive(worker):
            raise RuntimeError('parent/worker absent before watchdog handshake')
        write(root / 'WATCHDOG_READY.json', record)
        while True:
            peak = max(peak, sample(parent, known))
            elapsed = time.monotonic() - spec['started_monotonic']
            reason = ('PARENT_DEAD' if not alive(parent) else
                      'TIME_BUDGET' if elapsed >= spec['seconds'] else
                      'MEMORY_BUDGET' if peak > spec['memory_bytes'] else None)
            state = {**record, 'seconds': elapsed, 'peak_bytes': peak,
                     'known': list(known.values())}
            if reason:
                write(root / 'WATCHDOG_REPORT.json', {**state, 'status': 'STOPPED', 'reason': reason})
                terminate_owned(worker, known)
                stop_parent(parent)
                return
            stop = root / 'WATCHDOG_STOP.json'
            if stop.exists():
                request = json.loads(stop.read_text())
                if request != {'token': spec['token']} or any(alive(r) for r in known.values()):
                    raise RuntimeError('invalid stop or owned descendants remain alive')
                write(root / 'WATCHDOG_REPORT.json', {**state, 'status': 'CLEAN_STOP'})
                return
            write(root / 'WATCHDOG_REPORT.json', {**state, 'status': 'MONITORING'})
            time.sleep(.05)
    except BaseException:
        terminate_owned(worker, known)
        stop_parent(parent)
        raise


if __name__ == '__main__':
    watch(json.loads(Path(sys.argv[1]).read_text()))
