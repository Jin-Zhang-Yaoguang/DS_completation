"""herdsafe 表外格补格·选值:9 个 0/2 全负格 + 1 个重负格,vs herdsafe。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
TARGETS=["SMOOTHIE_SHOP|PET_CAFE","FARMERS_MARKET|BRUNCH_SPOT","PET_CAFE|FARMERS_MARKET",
 "ICE_CREAM_SHOP|SMOOTHIE_SHOP","BAKERY|PET_CAFE","FARMERS_MARKET|PIZZA_SHOP",
 "FARMERS_MARKET|YARN_STORE","YARN_STORE|ICE_CREAM_SHOP","YARN_STORE|BAKERY","YARN_STORE|BRUNCH_SPOT"]
CAND=[-1,0,100,101,103,107,110,111,112,115,118,120,123,124,126]
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
        return c,seed,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,seed,rid,None
if __name__=="__main__":
    jobs=[(c,s,r) for c in TARGETS for s in IDX.get(c,[])[:5] for r in CAND]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"hsfix_sel.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c in TARGETS:
        rows=agg[c]
        if not rows: print(f"{c:32s} 无数据"); continue
        bw,bn,bm=rows.get(-1,[0,0,0.0])
        ok=[(r,v) for r,v in rows.items() if r!=-1 and v[0]>=max(3,bw+1)]
        if not ok: print(f"{c:32s} 基线 {bw}/{bn} -> 无合格候选"); continue
        best=max(ok,key=lambda kv:(kv[1][0],kv[1][2]))
        draft[c]=best[0]
        print(f"{c:32s} 基线 {bw}/{bn}({bm/max(1,bn):+.0f}) -> 带{best[0]:4d} {best[1][0]}/{best[1][1]}({best[1][2]/max(1,best[1][1]):+.0f})")
    json.dump(draft, open(HERE/"hsfix_draft.json","w"))
    print("入围", len(draft))
