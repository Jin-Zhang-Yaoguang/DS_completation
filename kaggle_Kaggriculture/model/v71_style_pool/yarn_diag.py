"""纱线世界:羊毛数量/均价/在场羊数/照料次数 双方对比。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
def herd(f):
    c=collections.Counter()
    for row in f["tiles"]:
        for t in row:
            if isinstance(t,dict) and t.get("animal"): c[t["animal"]]+=1
    return dict(c)
def one(job):
    agent,opp,seed,seat,eid=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py"); op=fidelity.make_agent(f"sub:{OPP[opp]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat; P=(seat,o)
        Q=[collections.Counter(),collections.Counter()]; H={}; t=0; route=[None,None]
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o])
            pr=obs[0]["market"]["prices"]
            for i,p in enumerate(P):
                for x in ((a[p] or {}).get("market") or []):
                    if x and x[0]=="SELL" and x[1] in ("WOOL","MILK","EGG"): Q[i][x[1]+"_q"]+=x[2]; Q[i][x[1]+"_$"]+=x[2]*pr[x[1]]
                for u in [(a[p] or {}).get("farmer")]+list((a[p] or {}).get("hands") or []):
                    if u and u[0] in ("CARE","FEED","HARVEST"): Q[i][u[0]]+=1
            if t in (144,288,432,576,700): H[t]=(herd(obs[0]["farms"][seat]),herd(obs[0]["farms"][o]),pr["WOOL"])
            g.step(a[0],a[1]); t+=1
        return eid,dict(d=float(g.reward(seat)-g.reward(o)),Q=[dict(Q[0]),dict(Q[1])],H=H)
    except Exception as ex: return eid,{"err":str(ex)[:100]}
if __name__=="__main__":
    agent,opp=sys.argv[1],sys.argv[2]
    B=[x for x in json.load(open("axis_rows.json")) if x["cls"]=="新版人群" and "YARN_STORE" in x["shops"]]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,[(agent,opp,x["seed"],x["seat"],x["eid"]) for x in B],chunksize=1))
    json.dump(R,open(f"yarndiag_{agent}_{opp}.json","w"))
    for nm,f in (("负",lambda v:v["d"]<0),("胜",lambda v:v["d"]>0)):
        S=[v for v in R.values() if "d" in v and f(v)]
        if not S: continue
        av=lambda i,k: sum(v["Q"][i].get(k,0) for v in S)/len(S)
        print(f"{nm} n={len(S)}  羊毛 我 {av(0,'WOOL_q'):.0f}件 {av(0,'WOOL_$')/max(1,av(0,'WOOL_q')):.0f}/件  对手 {av(1,'WOOL_q'):.0f}件 {av(1,'WOOL_$')/max(1,av(1,'WOOL_q')):.0f}/件 | 奶 我 {av(0,'MILK_q'):.0f} 对手 {av(1,'MILK_q'):.0f} | 蛋 我 {av(0,'EGG_q'):.0f} 对手 {av(1,'EGG_q'):.0f} | CARE 我 {av(0,'CARE'):.0f} 对 {av(1,'CARE'):.0f} FEED 我 {av(0,'FEED'):.0f} 对 {av(1,'FEED'):.0f}")
        for t in (144,288,432,576,700):
            hs=[v["H"][str(t)] if str(t) in v["H"] else v["H"].get(t) for v in S]; hs=[h for h in hs if h]
            agg=lambda i,a: sum(h[i].get(a,0) for h in hs)/len(hs)
            print(f"   t{t}: 我 羊{agg(0,'SHEEP'):.1f} 牛{agg(0,'COW'):.1f} 鹅{agg(0,'GOOSE'):.1f} | 对 羊{agg(1,'SHEEP'):.1f} 牛{agg(1,'COW'):.1f} 鹅{agg(1,'GOOSE'):.1f} | 羊毛价 {sum(h[2] for h in hs)/len(hs):.0f}")
