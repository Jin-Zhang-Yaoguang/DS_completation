"""t150 判别表:t216 表内 10 组合 × {v54,v55,v56,busya_race,rescue7} × 2 seed,记对手 t150/t160 现金。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
T216=json.load(open(HERE/"t216_final.json"))
FAMS=["v54","v55","v56","busya_race","rescue7"]
def one(job):
    fam,seed,combo=job
    os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r6fr2_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{fam}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); marks={}
        for t in range(161):
            obs=[g.observe(0),g.observe(1)]
            if t in (150,160): marks[t]=round(float(obs[0]["farms"][1]["money"]),2)
            g.step(me(obs[0]),op(obs[1]))
        return fam,seed,combo,marks
    except Exception as e: return fam,seed,combo,None
if __name__=="__main__":
    jobs=[(f,s,c) for c in T216 for s in IDX[c][:2] for f in FAMS]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    by=collections.defaultdict(lambda:collections.defaultdict(set))
    for f,s,c,mk in res:
        if mk: by[c][("r7" if f=="rescue7" else "v5x")].add((mk[150],mk[160]))
    disc={}
    for c,d in sorted(by.items()):
        r7=d.get("r7",set()); v5=d.get("v5x",set())
        sep = not (r7 & v5)
        print(f"{c:34s} rescue7 {sorted(r7)} | V5x {len(v5)}值 分离={sep}")
        if sep and len(r7)==1: disc[c]=list(list(r7)[0])
    json.dump(disc, open(HERE/"t150_disc.json","w"))
    print("可判别格", len(disc), "/", len(by))
