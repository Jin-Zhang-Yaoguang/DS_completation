"""用 09-21/22 最新 replay 测 r17 对顶段(含榜首 Majkel)的表现。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
ROOT=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
TOP=["Majkel1337","M & M & P & Q","DSM","SpaTaro","Sida Zuo","ymg_aq","THIRD FARM CLUB",
     "Driz Lo","Orbital Terraformer","Excluding","Unknown Mother-Goose"]
CAP=12
def one(job):
    fn,seat,ver=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(fn)); s=r["steps"]
        op=fidelity.tape_agent([s[t+1][seat].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        my=1-seat
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"]); t=0; rk=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t==2:
                rv=obs[my]["farms"][seat]
                rk=(round(float(rv["money"]),3), int(obs[my]["market"]["inventory"]["WHEAT"]))
            a=[None,None]; a[my]=me(obs[my]); a[seat]=op(obs[seat]); g.step(a[0],a[1]); t+=1
        return r["info"]["TeamNames"][seat], str(rk), float(g.reward(my)-g.reward(seat))
    except Exception as e: return None,None,None
if __name__=="__main__":
    jobs=[]; cnt=collections.Counter()
    for d in ("2026-09-22","2026-09-21"):
        for fn in sorted(glob.glob(str(ROOT/f"date={d}"/"data"/"*.json"))):
            try: info=json.load(open(fn))["info"]
            except Exception: continue
            for seat,nm in enumerate(info["TeamNames"]):
                if nm in TOP and cnt[nm]<CAP:
                    cnt[nm]+=1; jobs.append((fn,seat,"v54r17"))
    print("任务",len(jobs),dict(cnt),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:[0,0]); keys=collections.defaultdict(collections.Counter)
    for nm,rk,m in res:
        if m is None: continue
        a=agg[nm]; a[0]+= m>0; a[1]+=1; keys[nm][rk]+=1
    tw=tn=0
    for nm,a in sorted(agg.items(), key=lambda kv: kv[1][0]/max(1,kv[1][1])):
        tw+=a[0]; tn+=a[1]
        k=keys[nm].most_common(1)[0][0]
        print(f"  {nm:22s} {a[0]:2d}/{a[1]:2d} ({a[0]/max(1,a[1]):5.1%})  rkey={k}")
    print(f"  合计 {tw}/{tn} ({tw/max(1,tn):.1%})")
