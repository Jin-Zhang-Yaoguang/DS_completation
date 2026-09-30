"""Majkel 式对手开环动作带评测:真实种子+席位,对手用线上实际动作带;我方 r36cut × {现状, t144 13 带}。"""
import sys, os, json, collections, statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
HERE=Path(__file__).resolve().parent
def one(job):
    eid,env=job
    for k in list(os.environ):
        if k.startswith("KAG_CUT"): os.environ.pop(k,None)
    for kv in env: k,v=kv.split("=",1); os.environ[k]=v
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(HERE/f"rlive3/{eid}.json")); seat=r["seat"]; o=1-seat
        op=fidelity.tape_agent([r["acts"][t+1][o] for t in range(len(r["acts"])-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/r36cut_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return eid,float(g.reward(seat)-g.reward(o))
    except Exception: return eid,None
if __name__=="__main__":
    G=json.load(open("boards_majkel.json")); hi=[x for x in G if x["opp"]>=2000]
    SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
    arms=[("现状",())]+[(f"t144带{r}",(f"KAG_CUT144={r}",)) for r in SHORT]
    for name,env in arms:
        with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv)>1 else 2) as ex: res=dict(ex.map(one,[(x["eid"],env) for x in G]))
        def s(B):
            v=[res[x["eid"]] for x in B if res.get(x["eid"]) is not None]
            return f"{sum(d>0 for d in v)}/{len(v)} 均差{st.mean(v):+6.0f}" if v else "-"
        print(f"  {name:9s} 全部 {s(G)} | 对手≥2000 {s(hi)}",flush=True)
