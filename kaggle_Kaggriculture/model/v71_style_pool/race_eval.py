"""RACE 窗口参数评估:v54r3{,w48,w60,w72} × 7 对手 × 8 seed 配对。"""
import sys, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
DB = M/"v58_mosaic"/"dist_backup"
VERS = ["v54r3","v54r3w48","v54r3w60","v54r3w72"]
OPPS = {"v55":None,"v56":None,"busya_race":None,"guru_v4":None,"metav4":None}
OPPS = {k: str(HERE/f"agents/{k}_main.py") for k in OPPS}
OPPS["y68i"]=f"{DB}/y68i_main.py"; OPPS["y68s2"]=f"{DB}/y68s2_main.py"
def one(job):
    ver, oname, seed = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        op=fidelity.make_agent(f"sub:{OPPS[oname]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return ver,oname,seed,float(g.reward(0)-g.reward(1))
    except Exception as e:
        return ver,oname,seed,None
if __name__=="__main__":
    jobs=[(v,o,s) for v in VERS for o in OPPS for s in range(10100,10108)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    per=collections.defaultdict(dict)
    for v,o,s,m in res:
        if m is not None: per[(o,s)][v]=m
    for v in VERS:
        w=collections.defaultdict(lambda:[0,0])
        dd=[]
        for (o,s),d in per.items():
            if v in d and "v54r3" in d:
                w[o][0]+=d[v]>0; w[o][1]+=1
                if v!="v54r3": dd.append(d[v]-d["v54r3"])
        line=" ".join(f"{o}:{x[0]}/{x[1]}" for o,x in sorted(w.items()))
        extra=f" 配对差中位 {statistics.median(dd):+.0f}" if dd else ""
        print(f"{v:10s} {line}{extra}")
