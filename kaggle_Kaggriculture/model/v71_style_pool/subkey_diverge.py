"""同 rkey 不同方案:我方(r22)观测到的对手状态在第几步开始分叉 → 二次指纹候选时点。"""
import sys, json, hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
GROUPS={"1039":["rescue7","v54","v56","harvestledger","hybrid2965","hai2965","guru_v4"],"1042":["herdsafe","engineV3","shepledger"]}
T=200
def one(job):
    opp,seed=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/v54r22_main.py"); op=fidelity.make_agent(f"sub:{OPP[opp]}")
    k=engine.load_kagsim(); g=k.Game(seed=seed); tr=[]
    for t in range(T):
        obs=[g.observe(0),g.observe(1)]
        f=obs[0]["farms"][1]
        tr.append((f["money"], hashlib.md5(json.dumps([f.get("tiles"),f.get("hands"),obs[0]["market"]["inventory"]],sort_keys=True).encode()).hexdigest()[:6]))
        g.step(me(obs[0]),op(obs[1]))
    return opp,seed,tr
if __name__=="__main__":
    jobs=[(o,s) for grp in GROUPS.values() for o in grp for s in (18001,18002,18003)]
    with ProcessPoolExecutor(3) as ex: res=list(ex.map(one,jobs))
    R={(o,s):tr for o,s,tr in res}
    for gk,grp in GROUPS.items():
        print(f"== 键 {gk}")
        for i,a in enumerate(grp):
            for b in grp[i+1:]:
                fs=[]
                for s in (18001,18002,18003):
                    ta,tb=R[(a,s)],R[(b,s)]
                    d=next((t for t in range(T) if ta[t]!=tb[t]),None); fs.append(d)
                print(f"  {a:14s} vs {b:14s} 首次分叉步 {fs}  t=分叉步现金 {[ (R[(a,s)][d][0],R[(b,s)][d][0]) if d is not None else None for s,d in zip((18001,18002,18003),fs)]}")
