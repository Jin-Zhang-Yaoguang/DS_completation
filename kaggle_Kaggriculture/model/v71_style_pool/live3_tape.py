"""rlive3 真实 2100-2200 段对手动作带重放(开环)。用法: python live3_tape.py <版本,版本,...>
按 rkey 键 + t92 谱系分组报告;同时跑 v54live 100 局旧动作带。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    kind,fn,ver=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(fn))
        if kind=="live3":
            seat=r["seat"]; o=1-seat; tape=[r["acts"][t+1][o] for t in range(len(r["acts"])-1)]; seed=r["seed"]
            mo=r["money"]; lin="cha" if mo[92] and mo[91] and mo[92][o]-mo[91][o]>50 else "main"
        else:
            nm=r["info"]["TeamNames"]; s=r["steps"]; seat=nm.index("datatuu"); o=1-seat
            tape=[s[t+1][o].get("action") or {} for t in range(len(s)-1)]; seed=r["info"]["seed"]; lin="-"
        op=fidelity.tape_agent(tape); me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        k=engine.load_kagsim(); g=k.Game(seed=seed)
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return kind,Path(fn).stem,ver,lin,float(g.reward(seat)-g.reward(o))
    except Exception as e: return kind,Path(fn).stem,ver,"ERR",None
if __name__=="__main__":
    vers=sys.argv[1].split(",")
    H=json.load(open(HERE/"rkey_head.json"))
    f3=sorted(glob.glob(str(HERE/"rlive3/*.json")))
    f1=[f for f in sorted(glob.glob(str(HERE/"v54live/episode-*.json"))) if json.load(open(f))["info"]["TeamNames"].count("datatuu")==1]
    jobs=[("live3",f,v) for f in f3 for v in vers]+[("v54live",f,v) for f in f1 for v in vers]
    print("任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    json.dump(res,open(HERE/f"live3_tape_{'_'.join(vers)}.json","w"))
    agg=collections.defaultdict(lambda:[0,0,0.0])
    for kind,e,ver,lin,m in res:
        if m is None: continue
        key=kind if kind=="v54live" else f"live3 {str(H.get(e,{}).get('rkey',['?'])[0])[:6]} {lin}"
        for k in (key, kind+" 合计"):
            a=agg[(k,ver)]; a[0]+=m>0; a[1]+=1; a[2]+=m
    for k in sorted({k for k,_ in agg}):
        print(f"{k:24s} "+"  ".join(f"{v}: {agg[(k,v)][0]}/{agg[(k,v)][1]}({agg[(k,v)][2]/max(1,agg[(k,v)][1]):+6.0f})" for v in vers))
