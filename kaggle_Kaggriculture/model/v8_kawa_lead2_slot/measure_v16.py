"""V8/V20 对公开分数榜第一 V16-RC5 的配对测量（16 核并行）。"""
import importlib.util
import os
import statistics
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
V8P = os.path.join(ROOT, "model", "v8_kawa_lead2_slot", "main.py")
OPP = os.path.join(os.environ["TMPDIR"], "kagg_survey", "opponents")
V20P = os.path.join(OPP, "v20_main.py")
V16P = os.path.join(OPP, "v16rc5_main.py")


def load(path, name):
    d = os.path.dirname(path)
    import sys
    sys.path.insert(0, d)
    for m in ("base_agent", "v1_fallback", "routes"):
        sys.modules.pop(m, None)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        import sys
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
    for seed in range(981001, 981009):
        for seat in (0, 1):
            tasks.append((V8P, V16P, seed, seat))
            tasks.append((V20P, V16P, seed, seat))
    with ProcessPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(job, tasks))
    v8m = [r for r, t in zip(results, tasks) if t[0] == V8P and r is not None]
    v20m = [r for r, t in zip(results, tasks) if t[0] == V20P and r is not None]
    for label, ms in (("V8 vs V16-RC5", v8m), ("V20 vs V16-RC5", v20m)):
        w = sum(1 for m in ms if m > 0)
        print(f"{label}: {len(ms)} 局, 胜 {w} ({w/len(ms)*100:.0f}%), 平均 margin {statistics.mean(ms):+.0f}")


if __name__ == "__main__":
    main()
