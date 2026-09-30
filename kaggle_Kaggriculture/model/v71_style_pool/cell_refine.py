"""格值精炼:现表 16 镜像格,每格候选带 × 索引 seeds × 3 子族,配对口径重选最优。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
CUR={"BRUNCH_SPOT|YARN_STORE":103,"ICE_CREAM_SHOP|FARMERS_MARKET":120,"PIZZA_SHOP|ICE_CREAM_SHOP":107,
 "ICE_CREAM_SHOP|BRUNCH_SPOT":110,"SMOOTHIE_SHOP|ICE_CREAM_SHOP":107,"ICE_CREAM_SHOP|YARN_STORE":100,
 "PET_CAFE|SMOOTHIE_SHOP":112,"SMOOTHIE_SHOP|YARN_STORE":126,"SMOOTHIE_SHOP|BAKERY":120,
 "FARMERS_MARKET|ICE_CREAM_SHOP":110,"BRUNCH_SPOT|PET_CAFE":107,"PIZZA_SHOP|FARMERS_MARKET":112,
 "PET_CAFE|PIZZA_SHOP":123,"BRUNCH_SPOT|BRUNCH_SPOT":110,"PET_CAFE|BAKERY":124,"PIZZA_SHOP|YARN_STORE":126}
# 候选带:现值 + 历史常胜带短名单
SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
OPPS=["v54","v56","rescue7"]
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
    for c,cur in CUR.items():
        seeds=IDX[c][:5]
        cands=sorted(set(SHORT+[cur]))
        for s in seeds:
            for r in cands:
                for o in OPPS: jobs.append((c,s,r,o))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"cell_refine.json","w"))
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,o,m in res:
        if m is None: continue
        a=agg[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    newtab={}
    for c,cur in sorted(CUR.items()):
        rows=agg[c]
        if cur not in rows: continue
        cw,cn,cm=rows[cur]
        best=max(rows.items(), key=lambda kv:(kv[1][0], kv[1][2]))
        bw,bn,bm=best[1]
        flag="改" if (best[0]!=cur and bw>cw) else "留"
        newtab[c]=best[0] if flag=="改" else cur
        print(f"[{flag}] {c:30s} 现{cur:4d} {cw}/{cn}({cm/max(1,cn):+.0f}) -> 最优{best[0]:4d} {bw}/{bn}({bm/max(1,bn):+.0f})")
    json.dump(newtab, open(HERE/"cell_refine_draft.json","w"))
    print("改值格:", sum(1 for c in CUR if newtab.get(c)!=CUR[c]))
