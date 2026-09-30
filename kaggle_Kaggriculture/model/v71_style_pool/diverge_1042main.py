"""1042 主干线上对手 vs 候选方案:同棋盘同步对照,找首次分歧步与分歧动作。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
def norm(a): return json.dumps({"farmer":a.get("farmer"),"hands":a.get("hands"),"market":[o for o in (a.get("market") or []) if o]},sort_keys=True)
def one(job):
    eid,cand=job
    r=json.load(open(HERE/f"rlive3/{eid}.json")); seat=r["seat"]; o=1-seat; ver=r["meta"]
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[cand]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54{ver}_main.py"); op=fidelity.make_agent(f"sub:{OPP[cand]}")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"]); t=0
        while not engine._val(g.done) and t<719:
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o])
            live=r["acts"][t+1][o] or {}
            if norm(a[o])!=norm(live):
                return eid,cand,t,{"sim":{k:a[o].get(k) for k in ("market",)},"live":{k:live.get(k) for k in ("market",)},
                                   "sim_units":[a[o].get("farmer")]+list(a[o].get("hands") or [])[:3],"live_units":[live.get("farmer")]+list(live.get("hands") or [])[:3]}
            g.step(a[0],a[1]); t+=1
        return eid,cand,719,None
    except Exception as e: return eid,cand,None,str(e)[:80]
if __name__=="__main__":
    B=json.load(open(HERE/(sys.argv[3] if len(sys.argv)>3 else "boards_all.json")))
    cands=sys.argv[1].split(",")
    jobs=[(x["eid"],c) for x in B for c in cands]
    with ProcessPoolExecutor(int(sys.argv[2]) if len(sys.argv)>2 else 3) as ex: res=list(ex.map(one,jobs))
    json.dump(res,open(HERE/("diverge_"+(sys.argv[4] if len(sys.argv)>4 else "1042main")+".json"),"w"))
    by=collections.defaultdict(list)
    for e,c,t,info in res: by[c].append(t)
    for c,ts in by.items():
        ts=[t for t in ts if t is not None]; ts.sort()
        print(f"  {c:10s} 首次分歧步 分位(10/25/50/75/90%): {[ts[int(len(ts)*q)] for q in (0.1,0.25,0.5,0.75,0.9)]}  吻合到终局 {sum(t>=719 for t in ts)}/{len(ts)}")
