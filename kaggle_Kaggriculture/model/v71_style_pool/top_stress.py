"""A. 顶段压力测试:r4(w48) vs 顶段选手动作带,官方索引 09-19/09-20。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
TOP = ["M & M & P & Q","DSM","SpaTaro","Sida Zuo","ymg_aq","THIRD FARM CLUB","Driz Lo",
       "Orbital Terraformer","Excluding","Thomas Tschinkel","Unknown Mother-Goose","Majkel"]
CAP = 10
def one(job):
    fn, seat = job   # seat = 顶段选手席位,我坐 1-seat
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(fn)); s=r["steps"]
        op=fidelity.tape_agent([s[t+1][seat].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r3w48_main.py")
        my=1-seat
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[my]=me(obs[my]); a[seat]=op(obs[seat]); g.step(a[0],a[1])
        return r["info"]["TeamNames"][seat], Path(fn).name, float(g.reward(my)-g.reward(seat))
    except Exception as e:
        return f"ERR{type(e).__name__}", str(fn), None
if __name__=="__main__":
    jobs=[]; cnt=collections.Counter()
    for d in ("2026-09-20","2026-09-19"):
        for fn in sorted(glob.glob(str(ROOT/f"date={d}"/"data"/"*.json"))):
            try: info=json.load(open(fn))["info"]
            except Exception: continue
            for seat,nm in enumerate(info["TeamNames"]):
                if nm in TOP and cnt[nm]<CAP:
                    cnt[nm]+=1; jobs.append((fn,seat))
    print("任务",len(jobs),dict(cnt),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:[0,0,[]])
    for nm,fn,m in res:
        if m is None: agg["ERR"][1]+=1; continue
        a=agg[nm]; a[0]+=m>0; a[1]+=1; a[2].append((round(m),fn))
    tw=tn=0
    for nm,a in sorted(agg.items(),key=lambda kv:kv[1][0]/max(1,kv[1][1])):
        if nm=="ERR": print("ERR",a[1]); continue
        tw+=a[0]; tn+=a[1]
        losses=[f"{m:+d}" for m,_ in sorted(a[2])[:3] if m<=0]
        print(f"{nm:22s} {a[0]:2d}/{a[1]:2d}  最差 {losses}")
    print(f"合计 {tw}/{tn}")
    json.dump([[nm,fn,m] for nm,fn,m in res], open(HERE/"top_stress.json","w"))
