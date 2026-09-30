"""B试验复验:w48 vs w48sida 对 Sida 40 局 tape 并排重放。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
def one(job):
    fn, seat, ver = job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(fn)); s=r["steps"]
        op=fidelity.tape_agent([s[t+1][seat].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        my=1-seat
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[my]=me(obs[my]); a[seat]=op(obs[seat]); g.step(a[0],a[1])
        return Path(fn).name, ver, float(g.reward(my)-g.reward(seat))
    except Exception as e:
        return Path(fn).name, ver, None
if __name__=="__main__":
    files=[]
    for d in ("2026-09-20","2026-09-19"):
        for fn in sorted(glob.glob(str(ROOT/f"date={d}"/"data"/"*.json"))):
            try: nm=json.load(open(fn))["info"]["TeamNames"]
            except Exception: continue
            if "Sida Zuo" in nm: files.append((fn,nm.index("Sida Zuo")))
            if len(files)>=40: break
        if len(files)>=40: break
    jobs=[(fn,seat,v) for fn,seat in files for v in ("v54r3w48","w48sida")]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    tab=collections.defaultdict(dict)
    for n,v,m in res:
        if m is not None: tab[n][v]=m
    a=sum(1 for v in tab.values() if v.get("v54r3w48",0)>0); b=sum(1 for v in tab.values() if v.get("w48sida",0)>0)
    print(f"{len(tab)} 局: w48 {a} 胜 | w48+sida带 {b} 胜")
    fl=[(n,round(v["v54r3w48"]),round(v["w48sida"])) for n,v in tab.items()
        if (v.get("v54r3w48",0)>0)!=(v.get("w48sida",0)>0)]
    for n,x,y in sorted(fl,key=lambda t:t[2]-t[1]): print(f"  翻转 {n} w48{x:+d} -> sida{y:+d}")
