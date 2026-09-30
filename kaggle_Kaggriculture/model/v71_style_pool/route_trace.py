import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
def one(job):
    eid,seed,seat,opp=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import engine
    ns1={}; exec(Path("agents/v54r32_main.py").read_text(),ns1); me=[v for k,v in ns1.items() if callable(v) and not k.startswith("__")][-1]
    ns2={}; exec(Path(f"agents/{opp}_main.py").read_text(),ns2); op=[v for k,v in ns2.items() if callable(v) and not k.startswith("__")][-1]
    k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; rt={}
    for t in range(720):
        if engine._val(g.done): break
        obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        if t in (200,500):
            rt[f"我t{t}"]=ns1["_IMPL"].chassis.players.get(seat,{}).get("route")
            if "_IMPL" in ns2: rt[f"对t{t}"]=ns2["_IMPL"].chassis.players.get(o,{}).get("route")
    return eid,rt,float(g.reward(seat)-g.reward(o))
if __name__=="__main__":
    m=json.load(open("meta_live.json")); J=[]
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); e=str(r["eid"]); v=m.get(e)
        if not v or v["ver"]!="r32" or not v.get("opp") or v["opp"].get("reward") is None or v["opp"]["initialScore"]<2200: continue
        if not (MILK & set((r.get("shops") or [])[:2])) or v["me"]["reward"]>v["opp"]["reward"]: continue
        J.append((e,r["seed"],r["seat"],"me2965_28"))
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,J))
    c=collections.Counter((tuple(sorted(rt.items()))) for e,rt,d in res)
    for k,n in c.most_common(10): print(n,k)
    print("模拟中我方对 me2965_28:",sum(d>0 for e,rt,d in res),"/",len(res))
