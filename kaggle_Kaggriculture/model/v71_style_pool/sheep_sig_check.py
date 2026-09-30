"""五已知子族在 PIZZA|ICE 组合下的 t150/t160 签名(核对与 Sheep 不撞)。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
SEEDS=IDX["PIZZA_SHOP|ICE_CREAM_SHOP"][:2]
FAMS=["v54","v55","v56","busya_race","rescue7"]
def one(job):
    fam,seed=job
    os.environ.pop("KAG_FORCE_ROUTE2",None); os.environ["KAG_FORCE_ROUTE"]="-1"
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{fam}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); marks={}
        for t in range(161):
            obs=[g.observe(0),g.observe(1)]
            if t in (150,160): marks[t]=round(float(obs[0]["farms"][1]["money"]),2)
            g.step(me(obs[0]),op(obs[1]))
        return fam,seed,(marks[150],marks[160])
    except Exception as e: return fam,seed,f"ERR{type(e).__name__}"
if __name__=="__main__":
    jobs=[(f,s) for f in FAMS for s in SEEDS]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    by=collections.defaultdict(set)
    for f,s,sig in res: by[f].add(sig)
    for f,v in by.items(): print(f"{f:12s} {sorted(v)}")
