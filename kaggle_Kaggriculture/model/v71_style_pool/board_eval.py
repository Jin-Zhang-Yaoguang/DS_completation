"""真实棋盘评测:线上对局种子+席位,我方各版本 vs 谱系代表方案(闭环)。用法: python board_eval.py r25,r26,r28"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
REP={("1042.0","cha"):"engineV3",("1042.0","main"):"engineV3"}
def one(job):
    ver,opp,seed,seat,eid=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v54{ver}_main.py"); op=fidelity.make_agent(f"sub:{OPP[opp]}")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return ver,eid,float(g.reward(seat)-g.reward(o))
    except Exception as e: return ver,eid,None
if __name__=="__main__":
    vers=sys.argv[1].split(",")
    rows=[x for x in json.load(open(HERE/"scan_live_rows.json")) if x.get("seed") is not None and (x["key"],x["lin"]) in REP]
    jobs=[(v,REP[(x["key"],x["lin"])],x["seed"],x["seat"],x["eid"]) for x in rows for v in vers]
    print("棋盘",len(rows),"任务",len(jobs),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    R={(v,e):d for v,e,d in res}
    json.dump([[v,e,d] for v,e,d in res],open(HERE/f"board_eval_{'_'.join(vers)}.json","w"))
    A=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0])); agree=collections.defaultdict(lambda:[0,0])
    for x in rows:
        g=(x["key"],x["lin"])
        for v in vers:
            d=R.get((v,x["eid"]))
            if d is None: continue
            a=A[g][v]; a[0]+=d>0; a[1]+=1
            if v==x["ver"]: b=agree[g]; b[0]+=(d>0)==(x["d"]>0); b[1]+=1
    for g in A:
        print(f"  {str(g):20s} 模拟: "+"  ".join(f"{v}:{A[g][v][0]}/{A[g][v][1]}" for v in vers)+f"   | 与线上真实胜负一致率 {agree[g][0]}/{agree[g][1]}")
