"""对战口径坐标下降：目标 = vs fam_W/fam_C 的平均 margin（4 seed × 双席位）。"""
import os, sys, json, time
from concurrent.futures import ProcessPoolExecutor
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from fidelity import play
OPPS = ["tape:tapes/fam_W_17w5l.json", "tape:tapes/fam_C_0w5l.json"]
SEEDS = [91, 92, 93, 94]
def one(a):
    cfg, opp, sd = a
    os.environ["V15_PARAMS"] = json.dumps(cfg)
    r0 = play(f"mod:{W}/v34_demand_align/main.py", opp, sd, [])
    r1 = play(opp, f"mod:{W}/v34_demand_align/main.py", sd, [])
    return (r0["bank"][0] - r0["bank"][1], r1["bank"][1] - r1["bank"][0])
def evaluate(cfg):
    jobs = [(cfg, o, sd) for o in OPPS for sd in SEEDS]
    res = []
    with ProcessPoolExecutor(8) as ex:
        for pair in ex.map(one, jobs): res += list(pair)
    return sum(res) / len(res), sum(r > 0 for r in res), len(res)
AXES = [
    ("straw_scale_zero", [0.5, 0.8, 1.0]),      # 无莓店时草莓比例
    ("straw_scale_one", [0.75, 1.0]),
    ("sheep_floor", [2, 3, 4]),                  # 无 yarn 保底羊
    ("cow_base", [3, 5, 7]),                     # 牛基数
    ("rate_mult", [1.0, 1.5, 2.5]),
    ("melon_tiles", [12, 16]),
]
if __name__ == "__main__":
    cur = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    best, w, n = evaluate(cur)
    print(f"start margin={best:+.0f} w={w}/{n}", flush=True)
    for name, vals in AXES:
        res = []
        for v in vals:
            if cur.get(name) == v: continue
            m, w2, n2 = evaluate({**cur, name: v})
            res.append((m, v, w2, n2))
            print(f"  {name}={v}: margin={m:+.0f} w={w2}/{n2}", flush=True)
        if res:
            top = max(res)
            if top[0] > best + 300:
                best = top[0]; cur[name] = top[1]
                print(f"ACCEPT {name}={top[1]} margin={best:+.0f}", flush=True)
    print("FINAL", best, json.dumps(cur), flush=True)
