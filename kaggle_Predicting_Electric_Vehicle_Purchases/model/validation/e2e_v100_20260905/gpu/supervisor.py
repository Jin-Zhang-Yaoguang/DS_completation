"""One process tree, hard wall/RSS guards; preserve remote partial output."""
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent
LIMIT=7200
MEMORY=24*1024**3
started=time.monotonic()
peak=0
lock=(ROOT/'gpu_run.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
marker=ROOT/'GPU_RUN_STARTED.json'
assert not marker.exists(),'do not start a duplicate run in the same workspace'
marker.write_text(json.dumps({'pid':os.getpid(),'started_unix':time.time(),'budget_seconds':LIMIT,'memory_bytes':MEMORY}))

def kill_tree(process):
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()

def guarded(script):
    global peak
    process=subprocess.Popen([sys.executable,'-u',str(ROOT/script)],cwd=ROOT,start_new_session=True)
    try:
        while process.poll() is None:
            root=psutil.Process(process.pid)
            descendants=[root,*root.children(recursive=True)]
            rss=0
            for child in descendants:
                try:rss+=child.memory_info().rss
                except psutil.NoSuchProcess:pass
            peak=max(peak,rss)
            if time.monotonic()-started>=LIMIT:raise TimeoutError('7200 second total GPU budget exceeded')
            if rss>MEMORY:raise MemoryError('24 GiB process-tree memory budget exceeded')
            time.sleep(.5)
        if process.returncode:raise RuntimeError(f'{script} failed with status {process.returncode}')
    finally:kill_tree(process)

try:
    guarded('bootstrap.py')
    guarded('cache_runner.py')
    status={'status':'GPU_CACHE_RUN_COMPLETE','seconds':time.monotonic()-started,'peak_process_tree_rss':peak}
except BaseException as exc:
    status={'status':'GPU_CACHE_RUN_FAILED','type':type(exc).__name__,'error':str(exc),'seconds':time.monotonic()-started,'peak_process_tree_rss':peak}
    (ROOT/'GPU_RUN_RESULT.json').write_text(json.dumps(status,indent=2))
    raise
else:(ROOT/'GPU_RUN_RESULT.json').write_text(json.dumps(status,indent=2))
finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
