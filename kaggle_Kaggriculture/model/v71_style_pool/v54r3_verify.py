"""v54r3 质检①:全部已进表格子在 V56 底盘复验(v56fr 强制表路线 vs V56 原生),对手=fork 全家桶。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
TAB = {"BRUNCH_SPOT|YARN_STORE":103, "SMOOTHIE_SHOP|FARMERS_MARKET":110, "PIZZA_SHOP|ICE_CREAM_SHOP":107,
       "YARN_STORE|PET_CAFE":126, "BAKERY|SMOOTHIE_SHOP":110, "ICE_CREAM_SHOP|FARMERS_MARKET":120,
       "SMOOTHIE_SHOP|ICE_CREAM_SHOP":107, "ICE_CREAM_SHOP|BRUNCH_SPOT":107}
OPPS = ["v54","v55","v56","guru_v4","busya_race","metav4"]
def play(opp, seed, rid, stop=False):
    os.environ["KAG_FORCE_ROUTE"] = str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{HERE}/agents/v56fr_main.py")
    op = fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); t=0; combo=None
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
        if t==146:
            combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo,None
    return combo, float(g.reward(0)-g.reward(1))
def scan(job):
    o,s=job
    try: return o,s,play(o,s,-1,stop=True)[0]
    except Exception as e: return o,s,f"ERR{type(e).__name__}"
def ev(job):
    o,s,r=job
    try:
        c,m=play(o,s,r); return o,s,r,c,m
    except Exception: return o,s,r,None,None
if __name__=="__main__":
    with ProcessPoolExecutor(7) as ex:
        sc=list(ex.map(scan,[(o,s) for o in OPPS for s in range(9900,9960)],chunksize=3))
    errs=collections.Counter(c for _,_,c in sc if isinstance(c,str) and c.startswith("ERR"))
    if errs: print("错误:",dict(errs))
    hits=[(o,s,c) for o,s,c in sc if c in TAB]
    print("扫描",len(sc),"命中",len(hits),flush=True)
    jobs=[(o,s,r) for o,s,c in hits for r in (-1,TAB[c])]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(ev,jobs,chunksize=2))
    json.dump([list(r) for r in res],open(HERE/"v54r3_verify.json","w"))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(o,s,c)][r]=m
    byc=collections.defaultdict(lambda:[0,0,0]); N=W=BW=0
    for (o,s,c),v in per.items():
        rid=TAB[c]
        if rid not in v or -1 not in v: continue
        N+=1; W+=v[rid]>0; BW+=v[-1]>0
        x=byc[c]; x[0]+=v[rid]>0; x[1]+=v[-1]>0; x[2]+=1
    print(f"复验 {N} 局: 表 {W} 胜 | V56原生 {BW} 胜")
    for c,x in sorted(byc.items(),key=lambda kv:kv[1][0]-kv[1][1]):
        print(f"  {c:34s} 路线{TAB[c]:4d} 表{x[0]}/{x[2]} 原生{x[1]}/{x[2]}")
