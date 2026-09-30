"""V8 自博弈席位不对称检验：同 seed 下座0 vs 座1 的胜负分布。"""
import importlib.util
import os
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
V8P = os.path.join(HERE, "main.py")


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


def job(seed):
    a = load(V8P, f"a{os.getpid()}").agent
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    steps = env.run([a, a])
    if [str(s.status) for s in steps[-1]] != ["DONE", "DONE"]:
        return None
    return [float(s.reward or 0) for s in steps[-1]]


def main():
    seeds = list(range(990001, 990013))
    with ProcessPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(job, seeds))
    s0 = s1 = ties = 0
    for r in results:
        if r is None:
            continue
        print(f"seed 座0={r[0]:.0f} 座1={r[1]:.0f} 差={r[0]-r[1]:+.0f}")
        if r[0] > r[1]:
            s0 += 1
        elif r[1] > r[0]:
            s1 += 1
        else:
            ties += 1
    print(f"\nV8 vs V8: 座0 胜 {s0}, 座1 胜 {s1}, 平 {ties}")


if __name__ == "__main__":
    main()
