"""败局分阶段诊断:无解格/弱格中,双方现金差在各商店解锁点的走势 —— 定位在哪个阶段输掉。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IR7=json.load(open(HERE/"combo_index.json"))["v54"]
IHS=json.load(open(HERE/"combo_index_hs.json"))["herdsafe"]
CK=[72,144,216,288,360,432,504,576,648,719]
CASES=[("rescue7",c) for c in ("SMOOTHIE_SHOP|PET_CAFE","FARMERS_MARKET|BRUNCH_SPOT","YARN_STORE|BRUNCH_SPOT")]+\
      [("herdsafe",c) for c in ("SMOOTHIE_SHOP|PET_CAFE","YARN_STORE|BRUNCH_SPOT","YARN_STORE|ICE_CREAM_SHOP","PET_CAFE|ICE_CREAM_SHOP")]
def one(job):
    opp,c,seed=job
    os.environ.pop("KAG_FORCE_ROUTE",None); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54r17_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; tr={}
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t in CK: tr[t]=float(obs[0]["farms"][0]["money"])-float(obs[0]["farms"][1]["money"])
            g.step(me(obs[0]),op(obs[1])); t+=1
        return opp,c,seed,tr,float(g.reward(0)-g.reward(1))
    except Exception as e: return opp,c,seed,None,None
if __name__=="__main__":
    jobs=[]
    for opp,c in CASES:
        idx=IR7 if opp=="rescue7" else IHS
        for s in idx.get(c,[])[:4]: jobs.append((opp,c,s))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs))
    json.dump([[o,c,s,tr,m] for o,c,s,tr,m in res],open(HERE/"phase_diag.json","w"))
    grp=collections.defaultdict(list)
    for o,c,s,tr,m in res:
        if tr is None: continue
        grp[(o,c)].append((tr,m))
    print(f"{'对手|组合':44s} " + " ".join(f"{'t'+str(t):>7s}" for t in CK) + "   终局")
    for (o,c),lst in grp.items():
        losses=[x for x in lst if x[1]<=0]
        use=losses or lst
        avg={t: sum(x[0].get(t,0) for x in use)/len(use) for t in CK}
        tag=f"{o}|{c}"[:42]
        print(f"{tag:44s} " + " ".join(f"{avg[t]:+7.0f}" for t in CK) + f"   负{len(losses)}/{len(lst)}")
