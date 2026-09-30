"""夜间多轮坐标下降：V23 结构参数，循环直到收敛或超时。"""
import os, sys, json, time
from concurrent.futures import ProcessPoolExecutor
os.environ.setdefault("SEARCH_TARGET", "v23_plan_scheduler")
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from fidelity import play
SH = [["ICE_CREAM_SHOP",72],["BRUNCH_SPOT",144],["YARN_STORE",216],["PIZZA_SHOP",288],["ICE_CREAM_SHOP",360],["PIZZA_SHOP",432],["PIZZA_SHOP",504],["SMOOTHIE_SHOP",576]]
SEEDS = [21, 22, 23]
def evaluate(params):
    os.environ["V23_PARAMS"] = json.dumps(params)
    tot = 0; prods = {}
    for sd in SEEDS:
        r = play(f"mod:{W}/v23_plan_scheduler/main.py", "pass:", sd, SH)
        tot += r["bank"][0]
        for k, v in r["prod"][0].items(): prods[k] = prods.get(k, 0) + v
    return tot / len(SEEDS), {k: round(v/len(SEEDS)) for k, v in prods.items()}
def run_one(a): return a[0], evaluate(a[1])
AXES = [
    ("straw_from", [3, 4, 5, 6]),
    ("straw_cash_floor", [150, 250, 400, 600]),
    ("straw_n", [26, 30, 33]),
    ("melon_n", [10, 12]),
    ("reuse_n", [28, 33, 38]),
    ("fert_keep", [12, 18, 24]),
    ("sell_batch", [7, 9, 12]),
    ("harvest_wheat_age", [3, 4]),
    ("animal_harvest_min", [2, 3]),
    ("carrot_from", [23, 25, 27]),
    ("hands_default", [11, 12, 13]),
    ("hv_crops", [["STRAWBERRY"], ["STRAWBERRY", "MELON"], ["STRAWBERRY", "MELON", "TOMATO"]]),
    ("straw_last_plant", [14, 16, 18]),
    ("wheat_last_plant", [26, 27, 28]),
]
if __name__ == "__main__":
    deadline = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 5) * 3600
    cur = {}
    best, bp0 = evaluate(cur)
    print(f"start {best:.0f} {bp0}", flush=True)
    rnd = 0
    while time.time() < deadline:
        rnd += 1; improved = False
        for name, vals in AXES:
            if time.time() > deadline: break
            jobs = [(v, {**cur, name: v}) for v in vals if cur.get(name) != v]
            res = []
            with ProcessPoolExecutor(min(6, max(1, len(jobs)))) as ex:
                for v, (sc, pr) in ex.map(run_one, jobs): res.append((sc, v, pr))
            if not res: continue
            top = max(res)
            line = " ".join(f"{v}:{sc:.0f}" for sc, v, _ in sorted(res, reverse=True))
            print(f"r{rnd} {name}: {line}", flush=True)
            if top[0] > best + 100:
                best = top[0]; cur[name] = top[1]; improved = True
                print(f"r{rnd} ACCEPT {name}={top[1]} best={best:.0f} prod={top[2]}", flush=True)
        print(f"ROUND {rnd} done best={best:.0f} cur={json.dumps(cur)}", flush=True)
        if not improved:
            print("CONVERGED", flush=True); break
    print(f"FINAL {best:.0f} {json.dumps(cur)}", flush=True)
