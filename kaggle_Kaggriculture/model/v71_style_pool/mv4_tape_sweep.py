"""metav4 键 6 个线上败局:全 41 带 tape 扫描,找一致克制带。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
EPS=json.load(open(HERE/"mv4_loss_eps.json"))
CAND=[-1,0,1,3,4,5,6,7,8,9,10,11,12,100,101,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128]
def one(job):
    ep,rid=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(HERE/"rlive"/ep)); nm=r["info"]["TeamNames"]; s=r["steps"]
        seat=nm.index("datatuu"); o=1-seat
        op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"]); t=0; combo=None; sig=[None,None]
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t in (150,160): sig[0 if t==150 else 1]=round(float(obs[seat]["farms"][o]["money"]),2)
            a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1]); t+=1
            if t==146:
                ob=g.observe(seat); combo="|".join(((ob.get("town") or {}).get("unlocked_shops") or [])[:2])
        return ep,rid,combo,tuple(sig),float(g.reward(seat)-g.reward(o))
    except Exception as e: return ep,rid,None,None,None
if __name__=="__main__":
    jobs=[(e,r) for e in EPS for r in CAND]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"mv4_sweep.json","w"))
    per=collections.defaultdict(dict); meta={}
    for ep,rid,c,sg,m in res:
        if m is None: continue
        per[ep][rid]=m; meta[ep]=(c,sg)
    allwin=collections.Counter()
    for ep,v in sorted(per.items()):
        c,sg=meta[ep]
        base=v.get(-1,0)
        wins=sorted(r for r,m in v.items() if r!=-1 and m>0)
        allwin.update(wins)
        print(f"{ep[:28]} {str(c):28s} sig={sg} 基线{base:+8.0f} 可翻带({len(wins)}): {wins[:10]}")
    print("\n跨败局通用克制带:", [(r,n) for r,n in allwin.most_common(8)])
