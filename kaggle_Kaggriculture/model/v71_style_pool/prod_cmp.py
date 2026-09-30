"""模拟中我方 vs 新版代表的生产对比(施肥/照料/各产品卖出/终局收益)。用法: python prod_cmp.py <我方> <代表> <棋盘json> <数量>"""
import sys, json, collections, statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
def one(job):
    ag,rep,seed,seat=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:agents/{ag}_main.py"); op=fidelity.make_agent(f"sub:agents/{rep}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; C=[collections.Counter(),collections.Counter()]
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o])
        for q,side in ((seat,0),(o,1)):
            for u in [a[q].get("farmer") or []]+list(a[q].get("hands") or []):
                if u and u[0] in ("FERTILIZE","CARE","FEED","HARVEST","WATER","COLLECT_FERTILIZER"): C[side][u[0]]+=1
            for x in (a[q].get("market") or []):
                if x and x[0]=="SELL" and len(x)>2: C[side]["卖"+x[1]]+=int(x[2])
        g.step(a[0],a[1])
    C[0]["收益"]=float(g.reward(seat)); C[1]["收益"]=float(g.reward(o))
    return C
if __name__=="__main__":
    ag,rep,bf,n=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4])
    comp={}
    import glob
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    B=[x for x in json.load(open(bf)) if x.get("seed") is not None and x["eid"] in comp and (MILK & set((comp[x["eid"]].get("shops") or [])[:2]))][:n]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,[(ag,rep,x["seed"],x["seat"]) for x in B]))
    keys=["收益","FERTILIZE","CARE","FEED","HARVEST","卖MILK","卖STRAWBERRY","卖WOOL","卖EGG","卖MELON","卖WHEAT"]
    print(f"{ag} vs {rep} 奶类世界 {len(B)} 盘(中位数)")
    for k in keys: print(f"  {k:14s} 我 {st.median(c[0][k] for c in res):9.0f}  对手 {st.median(c[1][k] for c in res):9.0f}")
    print("  我方胜",sum(c[0]["收益"]>c[1]["收益"] for c in res),"/",len(res))
