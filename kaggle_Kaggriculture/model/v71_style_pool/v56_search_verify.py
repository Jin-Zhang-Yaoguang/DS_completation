"""⑥ 留出复验:seed10300-10379 × 4 对手,命中草案格 → 草案 vs 基线,胜负优先。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
TAB = json.load(open(HERE/"v56_search_draft.json"))
OPPS = ["v56","v55","busya_race","metav4"]
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
    with ProcessPoolExecutor(7) as ex:
        sc=list(ex.map(scan,[(o,s) for o in OPPS for s in range(10300,10380)],chunksize=4))
    hits=[(o,s,c) for o,s,c in sc if c in TAB]
    print("扫描",len(sc),"命中",len(hits),flush=True)
    jobs=[(o,s,r) for o,s,c in hits for r in (-1,TAB[c])]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(ev,jobs,chunksize=2))
    json.dump([list(r) for r in res],open(HERE/"v56_verify.json","w"))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(o,s,c)][r]=m
    byc=collections.defaultdict(lambda:[0,0,0]); N=W=BW=0
    for (o,s,c),v in per.items():
        rid=TAB[c]
        if rid not in v or -1 not in v: continue
        N+=1; W+=v[rid]>0; BW+=v[-1]>0
        x=byc[c]; x[0]+=v[rid]>0; x[1]+=v[-1]>0; x[2]+=1
    print(f"复验 {N} 局: 草案 {W} 胜 | 基线 {BW} 胜")
    for c,x in sorted(byc.items(),key=lambda kv:kv[1][0]-kv[1][1]):
        mark = "进" if x[0]>x[1] else "弃"
        print(f"  [{mark}] {c:34s} 路线{TAB[c]:4d} 草案{x[0]}/{x[2]} 基线{x[1]}/{x[2]}")
