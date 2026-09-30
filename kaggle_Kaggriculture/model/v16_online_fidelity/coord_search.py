"""G0 坐标下降：逐参数扫，目标=教师序列 3 seed 平均 bank（单人）。"""
import os, sys, json, itertools, subprocess
from concurrent.futures import ProcessPoolExecutor
from fidelity import play
W = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
TARGET = __import__("os").environ.get("SEARCH_TARGET", "v15_closed_loop")
SH = [["ICE_CREAM_SHOP",72],["BRUNCH_SPOT",144],["YARN_STORE",216],["PIZZA_SHOP",288],["ICE_CREAM_SHOP",360],["PIZZA_SHOP",432],["PIZZA_SHOP",504],["SMOOTHIE_SHOP",576]]
SEEDS = [21, 22, 23]
def evaluate(params):
    os.environ["V15_PARAMS"] = json.dumps(params)
    tot = 0; prods = {}
    for sd in SEEDS:
        r = play(f"mod:{W}/{TARGET}/main.py", "pass:", sd, SH)
        tot += r["bank"][0]
        for k, v in r["prod"][0].items(): prods[k] = prods.get(k, 0) + v
    return tot / len(SEEDS), {k: round(v/len(SEEDS)) for k, v in prods.items()}
def run_one(args):
    return args[0], evaluate(args[1])
if __name__ == "__main__":
    base = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"fert_reserve": 24, "fertilize_crops": ["STRAWBERRY"], "animal_cash_reserve": 240}
    AXES = [
        ("wave_boost", [2.5, 4.0, 6.0]),
        ("wave_threshold", [5, 8, 12]),
    ]
    cur = dict(base)
    best, bp = evaluate(cur)
    print(f"start: {best:.0f} {bp}", flush=True)
    for name, vals in AXES:
        jobs = []
        for v in vals:
            if cur.get(name) == v: continue
            c = dict(cur); c[name] = v; jobs.append((v, c))
        results = []
        with ProcessPoolExecutor(min(6, len(jobs) or 1)) as ex:
            for v, (score, pr) in ex.map(run_one, jobs): results.append((score, v, pr))
        for score, v, pr in sorted(results, reverse=True):
            print(f"  {name}={v}: {score:.0f} S{pr.get('STRAWBERRY',0)} W{pr.get('WOOL',0)} M{pr.get('MILK',0)} F{pr.get('FERTILIZER',0)} wh{pr.get('WHEAT',0)}", flush=True)
        if results:
            top = max(results)
            if top[0] > best:
                best = top[0]; cur[name] = top[1]
                print(f"-> accept {name}={top[1]} best={best:.0f}", flush=True)
    print("FINAL", best, json.dumps(cur), flush=True)
