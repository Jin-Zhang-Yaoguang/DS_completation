"""K52 键拼接搜索:目标格 × {v52, v53} × 2 seed × {不切, t288/t360/t432/t504 × 9 候选}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v52"]
TG=json.load(open(HERE/"k52_splice_targets.json"))
CAND=[0,100,101,103,107,110,112,120,126]
ARMS=[(None,-1)]+[(c,r) for c in (288,360,432,504) for r in CAND]
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
        return c,opp,cut,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,opp,cut,rid,None
if __name__=="__main__":
    jobs=[(c,opp,s,cut,rid) for c in TG for opp in ("v52","v53") for s in IDX.get(c,[])[:2] for cut,rid in ARMS]
    print("K52 拼接 任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"k52_splice.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,cut,rid,m in res:
        if m is None: continue
        a=agg[c][(cut,rid)]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c in TG:
        rows=agg[c]; b=rows.get((None,-1),[0,0,0.0])
        (cut,rid),(w,n,mm)=max(rows.items(), key=lambda kv:(kv[1][0],kv[1][2]))
        gain=(mm-b[2])/max(1,n)
        if cut is not None and (w>b[0] or (w==b[0] and gain>=500)):
            draft[c]=[cut,rid,w-b[0],round(gain)]
            print(f"  {c:32s} 不切{b[0]}/{b[1]} -> t{cut}切{rid:3d} {w}/{n} 均差提升{gain:+6.0f}")
    json.dump(draft, open(HERE/"k52_splice_draft.json","w"))
    print("入围", len(draft))
