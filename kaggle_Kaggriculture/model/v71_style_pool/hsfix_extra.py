"""补测 2 个样本不足格:PET_CAFE|FM(124)、FM|BRUNCH(101),herdsafe 扩样本。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
PAIR={"PET_CAFE|FARMERS_MARKET":124,"FARMERS_MARKET|BRUNCH_SPOT":101}
def one(job):
    c,seed,rid=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/herdsafe_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,rid,None
if __name__=="__main__":
    jobs=[]
    for c,new in PAIR.items():
        seeds=IHS.get(c,[])
        print(f"{c}: 索引 {len(seeds)} seed")
        for s in seeds:  # 全部 seed
            jobs.append((c,s,-1)); jobs.append((c,s,new))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,r,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    extra={}
    for c,new in PAIR.items():
        bw,bn,bm=agg[c].get(-1,[0,0,0.0]); nw,nn,nm=agg[c].get(new,[0,0,0.0])
        ok = nn>=5 and nw>bw
        if ok: extra[c]=new
        print(f"[{'进' if ok else '弃'}] {c:30s} 带{new} herdsafe 基线{bw}/{bn}({bm/max(1,bn):+.0f}) 新{nw}/{nn}({nm/max(1,nn):+.0f})")
    json.dump(extra, open(HERE/"hsfix_extra.json","w"))
