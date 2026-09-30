"""metav4 键(1049)拼接粗筛:64 组合 × metav4 × 1 seed × {不切, t144 整带×13, t288/360/432/504 切×9}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index_mv4.json"))["metav4"]
SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
CAND=[0,100,101,103,107,110,112,120,126]
ARMS=[(None,-1)]+[(144,r) for r in SHORT]+[(c,r) for c in (288,360,432,504) for r in CAND]
def one(job):
    c,seed,cut,rid=job
    for k in list(os.environ):
        if k.startswith("KAG_CUT") or k.startswith("KAG_FORCE"): os.environ.pop(k,None)
    if cut: os.environ[f"KAG_CUT{cut}"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r19cut_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/metav4_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,cut,rid,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,cut,rid,None
if __name__=="__main__":
    jobs=[(c,ss[0],cut,rid) for c,ss in sorted(IDX.items()) for cut,rid in ARMS]
    print("组合",len(IDX),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"mv4_splice.json","w"))
    agg=collections.defaultdict(dict)
    for c,cut,rid,m in res:
        if m is not None: agg[c][(cut,rid)]=m
    bw=sum(1 for c in agg if agg[c].get((None,-1),0)>0)
    print(f"不切基线胜 {bw}/{len(agg)}")
    draft={}
    for c,rows in sorted(agg.items()):
        b=rows.get((None,-1),0)
        (cut,rid),m=max(rows.items(), key=lambda kv:kv[1])
        if cut is not None and ((m>0 and b<=0) or m-b>=800):
            draft[c]=[cut,rid,round(b),round(m)]
    for c,v in sorted(draft.items(), key=lambda kv:-(kv[1][3]-kv[1][2])):
        print(f"  {c:32s} 基{v[2]:+7d} -> t{v[0]}->{v[1]:3d} {v[3]:+7d}")
    json.dump(draft, open(HERE/"mv4_splice_draft.json","w"))
    print("入围", len(draft))
