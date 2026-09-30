"""B. 二级指纹:同 seed 下五子族 vs r5,记录我方可观测特征轨迹,找最早分歧步。"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
FAMS=["v54","v55","v56","busya_race","rescue7"]
def one(job):
    fam,seed=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r5w48_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{fam}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); tr=[]
        for t in range(150):
            obs=[g.observe(0),g.observe(1)]
            rv=obs[0]["farms"][1]; mk=obs[0]["market"]["inventory"]
            tr.append((round(float(rv["money"]),2), int(mk.get("WHEAT",0)), int(mk.get("FERTILIZER",0)),
                       len(rv.get("hands") or [])))
            g.step(me(obs[0]),op(obs[1]))
        return fam,seed,tr
    except Exception as e:
        return fam,seed,f"ERR{type(e).__name__}"
if __name__=="__main__":
    jobs=[(f,s) for f in FAMS for s in (12200,12201,12202,12203)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    by=collections.defaultdict(dict)
    for f,s,tr in res:
        if isinstance(tr,str): print(f,s,tr); continue
        by[s][f]=tr
    json.dump({str(s):{f:tr for f,tr in d.items()} for s,d in by.items()}, open(HERE/"subfam_diverge.json","w"))
    for s,d in sorted(by.items()):
        if len(d)<5: continue
        # 每对子族的最早分歧步
        print(f"== seed{s}")
        fams=list(d)
        for i in range(len(fams)):
            for j in range(i+1,len(fams)):
                a,b=d[fams[i]],d[fams[j]]
                div=next((t for t in range(150) if a[t]!=b[t]), None)
                print(f"  {fams[i]:10s} vs {fams[j]:10s} 最早分歧步 {div}")
