"""D. Sida Zuo 行搜索:w48fr vs Sida tape,40 局(24 搜/16 验)× 19 候选;记录 rkey/combo。"""
import sys, os, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
CAND=[-1,0,1,3,5,7,9,100,101,103,107,110,112,115,118,120,123,126,128]
TARGET="Sida Zuo"; N=40
def one(job):
    fn, seat, rid = job
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(fn)); s=r["steps"]
        op=fidelity.tape_agent([s[t+1][seat].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/w48fr_main.py")
        my=1-seat
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"]); t=0; rkey=None; combo=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]
            if t==2:
                rv=obs[my]["farms"][seat]
                rkey=(round(float(rv["money"]),3), int(obs[my]["market"]["inventory"]["WHEAT"]))
            a=[None,None]; a[my]=me(obs[my]); a[seat]=op(obs[seat]); g.step(a[0],a[1]); t+=1
            if t==146: combo="|".join(((g.observe(my).get("town") or {}).get("unlocked_shops") or [])[:2])
        return Path(fn).name, rid, str(rkey), combo, float(g.reward(my)-g.reward(seat))
    except Exception as e:
        return str(fn), rid, f"ERR{type(e).__name__}", None, None
if __name__=="__main__":
    files=[]
    for d in ("2026-09-20","2026-09-19"):
        for fn in sorted(glob.glob(str(ROOT/f"date={d}"/"data"/"*.json"))):
            try: nm=json.load(open(fn))["info"]["TeamNames"]
            except Exception: continue
            if TARGET in nm: files.append((fn, nm.index(TARGET)))
            if len(files)>=N: break
        if len(files)>=N: break
    jobs=[(fn,seat,r) for fn,seat in files for r in CAND]
    print("局",len(files),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    json.dump([list(r) for r in res],open(HERE/"sida_row.json","w"))
    ks=collections.Counter(k for _,r,k,_,_ in res if r==-1)
    print("rkey 分布:",dict(ks.most_common(4)))
    A={}; B={}
    for i,(fn,seat) in enumerate(files):
        d=A if i<24 else B
        for name,r,k,c,m in res:
            if name==Path(fn).name and m is not None: d.setdefault((name,c),{})[r]=m
    agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
    for (n,c),v in A.items():
        if -1 not in v: continue
        for r,m in v.items():
            a=agg[c][r]; a[0]+=m>0; a[1]+=m; a[2]+=1
    draft={}
    for c,rids in agg.items():
        base=rids.get(-1,[0,0,1]); best=max(rids.items(),key=lambda kv:(kv[1][0],kv[1][1]))
        if best[0]!=-1 and best[1][0]>base[0]: draft[c]=best[0]
    print("搜索半草案:",draft)
    for c,rid in sorted(draft.items()):
        w=b=n=0
        for (nm,c2),v in B.items():
            if c2!=c or rid not in v or -1 not in v: continue
            n+=1; w+=v[rid]>0; b+=v[-1]>0
        mark="进" if (n>0 and w>b) else "证据不足/弃"
        print(f"  [{mark}] {str(c):34s} 路线{rid:4d} 复验 表{w}/{n} 基线{b}/{n}")
