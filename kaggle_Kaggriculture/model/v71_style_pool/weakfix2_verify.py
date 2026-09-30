"""第二轮留出复验+跨族安全:12 格 × 新 seed × {rescue7,v54,v56}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v54"]; IDX2=json.load(open(HERE/"combo_index2.json"))["v54"]
NEW=json.load(open(HERE/"weakfix2_draft.json"))
OPPS=["rescue7","v54","v56"]
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
    jobs=[]; short=[]
    for c,new in NEW.items():
        seeds=(IDX2.get(c,[])[5:10]+IDX.get(c,[])[3:6])
        if len(seeds)<4: short.append((c,len(seeds)))
        for s in seeds:
            for o in OPPS:
                jobs.append((c,s,-1,o)); jobs.append((c,s,new,o))
    if short: print("seed 偏少:", short)
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"weakfix2_ver.json","w"))
    per=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,o,m in res:
        if m is None: continue
        a=per[(c,o)][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,new in sorted(NEW.items()):
        rows=[]; ok=False; safe=True
        for o in OPPS:
            bw,bn,bm=per[(c,o)].get(-1,[0,0,0.0]); nw,nn,nm=per[(c,o)].get(new,[0,0,0.0])
            rows.append(f"{o}:{nw}/{nn}(基{bw})")
            if o=="rescue7" and nn>0 and nw>bw: ok=True
            if o!="rescue7" and nn>0 and nw<bw: safe=False
        if ok and safe: final[c]=new
        print(f"[{'进' if (ok and safe) else ('跨族劣' if ok else '弃')}] {c:30s} 带{new:4d}  {'  '.join(rows)}")
    json.dump(final, open(HERE/"weakfix2_final.json","w"))
    print("终进", len(final))
