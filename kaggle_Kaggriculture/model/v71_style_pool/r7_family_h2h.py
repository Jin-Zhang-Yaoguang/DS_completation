"""r5 vs V54 家族(含我方在线版本)头对头,双席位 × 8 seed。"""
import sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
OPPS={"v54":"v54_main.py","v54r3":"v54r3_main.py","r4_w48":"v54r3w48_main.py","v52":"v52_main.py","v53":"v53_main.py","v55":"v55_main.py","v56":"v56_main.py","rescue7":"rescue7_main.py","r5":"v54r5w48_main.py"}
def one(job):
    o,s,seat=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r7_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{OPPS[o]}")
        k=engine.load_kagsim(); g=k.Game(seed=s); other=1-seat; a=[None,None]
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a[seat]=me(obs[seat]); a[other]=op(obs[other]); g.step(a[0],a[1])
        return o,s,seat,float(g.reward(seat)-g.reward(other))
    except Exception as e: return o,s,seat,None
if __name__=="__main__":
    jobs=[(o,s,st) for o in OPPS for s in range(11300,11308) for st in (0,1)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    agg=collections.defaultdict(lambda:[0,0,0,0.0])
    for o,s,st,m in res:
        if m is None: continue
        a=agg[o]; a[0]+=m>0; a[1]+=m==0; a[2]+=1; a[3]+=m
    for o,a in agg.items():
        print(f"vs {o:8s} {a[0]}胜 {a[1]}平 {a[2]-a[0]-a[1]}负 /{a[2]}  平均分差 {a[3]/max(1,a[2]):+.0f}")
