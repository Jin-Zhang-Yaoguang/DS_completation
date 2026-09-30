"""metav4 键拼接复验:① 对 metav4 原版 5 seed 留出;② 对 V41/V43/qq(同键 1049)跨族安全。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IM=json.load(open(HERE/"combo_index_mv4.json"))["metav4"]
IO=json.load(open(HERE/"combo_index_old3.json"))
D=json.load(open(HERE/"mv4_splice_draft.json"))
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
        for s in IM.get(c,[])[1:6]:
            jobs.append((c,"metav4",s,None,-1)); jobs.append((c,"metav4",s,cut,rid))
        for fam in ("V41","V43","qq"):
            for s in IO.get(fam,{}).get(c,[])[:2]:
                jobs.append((c,fam,s,None,-1)); jobs.append((c,fam,s,cut,rid))
    print("格",len(D),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"mv4_holdout.json","w"))
    per=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,opp,cut,m in res:
        if m is None: continue
        a=per[c][("s" if cut else "b",opp)]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,(cut,rid,_,_) in sorted(D.items()):
        p=per[c]
        mw,mn=p[("s","metav4")][0],p[("s","metav4")][1]; mb=p[("b","metav4")][0]
        dm=(p[("s","metav4")][2]-p[("b","metav4")][2])/max(1,mn)
        old=[(f,p[("s",f)][0],p[("b",f)][0],p[("s",f)][1]) for f in ("V41","V43","qq") if p[("s",f)][1]>0]
        safe=all(sw>=bw for _,sw,bw,_ in old)
        ok = mn>=4 and safe and (mw>mb or (mw==mb and dm>=300))
        if ok: final[c]=[cut,rid]
        ot=" ".join(f"{f}:{sw}/{n}(基{bw})" for f,sw,bw,n in old)
        print(f"[{'进' if ok else ('族劣' if not safe else '弃')}] {c:30s} t{cut}->{rid:3d} metav4 {mw}/{mn}(基{mb}) Δ均{dm:+6.0f} | {ot}")
    json.dump(final, open(HERE/"mv4_splice_final.json","w"))
    print("终进", len(final))
