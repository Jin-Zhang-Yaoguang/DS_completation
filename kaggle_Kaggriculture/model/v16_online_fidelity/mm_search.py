"""做市参数搜索：目标=对 B/C/F 三家族的加权 margin。"""
import os, sys, json
from concurrent.futures import ProcessPoolExecutor
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from fidelity import play
OPPS = ["tape:tapes/fam_B_cornhub.json", "tape:tapes/fam_C_0w5l.json", "tape:tapes/fam_F_new.json"]
SEEDS = [61, 62, 63, 64]
CAND = f"sub:{W}/v25_market_maker/main.py"
def one(a):
    cfg, opp, sd = a
    os.environ["MM_PARAMS"] = json.dumps(cfg)
    r0 = play(CAND, opp, sd, []); r1 = play(opp, CAND, sd, [])
    return (r0["bank"][0] - r0["bank"][1]) + (r1["bank"][1] - r1["bank"][0])
def score(cfg):
    jobs = [(cfg, o, sd) for o in OPPS for sd in SEEDS]
    with ProcessPoolExecutor(8) as ex:
        vals = list(ex.map(one, jobs))
    w = sum(v > 0 for v in vals) * 2  # 双席位配对里每 job 含 2 局的净差, 粗略
    return sum(vals) / len(jobs)
if __name__ == "__main__":
    grid = []
    for buy in (0.70, 0.80, 0.88):
        for sell in (0.90, 0.96):
            for lot in (8, 14):
                grid.append({"buy": buy, "sell": sell, "lot": lot})
    base = score({})
    print(f"base(0.80/0.93/8): margin={base:+.0f}", flush=True)
    best = (base, {})
    for cfg in grid:
        m = score(cfg)
        print(f"{cfg}: {m:+.0f}", flush=True)
        if m > best[0]: best = (m, cfg)
    print("BEST", best, flush=True)
