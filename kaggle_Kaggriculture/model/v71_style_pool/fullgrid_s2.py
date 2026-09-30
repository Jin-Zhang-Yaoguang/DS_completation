"""r7 全格工程·阶段2 精验:入围格 × seeds[1:4] × {v54,v56,rescue7} × {基线,候选}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
PICKS=json.load(open(HERE/"fullgrid_picks.json"))
OPPS=["v54","v56","rescue7"]
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
    for c,rid in PICKS.items():
        for s in IDX[c][1:4]:
            for o in OPPS:
                jobs.append((o,s,-1,c)); jobs.append((o,s,rid,c))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"fullgrid_s2.json","w"))
    per=collections.defaultdict(dict)
    for o,s,r,c,m in res:
        if m is not None: per[(c,o,s)][r]=m
    final={}
    for c,rid in sorted(PICKS.items()):
        w=b=n=0; byo=collections.Counter(); byob=collections.Counter(); byon=collections.Counter()
        for (c2,o,s),v in per.items():
            if c2!=c or rid not in v or -1 not in v: continue
            n+=1; w+=v[rid]>0; b+=v[-1]>0
            byo[o]+=v[rid]>0; byob[o]+=v[-1]>0; byon[o]+=1
        # 胜负优先 + 任一子族不得劣于基线超过1
        ok = w>b and all(byo[o]>=byob[o]-0 for o in byon)
        mark="进" if ok else "弃"
        if ok: final[c]=rid
        detail=" ".join(f"{o}:{byo[o]}/{byon[o]}({byob[o]})" for o in byon)
        print(f"[{mark}] {c:32s} 带{rid:3d} 总{w}/{n}(基线{b}) {detail}")
    json.dump(final, open(HERE/"fullgrid_final.json","w"))
    print("终进", len(final))
