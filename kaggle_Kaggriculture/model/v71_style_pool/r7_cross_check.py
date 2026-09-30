"""R7 候选格跨族安全检查:候选带 vs r5 自然行为,对手 v55/v56/busya。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
TAB={"BRUNCH_SPOT|BRUNCH_SPOT":110,"BRUNCH_SPOT|ICE_CREAM_SHOP":103,"PET_CAFE|BAKERY":124,
     "PIZZA_SHOP|YARN_STORE":126,"YARN_STORE|BRUNCH_SPOT":126,"YARN_STORE|SMOOTHIE_SHOP":126,
     "ICE_CREAM_SHOP|BRUNCH_SPOT":110,"PET_CAFE|PIZZA_SHOP":123,"PIZZA_SHOP|FARMERS_MARKET":9}
OPPS=["v55","v56","busya_race"]
def play(o,seed,rid,stop=False):
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
    op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; combo=None
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
        if t==146:
            combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo,None
    return combo,float(g.reward(0)-g.reward(1))
def scan(job):
    o,s=job
    try: return o,s,play(o,s,-1,stop=True)[0]
    except Exception: return o,s,None
def ev(job):
    o,s,r=job
    try:
        c,m=play(o,s,r); return o,s,r,c,m
    except Exception: return o,s,r,None,None
if __name__=="__main__":
    jobs=[(o,s) for o in OPPS for s in range(12000,12120)]
    with ProcessPoolExecutor(7) as ex: sc=list(ex.map(scan,jobs,chunksize=4))
    need=collections.Counter(); hits=[]
    for o,s,c in sc:
        if c in TAB and need[c]<8: need[c]+=1; hits.append((o,s,c))
    print("命中",dict(need),flush=True)
    jobs=[(o,s,r) for o,s,c in hits for r in (-1,TAB[c])]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(ev,jobs,chunksize=2))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(o,s,c)][r]=m
    byc=collections.defaultdict(lambda:[0,0,0])
    for (o,s,c),v in per.items():
        rid=TAB[c]
        if rid not in v or -1 not in v: continue
        x=byc[c]; x[0]+=v[rid]>0; x[1]+=v[-1]>0; x[2]+=1
    for c,x in sorted(byc.items()):
        mark="安全" if x[0]>=x[1] else "冲突劣"
        print(f"  [{mark}] {c:30s} 带{TAB[c]:3d} 新值{x[0]}/{x[2]} 现行为{x[1]}/{x[2]}")
