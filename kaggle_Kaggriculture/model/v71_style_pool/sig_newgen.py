"""新版公开方案 vs 老 herdsafe:r31 视角下对手现金序列(t0-143)首个差异点。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
AG=["herdsafe","shepledger","engineV3","me2965_28","guru28","hybrid28","demand28","idle28","harvest28","shep28"]
def one(job):
    o,seed=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[o]).parent))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/v54r31_main.py"); op=fidelity.make_agent(f"sub:{OPP[o]}")
    k=engine.load_kagsim(); g=k.Game(seed=seed); tr=[]; acts=[]
    for t in range(144):
        obs=[g.observe(0),g.observe(1)]; tr.append(float(obs[0]["farms"][1]["money"]))
        a1=op(obs[1]); acts.append(json.dumps([x for x in (a1.get("market") or []) if x])); g.step(me(obs[0]),a1)
    return o,seed,tr,acts
if __name__=="__main__":
    jobs=[(o,s) for o in AG for s in (18001,18077)]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    R={(o,s):(tr,a) for o,s,tr,a in res}
    for s in (18001,18077):
        base=R[("herdsafe",s)][0]
        for o in AG:
            tr=R[(o,s)][0]; d=next((t for t in range(144) if tr[t]!=base[t]),None)
            jumps=[(t,int(tr[t]-tr[t-1])) for t in range(1,144) if abs(tr[t]-tr[t-1])>0 and t in (58,92,94,96,120,121)]
            print(f"seed{s} {o:11s} 与herdsafe现金首差步 {d}  t@差 {(tr[d],base[d]) if d is not None else '-'}  t1市场 {R[(o,s)][1][1][:70]}")
