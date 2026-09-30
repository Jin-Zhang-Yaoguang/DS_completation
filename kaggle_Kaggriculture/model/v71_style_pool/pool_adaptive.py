"""池化是否优于池内任一固定带:BRUNCH|PET 格全 seed × 3 子族 × {基线,107,110,112,120,池化}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
CELL="BRUNCH_SPOT|PET_CAFE"
SEEDS=IDX[CELL]
OPPS=["v54","v56","rescue7","v55","busya_race"]
ARMS=[("fix",-1),("fix",107),("fix",110),("fix",112),("fix",120),("pool",None)]
def one(job):
    kind,rid,o,seed=job
    os.environ.pop("KAG_FORCE_ROUTE2",None)
    if kind=="pool":
        os.environ.pop("KAG_FORCE_ROUTE",None)
        ver="v54r9b"
    else:
        os.environ["KAG_FORCE_ROUTE"]=str(rid)
        ver="r5fr"   # fr 探针版可强制固定带
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return kind,rid,o,seed,float(g.reward(0)-g.reward(1))
    except Exception as e: return kind,rid,o,seed,None
if __name__=="__main__":
    jobs=[(k,r,o,s) for (k,r) in ARMS for o in OPPS for s in SEEDS]
    print(f"{CELL}: seeds={len(SEEDS)} 任务={len(jobs)}",flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:[0,0,0.0])
    for k,r,o,s,m in res:
        if m is None: continue
        key=("池化" if k=="pool" else ("基线" if r==-1 else f"固定{r}"))
        a=agg[key]; a[0]+= m>0; a[1]+=1; a[2]+=m
    for key,a in sorted(agg.items(), key=lambda kv:-kv[1][0]):
        print(f"  {key:8s} {a[0]:3d}/{a[1]:3d} 胜  均分差 {a[2]/max(1,a[1]):+8.0f}")
