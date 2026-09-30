"""v54r1 镜像格子 × (1042,9989) 新 fork 变体复验:表路线 vs V54 原生选择。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
TAB = {"BRUNCH_SPOT|YARN_STORE":103, "SMOOTHIE_SHOP|FARMERS_MARKET":110, "PIZZA_SHOP|ICE_CREAM_SHOP":107}
OPPS = ["v55","v56","busya_race","busya_seedfloat","multiroute","hai2965","evgen"]
def play(opp, seed, rid, stop=False):
    os.environ["KAG_FORCE_ROUTE"] = str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{HERE}/agents/v54fr_main.py")
    op = fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; g.step(me(obs[0]), op(obs[1])); t += 1
        if t == 146:
            combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo, None
    return combo, float(g.reward(0) - g.reward(1))
def scan(job):
    opp, sd = job
    try: return opp, sd, play(opp, sd, -1, stop=True)[0]
    except Exception as e: return opp, sd, f"ERR{type(e).__name__}"
def ev(job):
    opp, sd, rid = job
    try:
        c, m = play(opp, sd, rid); return opp, sd, rid, c, m
    except Exception: return opp, sd, rid, None, None
if __name__ == "__main__":
    with ProcessPoolExecutor(7) as ex:
        sc = list(ex.map(scan, [(o,s) for o in OPPS for s in range(9500,9550)], chunksize=3))
    errs = collections.Counter(c for _,_,c in sc if c and c.startswith("ERR"))
    if errs: print("扫描错误:", dict(errs))
    hits = [(o,s,c) for o,s,c in sc if c in TAB]
    print("扫描", len(sc), "命中表内组合", len(hits), flush=True)
    jobs = [(o,s,r) for o,s,c in hits for r in (-1, TAB[c])]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(ev, jobs, chunksize=2))
    json.dump([list(r) for r in res], open(HERE/"v54r1_variant.json","w"))
    per = collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(o,s,c)][r]=m
    agg = collections.defaultdict(lambda:[0,0,0,0.0])
    for (o,s,c),v in per.items():
        rid=TAB[c]
        if rid not in v or -1 not in v: continue
        a=agg[o]; a[0]+= v[rid]>0; a[1]+= v[-1]>0; a[2]+=1; a[3]+= v[rid]-v[-1]
    for o,a in agg.items():
        print(f"{o:16s} 局{a[2]:3d}  表路线胜{a[0]:3d} vs 原生胜{a[1]:3d}  净增{a[3]:+.0f}")
    tot=[sum(a[i] for a in agg.values()) for i in range(4)]
    print(f"合计 局{tot[2]}  表胜{tot[0]} vs 原生胜{tot[1]}  净增{tot[3]:+.0f}")
