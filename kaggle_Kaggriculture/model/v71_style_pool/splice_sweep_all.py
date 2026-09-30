"""拼接全组合普查(一阶段粗筛):60 个组合 × {rescue7, herdsafe} × 1 seed × 28 臂。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IR7=json.load(open(HERE/"combo_index.json"))["v54"]
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
DONE=set(json.load(open(HERE/"splice_final.json")))
CAND=[0,100,101,107,110,112,120,124,126]
ARMS=[(None,-1)]+[(c,r) for c in (360,432,504) for r in CAND]
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
    combos=sorted(set(IR7)&set(IHS)-DONE)
    jobs=[]
    for c in combos:
        for opp,idx in (("rescue7",IR7),("herdsafe",IHS)):
            s=idx[c][0]
            for cut,rid in ARMS: jobs.append((c,opp,s,cut,rid))
    print("组合",len(combos),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"splice_sweep_all.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,cut,rid,m in res:
        if m is None: continue
        a=agg[c][(cut,rid)]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c in combos:
        rows=agg[c]; b=rows.get((None,-1),[0,0,0.0])
        best=max(rows.items(), key=lambda kv:(kv[1][0],kv[1][2]))
        (cut,rid),(w,n,mm)=best
        gain=(mm-b[2])/max(1,n)
        if cut is not None and (w>b[0] or (w==b[0] and gain>=500)):
            draft[c]=[cut,rid,w-b[0],round(gain)]
    for c,v in sorted(draft.items(), key=lambda kv:(-kv[1][2],-kv[1][3])):
        print(f"  {c:32s} t{v[0]}->{v[1]:3d}  胜差{v[2]:+d} 均差提升{v[3]:+6d}")
    json.dump(draft, open(HERE/"splice_sweep_draft.json","w"))
    print("入围", len(draft))
