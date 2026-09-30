"""⑥ V56 底盘镜像行全组合搜索:v56fr × {v56,v55,busya_race,metav4} × seed10200-10223 × 19 候选。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND = [-1, 0, 1, 3, 5, 7, 9, 100, 101, 103, 107, 110, 112, 115, 118, 120, 123, 126, 128]
OPPS = ["rescue7","v56","v55","busya_race"]
def one(job):
    opp, seed, rid = job
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; combo=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
            if t==146: combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
        return opp,seed,rid,combo,float(g.reward(0)-g.reward(1))
    except Exception as e:
        return opp,seed,rid,f"ERR{type(e).__name__}",None
if __name__=="__main__":
    jobs=[(o,s,r) for o in OPPS for s in range(10200,10224) for r in CAND]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"r5_route_search.json","w"))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(o,s,c)][r]=m
    base_w=sum(1 for v in per.values() if v.get(-1,0)>0)
    orc=sum(1 for v in per.values() if v and max(v.values())>0)
    print(f"格 {len(per)};V56基线胜 {base_w};事后最优 {orc}")
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
    for (o,s,c),v in per.items():
        if -1 not in v: continue
        for rid,m in v.items():
            a=agg[c][rid]; a[0]+=m>0; a[1]+=m; a[2]+=1
    draft={}
    for c,rids in sorted(agg.items()):
        base=rids.get(-1,[0,0,1])
        best=max(rids.items(),key=lambda kv:(kv[1][0],kv[1][1]))
        if best[0]!=-1 and best[1][0]>base[0]:
            draft[c]=best[0]
            print(f"{c:34s} 基线 {base[0]}/{base[2]} -> 路线{best[0]} {best[1][0]}/{best[1][2]}")
    json.dump(draft,open(HERE/"r5_search_draft.json","w"))
    print("done")
