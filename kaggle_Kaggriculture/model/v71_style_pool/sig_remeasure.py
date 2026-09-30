"""r19 开局下重测 t216 门格签名:PET|FM、YARN|YARN(rescue7 vs V5x),Sheep 败局 tape。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
def one(job):
    kind,opp,seed,combo=job
    os.environ.pop("KAG_FORCE_ROUTE",None); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r19_main.py")
        if kind=="tape":
            r=json.load(open(HERE/"rlive"/"episode-111981662-replay.json")); s=r["steps"]
            nm=r["info"]["TeamNames"]; seat=nm.index("datatuu"); o=1-seat
            op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
            seed=r["info"]["seed"]
        else:
            op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py"); seat,o=0,1
        k=engine.load_kagsim(); g=k.Game(seed=seed); sig=[None,None]
        for t in range(161):
            obs=[g.observe(0),g.observe(1)]
            if t==150: sig[0]=round(float(obs[seat]["farms"][o]["money"]),2)
            if t==160: sig[1]=round(float(obs[seat]["farms"][o]["money"]),2)
            a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return kind,opp,combo,tuple(sig)
    except Exception as e: return kind,opp,combo,f"ERR {e}"
if __name__=="__main__":
    jobs=[("tape","sheep",0,"PIZZA_SHOP|ICE_CREAM_SHOP")]
    for c in ("PET_CAFE|FARMERS_MARKET","YARN_STORE|YARN_STORE"):
        for s in IDX[c][:2]:
            for o in ("rescue7","v54","v55","v56","busya_race"): jobs.append(("live",o,s,c))
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    d=collections.defaultdict(lambda:collections.defaultdict(set))
    for k,o,c,sg in res: d[c][o].add(str(sg))
    for c,m in d.items():
        print(f"== {c}")
        for o,sg in m.items(): print(f"   {o:12s} {sorted(sg)}")
