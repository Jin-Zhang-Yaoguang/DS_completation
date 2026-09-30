"""r5 vs r5w48 配对:4 对手 × 8 seed。"""
import sys, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
OPPS=["rescue7","v56","v55","busya_race"]
def one(job):
    ver,o,s=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=s)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return ver,o,s,float(g.reward(0)-g.reward(1))
    except Exception as e: return ver,o,s,None
if __name__=="__main__":
    jobs=[(v,o,s) for v in ("v54r5","v54r5w48") for o in OPPS for s in range(11200,11208)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    per=collections.defaultdict(dict)
    for v,o,s,m in res:
        if m is not None: per[(o,s)][v]=m
    for v in ("v54r5","v54r5w48"):
        w=collections.defaultdict(lambda:[0,0]); dd=[]
        for (o,s),d in per.items():
            if v in d: w[o][0]+=d[v]>0; w[o][1]+=1
            if v=="v54r5w48" and "v54r5" in d and v in d: dd.append(d[v]-d["v54r5"])
        line=" ".join(f"{o}:{x[0]}/{x[1]}" for o,x in sorted(w.items()))
        extra=f" 配对差中位 {statistics.median(dd):+.0f}" if dd else ""
        print(f"{v:10s} {line}{extra}")
