"""镜像键拼接留出复验(第二批):普查 + t288 入围格,每格至多 2 个候选臂 + 基线;
rescue7(索引2) 6 seed、herdsafe 6 seed、v56(索引2) 4 seed;三族合计胜局提升且无一族少赢。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IR7b=json.load(open(HERE/"combo_index2.json"))["v54"]
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
A=json.load(open(HERE/"splice_sweep_draft.json"))
B=json.load(open(HERE/"splice_t288_draft.json")) if (HERE/"splice_t288_draft.json").exists() else {}
CAND=collections.defaultdict(list)
for src in (A,B):
    for c,v in src.items(): CAND[c].append((v[0],v[1]))
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
    jobs=[]
    for c,arms in CAND.items():
        for opp,seeds in (("rescue7",IR7b.get(c,[])[:6]),("herdsafe",IHS.get(c,[])[3:9]),("v56",IR7b.get(c,[])[6:10])):
            for s in seeds:
                jobs.append((c,opp,s,None,-1))
                for cut,rid in arms: jobs.append((c,opp,s,cut,rid))
    print("格",len(CAND),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"splice_holdout2.json","w"))
    per=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,cut,rid,m in res:
        if m is None: continue
        a=per[(c,(cut,rid))][opp]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,arms in sorted(CAND.items()):
        base=per[(c,(None,-1))]
        best=None
        for arm in arms:
            s=per[(c,arm)]
            tw=sum(s[o][0] for o in s); tb=sum(base[o][0] for o in base)
            dm=sum(s[o][2] for o in s)-sum(base[o][2] for o in base)
            safe=all(s[o][0]>=base[o][0] for o in base)
            ok=safe and (tw>tb or (tw==tb and dm>0))
            if ok and (best is None or (tw,dm)>(best[1],best[2])): best=(arm,tw,dm,tb)
        if best:
            final[c]=list(best[0])
            print(f"[进] {c:30s} t{best[0][0]}->{best[0][1]:3d}  总胜 {best[1]} vs 基 {best[3]}  均差和 {best[2]:+8.0f}")
        else:
            print(f"[弃] {c:30s}")
    json.dump(final, open(HERE/"splice_final2.json","w"))
    print("终进", len(final))
