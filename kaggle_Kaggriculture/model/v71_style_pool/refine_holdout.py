"""改值格留出复验:新索引 seeds(14000+)× {v54,v56,rescue7,v55},现值 vs 新值,胜负优先。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX2=json.load(open(HERE/"combo_index2.json"))["v54"]
CUR={"BRUNCH_SPOT|BRUNCH_SPOT":110,"BRUNCH_SPOT|PET_CAFE":107,"BRUNCH_SPOT|YARN_STORE":103,
 "FARMERS_MARKET|ICE_CREAM_SHOP":110,"ICE_CREAM_SHOP|BRUNCH_SPOT":110,"ICE_CREAM_SHOP|FARMERS_MARKET":120,
 "PET_CAFE|BAKERY":124,"PET_CAFE|PIZZA_SHOP":123,"PET_CAFE|SMOOTHIE_SHOP":112,
 "PIZZA_SHOP|FARMERS_MARKET":112,"PIZZA_SHOP|ICE_CREAM_SHOP":107,"PIZZA_SHOP|YARN_STORE":126}
NEW={"BRUNCH_SPOT|BRUNCH_SPOT":101,"BRUNCH_SPOT|PET_CAFE":112,"BRUNCH_SPOT|YARN_STORE":126,
 "FARMERS_MARKET|ICE_CREAM_SHOP":120,"ICE_CREAM_SHOP|BRUNCH_SPOT":107,"ICE_CREAM_SHOP|FARMERS_MARKET":107,
 "PET_CAFE|BAKERY":112,"PET_CAFE|PIZZA_SHOP":120,"PET_CAFE|SMOOTHIE_SHOP":107,
 "PIZZA_SHOP|FARMERS_MARKET":123,"PIZZA_SHOP|ICE_CREAM_SHOP":124,"PIZZA_SHOP|YARN_STORE":0}
OPPS=["v54","v56","rescue7","v55"]
def one(job):
    c,seed,rid,o=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid); os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return c,seed,rid,o,float(g.reward(0)-g.reward(1))
    except Exception as e: return c,seed,rid,o,None
if __name__=="__main__":
    jobs=[]
    for c in CUR:
        for s in IDX2.get(c,[])[:6]:
            for o in OPPS:
                jobs.append((c,s,CUR[c],o)); jobs.append((c,s,NEW[c],o))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"refine_holdout.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,o,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c in sorted(CUR):
        cw,cn,cm=agg[c].get(CUR[c],[0,0,0.0]); nw,nn,nm=agg[c].get(NEW[c],[0,0,0.0])
        ok = nn>0 and cn>0 and nw>cw
        final[c]=NEW[c] if ok else CUR[c]
        print(f"[{'改' if ok else '留'}] {c:30s} 现{CUR[c]:4d} {cw}/{cn}({cm/max(1,cn):+.0f}) | 新{NEW[c]:4d} {nw}/{nn}({nm/max(1,nn):+.0f})")
    json.dump(final, open(HERE/"refine_final.json","w"))
    print("确认改值:", sum(1 for c in CUR if final[c]!=CUR[c]))
