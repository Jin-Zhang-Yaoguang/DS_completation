import sys, json, glob, collections, statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
def one(job):
    ag,rep,seed,seat=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:agents/{ag}_main.py"); op=fidelity.make_agent(f"sub:agents/{rep}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; C=[collections.Counter(),collections.Counter()]; first=[{},{}]
    t=0
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o])
        for q,side in ((seat,0),(o,1)):
            for x in (a[q].get("market") or []):
                if x and x[0]=="BUY_ANIMAL": C[side]["买"+x[1]]+=int(x[2]) if len(x)>2 else 1
            # 产奶:观测 shed 里 MILK 增量难取,改用对手/我方牲畜 tile 统计(终局)
        g.step(a[0],a[1]); t+=1
    fin=g.observe(seat)["farms"]
    for q,side in ((seat,0),(o,1)):
        for row in fin[q]["tiles"]:
            for tile in row:
                if isinstance(tile,dict) and tile.get("animal"): C[side]["终局"+tile["animal"]]+=1
    return C
if __name__=="__main__":
    ag,rep,n=sys.argv[1],sys.argv[2],int(sys.argv[3])
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    B=[x for x in json.load(open("boards_recent_all.json")) if x.get("seed") is not None and x["eid"] in comp and (MILK & set((comp[x["eid"]].get("shops") or [])[:2]))][:n]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,[(ag,rep,x["seed"],x["seat"]) for x in B]))
    keys=sorted({k for c in res for s in c for k in s})
    for k in keys: print(f"  {k:14s} 我 {st.median(c[0][k] for c in res):5.1f}  对手 {st.median(c[1][k] for c in res):5.1f}")
