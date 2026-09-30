"""rescue7 系代表搜索:最近 5 天 rescue7 棋盘(无 t92)上,候选代表的保真(模拟胜负与线上一致率、线上败局复现)。"""
import sys, os, json, glob, datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from review_fp import cls
def one(job):
    agent,opp_path,eid,seat=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(opp_path).parent))
    import fidelity, engine
    try:
        r=json.load(open(HERE/f"rlive3/{eid}.json"))
        me=fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py"); op=fidelity.make_agent(f"sub:{opp_path}")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"]); o=1-seat
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return job,float(g.reward(seat)-g.reward(o))
    except Exception: return job,None
if __name__=="__main__":
    SINCE=(datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
    ACT={"r32":"v54r32","r33":"v54r33","r34":"v54r34","r36":"v54r36","r38":"v54r38","r38b":"v54r38","r38c":"v54r38c"}
    B={}
    for x in json.load(open("axis_rows.json")):
        if x["cls"]=="rescue7系" and x["end"]>=SINCE and x["ver"] in ACT: B[x["eid"]]=(ACT[x["ver"]],x["seat"],x["d"])
    for e,v in json.load(open("online_games.json")).items():
        if v.get("key") and cls(float(round(v["key"][0])),v["lin"])=="rescue7系": B[e]=(ACT[v["ver"]],v["seat"],v["d"])
    B={e:v for e,v in B.items() if (HERE/f"rlive3/{e}.json").exists()}
    cands=[p for p in json.load(open("r7_cands.json")) if not os.path.basename(p).startswith(("v54r","v54fr","r5fr","r6fr","r17fr"))]
    print("rescue7 棋盘",len(B),"线上败局",sum(1 for v in B.values() if v[2]<0),"候选",len(cands),flush=True)
    jobs=[(v[0],p,e,v[1]) for p in cands for e,v in B.items()]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,jobs,chunksize=2))
    res=[]
    for p in cands:
        ok=sum(1 for e,v in B.items() if R.get((v[0],p,e,v[1])) is not None and (R[(v[0],p,e,v[1])]>0)==(v[2]>0))
        lw=sum(1 for e,v in B.items() if v[2]<0 and (R.get((v[0],p,e,v[1])) or 1)<0)
        res.append((ok,lw,p))
    for ok,lw,p in sorted(res,reverse=True)[:15]:
        print(f"   一致 {ok}/{len(B)} ({ok/len(B):.0%}) 败局复现 {lw}/{sum(1 for v in B.values() if v[2]<0)}  {p.split('model/')[-1][:90]}",flush=True)
