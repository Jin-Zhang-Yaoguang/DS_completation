"""轴4 标准评测集:64 组合 × 固定 2 seed × 4 对手 = 512 局配对评测。
用法: python bench.py <版本名>  (agents/<版本>_main.py);结果存 bench_<版本>.json"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
import os as _o
IDX=json.load(open(HERE/_o.environ.get("BENCH_INDEX","combo_index.json")))
OPPS=["v54","v56","rescue7","v52","metav4","herdsafe"]
def build():
    jobs=[]
    for o in OPPS:
        fam="v52" if o=="v52" else "v54"  # metav4 开局同 V54 系,沿用 v54 索引
        for c,seeds in sorted(IDX[fam].items()):
            for s in seeds[:2]: jobs.append((o,s,c))
    return jobs
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
        return o,seed,combo,float(g.reward(0)-g.reward(1))
    except Exception as e: return o,seed,combo,None
if __name__=="__main__":
    ver=sys.argv[1]
    jobs=[(ver,o,s,c) for (o,s,c) in build()]
    print(f"{ver}: 评测 {len(jobs)} 局",flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/f"bench_{ver}{_o.environ.get('BENCH_TAG','')}.json","w"))
    byo=collections.defaultdict(lambda:[0,0,0.0])
    for o,s,c,m in res:
        if m is None: continue
        a=byo[o]; a[0]+= m>0; a[1]+=1; a[2]+=m
    T=[0,0,0.0]
    for o,a in sorted(byo.items()):
        T[0]+=a[0]; T[1]+=a[1]; T[2]+=a[2]
        print(f"  vs {o:9s} {a[0]:3d}/{a[1]:3d} ({a[0]/max(1,a[1]):5.1%}) 均分差 {a[2]/max(1,a[1]):+8.0f}")
    print(f"  合计 {T[0]}/{T[1]} ({T[0]/max(1,T[1]):.1%}) 均分差 {T[2]/max(1,T[1]):+.0f}")
