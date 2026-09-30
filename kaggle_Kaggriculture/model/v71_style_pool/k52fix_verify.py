"""K52 补格留出复验:7 格 × seeds[5:] × {v52,v53} × {基线,新值}。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
IDX=json.load(open(HERE/"combo_index.json"))["v52"]
NEW=json.load(open(HERE/"k52fix_draft.json"))
OPPS=["v52","v53"]
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
    jobs=[]; info=[]
    for c,new in NEW.items():
        seeds=IDX.get(c,[])[5:]
        info.append((c,len(seeds)))
        for s in seeds:
            for o in OPPS:
                jobs.append((c,s,-1,o)); jobs.append((c,s,new,o))
    print("留出 seed 数:", info); print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/"k52fix_ver.json","w"))
    per=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
    for c,s,r,o,m in res:
        if m is None: continue
        a=per[c][r]; a[0]+= m>0; a[1]+=1; a[2]+=m
    final={}
    for c,new in sorted(NEW.items()):
        bw,bn,bm=per[c].get(-1,[0,0,0.0]); nw,nn,nm=per[c].get(new,[0,0,0.0])
        ok = nn>=4 and nw>bw
        if ok: final[c]=new
        print(f"[{'进' if ok else ('样本不足' if nn<4 else '弃')}] {c:30s} 带{new:4d} 基线{bw}/{bn}({bm/max(1,bn):+.0f}) 新{nw}/{nn}({nm/max(1,nn):+.0f})")
    json.dump(final, open(HERE/"k52fix_final.json","w"))
    print("终进", len(final))
