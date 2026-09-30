"""Herd-Safe / Shepherd 的 rkey 指纹 + r14 对撞胜率。"""
import sys, os, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    opp,seed,seat=job
    os.environ.pop("KAG_FORCE_ROUTE",None); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r14_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; a=[None,None]; t=0; rk=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t==2:
                rv=obs[seat]["farms"][o]
                rk=(round(float(rv["money"]),3), int(obs[seat]["market"]["inventory"]["WHEAT"]))
            a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1]); t+=1
        return opp,seed,seat,str(rk),float(g.reward(seat)-g.reward(o))
    except Exception as e: return opp,seed,seat,f"ERR{type(e).__name__}",None
if __name__=="__main__":
    jobs=[(o,s,st) for o in ("herdsafe","shepherd","rescue7") for s in range(15000,15008) for st in (0,1)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:[0,0,0.0]); keys=collections.defaultdict(collections.Counter)
    for o,s,st,rk,m in res:
        if m is None: print("ERR",o,rk); continue
        a=agg[o]; a[0]+= m>0; a[1]+=1; a[2]+=m; keys[o][rk]+=1
    print(f"{'对手':10s} {'rkey 指纹':24s} {'r14 战绩':>10s} {'均分差':>8s}")
    for o,a in sorted(agg.items()):
        k=keys[o].most_common(1)[0][0]
        print(f"{o:10s} {k:24s} {a[0]:3d}/{a[1]:3d}({a[0]/max(1,a[1]):5.1%}) {a[2]/max(1,a[1]):+8.0f}")
    print("\n镜像键基准 (1042.0, 9989);表是否触发取决于 rkey 是否匹配")
