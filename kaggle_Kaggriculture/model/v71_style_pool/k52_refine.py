"""K52 行格值精炼:7 格 × 候选带 × 索引(v52族)seeds × {v52,v53},配对口径。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v52"]
CUR={"BRUNCH_SPOT|YARN_STORE":103,"PIZZA_SHOP|ICE_CREAM_SHOP":107,"BRUNCH_SPOT|BRUNCH_SPOT":110,
     "PET_CAFE|BAKERY":124,"PIZZA_SHOP|SMOOTHIE_SHOP":120,"PIZZA_SHOP|YARN_STORE":126,
     "YARN_STORE|SMOOTHIE_SHOP":126}
SHORT=[0,100,101,103,107,110,111,112,115,118,120,123,124,126]
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
    for c,cur in CUR.items():
        for s in IDX.get(c,[])[:5]:
            for r in sorted(set(SHORT+[cur])):
                for o in OPPS: jobs.append((c,s,r,o))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"k52_refine.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,o,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c,cur in sorted(CUR.items()):
        rows=agg[c]
        if cur not in rows: print(f"[?] {c} 无数据"); continue
        cw,cn,cm=rows[cur]
        best=max(rows.items(), key=lambda kv:(kv[1][0], kv[1][2]))
        bw,bn,bm=best[1]
        flag="改" if (best[0]!=cur and bw>cw) else "留"
        if flag=="改": draft[c]=best[0]
        print(f"[{flag}] {c:30s} 现{cur:4d} {cw}/{cn}({cm/max(1,cn):+.0f}) -> 最优{best[0]:4d} {bw}/{bn}({bm/max(1,bn):+.0f})")
    json.dump(draft, open(HERE/"k52_refine_draft.json","w"))
    print("改值格:", len(draft))
