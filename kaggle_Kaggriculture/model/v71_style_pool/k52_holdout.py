"""K52 改值格留出复验:seeds[5:] × {v52,v53},现值 vs 新值。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v52"]
PAIR={"BRUNCH_SPOT|BRUNCH_SPOT":(110,101),"BRUNCH_SPOT|YARN_STORE":(103,126)}
OPPS=["v52","v53"]
def one(job):
    c,seed,rid,o=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,seed,rid,o,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,seed,rid,o,None
if __name__=="__main__":
    jobs=[]
    for c,(cur,new) in PAIR.items():
        for s in IDX[c][5:]:
            for o in OPPS:
                jobs.append((c,s,cur,o)); jobs.append((c,s,new,o))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,o,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,(cur,new) in sorted(PAIR.items()):
        cw,cn,cm=agg[c].get(cur,[0,0,0.0]); nw,nn,nm=agg[c].get(new,[0,0,0.0])
        ok = nn>0 and nw>=cw and nm>cm
        final[c]=new if ok else cur
        print(f"[{'改' if ok else '留'}] {c:30s} 现{cur:4d} {cw}/{cn}({cm/max(1,cn):+.0f}) | 新{new:4d} {nw}/{nn}({nm/max(1,nn):+.0f})")
    json.dump(final, open(HERE/"k52_final.json","w"))
