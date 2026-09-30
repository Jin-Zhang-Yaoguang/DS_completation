"""线上 v55b 对局的对手 → 本地哪个代表最像:本地重演(我方=v55b),逐步比对对手动作,首个不一致即停。"""
import json,sys,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(HERE)); os.chdir(HERE)
from pub_splice import OPP,M
IDX=json.load(open("online_games.json"))
def norm(a): return json.dumps(a or {},sort_keys=True)
def one(job):
    eid,opp=job
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[opp]).parent))
    import fidelity,engine
    r=json.load(open(f"rlive3/{eid}.json")); s=r["seat"]; o=1-s; A=r["acts"]
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/v55b_main.py"); op=fidelity.make_agent(f"sub:{OPP[opp]}")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"]); t=1
        while not engine._val(g.done) and t<len(A):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[s]=A[t][s]; a[o]=op(obs[o])
            if norm(a[o])!=norm(A[t][o]): return eid,opp,t-1
            g.step(a[0],a[1]); t+=1
        return eid,opp,t-1
    except Exception as e: return eid,opp,-1
if __name__=="__main__":
    E=[e for e,v in IDX.items() if v["ver"]==sys.argv[1]]
    cands=[k for k in OPP if not k.startswith(("v55","afrep","op_o","hsx"))]
    with ProcessPoolExecutor(8) as ex: R=list(ex.map(one,[(e,c) for e in E for c in cands],chunksize=2))
    best={}
    for e,c,n in R: best.setdefault(e,[]).append((n,c))
    out={}
    for e in E:
        b=sorted(best[e],reverse=True)[:3]; out[e]=b
        print(e,IDX[e]["opp_team"][:20].ljust(20),"key",round(IDX[e]["key"][0]),"d",round(IDX[e]["d"]),"最像:",b)
    json.dump(out,open(f"ana/rep_match_{sys.argv[1]}.json","w"),ensure_ascii=False)
