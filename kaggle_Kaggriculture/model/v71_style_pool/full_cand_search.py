"""全量候选搜索:r5fr × {v52,v53,rescue7} × seed11800-11815 × 40 候选。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND=[-1]+[r for r in [0,1,3,4,5,6,7,8,9,10,11,12,100,101,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128]]
OPPS=["v52","v53","rescue7"]
def one(job):
    o,s,rid=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/{o}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=s); t=0; combo=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
            if t==146: combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
        return o,s,rid,combo,float(g.reward(0)-g.reward(1))
    except Exception as e:
        return o,s,rid,f"ERR{type(e).__name__}",None
if __name__=="__main__":
    jobs=[(o,s,r) for o in OPPS for s in range(11800,11816) for r in CAND]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"full_cand_search.json","w"))
    # 按 (对手族,组合) 聚合;v52/v53 归 K52
    fam=lambda o:"K52" if o in ("v52","v53") else "rescue7"
    per=collections.defaultdict(dict)
    for o,s,rid,c,m in res:
        if m is not None: per[(fam(o),o,s,c)][rid]=m
    for f in ("K52","rescue7"):
        cells=[(k,v) for k,v in per.items() if k[0]==f and -1 in v]
        bw=sum(1 for _,v in cells if v[-1]>0)
        orc=sum(1 for _,v in cells if max(v.values())>0)
        # 新候选(旧19外)是否夺魁
        OLD={-1,0,1,3,5,7,9,100,101,103,107,110,112,115,118,120,123,126,128}
        newbest=0
        for _,v in cells:
            b=max(v.items(),key=lambda kv:kv[1])
            if b[0] not in OLD and b[1]>0: newbest+=1
        print(f"{f}: 格{len(cells)} 基线胜{bw} 事后最优{orc} 新带夺魁{newbest}")
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
    for (f,o,s,c),v in per.items():
        if -1 not in v: continue
        for rid,m in v.items():
            a=agg[(f,c)][rid]; a[0]+=m>0; a[1]+=m; a[2]+=1
    for (f,c),rids in sorted(agg.items()):
        base=rids.get(-1,[0,0,1]); best=max(rids.items(),key=lambda kv:(kv[1][0],kv[1][1]))
        if best[0]!=-1 and best[1][0]>base[0]:
            print(f"{f:8s} {str(c):32s} 基线{base[0]}/{base[2]} -> 带{best[0]} {best[1][0]}/{best[1][2]}")
