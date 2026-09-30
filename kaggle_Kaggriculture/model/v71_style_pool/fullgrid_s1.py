"""r7 全格工程·阶段1 粗搜:镜像行未覆盖组合 × 候选短名单 × {v54,rescue7} × 每组合1 seed。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
COVERED={"BRUNCH_SPOT|YARN_STORE","ICE_CREAM_SHOP|FARMERS_MARKET","PIZZA_SHOP|ICE_CREAM_SHOP",
 "ICE_CREAM_SHOP|BRUNCH_SPOT","SMOOTHIE_SHOP|ICE_CREAM_SHOP","ICE_CREAM_SHOP|YARN_STORE",
 "PET_CAFE|SMOOTHIE_SHOP","SMOOTHIE_SHOP|YARN_STORE","SMOOTHIE_SHOP|BAKERY","FARMERS_MARKET|ICE_CREAM_SHOP",
 "BRUNCH_SPOT|PET_CAFE","PIZZA_SHOP|FARMERS_MARKET","PET_CAFE|PIZZA_SHOP","BRUNCH_SPOT|BRUNCH_SPOT",
 "PET_CAFE|BAKERY","PIZZA_SHOP|YARN_STORE"}
CAND=[-1,0,3,9,100,101,103,107,110,111,112,115,118,120,123,124,126]
OPPS=["v54","rescue7"]
def one(job):
    o,seed,rid,combo=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return o,seed,rid,combo,float(g.reward(0)-g.reward(1))
    except Exception as e:
        return o,seed,rid,combo,None
if __name__=="__main__":
    jobs=[]
    for c,seeds in IDX.items():
        if c in COVERED or not seeds: continue
        s=seeds[0]
        for o in OPPS:
            for r in CAND: jobs.append((o,s,r,c))
    print("未覆盖组合", len({j[3] for j in jobs}), "任务", len(jobs), flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"fullgrid_s1.json","w"))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[c].setdefault(o,{})[r]=m
    picks={}
    for c,d in sorted(per.items()):
        # 联合口径:两子族都胜优先,其次胜数和净额
        stat={}
        for r in CAND:
            if r==-1: continue
            wins=sum(1 for o in OPPS if d.get(o,{}).get(r,0)>0)
            tot=sum(d.get(o,{}).get(r,0) for o in OPPS)
            stat[r]=(wins,tot)
        basew=sum(1 for o in OPPS if d.get(o,{}).get(-1,0)>0)
        best=max(stat.items(), key=lambda kv:kv[1])
        if best[1][0]>basew:
            picks[c]=best[0]
            print(f"{c:34s} 基线双族胜{basew}/2 -> 带{best[0]} 双族胜{best[1][0]}/2")
    json.dump(picks, open(HERE/"fullgrid_picks.json","w"))
    print("入围", len(picks))
