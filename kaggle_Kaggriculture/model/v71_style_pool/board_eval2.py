"""通用真实棋盘评测。用法: python board_eval2.py <棋盘json> <键/谱系;..> <对手> <版本|actual,...> <输出tag> [env=val,...给我方]"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
def one(job):
    agent,opp,seed,seat,eid,env=job
    for k in list(os.environ):
        if k.startswith(("KAG_CUT","KAG_EXEC","KAG_MILK","KAG_KEYMAP")): os.environ.pop(k,None)
    for kv in env:
        k,v=kv.split("=",1); os.environ[k]=v
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{agent}_main.py"); op=fidelity.make_agent(f"sub:{OPP[opp]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return eid,float(g.reward(seat)-g.reward(o))
    except Exception: return eid,None
def run(boards,agent,opp,env=(),procs=7):
    jobs=[(agent,opp,x["seed"],x["seat"],x["eid"],tuple(env)) for x in boards]
    with ProcessPoolExecutor(procs) as ex: return dict(ex.map(one,jobs,chunksize=2))
if __name__=="__main__":
    bf,groups,opp,vers,tag=sys.argv[1:6]; env=sys.argv[6].split(",") if len(sys.argv)>6 else []
    G=[tuple(g.split("/")) for g in groups.split(";")]
    B=[x for x in json.load(open(HERE/bf)) if x.get("seed") is not None and (x["key"],x["lin"]) in G]
    out={}
    for v in vers.split(","):
        if v=="actual":
            by=collections.defaultdict(list)
            for x in B: by[x["ver"]].append(x)
            res={}
            for ver,bs in by.items(): res.update(run(bs,f"v54{ver}",opp))
            agree=sum(1 for x in B if res.get(x["eid"]) is not None and (res[x["eid"]]>0)==(x["d"]>0)); n=sum(1 for x in B if res.get(x["eid"]) is not None)
            print(f"  actual(实际参赛版本) vs {opp}: 与线上一致 {agree}/{n} ({agree/max(1,n):.0%})",flush=True)
        else:
            res=run(B,v if (HERE/f"agents/{v}_main.py").exists() else f"v54{v}",opp,env)
            w=sum(1 for d in res.values() if d is not None and d>0); n=sum(1 for d in res.values() if d is not None)
            print(f"  {v}{'['+','.join(env)+']' if env else ''} vs {opp}: {w}/{n} ({w/max(1,n):.0%})",flush=True)
        out[v]=res
    json.dump(out,open(HERE/f"be2_{tag}.json","w"))
