"""herdsafe 改值留出复验:6 格 × 现值/新值 × herdsafe 索引 seeds[5:],需 >=5 局且胜局提升。"""
import sys, os, json, collections, re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
s=open(HERE/"agents/v54r17_main.py",encoding="utf-8").read()
l=s.find("_V54R3_MIR = {"); hs=s.find("_V54R3_HS = {")
MIR=dict((f"{a}|{b}",int(r)) for a,b,r in re.findall(r'\("([A-Z_]+)","([A-Z_]+)"\):\s*(\d+)', s[l:hs]))
NEW=json.load(open(HERE/"hs_reval_draft.json"))
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
    for c,new in NEW.items():
        sd=IHS.get(c,[])[5:]
        print(f"  {c}: 留出 {len(sd)} seed")
        for s2 in sd:
            jobs.append((c,s2,MIR[c])); jobs.append((c,s2,new))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,r,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,new in sorted(NEW.items()):
        cw,cn,cm=agg[c].get(MIR[c],[0,0,0.0]); nw,nn,nm=agg[c].get(new,[0,0,0.0])
        ok = nn>=5 and nw>cw
        if ok: final[c]=new
        print(f"[{'进' if ok else ('样本不足' if nn<5 else '弃')}] {c:30s} 现{MIR[c]:4d} {cw}/{cn}({cm/max(1,cn):+.0f}) | 新{new:4d} {nw}/{nn}({nm/max(1,nn):+.0f})")
    json.dump(final, open(HERE/"hs_reval_final.json","w"))
    print("终进", len(final))
