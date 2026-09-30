"""切点拼接搜索:9 个真实亏损格 × {rescue7, herdsafe} × 3 seed × {不切, t360切×13, t432切×13}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IR7=json.load(open(HERE/"combo_index.json"))["v54"]
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
CELLS=["YARN_STORE|BAKERY","SMOOTHIE_SHOP|PET_CAFE","FARMERS_MARKET|BRUNCH_SPOT","FARMERS_MARKET|YARN_STORE",
       "FARMERS_MARKET|PIZZA_SHOP","YARN_STORE|BRUNCH_SPOT","PIZZA_SHOP|PET_CAFE","PET_CAFE|SMOOTHIE_SHOP",
       "ICE_CREAM_SHOP|SMOOTHIE_SHOP"]
SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
ARMS=[(None,-1)]+[(360,r) for r in SHORT]+[(432,r) for r in SHORT]
def one(job):
    c,opp,seed,cut,rid=job
    for k in list(os.environ):
        if k.startswith("KAG_CUT") or k.startswith("KAG_FORCE"): os.environ.pop(k,None)
    if cut: os.environ[f"KAG_CUT{cut}"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r19cut_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,opp,seed,cut,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,opp,seed,cut,rid,None
if __name__=="__main__":
    jobs=[]
    for c in CELLS:
        for opp,idx in (("rescue7",IR7),("herdsafe",IHS)):
            for s in idx.get(c,[])[:3]:
                for cut,rid in ARMS: jobs.append((c,opp,s,cut,rid))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"splice_search.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,s,cut,rid,m in res:
        if m is None: continue
        a=agg[c][(cut,rid)]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c in CELLS:
        rows=agg[c]; b=rows.get((None,-1),[0,0,0.0])
        best=max(rows.items(), key=lambda kv:(kv[1][0],kv[1][2]))
        (cut,rid),(w,n,mm)=best
        ok = cut is not None and w>b[0]
        if ok: draft[c]=[cut,rid]
        print(f"[{'入围' if ok else '  '}] {c:30s} 不切 {b[0]}/{b[1]}({b[2]/max(1,b[1]):+6.0f}) -> "
              f"{'t'+str(cut) if cut else '不切'}切{rid:4d} {w}/{n}({mm/max(1,n):+6.0f})")
    json.dump(draft, open(HERE/"splice_draft.json","w"))
    print("入围", len(draft))
