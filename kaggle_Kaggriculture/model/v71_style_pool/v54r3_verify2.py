"""v54r3 质检①b:补验缺证据格子(更大 seed 池)+ V52/53 键行 on V56。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
NEED = {"SMOOTHIE_SHOP|FARMERS_MARKET":110, "BAKERY|SMOOTHIE_SHOP":110, "SMOOTHIE_SHOP|ICE_CREAM_SHOP":107}
R1 = {"BRUNCH_SPOT|YARN_STORE":103, "SMOOTHIE_SHOP|FARMERS_MARKET":110, "PIZZA_SHOP|ICE_CREAM_SHOP":107}
def play(opp, seed, rid, stop=False):
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/v56fr_main.py")
    op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; combo=None
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
        if t==146:
            combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo,None
    return combo, float(g.reward(0)-g.reward(1))
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
    # A) 镜像键缺证据格:v55/v56/busya_race × seed 9960-10079
    jobsA=[(o,s) for o in ("v55","v56","busya_race") for s in range(9960,10080)]
    # B) V52/53 键行:v52/v53 × seed 9900-9979
    jobsB=[(o,s) for o in ("v52","v53") for s in range(9900,9980)]
    with ProcessPoolExecutor(7) as ex: sc=list(ex.map(scan,jobsA+jobsB,chunksize=4))
    hits=[]
    for o,s,c in sc:
        if c is None: continue
        if o in ("v52","v53") and c in R1: hits.append((o,s,c,R1[c]))
        elif o not in ("v52","v53") and c in NEED: hits.append((o,s,c,NEED[c]))
    print("扫描",len(sc),"命中",len(hits),flush=True)
    jobs=[(o,s,r) for o,s,c,rid in hits for r in (-1,rid)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(ev,jobs,chunksize=2))
    json.dump([list(r) for r in res],open(HERE/"v54r3_verify2.json","w"))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(o,s,c)][r]=m
    byc=collections.defaultdict(lambda:[0,0,0])
    for (o,s,c),v in per.items():
        rid=R1[c] if (o in("v52","v53")) else NEED[c]
        key=("R1行" if o in("v52","v53") else "镜像行")+" "+c
        if rid not in v or -1 not in v: continue
        x=byc[key]; x[0]+=v[rid]>0; x[1]+=v[-1]>0; x[2]+=1
    for c,x in sorted(byc.items()):
        print(f"  {c:44s} 表{x[0]}/{x[2]} 原生{x[1]}/{x[2]}")
