"""t216 工程·C:有解格 × 索引 seeds[2:5] × {基线, t216切带},胜负优先。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]
DRAFT=json.load(open(HERE/"t216_draft.json"))
def one(job):
    seed,combo,rid2=job
    if rid2>=0: os.environ["KAG_FORCE_ROUTE2"]=str(rid2)
    else: os.environ.pop("KAG_FORCE_ROUTE2",None)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/r6fr2_main.py")
        op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
        return seed,combo,rid2,float(g.reward(0)-g.reward(1))
    except Exception as e: return seed,combo,rid2,None
if __name__=="__main__":
    jobs=[]
    for c,rid in DRAFT.items():
        for s in IDX[c][2:5]:
            jobs.append((s,c,-1)); jobs.append((s,c,rid))
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=3))
    json.dump([list(r) for r in res],open(HERE/"t216_c.json","w"))
    per=collections.defaultdict(dict)
    for s,c,r,m in res:
        if m is not None: per[(c,s)][r]=m
    final={}
    for c,rid in sorted(DRAFT.items()):
        w=b=n=0
        for (c2,s),v in per.items():
            if c2!=c or rid not in v or -1 not in v: continue
            n+=1; w+=v[rid]>0; b+=v[-1]>0
        mark="进" if (n>0 and w>b) else ("平" if w==b else "弃")
        if mark=="进": final[c]=rid
        print(f"[{mark}] {c:34s} t216带{rid:3d} 表{w}/{n} 基线{b}/{n}")
    json.dump(final, open(HERE/"t216_final.json","w"))
    print("终进", len(final))
