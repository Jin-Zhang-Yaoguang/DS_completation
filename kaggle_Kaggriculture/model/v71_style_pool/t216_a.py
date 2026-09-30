"""t216 工程·A:r6 vs rescue7 按组合找输格(索引 seeds[0:2])。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
def one(job):
    seed,combo=job
    os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r6fr2_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return seed,combo,float(g.reward(0)-g.reward(1))
    except Exception as e: return seed,combo,None
if __name__=="__main__":
    jobs=[(s,c) for c,ss in IDX.items() for s in ss[:2]]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"t216_a.json","w"))
    byc=collections.defaultdict(lambda:[0,0])
    for s,c,m in res:
        if m is None: continue
        byc[c][0]+=m>0; byc[c][1]+=1
    losers=[c for c,x in byc.items() if x[0]<x[1]]
    W=sum(x[0] for x in byc.values()); N=sum(x[1] for x in byc.values())
    print(f"总 {W}/{N};输格 {len(losers)}")
    for c in sorted(losers): print(" ", c, byc[c])
