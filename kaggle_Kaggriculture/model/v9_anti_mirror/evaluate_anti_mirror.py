"""v9b 反同质化层验证：对 V8（镜像）/ V20 / 弱池 的配对测量。"""
import importlib.util
import os
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
V9B = os.path.join(HERE, "main.py")
V8P = os.path.join(HERE, "..", "v8_kawa_lead2_slot", "main.py")
OPP = os.path.join(os.environ["TMPDIR"], "kagg_survey", "opponents")
V20P = os.path.join(OPP, "v20_main.py")


def load(path, name):
    d = os.path.dirname(path)
    sys.path.insert(0, d)
    for m in ("base_agent", "v1_fallback", "routes"):
        sys.modules.pop(m, None)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for m in ("base_agent", "v1_fallback", "routes"):
            sys.modules.pop(m, None)
        sys.path.pop(0)


def job(task):
    a_path, b_path, seed, seat = task
    a = load(a_path, f"a{os.getpid()}").agent
    b = load(b_path, f"b{os.getpid()}").agent
    from kaggle_environments import make
    agents = [a, b] if seat == 0 else [b, a]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    steps = env.run(agents)
    if [str(s.status) for s in steps[-1]] != ["DONE", "DONE"]:
        return None
    r = [float(s.reward or 0) for s in steps[-1]]
    return (r[0] - r[1]) if seat == 0 else (r[1] - r[0])


def main():
    tasks = []
    for seed in range(982001, 982009):
        for seat in (0, 1):
            tasks.append((V9B, V8P, seed, seat))
            tasks.append((V9B, V20P, seed, seat))
    with ProcessPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(job, tasks))
    m8 = [r for r, t in zip(results, tasks) if t[1] == V8P and r is not None]
    m20 = [r for r, t in zip(results, tasks) if t[1] == V20P and r is not None]
    for label, ms in (("V9b vs V8(镜像)", m8), ("V9b vs V20", m20)):
        w = sum(1 for m in ms if m > 0)
        print(f"{label}: {len(ms)} 局, 胜 {w} ({w/len(ms)*100:.0f}%), 平均 margin {statistics.mean(ms):+.0f}")


if __name__ == "__main__":
    main()
