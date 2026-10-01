"""监督 bootstrap 与训练的同一进程树，逐阶段闭合固定资源预算。"""
from __future__ import annotations
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parent
LIMIT = 7200.0
MEMORY = 24 * 1024**3
THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")


def child_environment():
    env = os.environ.copy()
    env.update({key: "4" for key in THREAD_KEYS})
    return env


def process_tree_rss():
    """包含监督进程本身；已退出子进程的查询竞争不导致假失败。"""
    root = psutil.Process(os.getpid())
    total = 0
    for process in (root, *root.children(recursive=True)):
        try:
            total += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
    return total


class Budget:
    def __init__(self, started=None, clock=time.monotonic, rss=process_tree_rss):
        self.clock = clock
        self.rss = rss
        self.started = clock() if started is None else started
        self.peak = 0
        self.checks = []

    def check(self, phase):
        elapsed = self.clock() - self.started
        current = self.rss()
        self.peak = max(self.peak, current)
        check = {"phase": phase, "seconds": elapsed, "rss_bytes": current,
                 "peak_process_tree_rss": self.peak}
        if not phase.endswith("POLL"):
            self.checks.append(check)
        if elapsed >= LIMIT:
            raise TimeoutError(f"7200 second total GPU budget exceeded at {phase}")
        if self.peak > MEMORY:
            raise MemoryError(f"24 GiB process-tree memory budget exceeded at {phase}")
        return check


def kill_tree(process):
    """子进程使用新会话；即使会话主进程先退出，也清理其遗留进程组。"""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def guarded(script, budget, root=ROOT, popen=subprocess.Popen, sleep=time.sleep):
    budget.check(f"BEFORE_{script}")
    process = popen([sys.executable, "-u", str(root / script)], cwd=root,
                    start_new_session=True, env=child_environment())
    try:
        budget.check(f"AFTER_START_{script}")
        while process.poll() is None:
            budget.check(f"{script}_POLL")
            sleep(0.5)
        budget.check(f"AFTER_EXIT_{script}")
        if process.returncode:
            raise RuntimeError(f"{script} failed with status {process.returncode}")
    finally:
        kill_tree(process)
        budget.check(f"AFTER_CLEANUP_{script}")


def atomic_result(root, payload):
    path = root / "GPU_RUN_RESULT.json"
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("x") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def main(root=ROOT):
    started = time.monotonic()
    # 在 bootstrap 导入数值库、安装依赖或执行合成 GPU smoke 之前设置。
    os.environ.update({key: "4" for key in THREAD_KEYS})
    budget = Budget(started=started)
    with (root / "gpu_run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = root / "GPU_RUN_STARTED.json"
        with marker.open("x") as handle:
            json.dump({"pid": os.getpid(), "started_unix": time.time(),
                       "budget_seconds": LIMIT, "memory_bytes": MEMORY,
                       "threads": 4, "one_shot": True}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            budget.check("START")
            guarded("bootstrap.py", budget, root)
            guarded("cache_runner.py", budget, root)
            final = budget.check("BEFORE_COMPLETE")
            status = {"status": "GPU_CACHE_RUN_COMPLETE", "seconds": final["seconds"],
                      "peak_process_tree_rss": budget.peak, "resource_checks": budget.checks}
            atomic_result(root, status)
        except BaseException as error:
            status = {"status": "GPU_CACHE_RUN_FAILED", "type": type(error).__name__,
                      "error": str(error), "seconds": time.monotonic() - started,
                      "peak_process_tree_rss": budget.peak, "resource_checks": budget.checks}
            atomic_result(root, status)
            raise
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
