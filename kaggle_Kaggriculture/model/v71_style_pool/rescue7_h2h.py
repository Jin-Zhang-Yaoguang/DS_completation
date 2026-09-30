"""r4(w48) vs 7-Turn Rescue v2 响应式对撞 + rkey。"""
import sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    seed,seat=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r3w48_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; a=[None,None]; t=0; rkey=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t==2:
                rv=obs[seat]["farms"][o]
                rkey=(round(float(rv["money"]),3), int(obs[seat]["market"]["inventory"]["WHEAT"]))
            a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1]); t+=1
        return seed,seat,str(rkey),float(g.reward(seat)-g.reward(o))
    except Exception as e:
        return seed,seat,f"ERR{type(e).__name__}:{e}"[:80],None
if __name__=="__main__":
    jobs=[(s,st) for s in range(11000,11012) for st in (0,1)]
    with ProcessPoolExecutor(6) as ex: res=list(ex.map(one,jobs))
    ks=collections.Counter(k for _,_,k,m in res if m is not None)
    w=sum(1 for *_,m in res if m and m>0); l=sum(1 for *_,m in res if m is not None and m<=0)
    errs=[k for _,_,k,m in res if m is None]
    print(f"w48 vs rescue7: {w}胜{l}负/{len(res)}  rkey {dict(ks.most_common(3))}")
    if errs: print("ERR:", errs[:3])
    ms=sorted(round(m) for *_,m in res if m is not None)
    print("分差分布:", ms)
