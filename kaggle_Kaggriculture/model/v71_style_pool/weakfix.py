"""弱项补格·选值:对 rescue7 全负/重负的表外格,候选带 × 索引 seeds[:4] × rescue7。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
IDX2=json.load(open(HERE/"combo_index2.json"))["v54"]
TARGETS=["SMOOTHIE_SHOP|BRUNCH_SPOT","SMOOTHIE_SHOP|PET_CAFE","FARMERS_MARKET|BRUNCH_SPOT",
 "BAKERY|SMOOTHIE_SHOP","PET_CAFE|BRUNCH_SPOT","PIZZA_SHOP|PET_CAFE","BAKERY|BRUNCH_SPOT",
 "PIZZA_SHOP|PIZZA_SHOP","YARN_STORE|BRUNCH_SPOT","PET_CAFE|ICE_CREAM_SHOP",
 "PIZZA_SHOP|SMOOTHIE_SHOP","SMOOTHIE_SHOP|PIZZA_SHOP"]
CAND=[-1,0,100,101,103,107,110,111,112,115,118,120,123,124,126]
def one(job):
    c,seed,rid=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,seed,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,seed,rid,None
if __name__=="__main__":
    jobs=[]
    for c in TARGETS:
        seeds=(IDX.get(c,[])[:3]+IDX2.get(c,[])[:2])
        for s in seeds:
            for r in CAND: jobs.append((c,s,r))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"weakfix_sel.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c in TARGETS:
        rows=agg[c]
        if not rows: continue
        bw,bn,bm=rows.get(-1,[0,0,0.0])
        best=max(((r,v) for r,v in rows.items() if r!=-1), key=lambda kv:(kv[1][0], kv[1][2]))
        if best[1][0]>bw or (best[1][0]==bw and best[1][2]>bm and bw<bn):
            draft[c]=best[0]
        print(f"{c:32s} 基线 {bw}/{bn}({bm/max(1,bn):+.0f}) -> 带{best[0]:4d} {best[1][0]}/{best[1][1]}({best[1][2]/max(1,best[1][1]):+.0f}) {'入围' if c in draft else ''}")
    json.dump(draft, open(HERE/"weakfix_draft.json","w"))
    print("入围", len(draft))
