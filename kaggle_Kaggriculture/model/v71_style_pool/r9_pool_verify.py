"""r9 池化验证:5 池化格 × 索引 seeds × {v54,v56,rescue7},r8c 单值 vs r9 池化;并统计选带分布。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
CELLS=["BRUNCH_SPOT|PET_CAFE","ICE_CREAM_SHOP|YARN_STORE","PET_CAFE|SMOOTHIE_SHOP",
       "SMOOTHIE_SHOP|BAKERY","SMOOTHIE_SHOP|YARN_STORE"]
OPPS=["v54","v56","rescue7"]
def one(job):
    ver,o,seed,combo=job
    os.environ.pop("KAG_FORCE_ROUTE",None); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return ver,o,seed,combo,float(g.reward(0)-g.reward(1))
    except Exception as e: return ver,o,seed,combo,None
if __name__=="__main__":
    jobs=[]
    for c in CELLS:
        for s in IDX[c][:6]:
            for o in OPPS:
                for v in ("v54r8c","v54r9"): jobs.append((v,o,s,c))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    per=collections.defaultdict(dict)
    for v,o,s,c,m in res:
        if m is not None: per[(c,o,s)][v]=m
    byc=collections.defaultdict(lambda:[0,0,0])
    for (c,o,s),d in per.items():
        if "v54r8c" not in d or "v54r9" not in d: continue
        x=byc[c]; x[0]+= d["v54r9"]>0; x[1]+= d["v54r8c"]>0; x[2]+=1
    T=[0,0,0]
    for c,x in sorted(byc.items()):
        T[0]+=x[0]; T[1]+=x[1]; T[2]+=x[2]
        mark="OK" if x[0]>=x[1] else "劣"
        print(f"  [{mark}] {c:30s} 池化{x[0]}/{x[2]} 单值{x[1]}/{x[2]}")
    print(f"合计: 池化 {T[0]}/{T[2]} | 单值 {T[1]}/{T[2]}")
