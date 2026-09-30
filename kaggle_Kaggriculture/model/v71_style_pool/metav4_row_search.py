"""metav4 行搜索:w48fr × metav4 × seed10500-10531 × 19 候选;含内置留出(前16搜索/后16复验)。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND=[-1,0,1,3,5,7,9,100,101,103,107,110,112,115,118,120,123,126,128]
def one(job):
    seed,rid=job
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/w48fr_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/metav4_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed); t=0; combo=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1])); t+=1
            if t==146: combo="|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
        return seed,rid,combo,float(g.reward(0)-g.reward(1))
    except Exception as e:
        return seed,rid,f"ERR{type(e).__name__}",None
if __name__=="__main__":
    jobs=[(s,r) for s in range(10500,10532) for r in CAND]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"metav4_row.json","w"))
    A={}; B={}
    for s,r,c,m in res:
        if m is None: continue
        (A if s<10516 else B).setdefault((s,c),{})[r]=m
    # 搜索半:选格
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
    for (s,c),v in A.items():
        if -1 not in v: continue
        for r,m in v.items():
            a=agg[c][r]; a[0]+=m>0; a[1]+=m; a[2]+=1
    draft={}
    for c,rids in agg.items():
        base=rids.get(-1,[0,0,1]); best=max(rids.items(),key=lambda kv:(kv[1][0],kv[1][1]))
        if best[0]!=-1 and best[1][0]>base[0]: draft[c]=best[0]
    print("搜索半草案:",draft)
    # 复验半
    for c,rid in sorted(draft.items()):
        w=b=n=0
        for (s,c2),v in B.items():
            if c2!=c or rid not in v or -1 not in v: continue
            n+=1; w+=v[rid]>0; b+=v[-1]>0
        mark="进" if (n>0 and w>b) else "证据不足/弃"
        print(f"  [{mark}] {c:34s} 路线{rid:4d} 复验 表{w}/{n} 基线{b}/{n}")
