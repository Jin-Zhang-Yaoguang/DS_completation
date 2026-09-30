"""轴4 基建:seed→组合索引。r5fr(-1) vs {v54(镜像族通用), v52(K52族)},t146 止。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    fam,seed=job
    os.environ["KAG_FORCE_ROUTE"]="-1"
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{fam}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        for t in range(146):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
        return fam,seed,combo
    except Exception as e:
        return fam,seed,f"ERR{type(e).__name__}"
if __name__=="__main__":
    jobs=[(f,s) for f in ("herdsafe",) for s in range(16000,16700)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=6))
    idx=collections.defaultdict(lambda:collections.defaultdict(list))
    for f,s,c in res:
        if isinstance(c,str) and not c.startswith("ERR"): idx[f][c].append(s)
    json.dump({f:{c:v for c,v in d.items()} for f,d in idx.items()}, open(HERE/"combo_index_hs.json","w"))
    for f,d in idx.items():
        sizes=sorted(((len(v),c) for c,v in d.items()), reverse=True)
        print(f"{f}: 组合数 {len(d)},局数 {sum(len(v) for v in d.values())}")
        print("  最少样本的组合:", [(c,n) for n,c in sizes[-8:]])
