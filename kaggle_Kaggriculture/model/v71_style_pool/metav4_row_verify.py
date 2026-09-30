"""metav4 行定向复验:seed10600-10719 扫描,命中 2 候选格即评双路线。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
TAB={"PIZZA_SHOP|BRUNCH_SPOT":126,"ICE_CREAM_SHOP|BAKERY":110}
def play(seed,rid,stop=False):
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/w48fr_main.py")
    op=fidelity.make_agent(f"sub:{HERE}/agents/metav4_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; combo=None
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
        if t==146:
            combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo,None
    return combo,float(g.reward(0)-g.reward(1))
def scan(s):
    try: return s,play(s,-1,stop=True)[0]
    except Exception: return s,None
def ev(job):
    s,r=job
    try:
        c,m=play(s,r); return s,r,c,m
    except Exception: return s,r,None,None
if __name__=="__main__":
    with ProcessPoolExecutor(7) as ex: sc=list(ex.map(scan,range(10600,10720),chunksize=4))
    hits=[(s,c) for s,c in sc if c in TAB]
    print("命中",len(hits),collections.Counter(c for _,c in hits),flush=True)
    jobs=[(s,r) for s,c in hits for r in (-1,TAB[c])]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(ev,jobs,chunksize=2))
    per=collections.defaultdict(dict)
    for s,r,c,m in res:
        if m is not None: per[(s,c)][r]=m
    byc=collections.defaultdict(lambda:[0,0,0])
    for (s,c),v in per.items():
        rid=TAB[c]
        if rid not in v or -1 not in v: continue
        x=byc[c]; x[0]+=v[rid]>0; x[1]+=v[-1]>0; x[2]+=1
    for c,x in sorted(byc.items()):
        mark="进" if x[0]>x[1] else "弃"
        print(f"  [{mark}] {c:34s} 表{x[0]}/{x[2]} 基线{x[1]}/{x[2]}")
