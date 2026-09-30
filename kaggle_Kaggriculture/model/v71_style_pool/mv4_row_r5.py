"""metav4 键行研究(r5 底):rlive 中对手 rkey=(1052,9989) 的局,r5fr 全候选网格。"""
import sys, os, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND=[-1,0,1,3,5,7,9,100,101,103,107,110,112,115,118,120,123,126,128]
def keyof(r, seat):
    o=1-seat
    try:
        obs=r["steps"][2][seat]["observation"]
        if "farms" not in obs: obs=r["steps"][2][0]["observation"]
        return (round(float(obs["farms"][o]["money"]),3), int(obs["market"]["inventory"]["WHEAT"]))
    except Exception: return None
def one(job):
    fn, seat, rid = job
    os.environ["KAG_FORCE_ROUTE"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(fn)); s=r["steps"]; o=1-seat
        op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/r5fr_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"]); t=0; combo=None
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1]); t+=1
            if t==146: combo="|".join(((g.observe(seat).get("town") or {}).get("unlocked_shops") or [])[:2])
        return Path(fn).name, rid, combo, float(g.reward(seat)-g.reward(o))
    except Exception as e:
        return Path(fn).name, rid, f"ERR{type(e).__name__}", None
if __name__=="__main__":
    files=[]
    for p in sorted(glob.glob(str(HERE/"rlive"/"episode-*.json"))):
        try: r=json.load(open(p))
        except Exception: continue
        nm=r["info"]["TeamNames"]
        if nm.count("datatuu")!=1: continue
        seat=nm.index("datatuu")
        if keyof(r,seat)==(1052.0,9989): files.append((p,seat))
    print("metav4 键局数",len(files),flush=True)
    jobs=[(fn,seat,r) for fn,seat in files for r in CAND]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    json.dump([list(r) for r in res],open(HERE/"mv4_row_r5.json","w"))
    per=collections.defaultdict(dict)
    for n,r,c,m in res:
        if m is not None: per[(n,c)][r]=m
    bw=sum(1 for v in per.values() if v.get(-1,0)>0)
    orc=sum(1 for v in per.values() if v and max(v.values())>0)
    print(f"局 {len(per)};r5基线胜 {bw};事后最优 {orc}")
    # 基线败局的可翻带
    for (n,c),v in sorted(per.items()):
        if v.get(-1,1)<=0:
            flips=sorted(r for r,m in v.items() if r!=-1 and m>0)
            print(f"  败局 {n} {c} 基线{v[-1]:+.0f} 可翻带 {flips[:8]}")
