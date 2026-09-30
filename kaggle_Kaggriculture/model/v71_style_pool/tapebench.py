"""tape-bench:用 rlive 真实线上 replay 做对手带,按对手 rkey 族分组报告。
用法: python tapebench.py <版本>  ;覆盖线上长尾人口(bench 的盲区)。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
FAM={(1039.0,9989):"镜像键(V5x/rescue7)",(1042.0,9989):"herdsafe键",(151.0,9959):"K52键",(1049.0,9989):"metav4/V41/43/qq键",(1045.0,9989):"y68系",(1050.0,9989):"V38/y68系"}
def keyof(r,seat):
    o=1-seat
    try:
        obs=r["steps"][2][seat]["observation"]
        if "farms" not in obs: obs=r["steps"][2][0]["observation"]
        return (round(float(obs["farms"][o]["money"]),3), int(obs["market"]["inventory"]["WHEAT"]))
    except Exception: return None
def one(job):
    fn,ver=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(fn)); nm=r["info"]["TeamNames"]; s=r["steps"]
        seat=nm.index("datatuu"); o=1-seat
        rk=keyof(r,seat)
        op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
        me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        live=float((r["rewards"][seat] or 0)-(r["rewards"][o] or 0))
        return rk, float(g.reward(seat)-g.reward(o)), live
    except Exception as e: return None,None,None
if __name__=="__main__":
    ver=sys.argv[1]
    fs=[]
    for p in sorted(glob.glob(str(HERE/"rlive"/"episode-*.json"))):
        try:
            nm=json.load(open(p))["info"]["TeamNames"]
        except Exception: continue
        if nm.count("datatuu")==1: fs.append(p)
    print(f"{ver}: tape-bench {len(fs)} 局",flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,[(f,ver) for f in fs],chunksize=3))
    agg=collections.defaultdict(lambda:[0,0,0])
    for rk,m,live in res:
        if m is None: continue
        fam=FAM.get(rk,"长尾/未知")
        a=agg[fam]; a[0]+= m>0; a[1]+=1; a[2]+= (live or 0)>0
    T=[0,0,0]
    for fam,a in sorted(agg.items(), key=lambda kv:-kv[1][1]):
        T[0]+=a[0]; T[1]+=a[1]; T[2]+=a[2]
        print(f"  {fam:10s} {a[0]:3d}/{a[1]:3d} ({a[0]/max(1,a[1]):5.1%})  [线上原版 {a[2]}/{a[1]}]")
    print(f"  合计 {T[0]}/{T[1]} ({T[0]/max(1,T[1]):.1%})  [线上原版 {T[2]}/{T[1]} ({T[2]/max(1,T[1]):.1%})]")
