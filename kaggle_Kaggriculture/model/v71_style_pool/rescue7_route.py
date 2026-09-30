"""对 rescue7 的克制带搜索:w48fr 强制路线 × seed11100-11123 双席位。"""
import sys, os, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND=[-1,0,1,3,5,7,9,100,101,103,107,110,112,115,118,120,123,126,128]
def one(job):
    seed,seat,rid=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/w48fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; a=[None,None]; t=0; combo=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1]); t+=1
            if t==146: combo="|".join(((g.observe(seat).get("town") or {}).get("unlocked_shops") or [])[:2])
        return seed,seat,rid,combo,float(g.reward(seat)-g.reward(o))
    except Exception as e:
        return seed,seat,rid,f"ERR{type(e).__name__}",None
if __name__=="__main__":
    jobs=[(s,st,r) for s in range(11100,11112) for st in (0,1) for r in CAND]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    import json; json.dump([list(r) for r in res],open(HERE/"rescue7_route.json","w"))
    per=collections.defaultdict(dict)
    for s,st,r,c,m in res:
        if m is not None: per[(s,st,c)][r]=m
    bw=sum(1 for v in per.values() if v.get(-1,0)>0)
    orc=sum(1 for v in per.values() if v and max(v.values())>0)
    print(f"格 {len(per)};基线胜 {bw};事后最优 {orc}")
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
    for (s,st,c),v in per.items():
        if -1 not in v: continue
        for r,m in v.items():
            a=agg[c][r]; a[0]+=m>0; a[1]+=m; a[2]+=1
    for c,rids in sorted(agg.items()):
        base=rids.get(-1,[0,0,1]); best=max(rids.items(),key=lambda kv:(kv[1][0],kv[1][1]))
        if best[0]!=-1 and best[1][0]>base[0]:
            print(f"{str(c):34s} 基线 {base[0]}/{base[2]} -> 路线{best[0]} {best[1][0]}/{best[1][2]}")
