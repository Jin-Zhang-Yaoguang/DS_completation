"""herdsafe 表内改值:9 个候选格 × 13 候选带 × herdsafe 索引 5 seed,与现值对比。"""
import sys, os, json, collections, re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
s=open(HERE/"agents/v54r17_main.py",encoding="utf-8").read()
l=s.find("_V54R3_MIR = {"); hs=s.find("_V54R3_HS = {")
MIR=dict((f"{a}|{b}",int(r)) for a,b,r in re.findall(r'\("([A-Z_]+)","([A-Z_]+)"\):\s*(\d+)', s[l:hs]))
TG=json.load(open(HERE/"hs_reval_targets.json"))
CAND=[0,100,101,103,107,110,112,115,118,120,123,124,126]
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
    jobs=[(c,s2,r) for c in TG for s2 in IHS.get(c,[])[:5] for r in sorted(set(CAND+[MIR[c]]))]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"hs_reval.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s2,r,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    draft={}
    for c in TG:
        rows=agg[c]; cur=MIR[c]
        if cur not in rows: continue
        cw,cn,cm=rows[cur]
        best=max(rows.items(), key=lambda kv:(kv[1][0],kv[1][2]))
        flag = best[0]!=cur and best[1][0]>cw
        if flag: draft[c]=best[0]
        print(f"[{'改' if flag else '留'}] {c:30s} 现{cur:4d} {cw}/{cn}({cm/max(1,cn):+.0f}) -> 最优{best[0]:4d} {best[1][0]}/{best[1][1]}({best[1][2]/max(1,best[1][1]):+.0f})")
    json.dump(draft, open(HERE/"hs_reval_draft.json","w"))
    print("改值候选", len(draft))
