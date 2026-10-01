"""No standalone training CLI. Internal child waits for its live parent's watchdog."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from watchdog import alive, identity


def entry(launch_path):
    from parent_supervisor import load_ct, need, source_check
    launch = json.loads(Path(launch_path).read_text())
    source_check(launch['supervision_sources'])
    parent = launch['parent']
    need(os.getppid() == parent['pid'] and os.getpid() == os.getpgrp(), 'not an isolated direct child')
    worker = identity(os.getpid())
    ready_path = Path(launch['attempt']) / 'WATCHDOG_READY.json'
    deadline = time.monotonic() + 10
    while not ready_path.exists():
        need(alive(parent) and os.getppid() == parent['pid'] and time.monotonic() < deadline,
             'parent lost before watchdog handshake')
        time.sleep(.02)
    ready = json.loads(ready_path.read_text())
    need(ready['token'] == launch['token'] and ready['parent'] == parent and ready['worker'] == worker
         and alive(parent) and alive(ready['watchdog']), 'watchdog handshake mismatch')
    report_path = Path(launch['attempt']) / 'WATCHDOG_REPORT.json'
    while not report_path.exists():
        need(alive(parent) and alive(ready['watchdog']) and time.monotonic() < deadline, 'watchdog report absent')
        time.sleep(.02)
    report = json.loads(report_path.read_text())
    need(report['status'] == 'MONITORING' and report['token'] == launch['token'], 'watchdog did not admit worker')
    lease = {'parent_pid': parent['pid'], 'parent_created': parent['created'],
             'config_sha256': launch['config_sha'], 'start_authorization_sha256': launch['auth_sha'],
             'prior_seconds': time.monotonic() - launch['started_monotonic'], 'prior_peak_bytes': report['peak_bytes']}
    # No CT imports, source graph hashes, numerical libraries or inputs before handshake.
    ct = load_ct()
    ct.run_authorized(launch['config_path'], launch['auth_path'], launch['config_sha'], launch['auth_sha'], lease)


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '_parent_worker':
        raise SystemExit('PREPARATION_ONLY_NOT_AUTHORIZED')
    entry(sys.argv[2])
