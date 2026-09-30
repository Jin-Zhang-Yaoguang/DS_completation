"""K52 拼接留出复验:19 格 × v52/v53 × 索引 seeds[2:8](选值用了[:2])× {不切, 拼接}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v52"]
D=json.load(open(HERE/"k52_splice_draft.json"))
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
        return c,opp,cut,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,opp,cut,None
if __name__=="__main__":
    jobs=[]
    for c,(cut,rid,_,_) in D.items():
        for opp in ("v52","v53"):
            for s in IDX.get(c,[])[2:8]:
                jobs.append((c,opp,s,None,-1)); jobs.append((c,opp,s,cut,rid))
    print("K52 留出 格",len(D),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    per=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,cut,m in res:
        if m is None: continue
        a=per[c][("s" if cut else "b",opp)]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,(cut,rid,_,_) in sorted(D.items()):
        p=per[c]
        sw=sum(p[("s",o)][0] for o in ("v52","v53")); bw=sum(p[("b",o)][0] for o in ("v52","v53"))
        n=sum(p[("s",o)][1] for o in ("v52","v53"))
        dm=sum(p[("s",o)][2]-p[("b",o)][2] for o in ("v52","v53"))/max(1,n)
        safe=all(p[("s",o)][0]>=p[("b",o)][0] for o in ("v52","v53"))
        ok = n>=6 and safe and (sw>bw or (sw==bw and dm>0))
        if ok: final[c]=[cut,rid]
        print(f"[{'进' if ok else '弃'}] {c:30s} t{cut}->{rid:3d}  拼接 {sw}/{n} vs 不切 {bw}/{n}  均差提升 {dm:+7.0f}")
    json.dump(final, open(HERE/"k52_splice_final.json","w"))
    print("终进", len(final))
