"""r38 线上 <900 键对局:对手用线上实际动作带(开环),比较 r38(Majkel 行开) 与 r36(无此行)。"""
import sys, os, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
HERE=Path(__file__).resolve().parent
def one(job):
    eid,agent=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(HERE/f"rlive3/{eid}.json")); seat=r["seat"]; o=1-seat
        op=fidelity.tape_agent([r["acts"][t+1][o] for t in range(len(r["acts"])-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return (eid,agent),float(g.reward(seat)-g.reward(o))
    except Exception as ex: return (eid,agent),None
if __name__=="__main__":
    m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
    B=[]
    for e,v in m.items():
        if v["ver"] not in ("r38","r38b") or not (HERE/f"rlive3/{e}.json").exists(): continue
        k=(H.get(e) or {}).get("rkey")
        if k and k[0]<900 and k[0] not in (151.0,7.0): B.append((e,v,k))
    jobs=[(e,a) for e,_,_ in B for a in ("v54r38","v54r38c","v54r36")]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,jobs))
    for e,v,k in sorted(B,key=lambda z:z[1]["opp"]["initialScore"]):
        print(f"{v['ver']:5s} opp {v['opp']['initialScore']:5.0f} key {k}  线上 {v['me']['reward']-v['opp']['reward']:7d} | r38 {R.get((e,'v54r38'))} r38c {R.get((e,'v54r38c'))} r36 {R.get((e,'v54r36'))}")
